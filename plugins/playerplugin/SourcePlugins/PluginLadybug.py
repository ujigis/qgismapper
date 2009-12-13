# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PluginLadybug_ui import Ui_PluginLadybug
from qgismapper.ladybug import LadybugWidget

import os, os.path



class PluginLadybug(QWidget, Ui_PluginLadybug):

	def __init__(self, controller, parent=None):
		QWidget.__init__(self, parent)
		self.controller=controller
		self.setupUi(self)
		self.name="Ladybug"
		self.w = None
		self.wGeom = QByteArray()
		self.startTime = None
		
		s = QSettings()
		self.wGeom = s.value("/plugins/player/ladybugwidget").toByteArray()
		
	def unload(self):
		if self.w is not None:
			s = QSettings()
			s.setValue("/plugins/player/ladybugwidget", QVariant(self.w.saveGeometry()))
	
	def loadRecording(self, dataDirectory):
		"""Tells the plugin to load recording from the specified directory."""
		
		self.dataDirectory=dataDirectory
		streamPath = os.path.join(self.dataDirectory, 'Ladybug', 'stream-000000.pgr')

		# open ladybug widget (if active and stream available)
		if os.path.exists(streamPath):
			if self.w is None:
				self.w = LadybugWidget()
				self.w.setWindowFlags(self.w.windowFlags() | Qt.WindowStaysOnTopHint)
				if not self.wGeom.isEmpty():
					self.w.restoreGeometry(self.wGeom)
			self.w.openStream(streamPath)
			self.w.show()
	
	def unloadRecording(self):
		"""Tells the plugin to unload current recording."""

		# kill ladybug widget
		if self.w is not None:
			#self.w.close()
			self.w.closeStream()
			#self.w = None
	
	def startReplay(self, fromTime):
		"""Tells the plugin to start replay from the specified time."""
		if self.w is not None:
			self.w.pause()
	
	def stopReplay(self):
		"""Tells the plugin to stop replay."""
		if self.w is not None:
			self.w.pause()
		
	def updateReplayToTime(self, time):
		"""
		Non-mandatory method.
		Update user interface to show informations of recording @ time. This
		call means that the replay continues without user intervention.
		"""
		# TODO: should update to the correct time (though we should be fine)

		# TODO: better way to find out start time???
		if self.startTime is None:
		    self.startTime=time
		
	def seekReplayToTime(self, time):
		"""
		Non-mandatory (though highly recommended) method.
		Sent to inform plugin that user moved the slider to seek the
		recording - and that plugin should reload required data.
		"""
		if self.w is not None:
			self.w.seekToTime( int((time-self.startTime)*1000) )
		
	def onMouseButtonPressed(self, button, canvasPoint, recordingLayerPoint):
		"""
		Non-mandatory method.
		Called, when the player map tool receives mouse press. The button (e.g. Qt.LeftButton)
		is stored in button parameter, canvasPoint contains coordinates of mouse press in
		canvas and recordingLayerPoint contains map coordinates of the point.
		"""
		return False
		
def getInstance(controller):
	"""
	This is a factory method to create the plugin's main object.
	The function also receives reference to controller instance, which is
	the main GatherPlugin object.
	"""
	return PluginLadybug(controller)
