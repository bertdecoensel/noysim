# Noysim -- Noise simulation tools for Aimsun.
# Copyright (c) 2010-2016 by Bert De Coensel, Ghent University & Griffith University.
#
# Generalized noise event detector

import os
import sys

import numpy
import pylab

from acoustics import TimeSeries


# default parameters
BACKGROUND = 35.0 # indoor background level [dB(A)]
INSULATIONS = {'NO': 0.0, 'OP': 5.0, 'CL': 25.0} # building insulation levels [dB(A)]: none, open or closed window


#---------------------------------------------------------------------------------------------------
# Utility functions
#---------------------------------------------------------------------------------------------------

def createIndoorTimeseries(ts, insulation):
  """ Create an indoor timeseries based on the given outdoor timeseries and insulation """
  result = ts.copy()
  result.correct(-INSULATIONS[insulation])
  result.addLevel(BACKGROUND)
  return result


#---------------------------------------------------------------------------------------------------
# Noise event class
#---------------------------------------------------------------------------------------------------

class NoiseEvent(object):
  """ Class representing a single noise event """

  def __init__(self, t1, t2, tmax, Lmax):
    """ Create a noise event """
    object.__init__(self)
    self.t1 = t1
    self.t2 = t2
    self.tmax = tmax
    self.Lmax = Lmax

  def __str__(self):
    """ Return a string representation of the event """
    return '[t1=%.1fs, t2=%.1fs, tmax=%.1fs, Lmax=%.1fs]' % (self.t1, self.t2, self.tmax, self.Lmax)

  def duration(self):
    """ Return the duration of the noise event (in s) """
    return self.t2 - self.t1

  def merge(self, other):
    """ Merge another event with the current event """
    self.t1 = min(self.t1, other.t1)
    self.t2 = max(self.t2, other.t2)
    if other.Lmax > self.Lmax:
      self.tmax = other.tmax
      self.Lmax = other.Lmax


#---------------------------------------------------------------------------------------------------
# Generalized event detector
#---------------------------------------------------------------------------------------------------

