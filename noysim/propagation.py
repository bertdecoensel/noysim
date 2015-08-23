# Noysim -- Noise simulation tools for Aimsun.
# Copyright (c) 2010-2011 by Bert De Coensel, Ghent University & Griffith University.
#
# Noise propagation model functions and classes

import numpy
import pylab

from acoustics import LOWDB, fromdB, OctaveBandSpectrum
from geo import EPSILON, Point, Direction, asPoint, asDirection
from emission import QLDCar, QLDBDouble, ImagineModel


#---------------------------------------------------------------------------------------------------
# Basic classes
#---------------------------------------------------------------------------------------------------

class Receiver(object):
  """ base class modelling a receiver """
  def __init__(self, position):
    # in the most simple case, a receiver is characterized by its position
    # detailed propagation models may want to define a subclass with additional receiver characteristics
    # (e.g. direction of head in case of human listener, if the listener is wearing a hearing protector etc.)
    object.__init__(self)
    self.position = position

  def __str__(self):
    """ return a string representation of the receiver """
    return '[p=%s]' % str(self.position)


class Environment(object):
  """ base class modelling the propagation environment """
  def __init__(self):
    # in the most simple case, the environment is empty (free field)
    # detailed propagation models may want to define a subclass with additional environment characteristics
    # (type of ground surface, terrain model, location of buildings, facade characteristics, meteo properties etc.)
    object.__init__(self)

  def __str__(self):
    """ return a string representation of the environment """
    return '[free field]'


class PropagationModel(object):
  """ base propagation model interface """
  def __init__(self, environment):
    # in the most simple case, the propagation model only needs to know the characteristics of the environment
    # detailed propagation models may want to have more a priori knowledge about the receivers,
    # e.g. in order to pre-calculate propagation paths
    object.__init__(self)
    self.environment = environment

  def __str__(self):
    """ return a string representation of the propagation model """
    return '[PropagationModel]'

  def zero(self):
    """ should return the immission in case there are no sources """
    raise NotImplementedError

  def immission(self, source, receiver):
    """ calculate the immission spectrum at the location of the receiver, caused by the emission of the given source.
        this method should calculate the attenuation between source and receiver cause by the environment,
        apply this attenuation to the source spectrum, and return the resulting spectrum as output
    """
    raise NotImplementedError

  def totalImmission(self, sources, receiver):
    """ calculates the immission spectrum at the location of the receiver, cause by the emission of all source in the supplied list """
    if len(sources) == 0:
      return self.zero()
    result = self.immission(sources[0], receiver)
    for source in sources[1:]:
      result += self.immission(source, receiver)
    return result


#---------------------------------------------------------------------------------------------------
# ISO 9613-2 propagation model
#---------------------------------------------------------------------------------------------------

# default environment values
REFGROUND = (0.0, 0.0, 0.0)
REFPRESSURE = 101325.0
REFTEMPERATURE = 20.0
REFHUMIDITY = 70.0


