# -*- coding: utf-8 -*-
from PyQt4.QtCore import * 
from PyQt4.QtGui import *
from PyQt4.QtXml import *
from PyQt4.QtTest import *
import SourcePlugins
import serial
import NMEA
import time,  datetime
import sys,  os
from GpxFile import GpxCreation
import logging

#maximal allowed delay (in seconds) between start of trksegment recording and
#first trkpt in it (if bigger, a fake/stub trkpt will be inserted)
MAX_TRKSEG_EMPTY_BEGIN_TIME=1

try:
	import gps
	gpsModuleAvailable=True
except:
	gpsModuleAvailable=False


class GpsSource_serial():
	"""Serial port gps source handler"""
	def __init__(self, path="/dev/rfcomm0", bauds=38400, initFile=None):
		logging.debug("Starting SERIAL gps source: %s at %d bauds" % (path, int(bauds)))
		try:
			self.ser = serial.Serial(path, bauds)
			logging.debug("Started successfully")
		except:
			self.ser=None
			logging.debug("Failed to start")
			return

		# now try to send initialization string from file (if any)
		if initFile is not None and len(initFile) != 0:
			self._sendInitFromFile(initFile)
		
	def poll(self):
		try:
			w=self.ser.inWaiting()
			return self.ser.read(w) if w != 0 else None
		except IOError:
			# TODO: we should probably try to reconnect
			logging.debug("i/o error on serial port")
			return None
	
	def ok(self):
		if self.ser==None:
			return 0
		return self.ser.isOpen()
	
	def close(self):
		if (self.ser!=None):
			self.ser.close()

	def _sendInitFromFile(self, initFile):
		# read contents of the initialization file
		try:
			f = file(initFile,'r')
			initData = f.read()
			f.close()
		except IOError:
			logging.debug("failed to read serial init file: "+initFile)
			return
		# send contents to the serial port
		try:
			self.ser.write(initData)
			logging.debug("sent init string to gps")
		except StandardError:
			logging.debug("failed to send init string to serial port")


class GpsSource_file():
	"""File gps source handler"""
	def __init__(self, path, charsPerSecond):
		logging.debug("Starting FILE gps source: " + path)
		if os.path.exists(path):
			self.file=open(path,  "r")
			self.lastTime=time.time()
			self.charsPerSecond=float(charsPerSecond)
			self.eof=False
			logging.debug("Started successfully")
		else:
			self.file=None
			self.eof=True
			logging.debug("File doesn't exist")
		
	def poll(self):
		curTime=time.time()
		charsToRead=int((curTime-self.lastTime)*self.charsPerSecond)
		self.lastTime=curTime
		rv=self.file.read(charsToRead)
		if len(rv)<charsToRead:
			self.eof=True
		return rv
	
	def ok(self):
		return not self.eof
	
	def close(self):
		if self.file:
			self.file.close()



class GpsSource_gpsd():
	"""GPSd gps source handler"""
	def __init__(self, host="localhost", port="2947"):
		self.data=[]
		logging.debug("Starting GPSD gps source on %s:%s" % (host,port))
		try:
			self.session=gps.gps(host, port)
			logging.debug("Connected to gps daemon")
		except:
			self.session=None
			logging.debug("Failed to connect to gps daemon")
			return
		self.session.set_raw_hook(self.gpsd_poller)
		self.session.query("r")
		
	def poll(self):
		if not self.session:
			return None
		
		if self.session.waiting():
			self.session.poll()
		
		if self.data==[]:
			return None

		rv=self.data[0]
		self.data=self.data[1:]
		return rv
	
	def gpsd_poller(self, data):
		self.data.append(data)
		
	def ok(self):
		return self.session!=None
	
	def close(self):
		self.session=None


READ_DATA_INTERVAL=200 #interval between 2 reads from gps source

