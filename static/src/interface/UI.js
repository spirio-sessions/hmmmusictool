import events from 'events'
import 'style/ui.css'
import 'style/tooltip.css'

const TIPS = {
    hmm_type: 'Create new HMM or choose saved HMM',
    topology: 'Parameters affecting the HMM structure',
    init: 'Initialization type for the transition and emission probabilities',
    note: 'Note assignment <br> •	Midikeys - (88 keys from 21-109) whole keyboard range, octave information included <br> •	Semitones - (12 tones from C-H) one octave, octave change depended on input <br> •	Intervals - (25 intervals from -12-12) two octaves, learns key distances in note changes',
    time: 'Duration assignment <br> •	Ms - resolution dependent on quantization from 0-2000ms <br> •	Beats - from 32th note - whole note',
    quantization: 'Resolution of the note durations in ms - smaller quantization results in more exactly representations, but larger models',
    layout: 'State and observation assignment <br> •	Note-Time - states = notes, observations = durations <br> •	Time-Note - states = durations, observations = notes <br> •	Joint - states = no assignment, observations = notes and durations joint',
    training: 'Parameters affecting the HMM training (pretraining + retraining)',
    pretraining: 'De-/activation of pretraining (adjusts the probabilities from prerecorded midi files)',
    data_path: 'Directory path to the midi data for pretraining <br> •	midi/ - prerecorded jazz saxophone midi <br> •	piano/ - prerecorded jazz piano midi <br> •	Local directory - e.g. /Users/mustermann/Documents/Midi/',
    retraining:  'De-/activation of retraining (adjusts the probabilities from live recorded input midi)',
    retraining_type: 'Retraining type <br> •	Normal - indirect training of states from observations by EM Algorithm <br> •	Diy - direct training of states and observations by counting and normalizing their occurrences',
    train_rate: 'Period to trigger training (update HMM), after how many notes/beats',
    sample_rate: 'Period to trigger sampling (generate output), after how many notes/beats',
    nr_samples: 'Number of generated samples (note-duration-pairs) sent to the output',
    window_size: 'Number of past notes considered for retraining',
    weighting: 'Weighting in percent for the retraining matrix <br> •	0% - only old matrix is considered, no retraining at all <br> •	50% - old matrix and retrained matrix are considered fifty-fifty <br> •	100% - only retrained matrix is considered, replaces old matrix',
    triggering: 'Triggering events considered for retraining and sampling <br> •	note-based - notes are counted <br> •	beat-based - beats from osc messages are counted'
}

class UI extends events.EventEmitter {

	constructor(container){
        super()
        var uiDiv = this.setupUI()
        container.appendChild(uiDiv)
	}

    setupUI(){
        // TOGGLE
        var toggleDiv = document.createElement('div')
        toggleDiv.id = 'togContainer'
        // UI
        var uiDiv = document.createElement('div')
        uiDiv.id = 'ui'
        var uiTitle = this.createLabel('ui-title', 'HMM Modifier', null)
        // FORM
        var form = document.createElement('form')
        form.id = 'uiForm'
        form.addEventListener('submit', (event) => {
            event.preventDefault()
		})
		// HMMS
		var hmms = ['new']
		var hmmType = document.createElement('div')
        hmmType.className = 'control'
        var select = this.createSelect('hmmType', hmms)
        select.addEventListener('change', (event) => {
            this.emit('send', 'changeHMM', event.target.value)
		})
        var label = this.createLabel('hmmType', 'HMM-Type: ', TIPS.hmm_type)
        hmmType.appendChild(label)
        hmmType.appendChild(select)
		// var hmms = ['new']
		// var hmmSelect = this.createSelectLabelCombi('hmmType', hmms, 'HMM-Type: ')
        // TOPOLOGY
        var topology = this.initTopology()
        // TRAINING
        var training = this.initTraining()
        // SUBMIT
        var submit = document.createElement('BUTTON')
        submit.id = 'submit'
        submit.textContent = 'New HMM'
        submit.addEventListener('click', () => {
            var json = this.formToJson()
            if(this.check()){
                this.emit('send', 'submit', json)
                alert('Created new HMM')
            }
		})
		// SAVE
		var saveHmm = document.createElement('BUTTON')
        saveHmm.id = 'saveHMM'
        saveHmm.textContent = 'Save HMM'
        saveHmm.addEventListener('click', () => {
            this.emit('send', 'saveHMM', 'HMM')
            alert('Saved HMM')
		})
        // TOGGLE BUTTON
        var toggle = document.createElement('BUTTON')
        toggle.id = 'tog'
        toggle.textContent = '+'
        toggle.addEventListener('click', () => {
            var x = document.getElementById("togContainer");
            if (x.style.display === "none") {
                x.style.display = "block";
            } else {
                x.style.display = "none";
            }
		})
		// APPEND ALL
		form.appendChild(hmmType)
        form.appendChild(topology)
        form.appendChild(training)
		toggleDiv.appendChild(uiTitle)
		toggleDiv.appendChild(form)
		toggleDiv.appendChild(submit)
		toggleDiv.appendChild(saveHmm)
		uiDiv.appendChild(toggle)
		uiDiv.appendChild(toggleDiv)
		return uiDiv
    }

