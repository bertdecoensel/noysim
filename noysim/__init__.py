# Noysim -- Noise simulation tools for Aimsun.
# Copyright (c) 2010-2011 by Bert De Coensel, Ghent University & Griffith University.
#
# Package placeholder

import sys

# check Python version
if sys.version_info[:2] < (2, 6):
  raise Warning('Noysim requires Python 2.6 or later')

# set Noysim version
import version
__version__ = version.version # Noysim version

# import modules
import viewer
import geo
import excel
import numeric
import acoustics
import emission
import propagation
import config
import aimsuntools
import trafficsim
import analysis