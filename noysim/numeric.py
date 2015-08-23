# Noysim -- Noise simulation tools for Aimsun.
# Copyright (c) 2010-2011 by Bert De Coensel, Ghent University & Griffith University.
#
# Numeric and random number generation methods and functions

import random
import math

import numpy
import scipy.special
import scipy.stats
import pylab


#---------------------------------------------------------------------------------------------------
# Normal and skewed normal distribution functions
#---------------------------------------------------------------------------------------------------

def phi(x):
  """ standard normal pdf """
  return (1.0/numpy.sqrt(2.0*numpy.pi))*numpy.exp(-(x**2)/2.0)

def skew(x, eta = 0.0, alpha = 1.0, kappa = 0.5):
  """ skewed normal pdf """
  y = -(1.0/kappa)*numpy.log(1.0 - kappa*(x-eta)/alpha)
  return phi(y)/(alpha - kappa*(x-eta))

def PHI(x):
  """ standard normal cdf """
  return 0.5 * (1.0 + scipy.special.erf(x/numpy.sqrt(2.0)))

def SKEW(x, eta = 0.0, alpha = 1.0, kappa = 0.5):
  """ skewed normal cdf """
  y = -(1.0/kappa)*numpy.log(1.0 - kappa*(x-eta)/alpha)
  return PHI(y)

def PHIinv(x):
  """ standard normal inverse cdf """
  return numpy.sqrt(2.0)*scipy.special.erfinv(2.0*x - 1.0)

def SKEWinv(x, eta = 0.0, alpha = 1.0, kappa = 0.5):
  """ skewed normal inverse cdf """
  return eta + alpha*(1.0 - numpy.exp(-kappa*PHIinv(x)))/kappa


#---------------------------------------------------------------------------------------------------
# Basic random number generation
#---------------------------------------------------------------------------------------------------

def seed(value = None):
  """ seed the random number generators """
  if value != None:
    random.seed(value)
    numpy.random.seed(value)


def urand(left = -1.0, right = 1.0):
  """ return a floating point random number, uniformly distributed between left and right """
  return left + random.random()*(right - left)


def logrand(left, right):
  """ return a floating point random number, logarithmically distributed between left and right (small values are favored) """
  assert (left > 0.0) and (right > 0.0)
  return numpy.exp(numpy.log(left) + random.random()*(numpy.log(right) - numpy.log(left)))


def rouletterand(partition):
  """ return an integer according to roulette wheel selection with given partition of 100%,
      e.g. partition = [33.3, 66.6] will return 0, 1 or 2 with equal chance
  """
  (r, v) = (random.random()*100.0, 0)
  for i in range(len(partition)):
    if r > partition[i]:
      v = i + 1
  return v


def randskewn(eta = 0.0, alpha = 1.0, kappa = 0.5):
  """ return a random number sampled from a skewed normal distribution (kappa = skew factor) """
  if (abs(kappa) < 1e-6):
    # assume a normal gaussian distribution
    return eta + alpha*numpy.random.randn()
  else:
    return SKEWinv(numpy.random.rand(), eta = eta, alpha = alpha, kappa = kappa)


#---------------------------------------------------------------------------------------------------
# Selection of random elements
#---------------------------------------------------------------------------------------------------

def choice(outcomes):
  """ return a random element of the given sequence (roulette wheel selection)
      outcome can be a dict {possibleoutcome: chance (in%), possibleoutcome: chance (in%),...}, or a list, in which each element has equal chance
  """
  # check for list
  if type(outcomes) is list:
   return random.choice(outcomes)
  # calculate cumulative chances
  (cumul, partition, choices) = (0.0, [], [])
  for outcome, percentage in outcomes.iteritems():
    cumul += percentage
    partition.append(cumul)
    choices.append(outcome)
  # calculate outcome
  return choices[rouletterand(partition)]


#---------------------------------------------------------------------------------------------------
# Emission correction generators
#---------------------------------------------------------------------------------------------------

class CorrectionGenerator(object):
  """ base class for generating random emission corrections """
  def __init__(self):
    object.__init__(self)

  def generate(self):
    """ generate a correction in dB according to a predefined distribution """
    raise NotImplementedError

  def plot(self, n = 20000, xlimits = (-20.0, 20.0), dx = 1.0):
    """ generate a plot of the distribution of generated values """
    v = [self.generate() for i in range(n)]
    bins = numpy.arange(xlimits[0]-(dx/2.0), xlimits[1]+(dx/2.0), dx)
    x = (bins[1:] + bins[:-1])/2.0
    (hist, edges) = numpy.histogram(v, bins=bins, normed=True)
    pylab.plot(x, hist, color='r', linewidth=2)