class ISO9613Environment(Environment):
  """ class implementing the basic environment characteristics used in the ISO 9613-2 model;
      barriers or other types of attenuation (foliage, industrial installations, houses) are not taken into account,
      and the model assumes that all vehicles are driving on a flat surface at height 0.0 (otherwise, a terrain model should be added)
  """
  def __init__(self, G = REFGROUND, p = REFPRESSURE, t = REFTEMPERATURE, r = REFHUMIDITY):
    Environment.__init__(self)
    self.G = G # coefficients for surface at (source, receiver, middle region), with 0.0 meaning hard and 1.0 meaning soft
    self.p = p # air pressure [Pa]
    self.t = t # temperature [degrees Celcius]
    self.r = r # relative humidity [%]
    # pre-calculate absorption coefficients for all octave band frequencies
    self.abscoeff = self.absorptionCoefficient(f = OctaveBandSpectrum().frequencies())

  def hasHardSurface(self):
    """ return True if the surface is hard """
    return self.G == REFGROUND

  def hasDefaultMeteo(self):
    """ return True if the meteo conditions have the default values """
    return (self.p, self.t, self.r) == (REFPRESSURE, REFTEMPERATURE, REFHUMIDITY)

  def terrainHeight(self, position):
    """ return the height of the terrain at the given position.
        as implemented, it is assumed that the terrain is flat and at height 0.0;
        subclasses could implement a more detailed terrain model (e.g. loaded from file)
    """
    return 0.0

  def __str__(self):
    """ return a string representation of the environment """
    return '[ISO9613: G=(%.2f,%.2f,%.2f), p=%.1f, t=%.1f, r=%.1f]' % (self.G[0], self.G[1], self.G[2], self.p, self.t, self.r)

  def absorptionCoefficient(self, f):
    """ return the atmospheric absorption coefficient of air in dB/m, for the current meteo, at the given frequency """
    t = self.t + 273.15 # conversion to Kelvin
    p = self.p/101325.0 # conversion to relative pressure
    C = 4.6151 - 6.8346*((273.16/t)**1.261)
    h = self.r*(10**C)*p
    tr = t/293.15 # conversion to relative air temperature (re 20 degrees Celcius)
    FRo = p*(24.0 + 40400.0*h*(0.02 + h)/(0.391 + h))
    FRn = p*(tr**(-0.5))*(9.0 + 280.0*h*(numpy.exp(-4.17*((tr**(-1.0/3.0))-1.0))))
    temp = 8.686*(tr**(-2.5))
    FC1 = 8.686*(1.84e-11)*(1.0/p)*numpy.sqrt(tr)
    FC2 = temp*0.01275*numpy.exp(-2239.1/t)
    FC3 = temp*0.1068*numpy.exp(-3352.0/t)
    f2 = f**2
    fo = FRo + f2/FRo
    fn = FRn + f2/FRn
    return f2*(FC1 + (FC2/fo) + (FC3/fn))


