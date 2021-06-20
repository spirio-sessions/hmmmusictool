import {Keyboard} from 'keyboard/Keyboard'
import {UI} from 'interface/UI'
import {AI} from 'ai/AI'
import {Sound} from 'sound/Sound'
import {Glow} from 'interface/Glow'
import {Splash} from 'interface/Splash'
import {Tutorial} from 'ai/Tutorial'
import 'babel-polyfill'

/////////////// SPLASH ///////////////////	

const splash = new Splash(document.body)
splash.on('click', () => {
	keyboard.activate()
	tutorial.start()
})


/////////////// PIANO ///////////////////

const container = document.createElement('div')
container.id = 'container'
document.body.appendChild(container)

const glow = new Glow(container)
const keyboard = new Keyboard(container)

const sound = new Sound()
sound.load()

keyboard.on('keyDown', (note, velocity) => {
	sound.keyDown(note)
	ai.keyDown(note, undefined, undefined, undefined, velocity)
	glow.user()
})

keyboard.on('keyUp', (note) => {
	sound.keyUp(note)
	ai.keyUp(note)
	glow.user()
})

/////////////// AI ///////////////////

const ai = new AI(container)

ai.on('keyDown', (note, time, instrument, velocity) => {
	sound.keyDown(note, time, true, instrument)
	keyboard.keyDown(note, time, true, instrument, velocity)
	glow.ai(time)
})

ai.on('keyUp', (note, time, instrument) => {
	sound.keyUp(note, time, true, instrument)
	keyboard.keyUp(note, time, true, instrument)
	glow.ai(time)
})

ai.on('saveMidi', () => {
	ai.saveMidi()
})

/////////////// UI ///////////////////

if (USE_WEBSOCKETS) {
    window.onload = function() {
        ai.sendUI('reload', {})
    }

	const ui = new UI(container)

	ui.on('send', (message, json) => {
		ai.sendUI(message, json)
	})

	ai.on('setHmmList', (args) => {
	    ui.setHmmList(args)
    })

    ai.on('updateHmmList', (args) => {
	    ui.updateHmmList(args)
    })

    ai.on('uiConfig', (args) => {
	    ui.setConfig(args)
    })
}

/////////////// TUTORIAL ///////////////////

const tutorial = new Tutorial(container)

tutorial.on('keyDown', (note, time) => {
	sound.keyDown(note, time)
	keyboard.keyDown(note, time)
	glow.user()
})

tutorial.on('keyUp', (note, time) => {
	sound.keyUp(note, time)
	keyboard.keyUp(note, time)
	glow.user()
})

tutorial.on('aiKeyDown', (note, time) => {
	ai.keyDown(note, time)
})

tutorial.on('aiKeyUp', (note, time) => {
	ai.keyUp(note, time)
})
