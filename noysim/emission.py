# Noysim -- Noise simulation tools for Aimsun.
# Copyright (c) 2010-2011 by Bert De Coensel, Ghent University & Griffith University.
#
# Noise emission model functions and classes

import warnings
import random

import numpy
import pylab

from geo import Point, Direction, asPoint, asDirection
from acoustics import LOWDB, fromdB, TertsBandSpectrum
import numeric


#---------------------------------------------------------------------------------------------------
# Basic classes
#---------------------------------------------------------------------------------------------------

class Vehicle(object):
  """ base class defining a vehicle, containing all properties that could have an influence on noise emissions """
  def __init__(self, vid, length, width, height, weight, cat, axles, doublemount, studs, fuel, cc, maxspeed, maxdecel, maxaccel,
                     position = Point(0.0,0.0,0.0), direction = Direction(0.0,0.0), speed = 0.0, acceleration = 0.0):
    object.__init__(self)
    # unique vehicle ID
    self._vid          = vid
    # size properties
    self._length       = length       # in m
    self._width        = width        # in m
    self._height       = height       # in m
    self._weight       = weight       # in kg
    # emission related properties
    self._cat          = cat          # emission category (usually an integer), to be interpreted by the emission models
    self._axles        = axles        # integer, number of axles of vehicle
    self._doublemount  = doublemount  # boolean, true for double-mounted tires (for trucks)
    self._studs        = studs        # boolean, true if the vehicle has winter tires
    self._fuel         = fuel         # the type of fuel the vehicle uses (string, e.g. 'petrol', 'diesel', 'electric')
    self._cc           = cc           # the cilinder capacity (cc)
    # kinematic properties
    self._maxspeed     = maxspeed     # in km/h
    self._maxdecel     = maxdecel     # in m/s^2 (negative value)
    self._maxaccel     = maxaccel     # in m/s^2
    # dynamic properties
    self._position     = position     # position Point(x,y,z) - center of bottom plane - in m
    self._direction    = direction    # Direction(bearing,gradient) of the vehicle, in degrees (0-360)
    self._speed        = speed        # velocity (km/h)
    self._acceleration = acceleration # acceleration (m/s^2)

  def vid(self):
    return self._vid

  def length(self):
    return self._length
  def width(self):
    return self._width
  def height(self):
    return self._height
  def weight(self):
    return self._weight

  def cat(self):
    return self._cat
  def axles(self):
    return self._axles
  def doublemount(self):
    return self._doublemount
  def studs(self):
    return self._studs
  def fuel(self):
    return self._fuel
  def cc(self):
    return self._cc

  def maxspeed(self):
    return self._maxspeed
  def maxdecel(self):
    return self._maxdecel
  def maxaccel(self):
    return self._maxaccel

  def position(self):
    return self._position
  def direction(self):
    return self._direction
  def speed(self):
    return self._speed
  def acceleration(self):
    return self._acceleration

  def __str__(self):
    """ return a string representation of the vehicle """
    s = '[ID %s: %.1fx%.1fx%.1fm, %dkg, ' % (str(self.vid()), self.length(), self.width(), self.height(), int(self.weight()))
    s += 'c=%s, ax=%d, dm=%s, ' % (str(self.cat()), self.axles(), str(self.doublemount()))
    s += 'stud=%s, %s, %dcc,' % (str(self.studs()), self.fuel(), int(self.cc()))
    s += '\n max=(%.1f,%.1f,%.1f), ' % (self.maxspeed(), self.maxdecel(), self.maxaccel())
    s += 'p=%s, d=%s, v=%.1f, a=%.1f]' % (str(self.position()), str(self.direction()), self.speed(), self.acceleration())
    return s

  def copy(self, cls = None):
    """ create a copy of the vehicle """
    if cls == None:
      cls = Vehicle
    return cls(vid = self._vid, length = self._length, width = self._width, height = self._height, weight = self._weight,
               cat = self._cat, axles = self._axles, doublemount = self._doublemount, studs = self._studs, fuel = self._fuel,
               cc = self._cc, maxspeed = self._maxspeed, maxdecel = self._maxdecel, maxaccel = self._maxaccel,
               position = self._position.copy(), direction = self._direction.copy(), speed = self._speed, acceleration = self._acceleration)

  def move(self, dx = 0.0, dy = 0.0, dz = 0.0):
    """ move the location of the vehicle """
    self._position.x += dx
    self._position.y += dy
    self._position.z += dz


class Roadsurface(object):
  """ base class defining a road surface, containing all properties that could have an influence on noise emissions """
  def __init__(self, cat, temperature, chipsize, age, wet, tc):
    object.__init__(self)
    self._cat         = cat         # surface category, to be interpreted by the various emission models
    self._temperature = temperature # temperature of air above road surface (degrees celsius)
    self._chipsize    = chipsize    # road surface chip size (in mm)
    self._age         = age         # road surface age (in years)
    self._wet         = wet         # boolean, true if the surface is wet
    self._tc          = tc          # road surface temperature coefficient (in dB/degree)

  def cat(self):
    return self._cat
  def temperature(self):
    return self._temperature
  def chipsize(self):
    return self._chipsize
  def age(self):
    return self._age
  def wet(self):
    return self._wet
  def tc(self):
    return self._tc

  def __str__(self):
    """ return a string representation of the road surface """
    s = '[c=%s, t=%.1fC, chip=%dmm, ' % (str(self.cat()), self.temperature(), int(self.chipsize()))
    s += 'age=%dy, wet=%s, tc=%.2f]' % (int(self.age()), str(self.wet()), self.tc())
    return s


