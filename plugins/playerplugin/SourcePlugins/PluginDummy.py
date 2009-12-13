# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PluginDummy_ui import Ui_PluginDummy

class PluginDummy(QWidget, Ui_PluginDummy):
	"""
	A dummy plugin doing absolutely nothing.
	"""
	def __init__(self, controller, parent=None):
		QWidget.__init__(self, parent)
		self.controller=controller
		
		self.setupUi(self)
		
		#This is a required property and has to be a unique source plugin string,
		#so it's good idea to name it the same as the file (between Plugin and .py)
		self.name="Dummy"
		
		# load some configuration variables
		settings = QSettings()
		# If no previous configuration exists, use some meaningful defaults here
		self.rv = settings.value("/plugins/GatherPlugin/Dummy/randomVal", QVariant(12345)).toInt()[0]
		
	def unload(self):
		"""
		Non-mandatory method.
		Allows plugin to do some cleanups and save configuration.
		"""
		settings = QSettings()
		settings.setValue("/plugins/GatherPlugin/Dummy/randomVal", QVariant(self.rv))
	
	def loadRecording(self, dataDirectory):
		"""Non-mandatory method. Tells the plugin to load recording from the specified directory."""
		self.setEnabled(0)
		
		self.dataDirectory=dataDirectory
	
	def unloadRecording(self):
		"""Non-mandatory method. Tells the plugin to unload current recording."""
		self.setEnabled(False)
	
	def startReplay(self, fromTime):
		"""Non-mandatory method. Tells the plugin to start replay from the specified time."""
		return
	
	def stopReplay(self):
		"""Non-mandatory method. Tells the plugin to stop replay."""
		return
		
	def updateReplayToTime(self, time):
		"""
		Non-mandatory method.
		Update user interface to show informations of recording @ time. This
		call means that the replay continues without user intervention.
		"""
		pass
		
	def seekReplayToTime(self, time):
		"""
		Non-mandatory (though highly recommended) method.
		Sent to inform plugin that user moved the slider to seek the
		recording - and that plugin should reload required data.
		"""
		pass
		
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
	return PluginDummy(controller)
