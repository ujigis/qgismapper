# -*- coding: utf-8 -*-
# code based on PyGPS

import string
import math
import logging

"""
The parsing implementation deserves some comments:
Let's divide gps receivers in two categories: simple and professional.
Simple receivers can retrieve signal from up to (usually) 12 channels.
Professional (geodetic?) receivers are more complex: in addition to
american positioning system (GPS) they can handle also russian
system (GLONASS) and potentionally also use satellites from position
augmenting systems like WAAS (USA) or EGNOS (Europe). This brings additional
complexity to parsing of NMEA data, particularly satellite information.

There are several prefixes of NMEA sentences:
GP - data from GPS
GL - data from GLONASS
GN - data from multiple positioning systems

GSV - satellite elevation and azimuth - sent in epochs (up to 3 sentences),
each sentence can inform about 4 satellites. In case there are more than 12
satellites in view, not all satellites might be included in one epoch.
Therefore we consider a satellite to disappear only if it hasn't been included
in two subsequent epochs.

GSA - information about used satellites, fix and dillution of position.
This sentence might be sent separately for each positioning system,  information
about fix might differ among the systems, so we use only RMC and GGA sentences
to find out whether the position is valid or not.
"""

class SatInfo:
	def __init__(self):
		# from GSV
		self.prn, self.elev, self.azim, self.snr = 0,0,0,0
		self.system = 'GPS' # GPS / GLONASS
		self.gsvEpoch = 0 # last epoch (set of GSV sentences) when the info was updated

		# from GSA
		self.used = False
		self.gsaLast = 0

	def __cmp__(self, other):
		return cmp(self.prn, other.prn)

	def update(self, satWords, system, gsvEpoch):
		""" parse satellite info from GSV sentence """
		prn, elev, azim, snr = satWords
		if prn:  self.prn = string.atoi(prn)
		if elev: self.elev = string.atoi(elev)
		if azim: self.azim = string.atoi(azim)
		if snr:  self.snr = string.atoi(snr)
		self.system = system
		self.gsvEpoch = gsvEpoch