class Source(object):
  """ base source class, which serves as the output of an emission model """
  def __init__(self, position, direction, emission, directivity = lambda theta, phi, f: 0.0):
    object.__init__(self)
    self.position = position # Point(x,y,z) in m
    self.direction = direction # Direction(bearing,gradient) of the source, in degrees (0-360)
    self.emission = emission # source emission spectrum
    self.directivity = directivity # function (or function object) for the directivity pattern of the source
                                   # (correction on source power level as a function of theta, phi and frequency)

  def __str__(self):
    """ return a string representation of the source """
    # only prints the A-weighted level
    return '[p=%s, d=%s, e=%.2f dBA]' % (str(self.position), str(self.direction), self.emission.laeq())

  def copy(self):
    """ return a copy of the source """
    return Source(position = self.position.copy(),
                  direction = self.direction.copy(),
                  emission = self.emission.copy(),
                  directivity = self.directivity)


class EmissionModel(object):
  """ base emission model interface - to be filled in by derived classes """
  def __init__(self):
    object.__init__(self)

  def __str__(self):
    """ return a string representation of the emission model """
    return '[EmissionModel]'

  def categoryNames(self):
    """ return a list with the names of the vehicle categories that the model supports """
    raise NotImplementedError

  def sources(self, vehicle, road):
    """ calculate the list of emission sources associated with the given vehicle and road surface """
    raise NotImplementedError

  def emission(self, vehicle, road):
    """ shorthand function, calculating the total emission associated with the given vehicle and road surface """
    raise NotImplementedError


class Viewport(object):
  """ viewport function object, acting as a vehicle filter
      should return True for each vehicle that has to be taken into account in subsequent processing
  """
  def __init__(self):
    object.__init__(self)

  def __str__(self):
    """ return a string representation of the viewport """
    return '[Viewport]'

  def __call__(self, vehicle):
    """ should return True only if the vehicle has to be taken into account """
    return True # the default is to consider all vehicles


#---------------------------------------------------------------------------------------------------
# Specialized vehicle and road surface classes
#---------------------------------------------------------------------------------------------------

# The constants in these predefined classes were taken from the Queensland vehicles defined in the Griffith Univ. Aimsun file,
# with missing values (e.g. weight or cc) filled in by best guess (these additional values do not have an influence on noise anyhow)

class QLDCar(Vehicle):
  """ Queensland car (CAR_QLD) with default values for all parameters (Imagine category 1) """
  def __init__(self, vid = 0, length = 4.0, width = 2.0, height = 1.5, weight = 800.0,
                     cat = 1, axles = 2, doublemount = False, studs = False, fuel = 'petrol', cc = 1600,
                     maxspeed = 110.0, maxdecel = -6.5, maxaccel = 2.8,
                     position = Point(0.0,0.0,0.0), direction = Direction(0.0,0.0), speed = 0.0, acceleration = 0.0):
    Vehicle.__init__(self, vid, length, width, height, weight, cat, axles, doublemount, studs, fuel, cc,
                     maxspeed, maxdecel, maxaccel, position, direction, speed, acceleration)
  def copy(self):
    return Vehicle.copy(self, cls = QLDCar)

class QLDVan(Vehicle):
  """ Queensland van (HV) with default values for all parameters (Imagine category 1) """
  def __init__(self, vid = 0, length = 7.0, width = 2.0, height = 2.0, weight = 2000.0,
                     cat = 1, axles = 2, doublemount = False, studs = False, fuel = 'petrol', cc = 2500,
                     maxspeed = 110.0, maxdecel = -5.0, maxaccel = 2.5,
                     position = Point(0.0,0.0,0.0), direction = Direction(0.0,0.0), speed = 0.0, acceleration = 0.0):
    Vehicle.__init__(self, vid, length, width, height, weight, cat, axles, doublemount, studs, fuel, cc,
                     maxspeed, maxdecel, maxaccel, position, direction, speed, acceleration)
  def copy(self):
    return Vehicle.copy(self, cls = QLDVan)

class QLDLightTruck(Vehicle):
  """ Queensland light truck (LT) with default values for all parameters (Imagine category 2) """
  def __init__(self, vid = 0, length = 12.0, width = 2.5, height = 2.5, weight = 5000.0,
                     cat = 2, axles = 2, doublemount = True, studs = False, fuel = 'petrol', cc = 4000,
                     maxspeed = 110.0, maxdecel = -3.0, maxaccel = 1.5,
                     position = Point(0.0,0.0,0.0), direction = Direction(0.0,0.0), speed = 0.0, acceleration = 0.0):
    Vehicle.__init__(self, vid, length, width, height, weight, cat, axles, doublemount, studs, fuel, cc,
                     maxspeed, maxdecel, maxaccel, position, direction, speed, acceleration)
  def copy(self):
    return Vehicle.copy(self, cls = QLDLightTruck)

class QLDSemiTrailer(Vehicle):
  """ Queensland semi-trailer (ST) with default values for all parameters (Imagine category 3) """
  def __init__(self, vid = 0, length = 19.0, width = 2.5, height = 3.0, weight = 10000.0,
                     cat = 3, axles = 4, doublemount = True, studs = False, fuel = 'petrol', cc = 5000,
                     maxspeed = 110.0, maxdecel = -2.9, maxaccel = 1.0,
                     position = Point(0.0,0.0,0.0), direction = Direction(0.0,0.0), speed = 0.0, acceleration = 0.0):
    Vehicle.__init__(self, vid, length, width, height, weight, cat, axles, doublemount, studs, fuel, cc,
                     maxspeed, maxdecel, maxaccel, position, direction, speed, acceleration)
  def copy(self):
    return Vehicle.copy(self, cls = QLDSemiTrailer)

