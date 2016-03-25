# Noysim -- Noise simulation tools for Aimsun.
# Copyright (c) 2010-2011 by Bert De Coensel, Ghent University & Griffith University.
#
# Simple traffic simulation model (straight single-lane road, free flow conditions)

import math
import random

import numpy
import pylab

from numeric import choice
from geo import Point, Direction
from acoustics import sumdB, TimeSeries
from emission import QLDCar, QLDLightTruck, QLDBDouble, QLDMotorcycle, Roadsurface, ImagineModel, SkewedNormalImagineCorrectionModel, DistributionImagineCorrectionModel
from propagation import Receiver, ISO9613Environment, ISO9613Model


MINRATE = 0.01


#---------------------------------------------------------------------------------------------------
# Headway distributions
#---------------------------------------------------------------------------------------------------

class HeadwayDistribution(object):
  """ class that generates signals for loading vehicles onto the network, using a given headway distribution over time
      a number of distributions can be found in GartnerTRB97
  """
  def __init__(self, dt):
    object.__init__(self)
    self._dt = dt # timestep of the simulation (in seconds)
    self._h = 0.0 # current headway (in seconds)
    self._history = []

  def inverseCumulativeProbability(self, p):
    """ return the inverse cumulative probability of the distribution, to be implemented in specialized subclasses """
    raise NotImplementedError

  def __call__(self):
    """ return True when a vehicle has to generated """
    self._h -= self._dt
    if self._h <= 0.0:
      self._h = self.inverseCumulativeProbability(numpy.random.random())
      self._history.append(self._h)
      return True
    else:
      return False

  def plot(self, bins = 20):
    """ plot a histogram of the generated headways """
    if len(self._history) > 0:
      pylab.hist(self._history, bins = bins)


class RegularDistribution(HeadwayDistribution):
  """ return passbys at regular time intervals (constant headway) """
  def __init__(self, dt, rate):
    HeadwayDistribution.__init__(self, dt)
    self._period = 3600.0/rate

  def inverseCumulativeProbability(self, p):
    return self._period # constant headway


class QuasiRegularDistribution(HeadwayDistribution):
  """ return passbys at quasi regular time intervals, with deviation from regularity (fraction of period) """
  def __init__(self, dt, rate, deviation = 0.25):
    HeadwayDistribution.__init__(self, dt)
    self._period = 3600.0/rate
    self._deviation = deviation
    self._a = self._period * (1.0 - self._deviation)
    self._b = 2.0 * self._period * self._deviation

  def inverseCumulativeProbability(self, p):
    return self._a + self._b * p # headway between bounds


class NegativeExponentialDistribution(HeadwayDistribution):
  """ return passbys with a negative exponential distribution (Poisson process) """
  def __init__(self, dt, rate):
    HeadwayDistribution.__init__(self, dt)
    self._q = rate/3600.0 # rate = #vehicles passing by per hour, q = #vehicles passing by per second

  def inverseCumulativeProbability(self, p):
    # cumulative probability: p = 1 - exp(-q*t)
    return -numpy.log(1.0-p)/self._q


class DisplacedNegativeExponentialDistribution(HeadwayDistribution):
  """ return passbys with a displaced negative exponential distribution """
  def __init__(self, dt, rate, hmin = 1.0):
    HeadwayDistribution.__init__(self, dt)
    q = rate/3600.0
    self._hmin = hmin # minimum headway (in seconds)
    self._lambda = q/(1.0-q*hmin)

  def inverseCumulativeProbability(self, p):
    # cumulative probability: p = 1 - exp[-lambda*(t-hmin)]
    return self._hmin - numpy.log(1.0-p)/self._lambda


