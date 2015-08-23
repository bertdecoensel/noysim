# Noysim -- Noise simulation tools for Aimsun.
# Copyright (c) 2010-2011 by Bert De Coensel, Ghent University & Griffith University.
#
# Classes for loading and saving the configuration

import os
import sys
import ConfigParser

import numpy
import pylab

if not hasattr(sys, 'frozen'):
  import wxversion
  wxversion.select('2.8-msw-unicode') # version of wxPython
import wx
from wx.lib.agw.floatspin import FloatSpin, EVT_FLOATSPIN

import version
from geo import Point
from emission import ImagineModel, SkewedNormalImagineCorrectionModel, DistributionImagineCorrectionModel, Roadsurface, RectangularViewport
from propagation import ISO9613Environment, ISO9613Model, Receiver


#---------------------------------------------------------------------------------------------------
# Default configuration
#---------------------------------------------------------------------------------------------------

# general emission model parameters
CFGEMODEL = [('emodel-name',                        'Imagine'), # kind of emission model
                                                                # options: 'Imagine', 'Imagine+SkewedNormal', 'Imagine+Distribution', ('Lookup': not implemented yet)
             # for the meaning of the Imagine parameters: see Deliverable 11 of the Imagine project
             # flags to switch corrections on/off (switching off corrections will make the model run faster)
             ('emodel-imagine-flag-acceleration',   'True'),
             ('emodel-imagine-flag-gradient',       'False'),
             ('emodel-imagine-flag-temperature',    'False'),
             ('emodel-imagine-flag-surface',        'False'),
             ('emodel-imagine-flag-wetness',        'False'),
             ('emodel-imagine-flag-axles',          'True'),
             ('emodel-imagine-flag-fleet',          'False'),
             # surface corrections (only applicable when emodel-imagine-flag-surface is True)
             ('emodel-imagine-surface-cat',         'REF'), # 'REF', 'DAC' or 'SMA'
             ('emodel-imagine-surface-temperature', '20.0'), # in degrees Celcius
             ('emodel-imagine-surface-chipsize',    '11.0'), # in mm
             ('emodel-imagine-surface-age',         '2.0'), # in years
             ('emodel-imagine-surface-wet',         'False'), # if True, the surface is wet
             ('emodel-imagine-surface-tc',          '0.08'), # temperature coefficient
             # fleet corrections (only applicable when emodel-imagine-flag-fleet is True)
             ('emodel-imagine-fleet-diesel',        '19.0'), # percentage of diesel vehicles for category 1
             ('emodel-imagine-fleet-tirewidth',     '187.0'), # average tire width in mm for category 1
             ('emodel-imagine-fleet-vans',          '10.5'), # percentage of delivery vans for category 1
             ('emodel-imagine-fleet-iress',         '1.0,35.0'), # % of illegal replacement exhaust silencer systems
                                                                 # for categories (1,2,3,5) and (4) respectively
             ('emodel-imagine-fleet-studs',         'False'), # if True, vehicles have studded tires
             # parameters for distributions on emission levels in case of 'Imagine+SkewedNormal' or 'Imagine+Distribution'
             ('emodel-random-seed',                 'None'), # seed value for random number generation (None = no seed set)
             ('emodel-skewednormal-stdev',          '0.0,0.0,0.0,0.0,0.0'), # one stdev for each Imagine vehicle category
             ('emodel-skewednormal-skew',           '0.0,0.0,0.0,0.0,0.0')] # one skewness value for each Imagine vehicle category
             # parameters for the lookup table emission model
             # no parameters yet

# viewport parameters (covering the area in which vehicles have to taken into account)
CFGVIEWPORT = [('viewport-rectangle', '-1000.0,-1000.0,1000.0,1000.0'), # dimensions of a rectangular viewport
               ('viewport-dynamic',   'True')] # if True, the viewport is constructed dynamically

# propagation model parameters
CFGPMODEL = [('pmodel-name',                                'ISO9613'), # propagation model (only ISO 9613 implemented)
             ('pmodel-iso9613-flag-geometric-divergence',   'True'),
             ('pmodel-iso9613-flag-atmospheric-absorption', 'True'),
             ('pmodel-iso9613-flag-ground-effect',          'True'),
             ('pmodel-iso9613-flag-source-directivity',     'True'),
             # environment corrections (only applicable with the atmospheric absorption / ground effect flag set to True)
             ('pmodel-iso9613-atmospheric-pressure',        '101325.0'), # in Pa
             ('pmodel-iso9613-atmospheric-temperature',     '20.0'), # in degrees Celcius
             ('pmodel-iso9613-atmospheric-humidity',        '70.0'), # in percentage
             ('pmodel-iso9613-ground-coeffs',               '0.0,0.0,0.0')] # coefficients for source, receiver and middle region
                                                                            # (0.0 = hard surface, 1.0 = soft surface)

