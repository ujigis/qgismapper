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

	def unload(self):
		"""
		Non-mandatory method.
		Allows plugin to do some cleanups and save configuration.
		"""
		settings = QSettings()
		settings.setValue("/plugins/GatherPlugin/Dummy/randomVal", QVariant(self.rv))
	
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
