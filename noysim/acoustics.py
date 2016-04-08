# Noysim -- Noise simulation tools for Aimsun.
# Copyright (c) 2010-2011 by Bert De Coensel, Ghent University & Griffith University.
#
# Acoustical functions and classes

import numpy
import pylab


#---------------------------------------------------------------------------------------------------
# Basic constants
#---------------------------------------------------------------------------------------------------

LOWDB = -100.0 # lowest value for decibel calculation (the "zero" value, corresponding to zero energy)

# octave band (8) and 1/3-octave band (31) center frequencies
FOCTAVE = [63., 125., 250., 500., 1000., 2000., 4000., 8000.]
FTERTS  = [ 20.,  25., 31.5,  40.,   50.,   63.,   80.,  100., 125., 160., 200., 250., 315., 400., 500., 630.,
           800., 1000., 1250., 1600., 2000., 2500., 3150., 4000., 5000., 6300., 8000., 10000., 12500., 16000., 20000.]
FTERTSEXACT = 1000.0*((2.0**(1.0/3.0))**numpy.arange(-17.0,14.0)) # exact center frequencies
FOFFSET = 4 # index of first FOCTAVE value in FTERTS list
LOCTAVE = ['63', '125', '250', '500', '1k', '2k', '4k', '8k'] # labels
LTERTS  = ['', '', '31.5', '', '', '63', '', '', '125', '', '', '250', '', '', '500',
           '', '', '1k', '', '', '2k', '', '', '4k', '', '', '8k', '', '', '16k', '']
LOCTERTS = {  31.5: '31.5', 63.0: '63', 125.0: '125', 250.0: '250', 500.0: '500',
            1000.0: '1k', 2000.0: '2k', 4000.0: '4k', 8000.0: '8k', 16000.0: '16k'}

# A- and C-weights for octave bands and 1/3-octave bands
AOCTAVE = [-26.2, -16.1,  -8.6,  -3.2,   0.0,   1.2,   1.0,  -1.1]
COCTAVE = [ -0.8,  -0.2,   0.0,   0.0,   0.0,  -0.2,  -0.8,  -3.0]
ATERTS  = [-50.5, -44.7, -39.4, -34.6, -30.2, -26.2, -22.5, -19.1, -16.1, -13.4, -10.9, -8.6, -6.6, -4.8,  -3.2, -1.9,
            -0.8,   0.0,   0.6,   1.0,   1.2,   1.3,   1.2,   1.0,   0.5,  -0.1,  -1.1, -2.5, -4.3, -6.6,  -9.3]
CTERTS  = [ -6.2,  -4.4,  -3.0,  -2.0,  -1.3,  -0.8,  -0.5,  -0.3,  -0.2,  -0.1,   0.0,  0.0,  0.0,  0.0,   0.0,  0.0,
             0.0,   0.0,   0.0,  -0.1,  -0.2,  -0.3,  -0.5,  -0.8,  -1.3,  -2.0,  -3.0, -4.4, -6.2, -8.5, -11.2]