class CowanM3Distribution(HeadwayDistribution):
  """ return passbys with a Cowan M3 dichotomized distribution """
  def __init__(self, dt, rate, hmin = 1.0):
    HeadwayDistribution.__init__(self, dt)
    q = rate/3600.0
    self._hmin = hmin # minimum headway (in seconds)
    self._alpha = numpy.exp(-7.5*q) # approximation as in GartnerTRB97 (page 8-8)
    self._lambda = (q*self._alpha)/(1.0-q*hmin)

  def inverseCumulativeProbability(self, p):
    # cumulative probability: p = 1 - alpha*exp[-lambda*(t-hmin)]
    if (p < (1.0 - self._alpha)):
      return self._hmin
    else:
      return self._hmin - numpy.log((1.0-p)/self._alpha)/self._lambda


#---------------------------------------------------------------------------------------------------
# Creation of vehicles
#---------------------------------------------------------------------------------------------------

class VehicleFactory(object):
  """ class for creating individual vehicles """
  def __init__(self, fleet, position, direction, speed, acceleration):
    object.__init__(self)
    self._fleet = fleet # vehicle fleet, as a dictionary {vClass: proportion(in%)}
    self._position = position # location where the vehicles should be created
    self._direction = direction # direction the vehicles are travelling
    self._speed = speed # speed of the vehicles
    self._acceleration = acceleration # acceleration of the vehicles
    self._idCount = 0

  def create(self):
    """ create a new vehicle """
    self._idCount += 1
    cls = choice(self._fleet)
    return cls(vid = self._idCount, position = self._position.copy(), direction = self._direction.copy(), speed = self._speed, acceleration = self._acceleration)


#---------------------------------------------------------------------------------------------------
# Traffic simulation
#---------------------------------------------------------------------------------------------------

class TrafficSimulation(object):
  """ class for running a simple traffic simulation:
      - a straight single-lane network along the x-axis is considered
      - free flow traffic conditions are considered, with all vehicles travelling at the limit speed
      - both light duty (class 1) and heavy duty (class 3) vehicle types are considered
  """
  def __init__(self, vlimit, fleet, dist, xmin = -1000.0, xmax = 1000.0, seed = 0):
    self._vlimit = vlimit # limit vehicle speed in km/h
    self._fleet = fleet # the vehicle fleet (proportion of each type)
    self._dist = dist # temporal distribution of vehicle pass-bys
    self._xmin = xmin # left boundary of network
    self._xmax = xmax # right boundary of network
    self._dt = self._dist._dt
    self._dx = (self._vlimit/3.6) * self._dt # distance travelled by a vehicle over the timestep (all travel at the limit speed)
    self._seed = seed

  def clear(self):
    """ clear the simulation """
    self._t = 0.0
    self._passbys = [] # list with vehicle passbys (at the origin)
    self._passbytimes = {1: [], 3: []}
    self._history = [] # history of vehicles at each timestep
    self._factory = VehicleFactory(fleet=self._fleet, position=Point(self._xmin, 0.0, 0.0), direction=Direction(bearing=0.0),
                                   speed=self._vlimit, acceleration=0.0)

  def currentVehicles(self):
    """ return a list of the vehicles currently in the network """
    if len(self._history) == 0:
      return []
    else:
      return self._history[-1]

  def step(self, warmup):
    """ advance the simulation with a single timestep """
    vehicles = []
    # move the vehicles that are currently in the network
    np = 0 # number of passbys
    for v in self.currentVehicles():
      newv = v.copy()
      newv.move(dx=self._dx)
      newv.passby = False
      x = newv.position().x
      isPassby = ((-self._dx/2.0 < x) and (x <= self._dx/2.0))
      if (isPassby and self._t >= warmup):
        newv.passby = True
        self._passbytimes[newv._cat].append(self._t - warmup)
      np += int(isPassby)
      if (newv.position().x <= self._xmax):
        vehicles.append(newv)
    self._passbys.append(np)
    self._t += self._dt
    # add a new vehicle if needed
    if self._dist():
      vehicles.append(self._factory.create())
      vehicles[-1].passby = False
    self._history.append(vehicles)

  def run(self, warmup = 0.0, duration = 3600.0, verbose = False):
    """ run the simulation for the specified duration, and return list with vehicles and with passbys """
    self.clear()
    numpy.random.seed(self._seed)
    # calculate number of timesteps
    n1 = int(round(warmup/self._dt))
    n2 = int(round(duration/self._dt))
    ntot = n1 + n2
    # perform actual simulation
    for i in range(ntot):
      self.step(warmup=warmup)
      if verbose:
        print 'performing traffic simulation: t = %.1f/%.1f\r' % (self._t, warmup + duration),
    if verbose:
      print
    # return results (number of passbys at origin, history)
    return (self._passbytimes, self._history[n1:])


