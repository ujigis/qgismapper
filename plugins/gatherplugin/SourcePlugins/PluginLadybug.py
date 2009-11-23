# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PluginLadybug_ui import Ui_PluginLadybug

from qgismapper.ladybug import Ladybug, LadybugFrame, LadybugGpsInfo

import os, sys, traceback

# TODO:
# - more diagnostics: invalid frames etc. (write to log!)

class PluginLadybug(QWidget, Ui_PluginLadybug):
	"""
	Plugin for controlling Ladybug2 spherical camera
	"""
	
	def __init__(self, controller, parent=None):
		QWidget.__init__(self, parent)
		self.controller=controller
		
		self.setupUi(self)

		#This is required and has to be a unique source plugin string,
		#so it's good idea to name it the same as the file (between Plugin and .py)
		self.name="Ladybug"

		self.cam = Ladybug()

		QObject.connect(
			self.btnEnableRecording, SIGNAL("clicked()"),
			self.recordingEnabledDisabled
		)
		
		QObject.connect(self.cam, SIGNAL("capturedFrame(LadybugFrame)"), self.capturedFrame)
		
		self.num_frames = 0
		self.num_mbytes = 0
		self.written = (0,0) # megabytes, frames
		self.frames_behind = 0
		self.frames_discarded = 0
		
		self.timerFps = QTimer()
		self.connect(self.timerFps, SIGNAL("timeout()"), self.updateFps)
		self.timerFps.start(1000)
		
		QObject.connect(self.cboCamera, SIGNAL("currentIndexChanged(int)"), self.cameraChanged)

		# TODO: ak spustim kameru tu tak to spadne
		
		# config defaults
		self.preview = True
		self.color = True
		self.cam_index = 1
		
		self.lblRecord.setText("") # what to show there when idle?
		
		
	def unload(self):
		""" called when plugin is going to quit """
		# stop the recording!
		if self.cam.isActive():
			self.cam.exit()

	def cameraChanged(self, index):
		self.cam_index = index
		self.updatePreviewSettings()
		
	def updatePreviewSettings(self):
		interval = 100
		color = True # always use color picture
		preview = (self.cam_index != 0) # first option is "no preview"
		camMask = (1 << (self.cam_index-1)) if preview else 0
		self.cam.setPreviewSettings(camMask, color, interval)
		
		# update gui
		self.widgetPreview.setImg(QImage())

	def updateFps(self):
		""" called every second to update status """
		self.lblFps.setText("%d" % self.num_frames)
		self.lblData.setText("%.1f MB/s" % self.num_mbytes)
		self.num_frames = 0
		self.num_mbytes = 0
		if not self.cam.isRecording():
		  self.lblRecord.setText("Off")
		  self.lblDiscarded.setText("None")
		else:
		  self.lblRecord.setText("%d frames\n%.1f MiB" % (self.written[1], self.written[0]) )
		  self.lblDiscarded.setText("%d frames" % self.frames_discarded)
		if self.frames_behind == 0:
		  self.lblLag.setText("None")
		else:
		  self.lblLag.setText("%d frames behind" % self.frames_behind)
		
	def recordingEnabledDisabled(self):
		
		if self.btnEnableRecording.isChecked():
			self.btnEnableRecording.setText("Recording enabled (click to disable)")
		else:
			self.btnEnableRecording.setText("Recording disabled (click to enable)")
		
		  
	def capturedFrame(self, f):
		try:
			#print "frame!!!", type(f), f.valid, f.frameBytes
			if f.valid:
				self.num_mbytes += float(f.frameBytes) / (1024 * 1024)
				self.num_frames += 1
				self.written = (f.megabytesWritten, f.framesWritten)
				self.frames_behind = f.framesBehind
				self.frames_discarded = f.framesDiscarded

				img = f.previewImage(self.cam_index-1 if self.cam_index > 0 else 0)
				if not img.isNull():
					self.widgetPreview.setImg(img)
		except:
			print "Error in PluginLadybug::capturedFrame:"
			print '-'*60
			traceback.print_exc(file=sys.stdout)
			print '-'*60


	def initCapture(self):
		""" initialize device """
		self.capturing = self.cam.init()
		if self.capturing:
			self.lblStatus.setText("OK")

			self.cboCamera.setCurrentIndex(self.cam_index)
			
			self.updatePreviewSettings()
		else:
			self.lblStatus.setText(self.cam.errorMessage())
			self.setEnabled(False)
			

	def finalizeUI(self):
		"""
		This method is called after the plugin widget was
		inserted to tab widget of gather widget. At this point,
		whole gather widget is initialized and it's possible
		to use all of it's standard functionality...
		(e.g. controller.getRecordingEnabledAuxCheckbox)
		"""
		QObject.connect(self.controller.gpsDaemon, SIGNAL("newTrackPoint(PyQt_PyObject)"), self.updateGpsInfo)

		self.initCapture()
		self.recordingEnabledDisabled()
		
	
	def startRecording(self, dataDirectory):
		"""
		Start recording of data. This method is called from inside
		of the main thread so it is safe to call Qt UI methods. Because
		of this, the method should return immediately after preparing
		the input 'stream'.
		"""
		if not self.cam.isActive():
		  # TODO: do something? a warning?
		  return
		
		self.btnEnableRecording.setEnabled(False)
		
		self.dataDirectory=dataDirectory+self.name+"/"
		if not os.path.isdir(self.dataDirectory):
			os.mkdir(self.dataDirectory)
		
		self.cam.startRecording(self.dataDirectory + "stream")
		

	def stopRecording(self):
		"""
		Terminate recording of stream
		"""
		self.btnEnableRecording.setEnabled(True)
		
		self.cam.stopRecording()
		
	def updateGpsInfo(self):
		""" tell ladybug about the position """
		gpsStatus = self.controller.gpsDaemon.getStatus()
		if not gpsStatus:
			return # we're not connected

		np=self.controller.getNmeaParser()
		if np.validPos:
			self.cam.setCurrentGpsInfo( LadybugGpsInfo(np.lon, np.lat, np.altitude) )


	# CONFIGURATION LOAD/SAVE

	def loadConfig(self, rootElement):
		"""
		This method should load plugin's configuration from the
		specified QtXml element (and subelements, if needed).
		"""
		if not rootElement:
			return
		self.cam_index = rootElement.attribute("camera", "1").toInt()[0]
		
		self.btnEnableRecording.setChecked( rootElement.attribute("recordingEnabled", "1").toInt()[0] )
		
		
	def saveConfig(self, rootElement):
		"""
		This method should save plugin's configuration to and
		under the specified QtXml element.
		"""
		rootElement.setAttribute("camera", str(self.cboCamera.currentIndex()) )

		rootElement.setAttribute("recordingEnabled", "1" if self.btnEnableRecording.isChecked() else "0")

	# UNUSED STUFF

	def pollRecording(self):
		"""
		In case the plugin writer doesn't want to run a separate thread/process
		for gathering data, every few milliseconds (as fast as possible) the
		gatherer cals all plugins' pollRecording method. If the method returns
		an integer, it is number of milliseconds that the plugin doesn't need
		any more data gathering (this may be used for optimizing the gathering
		cpu usage).
		"""
		pass
		
	def clearMapCanvasItems(self):
		"""
		Called, when gatherer wants to clear all the previously
		recorded data from map canvas.
		"""
		pass

def getInstance(controller):
	"""
	This is a factory method to create the plugin's main object.
	The function also receives reference to controller instance, which is
	the main GatherPlugin object.
	"""
	return PluginLadybug(controller)