# various standard markers for plotting 1/3-octave band spectra
marker = {'cross':                {'marker': 'x', 'markeredgecolor': 'black', 'markerfacecolor': 'white'},
          'circle white':         {'marker': 'o', 'markeredgecolor': 'black', 'markerfacecolor': 'white'},
          'circle grey':          {'marker': 'o', 'markeredgecolor': 'black', 'markerfacecolor': 'grey'},
          'circle black':         {'marker': 'o', 'markeredgecolor': 'black', 'markerfacecolor': 'black'},
          'circle transparent':   {'marker': 'o', 'markeredgecolor': 'black', 'markerfacecolor': 'None'},
          'square invisible':     {'marker': 's', 'markeredgecolor': 'white', 'markerfacecolor': 'white'},
          'square white':         {'marker': 's', 'markeredgecolor': 'black', 'markerfacecolor': 'white'},
          'square grey':          {'marker': 's', 'markeredgecolor': 'black', 'markerfacecolor': 'grey'},
          'square black':         {'marker': 's', 'markeredgecolor': 'black', 'markerfacecolor': 'black'},
          'square transparent':   {'marker': 's', 'markeredgecolor': 'black', 'markerfacecolor': 'None'},
          'diamond white':        {'marker': 'D', 'markeredgecolor': 'black', 'markerfacecolor': 'white'},
          'diamond grey':         {'marker': 'D', 'markeredgecolor': 'black', 'markerfacecolor': 'grey'},
          'diamond black':        {'marker': 'D', 'markeredgecolor': 'black', 'markerfacecolor': 'black'},
          'diamond transparent':  {'marker': 'D', 'markeredgecolor': 'black', 'markerfacecolor': 'None'},
          'triangle white':       {'marker': '^', 'markeredgecolor': 'black', 'markerfacecolor': 'white'},
          'triangle grey':        {'marker': '^', 'markeredgecolor': 'black', 'markerfacecolor': 'grey'},
          'triangle black':       {'marker': '^', 'markeredgecolor': 'black', 'markerfacecolor': 'black'},
          'triangle transparent': {'marker': '^', 'markeredgecolor': 'black', 'markerfacecolor': 'None'}}


#---------------------------------------------------------------------------------------------------
# Decibel calculus
#---------------------------------------------------------------------------------------------------

def fromdB(x):
  """ translate from dB values to linear values """
  return 10.0**(0.1*x)


def todB(x):
  """ translate from linear values to dB values """
  return 10.0*numpy.log10(numpy.clip(x, fromdB(LOWDB), numpy.Inf))


def plusdB(x, y):
  """ add two dB values - for the more general case, see sumdB """
  return todB(fromdB(x) + fromdB(y))


def averagedB(x, axis = None):
  """ energy equivalent average of (numpy) array of dB values, over given axis (default over all values, 0 = vertically, 1 = horizontally) """
  return todB(numpy.mean(fromdB(numpy.asarray(x)), axis = axis))


def sumdB(x, axis = None):
  """ energy equivalent sum of (numpy) array of dB values, over given axis (default over all values, 0 = vertically, 1 = horizontally) """
  return todB(numpy.sum(fromdB(numpy.asarray(x)), axis = axis))


def parsedB(s):
  """ convert a string to a float for loading data from textfiles (checks for 'Inf' or 'NaN', minimum python 2.6 needed) """
  return max(float(s), LOWDB)


#---------------------------------------------------------------------------------------------------
# Base band spectrum
#---------------------------------------------------------------------------------------------------