#---------------------------------------------------------------------------------------------------
# Construction of sound level time series
#---------------------------------------------------------------------------------------------------

def levelTimeSeries(vhist, dt, emodel, road, pmodel, receivers, verbose=False):
  """ calculate a time series of levels based on the given traffic simulation history """
  duration = len(vhist)*dt
  elevels = {}
  # calculate lists of sources
  t = 0.0
  sourcesList = []
  for vehicles in vhist:
    sources = []
    t += dt
    if verbose:
      print 'performing emission calculation: t = %.1f/%.1f\r' % (t, duration),
    for vehicle in vehicles:
      sList = emodel.sources(vehicle=vehicle, road=road)
      if vehicle.passby == True:
        # save total A-weighted emission level of vehicle during passby
        elevel = sumdB([source.emission.laeq() for source in sList])
        vcat = vehicle._cat
        if vcat in elevels:
          elevels[vcat].append(elevel)
        else:
          elevels[vcat] = [elevel]
      sources += sList
    sourcesList.append(sources)
  if verbose:
    print
  # calculate immission at receivers
  t = 0.0
  levelsList = []
  for sources in sourcesList:
    t += dt
    if verbose:
      print 'performing propagation calculation: t = %.1f/%.1f\r' % (t, duration),
    immi = [pmodel.totalImmission(sources, receiver) for receiver in receivers]
    levelsList.append([spectrum.laeq() for spectrum in immi])
  if verbose:
    print
  # construct timeseries
  return (elevels, [TimeSeries(z, dt) for z in zip(*levelsList)])


