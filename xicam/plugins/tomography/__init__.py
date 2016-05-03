#! /usr/bin/env python

__author__ = "Ronald J Pandolfi"
__copyright__ = "Copyright 2016, CAMERA, LBL, ALS"
__credits__ = ["Ronald J Pandolfi", "Dinesh Kumar", "Singanallur Venkatakrishnan", "Luis Luque", "Alexander Hexemer"]
__license__ = ""
__version__ = "1.2.1"
__maintainer__ = "Ronald J Pandolfi"
__email__ = "ronpandolfi@lbl.gov"
__status__ = "Beta"

# Use NSURL as a workaround to pyside/Qt4 behaviour for dragging and dropping on OSx
import platform
op_sys = platform.system()
# if op_sys == 'Darwin':
#     from Foundation import NSURL

import os
import numpy as np
import pipeline
from pipeline import loader
from PySide import QtCore, QtGui
from xicam import xglobals
import widgets as twidgets
from xicam.plugins import widgets, explorer
from xicam.plugins import base
from PySide import QtUiTools
import functionmanager
from pyqtgraph.parametertree import ParameterTree
from xicam import models
import ui


class plugin(base.plugin):
    name = "Tomography"

    def __init__(self, *args, **kwargs):

        self.leftwidget, self.centerwidget, self.rightwidget, self.bottomwidget, self.toolbar, self.functionwidget = ui.load()

        super(plugin, self).__init__(*args, **kwargs)

        self.centerwidget.currentChanged.connect(self.currentChanged)
        self.centerwidget.tabCloseRequested.connect(self.tabCloseRequested)

        # wire stuff up
        self.functionwidget.previewButton.clicked.connect(functionmanager.runpreviewstack)
        self.functionwidget.clearButton.clicked.connect(functionmanager.clearFeatures)
        self.functionwidget.moveUpButton.clicked.connect(
            lambda: functionmanager.swapFunctions(functionmanager.currentindex,
                                                  functionmanager.currentindex - 1))
        self.functionwidget.moveDownButton.clicked.connect(
            lambda: functionmanager.swapFunctions(functionmanager.currentindex,
                                                  functionmanager.currentindex + 1))

        # SETUP FEATURES
        functionmanager.layout = ui.functionslist
        functionmanager.load()

        # DRAG-DROP
        self.centerwidget.setAcceptDrops(True)
        self.centerwidget.dragEnterEvent = self.dragEnterEvent
        self.centerwidget.dropEvent = self.dropEvent

    def dropEvent(self, e):
        for url in e.mimeData().urls():
            if op_sys == 'Darwin':
                fname = str(NSURL.URLWithString_(str(url.toString())).filePathURL().path())
            else:
                fname = str(url.toLocalFile())
            if os.path.isfile(fname):
                print(fname)
                self.openfiles([fname])
            e.accept()

    def dragEnterEvent(self, e):
        print(e)
        e.accept()

    def currentChanged(self, index):
        for tab in [self.centerwidget.widget(i) for i in range(self.centerwidget.count())]:
            tab.unload()

        self.centerwidget.currentWidget().load()
        # self.imagePropModel.widgetchanged()
        ui.propertytable.setData([[key, value] for key, value in self.currentImage().data.header.items()])
        ui.propertytable.setHorizontalHeaderLabels([ 'Parameter', 'Value'])

    def tabCloseRequested(self, index):
        ui.propertytable.clear()
        self.centerwidget.widget(index).deleteLater()

    def openfiles(self, paths,*args,**kwargs):
        self.activate()
        if type(paths) is list:
            paths = paths[0]

        widget = widgets.OOMTabItem(itemclass=twidgets.tomoWidget, paths=paths)
        self.centerwidget.addTab(widget, os.path.basename(paths))
        self.centerwidget.setCurrentWidget(widget)

    def currentImage(self):
        return self.centerwidget.currentWidget().widget