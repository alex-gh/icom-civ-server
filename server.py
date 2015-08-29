import http.server
import json
import icomradio
from urllib.parse import urlparse
from threading import Lock

vfo_specific_state = frozenset(['freq', 'mode', 'patt'])

radio = icomradio.IcomRadio(b'\x58', '/dev/ttyO2')
radio_lock = Lock()
radio.set_scan(False)

state = {
    'scan': False,
    'agc': radio.read_agc(),
    'meter': radio.read_meter(),
    'mem': 2,
    'vfo_states': {}
    }

for vfo in ['A', 'B', 'Mem']:
    radio.set_vfo(vfo)
    state['vfo'] = vfo
    state['vfo_states'][vfo] = {
        'freq': radio.read_freq(),
        'mode': radio.read_mode(),
        'patt': radio.read_patt(),
        }

mems = {}

for ch in range(2, 25):
    radio.set_mem(ch)
    mems[ch] = radio.read_freq()

mem_ch_for_freq = {mems[ch]: ch for ch in mems}

radio.set_mem(2)

print(state)


def parse_path(path_str):
    return urlparse(path_str).path.strip('/').split('/')


def validate_arg(cmd, arg_str):
    if cmd == 'scan':
        if arg_str == 'True':
            return True
        elif arg_str == 'False':
            return False
        else:
            raise icomradio.BadInputError('Scan must be "True" or "False"')
    elif cmd == 'freq' or cmd == 'mem':
        if not arg_str.isdigit():
            raise icomradio.BadInputError('Freq must be an int')
        return int(arg_str)
    else:
        return arg_str


class NoSuchCmdError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return 'No such command: ' + self.msg


class RadioRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET') 
        self.end_headers()

    def do_POST(self):
        global state
        path = parse_path(self.path)
        print(path)
        response = None
        try:
            if len(path) != 2:
                raise icomradio.BadInputError(path)
            cmd = path[0]
            if cmd not in ['freq', 'mode', 'patt', 'agc', 'mem', 'vfo', 'scan']:
                raise NoSuchCmdError(cmd)
            arg_str = path[1]
            arg = validate_arg(cmd, arg_str)
            cmd_func = getattr(radio, 'set_' + cmd)
            with radio_lock:
                # Command radio
                cmd_func(arg)
                # Update state
                if cmd in vfo_specific_state:
                    state['vfo_states'][state['vfo']][cmd] = arg
                else:
                    state[cmd] = arg
                # Take acct of other state changes caused by command
                if cmd in ['vfo', 'freq', 'mem']:
                    state['scan'] = False
                if cmd == 'vfo' and state['vfo'] == 'Mem':
                    state['vfo_states']['Mem']['mode'] = 'FM'
                if cmd == 'scan' and not state['scan']:
                    state['vfo_states'][state['vfo']]['freq'] = radio.read_freq()
                    if state['vfo'] == 'Mem':
                        state['mem'] = mem_ch_for_freq[state['vfo_states']['Mem']['freq']]
                if cmd == 'mem':
                    state['vfo_states']['Mem']['freq'] = mems[state['mem']]
                response = state
        except NoSuchCmdError as e:
            self.send_response(404, str(e))
        except icomradio.BadInputError as bie:
            self.send_response(400, str(bie))
        except Exception as e:
            self.send_response(500, str(e))
        else:
            self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        if response is not None:
            response_bytes = bytes(json.dumps(response), 'UTF-8')
            self.wfile.write(response_bytes)

    def do_GET(self):
        path = parse_path(self.path)
        print(path)
        response = None
        try:
            if len(path) != 1:
                raise icomradio.BadInputError(path)
            if path[0] == 'state':
                with radio_lock:
                    state['meter'] = radio.read_meter()
                    if state['scan']:
                        freq = radio.read_freq()
                        state['vfo_states'][state['vfo']]['freq'] = freq
                        if state['vfo'] == 'Mem':
                            state['mem'] = mem_ch_for_freq[freq]
                    response = state
            elif path[0] == 'mems':
                response = [[ch, mems[ch]] for ch in mems]
            else:
                raise NoSuchCmdError(path[0])
        except NoSuchCmdError as e:
            self.send_response(404, str(e))
        except icomradio.BadInputError as bie:
            self.send_response(400, str(bie))
        except Exception as e:
            self.send_response(500, str(e))
        else:
            self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        if response is not None:
            response_bytes = bytes(json.dumps(response), 'UTF-8')
            self.wfile.write(response_bytes)


if __name__ == "__main__":
    PORT = 8925
    httpd = http.server.HTTPServer(("", PORT), RadioRequestHandler)
    print("serving at port", PORT)
    httpd.serve_forever()
