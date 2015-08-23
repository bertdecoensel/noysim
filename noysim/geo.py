# Noysim -- Noise simulation tools for Aimsun.
# Copyright (c) 2010-2011 by Bert De Coensel, Ghent University & Griffith University.
#
# Basic geometry functions and classes

import numpy
import pylab


EPSILON = 10e-12 # smallest difference for points/directions


#---------------------------------------------------------------------------------------------------
# Convenience functions
#---------------------------------------------------------------------------------------------------

def parse_coordinates(*args):
  """ parse 2D/3D coordinates x,y(,z) in a variety of fashions, and return a 3-element tuple """
  n = len(args)
  if n == 0:
    return (0.0,0.0,0.0)
  if n == 1:
    try: # try if a Point object is supplied
      return args[0].coordinates()
    except:
      if type(args[0]) in (tuple,list):
        # coordinates supplied as a tuple (x,y) or (x,y,z)
        if len(args[0]) == 2:
          return (args[0][0], args[0][1], 0.0)
        if len(args[0]) == 3:
          return (args[0][0], args[0][1], args[0][2])
      if type(args[0]) is str:
        # coordinates supplied as a string '(x,y,z)'
        c = args[0].strip('()').split(',')
        return (float(c[0]), float(c[1]), float(c[2]))
  else:
    # coordinates supplied as separate arguments x,y or x,y,z
    if n == 2:
      return (args[0], args[1], 0.0)
    if n == 3:
      return (args[0], args[1], args[2])
  raise Exception('unable to parse coordinates: ' + str(args))


def asPoint(p):
  """ create a point object from 2D/3D coordinates """
  if isinstance(p, Point):
    return p
  else:
    return Point(p)


def asDirection(d):
  """ create a direction object from a tuple (bearing, gradient) """
  if isinstance(d, Direction):
    return d
  else:
    return Direction(bearing = d[0], gradient = d[1])


#---------------------------------------------------------------------------------------------------
# Point class
#---------------------------------------------------------------------------------------------------

class Point(object):
  """ basic 3D point class """
  def __init__(self, *xyz):
    object.__init__(self)
    self.x, self.y, self.z = parse_coordinates(*xyz)

  def copy(self):
    """ return a copy """
    return Point(self.x, self.y, self.z)

  def coordinates(self):
    """ return the coordinates as a tuple (x,y,z) """
    return (self.x, self.y, self.z)

  def __getitem__(self, key):
    """ implement list style access to coordinates: p[0], p[1], p[2] """
    return self.coordinates()[key]

  def __str__(self):
    """ string representation of a point """
    return '(%.2f,%.2f,%.2f)' % self.coordinates()

  def middle(self, other):
    """ return the middle point between self and another point """
    return Point((self.x + other.x)/2.0, (self.y + other.y)/2.0, (self.z + other.z)/2.0)

  def distanceSquared(self, other):
    """ return the squared distance to another point """
    return (self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2

  def distance(self, other):
    """ return the distance to another point """
    return numpy.sqrt(self.distanceSquared(other))

  def distanceXY(self, other):
    """ return the distance to another point, both projected to the xy-plane """
    return numpy.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

  def __eq__(self, other):
    """ check if points coincide """
    if other == None:
      return False
    return (self.distance(other) < EPSILON)

  def __ne__(self, other):
    """ check if points do not coincide """
    return not self.__eq__(other)

  def __cmp__(self, other):
    """ compare the coordinates, first x, then y, then z """
    if self.x == other.x:
      if (self.y == other.y):
        return (self.z < other.z)
      else:
        return (self.y < other.y)
    else:
      return (self.x < other.x)

  def projectXY(self, z = 0.0):
    """ return the projection of the point on the xy-plane """
    return Point(self.x, self.y, z)

  def transform(self, func):
    """ perform a coordinate transformation with the given function (x,y,z) to (x',y',z') """
    self.x, self.y, self.z = func((self.x, self.y, self.z))

  def plot(self, color = 'black', size = 5):
    """ plot the point in the xy-plane """
    pylab.plot([self.x], [self.y], color = color, linestyle = 'None', marker = '.', markersize = size)


#---------------------------------------------------------------------------------------------------
# Direction class
#---------------------------------------------------------------------------------------------------

class Direction(object):
  """ basic geometrical 3D direction class """
  def __init__(self, bearing, gradient = 0.0):
    object.__init__(self)
    # both bearing and gradient are stored in degrees
    self.bearing = bearing
    self.gradient = gradient

  def copy(self):
    """ return a copy """
    return Direction(self.bearing, self.gradient)

  def __getitem__(self, key):
    """ implement list style access to bearing and gradient """
    return (self.bearing, self.gradient)[key]

  def bearingRadians(self):
    """ return the bearing (horizontal angle with the x-axis) in radians """
    return numpy.radians(self.bearing)

  def gradientRadians(self):
    """ return the gradient (vertical angle with the xy-plane) in radians """
    return numpy.radians(self.gradient)

  def __str__(self):
    """ return a string representation of the direction """
    return '[%.2f,%.2f]' % (self.bearing, self.gradient)

  def __eq__(self, other):
    """ check if directions coincide """
    if other == None:
      return False
    db = abs(self.bearing - other.bearing)
    dg = abs(self.gradient - other.gradient)
    return (db <= EPSILON) and (dg <= EPSILON)

  def __ne__(self, other):
    """ check if directions do not coincide """
    return not self.__eq__(other)


def directionFromTo(p1, p2):
  """ returns the direction from point 1 to point 2 """
  (dx, dy, dz) = (p2.x - p1.x, p2.y - p1.y, p2.z - p1.z)
  siz = p1.distance(p2)
  return Direction(bearing = numpy.degrees(numpy.arctan2(dy, dx)), gradient = numpy.degrees(numpy.arcsin(dz/siz)))


#---------------------------------------------------------------------------------------------------
# Test code
#---------------------------------------------------------------------------------------------------

if __name__ == '__main__':

  points = []
  points.append(Point(1.2, 3.4))
  points.append(Point([5.6, 7.8, 9.0]))
  points.append(Point('(7.8, 9.0, 1.2)'))

  pylab.figure()
  for p in points:
    p.plot()

  try:
    pylab.show()
  except:
    pass