class GpsDaemon_opener(QThread):
	"""Asynchronous gps source opener"""
	def __init__(self, daemon):
		QThread.__init__(self)
		self.daemon=daemon
		self.doReset=True
	
	def run(self):
		while self.doReset:
			self.doReset=False
			c = self.daemon.controller # shortcut :-)
			if c.gps_source == "serial":
				src=GpsSource_serial(c.gps_serial, c.gps_serialBauds, c.gps_initFile)
			elif c.gps_source == "file":
				src=GpsSource_file(c.gps_file, c.gps_fileCharsPerSecond)
			else:
				if gpsModuleAvailable:
					src=GpsSource_gpsd(c.gps_gpsdHost, c.gps_gpsdPort)
				else:
					#TODO: tell user about the error cause somehow
					src=None

			self.daemon.gpsSource = src
		
	def resetAfterFinish(self):
		self.doReset=True
	
class GpsDaemon(QObject):
	"""
	A daemon which continuosly tries to keep connection to
	gps device and/or publish (via NMEA.NMEA class) and store
	(to gpx xml file) incoming data.
	Keep in mind that the object/class isn't thread safe. 
	"""
	def __init__(self, parent, controller):
		QObject.__init__(self, parent)
		self.controller=controller
		
		self.readDataTimer=None
		self.retryOpeningTimer=None
		self.gpsSource=None
		self.gpsSourceOpening=False
		self.compassSource=None
		self.retryCount=0
		self.gpxDoc=None
		self.lastDataTime = 0
		self.lastSentenceTime = 0
		
		self.resetGpsSource()
		
	def resetGpsSource(self):
		"""Close current connection to GPS device and try opening a new one"""
		self.terminate()
		return self.startOpeningGpsSource()
		
	def isGpsConnected(self):
		"""Returns, whether gps device is opened (=connected to daemon)"""
		return self.gpsSource!=None
	
	def terminate(self):
		"""Close connection to gps source"""
		logging.debug("Terminating gps communication")
		if self.readDataTimer!=None:
			self.killTimer(self.readDataTimer)
			self.readDataTimer=None
			
		if self.retryOpeningTimer!=None:
			self.killTimer(self.retryOpeningTimer)
			self.retryOpeningTimer=None
		
		if self.gpsSource!=None:
			self.gpsSource.close()
		
		self.nmeaParser=None
		
	def startOpeningGpsSource(self):
		"""
		Initialize connecting to gps source. After successful opening,
		onOpenGpsSource_finished() is called.
		"""
		logging.debug("Starting gps source")
		if self.gpsSourceOpening:
			self.gpsSource_opener.resetAfterFinish()
			return False
		
		self.gpsSource=None
		self.gpsSource_opener=GpsDaemon_opener(self)
		self.gpsSourceOpening=True
		QObject.connect(self.gpsSource_opener, SIGNAL("finished()"), self.onOpenGpsSource_finished)
		
		self.gpsSource_opener.start()
		return True
	
	def startCompass(self, device, bauds):
		""" try to start compass. maybe it could also get some more love like reconnects etc """
		logging.debug("Starting compass source")

		self.compassSource=GpsSource_serial(device, bauds)
		self.compassBuffer=NMEA.NmeaBuffer(self.nmeaParser, self.compassSource, self.receivedNmeaSentence)
		if not self.compassSource.ok():
			logging.debug("Failed to start compass")
			self.compassSource=None

		
	def onOpenGpsSource_finished(self):
		"""Called when daemon successfully opened connection to gps source"""
		if self.isGpsConnected() and self.gpsSource.ok():
			self.nmeaParser=NMEA.NMEA()
			self.readDataTimer=self.startTimer(READ_DATA_INTERVAL)
			self.gpsBuffer=NMEA.NmeaBuffer(self.nmeaParser, self.gpsSource, self.receivedNmeaSentence)
			self.retryCount=0
		else:
			self.gpsSource=None
			self.retryOpeningTimer=self.startTimer(self.controller.gps_reconnectInterval*1000)
			self.nmeaParser=None
			self.retryCount+=1
			
		self.gpsSourceOpening=False
		self.gpsSource_opener=None
		
		self.emit(SIGNAL("gpsReconnect(PyQt_PyObject)"), ())

		if self.controller.compass_use:
			self.startCompass(self.controller.compass_device, self.controller.compass_bauds)
		
	def timerEvent(self, event):
		"""Misc. timer event handler"""
		if event.timerId()==self.retryOpeningTimer:
			self.resetGpsSource()
		elif event.timerId()==self.readDataTimer:
			
			#process all pending gps data
			while self.gpsBuffer.fetchAndProcessData():
			    self.lastDataTime = time.time()
			
			if not self.gpsSource.ok():
				self.resetGpsSource()

			# try to get data from compass is available
			if self.compassSource:
				while self.compassBuffer.fetchAndProcessData():
				    pass

	def startRecording(self, nmeaOutputFile, gpxPath):
		"""Start recording gps data to nmea and gps output files"""
		self.retryCount=0
		self.gpsBuffer.startLogging(nmeaOutputFile)
		self.gpxPath=gpxPath
		self.initializeGpxOutput()
	
	def stopRecording(self):
		"""Flush remaining data to output files and stop recording new ones."""
		file=QFile(self.gpxPath)
		file.open(QIODevice.WriteOnly)
		file.write(str(self.gpxDoc.toString()))
		file.close()
		self.gpxDoc=None
		
		self.gpsBuffer.stopLogging()
	
	def ok(self):
		"""
		Returns, whether the daemon is in good state (i.e. the gps connection is
		successfully opened or the opening retry count is less than limit value).
		"""
		return self.retryCount<=self.controller.gps_attemptsDuringRecording
	
	def initializeGpxOutput(self):
		"""Preinitialize gpx output object."""
		self.gpxDoc=QDomDocument()
		if os.path.isfile(self.gpxPath):
			file=QFile(self.gpxPath)
			if (file.open(QIODevice.ReadOnly)):
				self.gpxDoc.setContent(file)
				file.close()
				
				self.gpxRoot=self.gpxDoc.documentElement()		
		
				trkNodes=self.gpxRoot.elementsByTagName("trk")
				self.gpxTrk=trkNodes.item(trkNodes.length()-1).toElement()
				
				self.gpxTrkseg=self.gpxDoc.createElement("trkseg")
				self.gpxTrk.appendChild(self.gpxTrkseg)
		else:
			(self.gpxDoc,self.gpxTrkseg)=GpxCreation.createDom()
		
		self.gpxTrksegStartTime=datetime.datetime.now()
	
	def receivedNmeaSentence(self, sentence):
		""" callback method - called from the NmeaBuffer """
		#print "GOT ",sentence
		# update last sentence time - to signal that we're receiving correct data
		if sentence is not None:
			self.lastSentenceTime = time.time()

		if sentence=="GPRMC":
			if (self.nmeaParser.lat!=0 or self.nmeaParser.lon!=0) and self.gpxDoc:
				curTime=datetime.datetime.now()
				trkpt=GpxCreation.createTrkPt(self.gpxDoc, self.nmeaParser, curTime)
				if self.gpxTrkseg.elementsByTagName("trkpt").count()==0:
					#if delay between start of recording and first trk point is too big,
					#insert arbitary first track point to have a correct recording length
					#(so that user is able to play all recorded data - video etc.)
					diff=curTime-self.gpxTrksegStartTime
					if diff.days*24*3600+diff.seconds>MAX_TRKSEG_EMPTY_BEGIN_TIME:
						trkpt_stub=GpxCreation.createTrkPt(self.gpxDoc, self.nmeaParser, self.gpxTrksegStartTime)
						self.gpxTrkseg.appendChild(trkpt_stub)
				self.gpxTrkseg.appendChild(trkpt)
			
			self.emitNewTrackPoint()
		if sentence=="PTNTHPR":
			self.emitNewTrackPoint()
	
	def emitNewTrackPoint(self):
		self.emit(SIGNAL("newTrackPoint(PyQt_PyObject)"), (self.nmeaParser.lat, self.nmeaParser.lon, self.nmeaParser.angle, (self.nmeaParser.fix!="none")))

	def getStatus(self):
		""" find out whether everything's fine :-) """
		return self.isGpsConnected() and self.gpsSource.ok() and self.nmeaParser is not None


if __name__=="__main__":
	gs=GpsSource_gpsd()
	while (1):
		sys.stdout.write(gs.poll())
	
