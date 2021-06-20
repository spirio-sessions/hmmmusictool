import Tone from 'Tone/core/Tone'
import {Sampler} from 'sound/Sampler'

class Sound {
    constructor() {

        // make the samples loaded based on the screen size
        if (screen.availWidth < 750 && screen.availHeight < 750) {
            this._range = [48, 72]
        } else if (screen.availWidth < 1000 && screen.availHeight < 1000) {
            this._range = [48, 84]
        } else {
            this._range = [24, 108]
        }


        this._piano = new Sampler('audio/Salamander/', this._range)
        this._bass = new Sampler('audio/bass/mf/', null, [24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38])
        this._synth = new Sampler('audio/string_ensemble/', this._range)
        this._drum = new Sampler('audio/drum_kits/analog/', null, [36, 38, 42, 45, 46, 48, 50, 51])

    }

    load() {
        return Promise.all([this._piano.load(), this._synth.load(), this._drum.load(), this._bass.load()])
    }

    keyDown(note, time = Tone.now(), ai = false, instrument = 0) {
        if (instrument === 9) {
            this._drum.volume = -1
            this._drum.keyDown(note, time)
        } else if (instrument === 1) {
            this._piano.keyDown(note, time)
        } else {
            this._piano.keyDown(note, time)
            if (!ai) {
                this._synth.volume = -8
                this._synth.keyDown(note, time)
            }
        }
    }

    keyUp(note, time = Tone.now(), ai = false, instrument = 0) {
        time += 0.05
        if (instrument === 9) {
            this._drum.keyUp(note, time)
        } else if (instrument === 1) {
            this._piano.keyUp(note, time)
        } else {
            this._piano.keyUp(note, time)
            if (!ai) {
                this._synth.keyUp(note, time)
            }
        }
    }
}

export {Sound}
