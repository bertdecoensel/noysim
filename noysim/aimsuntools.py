# Noysim -- Noise simulation tools for Aimsun.
# Copyright (c) 2010-2011 by Bert De Coensel, Ghent University & Griffith University.
#
# Utility functions on top of the Aimsun API

import os
import math

import numpy

import geo
import acoustics
import emission


#---------------------------------------------------------------------------------------------------
# Link to the Aimsun API
#---------------------------------------------------------------------------------------------------

AIMSUN = None

def setAimsunAPI(module):
  """ supply a link to the Aimsun API module """
  global AIMSUN
  AIMSUN = module


#---------------------------------------------------------------------------------------------------
# Retrieving network information
#---------------------------------------------------------------------------------------------------

def getNetworkUnits():
  """ return the network units """
  return {0: 'english', 1: 'metric'}[AIMSUN.AKIInfNetGetUnits()]


class AimsunNetwork(object):
  """ class bundling all Aimsun network and simulation information """
  def __init__(self):
    object.__init__(self)
    # set demand type
    self.demandType = {1: 'odmatrix', 2: 'trafficstate'}[AIMSUN.AKIInfNetGetTrafficDemandType()]
    # fetch and save the speed limits and demands of the network
    self.vlimits = {} # dict with section speed limits
    self.demands = {} # dict with traffic state demands for all sections
    self._runNumber = 0 # default value if none is generated
    for i in range(AIMSUN.AKIInfNetNbSectionsANG()):
      sectionID = AIMSUN.AKIInfNetGetSectionANGId(i)
      self.vlimits[sectionID] = AIMSUN.AKIInfNetGetSectionANGInf(sectionID).speedLimit
      if self.demandType == 'trafficstate': # when the traffic demand is set by OD matrices, this is not very useful
        # save total demand for all Aimsun vehicle types, for all temporal slices
        #self.demands[sectionID] = [AIMSUN.AKIStateDemandGetDemandSection(sectionID, 0, i) for i in range(AIMSUN.AKIStateDemandGetNumSlices())]
        # update: save demands for each vehicle type separately
        self.demands[sectionID] = [[AIMSUN.AKIStateDemandGetDemandSection(sectionID, j+1, i) for j in range(AIMSUN.AKIVehGetNbVehTypes())] for i in range(AIMSUN.AKIStateDemandGetNumSlices())]

  def createFullOutputFilename(self, networkPath, outputPath, outputFilename, outputExtension):
    """ return the full filename for outputting the results """
    if not hasattr(self, '_outputFilename'):
      assert outputExtension in ('xls', 'xlsx')
      # create the path
      path = outputPath # as retrieved from the configuration file
      if path == '':
        path = networkPath # use the current working directory (where the network is situated)
      # create the base network name
      # Note: using the python Aimsun API, it is unfortunately not possible to retrieve the network name or network path,
      #       so a workaround is provided using the simulation scenario, experiment and replica ID's
      networkName = outputFilename # as retrieved from the configuration file
      if networkName == '':
        networkName = 'scen%d_exp%d_repl%d' % (AIMSUN.ANGConnGetScenarioId(), AIMSUN.ANGConnGetExperimentId(), AIMSUN.ANGConnGetReplicationId())
      filename = ('out_%s' % networkName)
      # add maximum speed limit for any given section
      maxv = max(self.vlimits.values())
      filename += '_%dkph' % maxv
      # add total demand in network during first timeslice
      if len(self.demands) != 0:
        sumd = sum([sum(x[0]) for x in self.demands.values()])
        filename += '_%dvph' % sumd
      # finally, generate run number
      self._runNumber = 0
      while True:
        self._runNumber += 1
        self._outputFilename = os.path.join(path, filename + ('_run%.3d.%s' % (self._runNumber, outputExtension)))
        if not os.path.exists(self._outputFilename):
          break
    return self._outputFilename

  def saveToWorksheet(self, excelFile, sheetName):
    """ save the network and simulation information to the given Excel worksheet """
    row = 0
    excelFile.setValue(sheetName, row, 0, 'General information:', 'bold'); row += 1
    excelFile.setValue(sheetName, row, 0, 'Scenario ID'); excelFile.setValue(sheetName, row, 1, AIMSUN.ANGConnGetScenarioId()); row += 1
    excelFile.setValue(sheetName, row, 0, 'Experiment ID'); excelFile.setValue(sheetName, row, 1, AIMSUN.ANGConnGetExperimentId()); row += 1
    excelFile.setValue(sheetName, row, 0, 'Replication ID'); excelFile.setValue(sheetName, row, 1, AIMSUN.ANGConnGetReplicationId()); row += 1
    excelFile.setValue(sheetName, row, 0, 'Run number'); excelFile.setValue(sheetName, row, 1, self._runNumber); row += 2 # blank line
    excelFile.setValue(sheetName, row, 0, 'Timing information:', 'bold'); row += 1
    excelFile.setValue(sheetName, row, 0, 'Predefined duration [s]:'); excelFile.setValue(sheetName, row, 1, AIMSUN.AKIGetEndSimTime() - AIMSUN.AKIGetIniSimTime(), 'float'); row += 1
    excelFile.setValue(sheetName, row, 0, 'Warm-up period [s]:'); excelFile.setValue(sheetName, row, 1, AIMSUN.AKIGetDurationTransTime(), 'float'); row += 1
    excelFile.setValue(sheetName, row, 0, 'Actually simulated [s]:'); excelFile.setValue(sheetName, row, 1, AIMSUN.AKIGetTimeSta(), 'float'); row += 1
    excelFile.setValue(sheetName, row, 0, 'Time step [s]:'); excelFile.setValue(sheetName, row, 1, AIMSUN.AKIGetSimulationStepTime(), 'float'); row += 2
    # save speed limits
    excelFile.setValue(sheetName, row, 0, 'Speed limits for each section [km/h]:', 'bold'); row += 1
    for sectionID, vLimit in self.vlimits.iteritems():
      excelFile.setValue(sheetName, row, 0, sectionID); excelFile.setValue(sheetName, row, 1, vLimit); row += 1
    row += 1
    # save vehicle demands
    excelFile.setValue(sheetName, row, 0, 'Demands for each section, traffic state and vehicle category [vehicles/h]:', 'bold'); row += 1
    nTrafficStates = AIMSUN.AKIStateDemandGetNumSlices()
    nVehCats = AIMSUN.AKIVehGetNbVehTypes()
    # save subheader
    header = ['Section', 'State', 'Total'] + [('VType%.2d' % (i+1)) for i in range(nVehCats)]
    for i, token in enumerate(header):
      excelFile.setValue(sheetName, row, i, token)
    row += 1
    # save actual demand data
    sectionIDs = self.demands.keys() + ['Total']
    dMatrices = self.demands.values()
    dMatrices += [numpy.sum([dMatrix for dMatrix in self.demands.values()], axis=0).tolist()]
    for sectionID, dMatrix in zip(sectionIDs, dMatrices):
      for state in range(nTrafficStates):
        excelFile.setValue(sheetName, row, 0, sectionID)
        excelFile.setValue(sheetName, row, 1, state+1)
        excelFile.setValue(sheetName, row, 2, sum(dMatrix[state]))
        for i, x in enumerate(dMatrix[state]):
          excelFile.setValue(sheetName, row, 3+i, x)
        row += 1
    # adjust column widths
    excelFile.setColumnWidth(sheetName, 0, 2+len('Predefined duration [s]:'))