class NMEA:
	def __init__(self):
		self.sats = { } # key: PRN, value: SatInfo
		self.gsvEpoch = 0
		self.gsaLast = 0
		self.time = '?'
		self.mode = 0
		self.lat = 0.0
		self.lon = 0.0
		self.validPos = False
		self.angle = 0.0
		self.angleFromCompass = False
		self.altitude = 0.0
		self.track = 0.0
		self.speed = 0.0
		self.SAT = 0
		self.LATLON = 0
		self.fix="none"
		self.hdop=None
		self.vdop=None
		self.pdop=None

	def add_checksum(self,sentence):
		csum = 0
		for c in sentence:
			csum = csum ^ ord(c)
		return sentence + "%02X" % csum + "\r\n"

	def checksum(self,sentence, cksum):
		csum = 0
		for c in sentence:
			csum = csum ^ ord(c)
		return "%02X" % csum == cksum

	def update(self, lval, value, category):
		if lval != value:
			return (value, 1)
		else:
			return (lval, category)

	def  do_lat_lon(self, words):
		if len(words[0]) == 0 or len(words[1]) == 0: # empty strings?
			return
		if words[0][-1] == 'N':
			words[0] = words[0][:-1]
			words[1] = 'N'
		if words[0][-1] == 'S':
			words[0] = words[0][:-1]
			words[1] = 'S'
		if words[2][-1] == 'E':
			words[2] = words[2][:-1]
			words[3] = 'E'
		if words[2][-1] == 'W':
			words[2] = words[2][:-1]
			words[3] = 'W'
		if len(words[0]):
			lat = string.atof(words[0])
			frac, intpart = math.modf(lat / 100.0)
			lat = intpart + frac * 100.0 / 60.0
			if words[1] == 'S':
				lat = -lat
			(self.lat, self.LATLON) = self.update(self.lat, lat, self.LATLON)
		if len(words[2]):
			lon = string.atof(words[2])
			frac, intpart = math.modf(lon / 100.0)
			lon = intpart + frac * 100.0 / 60.0
			if words[3] == 'W':
				lon = -lon
			(self.lon, self.LATLON) = self.update(self.lon, lon, self.LATLON)

	def processGPRMC(self, words):
		global seconds
		# the Navman sleeve's GPS firmware sometimes puts the direction in the wrongw ord.
		day = string.atoi(words[8][0:2])
		month = string.atoi(words[8][2:4])
		year = 2000 + string.atoi(words[8][4:6])
		hours = string.atoi(words[0][0:2])
		minutes = string.atoi(words[0][2:4])
		seconds = string.atoi(words[0][4:6])
		self.validPos = (words[1] == "A")
		if words[1] == "V" or words[1] == "A":
			self.time = ("%04d-%02d-%02d %02d:%02d:%02d" %
				(year,  month, day,  hours, minutes, seconds))
			if words[6]: self.speed = string.atof(words[6])
			if words[7]: self.track = string.atof(words[7])

			self.do_lat_lon(words[2:])
		# save heading only if we don't receive it from compass
		if words[7]!="" and not self.angleFromCompass:
			self.angle=string.atof(words[7])
		
	def processGPGGA(self,words):
		self.do_lat_lon(words[1:])
		self.validPos = (string.atoi(words[5]) > 0)
		self.satellites = string.atoi(words[6])
		self.altitude = string.atof(words[8]) if len(words[8]) else 0

	def parseGSA(self,words):
		if len(words[1]):
			(self.mode, self.LATLON) = self.update(self.mode, string.atoi(words[1]), self.LATLON)
			self.fix=["none", "2d", "3d"][string.atoi(words[1])-1]
		else:
			self.fix="none"
		
		usedSatellites=[int(i) for i in words[2:13] if i!='']

		for prn,sat in self.sats.iteritems():
			if prn in usedSatellites:
				sat.used = True
				sat.gsaLast = self.gsaLast
			elif self.gsaLast - sat.gsaLast > 2:
				sat.used = False

		self.gsaLast += 1
		
		if words[14]!="":
			self.pdop = string.atof(words[14])
		if words[15]!="":
			self.hdop = string.atof(words[15])
		if words[16]!="":
			self.vdop = string.atof(words[16])
			if self.vdop == 0: self.vdop = None

	def processGPGSA(self,words):
		""" satellite info from GPS """
		self.parseGSA(words)
	def processGLGSA(self, words):
		""" satellite info from GLONASS """
		self.parseGSA(words)
	def processGNGSA(self, words):
		""" satellite info from multiple GNSS systems """
		self.parseGSA(words)

	def parseGSV(self,words,system):
		n = string.atoi(words[1])
		in_view = string.atoi(words[2])

		if n == 1 and system=='GPS': # new epoch
			# clean up entries not updated last few (2) epochs
			satsToDelete = []
			for prn in self.sats:
			    if self.gsvEpoch - self.sats[prn].gsvEpoch > 2:
				satsToDelete.append(prn)
			for prn in satsToDelete:
			    del self.sats[prn]
			# start new epoch
			self.gsvEpoch += 1

		f = 3 # field index
		n = (n - 1) * 4 # jump over the indexes we've filled already (4 sats per sentence)
		m = n + 4

		while n < in_view and n < m:
			if words[f]:
			    prn = string.atoi(words[f])
			    if not self.sats.has_key(prn):
				self.sats[prn] = SatInfo()
			    self.sats[prn].update(words[f:f+4], system, self.gsvEpoch)
			f += 4 # jump over these four fields we've just read
			n += 1

	def processGPGSV(self,words):
		""" satellite info from GPS """
		self.parseGSV(words, 'GPS')
	def processGLGSV(self, words):
		""" satellite info from GLONASS """
		self.parseGSV(words, 'GLONASS')
	def processGNGSV(self, words):
		""" satellite info from multiple systems """
		self.parseGSV(words, 'multi')

	def processPRWIZCH(self,words):
		""" a proprietary sentence from Zodiac chips. Do we really want to handle it??? """
		for i in range(12):
			prn = string.atoi(words[2*i+0])
			if self.sats.has_key(prn):
				self.sats[prn].srn = string.atoi(words[2*i+1]) # not SNR - it's "signal strength" (0..7)

	def processPTNTHPR(self,words):
		""" proprietary sentence from Honeywell HMR3000 compass """
		if len(words[0]) != 0:
			self.angle = float(words[0])
			self.angleFromCompass = True
		# there's also pitch and roll - but they're not interesting for us
		

	def handle_line(self, line):
		""" parse one NMEA sentence """
		if line=='':
			return None
		
		if line[0] != '$' or line[-2] != '\r' or line [-1] != '\n':
			logging.debug("NMEA: invalid data (not NMEA) ->"+line)
			return
		line = string.split(line[1:-2], '*')
		if len(line) != 2:
			logging.debug("NMEA: no checksum or invalid line")
			return
		if not self.checksum(line[0], line[1]):
			logging.debug("NMEA: bad checksum")
			return
		if '\x00' in line[0]:
			logging.debug("NMEA: null character in the sentence")
			return
		words = string.split(line[0], ',')

		if NMEA.__dict__.has_key('process'+words[0]):
			NMEA.__dict__['process'+words[0]](self, words[1:])
		else:
			logging.debug("NMEA: unknown sentence "+words[0])
		return words[0]



	
	def satellitesList(self):
		""" return list of satellite information: (sat#, signal, usage, elevation, azimuth) """
		return sorted(self.sats.values())

	def numUsedSatellites(self):
		""" return number of used satellites """
		num = 0
		for prn,sat in self.sats.iteritems():
		    if sat.used: num += 1
		return num

class NmeaBuffer:
	def __init__(self, nmeaParser, source, callback):
		self.nmeaParser = nmeaParser
		self.source = source
		self.callback = callback
		self.nmeaRawFile = None
		self.dataBuffer = ""

	def startLogging(self, nmeaOutputFile):
		self.nmeaRawFile=open(nmeaOutputFile, "a")

	def stopLogging(self):
		if self.nmeaRawFile:
			self.nmeaRawFile.close()
			self.nmeaRawFile=None

	def fetchAndProcessData(self):

		data=self.source.poll()
		
		if data is None or len(data) == 0:
			return False

		self.dataBuffer+=data
		if self.nmeaRawFile:
			self.nmeaRawFile.write(data)
		
		self.processNmeaData()
		return True
	 
	def processNmeaData(self):
		lines = self.dataBuffer.splitlines(True)

		# go trough all lines except the list one (might not be complete)
		for l in lines[0:-1]:
			sentence = self.nmeaParser.handle_line(l)
			self.callback(sentence)

		self.dataBuffer = lines[-1] # the unparsed rest of buffer
