# -*- coding: utf-8 -*-
from PyQt4.QtCore import * 
from PyQt4.QtGui import *
from PyQt4.QtXml import *
from PyQt4.QtTest import *
import SourcePlugins
import serial
import time,  datetime
import sys,  os

class Gatherer(QThread):
	"""Thread object, that is managing all the data gathering."""
	def __init__(self, controller):
		QThread.__init__(self,  QThread.currentThread())
		self.controller=controller

		self.mutex=QMutex()
		self.alive=True
		
		if not self.initialize():
			self.terminate()
			return
		
	def run(self):
		"""Main execution method, that periodically polls for data."""
		self.stopMe=0
		
		while (self.stopMe==0) and self.controller.gpsDaemon.ok():
			QThread.msleep(50)
			SourcePlugins.callMethodOnEach("pollRecording", ())
		
		#let the caller know we finished
		self.emit(SIGNAL("gathererEvent(PyQt_PyObject)"), ("recordingTerminated", self.stopMe))
		
	def stop(self):
		"""Tell the gatherer thread to stop it's execution. Returns after it quits."""
		self.stopMe=1
		QThread.wait(self)

	def initialize(self):
		"""Initializes data gathering."""
		self.outputDirectory=self.getDataDirectory()
		
		SourcePlugins.callMethodOnEach("startRecording", (self.outputDirectory,))

		self.controller.gpsDaemon.startRecording(self.outputDirectory+"nmea.log", self.outputDirectory+"path.gpx")
		
		self.connect(self.controller.gpsDaemon, SIGNAL("newTrackPoint(PyQt_PyObject)"), self.onNewTrackPoint)
	
	def onNewTrackPoint(self, pt):
		"""Handle new track point."""
		(la, lo, an, fix)=pt
		self.emit(SIGNAL("gathererEvent(PyQt_PyObject)"), ("newTrackPoint", la, lo, an))
		
	def terminateAndCleanup(self):
		"""Stop gathering process."""
		self.msleep(500) #fixes video crashing when stopped immediately after start; TODO: do it better
		SourcePlugins.callMethodOnEach("stopRecording", ())
		
		self.controller.gpsDaemon.stopRecording()
		self.disconnect(self.controller.gpsDaemon, SIGNAL("newTrackPoint(PyQt_PyObject)"), self.onNewTrackPoint)
		
		self.alive=False
		
	def getDataDirectory(self):
		"""Returns directory path, where all data should be stored"""
		if not os.path.exists(self.controller.output_directory):
			os.makedirs(self.controller.output_directory)
		
		rv=""
		if (self.controller.output_append):
			rv=self.controller.getLastDataSubdirectory(self.controller.output_directory)
			
		if rv=="": #if none previous directory found
			rv=self.controller.output_directory+datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+"/"
			os.makedirs(rv)
		
		return rv
	
	def get_alive(self):
		self.mutex.lock()
		rv=self._alive
		self.mutex.unlock()
		return rv
		
	def set_alive(self, val):
		self.mutex.lock()
		self._alive=val
		self.mutex.unlock()
		
	alive=property(get_alive, set_alive)
	
	def getNmeaParser(self):
		"""Returns current gps data NMEA parser object."""
		return self.controller.gpsDaemon.nmeaParser
		
