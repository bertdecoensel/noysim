# Noysim -- Noise simulation tools for Aimsun.
# Copyright (c) 2010-2011 by Bert De Coensel, Ghent University & Griffith University.
#
# Classes for sending and viewing noise levels in real-time

import os
import sys
import socket
import threading
import time
import random
import msvcrt

if not hasattr(sys, 'frozen'):
  import wxversion
  wxversion.select('2.8-msw-unicode') # version of wxPython
import wx
from wx.lib.agw.floatspin import FloatSpin, EVT_FLOATSPIN

import matplotlib
matplotlib.use('WXAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigCanvas, NavigationToolbar2WxAgg as NavigationToolbar

import numpy
import pylab

USERPYC = True # if set to False, low level sockets are used
if USERPYC:
  try:
    # check if rpyc is installed
    import rpyc
    from rpyc.utils.server import ThreadedServer
    from rpyc.utils.classic import DEFAULT_SERVER_PORT
    from rpyc.utils.registry import UDPRegistryClient
    from rpyc.core import SlaveService
  except:
    # revert to using low level sockets
    USERPYC = False
    raise Exception('rpyc has to be installed')

import version


#---------------------------------------------------------------------------------------------------
# Parameters
#---------------------------------------------------------------------------------------------------

# general parameters
NAME = '%s %s Viewer' % (version.name.capitalize(), version.version)
ABOUT = NAME + '\n\n' + version.copyright.replace(', ', '\n') + '\n' + version.email

# communication with level viewer
RPYCTHREAD = None # global level thread variable (needed to circumvent the rpyc service factory)
HOST = 'localhost'
PORT = 50007
TIMEOUT = 0.01
SLEEP = 0.001
BUFSIZE = 4096

# timing parameters
REDRAWTIME = 100 # number of milliseconds between redraws
FLASHTIME = 1500 # duration of messages on the status bar, in milliseconds

# visualisation parameters
DPI = 100 # dots per inch for plotting and saving
FIGSIZE = (3.0, 3.0) # size of plotting canvas in inches (defaults to 300x300 pixels)
FONTSIZE = 8 # size of font of labels
BGCOLOR = 'black'
GRIDCOLOR = 'gray'
LINECOLOR = 'yellow'
LINEWIDTH = 1

# axes parameters
SPININC = 5.0 # increment of spin controls
XMIN = 10.0 # minimal x-axis range width
XWIDTH = 30.0 # initial value of x-axis range width
YMIN = (0.0, 10.0) # minimal y-axis low and height
YRANGE = (30.0, 60.0) # initial values of y-axis low and height
MARGIN = 1.0 # margin for auto range of levels

# test parameters
TESTDT = 0.5 # simulation timestep in seconds
TESTSLEEP = 0.2 # time between level updates
TESTLOCS = ['(1.00,2.00,3.00)', '(4.00,5.00,6.00)'] # locations of test receivers
randomLevel = lambda: 40.0 + 30.0*random.random() # function that generates a random sound level


#---------------------------------------------------------------------------------------------------
# Communication from plugin to viewer
#---------------------------------------------------------------------------------------------------

class LevelBuffer(object):
  """ base interface for sending levels to the viewer, implementing the one-way communication protocol
      types of messages:
      - command: 'clear'
      - levels: 't;loc:level;loc:level'
  """
  def __init__(self, host = HOST, port = PORT, active = True, sleep = 0, verbose = False):
    object.__init__(self)
    self.host = host
    self.port = port
    self.queue = [] # queue of messages to send
    self.active = active # if False, nothing is sent
    self.sleep = sleep/1000.0 # time to sleep (in seconds) after sending levels (to slow down a simulation)
    self.verbose = verbose # if True, debug code is printed

  def sendLevels(self, t, levels):
    """ send a series of levels at a particular time at different locations (dict of location:level) """
    if self.active:
      message = ('%.2f;' % t) + ';'.join([('%s:%.2f' % (str(loc), level)) for loc, level in levels.iteritems()])
      self.queue.append(message)
      self.flush()
      if self.sleep > 0.0:
        time.sleep(self.sleep)

  def sendClear(self):
    """ send a 'clear' message """
    if self.active:
      message = 'clear'
      self.queue.append(message)
      self.flush()

  def send(self, message):
    """ should send a single message string to the viewer (raise an error if not succesful) """
    raise NotImplementedError

  def flush(self):
    """ try to send all message strings in the queue to the viewer """
    while (len(self.queue) > 0) and (self.active == True):
      message = self.queue[0]
      try:
        if self.verbose:
          print 'trying to send message "%s"' % message
        self.send(message)
        # remove message from queue
        del self.queue[0]
        if self.verbose:
          print 'sending succesful'
      except:
        if self.verbose:
          print 'sending failed - aborting - length of queue: %d' % len(self.queue)
        break


class SocketLevelBuffer(LevelBuffer):
  """ implement the level buffer using low level sockets """
  def __init__(self, *args, **kwargs):
    LevelBuffer.__init__(self, *args, **kwargs)

  def send(self, message):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((self.host, self.port))
    s.sendall(message)
    s.close()


class RPyCLevelBuffer(LevelBuffer):
  """ implement the level buffer using Remote Python Calls (RPyC) """
  def __init__(self, *args, **kwargs):
    LevelBuffer.__init__(self, *args, **kwargs)

  def send(self, message):
    conn = rpyc.classic.connect('localhost')
    conn.root.processMessage(message)
    conn.close()


def createLevelBuffer(*args, **kwargs):
  """ create a level buffer according to the defined protocol """
  if USERPYC:
    return RPyCLevelBuffer(*args, **kwargs)
  else:
    return SocketLevelBuffer(*args, **kwargs)


#---------------------------------------------------------------------------------------------------
# Viewer thread for receiving levels
#---------------------------------------------------------------------------------------------------

VIEWERLOCK = threading.Lock()

class BaseLevelThread(threading.Thread):
  """ base interface for a thread for receiving levels """
  def __init__(self):
    threading.Thread.__init__(self)
    self.active = True # set this to false for the thread to stop
    self.clear()

  def clear(self):
    """ clear all data """
    VIEWERLOCK.acquire()
    self.data = {} # dict with received levels, for each receiver location
    self.times = [] # list with times
    VIEWERLOCK.release()

  def locations(self):
    """ return the receiver locations """
    VIEWERLOCK.acquire()
    result = self.data.keys()[:]
    VIEWERLOCK.release()
    return result

  def levels(self, loc):
    """ return the times and levels at the given location """
    VIEWERLOCK.acquire()
    result = (numpy.asarray(self.times).copy(), numpy.asarray(self.data[loc]).copy())
    VIEWERLOCK.release()
    return result


class DummyLevelThread(BaseLevelThread):
  """ dummy interface for receiving levels, which adds levels at regular instances in time """
  def __init__(self, dt = TESTDT, sleep = TESTSLEEP, locs = TESTLOCS):
    BaseLevelThread.__init__(self)
    self.dt = dt
    self.sleep = sleep
    self.locs = locs

  def run(self):
    """ instantiate the server """
    print 'thread started...'
    t = 0.0
    while self.active:
      t += self.dt
      VIEWERLOCK.acquire()
      self.times.append(t)
      for loc in self.locs:
        if not loc in self.data:
          self.data[loc] = []
        level = randomLevel()
        self.data[loc].append(level)
        print 'level received succesfully: time %.2fs, %s, %.2f dB' % (t, loc,level)
      VIEWERLOCK.release()
      time.sleep(self.sleep)


class ViewerLevelThread(BaseLevelThread):
  """ interface for receiving levels, as a thread that runs a server which listens to new levels """
  def __init__(self, frame = None, host = HOST, port = PORT, verbose = False):
    BaseLevelThread.__init__(self)
    self.frame = frame # frame to which the thread is connected
    self.host = host
    self.port = port
    self.verbose = verbose # if True, debug code is printed

  def processMessage(self, message):
    """ process an incoming message """
    if message == '':
      pass
    elif message == 'clear':
      self.clear()
      # clear the frame if applicable
      if self.frame != None:
        self.frame.clear_choices()
        self.frame.clear_plot()
      if self.verbose:
        print 'levels cleared'
    else:
      # parse the incoming message
      tokens = message.split(';')
      t = float(tokens[0])
      levels = []
      for token in tokens[1:]:
        loc, level = token.split(':')
        level = float(level)
        levels.append((loc, level))
      # when parsing is succesful, update the data
      if (len(self.times) > 0) and (t < self.times[-1]):
        if self.verbose:
          print 'discarding non-chronological levels: %s' % message
      else:
        VIEWERLOCK.acquire()
        self.times.append(t)
        for loc, level in levels:
          if not loc in self.data:
            self.data[loc] = []
          self.data[loc].append(level)
          if self.verbose:
            print 'level received succesfully: time %.2fs, %s, %.2f dB' % (t, loc,level)
        VIEWERLOCK.release()


class SocketViewerLevelThread(ViewerLevelThread):
  """ implementation of viewer level thread using low level sockets """
  def __init__(self, *args, **kwargs):
    ViewerLevelThread.__init__(self, *args, **kwargs)

  def run(self):
    """ instantiate the server """
    if self.verbose:
      print 'thread started...'
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((self.host, self.port))
    s.listen(1)
    while self.active:
      # wait for a connection from the plugin
      try:
        s.settimeout(TIMEOUT)
        conn, addr = s.accept()
        s.settimeout(None)
      except:
        time.sleep(SLEEP)
        continue
      # when there is a connection, fetch the message
      if self.verbose:
        print 'connection established'
      data = ''
      try:
        while True:
          temp = conn.recv(BUFSIZE)
          if not temp:
            break
          data += temp
        conn.close()
      except:
        if self.verbose:
          print 'socket error, so skipping message'
      # update the levels
      try:
        self.processMessage(data)
      except:
        if self.verbose:
          print 'error with received message: "%s"' % data
    s.close()


if USERPYC:
  class RPyCViewerService(SlaveService):
    """ service for managing received messages using Remote Python Calls (RPyC) """
    def __init__(self, conn):
      SlaveService.__init__(self, conn)

    def exposed_processMessage(self, message):
      """ send a message to the parent thread for processing """
      global RPYCTHREAD
      RPYCTHREAD.processMessage(message)


class RPyCViewerLevelThread(ViewerLevelThread):
  """ implementation of viewer level thread using Remote Python Calls (RPyC) """
  def __init__(self, *args, **kwargs):
    ViewerLevelThread.__init__(self, *args, **kwargs)

  def run(self):
    """ instantiate the server """
    if self.verbose:
      print 'thread started...'
    global RPYCTHREAD
    RPYCTHREAD = self
    self.server = ThreadedServer(RPyCViewerService, port = DEFAULT_SERVER_PORT, auto_register = False, registrar = UDPRegistryClient())
    self.server.start()

  def join(self):
    self.server.close()
    ViewerLevelThread.join(self)


def createViewerLevelThread(*args, **kwargs):
  """ create a viewer level thread according to the defined protocol """
  if USERPYC:
    return RPyCViewerLevelThread(*args, **kwargs)
  else:
    return SocketViewerLevelThread(*args, **kwargs)


#---------------------------------------------------------------------------------------------------
# Utility GUI controls
#---------------------------------------------------------------------------------------------------

class XAxisRangeBox(wx.Panel):
  """ panel for adjusting x-axis range """
  def __init__(self, parent, ID, minvalue = XMIN, initvalue = XWIDTH, increment = SPININC):
    wx.Panel.__init__(self, parent, ID)
    self.minvalue = minvalue
    self.value = initvalue # initial x-axis range width (in sliding mode)
    # controls
    self.radio_full = wx.RadioButton(self, -1, label = 'Full range', style = wx.RB_GROUP)
    self.radio_slide = wx.RadioButton(self, -1, label = 'Sliding')
    self.slide_width = FloatSpin(self, -1, size = (50, -1), digits = 0, value = self.value, min_val = minvalue, increment = increment)
    self.slide_width.GetTextCtrl().SetEditable(False)
    # event bindings
    self.Bind(wx.EVT_UPDATE_UI, self.on_update_radio_buttons, self.radio_full)
    self.Bind(EVT_FLOATSPIN, self.on_float_spin, self.slide_width)
    # layout
    box = wx.StaticBox(self, -1, 'X-axis')
    sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
    slide_box = wx.BoxSizer(wx.HORIZONTAL)
    slide_box.Add(self.radio_slide, flag=wx.ALIGN_CENTER_VERTICAL)
    slide_box.Add(self.slide_width, flag=wx.ALIGN_CENTER_VERTICAL)
    sizer.Add(self.radio_full, 0, wx.ALL, 10)
    sizer.Add(slide_box, 0, wx.ALL, 10)
    self.SetSizer(sizer)
    sizer.Fit(self)

  def on_update_radio_buttons(self, event):
    """ called when the radio buttons are toggled """
    self.slide_width.Enable(self.radio_slide.GetValue())

  def on_float_spin(self, event):
    """ called when the sliding mode spinbox is changed """
    self.value = self.slide_width.GetValue()

  def is_full(self):
    """ return True if full range is checked """
    return self.radio_full.GetValue()


class YAxisRangeBox(wx.Panel):
  """ panel for adjusting y-axis range """
  def __init__(self, parent, ID, minvalue = YMIN, initvalue = YRANGE, increment = SPININC):
    wx.Panel.__init__(self, parent, ID)
    self.value = initvalue # initial y-axis range (in manual mode), i.e. (min, max-min)
    # controls
    self.radio_auto = wx.RadioButton(self, -1, label = 'Auto', style = wx.RB_GROUP)
    self.radio_manual = wx.RadioButton(self, -1, label = 'Manual')
    self.manual_min = FloatSpin(self, -1, size = (50, -1), digits = 0, value = self.value[0], min_val = minvalue[0], increment = increment)
    self.manual_min.GetTextCtrl().SetEditable(False)
    self.manual_width = FloatSpin(self, -1, size = (50, -1), digits = 0, value = self.value[1], min_val = minvalue[1], increment = increment)
    self.manual_width.GetTextCtrl().SetEditable(False)
    # event bindings
    self.Bind(wx.EVT_UPDATE_UI, self.on_update_radio_buttons, self.radio_auto)
    self.Bind(EVT_FLOATSPIN, self.on_float_spin, self.manual_min)
    self.Bind(EVT_FLOATSPIN, self.on_float_spin, self.manual_width)
    # layout
    box = wx.StaticBox(self, -1, 'Y-axis')
    sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
    manual_box = wx.BoxSizer(wx.HORIZONTAL)
    manual_box.Add(self.radio_manual, flag=wx.ALIGN_CENTER_VERTICAL)
    manual_box.Add(self.manual_min, flag=wx.ALIGN_CENTER_VERTICAL)
    manual_box.Add(self.manual_width, flag=wx.ALIGN_CENTER_VERTICAL)
    sizer.Add(self.radio_auto, 0, wx.ALL, 10)
    sizer.Add(manual_box, 0, wx.ALL, 10)
    self.SetSizer(sizer)
    sizer.Fit(self)

  def on_update_radio_buttons(self, event):
    """ called when the radio buttons are toggled """
    toggle = self.radio_manual.GetValue()
    self.manual_min.Enable(toggle)
    self.manual_width.Enable(toggle)

  def on_float_spin(self, event):
    """ called when one of the manual mode spinboxes is changed """
    self.value = (self.manual_min.GetValue(), self.manual_width.GetValue())

  def is_auto(self):
    """ return True if auto range is checked """
    return self.radio_auto.GetValue()


#---------------------------------------------------------------------------------------------------
# Viewer frame class
#---------------------------------------------------------------------------------------------------

class ViewerFrame(wx.Frame):
  """ main frame of the viewer application """
  def __init__(self, test = False):
    wx.Frame.__init__(self, None, -1, NAME)
    self.paused = False
    self.locations = []
    # creation of controls
    self.create_menu()
    self.create_status_bar()
    self.create_main_panel()
    # timer for redrawing
    self.redraw_timer = wx.Timer(self)
    self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)
    self.redraw_timer.Start(REDRAWTIME)
    # handle closing the frame
    self.Bind(wx.EVT_CLOSE, self.on_exit, self)
    # manage window style (always on top or not)
    self.wstyle = self.GetWindowStyle()
    self.SetWindowStyle(self.wstyle | wx.STAY_ON_TOP)
    # coordination with data server
    if test:
      self.thread = DummyLevelThread()
    else:
      self.thread = createViewerLevelThread(frame = self)
    self.thread.start()

  def create_menu(self):
    """ construction of menu bar """
    self.menubar = wx.MenuBar()
    # File menu
    menu_file = wx.Menu()
    m_expt = menu_file.Append(-1, '&Save plot\tCtrl-S')
    self.Bind(wx.EVT_MENU, self.on_save_plot, m_expt)
    menu_file.AppendSeparator()
    m_exit = menu_file.Append(-1, 'E&xit\tCtrl-X')
    self.Bind(wx.EVT_MENU, self.on_exit, m_exit)
    # View menu
    menu_view = wx.Menu()
    self.m_ontop = menu_view.Append(-1, '&Stay on top', kind = wx.ITEM_CHECK)
    self.m_ontop.Check(True)
    self.Bind(wx.EVT_MENU, self.on_ontop, self.m_ontop)
    # Help menu
    menu_help = wx.Menu()
    m_about = menu_help.Append(-1, '&About...')
    self.Bind(wx.EVT_MENU, self.on_about, m_about)
    # construction of menu bar
    self.menubar.Append(menu_file, '&File')
    self.menubar.Append(menu_view, '&View')
    self.menubar.Append(menu_help, '&Help')
    self.SetMenuBar(self.menubar)

  def create_status_bar(self):
    """ construction of status bar """
    self.statusbar = self.CreateStatusBar()
    self.statusbar.SetFieldsCount(2)
    self.statusbar.SetStatusWidths([50, -1])

  def create_main_panel(self):
    """ construction of the main controls """
    self.panel = wx.Panel(self)
    # contruct plotting area
    self.fig = Figure(FIGSIZE, dpi = DPI)
    # construct axes
    self.axes = self.fig.add_subplot(111)
    self.axes.set_axis_bgcolor(BGCOLOR)
    # adjust font size of axes labels
    pylab.setp(self.axes.get_xticklabels(), fontsize = FONTSIZE)
    pylab.setp(self.axes.get_yticklabels(), fontsize = FONTSIZE)
    # construct canvas with plotting area
    self.plot_data = self.axes.plot([], linewidth = LINEWIDTH, color = LINECOLOR)[0]
    self.canvas = FigCanvas(self.panel, -1, self.fig)
    # construct location choice box
    self.location_txt = wx.StaticText(self.panel, -1, label = ' Select location:')
    self.location_box = wx.Choice(self.panel, -1, choices = [], size = (150,-1))
    self.location_box.Enable(False)
    self.Bind(wx.EVT_CHOICE, lambda event: self.draw_plot(), self.location_box)
    # layout location choice box
    self.hbox0 = wx.BoxSizer(wx.HORIZONTAL)
    self.hbox0.Add(self.location_txt, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
    self.hbox0.Add(self.location_box, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
    # construct buttons
    self.pause_button = wx.Button(self.panel, -1, 'Pause')
    self.Bind(wx.EVT_BUTTON, self.on_pause_button, self.pause_button)
    self.Bind(wx.EVT_UPDATE_UI, self.on_update_pause_button, self.pause_button)
    self.clear_button = wx.Button(self.panel, -1, 'Clear')
    self.Bind(wx.EVT_BUTTON, self.on_clear_button, self.clear_button)
    self.cb_grid = wx.CheckBox(self.panel, -1, 'Show grid', style=wx.ALIGN_RIGHT)
    self.Bind(wx.EVT_CHECKBOX, lambda event: self.draw_plot(), self.cb_grid)
    self.cb_grid.SetValue(True)
    self.cb_xlab = wx.CheckBox(self.panel, -1, 'X-labels', style=wx.ALIGN_RIGHT)
    self.Bind(wx.EVT_CHECKBOX, lambda event: self.draw_plot(), self.cb_xlab)
    self.cb_xlab.SetValue(True)
    # layout buttons (add space using self.hbox1.AddSpacer(5))
    self.hbox1 = wx.BoxSizer(wx.HORIZONTAL)
    self.hbox1.Add(self.pause_button, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
    self.hbox1.Add(self.clear_button, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
    self.hbox1.Add(self.cb_grid, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
    self.hbox1.Add(self.cb_xlab, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
    # construct axis controls
    self.xrange_control = XAxisRangeBox(self.panel, -1)
    self.yrange_control = YAxisRangeBox(self.panel, -1)
    # layout axis controls
    self.hbox2 = wx.BoxSizer(wx.HORIZONTAL)
    self.hbox2.Add(self.xrange_control, border=5, flag=wx.ALL)
    self.hbox2.Add(self.yrange_control, border=5, flag=wx.ALL)
    # finally, create layout of viewer frame
    self.vbox = wx.BoxSizer(wx.VERTICAL)
    self.vbox.Add(self.canvas, 1, flag=wx.LEFT | wx.TOP | wx.GROW)
    self.vbox.Add(self.hbox0, 0, flag=wx.ALIGN_LEFT | wx.TOP)
    self.vbox.Add(self.hbox1, 0, flag=wx.ALIGN_LEFT | wx.TOP)
    self.vbox.Add(self.hbox2, 0, flag=wx.ALIGN_LEFT | wx.TOP)
    self.panel.SetSizer(self.vbox)
    self.vbox.Fit(self)

  def draw_plot(self):
    """ redraw the plot and update the gui if necessary """
    if not self.paused:
      # check if data is available
      if len(self.locations) == 0:
        self.locations = sorted(self.thread.locations())
        if len(self.locations) > 0:
          self.location_box.AppendItems(self.locations)
          self.location_box.SetSelection(0)
          self.location_box.Enable(True)
          self.flash_status_message('Connection established')
      if len(self.locations) > 0:
        # fetch data at selected receiver location
        loc = self.locations[self.location_box.GetSelection()]
        times, levels = self.thread.levels(loc)
        if (len(times) == len(levels)):
          # calculate x-axis limits
          if self.xrange_control.is_full():
            # show the full range for the x-axis
            xmin = times[0]
            xmax = max(times[0] + self.xrange_control.minvalue, times[-1])
          else:
            # show a sliding window
            xmax = times[-1]
            xmin = xmax - self.xrange_control.value
          # calculate y-axis limits
          if self.yrange_control.is_auto():
            # find the min and max values of the data and add a minimal margin
            ymin = round(min(levels), 0) - MARGIN
            ymax = round(max(levels), 0) + MARGIN
          else:
            # use manual interval
            ymin = self.yrange_control.value[0]
            ymax = ymin + self.yrange_control.value[1]
          # set axis limits
          self.axes.set_xbound(lower = xmin, upper = xmax)
          self.axes.set_ybound(lower = ymin, upper = ymax)
          # finally, plot the data and redraw the plot
          self.plot_data.set_xdata(numpy.array(times))
          self.plot_data.set_ydata(numpy.array(levels))
      # draw grid
      if self.cb_grid.IsChecked():
        self.axes.grid(True, color = GRIDCOLOR)
      else:
        self.axes.grid(False)
      # draw axis labels
      pylab.setp(self.axes.get_xticklabels(), visible = self.cb_xlab.IsChecked())
      self.canvas.draw()

  def clear_plot(self):
    """ clear the data on the plot """
    self.plot_data.set_xdata([])
    self.plot_data.set_ydata([])
    self.canvas.draw()

  def on_redraw_timer(self, event):
    """ redraw the plot """
    self.draw_plot()

  def on_pause_button(self, event):
    """ called when the pause button is clicked """
    self.paused = not self.paused
    if self.paused:
      self.statusbar.SetStatusText('Paused', 0)
    else:
      self.statusbar.SetStatusText('', 0)

  def on_update_pause_button(self, event):
    """ called when the pause button is to be updated """
    label = 'Resume' if self.paused else 'Pause'
    self.pause_button.SetLabel(label)

  def on_clear_button(self, event):
    """ called when the clear butten is clicked """
    self.thread.clear()
    self.clear_choices()
    self.clear_plot()

  def clear_choices(self):
    """ clear the choices box """
    self.locations = []
    self.location_box.Clear()
    self.location_box.Enable(False)
    self.flash_status_message('Cleared')

  def on_save_plot(self, event):
    """ show a window for saving a screenshot """
    dlg = wx.FileDialog(self, message = 'Save plot as...', defaultDir = os.getcwd(), defaultFile = 'plot.png', wildcard = 'PNG (*.png)|*.png', style = wx.SAVE)
    if dlg.ShowModal() == wx.ID_OK:
      path = dlg.GetPath()
      self.canvas.print_figure(path, dpi = DPI)
      self.flash_status_message('Saved to %s' % path)

  def stop_thread(self):
    """ stop the level thread """
    self.thread.active = False
    self.thread.join()

  def on_exit(self, event):
    """ called when the viewer is closed """
    self.stop_thread()
    self.Destroy()

  def on_ontop(self, event):
    """ toggles the stay on top modus """
    if self.m_ontop.IsChecked():
      self.SetWindowStyle(self.wstyle | wx.STAY_ON_TOP)
    else:
      self.SetWindowStyle(self.wstyle)

  def on_about(self, event):
    """ show an about box """
    wx.MessageBox(ABOUT, 'About ' + NAME)

  def flash_status_message(self, message):
    """ flash a message on the status bar """
    try:
      self.statusbar.SetStatusText(message, 1)
      self.timeroff = wx.Timer(self)
      self.Bind(wx.EVT_TIMER, lambda event: self.statusbar.SetStatusText('', 1), self.timeroff)
      self.timeroff.Start(FLASHTIME, oneShot = True)
    except:
      pass


#---------------------------------------------------------------------------------------------------
# Test code
#---------------------------------------------------------------------------------------------------

if __name__ == '__main__':

  if len(sys.argv) <= 1:
    # no command line argument, so run the viewer application
    app = wx.PySimpleApp()
    app.frame = ViewerFrame()
    app.frame.Show()
    app.MainLoop()

  if (len(sys.argv) == 2) and (sys.argv[1] == 'test'):
    # run the viewer in test mode, i.e. generating its own levels for display
    app = wx.PySimpleApp()
    app.frame = ViewerFrame(test = True)
    app.frame.Show()
    app.MainLoop()

  if (len(sys.argv) == 2) and (sys.argv[1] == 'command'):
    # run the viewer in command line mode, i.e. only receiving levels and printing them to the console
    print 'Running viewer in command line mode - press any key to stop...'
    thread = createViewerLevelThread(frame = None, verbose = True)
    thread.start()
    # wait until a key is pressed
    stop = False
    while not stop:
      if msvcrt.kbhit():
        c = msvcrt.getch()
        stop = True
      time.sleep(0.1)
    # stop the thread
    thread.active = False
    thread.join()

  if (len(sys.argv) == 2) and (sys.argv[1] == 'dummy'):
    # run a dummy Aimsun/Noysim2 client that sends random levels (for use with viewer in normal or command line mode)
    print 'Running dummy Aimsun/Noysim2 client - press any key to stop...'
    client = createLevelBuffer(verbose = True, sleep = 1000*TESTSLEEP)
    client.sendClear()
    stop = False
    (t, dt) = (0.0, TESTDT)
    while not stop:
      t += dt
      client.sendLevels(t = t, levels = dict([(loc, randomLevel()) for loc in TESTLOCS]))
      if msvcrt.kbhit():
        c = msvcrt.getch()
        stop = True
