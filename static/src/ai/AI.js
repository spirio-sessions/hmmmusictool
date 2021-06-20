import Tone from 'Tone/core/Tone'
import MidiConvert from 'midiconvert'
import events from 'events'
import io from 'socket.io-client'

class AI extends events.EventEmitter {

    constructor(container) {
        super()

        this._socket = null;
        this._newTrack()
        this._sendTimeout = -1
        this._heldNotes = {}
        this._lastPhrase = -1
        this._aiEndTime = 0

        if (USE_WEBSOCKETS) {
            this._connectToServer()
            this._setupPrediction()
        }

        this._createSaveTracks()

        // save midi
        const saveMidiButton = document.createElement('a')
        saveMidiButton.id = 'saveMidi'
        saveMidiButton.innerHTML = 'Save MIDI'
        container.appendChild(saveMidiButton)

        saveMidiButton.addEventListener('click', () => {
            this.emit('saveMidi')
        })
    }

    _connectToServer() {
        this._socket = io(WEBSOCKETS_API);
        /*this._socket = io(WEBSOCKETS_API, {
            path: "/spiriosessions-hmm/socket.io"
        });*/
        this._socket.on('connect', function () {
            console.log('CONNECTED');
        });
    }

    _setupPrediction() {
        this._socket.on('predicted-melody', args => this.play(args));
        this._socket.on('predicted-drums', args => this.play(args));
        this._socket.on('setHmmList', args => this.emit('setHmmList', args));
        this._socket.on('updateHmmList', args => this.emit('updateHmmList', args));
        this._socket.on('uiConfig', args => this.emit('uiConfig', args));
        this._socket.on('msg', args => console.log(args));
    }

    _newTrack() {
        this._midi = new MidiConvert.create()
        this._track = this._midi.track()
        this._drumTrack = this._midi.track()
    }

    _createSaveTracks() {
        this._saveMidi = new MidiConvert.create()

        this._savePlayerTrack = this._saveMidi.track()
        this._savePlayerTrack.channel = 16
        this._savePlayerTrack.name = 'Player'

        this._saveAiTrack9 = this._saveMidi.track()
        this._saveAiTrack9.channel = 9
        this._saveAiTrack9.name = 'Drums'
        this._saveAiTrack9.instrumentNumber = 9
        this._saveAiTrack9.isPercussion = true

        this._saveAiTrack1 = this._saveMidi.track()
        this._saveAiTrack1.channel = 1
        this._saveAiTrack1.name = 'AI 1'

        this._saveAiTrack0 = this._saveMidi.track()
        this._saveAiTrack0.channel = 0
        this._saveAiTrack0.name = 'AI 0'
    }

    _updateSaveTracks(type, instrument, note, time, velocity) {
        switch (instrument) {
            case 9:
                type === 'On' ? this._saveAiTrack9.noteOn(note, time, velocity) :
                                this._saveAiTrack9.noteOff(note, time, velocity)
                break
            case 1:
                type === 'On' ? this._saveAiTrack1.noteOn(note, time, velocity) :
                                    this._saveAiTrack1.noteOff(note, time, velocity)
                break
            case 0:
                type === 'On' ? this._saveAiTrack0.noteOn(note, time, velocity) :
                                this._saveAiTrack0.noteOff(note, time, velocity)
                break
            default:
                type === 'On' ? this._savePlayerTrack.noteOn(note, time, velocity) :
                                this._savePlayerTrack.noteOff(note, time, velocity)
        }
    }

    saveMidi() {
        const blob = new Blob([Uint8Array.from(this._saveMidi.toArray()).buffer], {type: 'application/octet-stream'})
        const url = window.URL.createObjectURL(blob);
        const anchor = document.createElement('a')
        const now = new Date()
        anchor.download = `${now.toISOString()}-ai-duet.mid`
        anchor.href = url
        anchor.click()
        anchor.remove()
    }

