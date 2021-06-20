#!/usr/bin/env python
#
# midi_input_output.py
#
"""Show how to receive MIDI input by setting a callback function."""

from __future__ import print_function
from parser import Parser
import pretty_midi


class HMMHandler:
    def __init__(self, train=True, sample_rate=10, nr_samples=10, window_size=15, quantisation=50, layout='note-time',
                 train_diy=False, train_rate=10, files='midi/', init_type='zero', pretrain=True, weighting=50,
                 note_type='midikeys', time_type='ms', triggering='note-based'):
        self.obs_vector = []
        self.train_vector = []
        self.all_obs = []
        self.prev_note = 0
        self.octave = 4
        self.train = train
        self.sample_rate = sample_rate
        self.nr_samples = nr_samples
        self.window_size = window_size
        self.quantisation = quantisation
        self.layout = layout
        self.train_diy = train_diy
        self.train_rate = train_rate
        self.files = files
        self.init_type = init_type
        self.pretrain = pretrain
        self.weighting = weighting
        self.note_type = note_type
        self.time_type = time_type
        self.triggering = triggering
        # self.enter = True
        # print(quantisation)
        # for i in range(1, 11):
        #     filenames.append('midi/Sax_' + str(i) + '.mid')
        self.parser = Parser(self.files, verbose=False, time_step=self.quantisation, end_range=2000,
                             layout=self.layout, init_type=self.init_type, pretrain=self.pretrain,
                             note_type=self.note_type, time_type=time_type)
        self.hmm = self.parser.get_hmm()
        # self.generator = Generator.load(self.hmm)

    def call(self, note, duration, velocity=100):
        # if self.enter:
        #     self.sample()
        #     self.enter = False
        duration = int(duration * 1000)
        so_pair = self.parser.find_so_pair(note, duration, self.prev_note, velocity)
        print(so_pair)
        if note != self.parser.rest:
            self.octave = pretty_midi.note_number_to_name(note)[-1]
            self.prev_note = note
            if self.triggering == 'note-based':
                self.obs_vector.append(so_pair)
                self.train_vector.append(so_pair)
            self.all_obs.append(so_pair)
        else:
            if self.parser.beats[3] <= duration <= self.parser.beats[len(self.parser.beats) - 1]:
                # print('pause')
                self.all_obs.append(so_pair)
        if self.triggering == 'note-based':
            return self.check_for_triggering()
        else:
            return False

    def call_beat(self):
        self.train_vector.append('beat')
        self.obs_vector.append('beat')
        return self.check_for_triggering()

    def check_for_triggering(self):
        if self.train and len(self.train_vector) == self.train_rate:
            so_pairs = self.all_obs[-self.window_size:]
            self.hmm.train(so_pairs, self.train_diy, self.weighting, self.pretrain)
            self.train_vector = []
        if len(self.obs_vector) == self.sample_rate:
            self.obs_vector = []
            return self.sample(self.octave, self.prev_note)
        return False

    def sample(self, octave, prev_note):
        # print("sample")
        samples = self.hmm.get_sample_so_pairs(self.nr_samples)
        # self.generator.gen_live("../out/live.mid", sample)
        midi_instrument = pretty_midi.Instrument(program=0)
        time_start = 0
        velocity = 100
        for sample in samples:
            if self.layout == 'joint':
                note = sample.observation[0]
                duration = sample.observation[1]
            elif self.layout == 'velocity-joint':
                note = sample.observation[0]
                duration = sample.observation[1]
                velocity = sample.state
            elif self.layout == 'note-time':
                note = sample.state
                duration = sample.observation
            elif self.layout == 'time-note':
                note = sample.observation
                duration = sample.state
            duration = duration / 1000
            if note == self.parser.rest:
                time_start = time_start + duration
            else:
                if self.note_type == 'semitones':
                    note = pretty_midi.note_name_to_number(note + octave)
                if self.note_type == 'intervals':
                    note = prev_note + note
                    if note not in range(21, 110):
                        continue
                    else:
                        prev_note = note
                pretty_note = self._convert_note_message(note, duration, time_start, velocity)
                time_start = pretty_note.end + 0.03
                midi_instrument.notes.append(pretty_note)
        return self._sample_to_json(midi_instrument)

    @staticmethod
    def _convert_note_message(note, duration, time_start, velocity):
        time_end = time_start + duration
        pretty_note = pretty_midi.Note(velocity=velocity, pitch=note, start=time_start, end=time_end)
        return pretty_note

    @staticmethod
    def _sample_to_json(generated_sequence):
        notes = []
        for seq_note in generated_sequence.notes:
            notes.append({
                'pitch': seq_note.pitch,
                'velocity': seq_note.velocity,
                'start_time': seq_note.start,
                'end_time': seq_note.end,
                'instrument': 1
            })
        return notes