# receiver parameters
CFGRECEIVERS = [('receivers-locations',        '(0.0,-15.0,2.0);(0.0,-30.0,2.0);(0.0,-60.0,2.0)'), # (x,y,z) locations
                ('receivers-background-level', '30.0')] # (constant) background level at the location of the receiver

# output options
CFGOUTPUT = [('output-path',    ''), # absolute path to the output directory (if empty, then all output goes to the network directory)
            ('output-filename', ''), # specific filename for output of the results
                                     # (if empty, the file has the form of out_xxx_a_b_c.xls(x) with auto-generated xxx)
            ('output-extension', 'xlsx'), # output file extension ('xls' or 'xlsx')
            ('output-spectra',  'True')] # if True, octave-band spectra are output for all receivers


# the configuration is just one big dictionary with string keys and values
SECTIONS = ['emodel', 'viewport', 'pmodel', 'receivers', 'output']
DEFAULT = {'emodel': CFGEMODEL, 'viewport': CFGVIEWPORT, 'pmodel': CFGPMODEL, 'receivers': CFGRECEIVERS, 'output': CFGOUTPUT}
DEFAULTDICT = {}
for section in SECTIONS:
  DEFAULTDICT.update(dict(DEFAULT[section]))


#---------------------------------------------------------------------------------------------------
# Main configuration class
#---------------------------------------------------------------------------------------------------

