import os
import shutil

from flask import send_file
from flask_socketio import SocketIO
import time
import json
from flask import Flask, request
from flask_cors import CORS
from hmm_handler import HMMHandler
import pickle
import socket
import sys
import eventlet
from eventlet import tpool
# from generator import Generator

UDP_IP = "127.0.0.1"
UDP_PORT = 9001

app = Flask(__name__, static_url_path='', static_folder=os.path.abspath('../static'))
CORS(app)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode="eventlet")
socketio.init_app(app, cors_allowed_origins="*")
thread = None
# generator = Generator()

cache = {}

@socketio.on('message')
def handle_message(message):
    print('received message: ' + message)


@socketio.on('connect')
def handle_connect():
    sid = request.sid
    cache[sid] = {'keyup_notes': [], 'keydown_notes': [], 'hmm_handler': HMMHandler(), 'hmm_list': []}
    update_hmm_list(sid)
    socketio.emit('setHmmList', cache[sid]['hmm_list'], room=sid)


@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    cache.pop(sid)
    # path = 'pickle/' + sid + '/'
    # if os.path.exists(path):
    #     shutil.rmtree(path)


@socketio.on('saveHMM')
def handle_save(filename):
    sid = request.sid
    ts = time.gmtime()
    hmm_name = filename + time.strftime("%Y%m%d%H%M%S", ts)
    path = 'pickle/'
    # path = 'pickle/' + sid + '/'
    # os.mkdir(path)
    fn = path + hmm_name + '.pkl'
    with open(fn, "wb") as file:
        pickle.dump(cache[sid]['hmm_handler'], file)
        file.close()
    update_hmm_list(sid)
    socketio.emit('updateHmmList', hmm_name, room=sid)


@socketio.on('changeHMM')
def handle_change(filename):
    sid = request.sid
    if filename != 'new':
        # with open('pickle/' + sid + '/' + filename + ".pkl", "rb") as file:
        with open('pickle/' + filename + ".pkl", "rb") as file:
            cache[sid]['hmm_handler'] = pickle.load(file)
            file.close()
            global thread
            if cache[sid]['hmm_handler'].triggering == 'beat-based':
                thread = socketio.start_background_task(background_thread, sid)
    else:
        cache[sid]['hmm_handler'] = HMMHandler()
    hmm_handler = cache[sid]['hmm_handler']
    ui_config = {
        'init': hmm_handler.init_type,
        'note': hmm_handler.note_type,
        'time': hmm_handler.time_type,
        'quantisation': hmm_handler.quantisation,
        'layout': hmm_handler.layout,
        'pretrain': 'yes' if hmm_handler.pretrain else 'no',
        'files': hmm_handler.files,
        'retrain': 'yes' if hmm_handler.train else 'no',
        'diy': 'diy' if hmm_handler.train_diy else 'normal',
        'train-rate': hmm_handler.train_rate,
        'sample-rate': hmm_handler.sample_rate,
        'nr-samples': hmm_handler.nr_samples,
        'window-size': hmm_handler.window_size,
        'weighting': hmm_handler.weighting,
        'triggering': hmm_handler.triggering
    }
    socketio.emit('uiConfig', ui_config, room=sid)


@socketio.on('updateHMM')
def handle_update(json_string):
    sid = request.sid
    json_object = json.loads(json_string)
    hmm_handler = cache[sid]['hmm_handler']
    hmm_handler.train_vector = []
    hmm_handler.obs_vector = []
    hmm_handler.train = True if json_object['retrain'] == 'yes' else False
    hmm_handler.sample_rate = int(json_object['sample-rate'])
    hmm_handler.nr_samples = int(json_object['nr-samples'])
    hmm_handler.window_size = int(json_object['window-size'])
    hmm_handler.train_diy = True if json_object['diy'] == 'diy' else False
    hmm_handler.train_rate = int(json_object['train-rate'])
    hmm_handler.weighting = int(json_object['weighting'])
    hmm_handler.triggering = json_object['triggering']
    global thread
    if hmm_handler.triggering == 'beat-based':
        thread = socketio.start_background_task(background_thread, sid)
    cache[sid]['hmm_handler'] = hmm_handler


