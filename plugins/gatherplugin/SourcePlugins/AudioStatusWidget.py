# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import math

class AudioStatusWidget(QWidget):
	def __init__(self, parent=None):
		QWidget.__init__(self, parent)
		self.peak=0
	
	def setPeak(self, val):
		self.peak=math.sqrt(val)
		self.update()

	def paintEvent(self, e):
		r=e.rect()

		p=QPainter(self)
		p.setBrush(QBrush(Qt.black))
		p.setPen(QPen(Qt.NoPen))
		p.drawRect(r)

		p.setBrush(QBrush(Qt.red))
		r.setRight(r.width()*self.peak)
		
		r.setHeight(r.height()-4)
		r.moveTop(2)

		p.drawRect(r)
