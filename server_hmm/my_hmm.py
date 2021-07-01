#!/usr/bin/python
# This class handles the storage and manipulation of a hmm.
from hmmlearn.hmm import MultinomialHMM
from sklearn import preprocessing
import numpy as np
import numpy.random
from collections import namedtuple
import scipy.stats as st

SOPair = namedtuple('SOPair', ['state', 'observation'])


class HiddenMarkovModel(MultinomialHMM):
    def __init__(self, states, observations, init='zero', multitone=False, vice_versa=False):
        self.init = init
        self.multitone = multitone
        self.states = states
        self.n_states = len(self.states)
        self.observations = observations
        self.n_observations = len(self.observations)
        self.vice_versa = vice_versa
        self.flexible = False
        MultinomialHMM.__init__(self, n_components=self.n_states, n_iter=1000, init_params="")
        if init == 'random':
            self._init_random()
        elif init == 'zero':
            self._init_zeros()
        elif init == 'discrete':
            self._init_discrete()
        elif init == 'gauss':
            self._init_gauss()
        elif init == 'flexible':
            self.states = []
            self.n_states = len(self.states)
            self.observations = []
            self.n_observations = len(self.observations)
            self.flexible = True
            self._init_empty()

    # overwrite
    def _check_and_set_n_features(self, X):
        """
        Check if ``X`` is a sample from a Multinomial distribution, i.e. an
        array of non-negative integers.
        """
        if not np.issubdtype(X.dtype, np.integer):
            raise ValueError("Symbols should be integers")
        if X.min() < 0:
            raise ValueError("Symbols should be nonnegative")
        if hasattr(self, "n_features"):
            if self.n_features - 1 < X.max():
                raise ValueError(
                    "Largest symbol is {} but the model only emits "
                    "symbols up to {}"
                        .format(X.max(), self.n_features - 1))
        self.n_features = getattr(self, "n_features", self.emissionprob_.shape[1])

    def _init_random(self):
        self.startprob_ = np.random.rand(self.n_states)
        self.transmat_ = np.random.rand(self.n_states, self.n_states)
        self.emissionprob_ = np.random.rand(self.n_states, self.n_observations)
        self.normalize()

    def _init_zeros(self):
        self.startprob_ = np.zeros(self.n_states)
        self.transmat_ = np.zeros((self.n_states, self.n_states))
        self.emissionprob_ = np.zeros((self.n_states, self.n_observations))

    def _init_discrete(self):
        self._init_zeros()
        self.normalize()

    def _init_empty(self):
        self.startprob_ = np.empty((0, 1))
        self.transmat_ = np.empty((0, 1))
        self.emissionprob_ = np.empty((0, 1))

    def _init_gauss(self):
        s = [0, 3] if self.vice_versa else [-3, 3]
        o = [-3, 3] if self.vice_versa else [0, 3]
        self.startprob_ = self._get_gauss_matrix(1, self.n_states, s, s)[0]
        self.transmat_ = self._get_gauss_matrix(self.n_states, self.n_states, s, s)
        self.emissionprob_ = self._get_gauss_matrix(self.n_states, self.n_observations, s, o)
        self.normalize()

    @staticmethod
    def gkern(kernlen=21, nsig=3):
        """Returns a 2D Gaussian kernel."""
        x = np.linspace(-nsig, nsig, kernlen + 1)
        kern1d = np.diff(st.norm.cdf(x))
        kern2d = np.outer(kern1d, kern1d)
        return kern2d / kern2d.sum()

    @staticmethod
    def _get_gauss_matrix(m, n, y1, x1):
        # Initializing value of x-axis and y-axis
        # in the range -1 to 1
        x, y = np.meshgrid(np.linspace(x1[0], x1[1], n), np.linspace(y1[0], y1[1], m))
        dst = np.sqrt(x * x + y * y)
        # Intializing sigma and muu
        sigma = 1
        muu = 0.000
        # Calculating Gaussian array
        gauss = np.exp(-((dst - muu) ** 2 / (2.0 * sigma ** 2)))
        return gauss

    @staticmethod
    def serialize(state, observation):
        return SOPair(state, observation)

    # get a kxk matrix that rows sum to 1
    @staticmethod
    def get_random_matrix(m, n):
        result = np.random.rand(m, n)
        # Add a random drift term.  We can guarantee that the diagonal terms
        #     will be larger by specifying a `high` parameter that is < 1.
        # How much larger depends on that term.  Here, it is 0.25.
        # result = result + np.random.uniform(low=0., high=.25, size=(k, k))
        # Lastly, divide by row-wise sum to normalize to 1.
        # result / result.sum(axis=1, keepdims=1)
        return result

    def set_startprob(self, startprob):
        self.startprob_ = startprob

    def set_transmat(self, transmat):
        self.transmat_ = transmat

    def set_emissionprob(self, emissionprob):
        self.emissionprob_ = emissionprob

    def get_sample(self, nr_samples):
        return self.sample(nr_samples)

    def train(self, so_pairs, diy=False, weight=50, pretrain=True):
        weight = weight / 100
        # extend probabilities for flexible model
        if self.flexible:
            for so_pair in so_pairs:
                self.extend_probabilities(so_pair)
        # remember old probabilities
        old_starts = self.startprob_
        old_transmat = self.transmat_
        old_emissions = self.emissionprob_
        # train new probabilities
        if diy:
            self._init_zeros()
            self.fit_diy(so_pairs)
            self.norm()
        else:
            if self.flexible or (self.init == 'zero' and not pretrain):
                self._init_zeros()
                self.fit_diy(so_pairs)
                self.normalize()
            obs_index_vector = list(
                map(lambda x: self.observations.index(x.observation), so_pairs))
            X = np.array([obs_index_vector]).T
            self.fit(X)
        # calculate weighted probabilities from old and new
        self.startprob_ = self.startprob_ * weight + old_starts * (1 - weight)
        self.emissionprob_ = self.emissionprob_ * weight + old_emissions * (1 - weight)
        self.transmat_ = self.transmat_ * weight + old_transmat * (1 - weight)
        self.normalize()

    def fit_diy(self, so_pairs):
        previous_chunk = []
        current_chunk = []
        for so_pair in so_pairs:
            current_chunk.append(so_pair)
            self._sequence_gen(previous_chunk, current_chunk)
            previous_chunk = current_chunk
            current_chunk = []

    def extend_probabilities(self, so_pair):
        if so_pair.state not in self.states:
            self.states.append(so_pair.state)
            self.startprob_ = np.append(self.startprob_, 0)
            self.transmat_ = self.extend_matrix(self.transmat_, len(self.states), len(self.states))
            self.emissionprob_ = self.extend_matrix(self.emissionprob_, len(self.states),
                                                          len(self.observations))
            self.n_components = len(self.states)
            self.n_states = len(self.states)
        if so_pair.observation not in self.observations:
            self.observations.append(so_pair.observation)
            self.emissionprob_ = self.extend_matrix(self.emissionprob_, len(self.states),
                                                          len(self.observations))
            self.n_features = len(self.observations)
            self.n_observations = len(self.observations)

    @staticmethod
    def extend_matrix(matrix, m, n):
        shape = np.shape(matrix)
        padded_array = np.zeros((m, n))
        padded_array[:shape[0], :shape[1]] = matrix
        return padded_array

    def _sequence_gen(self, previous_chunk, current_chunk):
        """
        Given the previous chunk and the current chunk of notes as well
        as an averaged duration of the current notes, this function
        permutes every combination of the previous notes to the current
        notes and sticks them into the hmm.
        """
        for e1 in previous_chunk:
            self.addStartprob(e1.state)
            self.addEmissionprob(e1.state, e1.observation)
            for e2 in current_chunk:
                self.addTransmat(e1.state, e2.state)

    def get_sample_so_pairs(self, nr_samples):
        so_pairs = []
        observation_indices, state_indices = self.sample(nr_samples)
        for o_index, s_index in enumerate(state_indices):
            ob = self.observations[observation_indices[o_index][0]]
            st = self.states[s_index]
            so_pairs.append(self.serialize(st, ob))
        return so_pairs

    def get_sample_notes(self, nr_sample_notes):
        sample_notes = []
        time_indices, note_indices = self.sample(nr_sample_notes)
        for time_index, note_index in enumerate(note_indices):
            duration = self.observations[time_indices[time_index][0]]
            note = self.states[note_index]
            sample_notes.append(self.serialize(note, duration))
        return sample_notes

    def learn_all(self, notes):
        self.learn_startprob(notes)
        self.learn_transmat(notes)

    def learn_startprob(self, notes):
        for note in notes:
            itemindex = self.states.index(note.note)
            self.startprob_[itemindex] += 1
        self.startprob_ = self.normalize_1D_array(self.startprob_)

    def learn_transmat(self, notes):
        prev = None
        for note in notes:
            if prev is None:
                prev = note
            else:
                curr = note
                index_prev = self.states.index(prev.note)
                index_curr = self.states.index(curr.note)
                self.transmat_[index_prev][index_curr] += 1
                prev = curr
        self.transmat_ = self.normalize_2D_array(self.transmat_)

    def addStartprob(self, state):
        index_prev = self.states.index(state)
        self.startprob_[index_prev] += 1

    def addEmissionprob(self, state, observation):
        index_prev = self.states.index(state)
        index_duration = self.observations.index(observation)
        self.emissionprob_[index_prev][index_duration] += 1

    def addTransmat(self, from_state, to_state):
        index_prev = self.states.index(from_state)
        index_curr = self.states.index(to_state)
        self.transmat_[index_prev][index_curr] += 1

    def normalize(self):
        self.replace_zeros()
        self.norm()

    def norm(self):
        self.startprob_ = self.normalize_1D_array(self.startprob_)
        self.transmat_ = self.normalize_2D_array(self.transmat_)
        self.emissionprob_ = self.normalize_2D_array(self.emissionprob_)

    def replace_zeros(self):
        self.startprob_[self.startprob_ == 0.0] = 1e-15
        self.transmat_[self.transmat_ == 0.0] = 1e-15
        self.emissionprob_[self.emissionprob_ == 0.0] = 1e-15

    def replace_zero_rows(self):
        t_zero = (self.transmat_ == 0).all(axis=1)
        e_zero = (self.emissionprob_ == 0).all(axis=1)
        s = [0, 3] if self.vice_versa else [-3, 3]
        o = [-3, 3] if self.vice_versa else [0, 3]
        self.transmat_[t_zero, :] = self._get_gauss_matrix(1, self.n_states, s, s)[0]
        self.emissionprob_[e_zero, :] = self._get_gauss_matrix(1, self.n_observations, s, o)[0]

    @staticmethod
    def normalize_array(array):
        sum_of_values = array.sum()
        return array / sum_of_values

    @staticmethod
    def normalize_2D_array(array):
        return preprocessing.normalize(array, norm='l1')

    @staticmethod
    def normalize_1D_array(array):
        # norm = np.linalg.norm(array)
        # return array / norm
        return array / array.sum(axis=None, keepdims=1)

    @staticmethod
    def print_2D_array(array):
        print('\n'.join([' '.join(['{:4}'.format(item) for item in row]) for row in array]))

    def print_as_matrix(self):
        print("States")
        print(self.states)
        print()
        print("Observations")
        print(self.observations)
        print()
        print("Startprob")
        print(self.startprob_)
        print()
        print("Transmat")
        self.print_2D_array(self.transmat_)
        print()
        print("Emissionprob")
        self.print_2D_array(self.emissionprob_)


