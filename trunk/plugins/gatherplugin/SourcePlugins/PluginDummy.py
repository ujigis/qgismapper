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
		Mandatory method.
		This method is the first one called after the plugin object is created.
		It should load plugin's configuration from the specified QtXml
		element (and subelements, if needed). If no plugin configuration element
		was found in the configuration file, the rootElement is set to None.
		"""
		if not rootElement:
			#No previous configuration exists, use some meaningful defaults here
			self.rv=12345
			return
		
		if (rootElement.attribute("randomVal")!=""):
			self.rv=int(rootElement.attribute("randomVal"))
		
	def saveConfig(self, rootElement):
		"""
		Mandatory method.
		This method should save plugin's configuration to attributes of the
		specified QtXml element and/or to it's child elements. It's called right
		before the plugin is "deleted".
		"""
		rootElement.setAttribute("randomVal",
			str(int(self.rv))
		)
	
	def finalizeUI(self):
		"""
		Mandatory method.
		This method is called after the plugin widget was inserted to tab widget
		of gather widget and after the loadConfig() of this source plugin was
		called. At this point whole gather widget is initialized and it's possible
		to use all of it's standard functionality... 
		(e.g. controller.getRecordingEnabledAuxCheckbox)
		"""
		pass
	
	def startRecording(self, dataDirectory):
		"""
		Non-mandatory method.
		Start recording of data. This method is called from inside
		of the main thread so it is safe to call Qt UI methods. Because
		of this, the method should return immediately after preparing
		the input 'stream'.
		"""
		self.setEnabled(0)
		self.dataDirectory=dataDirectory
		
	def pollRecording(self):
		"""
		Non-mandatory method.
		In case the plugin writer doesn't want to run a separate thread/process
		for gathering data, every few milliseconds (as fast as possible) the
		gatherer cals all plugins' pollRecording method. If the method returns
		an integer, it is number of milliseconds that the plugin doesn't need
		any more data gathering (this may be used for optimizing the gathering
		cpu usage).
		"""
		pass
		
	def stopRecording(self):
		"""
		Non-mandatory method.
		Terminate recording of stream
		"""
		self.setEnabled(1)
		pass
		
	def clearMapCanvasItems(self):
		"""
		Non-mandatory method.
		Called when gatherer wants to clear all the previously
		recorded data from map canvas.
		"""
		pass
	
def getInstance(controller):
	"""
	This is a factory method to create the plugin's main object.
	The function also receives reference to controller instance, which is
	the main GatherPlugin object.
	"""
	return PluginDummy(controller)