	setHmmList(list){
	    var hmmSelect = document.getElementById('hmmType')
	    var length = hmmSelect.options.length;
        for (var i = length-1; i >= 1; i--) {
            hmmSelect.remove(i)
        }
	    for (const val of list) {
            var option = document.createElement('option');
            option.value = val;
            option.text = val.charAt(0).toUpperCase() + val.slice(1);
            hmmSelect.appendChild(option);
        }
	}

	updateHmmList(val){
	    var hmmSelect = document.getElementById('hmmType')
        var option = document.createElement('option');
        option.value = val;
        option.text = val.charAt(0).toUpperCase() + val.slice(1);
        hmmSelect.appendChild(option);
        hmmSelect.value = val;
	}

	setConfig(json){
	    var jsonObject = json
	    for (var key in jsonObject) {
            var element = document.getElementById(key)
            if(element != null){
                element.value = jsonObject[key]
            }else{
                // for radio button
                element = document.getElementById(key + jsonObject[key])
                element.checked = true
            }
            // for slider span
            var span = document.getElementById(key + 'span')
            if(span != null){
                span.innerHTML = jsonObject[key]
            }
        }
	}

	check(){
	    var rbs = document.getElementsByName('pretrain')
	    for (const rb of rbs) {
            if (rb.checked) {
                var notPretrain = rb.value == 'no';
                break;
            }
        }
        rbs = document.getElementsByName('retrain')
	    for (const rb of rbs) {
            if (rb.checked) {
                var notRetrain = rb.value == 'no';
                break;
            }
        }
	    var flex = document.getElementById('init').value == 'flexible'
	    var zero = document.getElementById('init').value == 'zero'
	    var trainRate = parseInt(document.getElementById('train-rate').value)
	    var sampleRate = parseInt(document.getElementById('sample-rate').value)
        var rateToSmall =  sampleRate < trainRate
        // var trainNormal = document.getElementById('diy').checked.value == 'normal'
        /*rbs = document.getElementsByName('diy')
	    for (const rb of rbs) {
            if (rb.checked) {
                var trainNormal = rb.value == 'normal';
                break;
            }
        }*/
	    if(notPretrain && (zero || flex) && rateToSmall){
	        alert('If pretraining is disabled and init-type is zero or flexible, the sample-rate must be greater or equals train-rate.')
	        return false
	    }else if(notPretrain && notRetrain && (zero || flex)){
            alert('If retraining and pretraining is disabled and init-type is zero or flexible, no samples can be generated. Please change the parameters.')
	        return false
	    }else{
	        return true
	    }
	}

	formToJson(){
	    var formElement = document.getElementsByTagName("form")[0],
                inputElements = formElement,
                jsonObject = {};
        for(var i = 0; i < inputElements.length; i++){
            var inputElement = inputElements[i];
            if (inputElement.checked || inputElement.type != 'radio'){
                // if (inputElement.id == 'files') {
                    // console.log(inputElement.value)
                    // jsonObject[inputElement.name] = inputElement.files;
                // }else{
                jsonObject[inputElement.name] = inputElement.value;
                // }
            }
        }
        var json = JSON.stringify(jsonObject);
        return json
    }

