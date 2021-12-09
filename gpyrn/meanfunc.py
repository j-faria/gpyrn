"""
Mean functions to use on the GPRN
"""
from functools import wraps
import numpy as np

__all__ = [
    'Constant', 'MultiConstant', 'Linear', 'Parabola', 'Cubic', 'Sine',
    'Keplerian'
]


def array_input(f):
    """ Decorator to provide the __call__ methods with an array """
    @wraps(f)
    def wrapped(self, t):
        t = np.atleast_1d(t)
        r = f(self, t)
        return r
    return wrapped


class MeanModel():
    """ Class for our mean functions"""
    _parsize = 0

    def __init__(self, *pars):
        self.pars = np.array(pars, dtype=float)

    def __repr__(self):
        """ Representation of each instance """
        return "{0}({1})".format(self.__class__.__name__,
                                 ", ".join(map(str, self.pars)))

    @classmethod
    def initialize(cls):
        """ Initialize instance, setting all parameters to 0. """
        return cls(*([0.] * cls._parsize))

    def get_parameters(self):
        return self.pars

    @array_input
    def set_parameters(self, p):
        msg = f'too few parameters for mean {self.__class__.__name__}'
        assert len(p) >= self.pars.size, msg
        if len(p) > self.pars.size:
            p = list(p)
            self.pars = np.array(p[:self.pars.size], dtype=float)
            for _ in range(self.pars.size):
                p.pop(0)
            return np.array(p)
        else:
            self.pars = p

    def __add__(self, b):
        return Sum(self, b)

    def __radd__(self, b):
        return self.__add__(b)

    def __mul__(self, b):
        return Product(self, b)

    def __rmul__(self, b):
        return self.__mul__(b)


class Sum(MeanModel):
    """ Sum of two mean functions """
    def __init__(self, m1, m2):
        self.m1, self.m2 = m1, m2
        self._param_names = tuple(list(m1._param_names) + list(m2._param_names))
        self._parsize = m1._parsize + m2._parsize
        self.pars = np.r_[self.m1.pars, self.m2.pars]

    def __repr__(self):
        return "{0} + {1}".format(self.m1, self.m2)

    @array_input
    def __call__(self, t):
        return self.m1(t) + self.m2(t)


class Product(MeanModel):
    """ Product of two mean functions """
    def __init__(self, m1, m2):
        self.m1, self.m2 = m1, m2
        self._param_names = tuple(list(m1._param_names) + list(m2._param_names))
        self._parsize = m1._parsize + m2._parsize
        self.pars = np.r_[self.m1.pars, self.m2.pars]

    def __repr__(self):
        return "{0} * {1}".format(self.m1, self.m2)

    @array_input
    def __call__(self, t):
        return self.m1(t) * self.m2(t)


##### f(x) = a #################################################################
class Constant(MeanModel):
    """  A constant offset mean function """
    _param_names = 'c',
    _parsize = 1

    def __init__(self, c):
        super(Constant, self).__init__(c)

    @array_input
    def __call__(self, t):
        return np.full(t.shape, self.pars[0])



class MultiConstant(MeanModel):
    """ Contant mean function for multiple instruments """
    _parsize = 0

    def __init__(self, offsets, obsid, time):
        """
        Arguments
        ---------
        offsets : array, list
            Initial values for the between-instrument offsets and the average
            value of the last instrument: [off_1, off_2, ..., avg_n]. Offsets
            are relative to the last instrument.
        obsid : array
            Indices of observations corresponding to each instrument. These
            should be one-based: [1, 1, ..., 2, 2, 2, ..., 3]
        time : array
            Observed times. Should be the same size as `obsid`.
        """
        self.obsid = obsid
        self.time = time
        self._parsize = (np.ediff1d(obsid) == 1).sum() + 1
        self.ii = obsid.astype(int) - 1

        if isinstance(offsets, float):
            offsets = [offsets]

        assert len(offsets) == self._parsize, \
            f'wrong number of parameters, expected {self._parsize} got {len(offsets)}'

        super().__init__(*offsets)
        self._param_names = [f'off{i}' for i in range(1, self._parsize)]
        self._param_names += ['mean']

    def time_bins(self):
        _1 = self.time[np.ediff1d(self.obsid, 0, None) != 0]
        _2 = self.time[np.ediff1d(self.obsid, None, 0) != 0]
        offset_times = np.mean((_1, _2), axis=0)
        return np.sort(np.r_[self.time[0], offset_times])

    @array_input
    def __call__(self, t):
        offsets, c = self.pars[:-1], self.pars[-1]
        offsets = np.pad(offsets, (0, 1))

        if t.size == self.time.size:
            ii = self.ii
        else:
            time_bins = self.time_bins()
            ii = np.digitize(t, time_bins) - 1

        m = np.full_like(t, c) + np.take(offsets, ii)
        return m