class EventDetector(object):
  """ Class that detects events in a timeseries
      The class provides a generalized state machine implementation
  """

  def __init__(self, Lbeta, E, Lomega=None, minTauG=0.0, minTauE=0.0, maxTauE=numpy.Inf, background=BACKGROUND, insulation='NO'):
    """ Create the event detector """
    object.__init__(self)
    # event detection parameters
    self.Lbeta = Lbeta # can be a value such as 55.0 dB(A), or a string (either 'LEQ', 'L50' or 'L90')
    self.Lomega = Lomega # event end level (default None equals Lalpha)
    self.E = E
    self.minTauG = minTauG
    self.minTauE = minTauE
    self.maxTauE = maxTauE
    self.insulation = insulation # building insulation label
    self.background = background # (indoor) background level [dB(A)]
    self.events = None

  def label(self):
    """ Return the label of the event detector """
    if isinstance(self.Lbeta, str):
      result = self.Lbeta
    else:
      result = 'T%.2d' % int(round(self.Lbeta))
    result += 'E%.2d' % int(round(self.E))
    result += 'G%.2d' % int(round(self.minTauG))
    result += self.insulation
    return result

  def __str__(self):
    """ Return a string description of the event detector parameters """
    unit = {True: '', False: ' dB(A)'}[isinstance(self.Lbeta, str)]
    values = (self.label(), str(self.Lbeta), unit, self.E, self.minTauG, INSULATIONS[self.insulation])
    return '%s: $L_\\beta$ = %s%s, $E$ = %.1f dB(A), $\\tau_G$ = %.1fs, insulation %.1f dB(A)' % values

  # event detection state machine methods

  def step(self, t, level):
    """ Step the state machine with a single time and level, and return a (candidate) NoiseEvent
        object if an event has occurred, or None otherwise
    """
    if self.t1 == None:
      # currently not in an event
      if level >= self.Lalpha:
        # the event start threshold is exceeded, so initialize the event state
        self.t1, self.tmax, self.Lmax = (t, t, level)
      else:
        return None
    else:
      # currently in an event
      # check if the maximum level has to be updated
      if level > self.Lmax:
        self.tmax, self.Lmax = (t, level)
      # check if the stop threshold is reached
      if level < self.Lomega:
        event = NoiseEvent(t1=self.t1, t2=t, tmax=self.tmax, Lmax=self.Lmax)
        self.t1, self.tmax, self.Lmax = (None, None, None)
        return event

  def stop(self, t):
    """ Purge the state machine when the end of the timeseries is reached """
    if self.t1 != None:
      event = NoiseEvent(t1=self.t1, t2=t, tmax=self.tmax, Lmax=self.Lmax)
      self.t1, self.tmax, self.Lmax = (None, None, None)
      return event
    else:
      return None

  def __call__(self, ts):
    """ Run the event detector for a timeseries and return a list of NoiseEvent objects """
    # initialize state machine parameters
    self.t1, self.tmax, self.Lmax, self.events = (None, None, None, [])
    # create indoor time series
    self.tsIndoor = createIndoorTimeseries(ts=ts, insulation=self.insulation)
    # initialize the event detector parameters
    self.indicators = self.tsIndoor.basicIndicators()
    if isinstance(self.Lbeta, str):
      self.Lalpha = self.indicators[{'LEQ': 'LAeq', 'L50': 'LA50', 'L90': 'LA90'}[self.Lbeta]] + self.E
    else:
      self.Lalpha = self.Lbeta + self.E
    if self.Lomega == None:
      self.Lomega = self.Lalpha
    # generate a list of event candidates
    candidates = []
    for t, level in self.tsIndoor:
      result = self.step(t=t, level=level)
      if result != None:
        candidates.append(result)
    result = self.stop(t=t)
    if result != None:
      candidates.append(result)
    # filter the event candidate list for time gaps, and merge events if necessary
    for candidate in candidates:
      if len(self.events) == 0:
        # first event, so no problem with time gap
        self.events.append(candidate)
      else:
        if candidate.t1 - self.events[-1].t2 < self.minTauG:
          self.events[-1].merge(candidate)
        else:
          self.events.append(candidate)
    # filter the event candidate list for event durations
    self.events = [event for event in self.events if event.duration() >= self.minTauE]
    self.events = [event for event in self.events if event.duration() <= self.maxTauE]
    return self

  # event metrics (assumes the detector has been called already for a timeseries)

  def numberOfEvents(self):
    """ Return the number of noise events detected """
    if self.events == None:
      raise Exception('event detector has not been called for a timeseries')
    return len(self.events)

  def totalEventDuration(self):
    """ Return the total duration of all events """
    if self.events == None:
      raise Exception('event detector has not been called for a timeseries')
    return sum([event.duration() for event in self.events])


#---------------------------------------------------------------------------------------------------
# Factory function
#---------------------------------------------------------------------------------------------------

def createEventDetector(label):
  """ Create an EventDetector object based on the label; example of labels are
      'L50E03G10OP' or 'T65E05G00CL'
  """
  if len(label) != 11:
    raise Exception('invalid event detector label: "%s"' % label)
  if label[0] == 'L':
    Lbeta = label[:3] # level provided as string
  else:
    Lbeta = float(label[1:3]) # level provided as number
  E = float(label[4:6])
  minTauG = float(label[7:9])
  insulation = label[-2:]
  return EventDetector(Lbeta=Lbeta, E=E, minTauG=minTauG, insulation=insulation)


#---------------------------------------------------------------------------------------------------
# Test code
#---------------------------------------------------------------------------------------------------

if __name__ == '__main__':

  # test EventDetector factory method
  labels = ['L50E03G10OP', 'T65E05G00CL']
  for label in labels:
    detector = createEventDetector(label=label)
    print label, detector.label(), (label == detector.label())
    print str(detector)
