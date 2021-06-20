import events from 'events'
import WebMidi from 'webmidi'
import Tone from "tone/Tone/core/Tone";

class Midi extends events.EventEmitter {
    constructor() {
        super()

        this._isEnabled = false
        this._output = null
        this._input = null

        WebMidi.enable((err) => {
            if (!err) {
                this._isEnabled = true

                console.log('Available in / out:')
                console.log(WebMidi.inputs)
                console.log(WebMidi.outputs)

                WebMidi.addListener('connected', (device) => {
                    if (device.input) {
                        this._bindInput(device.input)
                    }
                })

                if (this._output) {
                    this._output.playNote("E5", "all", {duration: 400})
                    this._output.playNote("B4", "all", {time: "+400", duration: 200})
                    this._output.playNote("C5", "all", {time: "+600", duration: 200})
                    this._output.playNote("D5", "all", {time: "+800", duration: 400})
                    this._output.playNote("C5", "all", {time: "+1200", duration: 200})
                    this._output.playNote("B4", "all", {time: "+1400", duration: 200})
                    this._output.playNote("A4", "all", {time: "+1600", duration: 800})
                }

                const container = document.getElementById('splash')
                container.appendChild(document.createElement('br'))

                const inLabel = document.createElement('span')
                inLabel.id = 'midiInLabel'
                inLabel.textContent = 'Midi IN'
                inLabel.style.padding = '5px 15px'
                container.appendChild(inLabel)
                const midiInSelect = document.createElement('select')
                midiInSelect.id = 'midiInSelect'
                container.appendChild(midiInSelect)
                const midiInputs = WebMidi.inputs;
                for (let i = 0; i < midiInputs.length; i++) {
                    const option = document.createElement("option");
                    option.value = midiInputs[i]._midiInput.id;
                    option.text = midiInputs[i]._midiInput.name;
                    midiInSelect.appendChild(option);
                }
                midiInSelect.addEventListener('change', (event) => {
                    this.updateParameterByName('midi_input_id', midiInSelect.value)
                    this._input = WebMidi.getInputById(this.getParameterByName('midi_input_id'))

                    if (this._input) {
                        this._bindInput(this._input)
                    }
                })
                midiInSelect.selectedIndex = -1


                container.appendChild(document.createElement('br'))
                const outLabel = document.createElement('span')
                outLabel.id = 'midiOutLabel'
                outLabel.textContent = 'Midi OUT'
                outLabel.style.padding = '5px 15px'
                container.appendChild(outLabel)
                const midiOutSelect = document.createElement('select')
                midiOutSelect.id = 'midiOutSelect'
                container.appendChild(midiOutSelect)
                const midiOutputs = WebMidi.outputs;
                for (let i = 0; i < midiOutputs.length; i++) {
                    const option = document.createElement("option");
                    option.value = midiOutputs[i]._midiOutput.id;
                    option.text = midiOutputs[i]._midiOutput.name;
                    midiOutSelect.appendChild(option);
                }
                midiOutSelect.addEventListener('change', (event) => {
                    this.updateParameterByName('midi_output_id', midiOutSelect.value)
                    this._output = WebMidi.getOutputById(this.getParameterByName('midi_output_id'))
                })
                midiOutSelect.selectedIndex = -1
            } else {
                console.log("Could not enable WebMidi")
                console.log(err)
            }
        })
    }

    keyDown(note, time = Tone.now(), instrument = 1, velocity = 100) {
        if (this._isEnabled && this._output) {
            const sendTime = (time - Tone.now()) * 1000
            this._output.playNote(note, Number(instrument), {time: '+' + sendTime.toString(), rawVelocity: true, velocity: velocity})
        }
    }

    keyUp(note, time = Tone.now(), instrument = 1) {
        if (this._isEnabled && this._output) {
            const sendTime = (time - Tone.now()) * 1000
            this._output.stopNote(note, Number(instrument), {time: '+' + sendTime.toString()})
        }
    }

    _bindInput(inputDevice) {
        if (this._isEnabled) {
            WebMidi.addListener('disconnected', (device) => {
                if (device.input) {
                    device.input.removeListener('noteOn')
                    device.input.removeListener('noteOff')
                }
            })
            inputDevice.addListener('noteon', 'all', (event) => {
                try {
                    //console.log(event.rawVelocity)
                    this.emit('keyDown', event.note.number, event.rawVelocity)
                } catch (e) {
                    console.warn(e)
                }
            })
            inputDevice.addListener('noteoff', 'all', (event) => {
                try {
                    //console.log(event.rawVelocity)
                    this.emit('keyUp', event.note.number)
                } catch (e) {
                    console.warn(e)
                }
            })
        }
    }

    getParameterByName(name) {
        const match = RegExp('[?&]' + name + '=([^&]*)').exec(window.location.search);
        return match && decodeURIComponent(match[1].replace(/\+/g, ' '));
    }

    updateParameterByName(name, value) {
        if ('URLSearchParams' in window) {
            const searchParams = new URLSearchParams(window.location.search);
            searchParams.set(name, value);
            const newRelativePathQuery = window.location.pathname + '?' + searchParams.toString();
            history.pushState(null, '', newRelativePathQuery);
        }
    }
}

export {Midi}