def simulateLevelHistory(# general simulation parameters
                         warmup = 120.0, # traffic build up time, 120 seconds should be ok in most cases
                         duration = 3600.0, # duration of the simulation (in seconds)
                         dt = 0.125, # simulation timestep
                         xlimits = (-1000.0, 1000.0), # network limits along x-axis
                         seed = 0, # seed for the simulation run
                         nsims = 1, # number of traffic simulations to run (the best one is kept)
                         verbose = False, # if True, progress information is printed
                         # traffic parameters
                         rate = 100, # traffic flow (vehicles/h)
                         pheavy = 10.0, # percentage of heavy vehicles
                         vlimit = 50.0, # limit speed (km/h)
                         hmin = 1.2, # minimum headway (seconds)
                         # modified Imagine emission model parameters
                         surface = ('REF', 20.0, 11.0, 2.0, False, 0.08), # road surface parameters
                         emodelname = 'Imagine', # name of the emission model to use
                         stdev = (0.0, 0.0, 0.0, 0.0, 0.0), # standard deviations of emissions for 5 Imagine vehicle categories
                         skew = (0.0, 0.0, 0.0, 0.0, 0.0), # skewness of emissions for 5 Imagine vehicle categories
                         ecorr = (True, False, False, False, False, True, False), # model correction flags
                         fleetcorr = (19.0, 187.0, 10.5, (1.0,35.0), False), # fleet corrections
                         # ISO 9613 propagation model parameters
                         G = (0.0, 0.0, 0.0), # ground effect
                         ptr = (101325.0, 20.0, 70.0), # air pressure, temperature and relative humidity
                         pcorr = (True, True, True, True), # model corrections (geometric divergence, atmospheric absorption, ground effect and source directivity)
                         # receiver parameters
                         distances = (7.5, 15.0, 30.0, 60.0), # distances to the road
                         h = 1.2): # receiver height
  """ simulate level time series with default values for the different models
      assuming that the simulation model is a straight single-lane road along the x-axis
  """
  # perform traffic simulation
  fleet = {QLDCar: (100.0 - pheavy), QLDBDouble: pheavy} # pheavy = percentage heavy vehicles
  expectRate = numpy.asarray([rate*(100.0-pheavy)*duration/360000.0, rate*pheavy*duration/360000.0])
  expectRateStr = '[' + ' '.join([('%.1f' % x) for x in expectRate]) + ']'
  cats = [key().cat() for key in fleet]
  dist = DisplacedNegativeExponentialDistribution(dt=dt, rate=rate, hmin=hmin)
  #dist = CowanM3Distribution(dt = dt, rate = rate, hmin = hmin)
  passbytimes = None
  vhist = None
  rateError = numpy.inf
  for i in range(nsims):
    tsim = TrafficSimulation(vlimit=vlimit, fleet=fleet, dist=dist, xmin=xlimits[0], xmax=xlimits[1], seed=(seed+i))
    (passbytimesTemp, vhistTemp) = tsim.run(warmup=warmup, duration=duration, verbose=verbose)
    realRate = numpy.asarray([len(passbytimesTemp[1]), len(passbytimesTemp[3])])
    rateErrorTemp = (numpy.abs(realRate - expectRate)/expectRate)**2
    rateErrorTemp = numpy.sum([x for x in rateErrorTemp if not numpy.isnan(x)])
    print 'expect rate: %s, real rate: %s, rate error: %.4f' % (expectRateStr, str(realRate), rateErrorTemp)
    if rateErrorTemp < rateError:
      rateError = rateErrorTemp
      passbytimes = passbytimesTemp
      vhist = vhistTemp
  # construct emission model
  road = Roadsurface(cat=surface[0], temperature=surface[1], chipsize=surface[2], age=surface[3], wet=surface[4], tc=surface[5])
  if emodelname.lower() == 'imagine':
    emodel = ImagineModel()
  elif emodelname.lower() == 'imagine+skewednormal':
    emodel = SkewedNormalImagineCorrectionModel(stdev = stdev, skew = skew, seed = seed)
  elif emodelname.lower() == 'imagine+distribution':
    emodel = DistributionImagineCorrectionModel(seed = seed)
  else:
    raise 'unknown emission model: %s' % emodelname
  emodel.correction['acceleration'] = ecorr[0]
  emodel.correction['gradient'] = ecorr[1]
  emodel.correction['temperature'] = ecorr[2]
  emodel.correction['surface'] = ecorr[3]
  emodel.correction['wetness'] = ecorr[4]
  emodel.correction['axles'] = ecorr[5]
  emodel.correction['fleet'] = ecorr[6]
  emodel.fleet['diesel'] = fleetcorr[0]
  emodel.fleet['tirewidth'] = fleetcorr[1]
  emodel.fleet['vans'] = fleetcorr[2]
  emodel.fleet['iress'] = fleetcorr[3]
  emodel.fleet['studs'] = fleetcorr[4]
  # construct propagation model
  environment = ISO9613Environment(G = G, p = ptr[0], t = ptr[1], r = ptr[2])
  pmodel = ISO9613Model(environment = environment)
  pmodel.correction['geometricDivergence'] = pcorr[0]
  pmodel.correction['atmosphericAbsorption'] = pcorr[1]
  pmodel.correction['groundEffect'] = pcorr[2]
  pmodel.correction['sourceDirectivity'] = pcorr[3]
  # construct list of receivers
  receivers = [Receiver(position = Point(0.0, -d, h)) for d in distances]
  # perform emission and propagation calculations
  elevels, tsList = levelTimeSeries(vhist=vhist, dt=dt, emodel=emodel, road=road, pmodel=pmodel, receivers=receivers, verbose=verbose)
  # return (number of passages, timeseries at different receivers)
  return (passbytimes, elevels, tsList)