class Spectrum(object):
  """ base class for spectra with octave and 1/3-octave bands, implementing decibel arithmetic """
  def __init__(self, f, z):
    object.__init__(self)
    self.setFreqAmps(f = f, z = z)

  def frequencies(self):
    """ return frequency values (Hz) """
    return self._f

  def amplitudes(self):
    """ return amplitude values (dB/dBA) """
    return self._z

  def copy(self):
    """ return a copy of the band spectrum """
    return Spectrum(f = self.frequencies().copy(), z = self.amplitudes().copy())

  def setFreqAmps(self, f, z):
    """ set the frequency and amplitude values """
    if len(f) != len(z):
      raise Exception('Spectrum frequency and amplitude arrays do not have same length')
    self._f = numpy.asarray(f).copy() # frequencies
    self._z = numpy.asarray(z).copy() # amplitudes

  def setFrequencies(self, f):
    """ set the frequency values """
    if len(f) != len(self._f):
      raise Exception('setFrequencies: Spectrum frequency and amplitude arrays do not have same length')
    self._f = numpy.asarray(f).copy()

  def setAmplitudes(self, z):
    """ set the amplitude values """
    if len(z) != len(self._z):
      raise Exception('setAmplitudes: Spectrum frequency and amplitude arrays do not have same length')
    self._z = numpy.asarray(z).copy()

  def __len__(self):
    """ return the number of values in the band spectrum """
    return len(self.frequencies())

  def freqindex(self, f):
    """ return the frequency index for a given frequency f """
    return numpy.where(self.frequencies() == f)[0][0]

  def __getitem__(self, f):
    """ return the band spectrum amplitude at frequency f """
    return self.amplitudes()[self.freqindex(f)]

  def __setitem__(self, f, z):
    """ set the band spectrum amplitude at frequency f """
    self.amplitudes()[self.freqindex(f)] = z

  def __iter__(self):
    """ return an iterator with the band spectrum frequencies and amplitudes """
    return iter(zip(self.frequencies(), self.amplitudes().flat))

  def __str__(self):
    """ return a simple string representation of the band spectrum """
    return '[' + ', '.join([('%.1f'%x) for x in self.amplitudes()]) + ']'

  def __iadd__(self, other):
    """ add two band spectra together (energy-wise) """
    if len(self.amplitudes()) != len(other.amplitudes()):
      raise Exception('Spectrum addition with spectra of different size')
    self.setAmplitudes(z = 10.0*numpy.log10(10.0**(self.amplitudes()/10.0) + 10.0**(other.amplitudes()/10.0)))
    return self

  def __add__(self, other):
    """ add two band spectra together (energy-wise) """
    result = self.copy()
    result += other
    return result

  def correct(self, other):
    """ add a correction (scalar or spectrum) to self, in dB """
    if isinstance(other, Spectrum):
      # correction with spectrum
      if len(self.amplitudes()) != len(other.amplitudes()):
        raise Exception('Spectrum.correct() with spectra of different size')
      self.setAmplitudes(self.amplitudes() + other.amplitudes())
    else:
      # correction with scalar value or numpy array
      self.setAmplitudes(self.amplitudes() + other)
    return self

  def multiply(self, factor):
    """ multiply the band spectrum energy with a given factor """
    self.setAmplitudes(self.amplitudes() + 10.0*numpy.log10(factor))

  def __imul__(self, factor):
    """ multiply the band spectrum energy with a given factor """
    self.multiply(factor)
    return self

  def __mul__(self, factor):
    """ multiply the band spectrum energy with a given factor """
    result = self.copy()
    result.multiply(factor)
    return result

  def __rmul__(self, factor):
    """ multiply the band spectrum energy with a given factor """
    return self.__mul__(factor)

  def divide(self, factor):
    """ divide the band spectrum energy by a given factor """
    self.setAmplitudes(self.amplitudes() - 10.0*numpy.log10(factor))

  def __idiv__(self, factor):
    """ divide the band spectrum energy by a given factor """
    self.divide(factor)
    return self

  def __div__(self, factor):
    """ divide the band spectrum energy by a given factor """
    result = self.copy()
    result.divide(factor)
    return result

  def __rdiv__(self, factor):
    """ divide the band spectrum energy by a given factor """
    return self.__div__(factor)

  def __neg__(self):
    """ unary - operator, return band spectrum with negated dB values """
    result = self.copy()
    result.setAmplitudes(-result.amplitudes())
    return result

  def aweights(self):
    """ return A-weighting values """
    raise NotImplementedError

  def cweights(self):
    """ return C-weighting values """
    raise NotImplementedError

  def leq(self):
    """ return energy equivalent sound power level """
    return sumdB(self.amplitudes())

  def laeq(self):
    """ return A-weighted energy equivalent sound power level """
    return sumdB(self.amplitudes() + self.aweights())

  def lceq(self):
    """ return C-weighted energy equivalent sound power level """
    return sumdB(self.amplitudes() + self.cweights())

  def labels(self):
    """ return the frequency labels """
    raise NotImplementedError


#---------------------------------------------------------------------------------------------------
# Octave and 1/3-octave band spectra
#---------------------------------------------------------------------------------------------------

