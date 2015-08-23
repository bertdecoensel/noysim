# Noysim -- Aimsun plugin for calculating road traffic noise.
# Copyright (c) 2010-2011 by Bert De Coensel, Ghent University & Griffith University.

# batch mode constants
BATCHMODE = False # set to True if batch calculations are needed (no user intervention)
BATCHCONFIG = 'default' # configuration filename in case of batch calculations

# standard python modules
import os
import sys
import distutils.sysconfig

# define base paths
AIMSUNPATH = os.path.sep.join(sys.argv[0].split(os.path.sep)[:-1]) # location of Aimsun.exe
SCRIPTPATH = os.path.dirname(os.path.realpath(__file__)) # location of this file
NETWORKPATH = os.getcwd() # Aimsun start location
# Note: NETWORKPATH will not work as desired when Aimsun is started from the desktop icon or the start menu

# add necessary paths to the python search path list
sys.path.append(os.path.join(AIMSUNPATH, 'programming', 'Scripting', 'libs')) # scripting modules
sys.path.append(os.path.join(AIMSUNPATH, 'programming', 'AAPI61', 'AAPIPython')) # Aimsun API module
sys.path.append(distutils.sysconfig.get_python_lib()) # installed modules from the host python installation
sys.path.append(SCRIPTPATH) # user scripts

# third-party libraries (have to be installed on the host system)
import noysim

# define plugin metadata
NAME = noysim.version.name.capitalize() # name of the plugin
VERSION = noysim.version.version # version of the plugin
COPYRIGHT = ' '.join([NAME, VERSION, noysim.version.copyright])

# import Aimsun Application Programmers Interface (AAPI)
try:
  import AAPI
  from AAPI import *
except ImportError as e:
  print NAME, 'can only be run as a plugin inside Aimsun'
  raise e
noysim.aimsuntools.setAimsunAPI(AAPI)

# global plugin variables, automatically assigned during simulation
DISABLED = False # if set to True, the plugin is disabled
CONFIGURATION = None # Configuration object
INFOLEVELS = None # if True, the A-weighted SPL at all receivers at each timestep is printed on the console window
INFOVEHICLES = None # if True, additional vehicle information is printed on the console window
VIEWER = None # if True, the timeseries of A-weighted SPL at the receivers is send to the viewer
SLOWDOWN = 0 # additional time (in milliseconds) between timesteps, to slow down the simulation for visualization
NETWORK = None # AimsunNetwork object, for gathering network related information
VEHICLES = None # VehicleInfo object, for gathering vehicle related information
NOISE = None # NoiseImmission object, for calculating and saving noise immissions
BUFFER = None # LevelBuffer object, for sending levels to the viewer


#---------------------------------------------------------------------------------------------------
# Aimsun callbacks
#---------------------------------------------------------------------------------------------------

def AAPIInit():
  """ called when the simulation is started """
  global DISABLED
  if not DISABLED:
    try:
      # print copyright message
      AKIPrintString(COPYRIGHT)
      # fetch the network units and check if they are metric
      if noysim.aimsuntools.getNetworkUnits() != 'metric':
        raise Exception(NAME + ' only accepts networks coded in metric units')
      # load the configuration and visualization options (using a configuration settings screen)
      global CONFIGURATION, INFOLEVELS, INFOVEHICLES, VIEWER, SLOWDOWN, NETWORK, VEHICLES, NOISE, BUFFER
      defaultFile = {False: 'default', True: BATCHCONFIG}[BATCHMODE] + '.' + NAME.lower()
      cfg = noysim.config.loadConfiguration(defaultFile = defaultFile, defaultPath = SCRIPTPATH, batch = BATCHMODE)
      (CONFIGURATION, INFOLEVELS, INFOVEHICLES, VIEWER, SLOWDOWN) = cfg
      if CONFIGURATION == None:
        # the user disabled the plugin
        DISABLED = True
        AKIPrintString(NAME + ' is disabled')
      else:
        # construct network and vehicle related objects
        NETWORK = noysim.aimsuntools.AimsunNetwork()
        VEHICLES = noysim.aimsuntools.VehicleInfo(CONFIGURATION)
        NOISE = noysim.aimsuntools.NoiseImmission(CONFIGURATION)
        # construct viewer communication object
        BUFFER = noysim.viewer.createLevelBuffer(active = VIEWER, sleep = SLOWDOWN)
        BUFFER.sendClear()
    except Exception as e:
      DISABLED = True
      AKIPrintString(NAME + ' is set to inactive because of errors (see below)')
      raise e
  return 0


def AAPIManage(timeSim, timeSta, timeTrans, timeStep):
  """ called at the beginning of every simulation step
      timeSim: absolute time of simulation (in seconds)
      timeSta: time of simulation in stationary period (in seconds)
      timeTrans: duration of warm-up period (in seconds)
      timeStep: duration of each simulation step (in seconds)
  """
  global DISABLED
  if not DISABLED:
    try:
      if timeSim >= timeTrans: # do not consider warm-up period
        # get a list with all vehicles
        vehicles = VEHICLES.getVehicles(timeSta, timeStep)
        # if necessary, print vehicle information
        if INFOVEHICLES:
          AKIPrintString('vehicles at time %.2f:' % timeSta)
          [AKIPrintString(str(vehicle)) for vehicle in vehicles]
        # calculate noise levels
        levels = NOISE.update(timeSta, vehicles)
        # send the levels to the viewer
        BUFFER.sendLevels(timeSta, levels)
        # if necessary, print the total A-weighted SPL at each receiver
        if INFOLEVELS:
          AKIPrintString(('Time: %.2fs' % timeSta) + ' -> SPL: ' + ' '.join([('[%s: %.1f dBA]' % (str(p), v)) for p, v in levels.iteritems()]))
    except Exception as e:
      DISABLED = True
      AKIPrintString(NAME + ' is set to inactive because of errors (see below)')
      raise e
  return 0


def AAPIFinish():
  """ called when the simulation is finished """
  global DISABLED
  if not DISABLED:
    try:
      # construct filename for saving results
      filename = NETWORK.createFullOutputFilename(NETWORKPATH, CONFIGURATION.outputPath(), CONFIGURATION.outputFilename(), CONFIGURATION.outputExtension())
      AKIPrintString('Saving results to file "%s"...' % filename)
      # create Excel workbook
      wb = noysim.excel.ExcelWorkbook(CONFIGURATION.outputExtension())
      # write simulation settings and results to file
      wb.createSheets(['simulation', 'plugin', 'counts', 'levels', 'indicators'])
      NETWORK.saveToWorksheet(wb, 'simulation')
      CONFIGURATION.saveToWorksheet(wb, 'plugin')
      VEHICLES.saveToWorksheet(wb, 'counts')
      NOISE.saveTimeseries(wb, 'levels', VEHICLES.passbys)
      NOISE.saveIndicators(wb, 'indicators')
      NOISE.saveSpectra(wb)
      # finally, save the workbook
      wb.save(filename)
    except Exception as e:
      DISABLED = True
      AKIPrintString(NAME + ' is set to inactive because of errors (see below)')
      raise e
  return 0


def AAPILoad():
  """ called when the module is loaded into Aimsun """
  return 0

def AAPIPostManage(timeSim, timeSta, timeTrans, timeStep):
  """ called at the end of every simulation step """
  return 0

def AAPIUnLoad():
  """ called when the module is unloaded """
  return 0

def AAPIEnterVehicle(idveh, idsection):
  """ called when a new vehicle enters the simulation """
  return 0

def AAPIExitVehicle(idveh, idsection):
  """ called when a vehicle reaches its destination """
  return 0
