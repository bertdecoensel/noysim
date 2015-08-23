# Noysim -- Noise simulation tools for Aimsun.
# Copyright (c) 2010-2011 by Bert De Coensel, Ghent University & Griffith University.
#
# Run the viewer as a windows program

import noysim.viewer

app = noysim.viewer.wx.PySimpleApp()
app.frame = noysim.viewer.ViewerFrame()
app.frame.Show()
app.MainLoop()