class QLDBDouble(Vehicle):
  """ Queensland B-Double heavy vehicle (BD) with default values for all parameters (Imagine category 3) """
  def __init__(self, vid = 0, length = 25.0, width = 2.5, height = 3.5, weight = 30000.0,
                     cat = 3, axles = 4, doublemount = True, studs = False, fuel = 'petrol', cc = 8000,
                     maxspeed = 110.0, maxdecel = -2.75, maxaccel = 0.8,
                     position = Point(0.0,0.0,0.0), direction = Direction(0.0,0.0), speed = 0.0, acceleration = 0.0):
    Vehicle.__init__(self, vid, length, width, height, weight, cat, axles, doublemount, studs, fuel, cc,
                     maxspeed, maxdecel, maxaccel, position, direction, speed, acceleration)
  def copy(self):
    return Vehicle.copy(self, cls = QLDBDouble)

class QLDMotorcycle(Vehicle):
  """ Queensland motorcycle with default values for all parameters (Imagine category 4b - here 5) """
  def __init__(self, vid = 0, length = 1.5, width = 0.5, height = 1.5, weight = 200.0,
                     cat = 5, axles = 2, doublemount = False, studs = False, fuel = 'petrol', cc = 1000,
                     maxspeed = 110.0, maxdecel = -6.0, maxaccel = 4.0,
                     position = Point(0.0,0.0,0.0), direction = Direction(0.0,0.0), speed = 0.0, acceleration = 0.0):
    Vehicle.__init__(self, vid, length, width, height, weight, cat, axles, doublemount, studs, fuel, cc,
                     maxspeed, maxdecel, maxaccel, position, direction, speed, acceleration)
  def copy(self):
    return Vehicle.copy(self, cls = QLDMotorcycle)


class ReferenceRoadsurface(Roadsurface):
  """ Harmonoise/Imagine reference road surface """
  def __init__(self, cat = 'REF', temperature = 20.0, chipsize = 11.0, age = 2.0, wet = False, tc = 0.08):
    Roadsurface.__init__(self, cat, temperature, chipsize, age, wet, tc)


#---------------------------------------------------------------------------------------------------
# Specialized viewport classes
#---------------------------------------------------------------------------------------------------

class RectangularViewport(Viewport):
  """ viewport that takes into account the vehicles that are situated in a rectangular area """
  def __init__(self, minx, miny, maxx, maxy):
    Viewport.__init__(self)
    (self.minx, self.miny, self.maxx, self.maxy) = (minx, miny, maxx, maxy)

  def __str__(self):
    """ return a string representation of the viewport """
    return '[RectangularViewport (%s, %s, %s, %s)]' % (self.minx, self.miny, self.maxx, self.maxy)

  def __call__(self, vehicle):
    """ check if the vehicle is situated inside the rectangular area """
    p = vehicle.position()
    if (self.minx <= p.x) and (p.x <= self.maxx) and (self.miny <= p.y) and (p.y <= self.maxy):
      return True
    return False


# TODO:
# - define the class below
# - uncomment the line in Configuration.viewport so it is used
# class DynamicViewport(RectangularViewport):
#   """ special case of a rectangular viewport, for which the dimensions are automatically tailored
#       to give optimal tradeoff between speed and accuracy, based on various network and receiver properties
#   """
#   def __init__(self):
#     # perform calculations for minx, miny, maxx, maxy
#     # finally create the viewport
#     RectangularViewport.__init__(minx, miny, maxx, maxy)


#---------------------------------------------------------------------------------------------------
# Imagine road traffic noise emission model
#---------------------------------------------------------------------------------------------------

