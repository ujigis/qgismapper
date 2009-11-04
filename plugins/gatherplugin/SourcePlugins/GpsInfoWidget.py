# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import datetime, time, math

WORLDSIDE_FONTSIZE=20
GPSINFO_FONTSIZE=12
SMALLFONT_SIZE=8

SATS_GRAPH_HEIGHT=100

usedSatelliteBrush=QBrush(QColor(85,170,255))
unusedSatelliteBrush=QBrush(QColor(192,192,192))
		
def formatCoord(val, signChars):
	if val<0:
		c=signChars[0]
	else:
		c=signChars[1]
	val = abs(val)
	deg = int(val)
	mins = (val-deg)*60
	return u"%c %02d°%06.3f'" % (c, deg, mins)

class GpsInfoWidget(QWidget):
	"""
	Widget displaying basic GPS info (position etc.) and
	a satellite-onsky-positions graph.
	"""
	def __init__(self, parent=None): 
		QWidget.__init__(self, parent)
		self.setMinimumHeight(150)
		self.setMinimumWidth(150)
		
		self.satellites=[]
		(self.lon, self.lat, self.validPos, self.altitude, self.angle, self.gpsTime, self.fix, self.hdop, self.vdop, self.pdop)=(0,0,False,0,0,0,0,0,0,0)
		
		self.nonePen=QPen(Qt.NoPen)
		self.textPen=QPen(Qt.white)
		self.blackPen=QPen(Qt.black)
		self.arrowPen=QPen(QColor(0,0,0,50))
		
		self.radarBrush=QBrush(QColor(120, 190, 255, 90))
		
		self.arrowNBrush=QBrush(QColor(255, 0, 0, 90))
		self.arrowSBrush=QBrush(QColor(0, 0, 255, 90))
		
		fnt = self.font()
		self.font1=QFont(fnt)
		self.font1.setPointSize(SMALLFONT_SIZE)
		self.font2=QFont(fnt)
		self.font2.setPointSize(WORLDSIDE_FONTSIZE)
		self.font2.setBold(True)
		self.font3=QFont(fnt)
		self.font3.setPointSize(GPSINFO_FONTSIZE)
		
		self.verbose=True

		self.clearError()
		
	def paintEvent(self, e):
		rect=QRect(e.rect())
		
		p=QPainter(self)
		
		rectGraph = QRect(0, rect.height()-SATS_GRAPH_HEIGHT, rect.width(), SATS_GRAPH_HEIGHT)

		rect.setHeight(rect.height()-1 - SATS_GRAPH_HEIGHT)
		rect.setWidth(rect.width()-1)

		if self.errorText is not None:
			p.setPen(Qt.darkRed)
			p.setFont(self.font3)
			p.drawText(20,40, self.errorText)
			return # no more drawing
		
		p.setRenderHint(QPainter.Antialiasing, False)
		self.drawBarGraph(p, rectGraph)
		p.setRenderHint(QPainter.Antialiasing)

		if self.verbose:
			p.save()
			p.translate(rect.width()-rect.width()*0.6, rect.top())
			p.scale(0.6, 0.6)
			self.drawSatGraph(p, QRect(rect))
			p.restore()
		else:
			self.drawSatGraph(p, rect)
		
		self.drawTextInfo(p, rect)



	def drawSatGraph(self, p, rect):
		"""
		Draw satellites'-position-on-the-sky graph
		"""
		if rect.width()>rect.height():
			rect.setWidth(rect.height())
		else:
			rect.setHeight(rect.width())
	
		#draw background circle
		p.setBrush(self.radarBrush)
		p.setPen(self.blackPen)
		p.drawEllipse(rect)
		
		course=math.radians(-self.angle)
		self.drawArrow(p, rect, course, self.arrowNBrush, self.arrowPen)
		self.drawArrow(p, rect, course+math.pi, self.arrowSBrush, self.arrowPen)
		
		self.drawWorldDirections(p, rect, course)
		self.drawSatellites(p, rect, course)
		
	def drawArrow(self, p, rect, course, arrowBrush, arrowPen):
		"""Draw north-south arrow"""
		p.setBrush(arrowBrush)
		p.setPen(arrowPen)
		
		radius=rect.width()/2
		
		poly=QPolygon([
			QPoint(math.sin(course+0)*radius, -math.cos(course+0)*radius),
			QPoint(math.sin(course+math.pi/2)*radius/3, -math.cos(course+math.pi/2)*radius/3),
			QPoint(math.sin(course+3*math.pi/2)*radius/3, -math.cos(course+3*math.pi/2)*radius/3)
		])
		poly.translate(rect.width()/2, rect.height()/2)
		
		p.drawPolygon(poly)
		
	def drawWorldDirections(self, p, rect, course):
		"""Draw world sides (NSEW) letters into the sky graph"""
		course=course-math.pi/360*10 #compensate text offset
		
		xC=rect.width()/2
		yC=rect.height()/2
		radius=rect.width()/2-WORLDSIDE_FONTSIZE
		
		p.setPen(self.blackPen)
		p.setFont(self.font2)
		
		self.drawText(p, QPoint(xC+math.sin(course)*radius, yC-math.cos(course)*radius), 0+math.degrees(course), "N")
		self.drawText(p, QPoint(xC+math.sin(course+math.pi)*radius, yC-math.cos(course+math.pi)*radius), 180+math.degrees(course), "S")
		self.drawText(p, QPoint(xC+math.sin(course+math.pi/2)*radius, yC-math.cos(course+math.pi/2)*radius), 90+math.degrees(course), "E")
		self.drawText(p, QPoint(xC+math.sin(course+3*math.pi/2)*radius, yC-math.cos(course+3*math.pi/2)*radius), 270+math.degrees(course), "W")
		
	def drawText(self, painter, point, angle, text):
		"""Draw text string, rotated and translated."""
		painter.save()
		painter.translate(point)
		painter.rotate(angle)
		painter.drawText(0, 0, text)
		painter.restore()
		
	def drawSatellites(self, p, rect, course):
		"""Draw satellites' positions into graph"""
		xC=rect.width()/2
		yC=rect.height()/2
		radius=rect.width()/2
		
		p.setFont(self.font1)
		
		for sat in self.satellites:
			if sat.used:
				p.setBrush(usedSatelliteBrush)
			else:
				p.setBrush(unusedSatelliteBrush)
			
			r=radius*(90-sat.elev)/100 #100 is a downscale factor, so that satellites aren't placed at border
			a=math.radians(sat.azim)+course
			
			satRect=QRect(math.sin(a)*r+xC, -(math.cos(a)*r)+yC, 9, 9)
			p.drawEllipse(satRect)
			
			p.drawText(satRect.left(), satRect.top(), str(sat.prn))
			
	def dopText(self, dop):
		if dop is None: return "---"
		if dop <= 2: return self.tr("Excellent")
		if dop <= 5: return self.tr("Good")
		if dop <=10: return self.tr("Moderate")
		if dop <=20: return self.tr("Fair")
		return self.tr("Poor")
		
	def drawTextInfo(self, p, rect):
		"""Draw textual informations about current position."""
		p.setFont(self.font1)
		if not self.verbose:
			p.drawText(0, SMALLFONT_SIZE, self.tr("Click for more info"))
		else:
			p.drawText(0, SMALLFONT_SIZE, self.tr("Click for less info"))
			
			p.setFont(self.font3)
			
			y = 1.5*SMALLFONT_SIZE+GPSINFO_FONTSIZE
			LINE_GAP = GPSINFO_FONTSIZE + 7
			if self.validPos:
				p.drawText(0, y, "Fix: %s" % self.fix)
				y += LINE_GAP
				#p.drawText(0, y, "HDop: " + self.dopText(self.hdop))
				#y += LINE_GAP
				#p.drawText(0, y, "VDop: " + self.dopText(self.vdop))
				#y += LINE_GAP
				p.drawText(0, y, "PDop: " + self.dopText(self.pdop))
			
				y += LINE_GAP
				p.drawText(0, y, formatCoord(self.lat, ('S','N')))
				y += LINE_GAP
				p.drawText(0, y, formatCoord(self.lon, ('W','E')))
				y += LINE_GAP
				p.drawText(0, y, "%s: %d m" % (self.tr("Altitude"), self.altitude) )
				y += LINE_GAP
			else:
				y += LINE_GAP * 5
			p.drawText(0, y, "Heading: %.1f" % self.angle)
			
			y += LINE_GAP
			p.drawText(0, y, "%s: %s" % (self.tr("GPS Time"), str(self.gpsTime)) )
				
			
	def setInfo(self, satellites, data):
		"""
		Sets current satellites and additional data from gps.
		A single satellite 'information' in the array has the following structure:
		(satelliteNumber, signalStrength, isSatelliteUsed, elevation, angle)
		"""
		self.satellites=satellites
		(self.lon, self.lat, self.validPos, self.altitude, self.angle, self.gpsTime, self.fix, self.hdop, self.vdop, self.pdop)=data
		self.update()
		
	def mousePressEvent(self, ev):
		"""Handle mouse press (cycle simple/verbose display mode)."""
		self.verbose=not self.verbose
		self.update()

	def setError(self, txt):
		""" Sets an error that will be shown in the widget """
		self.errorText = txt
		self.update()

	def clearError(self):
		""" Clear an error (if any) """
		self.setError(None)
	
	
	def drawBarGraph(self, p, rect):
		"""Draw bar graph of satellites in view into specified rectangle."""
		if len(self.satellites)==0:
			return
		
		fm = QFontMetrics(p.font())
		txtH = fm.height() # height of text
		originX=rect.left()
		originY=rect.top()
		boxH=rect.height() - txtH # space for satellite number
		boxW = min(25, rect.width()/len(self.satellites))
		satW = boxW-4
		
		for sat in self.satellites:
			p.setPen(Qt.black)
			p.setBrush(usedSatelliteBrush if sat.used else unusedSatelliteBrush)

			barHeight = boxH*sat.snr/60

			p.save()
			p.translate(originX+(boxW-satW)/2, originY+boxH)
			p.drawRect(0, -barHeight, satW, barHeight)
			p.drawText(0, 0, satW, txtH, Qt.AlignCenter, str(sat.prn))
			p.drawText(0, -barHeight-txtH, satW, txtH, Qt.AlignCenter, str(sat.snr))
			p.restore()
			
			originX+=boxW
