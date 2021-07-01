## HMM Music

A piano that responds to you.

## OVERVIEW

HMM Music is composed of two parts, the front-end which is in the `static` folder and the back-end which is in the `server` folder. 
The front-end client establishes a connection via Socket.IO and sends key events to a [Flask](http://flask.pocoo.org/) server. The server takes that input and "continues" if enough notes were played it using an HMM which is then returned back to the client. 

## INSTALLATION

If you already have a Python environment setup, install all of the server dependencies and start the server by typing the following in the terminal:

```bash
cd server
pip install -r requirements.txt
```

If it _did_ install tensorflow and magenta successfully, you can run the server by typing:

```bash
python server.py
```

Then to build and install the front-end JavaScript code, first make sure you have [Node.js](https://nodejs.org) installed. And then install of the dependencies of the project and build the code by typing the following in the terminal: 

```bash
cd static
npm install
npm run build
```

You can now play with A.I. Duet at [localhost:8080](http://localhost:8080).

## Docker
```bash
$ docker build -t ai-duet .
$ docker run -t -p 8080:8080 ai-duet
```

## MIDI SUPPORT

The A.I. Duet supports MIDI keyboard input using [Web Midi API](https://webaudio.github.io/web-midi-api/) and the [WebMIDI](https://github.com/cotejp/webmidi) library. 

For the output the first available MIDIOutput is taken, for the input the second MIDIInput is taken to avoid a loop.

Output is sent on all channels, same for the Input channels.

## PIANO KEYBOARD

The piano can also be controlled from your computer keyboard thanks to [Audiokeys](https://github.com/kylestetz/AudioKeys). The center row of the keyboard is the white keys.
