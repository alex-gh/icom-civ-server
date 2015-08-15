import serial
import time


class CivError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return 'CI-V Error: ' + str(self.msg)


class ComError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return 'Com Error: ' + str(self.msg)


class BadInputError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return 'Bad input: ' + str(self.msg)


class IcomRadio:
    BYTES_FOR_MODE = {
        'FM': b'\x05\x01',
        'USB': b'\x01\x01',
        'LSB': b'\x00\x01',
        'AM': b'\x02\x01',
        'CW': b'\x03\x01',
        'CWN': b'\x03\x02',
        'RTTY': b'\x04\x01',
        'WFM': b'\x06\x01'
    }

    MODE_FOR_BYTES = {v: k for k, v in BYTES_FOR_MODE.items()}

    def __init__(self, radio_addr, serial_port):
        self.radio_addr = radio_addr
        self.comp_addr = b'\xE0'
        self.s = serial.Serial(port=serial_port, baudrate=19200,
                               timeout=1, writeTimeout=1)
        print('acquired serial port')

    def flush(self):
        self.s.flushInput()

    def cmd(self, cmd_bytes, payload=b'', is_read_cmd=False):
        validate = b'\xFE\xFE' + self.comp_addr + self.radio_addr
        if is_read_cmd:
            validate += cmd_bytes

        to_send = b'\xFE\xFE' + self.radio_addr + self.comp_addr + cmd_bytes + payload + b'\xFD'

        receiving = False
        response = b''
        last_n_recvd = b'\x00' * len(validate)

        self.flush()
        self.s.write(to_send)

        t0 = time.time()

        while (time.time() - t0) < 1.0:
            b = self.s.read(1)
            if len(b) == 0:
                time.sleep(0.005)
            elif not receiving:
                last_n_recvd = last_n_recvd[1:] + b
                if validate == last_n_recvd:
                    receiving = True
            else:
                if b != b'\xFD':
                    response += b
                else:
                    if response == b'\xFA':
                        raise CivError(response)
                    if is_read_cmd:
                        return response
                    if response != b'\xFB':
                        raise CivError('Unexpected radio response ' + str(response))
                    return response
        print('Radio command timed out')
        raise ComError('Radio is probably off')

    def set_agc(self, speed):
        if speed == 'Fast':
            b = b'\x01'
        elif speed == 'Slow':
            b = b'\x02'
        else:
            raise BadInputError('AGC speed must be "Fast" or "Slow"')
        self.cmd(b'\x16\x12', b)

    def read_agc(self):
        resp = self.cmd(b'\x16\x12', is_read_cmd=True)
        if resp == b'\x01':
            return 'Fast'
        elif resp == b'\x02':
            return 'Slow'
        raise CivError('Unexpected response to AGC read: ' + str(resp))

    def set_freq(self, freq):
        freq = round(freq)
        if freq < 0 or freq > 9999999999:
            raise BadInputError('Freq out of range')
        payload = b''
        for n in range(5):
            digits = (freq // (100**n)) % 100
            bcd = (((digits // 10) % 10) << 4) | (digits % 10)
            payload += bytes([bcd])
        self.cmd([0x05], payload)

    def read_freq(self):
        resp = self.cmd([0x03], is_read_cmd=True)
        f = 0
        for n in range(5):
            f += (((resp[n] >> 4) & 0xF) * 10 + (resp[n] & 0xF)) * 100**n
        return f

    def set_mem(self, mem_ch):
        mem_ch = round(mem_ch)
        if mem_ch < 2 or mem_ch > 99:
            raise BadInputError('Mem ch out of range: ' + str(mem_ch))
        bcd = (((mem_ch // 10) % 10) << 4) | (mem_ch % 10)
        self.cmd(b'\x08')
        self.cmd(b'\x08', bytes([bcd]))

    def read_meter(self):
        resp = self.cmd(b'\x15\x02', is_read_cmd=True)
        return ((resp[0] & 0xF) * 100) + ((resp[1] >> 4) & 0xF) * 10 + (resp[1] & 0xF)

    def set_mode(self, m):
        m = m.upper()
        if m not in self.BYTES_FOR_MODE:
            raise BadInputError('No such mode')
        self.cmd(b'\x06', self.BYTES_FOR_MODE[m])

    def read_mode(self):
        resp = self.cmd(b'\x04', is_read_cmd=True)
        return self.MODE_FOR_BYTES[resp]

    def set_patt(self, patt):
        if patt == 'Pre':
            self.cmd(b'\x16\x02', b'\x01')
        elif patt == 'Att':
            self.cmd(b'\x11', b'\x20')
        elif patt == 'Off':
            self.cmd(b'\x16\x02', b'\x00')
            self.cmd(b'\x11', b'\x00')
        else:
            raise BadInputError('PAtt must be "Pre", "Att" or "Off"')

    def read_patt(self):
        if self.cmd(b'\x16\x02', is_read_cmd=True) == b'\x01':
            return 'Pre'
        if self.cmd(b'\x11', is_read_cmd=True) == b'\x20':
            return 'Att'
        return 'Off'

    def set_scan(self, scan):
        self.cmd(b'\x0E', b'\x01' if scan else b'\x00')

    def set_vfo(self, vfo):
        if vfo == 'Mem':
            self.cmd(b'\x08')
        else:
            vfo_bytes = {'A': b'\x00', 'B': b'\x01'}
            if vfo not in vfo_bytes.keys():
                raise BadInputError('VFO must be "A", "B" or "Mem"')
            self.cmd(b'\x07', vfo_bytes[vfo])
