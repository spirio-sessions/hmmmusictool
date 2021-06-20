import os
from flask import send_file
from flask_socketio import SocketIO
import time
import json
from flask import Flask
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
# socketio = SocketIO(app, async_handlers=False)
socketio.init_app(app, cors_allowed_origins="*")
hmm_handler = HMMHandler()
thread = None
# thread_lock = Lock()
# generator = Generator()

cache = {}
cache['keyup_notes'] = []
cache['keydown_notes'] = []
cache['hmm_list'] = []


@socketio.on('message')
def handle_message(message):
    print('received message: ' + message)


@socketio.on('connect')
def handle_connect():
    update_hmm_list()
    socketio.emit('setHmmList', cache['hmm_list'])


@socketio.on('reload')
def handle_reload(message):
    cache['keyup_notes'].clear()
    cache['keydown_notes'].clear()
    hmm_handler.__init__()
    # update_hmm_list()
    # socketio.emit('setHmmList', cache['hmm_list'])
    # global thread
    # # with thread_lock:
    # if thread is None:
    #     thread = socketio.start_background_task(background_thread)
        # thread = tpool.execute(background_thread)
        # thread = Thread(target=background_thread)
        # thread.daemon = True
        # thread.start()
    # else:
    #     print("..background thread is already running")


# @socketio.on('getHmmList')
# def handle_hmmlist(content):
#     # update_hmm_list()
#     socketio.emit('setHmmList', cache['hmm_list'])


@socketio.on('saveHMM')
def handle_save(filename):
    ts = time.gmtime()
    hmm_name = filename + time.strftime("%Y%m%d%H%M%S", ts)
    fn = 'pickle/' + hmm_name + '.pkl'
    with open(fn, "wb") as file:
        pickle.dump(hmm_handler, file)
        file.close()
    update_hmm_list()
    socketio.emit('updateHmmList', hmm_name)


@socketio.on('changeHMM')
def handle_change(filename):
    global hmm_handler
    if filename != 'new':
        with open('pickle/' + filename + ".pkl", "rb") as file:
            hmm_handler = pickle.load(file)
            file.close()
    else:
        hmm_handler.__init__()
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
        'weighting': hmm_handler.weighting
    }
    socketio.emit('uiConfig', ui_config)


@socketio.on('updateHMM')
def handle_update(json_string):
    json_object = json.loads(json_string)
    hmm_handler.train_vector = []
    hmm_handler.obs_vector = []
    hmm_handler.train = True if json_object['retrain'] == 'yes' else False
    hmm_handler.sample_rate = int(json_object['sample-rate'])
    hmm_handler.nr_samples = int(json_object['nr-samples'])
    hmm_handler.window_size = int(json_object['window-size'])
    hmm_handler.train_diy = True if json_object['diy'] == 'diy' else False
    hmm_handler.train_rate = int(json_object['train-rate'])
    hmm_handler.weighting = int(json_object['weighting'])


@socketio.on('submit')
def handle_submit(json_string):
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
    hmm_handler.__init__(retrain, sample_rate, nr_samples, window_size, quantisation, layout, train_diy, train_rate,
                         files, init_type, pretrain, weighting, note_type, time_type, triggering)
    global thread
    if triggering == 'beat-based':
        thread = socketio.start_background_task(background_thread)
    cache['keyup_notes'].clear()
    cache['keydown_notes'].clear()


# @socketio.on('savemidi')
# def handle_save(content):
#     print(content)
#     generator.gen(content['filename'], hmm_handler.all_obs)


@socketio.on('keydown')
def handle_keydown(content):
    cache['keydown_notes'].append([content['note'], time.time(), content['velocity']])
    # print("DOWN")
    # print(cache)
    if cache['keyup_notes']:
        keyup = cache['keyup_notes'][-1]
        keydown = cache['keydown_notes'][-1]
        start_time = keyup[1]
        end_time = keydown[1]
        duration = end_time - start_time
        rest = hmm_handler.parser.rest
        generated_sequence = hmm_handler.call(rest, duration)
        if generated_sequence:
            socketio.emit('predicted-melody', generated_sequence)
        cache['keyup_notes'].clear()
            # cache['last_melody_generation'] = time.time()