	initTopology(){
	    var topology = document.createElement('div')
		topology.id = 'topology'
		// TITEL
		var topologyTitle = this.createLabel('topology-title', 'Topology', TIPS.topology)
		// NOTE SELECT
		var note = this.createSelectLabelCombi('note', ['midikeys', 'semitones', 'intervals'], 'Note-Type: ', TIPS.note)
		var time = this.createSelectLabelCombi('time', ['ms', 'beats'], 'Time-Type: ', TIPS.time)
		// INIT SELECT
		var init = this.createSelectLabelCombi('init', ['zero', 'flexible', 'discrete', 'gauss', 'random'], 'Init-Type: ', TIPS.init)
		// QUANTISATION SLIDER
		var quantisation = this.createSlider('quantisation', 10, 300, 10, 50, 'Quantization Ms: ', TIPS.quantization)
		// STATE/OBSERVATION LAYOUT SELECT
		// var viceVersa = this.createRadio('vice-versa', ['Note-Time', 'Time-Note'], 'Layout: ')
		var layout = this.createSelectLabelCombi('layout', ['note-time', 'time-note', 'joint', 'velocity-joint'], 'Layout: ', TIPS.layout)
        topology.appendChild(topologyTitle)
		topology.appendChild(init)
		topology.appendChild(note)
        topology.appendChild(time)
	    topology.appendChild(quantisation)
		topology.appendChild(layout)
		return topology
	}

	initTraining(){
	    var training = document.createElement('div')
	    var trainingTitle = this.createLabel('training-title', 'Training', TIPS.training)
	    training.id = 'training'
		// RETRAINING RADIO
		var retrain = this.createRadio('retrain', ['yes', 'no'], 'Retraining: ', TIPS.retraining)
		// TRIGGERING
		var triggering = this.createSelectLabelCombi('triggering', ['note-based', 'beat-based'], 'Triggering: ', TIPS.triggering)
		// TRAIN RATE SLIDER
	    var trainRate = this.createSlider('train-rate', 1, 100, 1, 10, 'Train-Rate: ', TIPS.train_rate)
	    // SAMPLE RATE SLIDER
	    var sampleRate = this.createSlider('sample-rate', 1, 100, 1, 10, 'Sample-Rate: ', TIPS.sample_rate)
	    // NR SAMPLES SLIDER
	    var nrSamples = this.createSlider('nr-samples', 1, 100, 1, 10, 'Nr-Samples: ', TIPS.nr_samples)
	    // RETRAINING TYPE RADIO
		var diy = this.createRadio('diy', ['normal', 'diy'], 'Retraining-Type: ', TIPS.retraining_type)
		// WINDOW SIZE SLIDER
	    var windowSize = this.createSlider('window-size', 1, 100, 1, 15, 'Window-Size: ', TIPS.window_size)
	    // WEIGHING SLIDER
	    var weighting = this.createSlider('weighting', 0, 100, 10, 50, 'Weighting %: ', TIPS.weighting)
	    // PRETRAINING FILECHOOSER
	    // var files = this.createFileChooser('files', 'Pretrain Files: ')
	    var files = this.createTextfield('files', 'Data-Path: ', TIPS.data_path)
	    // PRETRAINING RADIO
		var pretrain = this.createRadio('pretrain', ['yes', 'no'], 'Pretraining: ', TIPS.pretraining)
		// UPDATE BUTTON
        var updateHMM = document.createElement('BUTTON')
        updateHMM.id = 'updateHMM'
        updateHMM.innerHTML = '<img src="images/reloadHMM.ico" />';
        updateHMM.addEventListener('click', () => {
            var json = this.formToJson()
            if(this.check()){
                this.emit('send', 'updateHMM', json)
                alert('Updated current HMM')
            }
		})

        var pretrain_div = document.createElement('div')
		pretrain_div.id = 'pretrain_div'
		var retrain_div = document.createElement('div')
        retrain_div.id = 'retrain_div'

		pretrain_div.appendChild(pretrain)
		pretrain_div.appendChild(files)
        retrain_div.appendChild(updateHMM)
		retrain_div.appendChild(retrain)
		retrain_div.appendChild(diy)
		retrain_div.appendChild(triggering)
		retrain_div.appendChild(trainRate)
		retrain_div.appendChild(sampleRate)
		retrain_div.appendChild(nrSamples)
		retrain_div.appendChild(windowSize)
		retrain_div.appendChild(weighting)
		training.appendChild(trainingTitle)
		training.appendChild(pretrain_div)
		training.appendChild(retrain_div)

		return training
	}