@socketio.on('submit')
def handle_submit(json_string):
    sid = request.sid
    json_object = json.loads(json_string)
    init_type = json_object['init']
    note_type = json_object['note']
    time_type = json_object['time']
    layout = json_object['layout']
    retrain = True if json_object['retrain'] == 'yes' else False
    sample_rate = int(json_object['sample-rate'])
    nr_samples = int(json_object['nr-samples'])
    window_size = int(json_object['window-size'])
    quantisation = int(json_object['quantisation'])
    train_diy = True if json_object['diy'] == 'diy' else False
    train_rate = int(json_object['train-rate'])
    weighting = int(json_object['weighting'])
    files = json_object['files']
    pretrain = True if json_object['pretrain'] == 'yes' else False
    triggering = json_object['triggering']
    cache[sid]['hmm_handler'] = HMMHandler(retrain, sample_rate, nr_samples, window_size, quantisation, layout,
                                                   train_diy, train_rate, files, init_type, pretrain, weighting, note_type, time_type, triggering)
    global thread
    if triggering == 'beat-based':
        thread = socketio.start_background_task(background_thread, sid)
    cache[sid]['keyup_notes'].clear()
    cache[sid]['keydown_notes'].clear()


# @socketio.on('savemidi')
# def handle_save(content):
#     print(content)
#     generator.gen(content['filename'], hmm_handler.all_obs)


@socketio.on('keydown')
def handle_keydown(content):
    sid = request.sid
    cache[sid]['keydown_notes'].append([content['note'], time.time(), content['velocity']])
    if cache[sid]['keyup_notes']:
        keyup = cache[sid]['keyup_notes'][-1]
        keydown = cache[sid]['keydown_notes'][-1]
        start_time = keyup[1]
        end_time = keydown[1]
        duration = end_time - start_time
        rest = cache[sid]['hmm_handler'].parser.rest
        generated_sequence = cache[sid]['hmm_handler'].call(rest, duration)
        if generated_sequence:
            socketio.emit('predicted-melody', generated_sequence, room=sid)
        cache[sid]['keyup_notes'].clear()


@socketio.on('keyup')
def handle_keyup(content):
    sid = request.sid
    cache[sid]['keyup_notes'].append([content['note'], time.time()])
    for keydown_note in cache[sid]['keydown_notes']:
        key_start = None
        key_end = None

        # find matching keyup event
        for keyup_note in cache[sid]['keyup_notes']:
            if keydown_note[0] == keyup_note[0] and keyup_note[1] > keydown_note[1]:
                key_start = keydown_note[1]
                key_end = keyup_note[1]
                cache[sid]['keydown_notes'].remove(keydown_note)

        if key_start and key_end:
            note = keydown_note[0]
            duration = key_end - key_start
            velocity = keydown_note[2]
            generated_sequence = cache[sid]['hmm_handler'].call(note, duration, velocity)
            if generated_sequence:
                socketio.emit('predicted-melody', generated_sequence, room=sid)


def background_thread(sid):
    print('start thread')
    sock = socket.socket(socket.AF_INET,  # Internet
                         socket.SOCK_DGRAM)  # UDP
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(False)
    print(cache[sid]['hmm_handler'].triggering)
    while cache[sid]['hmm_handler'].triggering == 'beat-based':
        try:
            data = sock.recv(2)  # buffer size is 1024 bytes
            print(data)
            generated_sequence = cache[sid]['hmm_handler'].call_beat()
            if generated_sequence:
                socketio.emit('predicted-melody', generated_sequence, room=sid)

            socketio.sleep(0)
        except socket.error as e:
            err = e.args[0]
            if err == 35:
                socketio.sleep(1)
                # print('No data available')
                continue
            else:
                # a "real" error occurred
                print(e)
                sys.exit(1)


@app.route('/', methods=['GET', 'POST'])
def index():
    return send_file('../static/index.html')


def update_hmm_list(sid):
    cache[sid]['hmm_list'] = []
    # for filename in os.listdir('pickle/' + sid + '/'):
    for filename in os.listdir('pickle/'):
        cache[sid]['hmm_list'].append(os.path.splitext(filename)[0])


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080)
