import http.server
import json
import icomradio


radio = icomradio.IcomRadio(b'\x58', '/dev/ttyO2')


def run_cmd(cmd, arg=None):
    if arg is None:
        if cmd == 'read_meter':
            return radio.read_meter()
        elif cmd == 'read_freq':
            return radio.read_freq()
        elif cmd == 'read_mode':
            return radio.read_mode()
        elif cmd == 'read_agc':
            return radio.read_agc()
        elif cmd == 'read_patt':
            return radio.read_patt()
        else:
            raise NoSuchCmdError()
    else:
        if cmd == 'set_scan':
            if arg == 'True':
                arg = True
            elif arg == 'False':
                arg = False
            else:
                raise icomradio.BadInputError('Scan must be "True" or "False')
            radio.set_scan(arg)
        elif cmd == 'set_freq':
            arg = int(arg)
            radio.set_freq(arg)
        elif cmd == 'set_vfo':
            radio.set_vfo(arg)
        elif cmd == 'set_mem':
            arg = int(arg)
            radio.set_mem(arg)
        elif cmd == 'set_agc':
            radio.set_agc(arg)
        elif cmd == 'set_patt':
            radio.set_patt(arg)
        elif cmd == 'set_mode':
            radio.set_mode(arg)
        else:
            raise NoSuchCmdError()
        return arg


class NoSuchCmdError(Exception):
    pass


class RadioRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET') 
        self.end_headers()

    def do_GET(self):
        path = self.path.strip('/').split('/')
        print(path)
        response = None
        try:
            cmd = path[0] if len(path) > 0 else None
            if cmd is None:
                raise NoSuchCmdError()
            arg = path[1] if len(path) == 2 else None
            response = run_cmd(cmd, arg)
        except NoSuchCmdError:
            self.send_response(404, 'No such command')
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
            response_bytes = bytes(json.dumps({'data': response}), 'UTF-8')
            self.wfile.write(response_bytes)


if __name__ == "__main__":
    PORT = 8925
    httpd = http.server.HTTPServer(("", PORT), RadioRequestHandler)
    print("serving at port", PORT)
    httpd.serve_forever()
