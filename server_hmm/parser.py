#!/usr/bin/python
# This class handles the parsing of a midi data and builds a hidden markov model from it.

import mido
import numpy as np
import os

from my_hmm import HiddenMarkovModel
from hmmlearn import hmm
import pretty_midi
# from music21 import *


class Parser:

    def __init__(self, filenames, verbose=False, time_step=50, end_range=2000, layout='note-time',
                 init_type='zero', pretrain=True, note_type='midikeys', time_type='ms'):
        """
        This is the constructor for a Serializer, which will serialize
        a midi given the filename and generate a hmm of the
        notes in the midi.
        """
        self.filenames = filenames.strip()
        self.time_step = time_step
        # The tempo is number representing the number of microseconds
        # per beat.
        self.tempo = 500000
        # The delta time between each midi message is a number that
        # is a number of ticks, which we can convert to beats using
        # ticks_per_beat.
        self.ticks_per_beat = None
        self.layout = layout
        self.end_range = end_range - (end_range % self.time_step) + self.time_step
        self.beats = self.beats_from_tempo()
        self.durations = self._get_durations(time_type)
        self.note_type = note_type
        self.notes = self._get_notes()
        self.rest = self.notes[-1]
        # self.velocities = [8, 20, 31, 42, 53, 64, 80, 96, 112, 127]
        self.velocities = list(range(8, 131, 5))
        # switch layout
        if self.layout == 'joint':
            states = [0]
            observations = self.get_joint_observations()
            vice_versa = False
        elif self.layout == 'velocity-joint':
            states = self.velocities
            observations = self.get_joint_observations()
            vice_versa = False
        elif self.layout == 'note-time':
            states = self.notes
            observations = self.durations
            vice_versa = False
        elif self.layout == 'time-note':
            states = self.durations
            observations = self.notes
            vice_versa = True
        self.my_hmm = HiddenMarkovModel(states, observations, init_type, False, vice_versa)
        if pretrain:
            self.pretty_parse_gen(verbose)

    def get_joint_observations(self):
        obs = []
        for note in self.notes:
            for duration in self.durations:
                joint = (note, duration)
                obs.append(joint)
        return obs

    def _get_notes(self):
        if self.note_type == 'midikeys':
            # MIDI KEYS + REST 109
            return list(range(21, 110))
        elif self.note_type == 'semitones':
            # SEMITONES + REST R
            return ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B', 'R']
        elif self.note_type == 'intervals':
            # INTERVALS + REST 13
            return list(range(-12, 14))

    def _get_durations(self, time_type):
        if time_type == 'ms':
            # DURATION IN MS
            return list(range(self.time_step, self.end_range, self.time_step))
        elif time_type == 'beats':
            # BEATS
            return self.beats

    def beats_from_tempo(self):
        beats_micros = [int(self.tempo / 8), int(self.tempo / 4), int(self.tempo / 2),
                        int(self.tempo), int(self.tempo * 2), int(self.tempo * 4)]
        return [x / 1000 for x in beats_micros]

    def find_so_pair(self, note, duration, prev_note=0, velocity=100):
        # get note from midikey
        if note != self.rest:
            # for semitones
            if self.note_type == 'semitones':
                note = pretty_midi.note_number_to_name(note)[:-1]
            # for intervals
            elif self.note_type == 'intervals':
                note = note - prev_note
                if note not in self.notes[:-1]:
                    note = 0
        # get nearest duration from durations array
        duration = self.bucket_duration(duration) if self.my_hmm.flexible else self._find_nearest(self.durations,
                                                                                                  duration)
        # switch layout
        if self.layout == 'joint':
            state = 0
            obs = (note, duration)
        elif self.layout == 'velocity-joint':
            state = self._find_nearest(self.velocities, velocity)
            obs = (note, duration)
        elif self.layout == 'note-time':
            state = note
            obs = duration
        elif self.layout == 'time-note':
            state = duration
            obs = note

        return self.my_hmm.serialize(state, obs)

    def _parse_gen(self, verbose=False):
        """
        This function handles the reading of the midi and parses the notes into state-observation pairs,
        which are used to train the hmm. (mido)
        """
        if os.path.exists(self.filenames):
            so_pairs = []
            for filename in os.listdir(self.filenames):
                if filename.endswith('.mid'):
                    prev_note = 0
                    midi = mido.MidiFile(self.filenames + filename)
                    self.ticks_per_beat = midi.ticks_per_beat
                    # default MIDI tempo
                    for track in midi.tracks:
                        for message in track:
                            if verbose:
                                print(message)
                            if message.type == "set_tempo":
                                self.tempo = message.tempo
                                self.beats = self.beats_from_tempo()
                            # and message.velocity != 0
                            elif message.type == "note_off":
                                so_pair = self.find_so_pair(message.note, self._ticks_to_ms(message.time), prev_note)
                                so_pairs.append(so_pair)
                                prev_note = message.note
                            elif message.type == "note_on":
                                if message.velocity == 0:
                                    so_pair = self.find_so_pair(message.note, self._ticks_to_ms(message.time),
                                                                prev_note)
                                    so_pairs.append(so_pair)
                                    prev_note = message.note
                                else:
                                    duration = self._ticks_to_ms(message.time)
                                    # if duration in range(self.beats[3], self.beats[len(self.beats) - 1]):
                                    if self.beats[3] <= duration <= self.beats[len(self.beats) - 1]:
                                        so_pair = self.find_so_pair(self.rest, self._ticks_to_ms(message.time))
                                        so_pairs.append(so_pair)
            if so_pairs:
                self.my_hmm.train(so_pairs, True)
        else:
            print('ERROR: not a directory')
            # TODO: send client alert
            return

    def pretty_parse_gen(self, verbose=False):
        """
        This function handles the reading of the midi and parses the notes into state-observation pairs,
        which are used to train the hmm. (pretty_midi)
        """
        if os.path.exists(self.filenames):
            so_pairs = []
            for filename in os.listdir(self.filenames):
                if filename.endswith('.mid'):
                    prev_note = 0
                    end = 0
                    try:
                        midi_data = pretty_midi.PrettyMIDI(self.filenames + filename)
                    except:
                        continue
                    midi_data.remove_invalid_notes()
                    for instrument in midi_data.instruments:
                        # (for jazz midi dataset preprocessing)
                        # if instrument.program in range(0, 7):
                        #     print(instrument.name)
                        #     print(instrument.program)
                        if not instrument.is_drum:
                            for note in instrument.notes:
                                if note.pitch in range(21, 110):
                                    if verbose:
                                        print(note)
                                    pitch = note.pitch
                                    duration = note.duration * 1000
                                    so_pair = self.find_so_pair(pitch, duration, prev_note, note.velocity)
                                    so_pairs.append(so_pair)
                                    start = note.start
                                    rest = (start - end) * 1000
                                    if self.beats[3] <= rest <= self.beats[len(self.beats) - 1]:
                                        so_pair = self.find_so_pair(self.rest, rest)
                                        so_pairs.append(so_pair)
                                    prev_note = pitch
                                    end = note.end
            if so_pairs:
                self.my_hmm.train(so_pairs, True)
        else:
            print('ERROR: not a directory')
            # TODO: send client alert
            return

    def _ticks_to_ms(self, ticks):
        try:
            return ((ticks / self.ticks_per_beat) * self.tempo) / 1000
        except TypeError:
            raise TypeError(
                "Could not read a tempo and ticks_per_beat from midi")

    def bucket_duration(self, ms):
        """
        This method takes a tick count and converts it to a time in
        milliseconds, bucketing it to the nearest x milliseconds defined by time_step.
        """
        modulo_ms = ms % self.time_step
        if modulo_ms >= self.time_step / 2:
            return self._round_up(ms)
        else:
            return self._round_down(ms)

    def _round_up(self, ms):
        return int(ms - (ms % self.time_step) + self.time_step)

    def _round_down(self, ms):
        return int(ms - (ms % self.time_step))

    @staticmethod
    def _find_nearest(array, value):
        # find nearest value in array for an given value
        return min(array, key=lambda x: abs(x - value))

    def get_hmm(self):
        return self.my_hmm