# model constants (LOWDB is used to fill in the values that are not supplied by Imagine, i.e. at 20 Hz and at 12kHz and above)
IMAGINE = {# Light motor vehicles
           1: {'AR': numpy.asarray([LOWDB, 69.9, 69.9, 69.9, 74.9, 74.9, 74.9, 79.3, 82.0, 81.2, 80.9, 78.9, 78.8, 80.5, 85.0, 87.9,
                                     90.9, 93.3, 92.8, 91.5, 88.5, 84.9, 81.8, 78.7, 74.9, 71.8, 69.1, 65.6,LOWDB,LOWDB,LOWDB]),
               'BR': numpy.asarray([  0.0, 33.0, 33.0, 33.0, 30.0, 30.0, 30.0, 41.0, 41.2, 42.3, 41.8, 38.6, 35.5, 32.9, 25.0, 25.0,
                                     27.0, 33.4, 36.7, 37.0, 37.5, 37.5, 38.6, 39.6, 40.0, 39.9, 40.2, 40.3,  0.0,  0.0,  0.0]),
               'AP': numpy.asarray([LOWDB, 87.0, 87.0, 87.0, 87.9, 90.8, 89.9, 86.9, 82.6, 81.9, 82.3, 83.9, 83.3, 82.4, 80.6, 80.2,
                                     77.8, 78.0, 81.4, 82.3, 82.6, 81.5, 80.2, 78.5, 75.6, 73.3, 71.0, 68.1,LOWDB,LOWDB,LOWDB]),
               'BP': numpy.asarray([  0.0,  0.0,  0.0,  0.0,  0.0, -3.0,  0.0,  8.0,  6.0,  6.0,  7.0,  8.0,  8.0,  8.0,  8.0,  8.0,
                                      8.0,  8.0,  8.0,  8.0,  8.0,  8.0,  8.0,  8.0,  8.0,  8.0,  8.0,  8.0,  0.0,  0.0,  0.0]),
               'CP': numpy.asarray([  0.0,  4.0,  4.0,  4.0,  7.0,  7.0,  7.0,  7.0,  7.0,  7.0,  7.0,  4.0,  4.0,  4.0,  4.0,  4.0,
                                      4.0,  4.0,  4.0,  4.0,  4.0,  4.0,  4.0,  4.0,  4.0,  4.0,  4.0,  4.0,  0.0,  0.0,  0.0])},
           # Medium heavy vehicles:
           2: {'AR': numpy.asarray([LOWDB, 76.5, 76.5, 76.5, 78.5, 79.5, 79.5, 82.5, 84.3, 84.7, 84.3, 87.4, 87.8, 89.8, 91.6, 93.5,
                                     94.6, 92.4, 89.6, 88.1, 85.9, 82.7, 80.7, 78.8, 76.8, 76.7, 75.7, 74.5,LOWDB,LOWDB,LOWDB]),
               'BR': numpy.asarray([  0.0, 33.0, 33.0, 33.0, 30.0, 30.0, 30.0, 32.9, 35.9, 38.1, 36.5, 33.5, 30.6, 27.7, 21.9, 23.8,
                                     28.4, 31.1, 35.4, 35.9, 36.7, 36.3, 37.7, 38.5, 39.8, 39.9, 40.2, 40.3,  0.0,  0.0,  0.0]),
               'AP': numpy.asarray([LOWDB, 93.9, 93.9, 94.1, 95.0, 97.3, 96.1, 92.5, 91.9, 90.4, 93.4, 94.4, 94.2, 93.0, 90.8, 92.1,
                                     92.5, 94.1, 94.5, 92.4, 90.1, 87.6, 85.8, 83.8, 81.4, 80.0, 77.2, 75.4,LOWDB,LOWDB,LOWDB]),
               'BP': numpy.asarray([  0.0,  0.0,  0.0,  0.0,  0.0, -4.0,  0.0,  4.0,  5.0,  5.5,  6.0,  6.5,  6.5,  6.5,  6.5,  6.5,
                                      6.5,  6.5,  6.5,  6.5,  6.5,  6.5,  6.5,  6.5,  6.5,  6.5,  6.5,  6.5,  0.0,  0.0,  0.0]),
               'CP': numpy.asarray([  0.0,  5.0,  5.0,  5.0,  9.0,  9.0,  9.0,  9.0,  9.0,  9.0,  9.0,  5.0,  5.0,  5.0,  5.0,  5.0,
                                      5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  0.0,  0.0,  0.0])},
           # Heavy vehicles
           3: {'AR': numpy.asarray([LOWDB, 79.5, 79.5, 79.5, 81.5, 82.5, 82.5, 85.5, 87.3, 87.7, 87.3, 89.5, 90.5, 93.8, 95.9, 97.3,
                                     98.0, 95.6, 93.2, 91.9, 88.9, 85.5, 84.1, 82.2, 79.8, 78.6, 77.5, 76.8,LOWDB,LOWDB,LOWDB]),
               'BR': numpy.asarray([  0.0, 33.0, 33.0, 33.0, 30.0, 30.0, 30.0, 31.4, 32.8, 36.0, 34.6, 32.7, 29.3, 26.4, 24.2, 25.9,
                                     30.4, 32.3, 36.5, 36.8, 38.0, 36.8, 38.5, 38.9, 38.5, 40.2, 40.8, 41.0,  0.0,  0.0,  0.0]),
               'AP': numpy.asarray([LOWDB, 95.7, 94.9, 94.1, 96.8,101.8, 98.6, 95.5, 96.2, 95.7, 97.2, 96.3, 97.2, 95.8, 95.9, 96.8,
                                     95.1, 95.8, 95.0, 92.7, 91.2, 88.7, 87.6, 87.2, 84.2, 82.7, 79.7, 77.6,LOWDB,LOWDB,LOWDB]),
               'BP': numpy.asarray([  0.0,  0.0,  0.0,  0.0, -4.0,  0.0,  4.0,  3.0,  3.0,  3.0,  4.0,  5.0,  5.0,  5.0,  5.0,  5.0,
                                      5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  0.0,  0.0,  0.0]),
               'CP': numpy.asarray([  0.0,  5.0,  5.0,  5.0,  9.0,  9.0,  9.0,  9.0,  9.0,  9.0,  9.0,  5.0,  5.0,  5.0,  5.0,  5.0,
                                      5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  5.0,  0.0,  0.0,  0.0])},
           # Powered two-wheelers 4a (mopeds < 50cc)
           4: {'AR': LOWDB*numpy.ones(31),
               'BR': numpy.zeros(31),
               'AP': numpy.asarray([LOWDB, 88.7, 87.6, 85.5, 85.8, 81.5, 80.7, 82.0, 85.6, 81.6, 81.4, 85.5, 86.3, 87.9, 88.7, 89.9,
                                     91.8, 91.2, 92.4, 95.0, 94.1, 92.9, 90.4, 89.1, 87.4, 84.9, 84.4, 82.2,LOWDB,LOWDB,LOWDB]),
               'BP': numpy.asarray([  0.0, -2.2, -0.1,  1.7,  5.9,  1.9,  3.3,  0.9, 17.3, 14.5,  5.0, 14.6,  9.9,  9.7, 12.7, 12.3,
                                     13.9, 16.6, 17.2, 17.9, 19.3, 20.6, 19.9, 20.8, 20.5, 21.0, 21.0, 19.3,  0.0,  0.0,  0.0]),
               'CP': numpy.asarray([  0.0,  4.0,  4.0,  4.0,  7.0,  7.0,  7.0,  7.0,  7.0,  7.0,  7.0,  4.0,  4.0,  4.0,  4.0,  4.0,
                                      4.0,  4.0,  4.0,  4.0,  4.0,  4.0,  4.0,  4.0,  4.0,  4.0,  4.0,  4.0,  0.0,  0.0,  0.0])},
           # Powered two-wheelers 4b (motorcycles > 50cc)
           5: {'AR': LOWDB*numpy.ones(31),
               'BR': numpy.zeros(31),
               'AP': numpy.asarray([LOWDB, 90.8, 88.9, 89.2, 90.5, 89.2, 90.7, 93.2, 93.2, 90.0, 88.4, 87.6, 87.7, 87.0, 87.4, 89.4,
                                     89.9, 90.1, 89.7, 89.8, 88.2, 86.5, 85.8, 85.1, 85.1, 82.7, 81.7, 80.4,LOWDB,LOWDB,LOWDB]),
               'BP': numpy.asarray([  0.0,  2.1,  3.1,  1.2,  2.3,  2.8,  4.2,  6.2,  4.8,  7.3, 11.3, 10.6, 13.9, 13.5, 11.0, 10.8,
                                     11.4, 11.4, 11.7, 13.4, 11.6, 12.2, 10.9, 10.5, 12.0, 12.0, 12.0, 12.0,  0.0,  0.0,  0.0]),
               'CP': numpy.asarray([  0.0,  4.0,  4.0,  4.0,  7.0,  7.0,  7.0,  7.0,  7.0,  7.0,  7.0,  4.0,  4.0,  4.0,  4.0,  4.0,
                                      4.0,  4.0,  4.0,  4.0,  4.0,  4.0,  4.0,  4.0,  4.0,  4.0,  4.0,  4.0,  0.0,  0.0,  0.0])}}

