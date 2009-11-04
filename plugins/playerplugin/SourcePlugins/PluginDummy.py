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
		
	def loadConfig(self, rootElement):
		"""
		This method is the first one called after the plugin object is created.
		It should load plugin's configuration from the specified QtXml
		element (and subelements, if needed). If no plugin configuration element
		was found in the configuration file, the rootElement is set to None.
		"""
		if not rootElement:
			self.rv=12345
			return
			
		if (rootElement.getAttribute("randomVal")!=""):
			self.rv=int(rootElement.getAttribute("randomVal"))
		
	def saveConfig(self, rootElement):
		"""
		This method should save plugin's configuration to attributes of the
		specified QtXml element and/or to it's child elements. It's called right
		before the plugin is "deleted".
		"""
		rootElement.setAttribute("randomVal",
			str(int(self.rv))
		)
	
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
