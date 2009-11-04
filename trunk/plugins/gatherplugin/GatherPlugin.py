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
from Enumerate import *
import Gatherer
import traceback
from CanvasMarkers import PositionMarker
import logging, logging.handlers

# find out whether qgismapper support has been installed
try:
	has_qgismapper = True
	import qgismapper
except ImportError, e:
	has_qgismapper = False

# continue with loading 
if has_qgismapper:
	from GpsDaemon import GpsDaemon

#path to plugin's configuration file
configFilePath=os.path.expanduser("~/.qgis/QGisMapper_GatherPlugin.xml")
logFilePath=os.path.expanduser("~/.qgis/GatherPlugin.log")

def parseBool(str):
	return {"True":True, "False":False}[str]

def QXmlGetNodeStr(node):
	"""Returns QXml node's text contents"""
	return str(node.firstChild().toText().data()).strip()
def QXmlGetAttr(node, attr):
	"""Returns QXml node's attribute value"""
	return str(node.attributes().namedItem(attr).toAttr().value())

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

		if not has_qgismapper:
			QMessageBox.information(self.iface.mainWindow(), "Gather plugin",
				"It seems that 'qgismapper' python module is missing.\nYou have to install it in order to use Gather plugin.")
			return

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

		if not has_qgismapper:
			return # ... wasn't initialized

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
		""" Load configuration from a config file """
		self.loadDefaults()
		if os.path.isfile(configFilePath):
			dom1=QDomDocument()
			dom1.setContent(open(configFilePath).read())
			node = dom1.documentElement()
			
			try:
				e_iface=node.elementsByTagName("interface").item(0)
				self.interface_simple=parseBool(QXmlGetAttr(e_iface, "simple"))
			except:
				pass #traceback.print_exc(file=sys.stdout)
			
			try:
				e_output=node.elementsByTagName("output").item(0)
				self.output_directory=QXmlGetNodeStr(e_output)
				self.output_append=int(QXmlGetAttr(e_output, "append"))
			except:
				pass #traceback.print_exc(file=sys.stdout)
				
			try:
				e_preview=node.elementsByTagName("preview").item(0).toElement()
				self.preview_followPosition=parseBool(QXmlGetAttr(e_preview, "followPosition"))
				self.preview_scale=int(QXmlGetAttr(e_preview, "scale"))
				self.preview_keepPaths=parseBool(QXmlGetAttr(e_preview, "keepPaths"))
			except:
				pass #traceback.print_exc(file=sys.stdout)
			
			try:
				e_gps=node.elementsByTagName("gps").item(0).toElement()
				self.gps_source=self.gps_source_ENUM.names.index(QXmlGetAttr(e_gps, "source"))
				
				attr=QXmlGetAttr(e_gps, "reconnectInterval")
				if attr!="":
					self.gps_reconnectInterval=int(attr)
					
				attr=QXmlGetAttr(e_gps, "attemptsDuringRecording")
				if attr!="":
					self.gps_attemptsDuringRecording=int(attr)

				self.gps_initFile=QXmlGetAttr(e_gps, "initFile")
				
				e_gpsSerial=e_gps.elementsByTagName("serial").item(0)
				if e_gpsSerial:
					self.gps_serial=QXmlGetNodeStr(e_gpsSerial)
					self.gps_serialBauds=QXmlGetAttr(e_gpsSerial, "bauds")
					
				e_gpsFile=e_gps.elementsByTagName("file").item(0)
				if e_gpsFile:
					self.gps_file=QXmlGetNodeStr(e_gpsFile)
					self.gps_fileCharsPerSecond=QXmlGetAttr(e_gpsFile, "charsPerSecond")
					
				e_gpsGpsd=e_gps.elementsByTagName("gpsd").item(0)
				if e_gpsGpsd:
					self.gps_gpsdHost=QXmlGetAttr(e_gpsGpsd, "host")
					self.gps_gpsdPort=int(QXmlGetAttr(e_gpsGpsd, "port"))
			except:
				pass #traceback.print_exc(file=sys.stdout)
				
			try:
				e_compass=node.elementsByTagName("compass").item(0).toElement()
				self.compass_use=parseBool(QXmlGetAttr(e_compass, "use"))
				self.compass_device=QXmlGetAttr(e_compass, "device")
				self.compass_bauds=int(QXmlGetAttr(e_compass, "bauds"))
			except:
				pass #traceback.print_exc(file=sys.stdout)

			elements=node.elementsByTagName("sourcePlugins")
			SourcePlugins.loadConfig(elements)
			
	def saveConfiguration(self):
		""" Save configuration to a config file """
		doc=QDomDocument()
		docRoot=doc.createElement("configuration")
		doc.appendChild(docRoot)
		
		e_iface=doc.createElement("interface")
		e_iface.setAttribute("simple", str(self.interface_simple))
		docRoot.appendChild(e_iface)
		
		e_output=doc.createElement("output")
		e_output.setAttribute("append",  str(self.output_append))
		e_outputDir=doc.createTextNode(self.output_directory)
		e_output.appendChild(e_outputDir)
		docRoot.appendChild(e_output)
		
		e_preview=doc.createElement("preview")
		e_preview.setAttribute("followPosition",  str(bool(self.preview_followPosition)))
		e_preview.setAttribute("scale",  str(self.preview_scale))
		e_preview.setAttribute("keepPaths",  str(self.preview_keepPaths))
		docRoot.appendChild(e_preview)
		
		e_gps=doc.createElement("gps")
		e_gps.setAttribute("source",  self.gps_source_ENUM.names[self.gps_source])
		e_gps.setAttribute("reconnectInterval",  str(self.gps_reconnectInterval))
		e_gps.setAttribute("attemptsDuringRecording",  str(self.gps_attemptsDuringRecording))
		e_gps.setAttribute("initFile", str(self.gps_initFile))
		docRoot.appendChild(e_gps)
		
		e_gpsSerial=doc.createElement("serial")
		e_gpsSerial.setAttribute("bauds", str(self.gps_serialBauds))
		e_gpsSerialPath=doc.createTextNode(self.gps_serial)
		e_gpsSerial.appendChild(e_gpsSerialPath)
		e_gps.appendChild(e_gpsSerial)
		
		e_gpsFile=doc.createElement("file")
		e_gpsFile.setAttribute("charsPerSecond", str(self.gps_fileCharsPerSecond))
		e_gpsFilePath=doc.createTextNode(self.gps_file)
		e_gpsFile.appendChild(e_gpsFilePath)
		e_gps.appendChild(e_gpsFile)
		
		e_gpsGpsd=doc.createElement("gpsd")
		e_gpsGpsd.setAttribute("host", str(self.gps_gpsdHost))
		e_gpsGpsd.setAttribute("port", str(self.gps_gpsdPort))
		e_gps.appendChild(e_gpsGpsd)
		
		e_compass=doc.createElement("compass")
		e_compass.setAttribute("use",  str(bool(self.compass_use)))
		e_compass.setAttribute("device",  str(self.compass_device))
		e_compass.setAttribute("bauds",  str(self.compass_bauds))
		docRoot.appendChild(e_compass)
		
		e_sourcePlugins=doc.createElement("sourcePlugins")
		SourcePlugins.saveConfig(doc, e_sourcePlugins)
		docRoot.appendChild(e_sourcePlugins)
		
		file=open(configFilePath,  "w")
		file.write(doc.toString())
		file.close()
		
	def loadDefaults(self):
		""" Load default configuration values """
		self.interface_simple=False
		self.gps_source_ENUM=Enumerate("SERIAL FILE GPSD")
		self.gps_source=self.gps_source_ENUM.SERIAL
		self.gps_reconnectInterval=2
		self.gps_attemptsDuringRecording=3
		self.gps_initFile = ""
		self.gps_serial="/dev/rfcomm0"
		self.gps_serialBauds=38400
		self.gps_file=os.path.expanduser("~/nmea_log")
		self.gps_fileCharsPerSecond=300
		self.gps_gpsdHost="localhost"
		self.gps_gpsdPort=2947
		self.compass_use=False
		self.compass_device="/dev/ttyUSB0"
		self.compass_bauds=19200
		self.output_directory=os.path.expanduser("~/qgis_mapper/gathered_data/")
		self.output_append=0
		self.preview_followPosition=True
		self.preview_scale=25
		self.last_preview_scale=25
		self.preview_keepPaths=True
	
	def recordingStart(self):
		""" Start new recording (only call if there isn't any). """
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
		self.rubberBand.setWidth(1)
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