class Configuration(object):
  """ Plugin configuration class """
  def __init__(self):
    object.__init__(self)
    self.default()

  def default(self):
    """ set the state to the default state """
    self.data = DEFAULTDICT.copy()

  def save(self, filename):
    """ save the configuration to a textfile """
    file = open(filename, 'w')
    for section in SECTIONS:
      file.write('[%s]\n' % section)
      for key, value in DEFAULT[section]:
        file.write('%s = %s\n' % ('-'.join(key.split('-')[1:]), self.data[key]))
      file.write('\n')
    file.close()

  def load(self, filename):
    """ load a configuration from a textfile """
    if not os.path.exists(filename):
      raise Exception('The configuration file "%s" does not exist' % filename)
    try:
      config = ConfigParser.ConfigParser()
      config.read(filename)
    except:
      raise Exception('Unable to load configuration "%s" - the file contains errors' % filename)
    # construct dictionary with configuration values
    temp = {}
    for section in SECTIONS:
      for key, value in config.items(section):
        temp[section + '-' + key] = value.strip()
    # check if all necessary key-value pairs are present
    for key in DEFAULTDICT.keys():
      if not key in temp:
        raise Exception('Parameter "%s" is missing in configuration "%s"' % (key, filename))
    self.data = temp

  def set(self, key, value):
    """ set the key to the given value """
    self.data[key] = str(value)

  def get(self, key):
    """ return the value for the given key """
    return self.data[key].strip()

  def getBool(self, key):
    """ return a boolean instead of a string """
    try:
      return {'true': True, 'false': False}[self.get(key).lower()]
    except:
      raise Exception('configuration file: "%s" is not a valid boolean value - use "True" or "False"' % self.get(key))

  def getInt(self, key):
    """ return an integer instead of a string """
    try:
      return int(self.get(key))
    except:
      raise Exception('configuration file: "%s" is not a valid integer' % self.get(key))

  def getFloat(self, key):
    """ return a float instead of a string """
    try:
      return float(self.get(key))
    except:
      raise Exception('configuration file: "%s" is not a valid number - use "5" or "3.14"' % self.get(key))

  def road(self):
    """ construct a road object based on the stored parameters """
    if not hasattr(self, '_road'):
      # construct road surface
      cat = self.get('emodel-imagine-surface-cat')
      temperature = self.getFloat('emodel-imagine-surface-temperature')
      chipsize = self.getFloat('emodel-imagine-surface-chipsize')
      age = self.getFloat('emodel-imagine-surface-age')
      wet = self.getBool('emodel-imagine-surface-wet')
      tc = self.getFloat('emodel-imagine-surface-tc')
      self._road = Roadsurface(cat = cat, temperature = temperature, chipsize = chipsize, age = age, wet = wet, tc = tc)
    return self._road

  def emodel(self):
    """ construct an emission model object based on the stored parameters """
    if not hasattr(self, '_emodel'):
      emodelname = self.get('emodel-name').lower()
      # get seed value for random value generators
      seed = self.get('emodel-random-seed')
      if seed.lower() == 'none':
        seed = None
      else:
        seed = self.getInt('emodel-random-seed')
      # construct emission model
      if emodelname == 'imagine':
        # construct Imagine emission model
        self._emodel = ImagineModel()
      elif emodelname == 'imagine+skewednormal':
        # construct skewed normal correction emission model
        stdev = tuple([float(x) for x in self.get('emodel-skewednormal-stdev').strip('()').split(',')])
        skew = tuple([float(x) for x in self.get('emodel-skewednormal-skew').strip('()').split(',')])
        self._emodel = SkewedNormalImagineCorrectionModel(stdev = stdev, skew = skew, seed = seed)
      elif emodelname == 'imagine+distribution':
        # construct distribution correction emission model with default (Australian) corrections
        self._emodel = DistributionImagineCorrectionModel(seed = seed)
      elif emodelname == 'lookup':
        # this has to be filled in if the LookupModel emission model is to be used
        raise NotImplementedError
      else:
        raise Exception('configuration file: Emission model "%s" not known - use "Imagine", "Imagine+SkewedNormal", "Imagine+Distribution" or "Lookup"' % emodelname)
      # all current models use the Imagine model as a base, so update the corrections
      # adjust correction flags
      self._emodel.correction['acceleration'] = self.getBool('emodel-imagine-flag-acceleration')
      self._emodel.correction['gradient'] = self.getBool('emodel-imagine-flag-gradient')
      self._emodel.correction['temperature'] = self.getBool('emodel-imagine-flag-temperature')
      self._emodel.correction['surface'] = self.getBool('emodel-imagine-flag-surface')
      self._emodel.correction['wetness'] = self.getBool('emodel-imagine-flag-wetness')
      self._emodel.correction['axles'] = self.getBool('emodel-imagine-flag-axles')
      self._emodel.correction['fleet'] = self.getBool('emodel-imagine-flag-fleet')
      # adjust fleet correction parameters
      self._emodel.fleet['diesel'] = self.getFloat('emodel-imagine-fleet-diesel')
      self._emodel.fleet['tirewidth'] = self.getFloat('emodel-imagine-fleet-tirewidth')
      self._emodel.fleet['vans'] = self.getFloat('emodel-imagine-fleet-vans')
      self._emodel.fleet['iress'] = tuple([float(x) for x in self.get('emodel-imagine-fleet-iress').strip('()').split(',')])
      self._emodel.fleet['studs'] = self.getBool('emodel-imagine-fleet-studs')
    return self._emodel

  def environment(self):
    """ construct an environment object based on the stored parameters """
    if not hasattr(self, '_environment'):
      self.pmodel()
    return self._environment

  def pmodel(self):
    """ construct a propagation model object based on the stored parameters """
    if not hasattr(self, '_pmodel'):
      pmodelname = self.get('pmodel-name')
      if pmodelname == 'ISO9613':
        # create environment
        G = tuple([float(x) for x in self.get('pmodel-iso9613-ground-coeffs').strip('()').split(',')])
        p = self.getFloat('pmodel-iso9613-atmospheric-pressure')
        t = self.getFloat('pmodel-iso9613-atmospheric-temperature')
        r = self.getFloat('pmodel-iso9613-atmospheric-humidity')
        self._environment = ISO9613Environment(G = G, p = p, t = t, r = r)
        # create propagation model
        self._pmodel = ISO9613Model(environment = self._environment)
        self._pmodel.correction['geometricDivergence'] = self.getBool('pmodel-iso9613-flag-geometric-divergence')
        self._pmodel.correction['atmosphericAbsorption'] = self.getBool('pmodel-iso9613-flag-atmospheric-absorption')
        self._pmodel.correction['groundEffect'] = self.getBool('pmodel-iso9613-flag-ground-effect')
        self._pmodel.correction['sourceDirectivity'] = self.getBool('pmodel-iso9613-flag-source-directivity')
      else:
        raise Exception('configuration file: Propagation model "%s" not known - use "ISO9613"' % pmodelname)
    return self._pmodel

  def receivers(self):
    """ construct a list of receivers based on the stored parameters """
    if not hasattr(self, '_receivers'):
      locs = self.get('receivers-locations').strip()
      if len(locs) == 0:
        self._receivers = []
      else:
        points = [Point(x) for x in locs.split(';')]
        self._receivers = [Receiver(p) for p in points]
    return self._receivers

  def background(self):
    """ return the background level, or None if no value given (-100.0) """
    if not hasattr(self, '_background'):
      value = self.getFloat('receivers-background-level')
      if value == -100.0:
        self._background = None
      else:
        self._background = value
    return self._background

  def outputPath(self):
    """ return the output path as provided """
    return self.get('output-path')

  def outputFilename(self):
    """ return the output filename as provided """
    return self.get('output-filename')

  def outputExtension(self):
    """ return the output extension as provided """
    return self.get('output-extension')

  def saveSpectra(self):
    """ return True if the spectra have to be saved also """
    if not hasattr(self, '_saveSpectra'):
      self._saveSpectra = self.getBool('output-spectra')
    return self._saveSpectra

  def viewport(self):
    """ construct the viewport """
    if not hasattr(self, '_viewport'):
      (minx, miny, maxx, maxy) = tuple([float(x) for x in self.get('viewport-rectangle').strip('()').split(',')])
      if self.getBool('viewport-dynamic'):
        # use the dynamically created viewport
        #return DynamicViewport() # TODO: define this class (see above)
        self._viewport = RectangularViewport(minx, miny, maxx, maxy)
      else:
        # use the rectangular viewport
        self._viewport = RectangularViewport(minx, miny, maxx, maxy)
    return self._viewport

  def saveToWorksheet(self, excelFile, sheetName):
    """ save the configuration to an Excel worksheet """
    row = 0
    for section in SECTIONS:
      excelFile.setValue(sheetName, row, 0, section + ' parameters:', 'bold')
      row += 1
      for key, value in DEFAULT[section]:
        excelFile.setValue(sheetName, row, 0, '-'.join(key.split('-')[1:]))
        value = self.data[key]
        try:
          value = float(value)
        except:
          pass # write as string
        excelFile.setValue(sheetName, row, 1, value)
        row += 1
      row += 1 # empty line between sections
    # adjust column widths
    excelFile.setColumnWidth(sheetName, 0, 2+len('iso9613-flag-atmospheric-absorption'))


