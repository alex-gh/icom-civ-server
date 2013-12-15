from flask import Flask
from icomradio import IcomRadio

radio = IcomRadio(0x58, '/dev/ttyO2')
app = Flask(__name__)

@app.route('/')
def hello():
    return '706 Remote Server'

@app.route('/set_mem/<n>')
def set_mem(n):
    return radio.set_mem(n)

@app.route('/read_meter')
def read_meter():
    return radio.read_meter()

@app.route('/set_vfo/<s>')
def set_vfo(s):
    return radio.set_vfo(s)

@app.route('/scan_start')
def scan_start():
    return radio.scan_start()

@app.route('/scan_stop')
def scan_stop():
    return radio.scan_stop()

@app.route('/set_agc/<s>')
def set_agc(s):
    return radio.set_agc(s)

@app.route('/set_patt/<s>')
def set_patt(s):
    return radio.set_patt(s)

@app.route('/set_mode/<s>')
def set_mode(s):
    return radio.set_mode(s)

@app.route('/set_freq/<s>')
def set_freq(s):
    return radio.set_freq(s)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8925)

