# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PluginGps_ui import Ui_PluginGps
import time

class PluginGps(QWidget, Ui_PluginGps):
	def __init__(self, controller, parent=None):
		QWidget.__init__(self, parent)
		self.controller=controller
		
		self.setupUi(self)
		self.name="Gps"
			
	def finalizeUI(self):
		self.enabledCheckBox=self.controller.getRecordingEnabledAuxCheckbox(self.name)
		QObject.connect(self.controller.gpsDaemon, SIGNAL("newTrackPoint(PyQt_PyObject)"), self.updateInfo)
		QObject.connect(self.controller.gpsDaemon, SIGNAL("gpsReconnect(PyQt_PyObject)"), self.updateInfo)

		self.updateTimer = QTimer()
		QObject.connect(self.updateTimer, SIGNAL("timeout()"), self.updateInfo)
		self.updateTimer.start(3000) # check in 3 seconds
		
	# configuration and recording is done in GpsDaemon, not here...
	def loadConfig(self, rootElement):
		return
	def saveConfig(self, rootElement):
		return
	def startRecording(self, dataDirectory):
		pass
	def stopRecording(self):
		pass
	def pollRecording(self):
		pass
	
	def updateInfo(self):
		""" update info contained in the widget: called from GpsDaemon """

		# check we're fine with GPS connection
		gpsStatus = self.controller.gpsDaemon.getStatus()
		if not gpsStatus:
			self.updateGui(0, self.tr("GPS not connected!"))
			return
		
		# check we're getting valid data
		timeNow = time.time()
		if timeNow - self.controller.gpsDaemon.lastDataTime > 3:
			self.updateGui(0, self.tr("No data coming from GPS!"))
			return
		if timeNow - self.controller.gpsDaemon.lastSentenceTime > 3:
			self.updateGui(0, self.tr("Invalid data coming from GPS!"))
			return

		# get info from nmea parser
		np=self.controller.getNmeaParser()
		posInfo = (np.lon, np.lat, np.validPos, np.altitude, np.angle, np.time, np.fix, np.hdop, np.vdop, np.pdop)
		sat = np.satellitesList()

		self.gpsInfo.setInfo(sat, posInfo)
		
		if np.fix=="none":
			self.updateGui(1, self.tr("GPS fix not available"))
		else:
			txt = self.tr("GPS fix available (using %1 of %2 satellites)").arg(np.numUsedSatellites()).arg(len(np.sats))
			self.updateGui(2, txt)


	def updateGui(self, state, errorMsg=None):
		""" status: 0=fatal 1=no signal 2=good """
		self.enabledCheckBox[0].setState(state)
		self.enabledCheckBox[1].setText(errorMsg)

		# update display widgets
		if state == 0: 
		  self.gpsInfo.setError(errorMsg)
		else:
		  self.gpsInfo.clearError()
		
		
def getInstance(controller):
	return PluginGps(controller)