class OctaveBandSpectrum(Spectrum):
  """ ISO octave band spectrum class """
  def __init__(self, z = [LOWDB]*len(FOCTAVE)):
    if len(z) != len(FOCTAVE):
      raise Exception('trying to construct OctaveBandSpectrum with nr of bands != ' + str(len(FOCTAVE)))
    Spectrum.__init__(self, f = FOCTAVE, z = z)

  def copy(self):
    return OctaveBandSpectrum(self.amplitudes().copy())

  def aweights(self):
    return numpy.asarray(AOCTAVE)

  def cweights(self):
    return numpy.asarray(COCTAVE)

  def labels(self):
    return LOCTAVE

  def octaveBandSpectrum(self):
    """ return the associated octave band spectrum (copy of itself in this case) """
    return self.copy()

  def plot(self, width = 0.5, shift = 0.0, color = 'black', interval = None):
    """ plot the spectrum using a bar chart, with given relative width of bands """
    x = numpy.arange(len(self.frequencies())) + 1.0 - width + shift
    handle = pylab.bar(x, self.amplitudes(), width = width, facecolor = color)
    a = pylab.axis()
    if interval == None:
      pylab.axis((0, len(self.frequencies()) + 1.0 - width, a[2], a[3]))
    else:
      pylab.axis((0, len(self.frequencies()) + 1.0 - width, interval[0], interval[1]))
    pylab.xticks(x + width/2 - shift, self.labels())
    pylab.xlabel('frequency [Hz]')
    return handle


class TertsBandSpectrum(Spectrum):
  """ ISO 1/3-octave band spectrum class """
  def __init__(self, z = [LOWDB]*len(FTERTS)):
    if len(z) != len(FTERTS):
      raise Exception('trying to construct TertsBandSpectrum with nr of bands != ' + str(len(FTERTS)))
    Spectrum.__init__(self, f = FTERTS, z = z)

  def copy(self):
    return TertsBandSpectrum(self.amplitudes().copy())

  def aweights(self):
    return numpy.asarray(ATERTS)

  def cweights(self):
    return numpy.asarray(CTERTS)

  def labels(self):
    return LTERTS

  def octaveBandSpectrum(self):
    """ return the associated octave band spectrum """
    temp = [0.0]*len(FOCTAVE)
    z = self.amplitudes()
    for i in range(len(FOCTAVE)):
      temp[i] = sumdB(z[(FOFFSET+i*3):(FOFFSET+3+i*3)])
    return OctaveBandSpectrum(z = temp)

  def plot(self, m = 'cross', color = 'black', interval = None):
    """ plot the 1/3-octave band spectrum using a line with given marker type and color """
    x = numpy.arange(len(self.frequencies())) + 0.5
    if m == 'cross':
      pylab.plot(x, self.amplitudes(), linewidth = 1.0, color = color)
      pylab.plot(x, self.amplitudes(), linestyle = 'None', markersize = 9.0, color = color, **marker['square invisible'])
      handle = pylab.plot(x, self.amplitudes(), linestyle = 'None', color = color, **marker['cross'])
    else:
      handle = pylab.plot(x, self.amplitudes(), linewidth = 1.0, color = color, **marker[m])
    a = pylab.axis()
    if interval == None:
      pylab.axis((0.0, len(self.frequencies()), a[2], a[3]))
    else:
      pylab.axis((0.0, len(self.frequencies()), interval[0], interval[1]))
    pylab.xticks(x, self.labels())
    pylab.xlabel('frequency [Hz]')
    return handle


def AWeightOctaveBandSpectrum():
  """ return an octave band spectrum with the A-weight values """
  return OctaveBandSpectrum(z = AOCTAVE)

def CWeightOctaveBandSpectrum():
  """ return an octave band spectrum with the C-weight values """
  return OctaveBandSpectrum(z = COCTAVE)

def AWeightTertsBandSpectrum():
  """ return a 1/3-octave band spectrum with the A-weight values """
  return TertsBandSpectrum(ATERTS)

def CWeightTertsBandSpectrum():
  """ return a 1/3-octave band spectrum with the C-weight values """
  return TertsBandSpectrum(CTERTS)


#---------------------------------------------------------------------------------------------------
# Noise level time series
#---------------------------------------------------------------------------------------------------

class Histogram:
  """ class for histogram manipulation """
  def __init__(self, x, n):
    self._x = x # the bin labels
    self._n = n # the bin amounts

  def plot(self):
    """ plot the histogram """
    pylab.plot(self._x, self._n, linewidth = 1.0)