#---------------------------------------------------------------------------------------------------
# Test code
#---------------------------------------------------------------------------------------------------

if __name__ == '__main__':

  # test headway distributions
  if 1:
    dt = 0.250
    rate = 400
    #dist = RegularDistribution(dt = dt, rate = rate)
    #dist = QuasiRegularDistribution(dt = dt, rate = rate, deviation = 0.25)
    #dist = NegativeExponentialDistribution(dt = dt, rate = rate)
    #dist = DisplacedNegativeExponentialDistribution(dt = dt, rate = rate, hmin = 3.0)
    dist = CowanM3Distribution(dt = dt, rate = rate, hmin = 3.0)
    for i in range(50000):
      dist()
    pylab.figure()
    dist.plot()

  # test running a traffic simulation
  if 1:
    fleet = {QLDCar: 100.0}
    dist = QuasiRegularDistribution(dt = 0.5, rate = 500.0)
    tsim = TrafficSimulation(vlimit = 50.0, fleet = fleet, dist = dist, seed = 0)
    (passbytimes, vhist) = tsim.run(warmup = 300.0, duration = 3600.0, verbose = True)
    print 'number of vehicle passbys:'
    for key, value in passbytimes.iteritems():
      print ' -> category %d: %d' % (key, len(value))
    print 'number of timesteps:', len(vhist)
    print 'max #vehicles at any time in the network:', max([len(x) for x in vhist])

  # test relation between demand and actual flow
  if 1:
    counts = []
    for seed in range(10):
      print 'running simulation %d...' % seed
      fleet = {QLDCar: 100.0}
      #dist = QuasiRegularDistribution(dt = 0.5, rate = 200.0)
      dist = CowanM3Distribution(dt = 0.5, rate = 200, hmin = 2.0)
      tsim = TrafficSimulation(vlimit = 50.0, fleet = fleet, dist = dist, seed = seed)
      (passbytimes, vhist) = tsim.run(warmup = 300.0, duration = 3600.0, verbose = False)
      counts.append(sum([len(x) for x in passbytimes.values()]))
    print counts

  # run level history simulation
  if 1:
    # general simulation parameters
    duration = 600.0
    dt = 1.0
    seed = 0
    verbose = True
    # traffic parameters
    rate = 500.0
    pheavy = 10.0
    vlimit = 60.0
    distances = (15.0, )
    # run simulation
    ts = []
    for emodelname, stdev, skew in [('Imagine', (0.0, 0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 0.0, 0.0)),
                                    ('Imagine+SkewedNormal', (1.0, 1.0, 1.0, 1.0, 1.0), (0.0, 0.0, 0.0, 0.0, 0.0)),
                                    ('Imagine+Distribution', (0.0, 0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 0.0, 0.0))]:
      print '*** Simulation with %s emission model ***' % emodelname
      (passbytimes, elevels, tsList) = simulateLevelHistory(duration=duration, dt=dt, seed=seed, verbose=verbose,
                                                            rate=rate, pheavy=pheavy, vlimit=vlimit,
                                                            emodelname=emodelname, stdev=stdev, skew=skew, distances=distances)
      print 'number of vehicle passbys:'
      for key, value in passbytimes.iteritems():
        print ' -> category %d: %d' % (key, len(value))
      ts.append(tsList[0])
      indicators = tsList[0].indicators()
      # print noise indicators
      print 'LAeq:', indicators['LAeq']
      print 'LAmax:', indicators['LAmax']
      print 'LA10:', indicators['LA10']
      print 'LA90:', indicators['LA90']
      print 'Ncn:', indicators['Ncn']
      print 'TNI:', indicators['TNI']
      print 'NPL:', indicators['NPL']
    # plot LAeq time series for both emission models
    pylab.figure()
    for i in range(3):
      pylab.subplot(3,1,i+1)
      ts[i].plot()

  try:
    pylab.show()
  except:
    pass

