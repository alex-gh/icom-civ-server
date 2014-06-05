from icomradio import IcomRadio
import socket
import threading
import time
import ossaudiodev
import json

SERVER_IP = '192.168.1.146'
CMD_PORT = 50010
AUDIO_PORT = 50009

radio_lock = threading.Lock()
socket_lock = threading.Lock()
client_present = False

radio = IcomRadio(0x58, '/dev/ttyO2')


class meter_thread(threading.Thread):
    def __init__(self, conn, remote_ip):
        threading.Thread.__init__(self)
        self.remote_ip = remote_ip
        self.conn = conn

    def run(self):
        while 1:
            if not client_present:
                return
            radio_lock.acquire()
            reading = radio.read_meter()
            tosend = json.dumps({"cmd" : "read_meter", "response" : reading}) + '\n'
            radio_lock.release()
            socket_lock.acquire()
            try:
                self.conn.send(bytes(tosend, 'ascii'))
            except:
                pass
            socket_lock.release()
            time.sleep(0.1)


class audio_thread(threading.Thread):
    def __init__(self, remote_ip):
        threading.Thread.__init__(self)
        self.remote_ip = remote_ip
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.mixer = ossaudiodev.openmixer('/dev/mixer1')
        self.mixer.set(ossaudiodev.SOUND_MIXER_MIC, (1,1))
        print('set up mixer')
    
        print('{0:08b}'.format(self.mixer.stereocontrols()))
        print('{0:08b}'.format(self.mixer.reccontrols()))
   
        self.dsp = ossaudiodev.open('/dev/dsp1', 'r')
        self.dsp.setfmt(ossaudiodev.AFMT_S16_LE)
        self.dsp.channels(1)
        self.dsp.speed(44100)
        print('set up audio device file') 
    
    def run(self):
        while True:
            if not client_present:
                return
            in_samples = self.dsp.read(1024)
            self.sock.sendto(in_samples, (self.remote_ip, AUDIO_PORT))


def cmd_radio(cmd):
    if cmd['cmd'] in IcomRadio.valid_cmds:
        methodToCall = getattr(radio, cmd['cmd'])
        radio_lock.acquire()
        if not cmd['arg']:
            ret = methodToCall()
        else:
            ret = methodToCall(cmd['arg'])
        radio_lock.release()
        return json.dumps({'cmd': cmd['cmd'], 'response': ret, 'arg': cmd['arg']})
    else:
        cmd['response'] = False;
        return cmd;

def connection(conn):
    global client_present
    client_present = True
    closed = False

    remote_ip = ''
    c = conn.recv(1).decode('ascii')
    while c != '\n':
        remote_ip += c
        c = conn.recv(1).decode('ascii')

    print('remote_ip:', remote_ip)

    meter_thread(conn, remote_ip).start()
    audio_thread(remote_ip).start()

    while 1:
        rcv = ''
        while len(rcv.split('\n')) < 2:
            chunk = conn.recv(1024)
            if not chunk:
                closed = True
                break
            rcv += chunk.decode('ascii')

        if not closed:
            token = rcv.split('\n')
            rcv = rcv[len(token[0]):]
            cmd = json.loads(token[0])
            print('recieved:', cmd)
            reply = cmd_radio(cmd)
            socket_lock.acquire()
            conn.send(bytes(reply + '\n', 'ascii'))
            socket_lock.release()
        else:
            print('client closing\n')
            client_present = False
            return

if __name__ == '__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((SERVER_IP, CMD_PORT))
    sock.listen(1)
    while 1:
        conn, addr = sock.accept()
        connection(conn)
        conn.close()