#---------------------------------------------------------------------------------------------------
# Retrieving vehicle information
#---------------------------------------------------------------------------------------------------

# Mapping between aimsun vehicles and the vehicle classes of the emission model
# Note: because there is no easy way to get the vehicle class names from Aimsun via a python plugin,
#       and vehicle types as extracted through the Aimsun API are just numbers, which could differ between networks,
#       a shortcut is taken via the vehicle size, which should give a (hopefully unique) cue for the vehicle class.
# In the following dictionary, the key provides the vehicle length and width intervals, while the value is a tuple containing:
# - the emission model vehicle class (e.g. 1 to 5 for the Imagine model)
# - a fitting class as defined in emission.py, which supplies the remaining settings that do not make
#   part of aimsun but could be of interest for the emission model (e.g. number of axles, double-mounting of wheels,...)
VEHICLETYPES = {(( 3.0,  5.0), (2.0, 2.0)): (1, emission.QLDCar),
                (( 5.0,  9.0), (2.0, 2.0)): (1, emission.QLDVan),
                ((10.0, 14.0), (2.5, 2.5)): (2, emission.QLDLightTruck),
                ((19.0, 19.0), (2.5, 2.5)): (3, emission.QLDSemiTrailer),
                ((25.0, 25.0), (2.5, 2.5)): (3, emission.QLDBDouble),
                (( 1.5,  1.5), (0.6, 0.6)): (5, emission.QLDMotorcycle)}


