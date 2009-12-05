# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtXml import *
from qgis.core import *
from qgis.gui import *
import resources_rc
from DockWidget import *
import SourcePlugins
import sys, os, re, shutil
from Enumerate import *
import traceback
from CanvasMarkers import PositionMarker
import math
from ReplayMapTool import *

# find out whether qgismapper support has been installed
try:
	has_qgismapper = True
	import qgismapper
except ImportError, e:
	has_qgismapper = False

# continue with loading 
if has_qgismapper:
	from qgismapper.GpxFile import GpxFile,GpxCreation
	from qgismapper import NMEA


configFilePath=os.path.expanduser("~/.qgis/QGisMapper_PlayerPlugin.xml")
""" path to plugins configuration file """

def parseBool(str):
	return {"True":True, "False":False}[str]
def QXmlGetNodeStr(node):
	return str(node.firstChild().toText().data()).strip()
def QXmlGetAttr(node, attr):
	return str(node.attributes().namedItem(attr).toAttr().value())
	
def nmeaToGpx(outFilePath, nmeaFile):
	"""Convert a nmea file to a gpx file."""
	parser=NMEA.NMEA()
	(gpxDoc,gpxTrkseg)=GpxCreation.createDom()
	
	while True:
		l=nmeaFile.readline().strip()
		if l=="":
			break
		
		if parser.handle_line(l)=="GPRMC" and (parser.lat!=0 or parser.lon!=0) and (parser.time!="?"):
			gpxTrkseg.appendChild(GpxCreation.createTrkPt(gpxDoc, parser))
	
	file=QFile(outFilePath)
	file.open(QIODevice.WriteOnly)
	file.write(str(gpxDoc.toString()))
	file.close()
	
def convertNmeaToRecording(targetDirectory, nmeaPath):
	"""
	Convert a nmea file to a new recording. The recording subdirectory will be
	automatically created from first real time spotted in the nmea file.
	"""
	f=open(nmeaPath, "r")
	parser=NMEA.NMEA()
	if not f:
		return False
	
	#determine start time
	while True:
		l=f.readline().strip()
		if l=="": #probably not a NMEA file
			return False
		
		if parser.handle_line(l)=="GPRMC" and (parser.lat!=0 or parser.lon!=0) and (parser.time!="?"):
			break
	
	newdir=targetDirectory+parser.time.replace(":", "-").replace(" ", "_")+"/"
	try:
		os.mkdir(newdir)
	except:
		return self.tr("Directory ")+newdir+self.tr(" exists. Move it away to continue...")
	
	f.seek(0)
	
	nmeaToGpx(newdir+"path.gpx", f)
	return True

