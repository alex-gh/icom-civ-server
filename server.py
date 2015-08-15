import http.server
import json
import icomradio

class NoSuchCmdError(Exception):
    pass

radio = icomradio.IcomRadio(b'\x58', '/dev/ttyO2')
state = {}

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
#        try:
        if len(path) == 1:
            cmd = path[0]
            if cmd == 'read_meter':
                response = radio.read_meter()
            elif cmd == 'read_freq':
                response = radio.read_freq()
            elif cmd == 'read_mode':
                response = radio.read_mode()
            elif cmd == 'read_agc':
                response = radio.read_agc()
            elif cmd == 'read_patt':
                response = radio.read_patt()
            else:
                raise NoSuchCmdError()
        elif len(path) == 2:
            cmd = path[0]
            arg = path[1]
            if cmd == 'set_scan':
                radio.set_scan(arg)
            elif cmd == 'set_freq':
                radio.set_freq(arg)
            elif cmd == 'set_vfo':
                radio.set_vfo(arg)
            elif cmd == 'set_mem':
                radio.set_mem(arg)
            elif cmd == 'set_agc':
                radio.set_agc(arg)
            elif cmd == 'set_patt':
                radio.set_patt(arg)
            elif cmd == 'set_mode':
                radio.set_mode(arg)
            else:
                raise NoSuchCmdError()
            response = int(arg) if arg.isdigit() else arg
        else:
            raise NoSuchCmdError()
        '''
        except NoSuchCmdError:
            self.send_response(404, 'No such command')
        except icomradio.BadInputError as bie:
            self.send_response(400, str(bie))
        except Exception as e:
            self.send_response(500, str(e))
        else:
        ''' 
        self.send_response(200)
       	self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        if response != None:
            responseBytes = bytes(json.dumps({'data' : response}), 'UTF-8')
       	    self.wfile.write(responseBytes)

if __name__ == "__main__":
    PORT = 8925
    httpd = http.server.HTTPServer(("", PORT), RadioRequestHandler)
    print("serving at port", PORT)
    httpd.serve_forever()