class VehicleInfo(object):
  """ class bundling all Aimsun vehicle information (during simulation) """
  def __init__(self, configuration):
    object.__init__(self)
    self.viewport = configuration.viewport() # necessary to filter the vehicles of interest
    self.emodel = configuration.emodel() # necessary to get the names of the relevant vehicle emission classes
    # dynamic information, filled during simulation
    self.vtypes = {} # dictionary with vehicle ID's and vehicle types
    self.counts = {} # dictionary with vehicle counts on all sections (one list with vehicle ID's for every emission class)
    for i in range(AIMSUN.AKIInfNetNbSectionsANG()):
      sectionID = AIMSUN.AKIInfNetGetSectionANGId(i)
      self.counts[sectionID] = [[] for name in self.emodel.categoryNames()]
    # vehicle pass-bys at the origin (only useful for test networks with a single road along the x-axis)
    self.vlocs = {} # dictionary with vehicle locations along the x-axis (-1 or 1)
    self.passbys = [] # list of vehicle pass-bys

  def getVehicleType(self, vID, vLength, vWidth):
    """ return the vehicle type, based on its dimensions (length and width) """
    # check if we encountered the vehicle before
    if vID in self.vtypes:
      return self.vtypes[vID]
    # otherwise, guess the vehicle type based on its size
    for interval, vType in VEHICLETYPES.iteritems():
      if (interval[0][0] <= vLength) and (vLength <= interval[0][1]) and (interval[1][0] <= vWidth) and (vWidth <= interval[1][1]):
        self.vtypes[vID] = vType
        return vType
    raise Exception('could not classify vehicle %d' % vID)

  def createVehicle(self, sInf, dInf, timeStep):
    """ create a vehicle object from aimsun static and dynamic information objects, and the simulation timeStep """
    # fetch static vehicle information
    vID = sInf.idVeh
    (vLength, vWidth) = (sInf.length, sInf.width)
    (vMaxSpeed, vMaxDecel, vMaxAccel) = (sInf.maxDesiredSpeed, -sInf.maxDeceleration, sInf.maxAcceleration)
    # fetch the vehicle type and emission class
    cat, vehicleClass = self.getVehicleType(vID, vLength, vWidth)
    # calculate position (middle point) and direction (bearing and gradient) of vehicle
    vPosFront = geo.Point(dInf.xCurrentPos, dInf.yCurrentPos, dInf.zCurrentPos)
    vPosBack = geo.Point(dInf.xCurrentPosBack, dInf.yCurrentPosBack, dInf.zCurrentPosBack)
    vPosition = vPosFront.middle(vPosBack)
    vDirection = geo.directionFromTo(vPosBack, vPosFront)
    # fetch speed [km/h] and acceleration [m/s^2]
    vSpeed = dInf.CurrentSpeed
    vAcceleration = (dInf.CurrentSpeed - dInf.PreviousSpeed)/(3.6*timeStep)
    # finally, construct vehicle
    return vehicleClass(vid = vID, length = vLength, width = vWidth, cat = cat,
                        maxspeed = vMaxSpeed, maxdecel = vMaxDecel, maxaccel = vMaxAccel,
                        position = vPosition, direction = vDirection, speed = vSpeed, acceleration = vAcceleration)

  def getVehicles(self, timeSta, timeStep):
    """ return a list with all the vehicles currently in the network, taking into account the viewport """
    vehicles = []
    # fetch vehicles on sections
    for i in range(AIMSUN.AKIInfNetNbSectionsANG()):
      sectionID = AIMSUN.AKIInfNetGetSectionANGId(i)
      for j in range(AIMSUN.AKIVehStateGetNbVehiclesSection(sectionID, True)):
        sInf = AIMSUN.AKIVehGetVehicleStaticInfSection(sectionID, j)
        dInf = AIMSUN.AKIVehStateGetVehicleInfSection(sectionID, j)
        vehicle = self.createVehicle(sInf, dInf, timeStep)
        if self.viewport(vehicle):
          vehicles.append(vehicle)
        # side-effect: update vehicle counts for this section
        clist = self.counts[sectionID][vehicle.cat()-1]
        if not vehicle.vid() in clist:
          # the vehicle is new, so add it to the section count
          clist.append(vehicle.vid())
    # fetch vehicles on junctions
    for i in range(AIMSUN.AKIInfNetNbJunctions()):
      junctionID = AIMSUN.AKIInfNetGetJunctionId(i)
      for j in range(AIMSUN.AKIVehStateGetNbVehiclesJunction(junctionID)):
        sInf = AIMSUN.AKIVehGetVehicleStaticInfJunction(junctionID, j)
        dInf = AIMSUN.AKIVehStateGetVehicleInfJunction(junctionID, j)
        vehicle = self.createVehicle(sInf, dInf, timeStep)
        if self.viewport(vehicle):
          vehicles.append(vehicle)
    # side-effect: update pass-bys
    for vehicle in vehicles:
      # fetch x-coordinate (1 for positive or zero, -1 for negative)
      vloc = int(math.copysign(1.0, vehicle.position().x))
      # check if the vehicle has passed the origin
      vID = vehicle.vid()
      if (vID in self.vlocs) and (vloc != self.vlocs[vID]):
        self.passbys.append((timeSta, vID, self.emodel.categoryNames()[vehicle.cat()-1], vehicle.speed()))
      self.vlocs[vID] = vloc
    return vehicles

  def saveToWorksheet(self, excelFile, sheetName):
    """ save the vehicle information to the given Excel worksheet """
    row = 0
    # save vehicle counts
    excelFile.setValue(sheetName, row, 0, 'Vehicle counts for each section (per emission class):', 'bold'); row += 1
    [excelFile.setValue(sheetName, row, i+1, name) for i, name in enumerate(['Total'] + self.emodel.categoryNames())]; row += 1
    for sectionID, clist in self.counts.iteritems():
      clist = [len(x) for x in clist] # actually performs the counting
      excelFile.setValue(sheetName, row, 0, sectionID)
      excelFile.setValue(sheetName, row, 1, sum(clist))
      [excelFile.setValue(sheetName, row, i+2, c) for i, c in enumerate(clist)]
      row += 1
    row += 1
    # save vehicle pass-bys at the origin
    excelFile.setValue(sheetName, row, 0, 'Vehicle pass-bys at the origin (only useful for test networks with a single road along the x-axis):', 'bold'); row += 1
    [excelFile.setValue(sheetName, row, i, token) for i, token in enumerate(['Time', 'vID', 'Category', 'Speed', 'Level at Rcvr01'])]; row += 1
    for (t, vID, cat, speed) in self.passbys:
      excelFile.setValue(sheetName, row, 0, t, 'float')
      excelFile.setValue(sheetName, row, 1, vID)
      excelFile.setValue(sheetName, row, 2, cat)
      excelFile.setValue(sheetName, row, 3, speed, 'float')
      # formula: add lookup to level at first receiver
      if excelFile.canHaveColumnRanges():
        formula = "vlookup(A%d,levels!A:B,2,false)" % (row+1)
      else:
        formula = "vlookup(A%d,levels!A1:B65536,2,false)" % (row+1)
      excelFile.setFormula(sheetName, row, 4, formula, 'float')
      row += 1


