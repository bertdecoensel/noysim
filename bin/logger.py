# Noysim -- Aimsun plugin for calculating road traffic noise.
# Copyright (c) 2010-2011 by Bert De Coensel, Ghent University & Griffith University.
#
# "logger.py": simple plugin that logs vehicle information at each timestep

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
COPYRIGHT = ' '.join(['logger.py', noysim.version.copyright])

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
FILENAME = None # output logger file


#---------------------------------------------------------------------------------------------------
# Utility function
#---------------------------------------------------------------------------------------------------

def vehicleInformation(sInf, dInf, timeStep):
  """ return the necessary vehicle information """
  # fetch the vehicle ID and dimensions (to estimate emission class)
  (vID, vLength, vWidth) = (sInf.idVeh, sInf.length, sInf.width)
  # calculate position (middle point) and direction (bearing and gradient) of vehicle
  vPosFront = noysim.geo.Point(dInf.xCurrentPos, dInf.yCurrentPos, dInf.zCurrentPos)
  vPosBack = noysim.geo.Point(dInf.xCurrentPosBack, dInf.yCurrentPosBack, dInf.zCurrentPosBack)
  vPosition = vPosFront.middle(vPosBack)
  vDirection = noysim.geo.directionFromTo(vPosBack, vPosFront)
  # fetch speed [km/h] and acceleration [m/s^2]
  vSpeed = dInf.CurrentSpeed
  vAcceleration = (dInf.CurrentSpeed - dInf.PreviousSpeed)/(3.6*timeStep)
  # return information
  return (vID, (vLength, vPosition.x, vPosition.y, vDirection.bearing, vSpeed, vAcceleration))


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
        raise Exception('logger.py only accepts networks coded in metric units')
      # construct output filename
      global FILENAME
      FILENAME = os.path.join(NETWORKPATH, 'logger.txt')
    except Exception as e:
      DISABLED = True
      AKIPrintString('logger.py is set to inactive because of errors (see below)')
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
        data = []
        # loop over vehicles on sections
        for i in range(AIMSUN.AKIInfNetNbSectionsANG()):
          sectionID = AIMSUN.AKIInfNetGetSectionANGId(i)
          for j in range(AIMSUN.AKIVehStateGetNbVehiclesSection(sectionID, True)):
            sInf = AIMSUN.AKIVehGetVehicleStaticInfSection(sectionID, j)
            dInf = AIMSUN.AKIVehStateGetVehicleInfSection(sectionID, j)
            data.append(vehicleInformation(sInf, dInf, timeStep))
        # loop over vehicles on junctions
        for i in range(AIMSUN.AKIInfNetNbJunctions()):
          junctionID = AIMSUN.AKIInfNetGetJunctionId(i)
          for j in range(AIMSUN.AKIVehStateGetNbVehiclesJunction(junctionID)):
            sInf = AIMSUN.AKIVehGetVehicleStaticInfJunction(junctionID, j)
            dInf = AIMSUN.AKIVehStateGetVehicleInfJunction(junctionID, j)
            data.append(vehicleInformation(sInf, dInf, timeStep))
        # finally, save data to file
        file = open(FILENAME, 'a')
        file.write('%.3f\n' % timeSta)
        for vID, vInfo in data:
          file.write('%d\t' % vID)
          file.write('\t'.join([('%.1f' % x) for x in vInfo]) + '\n')
        file.close()
    except Exception as e:
      DISABLED = True
      AKIPrintString('logger.py is set to inactive because of errors (see below)')
      raise e
  return 0


def AAPIFinish():
  """ called when the simulation is finished """
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
