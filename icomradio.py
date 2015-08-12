import serial
import time
import binascii

class IcomRadio:
    BAD_INPUT = { 'success': False, 'error': 'Bad argument for cmd' }

    MODE_BYTES = { 'FM':  [0x05, 0x01],
                'USB':  [0x01, 0x01],
                'LSB':  [0x00, 0x01],
                'AM':   [0x02, 0x01],
                'CW':   [0x03, 0x01],
                'CWN': [0x03, 0x02],
                'RTTY': [0x04, 0x01],
                'WFM':  [0x06, 0x01] }
   
    VALID_CMDS = frozenset(['scan_start',
                            'scan_stop',
                            'set_mode',
                            'set_freq',
                            'set_patt',
                            'set_agc'])    
   
    def __init__(self, radio_addr, serial_port):
        self.radio_addr = radio_addr
        self.comp_addr = 0xE0
        self.s = serial.Serial(port=serial_port, baudrate=19200,
                               timeout=1, writeTimeout=1)
        print('acquired serial port')

    def flush(self):
        self.s.flushInput()        

    def cmd(self, cmd_bytes, payload=[], respond_with_data=False):
        validate = [0xFE, 0xFE, self.comp_addr, self.radio_addr]
        if respond_with_data:
            validate.extend(cmd_bytes)

        to_send = [0xFE, 0xFE, self.radio_addr, self.comp_addr]
        to_send.extend(cmd_bytes)
        to_send.extend(payload)
        to_send.append(0xFD)

        receiving = False
        response = bytearray()
        last_n_recvd = [0] * len(validate)

        self.flush()
        self.s.write(bytearray(to_send))

        t0 = time.time() 

        while (time.time() - t0) < 1.0:
            b = self.s.read(1)
            if len(b) != 1:
                continue
            if receiving:
                if b == b'\xFD':
                    r = binascii.b2a_hex(response).decode('ascii')
                    if respond_with_data:
                        return {'success': True, 'data': r}
                    else:
                        if r == 'fb':
                            return { 'success': True }
                        else:
                            return { 'success': False, 'error': 'CI-V error: ' + r }
                else:
                    response += b
            else:
                last_n_recvd.pop(0)
                last_n_recvd.append(ord(b))
                if validate == last_n_recvd:
                    receiving = True

        print('timed out')
        return { 'success': False, 'error': 'Radio off or serial conn down' }
            
    def set_freq(self, freq):
        if not freq.isdigit() or len(freq) > 10:
            return IcomRadio.BAD_INPUT
        freq = freq.zfill(10)
        payload = []
        for x in range(0,5):
            payload.insert(0, int(freq[2*x:2*x+2], 16))
        r = self.cmd([0x05], payload)
        if r['success']:
            r['data'] = int(freq)
        return r
        
    def set_mem(self, memnum):
        if not memnum.isdigit() or len(memnum) > 2:
            return IcomRadio.BAD_INPUT
        memnum = memnum.zfill(2)
        bcd = int(memnum[0]) << 4 | int(memnum[1])
        r = self.cmd([0x08])
        if r['success']:
            r = self.cmd([0x08], [bcd])
            if r['success']:
                r['data'] = int(memnum, 10)
        return r
            
    def set_vfo(self, vfo):
        if vfo == 'Mem':
            r = self.cmd([0x08])
        else:
            vfo_bytes = { 'A' : 0x00, 'B' : 0x01 }
            if vfo not in vfo_bytes.keys():
                return IcomRadio.BAD_INPUT
            r = self.cmd([0x07], [vfo_bytes[vfo]])
        if r['success']:
            r['data'] = vfo
        return r
        
    def set_scan(self, scan):
        if scan == 'True':
            b = [0x01]
        elif scan == 'False':
            b = [0x00]
        else:
            return IcomRadio.BAD_INPUT
        r = self.cmd([0x0E], b)
        if r['success']:
            r['data'] = scan == 'True'
        return r
        
    def set_mode(self, m):
        m = m.upper()
        if m not in IcomRadio.MODE_BYTES:
            return IcomRadio.BAD_INPUT
        r = self.cmd([0x06], self.MODE_BYTES[m])
        if r['success']:
            r['data'] = m
        return r
    
    def read_freq(self):
        response = self.cmd([0x03], respond_with_data=True)
        data = response['data']
        if len(data) < 10:
            return response
        f = data[8:10] + data[6:8] + data[4:6] 
        f += data[2:4] + data[0:2]
        return { 'success': True, 'data': int(f)}
    
    def read_mode(self):
        mode_decode = { '0001' : 'LSB',
                        '0101' : 'USB',
                        '0201' : 'AM',
                        '0301' : 'CW',
                        '0302' : 'CWN',
                        '0401' : 'RTTY',
                        '0501' : 'FM',
                        '0601' : 'WFM' }

        r = self.cmd([0x04], respond_with_data=True)
        if r['success'] and (r['data'] in mode_decode.keys()):
            r['data'] = mode_decode[r['data']]
        return r
    
    def read_att(self):
        return self.cmd([0x11], respond_with_data=True)
        
    def read_meter(self):
        r = self.cmd([0x15, 0x02], respond_with_data=True)
        if r['success']:
            r['data'] = int(r['data'])
        return r
    
    def set_patt(self, a):
        if a == 'Pre':
            r = self.cmd([0x16, 0x02],  [0x01])
        elif a =='Att':
            r = self.cmd([0x11], [0x20])
        elif a == 'Off':
            r1 = self.cmd([0x16, 0x02], [0x00])
            r2 = self.cmd([0x11], [0x00])
            r = { 'success': r1['success'] and r2['success'] }
        else:
            return IcomRadio.BAD_INPUT
        if r['success']:
            r['data'] = a
        return r
        
    def set_agc(self, a):
        if a == 'Fast':
            n = 0x01
        elif a == 'Slow':
            n = 0x02
        else:
            return IcomRadio.BAD_INPUT
        r = self.cmd([0x16, 0x12], [n])
        if (r['success']):
            r['data'] = a
        return r

