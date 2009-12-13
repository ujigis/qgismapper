# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtXml import *
from qgis.core import *
from qgis.gui import *
import resources
from DockWidget import DockWidget
from DockWidget_simple import DockWidget_simple
import SourcePlugins
import sys, os, re
import Gatherer
import traceback
from CanvasMarkers import PositionMarker
import logging, logging.handlers

from GpsDaemon import GpsDaemon

logFilePath=os.path.expanduser("~/.qgis/GatherPlugin.log")


class GatherPlugin(QObject):
	"""
	Main Gahterer plugin class - handles interaction with QGis and 
	organizes all the recording stuff.
	"""

	def __init__(self, iface):
		QObject.__init__(self)
		self.iface = iface
	
	def initGui(self):
		""" Initialize plugin's UI """

		self.initLogging()
		self.recording=False
		self.loadPlugins()
		self.loadConfiguration()
		self.rubberBand=None
		self.lastPosition=None
		self.timer=None
		self.previousPaths=[] #previews of previously recorded paths
		
		self.gpsDaemon=GpsDaemon(self, self)
		self.canvas=self.iface.mapCanvas()
		
		self.gatherer=None
		self.dockWidget=None
		self.dockWidget_simple=None
    
		self.dockWidget=DockWidget(self)
		self.dockWidget_simple=DockWidget_simple(self)
		
		self.actionDockWidget=QAction("Show Gatherer dock widget",self.iface.mainWindow())
		self.actionDockWidget.setCheckable(True)
		QObject.connect(self.actionDockWidget, SIGNAL("triggered()"), self.showHideDockWidget)
		self.iface.addPluginToMenu("Qgis-&mapper", self.actionDockWidget)
		QObject.connect(self.dockWidget, SIGNAL("visibilityChanged(bool)"), lambda : self.__dockwidgetVisibilityChanged(0))
		QObject.connect(self.dockWidget_simple, SIGNAL("visibilityChanged(bool)"), lambda : self.__dockwidgetVisibilityChanged(1))
		
		SourcePlugins.initializeUI(self.dockWidget.dataInputPlugins_tabWidget)
		
		self.curDockWidget=None
		self.showInterface(self.interface_simple)
		
		self.canvas=self.iface.mapCanvas()
		self.positionMarker=PositionMarker(self.canvas)
		self.connect(self.gpsDaemon, SIGNAL("newTrackPoint(PyQt_PyObject)"), self.gotNewTrackPoint)

	def unload(self):
		""" Cleanup and unload the plugin """

		self.canvas.scene().removeItem(self.positionMarker)
		self.positionMarker=None
		
		if self.recording:
			self.recordingStop()
		
		self.saveConfiguration()
		SourcePlugins.unloadPlugins()

		self.gpsDaemon.terminate()
		
		self.dockWidget.unload()
		self.showInterface(None)
		
		del self.dockWidget
		del self.dockWidget_simple
		
		self.iface.removePluginMenu("Qgis-&mapper",self.actionDockWidget)
		del self.actionDockWidget
		
		logging.debug("Plugin terminated.")

	def initLogging(self):
		""" set up rotating log file handler with custom formatting """
		handler = logging.handlers.RotatingFileHandler(logFilePath, maxBytes=1024*1024*10, backupCount=5)
		formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s")
		handler.setFormatter(formatter)
		logger = logging.getLogger() # root logger
		logger.setLevel(logging.DEBUG)
		logger.addHandler(handler)
		logging.debug("Plugin started.")

	def loadPlugins(self):
		"""Load all existing plugins"""
		SourcePlugins.loadPlugins(self)
	
	def loadConfiguration(self):
		""" Load configuration from settings """

		self.last_preview_scale=25

		settings = QSettings()
		settings.beginGroup("/plugins/GatherPlugin")

		# GUI
		self.interface_simple = settings.value("interface/simple", QVariant(False)).toBool()
		self.output_directory = settings.value("output/directory", QVariant(os.path.expanduser("~/qgismapper/data/"))).toString()
		self.output_append = settings.value("output/append", QVariant(0)).toInt()[0]
		self.preview_followPosition = settings.value("preview/followPosition", QVariant(True)).toBool()
		self.preview_scale = settings.value("preview/scale", QVariant(25)).toInt()[0]
		self.preview_keepPaths = settings.value("preview/keepPaths", QVariant(True)).toBool()

		# gps
		self.gps_source = settings.value("gps/source", QVariant("serial")).toString()
		self.gps_reconnectInterval = settings.value("gps/reconnectInterval", QVariant(2)).toInt()[0]
		self.gps_attemptsDuringRecording = settings.value("gps/attemptsDuringRecording", QVariant(3)).toInt()[0]
		self.gps_initFile = settings.value("gps/initFile", QVariant()).toString()
		self.gps_serial = settings.value("gps/serial/device", QVariant("/dev/rfcomm0")).toString()
		self.gps_serialBauds = settings.value("gps/serial/bauds", QVariant(38400)).toInt()[0]
		self.gps_file = settings.value("gps/file/path", QVariant(os.path.expanduser("~/nmea_log"))).toString()
		self.gps_fileCharsPerSecond = settings.value("gps/file/charsPerSecond", QVariant(300)).toInt()[0]
		self.gps_gpsdHost = settings.value("gps/gpsd/host", QVariant("localhost")).toString()
		self.gps_gpsdPort = settings.value("gps/gpsd/port", QVariant(2947)).toInt()[0]

		# compass
		self.compass_use = settings.value("compass/use", QVariant(False)).toBool()
		self.compass_device = settings.value("compass/device", QVariant("/dev/ttyUSB0")).toString()
		self.compass_bauds = settings.value("compass/bauds", QVariant(19200)).toInt()[0]
			
	def saveConfiguration(self):
		""" Save configuration to settings """

		settings = QSettings()
		settings.beginGroup("/plugins/GatherPlugin")

		# GUI
		settings.setValue("interface/simple", QVariant(self.interface_simple))
		settings.setValue("output/directory", QVariant(self.output_directory))
		settings.setValue("output/append", QVariant(self.output_append))
		settings.setValue("preview/followPosition", QVariant(self.preview_followPosition))
		settings.setValue("preview/scale", QVariant(self.preview_scale))
		settings.setValue("preview/keepPaths", QVariant(self.preview_keepPaths))

		# gps
		settings.setValue("gps/source", QVariant(self.gps_source))
		settings.setValue("gps/reconnectInterval", QVariant(self.gps_reconnectInterval))
		settings.setValue("gps/attemptsDuringRecording", QVariant(self.gps_attemptsDuringRecording))
		settings.setValue("gps/initFile", QVariant(self.gps_initFile))
		settings.setValue("gps/serial/device", QVariant(self.gps_serial))
		settings.setValue("gps/serial/bauds", QVariant(self.gps_serialBauds))
		settings.setValue("gps/file/path", QVariant(self.gps_file))
		settings.setValue("gps/file/charsPerSecond", QVariant(self.gps_fileCharsPerSecond))
		settings.setValue("gps/gpsd/host", QVariant(self.gps_gpsdHost))
		settings.setValue("gps/gpsd/port", QVariant(self.gps_gpsdPort))

		# compass
		settings.setValue("compass/use", QVariant(self.compass_use))
		settings.setValue("compass/device", QVariant(self.compass_device))
		settings.setValue("compass/bauds", QVariant(self.compass_bauds))

		
	def recordingStart(self):
		""" Start new recording (only call if there isn't any). """

		# check that we have gps input
		if not self.isGpsConnected():
			QMessageBox.warning(self.dockWidget, self.tr("Warning"), self.tr("GPS device isn't connected!\n\nPlease configure GPS input."))
			self.dockWidget.recording = False
			return
		# check we have position
		if self.getNmeaParser().fix == "none":
			if QMessageBox.warning(self.dockWidget, self.tr("Warning"),
					    self.tr("GPS doesn't have a valid position.\n\nDo you really want to start recording?"),
					    QMessageBox.Yes|QMessageBox.No) != QMessageBox.Yes:
				self.dockWidget.recording = False
				return

		self.recordingStartPathPreview()
		if not self.recordingStartGatherer():
			self.recordingStop()
			QMessageBox.information(self.dockWidget, self.tr("Warning"), self.tr("Recording was cancelled during initialization..."), self.tr("Ok"))
			return
		
		self.dockWidget.recording=True
		self.dockWidget_simple.recording=True
		
		#start a timer to keep the thread running...
		self.timer = QTimer()
		QObject.connect(self.timer, SIGNAL("timeout()"), self.runStatusTicker)
		self.timer.start(10)
		
		self.recording=True
		
	def recordingStop(self):
		""" Stop ongoing recording (only call if there is some). """
		self.recordingStopGatherer()
		if self.timer!=None:
			self.timer.stop()
			self.timer=None
			
		#we need to correctly terminate recording by processing events,
		#this leads to processGathererEvent_recordingTerminated()
		QCoreApplication.processEvents()
		
		self.recordingStopPathPreview()
		self.dockWidget.recording=False
		self.dockWidget_simple.recording=False
		self.recording=False
	
	def recordingStartGatherer(self):
		"""Start data gatherer thread"""
		self.gatherer=Gatherer.Gatherer(self)
		
		if not self.gatherer.alive:
			self.gatherer=None #don't try to stop the thread, as it's not running/alive
			return False
		
		QObject.connect(self.gatherer, SIGNAL("gathererEvent(PyQt_PyObject)"), self.processGathererEvent)
		
		self.gatherer.start()
		return True
		
	def recordingStopGatherer(self):
		"""Terminate data gatherer thread"""
		if self.gatherer!=None:
			self.gatherer.stop()
		
		#QObject.disconnect(gathererEvent) is done automatically...
			
	def recordingStartPathPreview(self):
		"""Initialize previewing recorded path"""
		self.rubberBand=QgsRubberBand(self.canvas)
		self.rubberBand.setColor(Qt.red)
		self.rubberBand.setWidth(3)
		self.rubberBand.reset(False)
	
	def recordingStopPathPreview(self):
		"""Terminate previewing recorded path"""
		self.rubberBand.setColor(Qt.green)
		self.previousPaths.append(self.rubberBand)
		self.rubberBand=None
		
		if not self.preview_keepPaths:
			self.removePathPreviews()
		else:
			self.canvas.refresh()
		
	def removePathPreviews(self):
		"""Remove recorded path previews from the map canvas"""
		for rb in self.previousPaths:
			self.canvas.scene().removeItem(rb)
		SourcePlugins.callMethodOnEach("clearMapCanvasItems", ())
		self.previousPaths=[]
		self.canvas.refresh()
	
	def recordingSwitch(self):
		""" If recording is on, turn it of - and the opposite :-) """
		if self.recording==False:
			self.recordingStart()
		else:
			self.recordingStop()
	
	def runStatusTicker(self):
		"""
		Make it possible for python to switch threads and
		if the gathering thread is not alive anymore, let
		the user know.
		"""
		if self.gatherer!=None:
			self.gatherer.msleep(1)

	def getLastDataSubdirectory(root):
		"""
			Returns last used data directory (including the time postfix). If no
			directory can be found, it returns empty string. The root parameter
			is data directory (specified by user), where the recordings are stored.
		"""
		dirs=[f for f in sorted(os.listdir(root))
			if os.path.isdir(os.path.join(root, f))]
			
		r=re.compile("[0-9]*-[0-9]*-[0-9]*_[0-9]*-[0-9]*-[0-9]*")
		dirs=[f for f in dirs if r.match(f)!=None]
		if len(dirs)!=0:
			return root+dirs[-1]+"/"
		else:
			return ""
	getLastDataSubdirectory=staticmethod(getLastDataSubdirectory)

	def processGathererEvent(self, data):
		try:
			apply(getattr(self, "processGathererEvent_"+data[0]), data[1:])
		except:
			traceback.print_exc(file=sys.stdout)
	
	def processGathererEvent_newTrackPoint(self, lat, lon, angle):
		"""Process 'new track point' event from gatherer."""
		try:
			if self.rubberBand and (lat!=0 or lon!=0):
				self.rubberBand.addPoint(QgsPoint(lon, lat))
		except:
			traceback.print_exc(file=sys.stdout)
	
	def gotNewTrackPoint(self, pt):
		""" update position marker """
		(lat, lon, angle, fix)=pt
		if lat!=0 or lon!=0:
			self.lastPosition=QgsPoint(lon, lat)
			self.lastAngle=angle
			self.lastFix=fix
			self.updatePositionMarker()
			self.updateExtent()
		
	
	def processGathererEvent_recordingTerminated(self, onUserRequest):
		"""Process 'recording terminated' event from gatherer."""
		self.gatherer.terminateAndCleanup()
		self.gatherer=None
		if not onUserRequest:
			self.recordingStop()
			QMessageBox.information(self.dockWidget,
				self.tr("Warning"),
				self.tr("Recording was cancelled by the gatherer thread (probably because of some communication error)..."),
				self.tr("Ok")
			)
			
	def updateExtent(self):
		"""Set correct map canvas extent for the current position and redraw."""
		extent=self.canvas.extent()
		if not self.preview_followPosition or self.lastPosition==None:
			pos=extent.center()
		else:
			boundaryExtent=QgsRectangle(extent)
			boundaryExtent.scale(0.5)
			if not boundaryExtent.contains(QgsRectangle(self.lastPosition, self.lastPosition)):
				pos=self.lastPosition
			else:
				pos=extent.center()
		
		if self.preview_scale!=self.last_preview_scale or pos!=extent.center():
			scale=pow(float(self.preview_scale)/99, 2)*0.4+0.0001
			newExtent=QgsRectangle(pos.x()-scale/2, pos.y()-scale/2, pos.x()+scale/2, pos.y()+scale/2)
			
			self.last_preview_scale=self.preview_scale
			
			self.canvas.setExtent(newExtent)
			self.canvas.refresh()

	def updatePositionMarker(self):
		"""Update position marker for the current position/orientation"""
		if self.positionMarker is None:
			return
		self.positionMarker.setHasPosition(self.lastFix)
		self.positionMarker.newCoords(self.lastPosition)
		self.positionMarker.angle=self.lastAngle
	
	def getNmeaParser(self):
		"""Returns the NMEA gps data parser object (useful to gather current pos. info)"""
		return self.gpsDaemon.nmeaParser
	
	def isGpsConnected(self):
		"""Returns, whether the gatherer is connected to gps device"""
		return self.gpsDaemon.isGpsConnected()

	def showInterface(self, simple):
		"""Show the specified version (simple or full) of user interface"""
		self.interface_simple=simple
		if self.curDockWidget!=None:
			self.iface.removeDockWidget(self.curDockWidget)
		
		if simple:
			self.curDockWidget=self.dockWidget_simple
		else:
			self.curDockWidget=self.dockWidget
		
		if simple!=None:
			self.iface.addDockWidget(Qt.RightDockWidgetArea, self.curDockWidget)
	
	def getRecordingEnabledAuxCheckbox(self, source):
		"""
		Returns checkbox widget for the specified source (string, e.g. 'Audio'),
		that informs user about recording status in the simple version of interface.
		Returns None, if specified source's checkbox isn't available.
		"""
		return self.dockWidget_simple.getRecordingEnabledCheckbox(source)
	
	def showHideDockWidget(self):
		if self.curDockWidget.isVisible():
			self.curDockWidget.hide()
		else:
			self.curDockWidget.show()

	def __dockwidgetVisibilityChanged(self, which):
		if self.curDockWidget.isVisible():
			self.actionDockWidget.setChecked(True)
		else:
			self.actionDockWidget.setChecked(False)