class ISO9613Model(PropagationModel):
  """ class implementing the ISO 9613-2 propagation model
      reference: ISO 9613-2:1996, 'Acoustics - Attenuation of sound during propagation
                                   outdoors - Part 2: General method of calculation'
      Notes:
      - only attenuation caused by geometrical divergence, atmospheric absorption and ground effect are considered
      - the model additionally takes into account the directivity of the source (as described in the source model)
      - the model only works in octave bands, so source spectra are, in a first step, transformed to octave band spectra
  """
  def __init__(self, environment = ISO9613Environment()):
    PropagationModel.__init__(self, environment)
    self.correction = {'geometricDivergence': True, 'atmosphericAbsorption': True, 'groundEffect': True, 'sourceDirectivity': True}

  def __str__(self):
    """ return a string representation of the propagation model """
    return '[ISO9613 propagation model]'

  def zero(self):
    """ return the immission in case there are no sources (empty octave-band spectrum) """
    return OctaveBandSpectrum()

  def immission(self, source, receiver):
    """ calculate the immission spectrum at the location of the receiver, caused by the emission of the given source """
    result = source.emission.octaveBandSpectrum() # ISO 9613 only works on octave bands
    if self.correction['geometricDivergence'] == True:
      result.correct(self.geometricDivergence(source, receiver))
    if self.correction['atmosphericAbsorption'] == True:
      result.correct(self.atmosphericAbsorption(source, receiver))
    if self.correction['groundEffect'] == True:
      result.correct(self.groundEffect(source, receiver))
    if self.correction['sourceDirectivity'] == True:
      result.correct(self.sourceDirectivity(source, receiver))
    return result

  def geometricDivergence(self, source, receiver):
    """ return the attenuation (in dB) caused by geometric divergence in air """
    return -20.0*numpy.log10(receiver.position.distance(source.position)) - 11.0

  def atmosphericAbsorption(self, source, receiver):
    """ return the attenuation (in dB) caused by atmospheric absorption in air """
    return -self.environment.abscoeff * receiver.position.distance(source.position)

  def groundEffect(self, source, receiver):
    """ return the attenuation/amplification (in dB) caused by the ground effect """
    distance = receiver.position.distanceXY(source.position) # distance in XY-plane
    sourceH = source.position.z - self.environment.terrainHeight(source.position)
    recH = receiver.position.z - self.environment.terrainHeight(receiver.position)
    # shorthand for hard surfaces
    if self.environment.hasHardSurface():
      if distance > EPSILON:
        return 3.0 - min(0.0, -3.0 + 90.0*(sourceH + recH)/distance)
      else:
        return 3.0
    # temporary constants
    x = 1.0 - numpy.exp(-distance/50.0)
    y = 1.0 - numpy.exp(-(2.8e-6)*(distance**2))
    G = self.environment().G
    # calculating attenuation at source
    (h1, h2) = ((sourceH - 5.0)**2, sourceH**2)
    aa = 1.5 +  3.0*numpy.exp(-0.12*h1)*x + 5.7*numpy.exp(-0.09*h2)*y
    bb = 1.5 +  8.6*numpy.exp(-0.09*h2)*x
    cc = 1.5 + 14.0*numpy.exp(-0.46*h2)*x
    dd = 1.5 +  5.0*numpy.exp(-0.90*h2)*x
    a = numpy.asarray([-1.5,           -1.5 + G[0]*aa,    -1.5 + G[0]*bb,    -1.5 + G[0]*cc,
                       -1.5 + G[0]*dd, -1.5*(1.0 - G[0]), -1.5*(1.0 - G[0]), -1.5*(1.0 - G[0])])
    # calculating attenuation at observer
    (h1, h2) = ((recH - 5.0)**2, recH**2)
    aa = 1.5 +  3.0*numpy.exp(-0.12*h1)*x + 5.7*numpy.exp(-0.09*h2)*y
    bb = 1.5 +  8.6*numpy.exp(-0.09*h2)*x
    cc = 1.5 + 14.0*numpy.exp(-0.46*h2)*x
    dd = 1.5 +  5.0*numpy.exp(-0.90*h2)*x
    a += numpy.asarray([-1.5,           -1.5 + G[1]*aa,    -1.5 + G[1]*bb,    -1.5 + G[1]*cc,
                        -1.5 + G[1]*dd, -1.5*(1.0 - G[1]), -1.5*(1.0 - G[1]), -1.5*(1.0 - G[1])])
    # calculation attenuation in middle region
    mind = 30.0*(sourceH + recH)
    if distance > EPSILON:
      Dm = min(0.0, -3.0 + 3.0*(mind/distance))
    else:
      Dm = 0.0
    a += numpy.asarray([Dm] + 7*[Dm*(1.0 - G[2])])
    return -a

  def sourceDirectivity(self, source, receiver):
    """ return the attenuation/amplification (in dB) caused by the directivity of the source """
    # calculate angles between source and receiver
    dx = receiver.position.x - source.position.x
    dy = receiver.position.y - source.position.y
    dz = receiver.position.z - source.position.z
    theta = numpy.angle(numpy.complex(dx, dy), deg = True) - source.direction.bearing
    phi = numpy.degrees(numpy.arctan2(dz, numpy.sqrt(dx**2 + dy**2)))
    # Note: the calculation of phi neglects the bearing and gradient of the source (vehicle), but this will
    # usually be a small number, and the Harmonoise/Imagine model assumes that the vertical directivity of
    # the noise emitted by a vehicle is the same for all horizontal angles, so this approximation can be justified
    return numpy.asarray([source.directivity(theta = theta, phi = phi, f = f) for f in OctaveBandSpectrum().frequencies()])


#---------------------------------------------------------------------------------------------------
# Calculating and drawing noise maps
#---------------------------------------------------------------------------------------------------