##### f(x) = ax + b ############################################################
class Linear(MeanModel):
    """
    A linear mean function
    m(t) = slope * t + intercept
    """
    _param_names = ('slope', 'intercept')
    _parsize = 2

    def __init__(self, slope, intercept):
        super(Linear, self).__init__(slope, intercept)
        self.slope, self.intercept = slope, intercept

    @array_input
    def __call__(self, t):
        tmean = t.mean()
        return self.pars[0] * (t - tmean) + self.pars[1]


##### f(x) = ax**2 + bx + c ####################################################
class Parabola(MeanModel):
    """
    A 2nd degree polynomial mean function
    m(t) = quad * t**2 + slope * t + intercept
    """
    _param_names = ('slope', 'intercept', 'quadratic')
    _parsize = 3

    def __init__(self, quad, slope, intercept):
        super(Parabola, self).__init__(quad, slope, intercept)

    @array_input
    def __call__(self, t):
        return np.polyval(self.pars, t)


##### f(x) = ax**3 + bx**2 + cx + d ############################################
class Cubic(MeanModel):
    """
    A 3rd degree polynomial mean function
    m(t) = cub * t**3 + quad * t**2 + slope * t + intercept
    """
    _param_names = ('slope', 'intercept', 'quadratic', 'cubic')
    _parsize = 4

    def __init__(self, cub, quad, slope, intercept):
        super(Cubic, self).__init__(cub, quad, slope, intercept)

    @array_input
    def __call__(self, t):
        return np.polyval(self.pars, t)


##### f(x) = a**2 * sine(2*pi*t/b + c) + d #####################################
class Sine(MeanModel):
    """
    A sinusoidal mean function
    m(t) = amplitude * sin( 2*pi*t/P + phase)
    """
    _param_names = ('amplitude', 'period', 'phase')
    _parsize = 3

    def __init__(self, amplitude, period, phase):
        super(Sine, self).__init__(amplitude, period, phase)

    @array_input
    def __call__(self, t):
        A, P, φ = self.pars
        return A * np.sin((2 * np.pi * t / P) + φ)


##### f(x) = K*(e*np.cos(w+np.cos(w+nu(x))) + d ################################
class Keplerian(MeanModel):
    """
    Keplerian function adapted from radvel
    We have RV = K[cos(w+v) + e*cos(w)] + sys_vel
    P  = period in days
    e = eccentricity
    K = RV amplitude in m/s
    w = longitude of the periastron
    phi = orbital phase
    sys_vel = offset
    """
    _parsize = 6
    def __init__(self, P, K, e, w, phi, sys_vel):
        super(Keplerian, self).__init__(P, K, e, w, phi, sys_vel)
        self.P, self.K, self.e, self.w, self.phi = P, K, e, w, phi
        self.sys_vel = sys_vel

    @array_input
    def __call__(self, t):
        P, K, e, w, phi, sys_vel = self.pars
        T0 = t[0] - (P*phi)/(2.*np.pi)
        M0 = 2*np.pi*(t-T0)/P #first guess at M
        E0 = M0 + e*np.sin(M0) + 0.5*(e**2)*np.sin(2*M0)  #first guess at E
        M1 = ( E0 - e * np.sin(E0) - M0) #goes to zero when converges
        criteria = 1e-10
        convd = np.where(np.abs(M1) > criteria)[0]  # which indices have not converged
        nd = len(convd)  # number of unconverged elements
        count = 0
        while nd > 0:
            count += 1
            E = E0
            M1p = 1 - e * np.cos(E)
            M1pp = e * np.sin(E)
            M1ppp = 1 - M1p
            d1 = -M1 / M1p
            d2 = -M1 / (M1p + d1 * M1pp / 2.0)
            d3 = -M1 / (M1p + d2 * M1pp / 2.0 + d2 * d2 * M1ppp / 6.0)
            E = E + d3
            E0 = E
            M0 = E0 - e*np.sin(E0)
            M1 = ( E0 - e * np.sin( E0 ) - M0)
            convergence_criteria = np.abs(M1) > criteria
            nd = np.sum(convergence_criteria is True)
        nu = 2*np.arctan(np.sqrt((1+e)/(1-e))*np.tan(E0/2))
        RV = K*(e*np.cos(w)+np.cos(w+nu)) + sys_vel
        return RV


##### f(x) = (x - a)**(-3) + b #################################################
class CubicSun(MeanModel):
    """
    A 3rd degree mean function
    m(t) = (t - xshift)**(-3) + yshift
    """
    _parsize = 4
    def __init__(self, xshift, yshift):
        super(Cubic, self).__init__(xshift, yshift)
        self.xshift = xshift
        self.yshift = yshift

    @array_input
    def __call__(self, t):
        return (t - self.xshift)**(-3) + self.yshift


### END
