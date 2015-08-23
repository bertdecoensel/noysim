# Noysim

Noysim is a free, open source Python package for estimating road traffic noise levels. It is especially designed for integration with the microscopic traffic simulation tool Aimsun. It implements the Imagine emission model and the ISO 9613 propagation model, and provides basic tools for the construction of an Aimsun plugin. Noysim requires both
[Aimsun](http://www.aimsun.com/) and [Python](http://www.python.org/).

## Python installation

Aimsun/Noysim requires that Python 2.6 (32-bit) is installed on the host system (website: http://www.python.org/download/releases/2.6.5/).

## Additional libraries

Next to the Python interpreter, the following free and open source libraries have to be installed:

* [Numpy](http://numpy.scipy.org/). This is a widely used package for scientific computing with Python, providing functions for linear algebra, Fourier transformation and random numbers.
* [Matplotlib](http://matplotlib.sourceforge.net/). This library provides plotting functionality for Python, producing publication quality figures, with a set of functions familiar to MATLAB users.
* [wxPython](http://www.wxpython.org/). This toolkit provides a wrapper around the popular wxWidgets cross-platform Graphical User Interface (GUI) library, allowing to create programs in Python with a robust, highly functional graphical user interface.
* [Xlwt](http://pypi.python.org/pypi/xlwt/). This library makes it possible to use simple Python commands to generate xls spreadsheet files that are compatible with MS Excel.
* [RPyC](http://rpyc.wikidot.com/). This library implements remote procedure calls and facilities for distributed computing, useful to allow inter-process communication.
* [Scipy](http://www.scipy.org/). This is a widely used package for scientific computing with Python, providing additional numerical routines on top of Numpy.
* [OpenPyXL](http://pypi.python.org/pypi/openpyxl/). This library makes it possible to use simple Python commands to generate xlsx spreadsheet files that are compatible with MS Excel 2007 and higher.

To install the above libraries, just download them and run the installer. It will find the installation path of python automatically. The above list will now and then be updated with the latest versions of the libraries if necessary. To update a library, simply download and re-install the library.

## Noysim installation

The Noysim software consists of a Python library containing the underlying code for Noysim. This library has to be installed in the same way as the libraries above. Next to this, a number of scripts are provided:

* **`plugin.py`**, the plugin file. This file should be saved to your computer (e.g. in a central folder or into a folder where the Aimsun networks are located). In order to use this Noysim plugin, networks have to load this file through the AAPI. This can be done by double-clicking on a scenario, selecting the Aimsun API tab, and adding the plugin.py file to the bottom list (make sure the check box is marked). See the manual for more information.
* `**runviewer.pyw**`, the viewer application. This file can be saved to the desktop, and can be run to show the viewer application for real time visualization of noise levels, by double-clicking on the icon. The viewer window will be shown only if all the above libraries are installed correctly.
* `**diagnostics.py**`, a diagnostics script. Save this file to your computer and double-click the icon to run it. It will show a console window with useful information about the installation. If all lines start with OK, then noysim was installed correctly.
* `**logger.py**`, a script that simply logs simulations for further analysis.