	createSelectLabelCombi(id, values, text, tip){
        var div = document.createElement('div')
        div.className = 'control'
        var select = this.createSelect(id, values)
        var label = this.createLabel(id, text, tip)
        div.appendChild(label)
        div.appendChild(select)
        return div
    }

	createSelect(id, values){
        var select = document.createElement('select');
        select.id = id
        select.name = id
        for (const val of values) {
            var option = document.createElement('option');
            option.value = val;
            option.text = val.charAt(0).toUpperCase() + val.slice(1);
            select.appendChild(option);
        }
        return select
	}

	createLabel(id, text, tip){
	    var label = document.createElement('label');
        label.innerHTML = text;
        label.id = id + 'label';
        if(tip != null){
            var tooltip_div = document.createElement('div')
            tooltip_div.id = id + 'tooltip'
            tooltip_div.className = 'tooltip'
            var tooltip_span = document.createElement('span')
            tooltip_span.className = 'tooltiptext'
            tooltip_span.innerHTML = tip
            tooltip_div.appendChild(tooltip_span)
            tooltip_div.appendChild(label)
            return tooltip_div
        }else{
            return label
        }
	}

	createRadio(id, values, text, tip){
	    var div = document.createElement('div')
        div.className = 'control'
	    var title = this.createLabel(id, text, tip)
	    div.appendChild(title)
	    //for (const val of values) {
	    for (var i = 0; i < values.length; i++) {
	        var val = values[i]
	        var radio = document.createElement('INPUT');
            radio.setAttribute('type', 'radio');
            radio.id = id + val
            radio.name = id
            radio.value = val
            if(i == 0){
                radio.checked = true
            }
            var label = this.createLabel(radio.id, val.charAt(0).toUpperCase() + val.slice(1), null)
            div.appendChild(label).appendChild(radio)
	    }
        return div
	}

	createSlider(id, min, max, step, val, text, tip){
	    var div = document.createElement('div')
        div.className = 'control'
	    var slider = document.createElement('INPUT');
	    slider.id = id
	    slider.name = id
	    slider.setAttribute('type', 'range');
	    slider.setAttribute('min', min);
	    slider.setAttribute('max', max);
	    slider.setAttribute('step', step);
	    slider.setAttribute('value', val);
	    var label = this.createLabel(id, text, tip)
	    var divText = document.createElement('span')
	    divText.id = id + 'span'
	    divText.innerHTML = ' ' + slider.value
	    slider.oninput = function (){
	        divText.innerHTML = this.value
	    }
	    div.appendChild(label)
	    div.appendChild(slider)
	    div.appendChild(divText)
	    return div
	}

	createFileChooser(id, text, tip){
	    var div = document.createElement('div')
        div.className = 'control'
	    var files = document.createElement('INPUT');
	    files.id = id
	    files.name = id
	    files.setAttribute('type', 'file');
	    files.setAttribute('multiple', true)
	    var label = this.createLabel(id, text, tip)
    	div.appendChild(label)
    	div.appendChild(files)
	    return div
	}

	createTextfield(id, text, tip){
	    var div = document.createElement('div')
        div.className = 'control'
	    var textfield = document.createElement('INPUT')
        textfield.id = id
        textfield.name = id
        textfield.value = 'midi/'
	    textfield.setAttribute('type', 'text')
	    var label = this.createLabel(id, text, tip)
    	div.appendChild(label)
    	div.appendChild(textfield)
	    return div
	}
}

export {UI}