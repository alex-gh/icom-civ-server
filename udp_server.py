import socket
import icomradio
import threading
import time

valid_cmds = frozenset(['scan_start', 'scan_stop', 'set_mode', 'set_freq', 'set_patt', 'set_agc'])
SERVER_IP = '192.168.1.146'
REMOTE_IP = None
CMD_PORT = 50007
MET_PORT = 50008
SERVER_SLEEP = b'\x7E'
CLIENT_DETACHING = b'\x10'
radio_lock = threading.Lock()
radio = icomradio.IcomRadio(0x58, '/dev/ttyO2')

class meter_thread(threading.Thread):
    def run(self):
        watchdog_cnt = -1
        sock_met = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_met.bind((SERVER_IP, MET_PORT))
        global REMOTE_IP
        sock_met.settimeout(.1)
        while 1:
            if watchdog_cnt >= 0:
                try:
                    if sock_met.recv(128) == CLIENT_DETACHING:
                        watchdog_cnt = 0
                except socket.timeout:
                    pass
                radio_lock.acquire()
                reading = bytes(radio.read_meter(), 'ascii')
                radio_lock.release()
                try:
                    sock_met.sendto(reading, (REMOTE_IP, MET_PORT))
                except:
                    pass
                watchdog_cnt = watchdog_cnt - 1
            elif watchdog_cnt < 0:
                try:
                    if len(REMOTE_IP) > 0:
                        sock_met.sendto(SERVER_SLEEP, (REMOTE_IP, MET_PORT))
                except:
                    pass
                sock_met.settimeout(None)
                kick = sock_met.recv(128).decode('ascii')
                REMOTE_IP = None
                print('dog kicked')
                if kick[0:10] == '192.168.1.':
                    watchdog_cnt = 30
                    REMOTE_IP = kick[0:13]
                sock_met.settimeout(.1)


class cmd_thread(threading.Thread):
    def run(self):
        sock_cmd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_cmd.bind((SERVER_IP, CMD_PORT))
        # global REMOTE_IP
        while 1:
            cmd = sock_cmd.recv(128).decode('ascii')
            print(cmd)
            cmd = cmd.split()
            if cmd[0] in valid_cmds:
                print('cmd is valid')
                methodToCall = getattr(radio, cmd[0])
                radio_lock.acquire()
                if len(cmd) == 1:
                    response = methodToCall()
                else:
                    response = methodToCall(cmd[1])
                radio_lock.release()
                while REMOTE_IP == None:
                    print('no ip')
                    time.sleep(.02)
                try:
                    sock_cmd.sendto(bytes(response + '\n', 'ascii'), (REMOTE_IP, CMD_PORT))
                except:
                    pass


if __name__ == '__main__':
    met_thd = meter_thread()
    cmd_thd = cmd_thread()
    met_thd.start()
    cmd_thd.start()