if __name__ == '__main__':
    # test program
    s = np.arange(0, 500, 250)
    o = np.arange(60, 64)
    print("states")
    print(s)
    print("obs")
    print(o)
    m_hmm = HiddenMarkovModel(s, o, False, False)
    m_hmm.startprob_ = np.array([1, 0])
    m_hmm.transmat_ = np.array([
        [1.0, 0.0],
        [0.0, 0.0]
    ])
    m_hmm.emissionprob_ = np.array([
        [0.25, 0.25, 0.5, 0.0],
        [0.0, 0.0, 0.0, 0.0]
    ])
    m_hmm.normalize()
    note_vector = [60, 61, 62, 60, 60, 60, 60, 60]
    # note_index_vector = list(map(lambda x: m_hmm.observations.tolist().index(x), note_vector))
    note_index_vector = list(map(lambda x: m_hmm.observations.index(x), note_vector))
    note_vector = np.array([note_index_vector]).T
    m_hmm.train(note_vector)
    print("Start")
    print(m_hmm.startprob_)
    print("Trans")
    print(m_hmm.transmat_)
    print("Emiss")
    print(m_hmm.emissionprob_)

    a = np.array([[0.25, 0.25, 0.5],
                  [0.0, 0.5, 0.5]])
    b = np.array([[1.0, 0.0, 0.0],
                  [1.0, 0.0, 0.0]])
    a = a + b
    print(a)
    print(m_hmm.normalize_2D_array(a))