    play(notes) {
        for (const note of notes) {
            const now = Tone.now() + 0.05
            if (note.start_time + now > this._aiEndTime) {
                this._aiEndTime = note.start_time + now
                this.emit('keyDown', note.pitch, note.start_time + now, note.instrument, note.velocity)
                let duration = note.end_time - note.start_time;
                duration = duration * 0.9
                duration = Math.min(note.duration, 4)
                this.emit('keyUp', note.pitch, note.end_time + now, note.instrument)

                this._updateSaveTracks('On', note.instrument, note.pitch, note.start_time + now, note.velocity)
                this._updateSaveTracks('Off', note.instrument, note.pitch, note.end_time + now, note.velocity)
            }
        }
    }

    sendUI(message, json) {
        console.log(message)
        this._socket.emit(message, json);
    }

    send() {
        //trim the track to the first note
        if (this._track.length) {
            let request = this._midi.slice(this._midi.startTime)
            this._newTrack()
            let endTime = request.duration
            //shorten the request if it's too long
            /*
            if (endTime > 10) {
                request = request.slice(request.duration - 15)
                endTime = request.duration
            }
            */
            let additional = endTime
            additional = Math.min(additional, 8)
            additional = Math.max(additional, 1)

            fetch(`${REST_API}/vae-genre?duration=${endTime + additional}`, {
                method: "POST",
                body: JSON.stringify(request.toArray())
            }).then(response => response.json())
                .then(data => {
                    const now = Tone.now() + 0.05
                    for (const note of data) {
                        if ([0, 1, 9].includes(note.instrument)) {
                            const noteStartTime = note.start_time + now
                            const noteEndTime = note.end_time + now
                            this._aiEndTime = noteStartTime
                            this.emit('keyDown', note.pitch, noteStartTime, note.instrument, note.velocity)
                            this.emit('keyUp', note.pitch, noteEndTime, note.instrument, note.velocity)

                            this._updateSaveTracks('On', note.instrument, note.pitch, noteStartTime, note.velocity)
                            this._updateSaveTracks('Off', note.instrument, note.pitch, noteEndTime, note.velocity)
                        }
                    }
                });

            this._lastPhrase = -1
            this.emit('sent')
        }
    }

    keyDown(note, time = Tone.now(), instrument = 16, endTime = Tone.now(), velocity = 100) {
        if (USE_WEBSOCKETS) {
            this._socket.emit('keydown', {note: note, instrument: instrument, velocity: velocity});
        }
        this._updateSaveTracks('On', instrument, note, time, velocity)

        if (this._track.length === 0 && this._lastPhrase === -1) {
            this._lastPhrase = Date.now()
        }
        this._track.noteOn(note, time)
        clearTimeout(this._sendTimeout)

        this._heldNotes[note] = true
    }

    keyUp(note, time = Tone.now(), instrument = 16, endTime = Tone.now(), velocity = 100) {
        if (USE_WEBSOCKETS) {
            this._socket.emit('keyup', {note: note, instrument: instrument});
        }

        this._updateSaveTracks('Off', instrument, note, time, velocity)

        this._track.noteOff(note, time)
        delete this._heldNotes[note]


        // send something if there are no events for a moment
        // TODO: export as config
        if (!USE_WEBSOCKETS) {
            if (Object.keys(this._heldNotes).length === 0) {
                if (this._lastPhrase !== -1 && Date.now() - this._lastPhrase > 6000) {
                    //just send it
                    this.send()
                } else {
                    // this._sendTimeout = setTimeout(this.send.bind(this), 600 + (time - Tone.now()) * 1000)
                }
            }
        }
    }

    handleServerRequest() {
        if (Object.keys(this._heldNotes).length === 0) {
            if (this._lastPhrase !== -1 && Date.now() - this._lastPhrase > 6000) {
                //just send it
                this.send()
            } else {
                this._sendTimeout = setTimeout(this.send.bind(this), 600 + (time - Tone.now()) * 1000)
            }
        }
    }
}

export {AI}
