# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import math

class GpsStatusWidget(QWidget):
	def __init__(self, parent=None):
		QWidget.__init__(self, parent)
		self.state=0
	
	def setState(self, val):
		self.state=val
		self.update()

	def paintEvent(self, e):
		r=e.rect()

		p=QPainter(self)

		if self.state==0:
			p.setBrush(QBrush(Qt.red))
		elif self.state==1:
			p.setBrush(QBrush(Qt.yellow))
		elif self.state==2:
			p.setBrush(QBrush(Qt.green))

		r.setBottom(r.bottom()-1)
		r.setRight(r.right()-1)
		if r.width()<r.height():
			r.setHeight(r.width())
		else:
			r.setWidth(r.height())
			
		p.drawEllipse(r)