@socketio.on('keyup')
def handle_keyup(content):
    cache['keyup_notes'].append([content['note'], time.time()])
    # print(cache['keydown_notes'][:1][0][1])
    # print("UP")
    # print(cache)
    for keydown_note in cache['keydown_notes']:
        key_start = None
        key_end = None

        # find matching keyup event
        for keyup_note in cache['keyup_notes']:
            if keydown_note[0] == keyup_note[0] and keyup_note[1] > keydown_note[1]:
                key_start = keydown_note[1]
                key_end = keyup_note[1]
                cache['keydown_notes'].remove(keydown_note)
                # cache['keyup_notes'].remove(keyup_note)

        if key_start and key_end:
            note = keydown_note[0]
            duration = key_end - key_start
            velocity = keydown_note[2]
            generated_sequence = hmm_handler.call(note, duration, velocity)
            if generated_sequence:
                socketio.emit('predicted-melody', generated_sequence)

    # keyup = cache['keyup_notes'][-1]
    # keydown = cache['keydown_notes'][-1]
    # note = keyup[0]
    # end_time = keyup[1]
    # start_time = keydown[1]
    # duration = end_time - start_time
    # velocity = keydown[2]
    # # midi_instrument.notes.append(note)
    # generated_sequence = hmm_handler.call(note, duration, velocity)
    # if generated_sequence:
    #     socketio.emit('predicted-melody', generated_sequence)
        # cache['last_melody_generation'] = time.time()

    # for idx, val in enumerate(cache['keyup_notes']):
    #     note = val[0]
    #     end_time = val[1]
    #     start_time = cache['keydown_notes'][idx][1]
    #     duration = end_time - start_time
    #     # midi_instrument.notes.append(note)
    #     print(note, duration)
    #     generated_sequence = hmm_handler.call(note, duration)
    #     if generated_sequence:
    #         socketio.emit('predicted-melody', generated_sequence)
    #         cache['last_melody_generation'] = time.time()
    # cache['keyup_notes'].clear()
    # cache['keydown_notes'].clear()

    # if len(cache['keyup_notes']) > NUMBER_OF_NOTES:
    #     # create prediction and send back
    #
    #     if time.time() > cache['last_melody_generation'] + MELODY_GENERATE_DURATION:
    #         midi_data = pretty_midi.PrettyMIDI()
    #         midi_instrument = pretty_midi.Instrument(program=0)
    #
    #         sequence_start_time = cache['keydown_notes'][:1][0][1]
    #
    #         for keydown_note in cache['keydown_notes']:
    #             key_start = None
    #             key_end = None
    #
    #             # find matching keyup event
    #             for keyup_note in cache['keyup_notes']:
    #                 if keydown_note[0] == keyup_note[0] and keyup_note[1] > keydown_note[1]:
    #                     key_start = keydown_note[1] - sequence_start_time
    #                     key_end = keyup_note[1] - sequence_start_time
    #
    #             if key_start and key_end:
    #                 note = pretty_midi.Note(velocity=127, pitch=keydown_note[0], start=key_start, end=key_end)
    #                 midi_instrument.notes.append(note)
    #
    #         midi_data.instruments.append(midi_instrument)
    #
    #         time_end = float(cache['keyup_notes'][-1:][0][1])
    #         time_start = float(cache['keydown_notes'][:1][0][1])
    #         duration = time_end - time_start
    #
    #         #ret_sequence_melody = generate_sequence(midi_data, duration + 0.4) # duration*2
    #         #json_sequence_melody = sequence_to_json(ret_sequence_melody)
    #         json_sequence_melody = hmm_handler.sample()
    #         print(json_sequence_melody)
    #         socketio.emit('predicted-melody', json_sequence_melody)
    #         cache['last_melody_generation'] = time.time()
    #
    #     # cut to number of notes
    #     cache['keyup_notes'] = cache['keyup_notes'][-NUMBER_OF_NOTES:]
    #     cache['keydown_notes'] = cache['keydown_notes'][-NUMBER_OF_NOTES:]


def background_thread():
    print('start thread')
    sock = socket.socket(socket.AF_INET,  # Internet
                         socket.SOCK_DGRAM)  # UDP
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(False)
    while hmm_handler.triggering == 'beat-based':
        try:
            data = sock.recv(2)  # buffer size is 1024 bytes
            print(data)
            # thread_lock.acquire(False)
            generated_sequence = hmm_handler.call_beat()
            if generated_sequence:
                socketio.emit('predicted-melody', generated_sequence)
            # thread_lock.release()
            # eventlet.sleep(0.1)
            # time.sleep(1)
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
    # socketio.sleep(0.1)


@app.route('/', methods=['GET', 'POST'])
def index():
    return send_file('../static/index.html')


@app.before_first_request
def _run_on_start():
    print("STARTUP LOAD")


def update_hmm_list():
    cache['hmm_list'] = []
    for filename in os.listdir('pickle/'):
        cache['hmm_list'].append(os.path.splitext(filename)[0])


if __name__ == '__main__':
    # thread = Thread(target=background_thread)
    # thread.daemon = True
    # thread.start()
    # socketio.start_background_task(target=background_thread)
    socketio.run(app, host='0.0.0.0', port=8080)