class TimeSeries(object):
  """ time series of noise levels """
  def __init__(self, z, dt = 1.0):
    """ initialize the time series with a series of values (list or numpy array) """
    object.__init__(self)
    self._dt = dt # time step (seconds)
    self._z = numpy.asarray(z).copy()

  def amplitudes(self):
    """ return the raw values of the timeseries, as a numpy array """
    return self._z

  def __len__(self):
    """ return the number of values in the timeseries """
    return len(self.amplitudes())

  def dt(self):
    """ return the timestep (s) """
    return self._dt

  def fs(self):
    """ return the sample rate (Hz) """
    return 1.0/(self.dt())

  def duration(self):
    """ return the duration (s) """
    return len(self)*self.dt()

  def times(self):
    """ return a numpy array with the time values """
    return numpy.arange(0.0, self.duration(), self.dt())

  def __iter__(self):
    """ return an iterator with the time series times and values """
    return iter(zip(self.times(), self.amplitudes().flat))

  def __str__(self):
    """ return a simple string representation of the timeseries """
    return '[' + ', '.join([('%.1f'%x) for x in self.amplitudes()]) + ']'

  def copy(self):
    """ return a (deep) copy of the time series """
    return TimeSeries(z = self.amplitudes(), dt = self.dt())

  def timeindex(self, t):
    """ return the time index for a given time t (in seconds) """
    return numpy.round(t/self.dt())

  def __getitem__(self, t):
    """ retrieve the value at the given time [s] (no bounds checking) """
    return self.amplitudes()[self.timeindex(t)]

  def __setitem__(self, t, value):
    """ set the value at the given time [s] (no bounds checking) """
    self.amplitudes()[self.timeindex(t)] = value

  def __iadd__(self, other):
    """ concatenation of timeseries or values + assignment """
    if type(other) == float:
      # add a single value at the end
      self._z = numpy.hstack([self.amplitudes(), other])
    else:
      # concatenation of timeseries
      if self.dt() != other.dt():
        raise 'impossible to concatenate 2 time series with different sample rate'
      self._z = numpy.hstack([self.amplitudes(), other.amplitudes()])
    return self

  def __add__(self, other):
    """ concatenation of timeseries or values """
    t = self.copy()
    t += other
    return t

  def addLevel(self, level):
    """ add a constant level to the timeseries values """
    self._z = plusdB(self._z, level)
    return self

  def addTimeseries(self, ts):
    """ add another timeseries to the current timeseries, sample by sample, in decibel """
    self._z = plusdB(self._z, ts.amplitudes())

  def save(self, filename, format = '%.4f'):
    """ save the timeseries to a textfile """
    f = open(filename, 'w')
    for v in self.amplitudes():
      f.write((format + '\n') % v)
    f.close()

  def view(self, start, duration):
    """ return a view (= reference) of a temporal section of the timeseries (numpy array) """
    n = len(self)
    iBegin = numpy.clip(self.timeindex(start), 0, n-1)
    iEnd   = numpy.clip(iBegin + self.timeindex(duration), iBegin+1, n)
    return self.amplitudes()[iBegin:iEnd]

  def section(self, start, duration):
    """ return a temporal section of the timeseries as a new timeseries (start and duration are given in seconds) """
    return TimeSeries(self.view(start,duration), dt = self.dt())

  def percentile(self, p):
    """ return percentile values with p a scalar or sequence of percentiles (in %) """
    y = numpy.sort(self.amplitudes())
    trim = 1.0 + (y.size - 1)*(100.0 - numpy.asarray(p))*0.01
    f = numpy.floor(trim).astype('int')
    c = numpy.ceil(trim).astype('int')
    d = (trim - f)
    return y[f-1]*d + y[c-1]*(1.0 - d)

  def statdist(self, r = (0,100)):
    """ calculate the statistical distribution (histogram) within the integer level range r = (min,max) """
    (minr,maxr) = r
    x = range(minr, maxr+1)
    n = maxr - minr + 1
    y = numpy.zeros(n)
    for v in self.amplitudes():
      b = utils.numeric.restrict(int(round(v)),r)
      y[b - minr] += 1
    return Histogram(x, y)

  def ncn(self, reference, threshold = 3.0, duration = 3.0):
    """ return the number of events that exceed the reference level (eg. LA50, LA95) with at least the
        threshold value (default 3 dBA), for at least the given duration in seconds (default 3 seconds)
    """
    z = numpy.zeros(len(self))
    z[numpy.where(self.amplitudes() >= (reference + threshold))[0]] = 1
    t = ''.join(map(lambda x: {0:'a',1:'b'}[x],z)).split('a')
    return len([p for p in t if len(p) >= duration*self.fs()])

  def minimum(self):
    """ return the minimum value of the timeseries """
    return numpy.min(self.amplitudes())

  def maximum(self):
    """ return the maximum value of the timeseries """
    return numpy.max(self.amplitudes())

  def average(self):
    """ returns the average value (of dB values) of the timeseries """
    return numpy.average(self.amplitudes())

  def stdev(self):
    """ returns the standard deviation of the timeseries dB values """
    return numpy.std(self.amplitudes())

  def leq(self):
    """ return L(A)eq value of the timeseries, asserting that it consists of dB(A) values """
    return averagedB(self.amplitudes())

  def sel(self):
    """ return (A)SEL value of the timeseries, asserting that it consists of dB(A) values """
    return todB(fromdB(sumdB(self.amplitudes()))*self.dt())

  def madmax(self, threshold = 60.0, drop = 5.0, droptime = 25.0, mindt = 3.0):
    """ calculate the noise events (and levels) according to the MadMax algorithm
        - threshold: minimum level for maxima
        - drop: minimum drop in level between maxima
        - droptime: maximum time to wait for drop in level
        - mindt: minimum time in between noise events
        return a list with (time, level) noise event tuples
    """
    times = self.dt() * numpy.arange(-1, len(self)+1)
    levels = numpy.hstack(([numpy.Inf], self.amplitudes(), [numpy.Inf]))
    candidates = []
    events = []
    for i in range(1, len(levels)-1):
      # check if a new maximum is encountered that is higher than the threshold
      if (levels[i-1] < levels[i]) and (levels[i] > levels[i+1]):
        if levels[i] >= threshold:
          candidates.append(i)
      # check which of the candidates can be removed
      for j in candidates:
        if ((times[i] - times[j]) > droptime):
          # it takes too long for the level to drop
          candidates.remove(j)
        elif (len(events) > 0) and ((times[j] - times[events[-1]]) < mindt):
          # the peak is too close to the previous peak
          candidates.remove(j)
      # check which of the candidates can be upgraded to events
      for j in candidates:
        if ((levels[j] - levels[i]) >= drop):
          events.append(j)
          candidates.remove(j)
    return [(times[i], levels[i]) for i in events]

  def plot(self, locs = None, interval = None, color = 'black', linewidth = 1.0):
    """ plot the timeseries """
    """ locs: the locations of the labels, in seconds """
    pylab.plot(range(len(self)), self.amplitudes(), color = color, linewidth = linewidth)
    # correcting x-axis labels
    if locs == None: # standard values
      locs, labels = pylab.xticks()
    else: # put user defined labels
      locs = numpy.asarray(locs)*self.fs()
    labels = map(str,numpy.asarray(locs)/self.fs())
    pylab.xticks(locs, labels)
    # correcting y-axis
    if interval != None:
      a = pylab.axis()
      pylab.axis((0.0, len(self), interval[0], interval[1]))
    pylab.xlabel('time [s]')

  # list of the indicators that can be calculated
  INDICATORLIST = ['LAeq', 'ASEL', 'LAmax', 'LA05', 'LA10', 'LA50', 'LA90', 'LA95', 'Ncn', 'TNI', 'NPL']

  def indicators(self):
    """ calculate a set of level time series indicators (assuming dBA values) """
    result = {}
    # energy-equivalent levels
    result['LAeq']  = self.leq()
    result['ASEL']  = self.sel()
    # percentile levels
    result['LAmax'] = self.maximum()
    result['LAmin'] = self.minimum()
    result['LA05']  = self.percentile(5.0)
    result['LA10']  = self.percentile(10.0)
    result['LA50']  = self.percentile(50.0)
    result['LA90']  = self.percentile(90.0)
    result['LA95']  = self.percentile(95.0)
    # noise event indicators
    result['Ncn']   = self.ncn(reference = result['LA50'])
    result['MM60']  = len(self.madmax())
    # hybrid indicators
    result['TNI']   = 4.0*(result['LA10'] - result['LA90']) + result['LA90'] - 30.0 # traffic noise index
    result['NPL']   = result['LAeq'] + 2.56 * self.stdev() # noise pollution level
    return result

  def basicIndicators(self):
    """ calculate a set of basic indicators (assuming dBA values) """
    result = {}
    result['LAeq']  = self.leq()
    result['LAmin'] = self.minimum()
    result['LAmax'] = self.maximum()
    result['LA10']  = self.percentile(10.0)
    result['LA50']  = self.percentile(50.0)
    result['LA90']  = self.percentile(90.0)
    result['sigma'] = self.stdev()
    return result