class PlayerPlugin(QObject):
	"""
	Main Player plugin class - handles interaction with QGis and 
	organizes all the replaying stuff.
	"""

	def __init__(self, iface):
		QObject.__init__(self)
		self.iface = iface
	
	def initGui(self):
		""" Initialize plugin's UI """
		
		if not has_qgismapper:
			QMessageBox.information(self.iface.mainWindow(), "Player plugin",
				"It seems that 'qgismapper' python module is missing.\nYou have to install it in order to use Player plugin.")
			return
		
		#basic stuff
		self.lastRecordingLayer=None
		self.recording=0
		self.loadPlugins()
		self.loadConfiguration()
		self.rubberBand=None
		self.positionMarker=None
		self.replaySpeedScalingEnablingList={}
		
		#replay timer stuff
		self.replayTimer = QTimer()
		QObject.connect(self.replayTimer, SIGNAL("timeout()"), self.replayTimer_tick)
		self.replayTimeSource=self.defaultTimerSource
		
		#maptool
		QObject.connect(self.iface.mapCanvas(), SIGNAL("mapToolSet(QgsMapTool*)"), self.mapToolChanged)
		self.mapTool=ReplayMapTool(self.iface.mapCanvas(), self)
		self.mapTool_previous=None
		
		#GUI
		self.dockWidget=DockWidget(self)
		SourcePlugins.initializeUI(self.dockWidget.dataInputPlugins_tabWidget)
		self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockWidget)
		
		self.actionDockWidget=QAction("Show Player dock widget",self.iface.mainWindow())
		self.actionDockWidget.setCheckable(True)
		QObject.connect(self.actionDockWidget, SIGNAL("triggered()"), self.showHideDockWidget)
		self.iface.addPluginToMenu("Qgis-&mapper", self.actionDockWidget)
		QObject.connect(self.dockWidget, SIGNAL("visibilityChanged(bool)"), self.__dockwidgetVisibilityChanged)
		
		#corner-case - user erases the plugin's vector layer
		QObject.connect(QgsMapLayerRegistry.instance(), SIGNAL("layerWillBeRemoved(QString)"), self.onLayerWillBeRemoved)
		
	def unload(self):
		""" Cleanup and unload the plugin """

		if not has_qgismapper:
			return # ... wasn't initialized

		self.unloadRecording()
		
		self.dockWidget.unload()
		self.saveConfiguration()
		self.iface.removeDockWidget(self.dockWidget)
		
		self.iface.removePluginMenu("Qgis-&mapper",self.actionDockWidget)
		del self.actionDockWidget
		self.useMapTool(False)
		del self.mapTool
	
	def loadPlugins(self):
		SourcePlugins.loadPlugins(self)
	
	def loadConfiguration(self):
		""" Load configuration from a config file """
		self.loadDefaults()
		if os.path.isfile(configFilePath):
			try:
				dom1=QDomDocument()
				dom1.setContent(open(configFilePath).read())
				node = dom1.documentElement()
			except:
				return
			
			try:
				e_source=node.elementsByTagName("source").item(0)
				self.source_directory=QXmlGetNodeStr(e_source)
			except:
				pass
				
			try:
				e_replay=node.elementsByTagName("replay").item(0)
				self.replay_followPosition=parseBool(QXmlGetAttr(e_replay, "followPosition"))
				self.replay_speed=int(QXmlGetAttr(e_replay, "speed"))
			except:
				pass
			
			elements=node.elementsByTagName("sourcePlugins")
			SourcePlugins.loadConfig(elements)
		
	def saveConfiguration(self):
		""" Save configuration to a config file """
		doc=QDomDocument()
		docRoot=doc.createElement("configuration")
		doc.appendChild(docRoot)
		
		e_replay=doc.createElement("replay")
		e_replay.setAttribute("followPosition",  str(bool(self.replay_followPosition)))
		e_replay.setAttribute("speed",  str(int(self.replay_speed)))
		docRoot.appendChild(e_replay)
		
		e_source=doc.createElement("source")
		e_sourceDir=doc.createTextNode(self.source_directory)
		e_source.appendChild(e_sourceDir)
		docRoot.appendChild(e_source)
				
		e_sourcePlugins=doc.createElement("sourcePlugins")
		SourcePlugins.saveConfig(doc, e_sourcePlugins)
		docRoot.appendChild(e_sourcePlugins)
		
		file=open(configFilePath,  "w")
		file.write(doc.toString())
		file.close()
		
	def loadDefaults(self):
		""" Load default configuration values """
		self.source_directory=os.path.expanduser("~/qgismapper/data/")
		self.replay_followPosition=True
		self.replay_speed=100
	
	def loadRecordingsList(self):
		"""Load list of recordings in the current list.source_directory."""
		if not os.path.isdir(self.source_directory):
			QMessageBox.critical(self.dockWidget, self.tr("Error"), self.tr("Couldn't open the source directory: ")+self.source_directory)
			return

		self.dockWidget.setRecordingsListContents(
			PlayerPlugin.listRecordings(self.source_directory)
		)
		
		self.dockWidget.enableRecordingsList(True)
	
	def listRecordings(root):
		"""Returns list of recordings in the specified directory"""
		dirs=[f for f in sorted(os.listdir(root))
			if os.path.isdir(os.path.join(root, f))]
			
		r=re.compile("[0-9]*-[0-9]*-[0-9]*_[0-9]*-[0-9]*-[0-9]*")
		return [f for f in dirs if r.match(f)!=None]
	listRecordings=staticmethod(listRecordings)
	
	def loadSelectedRecording(self):
		"""Load the currently selected (in GUI) recording"""
		path = os.path.join(self.source_directory, self.dockWidget.getCurrentRecording())
		self.loadRecording(path)
	
	def loadRecording(self, path):
		"""Load the specified recording"""
		self.dockWidget.setEnabled(False)
		
		try:
			self.__loadRecording(path)
		except:
			pass
			
		self.dockWidget.setEnabled(True)
		
	def __loadRecording(self, path):
		"""Load the specified recording"""
		gpxFilePath=path+"/path.gpx"
		if not os.path.isfile(gpxFilePath):
			QMessageBox.information(self.dockWidget, self.tr("Error"), self.tr("Recording ")+path+self.tr(" couldn't be loaded (gpx file doesn't exist)"), self.tr("Ok"))
			return
		gpxFile=GpxFile(gpxFilePath)
		if not gpxFile.ok():
			QMessageBox.information(self.dockWidget, self.tr("Error"), self.tr("Recording ")+path+self.tr(" couldn't be loaded (invalid gpx file)"), self.tr("Ok"))
			return

		if gpxFile.isEmpty():
			QMessageBox.information(self.dockWidget, self.tr("Error"), self.tr("Recording ")+path+self.tr(" doesn't contain any valid track points, loading aborted."), self.tr("Ok"))
			return
		
		self.unloadRecording()

		self.gpxFile=gpxFile
		
		fileInfo=QFileInfo(gpxFilePath)
		pathParts=path.split("/")
		
		#we could get here twice (ass addVectorLayer() calls QApp::processEvents()),
		#but DockWidget should be disabled during __loadRecording(), thus preventing
		#user to click any user interface widgets...
		self.lastRecordingLayer=QgsVectorLayer(gpxFilePath+"?type=track", pathParts[len(pathParts)-1]+" track", "gpx")
		QgsMapLayerRegistry.instance().addMapLayer( self.lastRecordingLayer )
		QgsProject.instance().dirty( True )
		
		self.replay_currentPos=0
		
		SourcePlugins.callMethodOnEach("loadRecording", (path+"/",))
		
		if self.positionMarker==None:
			self.positionMarker=PositionMarker(self.iface.mapCanvas())
		
		self.emit(SIGNAL("recordingSwitched()"))
	
	def unloadRecording(self, deleteRecordingLayer=True):
		"""Unload the currently loaded recording"""
		if self.replayTimer.isActive():
			self.stopReplay()
		
		if self.lastRecordingLayer!=None:
			SourcePlugins.callMethodOnEach("unloadRecording", ())
			
			lid=self.lastRecordingLayer.getLayerID()
			self.lastRecordingLayer=None
			
			if deleteRecordingLayer:
				QgsMapLayerRegistry.instance().removeMapLayer(lid)
			
			self.gpxFile=None
			if self.positionMarker!=None:
				self.iface.mapCanvas().scene().removeItem(self.positionMarker)
				self.positionMarker=None
		
		self.emit(SIGNAL("recordingSwitched()"))
		
	def deleteRecording(self, rec):
		"""Delete specified recording from disk (and unload it, if it's loaded)"""
		self.unloadRecording()
		path = os.path.join(self.source_directory, self.dockWidget.getCurrentRecording())
		shutil.rmtree(path)
		self.loadRecordingsList()
	
	def isRecordingLoaded(self):
		"""Return true if some recording is loaded."""
		return self.lastRecordingLayer!=None
		
	def updateReplayPosition(self, pos):
		"""
		Update replay position to specified track position and update UI if required.
		If UI update is required, it can be specified, whether the onmap current position tracking
		should stop (which is convenient, when user is dragging the position marker by mouse to rewind).
		Also notifies plugins to update.
		Updating replay position means the replay should normally continue, not rewind as
		the direct consequence of this call (i.e. rewind should occur only if the current
		position differs from the requested too much).
		"""
		if not self.isRecordingLoaded():
			return
			
		self.replay_currentPos=pos
		self.replay_currentCoords=self.gpxFile.getTrkPtAtIndex(pos).getQGisCoords()
		self.replay_currentAngle=self.gpxFile.getTrkPtAtIndex(pos).angle
		
		self.positionMarker.setHasPosition(True)
		self.positionMarker.newCoords(self.replay_currentCoords)
		self.positionMarker.angle=self.replay_currentAngle
		
		if self.replay_followPosition:
			extent=self.iface.mapCanvas().extent()
			
			boundaryExtent=QgsRectangle(extent)
			boundaryExtent.scale(0.7)
			if not boundaryExtent.contains(QgsRectangle(self.replay_currentCoords, self.replay_currentCoords)):
				extentCenter=self.replay_currentCoords
				newExtent=QgsRectangle(
					extentCenter.x()-extent.width()/2,
					extentCenter.y()-extent.height()/2,
					extentCenter.x()+extent.width()/2,
					extentCenter.y()+extent.height()/2
				)
			
				self.iface.mapCanvas().setExtent(newExtent)
				self.iface.mapCanvas().refresh()
			
		SourcePlugins.callMethodOnEach("updateReplayToTime", (self.gpxFile.getTrkPtAtIndex(pos).time,))
	
	def seekReplayPosition(self, pos, stopFollowingPosition=False):
		"""Seek the current position to specified one"""
		if not self.isRecordingLoaded():
			return
		
		if stopFollowingPosition:
			self.dockWidget.setReplayFollowPositionChecked(False)
		
		self.dockWidget.setReplayPosition(pos, True)
		
	def notifySeekReplayPosition(self, pos):
		"""Notify plugins about seeking of the current position"""
		self.replayTimer_lastRecordingTime=self.gpxFile.getTrkPtAtIndex(pos).time
		SourcePlugins.callMethodOnEach("seekReplayToTime", (self.gpxFile.getTrkPtAtIndex(pos).time,))
		
	def enableScalingReplaySpeed(self, afector, enable):
		"""
		Tell, whether the specified afector (data player) allows
		non-realtime operation (i.e. slower or faster replay). If
		some of the afectors doesn't allow it, the functionality
		will be disabled globally.
		"""
		self.replaySpeedScalingEnablingList[afector]=enable
		for l in self.replaySpeedScalingEnablingList:
			if self.replaySpeedScalingEnablingList[l]==False:
				self.dockWidget.enableScalingReplaySpeed(False)
				return
		self.dockWidget.enableScalingReplaySpeed(True)
		
	def findNearestPointInRecording(self, toPoint):
		"""
		Find the point nearest (spatially) to the specified
		point (in map coordinates). Returns the point's index
		and it's position.
		"""
		dist=1e20
		nearestPoint=None
		nearestPointIdx=-1
		for (i, pt) in self.gpxFile.allTrackPoints():
			d=abs(complex(pt.lon-toPoint.x(), pt.lat-toPoint.y()))
			if d<dist:
				nearestPoint=pt
				nearestPointIdx=i
				dist=d
	
		return (nearestPointIdx, nearestPoint)
	
	def startReplay(self, startPos):
		"""Start data replay from specified position"""
		SourcePlugins.callMethodOnEach("startReplay", (self.gpxFile.getTrkPtAtIndex(startPos).time,))
		
		self.initTimerSource(startPos)
		self.replayTimer.start(1000)
		self.replayTimer_lastTime=time.time()
	
	def stopReplay(self):
		"""Stop ongoing replay."""
		if self.replayTimer.isActive():
			self.dockWidget.replayPlay_set(False)
			self.replayTimer.stop()
			SourcePlugins.callMethodOnEach("stopReplay", ())
	
	def isReplayOn(self):
		"""Returns true, if replay is active."""
		return self.replayTimer.isActive()
	
	def onMouseButtonPressed(self, button, canvasPoint, recordingLayerPoint):
		"""Handle muse button press on the map (pass the message to source plugins)"""
		return SourcePlugins.callMethodOnEachAndGetCumulativeReturnValue("onMouseButtonPressed", (button, canvasPoint, recordingLayerPoint))
	
	def importNmeaLog(self, path):
		""""Convert the specified nmea log to a recording."""
		return convertNmeaToRecording(self.source_directory, path)
	
	def setActiveSourceTab(self, widget):
		"""Activate the specified source plugin widget in the source plugins tab widget."""
		self.dockWidget.setActiveSourceTab(widget)

	def getCurrentReplayPos(self):
		return self.replay_currentPos

	def useMapTool(self, use):
		"""
		Replace current map tool with player plugin's one (if use==true), or restore
		the previous one (use==false).
		"""
		if use:
			if self.iface.mapCanvas().mapTool()!=self.mapTool:
				self.mapTool_previous=self.iface.mapCanvas().mapTool()
				self.iface.mapCanvas().setMapTool(self.mapTool)
		else:
			if self.mapTool_previous!=None:
				self.iface.mapCanvas().setMapTool(self.mapTool_previous)
			else:
				self.iface.mapCanvas().unsetMapTool(self.mapTool)
	
	def mapToolChanged(self, tool):
		"""Handle map tool changes outside player plugin"""
		if (tool!=self.mapTool) and self.dockWidget.mapToolChecked:
			self.mapTool_previous=None
			self.dockWidget.mapToolChecked=False
	
	def initTimerSource(self, pos):
		"""Initialize internal timer source"""
		self.replayTimer_lastTime=time.time()
		self.replayTimer_lastRecordingTime=self.gpxFile.getTrkPtAtIndex(pos).time
		
	def defaultTimerSource(self):
		"""Default timer source function"""
		curTime=time.time()
		
		#how much we want to move position in recording?
		diff=(curTime-self.replayTimer_lastTime)*float(self.replay_speed)/float(100)
		
		#try to move
		curPos=self.gpxFile.getTrkPtAtTime(self.replayTimer_lastRecordingTime)
		
		newRecTime=self.replayTimer_lastRecordingTime+diff
		
		#if we did move, remember it
		if curPos!=self.gpxFile.getTrkPtAtTime(newRecTime):
			self.replayTimer_lastTime=curTime
			self.replayTimer_lastRecordingTime=newRecTime
		
		return newRecTime
		
	def replayTimer_tick(self):
		"""
		Handle replay timer tick.
		"""
		self.dockWidget.setReplayPosition(
			self.gpxFile.getTrkPtAtTime(
				self.replayTimeSource()
			)
		)
		
		#and stop recording, if we hit the end
		if self.dockWidget.getReplayPosition()>=(self.gpxFile.length-1):
			self.stopReplay()
	
	def onLayerWillBeRemoved(self, layer):
		if self.lastRecordingLayer!=None:
			if layer==self.lastRecordingLayer.getLayerID():
				#our recording layer is deleted, unload the current recording, but
				#don't delete the layer again by doing that (qgis segfaults)
				self.unloadRecording(False)
				self.dockWidget.selectNoRecording()
		
	def setReplayTimeSource(self, source, initPos=None):
		"""
		Set the specified time source as the replay time source.
		Also initializes the replay position to the specified value,
		if source==None (internal timer source is used).
		"""
		if source==None:
			self.replayTimeSource=self.defaultTimerSource
			self.initTimerSource(initPos)
		else:
			self.replayTimeSource=source
		
	def showHideDockWidget(self):
		if self.dockWidget.isVisible():
			self.dockWidget.hide()
		else:
			self.dockWidget.show()

	def __dockwidgetVisibilityChanged(self):
		if self.dockWidget.isVisible():
			self.actionDockWidget.setChecked(True)
		else:
			self.actionDockWidget.setChecked(False)