# correction values for studded tires
STUDS = {'A':  numpy.asarray([ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.3,  1.4,  1.5,  0.9,  1.2,  1.5,  1.9,  1.8,
                               0.8,  0.5,  0.2, -0.2, -0.4,  0.5,  0.8,  0.9,  2.1,  5.0,  7.3, 10.0,  0.0,  0.0,  0.0]),
         'B':  numpy.asarray([ 0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0, -4.1, -6.0, -8.5, -4.1,  1.7,  0.6, -4.6, -3.9,
                              -2.7, -4.2,-11.7,-11.7,-14.9,-17.6,-21.8,-21.6,-19.2,-14.6, -9.9,-10.2,  0.0,  0.0,  0.0])}


class ImagineDirectivity(object):
  """ function object implementing the Harmonoise/Imagine directivity pattern
      once an object of this class is created, it behaves like a function (thanks to the '__call__' method)
  """
  def __init__(self, cat, h):
    """ create the directivity function, for the given vehicle category and source height """
    object.__init__(self)
    self.cat = cat # vehicle category
    self.h = h # source height

  def __call__(self, theta, phi, f):
    """ return the directivity correction for the given angles, at the given frequency """
    # theta: horizontal angle between travelling direction of vehicle and reciever (0 degrees means receiver in front of vehicle)
    # phi: vertical angle between travelling direction of vehicle and receiver (0 degrees means receiver in front of vehicle)
    # NOTE: for readability reasons, other symbols are used than in the Imagine document
    # restrict the angles to the correct range
    while theta < 0.0:
      theta += 360.0
    while theta > 360.0:
      theta -= 360.0
    while phi < -180.0:
      phi += 360.0
    while phi > 180.0:
      phi -= 360.0
    # enforce horizontal and vertical symmetry
    if theta > 180.0:
      theta = 360.0 - theta
    if phi < 0.0:
      phi = -phi
    if phi > 90.0:
      phi = 180.0 - phi
    # calculate shorthands
    thetaRad = (numpy.pi/180.0)*theta
    phiRad = (numpy.pi/180.0)*phi
    pi2theta = numpy.pi/2.0 - thetaRad
    sinpi2theta = numpy.sin(pi2theta)
    sqrtcosphi = numpy.sqrt(numpy.cos(phiRad))
    # calculate horizontal directivity (formulas from Harmonoise model, depending on source height, independent of vehicle category)
    if self.h == 0.01:
      # horn effect, only for certain frequency range
      if (1600.0 <= f) and (f <= 6300.0):
        horizontal = (-1.5 + 2.5*abs(sinpi2theta)) * sqrtcosphi
      else:
        horizontal = 0.0
    elif self.h == 0.30:
      horizontal = 0.0
    elif self.h == 0.75:
      # screening by the body of the heavy vehicle
      horizontal = (1.546*(pi2theta**3) - 1.425*(pi2theta**2) + 0.22*pi2theta + 0.6) * sqrtcosphi
    else:
      raise Exception('no directivity defined for sources at height %.2f' % self.h)
    # calculate vertical directivity (approximations from Imagine model, depending on vehicle category, independent of source height)
    if self.cat == 1:
      vertical = -abs(phi/20.0) # phi in degrees
    elif self.cat in (2, 3):
      vertical = -abs(phi/30.0)
    else:
      vertical = 0.0 # no corrections for categories 4 and 5
    return horizontal + vertical


