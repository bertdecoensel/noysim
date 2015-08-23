# Noysim -- Aimsun plugin for calculating road traffic noise.
# Copyright (c) 2010-2011 by Bert De Coensel, Ghent University & Griffith University.
#
# Script for verifying the correct installation of Noysim

import os
import sys
import distutils.version


result = []
print 'checking installation...'


# check version of operating system
if sys.platform == 'win32':
  result.append('OK: Operating system MS Windows')
else:
  result.append('Error: operating system not MS Windows')

# check version of python interpreter
v = sys.version_info
if (v[0] == 2) and (v[1] == 6):
  result.append('OK: Python version 2.6')
else:
  result.append('Error: Python version is %d.%d, should be at least 2.6' % (v[0], v[1]))


def checkVersion(module, minVersion):
  """ check if a module is installed and if the version is at least the one given """
  # try to import the module
  try:
    m = __import__(module)
  except:
    return 'Error: module %s not installed (correctly)' % module
  # try to fetch the version information
  if hasattr(m, '__version__'):
    v = m.__version__
  elif hasattr(m, '__VERSION__'):
    v = m.__VERSION__
  else:
    return 'Error: module %s has no version information' % module
  # try to parse the version information
  try:
    if type(v) is tuple:
      v = '.'.join([str(x) for x in v])
    v = distutils.version.StrictVersion(v)
  except:
    return 'Error: module %s - version number %s is not valid' % (module, str(v))
  # finally, compare version to minimum version
  if v >= minVersion:
    return 'OK: module %s version %s installed' % (module, str(v))
  else:
    return 'Error: module %s version is %s but should be at least %s' % (module, str(v), minVersion)


def checkWxPython(version):
  """ check if the specified version of wxPython is installed """
  # try to import the module
  try:
    import wxversion
  except:
    return 'Error: module wxPython not installed (correctly)'
  # check if the specified version is available
  v = wxversion.getInstalled()
  if version in v:
    return 'OK: module wxPython version %s installed' % version
  else:
    return 'Error: module wxPython version should be at least %s (installed: %s)' % (version, ', '.join(v))


# check versions of additional modules
result.append(checkVersion('numpy', '1.6.1'))
result.append(checkVersion('scipy', '0.10.0b2'))
result.append(checkVersion('matplotlib', '1.0.0'))
result.append(checkVersion('xlwt', '0.7.2'))
result.append(checkVersion('openpyxl', '1.5.4'))
result.append(checkVersion('rpyc', '3.1.0'))
result.append(checkWxPython('2.8-msw-unicode'))
result.append(checkVersion('noysim', '2.2.0'))
result = '\n'.join(result)


# copy result to clipboard
from Tkinter import Tk
r = Tk()
r.withdraw()
r.clipboard_clear()
r.clipboard_append(result)
r.destroy()


# print result to screen
print result
os.system('pause')
