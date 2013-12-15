import serial
import time
import binascii

class IcomRadio:
    mode_bytes = {'FM':  [0x05, 0x01],
                'USB':  [0x01, 0x01],
                'LSB':  [0x00, 0x01],
                'AM':   [0x02, 0x01],
                'CW':   [0x03, 0x01],
                'CW-N': [0x03, 0x02],
                'RTTY': [0x04, 0x01],
                'WFM':  [0x06, 0x01] }
    
    def __init__(self, radio_addr, serial_port):
        self.radio_addr = radio_addr
        self.comp_addr = 0xE0
        self.s = serial.Serial(port=serial_port, baudrate=19200,
                               timeout=0, writeTimeout=0.5)
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
        time.sleep(.020)
        n = 0 
        t0 = time.clock() 
        while (time.clock() - t0) < 0.5:
            b = self.s.read(1)
            if len(b) != 1:
                continue
            if n == len(validate):
                if b == b'\xFD':
                    return binascii.b2a_hex(response).decode('ascii').upper()
                else:
                    response += b
            elif ord(b) == validate[n]:
                n=n+1
        print('timed out')
        return 'FF' 
            
    def set_freq(self, freq):
        if not freq.isdigit() or len(freq) != 10:
            return 'FF'
        payload = []
        for x in range(0,5):
            payload.insert(0, int(freq[2*x:2*x+2], 16))
        return self.cmd([0x05], payload)
        
    def set_mem(self, memnum):
        if not memnum.isdigit() or len(memnum) != 2:
            return 'FF'
        b = self.cmd([0x08])
        if b != 'FB':
            return b
        return self.cmd([0x08], [int(memnum, 16)])
            
    def set_vfo(self, l):
        vfo_bytes = {'A' : 0x00, 'B' : 0x01}
        if l not in vfo_bytes.keys():
            return 'FF'
        r = self.cmd([0x07], [vfo_bytes[l]])
        if r != 'FB':
            return r
        mode = self.read_mode()
        if mode == 'FA' or mode == 'FF':
            return mode
        freq = self.read_freq()
        if freq == 'FA' or freq == 'FF':
            return freq
        return mode + ' ' + freq
        
    def scan_start(self):
        return self.cmd([0x0E], [0x01])
    
    def scan_stop(self):
        r = self.cmd([0x0E], [0x00])
        if r != 'FB':
            return r
        return self.read_freq()
        
    def set_mode(self, m):
        if m not in self.mode_bytes:
            return 'FF'
        return self.cmd([0x06], self.mode_bytes[m])
    
    def read_freq(self):
        response = self.cmd([0x03], respond_with_data=True)
        if len(response) < 10:
            return response
        f = response[8:10] + response[6:8] + response[4:6] 
        f += response[2:4] + response[0:2]
        return f
    
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
        if response in mode_decode.keys():
            return mode_decode[response]
        else:
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
            if response1 == 'FB' and response2 == 'FB':
                return 'FB'
        return 'FF'
        
    def set_agc(self, a):
        if a == 'FAST':
            n = 0x01
        elif a == 'SLOW':
            n = 0x02
        else:
            return 'FF'
        return self.cmd([0x16, 0x12], [n])