#---------------------------------------------------------------------------------------------------
# Test code
#---------------------------------------------------------------------------------------------------

if __name__ == '__main__':

  # test decibel calculus
  print 'todB'
  print todB(4000.0)
  print todB(numpy.asarray([[4000.0, -5000.0], [6000.0, 7000.0]]))
  print 'plusdB'
  print plusdB(0.0, 0.0)
  print plusdB(numpy.asarray([[0.0, 0.0], [0.0, 0.0]]), numpy.asarray([[1.0, 3.0], [10.0, 30.0]]))
  print 'averagedB'
  print averagedB([0.0, 0.0, 10.0, 0.0])
  print averagedB(numpy.asarray([[1.0, 2.0], [3.0, 4.0]]))
  print averagedB(numpy.asarray([[1.0, 2.0], [3.0, 4.0]]), axis=0)
  print averagedB(numpy.asarray([[1.0, 2.0], [3.0, 4.0]]), axis=1)
  print 'sumdB'
  print sumdB([0.0, 0.0, 10.0, 0.0])
  print sumdB(numpy.asarray([[1.0, 2.0], [3.0, 4.0]]))
  print sumdB(numpy.asarray([[1.0, 2.0], [3.0, 4.0]]), axis=0)
  print sumdB(numpy.asarray([[1.0, 2.0], [3.0, 4.0]]), axis=1)
  print 'parsedB'
  print parsedB('20.0')
  print parsedB('-150.0')
  print parsedB('-Inf')

  # test band spectrum arithmetic
  a = OctaveBandSpectrum([80., 82., 81., 79., 81., 82., 78., 76.])
  b = OctaveBandSpectrum()
  b[1000] = 90.0
  ab = a + b
  print 'a:    ', a
  print 'b:    ', b
  print 'a+b:  ', ab
  print isinstance(ab, OctaveBandSpectrum) # should be True
  print 'a/2.0:', a/2.0
  print 'a*2.0:', a*2.0
  c = b.copy()
  b[1000] = 123.0
  print 'b:    ', b
  print 'c:    ', c
  for f, v in a:
    print str(f) + ' Hz: ' + str(v)

  # test 1/3-octave band to octave band conversion
  t = TertsBandSpectrum()
  print t.octaveBandSpectrum()

  # test plotting spectra
  a = []
  a.append(OctaveBandSpectrum([65., 72., 81., 79., 88., 82., 78., 66.]))
  a.append(TertsBandSpectrum([ 5.0, 20.0, 24.0, 34.0, 24.0, 43.0, 52.0, 62.0, 54.0, 58.0, 61.0, 52.0, 39.0, 43.0, 48.0, 49.0,
                              53.0, 59.0, 62.0, 69.0, 61.0, 52.0, 48.0, 43.0, 48.0, 41.0, 39.0, 32.0, 24.0, 15.0, 10.0]))
  for x in a:
    pylab.figure()
    x.plot()
  pylab.figure()
  a[1].plot(m = 'cross', color = 'green')

  try:
    pylab.show()
  except:
    pass