if __name__ == "__main__":
    # test programm
    parser = Parser('jazz_midi/', verbose=False, time_step=10, end_range=2000, note_type='semitones',
                    init_type='flexible', layout='note-time')

    parser._parse()
    hmm = parser.get_hmm()
    print("States")
    print(hmm.states)
    print()
    print("Observations")
    print(hmm.observations)
    print()
    print("Startprob")
    print(hmm.startprob_)
    print()
    print("Transmat")
    hmm.print_2D_array(hmm.transmat_)
    print()
    print("Emissionprob")
    hmm.print_2D_array(hmm.emissionprob_)

    hmm._check()
    for i in range(len(hmm.observations)):
        swap = i + np.argmin(hmm.observations[i:])
        (hmm.observations[i], hmm.observations[swap]) = (hmm.observations[swap], hmm.observations[i])
        hmm.emissionprob_[:, [i, swap]] = hmm.emissionprob_[:, [swap, i]]
    note_vector = [250, 500, 500, 1000, 500, 500, 500, 500]
    # note_index = list(map(lambda x: hmm.observations.tolist().index(x), note_vector))
    note_index = list(map(lambda x: hmm.observations.index(x), note_vector))
    note_vector = np.array([note_index]).T
    hmm.fit(note_vector)

    print("Startprob2")
    print(hmm.startprob_)
    print("Transmat2")
    hmm.print_2D_array(hmm.transmat_)
    print()
    print("Emissionprob2")
    hmm.print_2D_array(hmm.emissionprob_)