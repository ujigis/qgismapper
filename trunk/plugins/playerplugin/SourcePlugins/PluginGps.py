# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PluginGps_ui import Ui_PluginGps
import datetime, time

def unixTimeToString(t):
	return str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t)))
	
class PluginGps(QWidget, Ui_PluginGps):
	"""Source plugin, that displays current position's gps info in the plugin's tab widget"""
	def __init__(self, controller, parent=None):
		QWidget.__init__(self, parent)
		self.controller=controller
		
		self.setupUi(self)
		self.name="Gps"

		# create 10 empty items
		items = [ QTreeWidgetItem(None, [ "", ""]) for i in xrange(10) ]
		self.info_treeWidget.insertTopLevelItems(0, items)
		
	def loadRecording(self, dataDirectory):
		self.setEnabled(1)
		self.dataDirectory=dataDirectory
	def unloadRecording(self):
		self.setEnabled(False)
		
	def updateReplayToTime(self, time):
		pt=self.controller.gpxFile.getTrkPtAtIndex(self.controller.getCurrentReplayPos())
		try:
			gpsTime=pt.gpsTime
		except:
			gpsTime=pt.time
		
		self.showInfo(pt.lon, pt.lat, pt.ele, pt.angle, pt.time, gpsTime, pt.fix, pt.hdop, pt.vdop, pt.pdop)
	def seekReplayToTime(self, time):
		return
		
	def showInfo(self, lon, lat, ele, angle, time, gpsTime, fix, hdop, vdop, pdop):
		self.showInfoItem(0, self.tr("Longitude"), str(lon))
		self.showInfoItem(1, self.tr("Latitude"), str(lat))
		self.showInfoItem(2, self.tr("Elevation"), str(ele))
		self.showInfoItem(3, self.tr("Bearing"), str(angle))
		self.showInfoItem(4, self.tr("Time of record"), unixTimeToString(time))
		self.showInfoItem(5, self.tr("GPS time of record"), unixTimeToString(gpsTime))
		self.showInfoItem(6, self.tr("Fix"), str(fix))
		self.showInfoItem(7, self.tr("HDop"), str(hdop))
		self.showInfoItem(8, self.tr("VDop"), str(vdop))
		self.showInfoItem(9, self.tr("PDop"), str(pdop))
	
	def showInfoItem(self, row, key, val):
		item = self.info_treeWidget.topLevelItem(row)
		item.setText(0, key)
		item.setText(1, val)
	
	def onMouseButtonPressed(self, button, canvasPoint, recordingLayerPoint):
		return False
		
def getInstance(controller):
	return PluginGps(controller)