class TabulatedCorrectionGenerator(CorrectionGenerator):
  """ generate samples from a given tabulated distribution """
  def __init__(self, values, dx = 1.0, zeropoint = 'meanEn'):
    self._values = numpy.asarray(values, dtype=float) # array with counts in bins with width dx
    self._n = len(values)
    self._dx = dx
    # calculate cumulative distribution
    self._cumdist = 100.0*numpy.cumsum(self._values/numpy.sum(self._values))
    self._partition = self._cumdist[:-1]
    # estimate mean/median value and adjust x-range to have mean/median at zero
    self._xvalues = numpy.arange(0, self._n, self._dx, dtype=float)
    self._median = self._xvalues[numpy.where(self._cumdist >= 50.0)[0][0]]
    self._meandB = numpy.sum(self._values * self._xvalues)/numpy.sum(self._values)
    self._meanEn = 10.0*numpy.log10(numpy.sum(self._values * (10**(self._xvalues/10.0)))/numpy.sum(self._values))
    self._xvalues -= {'median': self._median, 'meandB': self._meandB, 'meanEn': self._meanEn}[zeropoint]
    #print 'median:', self._median
    #print 'meandB:', self._meandB
    #print 'meanEn:', self._meanEn

  def generate(self):
    # select random bin
    result = self._xvalues[rouletterand(self._partition)]
    # assume that corrections are uniformily distributed within a bin
    result += urand(left = -self._dx/2.0, right = self._dx/2.0)
    return result

  def plotData(self):
    """ plot the original data as a bar chart """
    y = self._values/numpy.sum(self._values)
    pylab.bar(self._xvalues - (self._dx/2.0), y)


class NormalCorrectionGenerator(CorrectionGenerator):
  """ generate samples with a normal distribution around zero """
  def __init__(self, stdev = 1.0):
    CorrectionGenerator.__init__(self)
    self._stdev = stdev # standard deviation

  def generate(self):
    return self._stdev * numpy.random.randn()


class SkewedNormalCorrectionGenerator(CorrectionGenerator):
  """ generate samples with a skewed normal distribution, with median value zero """
  def __init__(self, stdev = 1.0, skew = 0.0):
    CorrectionGenerator.__init__(self)
    self._alpha = stdev
    self._kappa = skew

  def generate(self):
    return randskewn(eta = 0.0, alpha = self._alpha, kappa = self._kappa)


class DistributionCorrectionGenerator(CorrectionGenerator):
  """ generate samples according to a named distribution in scipy.stats """
  def __init__(self, name, invert = False, *args, **kwargs):
    CorrectionGenerator.__init__(self)
    self._invert = {True: -1.0, False: 1.0}[invert] # if True, the inverse along the x-axis is returned
    self._generator = scipy.stats.__dict__[name](*args, **kwargs)
    self._median = self._generator.median()

  def generate(self):
    return self._invert*(self._generator.rvs() - self._median)


#---------------------------------------------------------------------------------------------------
# Test code
#---------------------------------------------------------------------------------------------------

if __name__ == '__main__':

  # test skewed normal random number generation
  if 0:
    n = 20000
    eta = 2.0
    alpha = 1.5
    kappa = 0.5
    xlimits = (-5.0, 5.0)
    xvalues = numpy.arange(xlimits[0], xlimits[1], 0.01)
    a = [randskewn(eta=eta, alpha=alpha, kappa=kappa) for i in range(n)]
    b = skew(xvalues, eta=eta, alpha=alpha, kappa=kappa)
    pylab.figure()
    pylab.hist(a, bins = 50, range = (-5.0, 5.0), normed = True)
    pylab.plot(xvalues, b, color='r', linewidth=2)

  # test emission correction generators
  if 1:
    pylab.figure()
    #NormalCorrectionGenerator(stdev = 5.0).plot()
    #SkewedNormalCorrectionGenerator(stdev = 4.2, skew = 0.06).plot()
    #DistributionCorrectionGenerator('gamma', True, 1.5, scale = 7.0).plot()
    # tabulated distribution
    values = numpy.asarray([89, 188, 207, 386, 438, 437, 556, 596, 821, 797, 905, 1099, 1369, 1567, 1727, 2184, 2674, 3426, 3502, 3522, 3123, 2455, 1696, 1238, 832, 468, 362, 286, 195, 126, 74, 77, 32, 34, 14, 14, 11, 6, 6, 4, 5, 6, 3, 2, 5, 8, 0, 0, 0, 0, 0], dtype=float)
    TabulatedCorrectionGenerator(values = values, dx = 1.0).plot()

  try:
    pylab.show()
  except:
    pass