#---------------------------------------------------------------------------------------------------
# Configuration window
#---------------------------------------------------------------------------------------------------

class ConfigFrame(wx.Frame):
  """ configuration window class, shown at the start of the simulation,
      for picking the configuration file and setting visualization flags
  """
  def __init__(self, parent, id, title, defaultFile, defaultPath, app):
    wx.Frame.__init__(self, parent, id, title, style = wx.CAPTION | wx.TAB_TRAVERSAL | wx.CLIP_CHILDREN)
    self.defaultFile = defaultFile # the filename of the default config file
    self.defaultPath = defaultPath # the initial path that is given for the file picker dialog
    self.app = app # reference to the application that constructed this frame
    # dimensions of main panel
    fullWidth = 300
    buttonWidth = 100
    borderWidth = 10
    # create main panel
    mainPanel = wx.Panel(self, wx.ID_ANY)
    # create configuration widgets
    configBox = wx.StaticBox(mainPanel, wx.ID_ANY, label = 'Configuration file', style = wx.BORDER_SUNKEN)
    configBoxSizer = wx.StaticBoxSizer(configBox, wx.VERTICAL)
    self.configText = wx.TextCtrl(mainPanel, wx.ID_ANY, value = self.defaultFilename(), size = (fullWidth, -1), style = wx.TE_READONLY)
    self.createButton = wx.Button(mainPanel, wx.ID_ANY, label = 'Create...', size = (buttonWidth, -1))
    self.loadButton = wx.Button(mainPanel, wx.ID_ANY, label = 'Load...', size = (buttonWidth, -1))
    # layout configuration widgets
    configButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
    configButtonSizer.Add(self.createButton, flag = wx.ALL, border = 0)
    configButtonSizer.Add((fullWidth - 2*buttonWidth, -1), 1)
    configButtonSizer.Add(self.loadButton, flag = wx.ALL, border = 0)
    configBoxSizer.Add(self.configText, 0, wx.ALL, border = borderWidth)
    configBoxSizer.Add(configButtonSizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, border = borderWidth)
    configBoxSizer.Fit(configBox)
    # create visualization widgets
    visualBox = wx.StaticBox(mainPanel, wx.ID_ANY, label = 'Demonstration options', style = wx.BORDER_SUNKEN)
    visualBoxSizer = wx.StaticBoxSizer(visualBox, wx.VERTICAL)
    self.checkLevels = wx.CheckBox(mainPanel, wx.ID_ANY, label = ' Print A-weighted SPL at receivers to console')
    self.checkVehicles = wx.CheckBox(mainPanel, wx.ID_ANY, label = ' Print detailed vehicle information to console')
    self.checkTimeseries = wx.CheckBox(mainPanel, wx.ID_ANY, label = ' Send level timeseries at receivers to Viewer')
    # create slowdown spinbox
    self.slowdownTxt1 = wx.StaticText(mainPanel, -1, label = '       Slowdown: ')
    self.slowdownSpin = FloatSpin(mainPanel, -1, size = (60, -1), digits = 0, value = 0, min_val = 0, increment = 50)
    self.slowdownSpin.GetTextCtrl().SetEditable(False)
    self.slowdownTxt2 = wx.StaticText(mainPanel, -1, label = ' milliseconds/timestep')
    self.enableSlowdown(False)
    self.slowdownBoxSizer = wx.BoxSizer(wx.HORIZONTAL)
    self.slowdownBoxSizer.Add(self.slowdownTxt1, border=0, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
    self.slowdownBoxSizer.Add(self.slowdownSpin, border=0, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
    self.slowdownBoxSizer.Add(self.slowdownTxt2, border=0, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
    # layout visualization widgets
    visualBoxSizer.Add(self.checkLevels, 0, wx.ALL, border = borderWidth)
    visualBoxSizer.Add(self.checkVehicles, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, border = borderWidth)
    visualBoxSizer.Add(self.checkTimeseries, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, border = borderWidth)
    visualBoxSizer.Add(self.slowdownBoxSizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, border = borderWidth)
    visualBoxSizer.Add((fullWidth + 2*borderWidth, -1), 1)
    visualBoxSizer.Fit(visualBox)
    # create buttons
    self.disableButton = wx.Button(mainPanel, wx.ID_ANY, label = 'Disable plugin', size = (buttonWidth, -1))
    self.okButton = wx.Button(mainPanel, wx.ID_ANY, label = 'Ok', size = (buttonWidth, -1))
    okButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
    okButtonSizer.Add(self.disableButton, flag = wx.ALL, border = 0)
    okButtonSizer.Add((fullWidth + 3*borderWidth - 2*buttonWidth, -1), 1)
    okButtonSizer.Add(self.okButton, flag = wx.ALL, border = 0)
    # finally, add main sizer with border
    mainSizer = wx.BoxSizer(wx.VERTICAL)
    mainSizer.Add(configBoxSizer, 0, flag = wx.ALL, border = borderWidth)
    mainSizer.Add(visualBoxSizer, 0, flag = wx.LEFT | wx.RIGHT | wx.BOTTOM, border = borderWidth)
    mainSizer.Add(okButtonSizer, 0, flag = wx.LEFT | wx.RIGHT | wx.BOTTOM, border = borderWidth)
    mainPanel.SetSizerAndFit(mainSizer)
    self.Fit()
    # associate events with class methods
    self.createButton.Bind(wx.EVT_BUTTON, self.OnCreate)
    self.loadButton.Bind(wx.EVT_BUTTON, self.OnLoad)
    self.disableButton.Bind(wx.EVT_BUTTON, self.OnDisable)
    self.okButton.Bind(wx.EVT_BUTTON, self.OnOK)
    self.checkTimeseries.Bind(wx.EVT_CHECKBOX, self.OnTimeseries)
    self.okButton.SetFocus()
    # set result value to default
    self.checkFilename()
    self.app.result = None

  def defaultFilename(self):
    """ return the default filename, including the full path """
    return os.path.join(self.defaultPath, self.defaultFile)

  def checkFilename(self):
    """ check if the filename in the configText exists, and apply the necessary gui updates """
    # fetch the full filename
    filename = self.configText.GetValue()
    if os.path.exists(filename):
      # enable OK button
      self.okButton.Enable(True)
      return True
    else:
      # clear the filename box
      self.configText.SetValue('')
      # disable the OK button
      self.okButton.Enable(False)
      return False

  def enableSlowdown(self, flag=True):
    """ enable or disable the slowdown spinbox """
    for widget in [self.slowdownTxt1, self.slowdownSpin, self.slowdownTxt2]:
      widget.Enable(flag)

  def OnTimeseries(self, event):
    """ executed when the user toggles the checkTimeseries check box """
    self.enableSlowdown(self.checkTimeseries.GetValue())

  def OnCreate(self, event):
    """ executed when the user presses the Create button """
    # ask for filename
    dialog = wx.FileDialog(None, message = 'Save the configuration file as...', defaultDir = self.defaultPath,
                           wildcard = ('*.%s' % version.name), style = wx.SAVE | wx.FD_OVERWRITE_PROMPT)
    if dialog.ShowModal() == wx.ID_OK:
      # create a default configuration file
      filename = dialog.GetPath()
      cfg = Configuration()
      cfg.save(filename)
      # finally, update the filename box and the gui
      self.configText.SetValue(filename)
      self.checkFilename()

  def OnLoad(self, event):
    """ executed when the user presses the Load button """
    # show a file picker dialog
    dialog = wx.FileDialog(None, message = 'Select a configuration file', defaultDir = self.defaultPath,
                           wildcard = ('*.%s' % version.name), style = wx.OPEN)
    if dialog.ShowModal() == wx.ID_OK:
      self.configText.SetValue(dialog.GetPath())
      self.checkFilename()

  def OnDisable(self, event):
    """ executed when the user presses the Disable button """
    # close without a configuration filename (thus disable the plugin)
    self.app.result = (None, False, False, False, 0)
    self.Destroy()

  def OnOK(self, event):
    """ executed when the user presses the OK button """
    # fetch the options
    if self.checkFilename():
      self.app.result = (self.configText.GetValue(), self.checkLevels.GetValue(), self.checkVehicles.GetValue(),
                         self.checkTimeseries.GetValue(), self.slowdownSpin.GetValue())
      self.Destroy()


def showConfigurationWindow(defaultFile, defaultPath):
  """ show the configuration window and return the user choices """
  app = wx.PySimpleApp()
  title = '%s %s - configuration' % (version.name.capitalize(), version.version)
  app.frame = ConfigFrame(None, wx.ID_ANY, title, defaultFile = defaultFile, defaultPath = defaultPath, app = app)
  app.frame.Center()
  app.frame.Show()
  app.SetTopWindow(app.frame)
  app.MainLoop()
  return app.result


def loadConfiguration(defaultFile, defaultPath, batch=False):
  """ create and return a configuration object, together with visualization options
      if batch is True, no configuration window is shown, but the value supplied by defaultFile is returned
      (i.e. useful for running batch simulations without user intervention)
  """
  if batch == False:
    (filename, levels, vehicles, timeseries, slowdown) = showConfigurationWindow(defaultFile, defaultPath)
  else:
    filename = os.path.join(defaultPath, defaultFile)
    (levels, vehicles, timeseries, slowdown) = (False, False, False, 0)
  if filename == None:
    cfg = None
  else:
    # create the configuration object
    cfg = Configuration()
    cfg.load(filename)
  return (cfg, levels, vehicles, timeseries, slowdown)


#---------------------------------------------------------------------------------------------------
# Test code
#---------------------------------------------------------------------------------------------------

if __name__ == '__main__':

  if len(sys.argv) <= 1:
    # no command line argument, so test showing the configuration screen
    print showConfigurationWindow(defaultFile = 'default.noysim', defaultPath = os.getcwd())

  if (len(sys.argv) == 2) and (sys.argv[1] == 'default'):
    # create a new default configuration file in the current directory
    print 'creating a new default configuration file...'
    cfg = Configuration()
    cfg.save('default.noysim')

  if (len(sys.argv) == 2) and (sys.argv[1] == 'test'):
    # test the configuration object with default arguments
    cfg = Configuration()
    print cfg.road()
    print cfg.emodel()
    print cfg.environment()
    print cfg.pmodel()
    print [str(rec) for rec in cfg.receivers()]
    print cfg.background()
    print cfg.outputPath()
    print cfg.outputFilename()
    print cfg.outputExtension()
    print cfg.saveSpectra()
    print cfg.viewport()