class ImagineModel(EmissionModel):
  """ Imagine road traffic noise emission model """
  def __init__(self):
    EmissionModel.__init__(self)
    # parameters
    self.vref = 70.0
    self.vinterval = (0.1, 160.0)
    # flags for applying different types of corrections - to be adjusted after object creation if necessary
    self.correction = {'acceleration': True, 'gradient': False, 'temperature': False,
                       'surface': False, 'wetness': False, 'axles': True, 'fleet': False}
    self.fleet = {'diesel': 19.0, 'tirewidth': 187.0, 'vans': 10.5, 'iress': (1.0, 35.0), 'studs': False}

  def __str__(self):
    """ return a string representation of the emission model """
    return '[Imagine emission model]'

  def categoryNames(self):
    return ['Light', 'Medium', 'Heavy', 'Moped', 'Motorcycle']

  def rollingNoise(self, vehicle, road):
    # calculate base rolling noise
    v = numpy.clip(vehicle.speed(), *self.vinterval)
    z = IMAGINE[vehicle.cat()]['AR'] + IMAGINE[vehicle.cat()]['BR']*numpy.log10(v/self.vref)
    # apply corrections
    if self.correction['temperature'] == True:
      z += self.temperatureCorrection(vehicle, road)
    if self.correction['surface'] == True:
      z += self.surfaceCorrection(vehicle, road)
    if self.correction['wetness'] == True:
      z += self.wetnessCorrection(vehicle, road)
    if self.correction['axles'] == True:
      z += self.axlesCorrection(vehicle, road)
    if self.correction['fleet'] == True:
      z += self.fleetCorrectionRolling(vehicle, road)
    return z

  def propulsionNoise(self, vehicle, road):
    # calculate base propulsion noise
    v = numpy.clip(vehicle.speed(), *self.vinterval)
    z = IMAGINE[vehicle.cat()]['AP'] + IMAGINE[vehicle.cat()]['BP']*((v - self.vref)/self.vref)
    # apply corrections
    if self.correction['acceleration'] == True:
      z += self.accelerationCorrection(vehicle, road)
    if self.correction['gradient'] == True:
      z += self.gradientCorrection(vehicle, road)
    if self.correction['fleet'] == True:
      z += self.fleetCorrectionPropulsion(vehicle, road)
    return z

  def accelerationCorrection(self, vehicle, road):
    # restrict acceleration
    maxaccel = {1: 2.0, 2: 1.0, 3: 1.0, 4: 4.0, 5: 4.0}[vehicle.cat()]
    a = numpy.clip(vehicle.acceleration(), -1.0, maxaccel)
    return IMAGINE[vehicle.cat()]['CP'] * a

  def gradientCorrection(self, vehicle, road):
    # calculate gradient as a percentage
    alpha = 100.0*numpy.tan(asDirection(vehicle.direction()).gradientRadians())
    cp = IMAGINE[vehicle.cat()]['CP']
    g = 9.81
    if vehicle.cat() in [1, 4, 5]:
      if alpha >= -2.0:
        return cp * g * (alpha/100.0)
      if (-8.0 < alpha) and (alpha < -2.0):
        return cp * g * (-2.0/100.0)
      if alpha <= -8.0:
        return -cp * g * ((alpha + 10.0)/100.0)
    if vehicle.cat() in [2, 3]:
      if alpha >= -2.0:
        return cp * g * (alpha/100.0)
      if alpha < -2.0:
        return -cp * g * ((alpha + 4.0)/100.0)
    raise Exception('Imagine model: condition for gradient correction not found')

  def temperatureCorrection(self, vehicle, road):
    factor = {1: 1.0, 2: 0.5, 3: 0.5, 4: 1.0, 5: 1.0}[vehicle.cat()] # half temperature coefficient for cats 2 and 3
    return factor * road.tc() * (20.0 - road.temperature())

  def surfaceCorrection(self, vehicle, road):
    """ corrections for road surfaces belonging to the reference cluster (DAC and SMA) """
    # check for vehicle type and surface type
    if vehicle.cat() in [2, 3]:
      return 0.0 # no correction for heavy vehicles
    if not (road.cat() in ['REF', 'DAC', 'SMA']):
      return 0.0 # surface not in reference cluster
    chipsize = numpy.clip(road.chipsize(), 8.0, 16.0)
    # surface chipsize and type correction
    z = 0.25*(chipsize - 11.0)
    z += {'REF': 0.0, 'DAC': -0.3, 'SMA': 0.3}[road.cat()]
    return z

  def wetnessCorrection(self, vehicle, road):
    # check for vehicle type and wetness
    if not (road.wet() and (vehicle.cat() == 1)):
      return 0.0
    # retrieve applicable model constants
    v = numpy.clip(vehicle.speed(), *self.vinterval)
    return max(0.0, 15.0*numpy.log10(numpy.asarray(FTERTS)) - 12.0*numpy.log10(v/self.vref) - 48.0)

  def axlesCorrection(self, vehicle, road):
    if not (vehicle.cat() == 3):
      return 0.0 # correction only for heavy trucks
    if not vehicle.doublemount():
      return 6.8*numpy.log10(vehicle.axles()/4.0)
    else:
      return 9.1*numpy.log10(vehicle.axles()/4.0) + 0.8

  def fleetCorrectionRolling(self, vehicle, road):
    z = 0.0
    # correction for tire width
    if vehicle.cat() == 1:
      z += 0.04 * (self.fleet['tirewidth'] - 187.0)
    # correction for percentage of delivery vans
    if vehicle.cat() == 1:
      z += 1.0 * (self.fleet['vans'] - 10.5)/100.0
    # correction for winter/studded tires
    if (self.fleet['studs'] == True) and (vehicle.cat() == 1):
      v = numpy.clip(vehicle.speed(), 50.0, 90.0)
      z += STUDS['A'] + STUDS['B']*numpy.log10(v/self.vref)
    return z

  def fleetCorrectionPropulsion(self, vehicle, road):
    z = 0.0
    # correction for percentage of diesel vehicles
    if vehicle.cat() == 1:
      z += 3.0 * (self.fleet['diesel'] - 19.0)/100.0
    # correction for percentage of delivery vans
    if vehicle.cat() == 1:
      z += 5.0 * (self.fleet['vans'] - 10.5)/100.0
    # correction for illegal replacement exhaust silencer systems (IRESS)
    if vehicle.cat() in [1, 2, 3]:
      piress = (self.fleet['iress'][0] - 1.0)/100.0
    else:
      piress = (self.fleet['iress'][1] - 35.0)/100.0
    z += (29.0 * piress) - (24.0 * piress**2)
    return z

  def sources(self, vehicle, road = ReferenceRoadsurface()):
    # calculate position of sources
    pos = vehicle.position()
    h = {1: (0.01, 0.30), 2: (0.01, 0.75), 3: (0.01, 0.75), 4: (0.30, 0.30), 5: (0.30, 0.30)}[vehicle.cat()]
    lopos = Point(pos[0], pos[1], pos[2] + h[0])
    hipos = Point(pos[0], pos[1], pos[2] + h[1])
    # calculate rolling and propulsion noise
    r = fromdB(self.rollingNoise(vehicle, road))
    p = fromdB(self.propulsionNoise(vehicle, road))
    # calculate low and high noise
    lonoise = 10.0*numpy.log10(0.8*r + 0.2*p)
    hinoise = 10.0*numpy.log10(0.2*r + 0.8*p)
    # construct sources
    return [Source(position = lopos,
                   direction = asDirection(vehicle.direction()),
                   emission = TertsBandSpectrum(lonoise),
                   directivity = ImagineDirectivity(cat = vehicle.cat(), h = h[0])),
            Source(position = hipos,
                   direction = asDirection(vehicle.direction()),
                   emission = TertsBandSpectrum(hinoise),
                   directivity = ImagineDirectivity(cat = vehicle.cat(), h = h[1]))]

  def emission(self, vehicle, road = ReferenceRoadsurface()):
    """ return the total emission as a single spectrum, assuming that all is emitted by the same source """
    return TertsBandSpectrum(10.0*numpy.log10(fromdB(self.rollingNoise(vehicle,road)) + fromdB(self.propulsionNoise(vehicle,road))))


