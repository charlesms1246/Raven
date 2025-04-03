from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit
import base64
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return 'WebSocket Image Server Running'

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    send_image()

def send_image():
    image_path = os.path.join('static', 'images', 'police.png')
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        emit('image_data', {'image': encoded_string})
        print("Image sent!")

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
