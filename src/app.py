from flask import Flask, jsonify
import datetime
import socket

app = Flask(__name__)

@app.route('/api/v1/details')
def details():
    return jsonify ({
        'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'hostname': socket.gethostname()
        }), 200

@app.route('/api/v1/health')
def health():
    return jsonify ({ 'status' : 'up' }), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0")