#---------------------------------------------------------------------------------------------------
# Calculation of noise immissions
#---------------------------------------------------------------------------------------------------

# Note: at the start of the simulation, a RoadSurface object is created which models the surface of
# the road throughout the network, based on the values in the configuration file. At each timestep,
# the plugin creates a list of Vehicle objects, using the functions available in the Aimsun API for
# retrieving vehicle properties. Only vehicles that are within the defined viewport are considered.
# Subsequently, for each vehicle, a list of sources is calculated using an EmissionModel object. The
# sources of all vehicles are then supplied to a PropagationModel object, which calculates the noise
# immission at a defined set of Receiver objects, taking into account basic environmental properties
# defined in an Environment object.

class NoiseImmission(object):
  """ class for calculating and saving noise immissions """
  def __init__(self, configuration):
    object.__init__(self)
    self.configuration = configuration
    self.results = [] # list with noise results at each timestep
    self.receivers = self.configuration.receivers()
    self.rpos = [r.position for r in self.receivers]

  def update(self, timeSta, vehicles):
    """ calculates emissions, propagation and immission, and saves results; should be called once each timestep """
    # calculate the list of sources
    sources = []
    for vehicle in vehicles:
      sources += self.configuration.emodel().sources(vehicle = vehicle)
    # calculate immission at receivers
    immi = [self.configuration.pmodel().totalImmission(sources, receiver) for receiver in self.receivers]
    laeqs = [spectrum.laeq() for spectrum in immi]
    # add background level (only to the total level because nothing is known about the spectral shape of the background)
    bg = self.configuration.background()
    if bg != None:
      laeqs = [acoustics.plusdB(x, bg) for x in laeqs]
    # store the results
    self.results.append((timeSta, immi, laeqs))
    # finally, return a dict of levels for all receivers
    return dict(zip(self.rpos, laeqs))

  def saveTimeseries(self, excelFile, sheetName, passbys):
    """ save the A-weighted SPL timeseries to the given Excel worksheet """
    # fill passby dictionary
    pbdict = {}
    for (t, vID, cat, speed) in passbys:
      if not (t in pbdict):
        pbdict[t] = []
      pbdict[t] += [(cat, speed)]
    # write out header
    header = ['Time'] + [('Rcvr%.2d' % (i+1)) for i in range(len(self.receivers))] + ['Passbys', 'Category', 'Speed']
    for i, token in enumerate(header):
      excelFile.setValue(sheetName, 0, i, token)
    # write out data
    pbcol = len(self.rpos) + 1
    for i, (t, immi, laeqs) in enumerate(self.results):
      excelFile.setValue(sheetName, i+1, 0, t, 'float')
      for j, laeq in enumerate(laeqs):
        excelFile.setValue(sheetName, i+1, j+1, laeq, 'float')
      pb = 0
      if t in pbdict:
        pb = len(pbdict[t])
        excelFile.setValue(sheetName, i+1, pbcol+1, str(pbdict[t][0][0])) # cat of first pass-by
        excelFile.setValue(sheetName, i+1, pbcol+2, float(pbdict[t][0][1]), 'float') # speed of first pass-by
      excelFile.setValue(sheetName, i+1, pbcol, pb)

  def saveSpectra(self, excelFile):
    """ add worksheets to the given workbook, for each receiver, with the spectra over time """
    if self.configuration.saveSpectra():
      for r in range(len(self.receivers)):
        # each receiver has its own sheet
        sheetName = 'spectra%.2d' % (r+1)
        excelFile.createSheets([sheetName])
        header = ['Time'] + [(f + 'Hz') for f in acoustics.LOCTAVE]
        for i, token in enumerate(header):
          excelFile.setValue(sheetName, 0, i, token)
        for i, (t, immi, laeqs) in enumerate(self.results):
          excelFile.setValue(sheetName, i+1, 0, t, 'float')
          for j, level in enumerate(immi[r].amplitudes()):
            excelFile.setValue(sheetName, i+1, j+1, level, 'float')

  def saveIndicators(self, excelFile, sheetName):
    """ save a series of acoustical indicators for each receiver to the given Excel worksheet """
    nrecv = len(self.receivers)
    # write out header
    header = ['Indicator'] + [('Rcvr%.2d' % (i+1)) for i in range(nrecv)]
    for i, token in enumerate(header):
      excelFile.setValue(sheetName, 0, i, token)
    # construct timeseries objects and calculate indicators (only meaningful if at least one timestep was simulated)
    if len(self.results) > 0:
      dt = AIMSUN.AKIGetSimulationStepTime()
      tsList = [acoustics.TimeSeries(z = [laeqs[i] for (t, immi, laeqs) in self.results], dt = dt) for i in range(nrecv)]
      indicators = [ts.indicators() for ts in tsList]
      # write out results
      for i, indicator in enumerate(acoustics.TimeSeries.INDICATORLIST):
        excelFile.setValue(sheetName, i+1, 0, indicator)
        for j in range(nrecv):
          excelFile.setValue(sheetName, i+1, j+1, indicators[j][indicator], 'float')
