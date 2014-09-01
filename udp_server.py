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
        global client_present
        failures = 0
        while client_present:
            radio_lock.acquire()
            response = radio.read_meter()
            radio_lock.release()
            response['cmd'] = 'read_meter'
            response['arg'] = False
            tosend = json.dumps(response) + '\n'
            socket_lock.acquire()
            try:
                self.conn.send(bytes(tosend, 'ascii'))
            except BrokenPipeError:
                socket_lock.release()
                client_present = False
            except:
                socket_lock.release()
                if failures < 5:
                    failures += 1
                else:
                    client_present = False
            else:
                socket_lock.release()
                failures = 0
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
        while client_present:
            in_samples = self.dsp.read(1024)
            try:
                self.sock.sendto(in_samples, (self.remote_ip, AUDIO_PORT))
            except:
                pass
        self.dsp.close()
        self.mixer.close()


def cmd_radio(cmd):
    if cmd['cmd'] in IcomRadio.VALID_CMDS:
        methodToCall = getattr(radio, cmd['cmd'])
        radio_lock.acquire()
        if not cmd['arg']:
            response = methodToCall()
        else:
            response  = methodToCall(cmd['arg'])
        cmd = dict(list(cmd.items()) + list(response.items()))
        radio_lock.release()
    else:
        cmd['response'] = False
        cmd['error'] = 'Unknown command'
    return cmd

def connection(conn):
    global client_present
    client_present = True

    sock_file = conn.makefile()
    
    try:
        remote_ip = sock_file.readline()
    except:
        client_present = False
        return

    print('remote ip:', remote_ip)

    met_thd = meter_thread(conn, remote_ip)
    met_thd.start()

    audio_thd = audio_thread(remote_ip)
    audio_thd.start()

    conn.settimeout(0.5)
    rcv = ''
    while client_present:
        while client_present and len(rcv.split('\n')) < 2:
            try:
                chunk = conn.recv(1024)
                rcv += chunk.decode('ascii')
            except:
                pass

        if client_present:
            token = rcv.split('\n')
            rcv = rcv[(len(token[0])+1):]
            cmd = json.loads(token[0])
            print('recieved:', token[0])
            response = cmd_radio(cmd)
            print(response)
            reply = json.dumps(response)
            socket_lock.acquire()
            try:
                conn.send(bytes(reply + '\n', 'ascii'))
            except:
                pass
            socket_lock.release()
    # Cleanup
    met_thd.join()
    audio_thd.join()
    print('client gone\n')

if __name__ == '__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((SERVER_IP, CMD_PORT))
    sock.listen(1)
    while 1:
        conn, addr = sock.accept()
        connection(conn)
        conn.close()
