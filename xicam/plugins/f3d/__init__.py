from xicam.plugins import base
from PySide import QtCore, QtGui
from PySide.QtUiTools import QUiLoader
from xicam.plugins.tomography.viewers import RunConsole
from xicam.widgets.customwidgets import F3DButtonGroup, DeviceWidget
from xicam.threads import Worker, RunnableMethod
from pipeline.loader import StackImage
from pipeline import msg
from functools import partial
from ClAttributes import ClAttributes
from filters import POCLFilter
import f3d_viewers
import os
import pyqtgraph as pg
import filtermanager as fm
import pyopencl as cl
import numpy as np
import importer
import Queue
import time


class plugin(base.plugin):

    name = "F3D"

    sigFilterAdded = QtCore.Signal(dict)


    def __init__(self, placeholders, *args, **kwargs):

        self.toolbar = Toolbar()
        self.toolbar.connectTriggers(self.run, self.preview)
        # self.build_toolbutton_menu(self.toolbar.addMaskMenu, 'Open file for mask', self.openMaskFile)
        # self.build_toolbutton_menu(self.toolbar.addMaskMenu, 'Open directory for mask', self.openMaskFolder)


        self.functionwidget = QUiLoader().load('xicam/gui/tomographyleft.ui')
        self.functionwidget.functionsList.setAlignment(QtCore.Qt.AlignBottom)

        self.functionwidget.addFunctionButton.setToolTip('Add function to pipeline')
        self.functionwidget.clearButton.setToolTip('Clear pipeline')
        self.functionwidget.fileButton.setToolTip('Save/Load pipeline')
        self.functionwidget.moveDownButton.setToolTip('Move selected function down')
        self.functionwidget.moveUpButton.setToolTip('Move selected function up')


        filefuncmenu = QtGui.QMenu()
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("xicam/gui/icons_55.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.openaction = QtGui.QAction(icon, 'Open', filefuncmenu)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("xicam/gui/icons_59.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.saveaction = QtGui.QAction(icon, 'Save', filefuncmenu)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("xicam/gui/icons_56.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.refreshaction = QtGui.QAction(icon, 'Reset', filefuncmenu)
        filefuncmenu.addActions([self.openaction, self.saveaction, self.refreshaction])

        leftwidget = QtGui.QSplitter(QtCore.Qt.Vertical)
        paramtree = pg.parametertree.ParameterTree()
        self.param_form = QtGui.QStackedWidget()
        self.param_form.addWidget(paramtree)
        self.property_table = pg.TableWidget()
        self.property_table.verticalHeader().hide()
        self.property_table.horizontalHeader().setStretchLastSection(True)
        self.property_table.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)
        leftwidget.addWidget(self.param_form)
        leftwidget.addWidget(self.functionwidget)

        self.log = RunConsole()
        icon_functions = QtGui.QIcon(QtGui.QPixmap("xicam/gui/icons_49.png"))
        icon_log = QtGui.QIcon(QtGui.QPixmap("xicam/gui/icons_64.png"))

        self.leftmodes = [(leftwidget, icon_functions), (self.log, icon_log)]

        self.centerwidget = QtGui.QTabWidget()
        self.centerwidget.setDocumentMode(True)
        self.centerwidget.setTabsClosable(True)
        self.centerwidget.tabCloseRequested.connect(self.tabCloseRequested)
        self.centerwidget.currentChanged.connect(self.currentChanged)
        self.centerwidget.tabCloseRequested.connect(self.tabCloseRequested)

        # DRAG-DROP
        self.centerwidget.setAcceptDrops(True)
        self.centerwidget.dragEnterEvent = self.dragEnterEvent
        self.centerwidget.dropEvent = self.dropEvent

        self.readAvailableDevices()
        self.rightwidget = F3DOptionsWidget(self.devices, 0)


        self.manager = fm.FilterManager(self.functionwidget.functionsList, self.param_form,
                                       blank_form='Select a filter from\n below to set parameters...')
        self.manager.sigFilterAdded.connect(lambda: self.sigFilterAdded.emit(self.filter_images))
        # self.manager.sigFilterAdded.connect(self.emit_filters)

        self.functionwidget.fileButton.setMenu(filefuncmenu)
        self.functionwidget.fileButton.setPopupMode(QtGui.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.functionwidget.fileButton.setArrowType(QtCore.Qt.NoArrow)

        self.addfunctionmenu = QtGui.QMenu()
        self.functionwidget.addFunctionButton.setMenu(self.addfunctionmenu)
        self.functionwidget.addFunctionButton.setPopupMode(QtGui.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.functionwidget.addFunctionButton.setArrowType(QtCore.Qt.NoArrow)
        self.openaction.triggered.connect(self.loadPipeline)
        self.saveaction.triggered.connect(self.savePipeline)
        self.functionwidget.moveDownButton.clicked.connect(
            lambda: self.manager.swapFeatures(self.manager.selectedFeature,self.manager.previousFeature))
        self.functionwidget.moveUpButton.clicked.connect(
            lambda: self.manager.swapFeatures(self.manager.selectedFeature, self.manager.nextFeature))
        self.functionwidget.clearButton.clicked.connect(self.clearPipeline)




        super(plugin, self).__init__(placeholders, *args, **kwargs)

        self.threadWorker = Worker(Queue.Queue())
        self.threadWorker.pool.setExpiryTimeout(1)

        self.filter_images = {}
        self.startIndex = 0
        self.stacks = []

        self.sigFilterAdded.connect(self.manager.updateFilterMasks)
        self.build_function_menu(self.addfunctionmenu, importer.filters, self.manager.addFilter)

    def dropEvent(self, e):
        for url in e.mimeData().urls():
            if op_sys == 'Darwin':
                fname = str(NSURL.URLWithString_(str(url.toString())).filePathURL().path())
            else:
                fname = str(url.toLocalFile())
            if os.path.isfile(fname):
                self.openfiles([fname])
            if os.path.isdir(fname):
                self.opendirectory([fname])
            e.accept()

    def dragEnterEvent(self, e):
        e.accept()

    def openfiles(self, paths):
        """
        Override openfiles method in base plugin. Used to open a tomography dataset from the recognized file formats
        and instantiate a viewer.TomoViewer tab. This function takes quite a bit, consider running this in a background
        thread

        Parameters
        ----------
        paths : str/list
            Path to file. Currently only one file is supported. Multiple paths (ie stack of tiffs should be easy to
            implement using the formats.StackImage class.

        """

        msg.showMessage('Loading file...', timeout=10)
        self.activate()
        if type(paths) is list:
            paths = paths[0]

        widget = f3d_viewers.F3DViewer(files=paths)

        # check if file is already in filter_images, and load if it is not
        if not paths in self.filter_images.iterkeys():
            self.filter_images[paths] = widget
            self.sigFilterAdded.emit(self.filter_images)

        self.centerwidget.addTab(widget, os.path.basename(paths))
        self.centerwidget.setCurrentWidget(widget)
        msg.showMessage('Done.', timeout=10)

    def opendirectory(self, file, operation=None):
        msg.showMessage('Loading directory...', timeout=10)
        self.activate()
        if type(file) is list:
            file = file[0]

        files = [os.path.join(file, path) for path in os.listdir(file) if path.endswith('.tif') or path.endswith('.tiff')]
        widget = f3d_viewers.F3DViewer(files=files)

        # check if file is already in filter_images, and load if it is not
        if not file in self.filter_images.iterkeys():
            self.filter_images[file] = widget
            self.sigFilterAdded.emit(self.filter_images)

        self.centerwidget.addTab(widget, os.path.basename(file))
        self.centerwidget.setCurrentWidget(widget)
        msg.showMessage('Done.', timeout=10)


    ## TODO: have separate readers for masks? maybe just have all open images be available as masks

    # def openMaskFile(self):
    #
    #     mask_path = QtGui.QFileDialog().getOpenFileName(caption="Select file to open as mask: ")
    #
    #     if not mask_path[0]:
    #         return
    #     try:
    #         mask = StackImage(mask_path[0]).fabimage.rawdata
    #     except AttributeError:
    #         self.log.log2local("Could not open file \'{}\'".format(mask_path[0]))
    #
    #     self.filter_images[mask_path[0]] = mask
    #     self.log.log2local('Successfully loaded \'{}\' as mask'.format(os.path.basename(mask_path[0])))
    #     self.leftwidget.setCurrentWidget(self.log)
    #     self.sigFilterAdded.emit(self.filter_images)
    #
    #
    #
    # def openMaskFolder(self):
    #     mask_path = QtGui.QFileDialog().getExistingDirectory(caption=
    #                                                 "Select directory to search for mask images: ")
    #
    #     if not mask_path:
    #         return
    #     try:
    #         files = [os.path.join(mask_path, path) for path in os.listdir(mask_path) if
    #                  path.endswith('.tif') or path.endswith('.tiff')]
    #         mask = StackImage(files).fabimage.rawdata
    #     except AttributeError:
    #         self.log.log2local("Could not open directory \'{}\'".format(mask_path))
    #
    #     self.filter_images[mask_path] = mask
    #     self.log.log2local('Successfully loaded images in \'{}\' as mask'.format(os.path.basename(mask_path)))
    #     self.leftwidget.setCurrentWidget(self.log)
    #     self.sigFilterAdded.emit(self.filter_images)

    def currentWidget(self):
        """
        Return the current widget (viewer.TomoViewer) from the centerwidgets tabs
        """

        try:
            return self.centerwidget.currentWidget()
        except AttributeError:
            return None

    def currentChanged(self, index):
        """
        Slot to recieve centerwidgets currentchanged signal when a new tab is selected
        """

        try:
            current_widget = self.centerwidget.widget(index)
            self.rightwidget.update_widget_spinboxes(current_widget.data.shape[0])
        #     self.setPipelineValues()
        #     self.manager.updateParameters()
        #     self.toolbar.actionCenter.setChecked(False)
        except (AttributeError, RuntimeError) as e:
            msg.logMessage(e.message, level=msg.ERROR)

    def reconnectTabs(self):
        """
        Reconnect TomoViewers when the pipeline is reset
        """
        for idx in range(self.centerwidget.count()):
            self.centerwidget.widget(idx).wireupCenterSelection(self.manager.recon_function)
            self.centerwidget.widget(idx).sigSetDefaults.connect(self.manager.setPipelineFromDict)

    def tabCloseRequested(self, index):
        """
        Slot to receive signal when a tab is closed. Simply resets configuration parameters and clears metadata table

        Parameters
        ----------
        index : int
            Index of tab that is being closed.
        """

        self.centerwidget.widget(index).deleteLater()

    def run(self):
        # corresponds to F3DImageProcessing_JOCL_.java.run() (?)
        name = self.centerwidget.tabText(self.centerwidget.currentIndex())
        msg.showMessage('Running pipeline for {}'.format(name), timeout=0)

        pipeline = self.manager.getPipeline()
        pipeline_dict = self.manager.getPipelineDict()
        self.startIndex = 0

        # print status output
        self.log.local_console.clear()
        devices_tmp = self.rightwidget.chosen_devices
        devices_tmp.reverse(); pipeline.reverse()
        for item in pipeline:
            filter = item.filter
            self.log.log2local("{}".format(filter.name))
        self.log.log2local("Pipeline to be processed:")
        for device in devices_tmp:
            self.log.log2local("{}".format(device.name))
        self.log.log2local("Using {} device(s):".format(str(len(devices_tmp))))
        del devices_tmp; pipeline.reverse()
        self.leftwidget.setCurrentWidget(self.log)

        # execute filters. Create one thread per device
        print '1'
        self.current = self.currentWidget()
        runnables = []
        self.counter = 0
        for i in range(len(self.rightwidget.chosen_devices)):

            #initalize args
            device = self.rightwidget.chosen_devices[i]
            context = self.contexts[device]
            overlapAmount = 0
            atts = POCLFilter.FilteringAttributes()
            index = self.rightwidget.chosen_devices.index(device)
            clattr = ClAttributes(context, device, cl.CommandQueue(context, device),
                                              None, None, None)
            clattr.setMaxSliceCount(self.current.rawdata[:10])
            method_kwargs = {'pipeline': pipeline, 'device': device, 'context': context, 'overlapAmount': overlapAmount,
                             'attributes': atts, 'index': index, 'clattr': clattr}
            # runnables.append(RunnableMethod(method=self.doFilter, method_kwargs=method_kwargs,
            #                                 finished_slot=self.waitForThreads))
            runnables.append(RunnableMethod(method=self.dummy,
                                            callback_slot=self.waitForThreads))

            # runnables.append(RunnableMethod(method=self.dummy))

        # necessary?
        # # if only one device is available then skip thread creation and execute
        # if len(runnables) == 1:
        #     runnables[0]()

        print '2'

        self.stop = len(runnables)
        for i in range(len(runnables)):
            self.threadWorker.queue.put(runnables[i])

        print '3'

        # run worker
        if not self.threadWorker.isRunning():
            self.threadWorker.run()

        #
        # print '5'
        #
        # # all threads now finished, so reconstruct final image
        # self.stacks = sorted(self.stacks) #sort by starting slice
        #
        # image = self.stacks[0].stack
        # for stack in self.stacks[1:]:
        #     image = np.append(image, stack.stack, axis=0)
        #
        # # for now, only show previews
        # # for i in range(image.shape[0]):
        # for i in range(10):
        #     self.current.addPreview(np.rot90(image[i],1), pipeline_dict, 0) #slice no goes here eventually)

    @QtCore.Slot()
    def dummy(self,):
        print 'herehere'
        return 'it connects'

    def waitForThreads(self, success):
        print 'success!!!!'
        print success

        # self.counter += 1
        # if self.counter == self.stop:
        #     self.threadWorker.stop()


    def doFilter(self, pipeline, device, context, overlapAmount, attributes, index, clattr):

        print 'it gets here'

        maxOverlap = 0
        for item in pipeline:
            filter = item.filter
            maxOverlap = max(maxOverlap, filter.getInfo().overlapZ)

        print 'hey1'

        #currentWidget is F3dviewer type
        maxSliceCount = clattr.maxSliceCount
        clattr.initializeData(self.current.rawdata, attributes, overlapAmount, maxSliceCount)

        print 'hey2'

        for item in pipeline:
            filter = item.filter
            if filter.getInfo().useTempBuffer:
                clattr.outputTmpBuffer = cl.Buffer(clattr.context, cl.mem_flags.READ_WRITE,
                                                   clattr.inputBuffer.size)
                break

        print 'hey3'

        stackRange = [0, 0]
        while self.getNextRange(stackRange, maxSliceCount):
            attributes.sliceStart = stackRange[0]
            attributes.sliceEnd = stackRange[1]
            clattr.loadNextData(self.current.rawdata, attributes, stackRange[0], stackRange[1], maxOverlap)
            maxSliceCount = stackRange[1] - stackRange[0]

            pipelineTime = time.time()

            for i in range(len(pipeline)):
                filter = pipeline[i].clone()
                filter.setAttributes(clattr, attributes, index)
                if not filter.loadKernel():
                    raise Exception('Failure to load kernel for: {}'.format(filter.getName()))
                filterTime = time.time()
                if not filter.runFilter():
                    raise Exception('Failure to run kernel for: {}'.format(filter.getName()))

                filterTime = time.time() - filterTime
                pipelineTime += filterTime

                if i < len(pipeline) - 1:
                    clattr.swapBuffers()
                filter.releaseKernel()

            # save output of image after pipeline execution to get final result
            image = clattr.writeNextData(attributes, stackRange[0], stackRange[1], maxOverlap)
            self.addResultStack(stackRange[0], stackRange[1], image, device.name, pipelineTime)

        clattr.inputBuffer.release()
        clattr.outputBuffer.release()
        if clattr.outputTmpBuffer is not None:
            clattr.outputTmpBuffer.release() #  careful of seg fault if it's already released. How to check?

        return True


    def addResultStack(self, startRange, endRange, image, name, pipelineTime):
        slices = self.currentWidget().rawdata.shape[0]
        sr = StackRange()
        sr.startRange = startRange
        sr.endRange = endRange
        sr.stack = image
        sr.name = name
        sr.time = pipelineTime

        self.stacks.append(sr)

        #show progress somehow with slices varaible as compared to image size


    def getNextRange(self, range, sliceCount):
        endIndex = 10
        # endIndex = self.current.rawdata.shape[0]
        if self.startIndex >=endIndex:
            return False

        range[0] = self.startIndex
        range[1] = self.startIndex + sliceCount
        if range[1] >= endIndex:
            range[1] = endIndex

        self.startIndex = range[1]
        return True



    def preview(self):
        pass


    def build_function_menu(self, menu, filter_data, actionslot):
        """
        Builds the filter menu and connects it to the corresponding slot to add them to the workflow pipeline

        Parameters
        ----------
        menu : QtGui.QMenu
            Menu object to populate with filter names
        functiondata : dict
            Dictionary with function information. See importer.filters.yml
        actionslot : QtCore.Slot,
            slot where the function action triggered signal should be connected
        """

        for func, options in filter_data.iteritems():
                try:
                    funcaction = QtGui.QAction(func, menu)
                    funcaction.triggered.connect(partial(actionslot, func))
                    menu.addAction(funcaction)
                except KeyError:
                    pass

    def build_toolbutton_menu(self, menu, heading, actionslot):

        action = QtGui.QAction(heading, menu)
        action.triggered.connect(actionslot)
        menu.addAction(action)

    def loadPipeline(self):
        pass

    def savePipeline(self):
        pass

    def clearPipeline(self):
        pass

    def readAvailableDevices(self):
        """
        Somehow read and return list of all gpus usable for processing
        """

        platforms = cl.get_platforms()
        devices_tmp = []
        for item in platforms:
            devices_tmp.append(item.get_devices())

        self.contexts = {}
        self.devices = []
        if len(devices_tmp) == 1:
            self.devices = devices_tmp[0]
            self.contexts[devices_tmp[0][0]] = (cl.Context(devices_tmp[0]))
        else:
            for i in range(len(devices_tmp)):
                # devices = devices_tmp[i] + devices_tmp[i + 1]
                self.devices += devices_tmp[i]
                try:
                    self.contexts[devices_tmp[i][0]] = cl.Context(devices_tmp[i])
                except RuntimeError as e:
                    self.log.log2local("ERROR: There was a problem detecting drivers. Please verify the installation" +
                                       " of your graphics device\'s drivers.")
                    msg.logMessage(e.message, level=msg.ERROR)
                    self.leftwidget.setCurrentWidget(self.log)
                # except NoClassFoundError - does not apply for this?


class Toolbar(QtGui.QToolBar):

    def __init__(self):
        super(Toolbar, self).__init__()

        self.actionRun = QtGui.QAction(self)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("xicam/gui/icons_34.png"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.actionRun.setIcon(icon)
        self.actionRun.setToolTip('Run pipeline')

        self.actionPreview = QtGui.QAction(self)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("xicam/gui/icons_50.png"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.actionPreview.setIcon(icon)
        self.actionPreview.setToolTip('Run preview')


        # self.actionAddMask = QtGui.QToolButton(self)
        # self.addMaskMenu = QtGui.QMenu()
        # self.actionAddMask.setMenu(self.addMaskMenu)
        # self.actionAddMask.setPopupMode(QtGui.QToolButton.ToolButtonPopupMode.InstantPopup)
        # self.actionAddMask.setArrowType(QtCore.Qt.NoArrow)
        # icon = QtGui.QIcon()
        # icon.addPixmap(QtGui.QPixmap("xicam/gui/icons_08.png"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        # self.actionAddMask.setIcon(icon)
        # self.actionAddMask.setToolTip('Add additional mask from disk')

        self.setIconSize(QtCore.QSize(32, 32))

        self.addAction(self.actionRun)
        self.addAction(self.actionPreview)
        # self.addWidget(self.actionAddMask)

    def connectTriggers(self, run, preview):

        self.actionRun.triggered.connect(run)
        self.actionPreview.triggered.connect(preview)



class F3DOptionsWidget(QtGui.QWidget):
    """
    rightwidget for f3d plugin
    """

    def __init__(self, devices, shape, parent=None):
        super(F3DOptionsWidget, self).__init__(parent=parent)
        layout = QtGui.QVBoxLayout()
        options = QtGui.QLabel('Devices Options')
        self.device_widgets = {}
        self.devices = devices
        self.buttons = F3DButtonGroup()

        layout.addWidget(options)
        layout.addSpacing(10)


        counter = 0
        for device in devices:
            self.device_widgets[device.name] = DeviceWidget(device.name, counter, shape)
            self.buttons.addButton(self.device_widgets[device.name].checkbox, counter)
            if counter == 0:
                self.device_widgets[device.name].checkbox.setChecked(True)
            counter += 1
        self.maxNumDevices = counter - 1

        layout.addWidget(QtGui.QLabel('Total number of devices: {}'.format(str(counter))))
        layout.addSpacing(5)

        for idx in range(len(self.device_widgets)):
            for widget in self.device_widgets.itervalues():
                if widget.number == idx: layout.addWidget(widget)


        layout.addSpacing(30)

        # widget to hold virtual stack options
        l = QtGui.QVBoxLayout()
        h = QtGui.QHBoxLayout()
        self.virtual_stack = QtGui.QCheckBox()
        self.virtual_stack.stateChanged.connect(self.findDirectory)
        self.output = QtGui.QLineEdit(' ')
        self.output.setReadOnly(True)
        h.addWidget(self.virtual_stack)
        h.addWidget(QtGui.QLabel('Use Virtual Stack'))
        l.addLayout(h)
        l.addWidget(self.output)
        layout.addLayout(l)
        layout.addSpacing(10)

        self.intermediate_steps = QtGui.QCheckBox()
        h_layout = QtGui.QHBoxLayout()
        h_layout.addWidget(self.intermediate_steps)
        h_layout.addWidget(QtGui.QLabel('Show Intermediate Steps '))
        layout.addLayout(h_layout)
        layout.addStretch(50)

        self.setLayout(layout)

    def update_widget_spinboxes(self, shape):
        for name in self.device_widgets.iterkeys():
            self.device_widgets[name].slicebox.setMinimum(1)
            self.device_widgets[name].slicebox.setMaximum(shape)
            self.device_widgets[name].slicebox.setValue(shape)

    @property
    def use_virtual(self):
        return self.virtual_stack.checkState()

    @property
    def use_intermediate(self):
        return self.intermediate_steps.checkState()

    def findDirectory(self, bool):

        if bool:
            path = QtGui.QFileDialog().getExistingDirectory(caption=
                                                    "Choose output directory: ")
            if path: self.output.setText(path)

    @property
    def chosen_devices(self):
        device_names = []
        for name, widget in self.device_widgets.iteritems():
            if self.device_widgets[name].checkbox.isChecked(): device_names.append(name)

        return [device for device in self.devices if device.name in device_names]

class StackRange:

    def __init__(self):
        self.processTime = 0
        self.startRange = 0
        self.endRange = 0
        self.name = ""
        self.stack = None

    def __lt__(self, sr):
        # ascending
        return self.startRange - sr.startRange < 0

    def __eq__(self, other):
        if self is other:
            return True
        elif type(self) != type(other):
            return False
        else:
            return self.startRange==other.startRange and self.endRange==other.endRange