#---------------------------------------------------------------------------------------------------
# Random corrected road traffic noise emission models
#---------------------------------------------------------------------------------------------------

class ImagineCorrectionModel(ImagineModel):
  """ Road traffic noise emission model with random corrections on the emissions
      This model uses the Imagine model as a base, but adds a random (frequency-independent) sound power level correction
      to each vehicle, in order to model a realistic distribution of louder/quiter vehicles within the same emission class.
  """
  def __init__(self, seed = None):
    ImagineModel.__init__(self)
    numeric.seed(seed)
    self.corrections = {} # dict with a random correction for each vehicle, filled during simulation
    self.generators = {} # dict with correction generators for each vehicle category, to be filled in by subclasses

  def __str__(self):
    """ return a string representation of the emission model """
    return '[Random correction emission model]'

  def getCorrection(self, vehicle):
    """ return the correction for a given vehicle """
    (vid, cat) = (vehicle.vid(), vehicle.cat())
    if vid in self.corrections:
      # vehicle was encountered before, so use the same correction
      corr = self.corrections[vid]
    else:
      # new vehicle, so calculate a new correction and save it
      corr = self.generators[cat].generate()
      self.corrections[vid] = corr
    return corr

  def sources(self, vehicle, road = ReferenceRoadsurface()):
    """ overload the ImagineModel implementation """
    # calculate the sources using the Imagine model
    result = ImagineModel.sources(self, vehicle, road)
    # get the sound power level correction and apply it to the sources
    corr = self.getCorrection(vehicle)
    for source in result:
      source.emission.correct(corr)
    return result

  def emission(self, vehicle, road = ReferenceRoadsurface()):
    """ overload the ImagineModel implementation """
    # calculate the emission using the Imagine model
    result = ImagineModel.emission(self, vehicle, road)
    # get the sound power level correction and apply it to the emission
    corr = self.getCorrection(vehicle)
    result.correct(corr)
    return result


class SkewedNormalImagineCorrectionModel(ImagineCorrectionModel):
  """ Emission model that samples random corrections from a skewed normal distribution """
  def __init__(self, stdev = (0.0,0.0,0.0,0.0,0.0), skew = (0.0,0.0,0.0,0.0,0.0), seed = None):
    ImagineCorrectionModel.__init__(self, seed=seed)
    assert (len(stdev) == 5) and (len(skew) == 5)
    for i in range(5):
      self.generators[i+1] = numeric.SkewedNormalCorrectionGenerator(stdev = stdev[i], skew = skew[i])

  def __str__(self):
    """ return a string representation of the emission model """
    return '[Skewed normal correction emission model]'


# Distributions of sound power levels from Australian study
# (Brown & Tomerini, Road & Transport Research, 20(3):50-63, 2011)
AUSTDIST = {1: numpy.asarray([89, 188, 207, 386, 438, 437, 556, 596, 821, 797, 905, 1099, 1369, 1567, 1727, 2184, 2674, 3426, 3502, 3522, 3123, 2455, 1696, 1238, 832, 468, 362, 286, 195, 126, 74, 77, 32, 34, 14, 14, 11, 6, 6, 4, 5, 6, 3, 2, 5, 8, 0, 0, 0, 0, 0], dtype=float),
            2: numpy.asarray([4, 8, 12, 27, 33, 39, 36, 55, 55, 67, 82, 70, 103, 87, 91, 94, 152, 258, 301, 369, 459, 568, 687, 622, 574, 486, 344, 296, 241, 168, 134, 80, 61, 50, 34, 28, 21, 12, 4, 4, 2, 1, 5, 0, 2, 3, 0, 0, 0, 0, 0], dtype=float),
            3: numpy.asarray([14, 120, 81, 194, 307, 277, 306, 319, 328, 345, 404, 436, 488, 456, 507, 514, 473, 584, 611, 668, 679, 711, 919, 1083, 1430, 1662, 2007, 2018, 1872, 1696, 1268, 935, 547, 378, 261, 197, 102, 77, 60, 40, 24, 32, 22, 11, 13, 16, 1, 0, 0, 0, 2], dtype=float),
            4: numpy.asarray([0, 0, 2, 5, 8, 5, 9, 8, 9, 19, 22, 24, 20, 32, 34, 48, 54, 58, 78, 74, 72, 70, 50, 52, 34, 33, 43, 26, 21, 13, 14, 14, 4, 3, 5, 4, 5, 2, 0, 2, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0], dtype=float),
            5: numpy.asarray([0, 0, 2, 5, 8, 5, 9, 8, 9, 19, 22, 24, 20, 32, 34, 48, 54, 58, 78, 74, 72, 70, 50, 52, 34, 33, 43, 26, 21, 13, 14, 14, 4, 3, 5, 4, 5, 2, 0, 2, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0], dtype=float)}