class Noisemap(object):
  """ class for calculating and drawing noise maps (A-weighted SPL, uncorrelated sources) """
  def __init__(self, pmodel, recx, recy, recz):
    self.pmodel = pmodel # propagation model to be used
    self.recx = recx # range of x values for the map
    self.recy = recy # range of x values for the map
    self.recz = recz # height of the grid for the map
    self.clear()

  def clear(self):
    """ clear the noisemap """
    self.energy = numpy.zeros((len(self.recx),len(self.recy)))

  def add(self, source):
    """ add the effect of a single source to the noise map """
    for i in range(len(self.recx)):
      for j in range(len(self.recy)):
        receiver = Receiver(position = Point(self.recx[i], self.recy[j], self.recz))
        level = pmodel.immission(source, receiver).laeq() # A-weighted SPL at receiver
        self.energy[i,j] += fromdB(level)

  def plot(self, interval = None, cbar = True):
    """ draw the noisemap, within given interval and with/without a colorbar """
    # calculate the noise levels
    levels = 10.0*numpy.log10(self.energy)
    levels[numpy.where(levels == -numpy.inf)] = LOWDB
    if interval == None:
      # try to estimate the best interval
      interval = (numpy.min(levels), numpy.max(levels))
    im = pylab.imshow(levels.T, cmap = pylab.cm.jet, vmin = interval[0], vmax = interval[1], origin = 'lower')
    im.set_interpolation('nearest') # shading ?
    pylab.axis('auto') # image ?
    if cbar == True:
      pylab.colorbar()
    # fix axis labels
    (nx, ny) = (len(self.recx), len(self.recy))
    ix = [0, nx/4, nx/2, 3*(nx/4)]
    iy = [0, ny/4, ny/2, 3*(ny/4)]
    pylab.xticks(ix, [('%.1f' % self.recx[i]) for i in ix])
    pylab.yticks(iy, [('%.1f' % self.recy[i]) for i in iy])


#---------------------------------------------------------------------------------------------------
# Test code
#---------------------------------------------------------------------------------------------------

if __name__ == '__main__':

  # test of propagation model
  if 1:
    vehicle = QLDCar(position = Point(0.0, 0.0, 0.0), direction = Direction(0.0, 0.0), speed = 70.0, acceleration = 0.0)
    emodel = ImagineModel()
    sources = emodel.sources(vehicle = vehicle)
    receiver = Receiver(position = Point(0.0, 10.0, 0.0))
    environment = ISO9613Environment(G = (0.0, 0.0, 0.0))
    pmodel = ISO9613Model(environment = environment)
    # switching corrections on/off
    pmodel.correction['geometricDivergence']   = True
    pmodel.correction['atmosphericAbsorption'] = True
    pmodel.correction['groundEffect']          = True
    pmodel.correction['sourceDirectivity']     = True
    # plotting both spectra at source and receiver
    pylab.figure()
    ncols = len(sources)
    for i, source in enumerate(sources):
      pylab.subplot(1, ncols, i+1)
      pylab.title('source at height %.2f' % source.position.z)
      emission = source.emission.octaveBandSpectrum()
      immission = pmodel.immission(source, receiver)
      interval = (30.0, 100.0)
      em = emission.plot(interval = interval, width = 0.3, shift = -0.15, color = 'blue')
      im = immission.plot(interval = interval, width = 0.3, shift = 0.15, color = 'green')
      pylab.legend((em[0], im[0]), ('sound power level of source', 'immision sound pressure level'))

  # test of calculating noise maps
  if 1:
    print 'testing propagation model...'
    # construction of vehicles
    vehicles = [QLDCar(position = Point(-5.0, -20.0), direction = Direction(45.0), speed = 70.0, acceleration = 0.0),
                QLDBDouble(position = Point(20.0, 20.0), direction = Direction(90.0), speed = 50.0, acceleration = 0.0)]
    # construction of emission and propagation model
    emodel = ImagineModel()
    environment = ISO9613Environment(G = (0.0, 0.0, 0.0))
    pmodel = ISO9613Model(environment = environment)
    # switching corrections on/off
    pmodel.correction['geometricDivergence']   = True
    pmodel.correction['atmosphericAbsorption'] = True
    pmodel.correction['groundEffect']          = True
    pmodel.correction['sourceDirectivity']     = True
    # properties of the noise map
    r = numpy.arange(-50.0, 50.0, 1.0)
    h = 2.0 # height of the receivers
    # construct the noise map
    noisemap = Noisemap(pmodel = pmodel, recx = r, recy = r, recz = h)
    i = 0
    for vehicle in vehicles:
      sources = emodel.sources(vehicle = vehicle)
      for source in sources:
        i += 1
        print 'adding source', i
        noisemap.add(source)
    # finally, plot the noisemap
    pylab.figure()
    noisemap.plot()


  try:
    pylab.show()
  except:
    pass
