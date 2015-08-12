import http.server
import json
from icomradio import IcomRadio

radio = IcomRadio(0x58, '/dev/ttyO2')

class RadioRequestHandler(http.server.BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET') 
        self.end_headers()

    def do_GET(self):
        path = self.path.split('/')
        print(path)
        cmd = path[1] if len(path) > 1 else None
        response = None
        
        if cmd == None:
            pass
        elif cmd == 'read_meter':
            response = radio.read_meter()
        elif cmd == 'scan_start':
            response = radio.scan_start()
        elif cmd == 'scan_stop':
            response = radio.scan_stop()
        elif cmd == 'read_freq':
            response = radio.read_freq()
        elif cmd == 'read_mode':
            response = radio.read_mode()
        elif len(path) > 2:
            arg = path[2]
            if cmd == 'set_scan':
                response = radio.set_scan(arg)
            elif cmd == 'set_freq':
                response = radio.set_freq(arg)
            elif cmd == 'set_vfo':
                response = radio.set_vfo(arg)
            elif cmd == 'set_mem':
                response = radio.set_mem(arg)
            elif cmd == 'set_agc':
                response = radio.set_agc(arg)
            elif cmd == 'set_patt':
                response = radio.set_patt(arg)
            elif cmd == 'set_mode':
                response = radio.set_mode(arg)
        
        if response == None:
            self.send_response(404)
            response = {'success': False, 'error': 'WrongCommand'}
        elif not response['success']:
            self.send_response(500, response.get('error', 'Unknown error'))
        else:
            self.send_response(200)
        
       	self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        responseBytes = bytes(json.dumps(response), 'UTF-8')
       	self.wfile.write(responseBytes)

if __name__ == "__main__":
    PORT = 8925
    httpd = http.server.HTTPServer(("", PORT), RadioRequestHandler)
    print("serving at port", PORT)
    httpd.serve_forever()

