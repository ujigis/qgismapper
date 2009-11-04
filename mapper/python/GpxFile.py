# -*- coding: utf-8 -*-
import xml.dom.minidom
from PyQt4.QtXml import *
import sys, os, re
import traceback
from datetime import datetime
from time import mktime
from qgis.core import *
from qgis.gui import *

def getTextFromNode(root, name, valOnErr):
	try:
		element=root.getElementsByTagName(name)[0]
		return element.childNodes[0].nodeValue.strip()
	except:
		return valOnErr
	
def getFloatFromNode(root, name, valOnErr):
	rv=getTextFromNode(root, name, valOnErr)
	try:
		return float(rv)
	except:
		return rv

def parseIsoTime(text):
	t=datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
	return mktime(t.timetuple())+1e-6*t.microsecond

class TrkPoint():
	def __init__(self, element):
		self.lon=float(element.getAttribute("lon"))
		self.lat=float(element.getAttribute("lat"))
		
		self.ele=getFloatFromNode(element, "ele", 0)
		self.time=parseIsoTime(getTextFromNode(element, "time", 0))
		
		self.fix=getTextFromNode(element, "fix","")
		self.hdop=getFloatFromNode(element, "hdop",-1)
		self.vdop=getFloatFromNode(element, "vdop",-1)
		self.pdop=getFloatFromNode(element, "pdop",-1)
		
		self.angle=0
		self.gpsTime=0
		
		try:
			self.angle=float(getTextFromNode(element.getElementsByTagName("extensions")[0], "angle",0))
			self.gpsTime=parseIsoTime(getTextFromNode(element.getElementsByTagName("extensions")[0], "gpsTime",0))
		except:
			pass

	def getQGisCoords(self):
		return QgsPoint(self.lon, self.lat)
		
class TrkSeg():
	def __init__(self, element):
		self.mTrkPoints=[]
		for pt in element.getElementsByTagName("trkpt"):
			self.mTrkPoints.append(TrkPoint(pt))

class GpxFile():
	def __init__(self, path):
		self.mOk=True
		self.mTrkSegs=[]
	
		self.parse(path)
		self.recalculateInternals()
	
	def ok(self):
		return self.mOk
	
	def parse(self, path):
		dom1=xml.dom.minidom.parse(path)
		e_gpx = dom1.documentElement
		
		try:
			e_trk=e_gpx.getElementsByTagName("trk")[0]
			for seg in e_trk.getElementsByTagName("trkseg"):
				self.mTrkSegs.append(TrkSeg(seg))
		except:
			print "Error parsing "+path
			traceback.print_exc(file=sys.stdout)
			self.mOk=False
	
	def trackSegments(self):
		return self.mTrkSegs
	
	def recalculateInternals(self):
		self.length=0
		minTime=1e20
		maxTime=0
		for ts in self.trackSegments():
			for p in ts.mTrkPoints:
				self.length+=1
				if p.time<minTime:
					minTime=p.time
				if p.time>maxTime:
					maxTime=p.time
		
		self.minTimeF=minTime
		self.minTime=int(minTime)
		self.maxTime=int(maxTime)
		self.duration=self.maxTime-self.minTime

	def getTrkPtAtTime(self, time, negTolerance=0.0):
		"""
		Find the point in all segments, that's recorded at
		specified time or the "nearest previous time". If no such point
		exists, the first point is returned. Returns index of the point.
		@param negTolerance specifies, what is the maximal negative time difference
			between time requested and time of track point that's returned by
			the GpxFile.getTrkPtAtTime() method.
		"""
		pt=None
		i=0
		for ts in self.trackSegments():
			for p in ts.mTrkPoints:
				if p.time<=time+negTolerance:
					#points have ascending time, so we don't have to check
					pt=i
				else:
					if pt==None:
						pt=i
					return pt
				i+=1
		return pt
	
	def getTrkPtAtIndex(self, pos):
		"""
		Returns track point (TrkPoint object) at specified position in track.
		"""
		i=0
		for ts in self.trackSegments():
			if i+len(ts.mTrkPoints)<=pos:
				i+=len(ts.mTrkPoints)
				continue
			return ts.mTrkPoints[pos-i]

	def allTrackPoints(self):
		i=0
		for ts in self.trackSegments():
			for p in ts.mTrkPoints:
				yield (i, p)
				i+=1
	
	def isEmpty(self):
		"""Returns True, if gpx file doesn't contain any track points"""
		try:
			tmp=self.allTrackPoints().next()
			return False
		except:
			return True
	
class GpxCreation():
	def addElementFromNmea(gpxDoc, parentElement, elementName, nmeaVar, nmeaParser):
		if (not nmeaParser.__dict__.has_key(nmeaVar)):
			return
		element=gpxDoc.createElement(elementName)
		element.appendChild(
			gpxDoc.createTextNode(str(nmeaParser.__dict__[nmeaVar]))
		)
		parentElement.appendChild(element)
	addElementFromNmea=staticmethod(addElementFromNmea)
	
	def createTrkPt(gpxDoc, nmeaParser, forcedTime=None):
		trkpt=gpxDoc.createElement("trkpt")
		trkpt.setAttribute("lat", str(nmeaParser.lat))
		trkpt.setAttribute("lon", str(nmeaParser.lon))
		
		GpxCreation.addElementFromNmea(gpxDoc, trkpt, "ele",  "altitude", nmeaParser)
		if (forcedTime!=None):
			ext_time=gpxDoc.createElement("time")
			ext_time.appendChild(
				gpxDoc.createTextNode(str(forcedTime.strftime("%Y-%m-%d %H:%M:%S")))
			)
			trkpt.appendChild(ext_time)
		else:
			GpxCreation.addElementFromNmea(gpxDoc, trkpt, "time",  "time", nmeaParser)
		
		GpxCreation.addElementFromNmea(gpxDoc, trkpt, "fix",  "fix", nmeaParser)
		#GpxCreation.addElementFromNmea(trkpt, "sat",  "usedSatellites")
		GpxCreation.addElementFromNmea(gpxDoc, trkpt, "hdop",  "hdop", nmeaParser)
		GpxCreation.addElementFromNmea(gpxDoc, trkpt, "vdop",  "vdop", nmeaParser)
		GpxCreation.addElementFromNmea(gpxDoc, trkpt, "pdop",  "pdop", nmeaParser)
		
		ext=gpxDoc.createElement("extensions")
		GpxCreation.addElementFromNmea(gpxDoc, ext, "angle",  "angle", nmeaParser)
		if forcedTime!=None:
			GpxCreation.addElementFromNmea(gpxDoc, ext, "gpsTime",  "time", nmeaParser)
		trkpt.appendChild(ext)
		
		return trkpt
	createTrkPt=staticmethod(createTrkPt)
	
	def createDom():
		gpxDoc=QDomDocument()
		gpxDoc.appendChild(
			gpxDoc.createProcessingInstruction(
				"xml", "version=\"1.0\" encoding=\"utf-8\""
			)
		)
	
		gpxRoot=gpxDoc.createElement("gpx")
		gpxRoot.setAttribute("version",  "1.1")
		gpxDoc.appendChild(gpxRoot)
		
		gpxTrk=gpxDoc.createElement("trk")
		gpxRoot.appendChild(gpxTrk)
	
		gpxTrkseg=gpxDoc.createElement("trkseg")
		gpxTrk.appendChild(gpxTrkseg)
		
		return (gpxDoc, gpxTrkseg)
	createDom=staticmethod(createDom)