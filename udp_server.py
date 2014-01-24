import socket
from icomradio import IcomRadio
import threading
import time
import ossaudiodev

SERVER_IP = '192.168.1.146'
REMOTE_IP = None
CONTROL_PORT = 50006
CMD_PORT = 50007
MET_PORT = 50008
AUDIO_PORT = 50009
SERVER_SLEEP = b'\x7E'
CLIENT_DETACHING = b'\x10'
radio_lock = threading.Lock()
radio = IcomRadio(0x58, '/dev/ttyO2')

client_present = threading.Event()

class control_thread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((SERVER_IP, CONTROL_PORT))
        self.sock.settimeout(.1)
    def run(self):
        global REMOTE_IP
        watchdog_cnt = -1
        while 1:
            if watchdog_cnt >= 0:
                try:
                    if self.sock.recv(128) == b'\x10':
                        watchdog_cnt = 0;
                except socket.timeout:
                    pass
                watchdog_cnt -= 1
            else:
                if REMOTE_IP:
                    try:
                        self.sock.sendto(b'x', (REMOTE_IP, CONTROL_PORT))
                    except:
                        pass
                self.sock.settimeout(None)
                client_present.clear()
                REMOTE_IP = None
                wakeup = self.sock.recv(128).decode('ascii')
                print('dog kicked')
                if wakeup[0:10] == '192.168.1.':
                    watchdog_cnt = 30
                    REMOTE_IP = wakeup[0:13]
                    client_present.set()
                self.sock.settimeout(.1)

class meter_thread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((SERVER_IP, MET_PORT))
        self.sock.settimeout(.1)
    
    def run(self):
        while 1:
            if not client_present.is_set():
                client_present.wait()
                ip = REMOTE_IP
            radio_lock.acquire()
            reading = bytes(radio.read_meter(), 'ascii')
            radio_lock.release()
            try:
               self.sock.sendto(reading, (REMOTE_IP, MET_PORT))
            except:
               pass
            time.sleep(.1)


class cmd_thread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((SERVER_IP, CMD_PORT))

    def run(self):
        while 1:
            cmd = self.sock.recv(128).decode('ascii')
            print(cmd)
            cmd = cmd.split()
            if cmd[0] in IcomRadio.valid_cmds:
                print('cmd is valid')
                methodToCall = getattr(radio, cmd[0])
                radio_lock.acquire()
                if len(cmd) == 1:
                    response = methodToCall()
                else:
                    response = methodToCall(cmd[1])
                radio_lock.release()
                if not client_present.is_set():
                    client_present.wait()
                try:
                    self.sock.sendto(bytes(response + '\n', 'ascii'), (REMOTE_IP, CMD_PORT))
                except:
                    pass

class audio_thread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.mixer = ossaudiodev.openmixer('/dev/mixer1')
        self.mixer.set(ossaudiodev.SOUND_MIXER_MIC, (1,1))
        print('set up mixer')
    
        print('{0:08b}'.format(self.mixer.stereocontrols()))
        print('{0:08b}'.format(self.mixer.reccontrols()))
   
        self.dsp = ossaudiodev.open('/dev/dsp1', 'r')
        self.dsp.setfmt(ossaudiodev.AFMT_S16_LE)
        self.dsp.channels(1)
        self.dsp.speed(22050)
        print('set up audio device file') 
    
    def run(self):
        while True:
            if not client_present.is_set():
                client_present.wait()
                ip = REMOTE_IP
            in_samples = self.dsp.read(1024)
            self.sock.sendto(in_samples, (ip, AUDIO_PORT))

if __name__ == '__main__':
    met_thd = meter_thread()
    cmd_thd = cmd_thread()
    audio_thd = audio_thread()
    cntrl_thd = control_thread()

    met_thd.start()
    cmd_thd.start()
    audio_thd.start()
    cntrl_thd.start()

