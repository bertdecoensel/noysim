#!/usr/bin/env python
"""Noysim: Noise simulation tools for Aimsun.

Noysim is a Python package for estimating road traffic noise
levels. It is especially designed for integration with the
microscopic traffic simulation tool Aimsun. It implements the
Imagine emission model and the ISO 9613 propagation model, and
provides basic tools for the construction of an Aimsun plugin.
"""

from distutils.core import setup

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

# auto-generated information
DOCLINES         = __doc__.split("\n")
DESCRIPTION      = DOCLINES[0]
LONG_DESCRIPTION = '\n'.join(DOCLINES[2:])
VERSION          = '%d.%d.%d' % (MAJOR, MINOR, PATCH)
FULLPACKAGES     = [NAME] + [(NAME + '.' + p) for p in PACKAGES]

if __name__ == '__main__':

  # create version file
  file = open(NAME + '/version.py', 'w')
  file.write('name = \'%s\'\n' % NAME)
  file.write('version = \'%s\'\n' % VERSION)
  file.write('copyright = \'%s\'\n' % COPYRIGHT)
  file.write('email = \'%s\'\n' % AUTHOR_EMAIL)
  file.close()

  # perform setup
  setup(name=NAME,
        version=VERSION,
        platforms=PLATFORMS,
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        author=AUTHOR,
        author_email=AUTHOR_EMAIL,
        url=URL,
        packages=FULLPACKAGES)

# optional additional arguments to setup:
# package_dir={NAME: 'src'})
