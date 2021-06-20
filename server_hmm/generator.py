#!/usr/bin/python
# This class handles the generation of a new song given a markov chain
# containing the note transitions and their frequencies.
from my_hmm import HiddenMarkovModel

import mido

class Generator:

    def __init__(self):
        self.midi = mido.midifiles.MidiFile()
        self.track = mido.MidiTrack()

    @staticmethod
    def load(my_hmm):
        assert isinstance(my_hmm, HiddenMarkovModel)
        return Generator(my_hmm)

    def _note_to_messages(self, note, duration):
        return [
            mido.Message('note_on', note=note, velocity=100,
                         time=0),
            mido.Message('note_on', note=note, velocity=0,
                         time=duration)
        ]

    def _note_to_message(self, note):
        return [
            mido.Message('note_on', note=note.note, velocity=100,
                         time=note.duration)
        ]

    def _note_to_message_release(self, note, duration):
        return [
            mido.Message('note_on', note=note.note, velocity=0,
                         time=duration)
        ]

    # def gen(self, filename):
    #     with mido.midifiles.MidiFile() as midi:
    #         track = mido.MidiTrack()
    #         samples = self.my_hmm.get_sample_so_pairs(100)
    #         # Generate a sequence of 100 samples
    #         for sample in samples:
    #             track.extend(self._note_to_messages(sample.observation, sample.state))
    #         midi.tracks.append(track)
    #         midi.save(filename)

    def gen_live(self, filename, samples):
        # Generate a sequence of 100 samples
        for sample in samples:
            self.track.extend(self._note_to_messages(sample.observation, sample.state))
        print("LÄNGE")
        print(len(self.track))
        if len(self.track) >= 64:
            self.midi.tracks.append(self.track)
            self.midi.save(filename)

    def gen(self, filename, nd_pairs):
        for nd_pair in nd_pairs:
            self.track.extend(self._note_to_messages(nd_pair.state, nd_pair.observation))
        self.midi.tracks.append(self.track)
        self.midi.save(filename)

    def generate(self, filename):
        with mido.midifiles.MidiFile() as midi:
            track = mido.MidiTrack()
            notes = self.my_hmm.get_sample_notes(100)
            # Generate a sequence of 100 notes
            if self.my_hmm.multitone:
                chunk = []
                for note in notes:
                    if note.duration == 0:
                        chunk.append(note)
                    else:
                        if chunk:
                            for n in chunk:
                                track.extend(self._note_to_message(n))
                            track.extend(self._note_to_message_release(chunk[0], note.duration))
                            del chunk[0]
                            for n in chunk:
                                track.extend(self._note_to_message_release(n, 0))
                            chunk = []
                        track.extend(self._note_to_messages(note.note, note.duration))
            else:
                for note in notes:
                    track.extend(self._note_to_messages(note.note, note.duration))
            midi.tracks.append(track)
            midi.save(filename)

    def generateMultitone(self, filename):
        with mido.midifiles.MidiFile() as midi:
            track = mido.MidiTrack()
            notes = self.my_hmm.get_sample_notes(100)
            # Generate a sequence of 100 notes
            chunk = []
            for note in notes:
                if note.duration == 0:
                    chunk.append(note)
                else:
                    if chunk:
                        for n in chunk:
                            track.extend(self._note_to_message(n))
                        track.extend(self._note_to_message_release(chunk[0], note.duration))
                        del chunk[0]
                        for n in chunk:
                            track.extend(self._note_to_message_release(n, 0))
                        chunk = []
                    track.extend(self._note_to_messages(note.note, note.duration))
            midi.tracks.append(track)
            midi.save(filename)

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3:
        # Example usage:
        # python generator.py <in.mid> <out.mid>
        from parser import Parser
        hmm = Parser(sys.argv[1], verbose=False, time_step=250).get_hmm()
        Generator.load(hmm).gen(sys.argv[2])
        # hmm = HiddenMarkovModel(False)
        # Generator.load(hmm).generate(sys.argv[2])
        print('Generated hidden markov model')
        # hmm.print_as_matrix()
    else:
        print('Invalid number of arguments:')
        print('Example usage: python generator.py <in.mid> <out.mid>')
