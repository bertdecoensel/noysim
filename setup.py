#!/usr/bin/env python
"""Noysim: Noise simulation tools for Aimsun.

Noysim is a Python package for estimating road traffic noise
levels. It is especially designed for integration with the
microscopic traffic simulation tool Aimsun. It implements the
Imagine emission model and the ISO 9613 propagation model, and
provides basic tools for the construction of an Aimsun plugin.
"""

import os
import sys

from setuptools import setup, find_packages

# utility function to read the README file
def read(filename):
  return open(os.path.join(os.path.dirname(__file__), filename)).read()

# utility function to find all script files
def find_scripts():
  filenames = filter(lambda fn: os.path.splitext(fn)[1] == '.py', os.listdir('bin'))
  return [('bin/'+filename) for filename in filenames]

# main information
NAME         = 'noysim'
URL          = 'http://users.ugent.be/~bdcoense'
AUTHOR       = 'Bert De Coensel'
AUTHOR_EMAIL = 'bert.decoensel@intec.ugent.be'
PLATFORMS    = ['Windows']
MAJOR        = 2
MINOR        = 2
PATCH        = 1
PACKAGES     = []
COPYRIGHT    = '(c) Bert De Coensel, Griffith University & Ghent University, 2010-2011'
CLASSIFIERS  = ['Development Status :: 2 - Pre-Alpha',
                'Intended Audience :: Developers',
                'Intended Audience :: Science/Research',
                'Operating System :: Microsoft :: Windows',
                'Programming Language :: Python',
                'Topic :: Scientific/Engineering :: Atmospheric Science',
                'Topic :: Scientific/Engineering :: GIS',
                'Topic :: Scientific/Engineering :: Information Analysis']

# auto-generated information
DOCLINES         = __doc__.split("\n")
DESCRIPTION      = DOCLINES[0]
LONG_DESCRIPTION = '\n'.join(DOCLINES[2:])
VERSION          = '%d.%d.%d' % (MAJOR, MINOR, PATCH)

# create version file
file = open(NAME + '/version.py', 'w')
file.write('name = \'%s\'\n' % NAME)
file.write('version = \'%s\'\n' % VERSION)
file.write('copyright = \'%s\'\n' % COPYRIGHT)
file.write('email = \'%s\'\n' % AUTHOR_EMAIL)
file.close()

# perform setup
setup(name = NAME,
      version = VERSION,
      author = AUTHOR,
      author_email = AUTHOR_EMAIL,
      url = URL,
      description = DESCRIPTION,
      long_description = LONG_DESCRIPTION,
      platforms = PLATFORMS,
      packages = find_packages(),
      scripts = find_scripts(),
      classifiers = CLASSIFIERS)
