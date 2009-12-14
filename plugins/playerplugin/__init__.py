# -*- coding: utf-8 -*-
def name():
	return "Data Player Plugin"
def description():
	return "QGIS Mapper - Replay tool"
def version():
	return "Version 0.3"
def qgisMinimumVersion():
	return "1.0.0"
def classFactory(iface):
	from PlayerPlugin import PlayerPlugin
	return PlayerPlugin(iface)