class DistributionImagineCorrectionModel(ImagineCorrectionModel):
  """ Emission model that samples random corrections from a predefined distribution """
  def __init__(self, corrdist = AUSTDIST, seed = None, zeropoint='meanEn'):
    # corrdist = dict with correction distributions (in bins of 1dB) for each Imagine vehicle class
    ImagineCorrectionModel.__init__(self, seed=seed)
    for cat, values in corrdist.iteritems():
      self.generators[cat] = numeric.TabulatedCorrectionGenerator(values = values, dx = 1.0, zeropoint=zeropoint)

  def __str__(self):
    """ return a string representation of the emission model """
    return '[Distribution correction emission model]'


#---------------------------------------------------------------------------------------------------
# Lookup table road traffic noise emission model
#---------------------------------------------------------------------------------------------------

# TODO: Implement lookup table model, for which the following has to be done
# - create a class LookupModel, that is a subclass from ImagineModel, and overload the 'sources' and 'emission' methods
#   (same way as the DistributionModel class above); a subclass from the Imagine model is necessary because the Lookup model
#   may use the shape of the emission spectrum as from the Imagine model
# - add necessary values to the default configuration (CFGEMODEL, see above) and create a new default configuration file,
#   by running this script from the command line with the flag MAIN_CONFIG set to True
# - update the method 'Configuration.emodel' (see below) such that a LookupModel object is created when appropriate


#---------------------------------------------------------------------------------------------------
# Test code
#---------------------------------------------------------------------------------------------------

if __name__ == '__main__':

  # test emission correction generator
  if 1:
    vClass = 3
    pylab.figure()
    g = numeric.TabulatedCorrectionGenerator(values = AUSTDIST[vClass], zeropoint='meanEn')
    g.plotData() # measured distribution
    g.plot() # fitted distribution

  # plot of Imagine emission spectrum at different vehicle speeds
  if 0:
    road = ReferenceRoadsurface()
    model = ImagineModel()
    cat = 1
    pylab.figure()
    speeds = [30, 40, 50, 60, 70, 80, 90, 100, 110, 120]
    markers = ['circle grey', 'diamond black', 'square white', 'triangle grey', 'circle black',
               'diamond white', 'square grey', 'triangle black', 'circle white', 'diamond grey']
    for v, m in zip(speeds, markers):
      model.emission(QLDCar(cat = cat, speed = v, acceleration = 0.0)).plot(m = m, interval = (60.0, 110.0))
    pylab.legend([('%d km/h' % v) for v in speeds])
    pylab.title('Imagine emission spectrum at different vehicle speeds')

  # reproduction of Figure 25 of Imagine report (emission spectra for rolling and propulsion noise, and total emission spectrum)
  if 0:
    road = ReferenceRoadsurface()
    model = ImagineModel()
    vList = {1: range(10, 161), 2: range(10, 101), 3: range(10, 101)}
    yRange = {1: (70, 115), 2: (75, 115), 3: (75, 115)}
    pylab.figure()
    for cat in [1, 2, 3]:
      p = [TertsBandSpectrum(model.propulsionNoise(QLDCar(cat = cat, speed = v, acceleration = 0.0), road)).laeq() for v in vList[cat]]
      r = [TertsBandSpectrum(model.rollingNoise(QLDCar(cat = cat, speed = v, acceleration = 0.0), road)).laeq() for v in vList[cat]]
      e = [model.emission(QLDCar(cat = cat, speed = v, acceleration = 0.0)).laeq() for v in vList[cat]]
      pylab.subplot(2, 2, cat)
      pylab.plot(vList[cat], p)
      pylab.plot(vList[cat], r)
      pylab.plot(vList[cat], e)
      # adjust y-axis
      a = pylab.axis()
      pylab.axis([a[0], a[1], yRange[cat][0], yRange[cat][1]])

  # reproduction of Figure 5.32 of Harmonoise report (directivity functions for source heights 0.1m and 0.75m)
  if 0:
    cat = 1 # vehicle category of interest
    f = 2000.0 # frequency of interest
    thetas = numpy.arange(0.0, 180.0)
    pylab.figure()
    for h in [0.01, 0.75]:
      func = [ImagineDirectivity(cat = cat, h = h)(theta = theta, phi = 0.0, f = f) for theta in thetas]
      pylab.plot((numpy.pi/180.0)*thetas, func)
    # adjust y-axis
    a = pylab.axis()
    pylab.axis([0.0, 3.5, -10.0, 4.0])
    # draw grid
    pylab.gca().xaxis.grid(color='gray', linestyle='dashed')
    pylab.gca().yaxis.grid(color='gray', linestyle='dashed')

  # plot of Harmonoise/Imagine directivity patterns as polar plot
  if 0:
    warnings.simplefilter('ignore', UserWarning)
    cat = 1
    f = 2000.0
    pylab.figure()
    iplot = 0
    for h in [0.01, 0.30, 0.75]:
      for phi in [0.0, 30.0, 60.0, 90.0]:
        directivity = ImagineDirectivity(cat = cat, h = h)
        thetas = numpy.arange(0.0, 360.0)
        Lcorrs = [directivity(theta = theta, phi = phi, f = f) for theta in thetas] # level corrections
        iplot += 1
        pylab.subplot(3, 4, iplot, polar = True)
        pylab.polar((numpy.pi/180.0)*thetas, numpy.zeros(360), color = 'black', linestyle = '--') # draw the zero line
        pylab.polar((numpy.pi/180.0)*thetas, Lcorrs)
        pylab.ylim(-10.0, 4.0)


  try:
    pylab.show()
  except:
    pass
