import serial
import time
import binascii

class IcomRadio:
    BAD_INPUT = { 'success': False, 'error': 'BAD_INPUT' }

    MODE_BYTES = { 'FM':  [0x05, 0x01],
                'USB':  [0x01, 0x01],
                'LSB':  [0x00, 0x01],
                'AM':   [0x02, 0x01],
                'CW':   [0x03, 0x01],
                'CW-N': [0x03, 0x02],
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
        response = bytearray()
        validate = [self.comp_addr, self.radio_addr]
        if respond_with_data:
            validate.extend(cmd_bytes)
        to_send = [0xFE, 0xFE, self.radio_addr, self.comp_addr]
        to_send.extend(cmd_bytes)
        to_send.extend(payload)
        to_send.append(0xFD)
        self.flush()
        self.s.write(bytearray(to_send))
        #time.sleep(.200)
        i = 0
        n = 0
        t0 = time.time() 
        while (time.time() - t0) < 5.0:
            b = self.s.read(1)
            if len(b) != 1:
                i += 1
                continue
            if n == len(validate):
                if b == b'\xFD':
                    r = binascii.b2a_hex(response).decode('ascii')
                    if respond_with_data:
                        return {'success': True, 'data': r}
                    else:
                        if r == 'fb':
                            return { 'success': True }
                        else:
                            return { 'success': False, 'error': 'CI-V_ERROR' }
                else:
                    response += b
            elif ord(b) == validate[n]:
                n=n+1
        print('timed out')
        return { 'success': False, 'error': 'RADIO_NO_REPONSE' }
            
    def set_freq(self, freq):
        if not freq.isdigit() or len(freq) != 10:
            return IcomRadio.BAD_INPUT
        payload = []
        for x in range(0,5):
            payload.insert(0, int(freq[2*x:2*x+2], 16))
        response = self.cmd([0x05], payload)
        if response['success']:
            return { 'success': True, 'data': freq }
        else:
            return response
        
    def set_mem(self, memnum):
        if not memnum.isdigit() or len(memnum) != 2:
            return IcomRadio.BAD_INPUT
        b = self.cmd([0x08])
        if b['success']:
            return self.cmd([0x08], [int(memnum, 16)])
        else:
            return b
            
    def set_vfo(self, l):
        vfo_bytes = { 'A' : 0x00, 'B' : 0x01 }
        if l not in vfo_bytes.keys():
            return IcomRadio.BAD_INPUT
        r = self.cmd([0x07], [vfo_bytes[l]])
        if not r['success']:
            return r
        mode = self.read_mode()
        if not mode['success']:
            return mode
        freq = self.read_freq()
        if not freq['success']:
            return freq
        return { 'success': True, 'data': mode['data'] + ' ' + freq['data'] }
        
    def scan_start(self):
        return self.cmd([0x0E], [0x01])
    
    def scan_stop(self):
        r = self.cmd([0x0E], [0x00])
        if r['success']:
            return self.read_freq()
        else:
            return r
        
    def set_mode(self, m):
        if m not in IcomRadio.MODE_BYTES:
            return IcomRadio.BAD_INPUT
        return self.cmd([0x06], self.MODE_BYTES[m])
    
    def read_freq(self):
        response = self.cmd([0x03], respond_with_data=True)
        data = response['data']
        if len(data) < 10:
            return response
        f = data[8:10] + data[6:8] + data[4:6] 
        f += data[2:4] + data[0:2]
        return { 'success': True, 'data': f}
    
    def read_mode(self):
        mode_decode = { '0001' : 'LSB',
                        '0101' : 'USB',
                        '0201' : 'AM',
                        '0301' : 'CW',
                        '0302' : 'CW-N',
                        '0401' : 'RTTY',
                        '0501' : 'FM',
                        '0601' : 'WFM' }

        response = self.cmd([0x04], respond_with_data=True)
        if response['data'] in mode_decode.keys():
            response['data'] = mode_decode[response['data']]
        return response
    
    def read_att(self):
        return self.cmd([0x11], respond_with_data=True)
        
    def read_meter(self):
        return self.cmd([0x15, 0x02], respond_with_data=True)
    
    def set_patt(self, a):
        if a == 'PRE':
            return self.cmd([0x16, 0x02],  [0x01])
        elif a =='ATT':
            return self.cmd([0x11], [0x20])
        elif a == 'OFF':
            response1 = self.cmd([0x16, 0x02], [0x00])
            response2 = self.cmd([0x11], [0x00])
            return { 'success': response1['success'] and response2['success'] } 
        return IcomRadio.BAD_INPUT
        
    def set_agc(self, a):
        if a == 'FAST':
            n = 0x01
        elif a == 'SLOW':
            n = 0x02
        else:
            return IcomRadio.BAD_INPUT
        return self.cmd([0x16, 0x12], [n])

