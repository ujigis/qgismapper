# -*- coding: utf-8 -*-
def name():
	return "Data Gather Plugin"
def description():
	return "QGIS Mapper - Capture tool"
def version():
	return "Version 0.3.1"
def qgisMinimumVersion():
	return "1.0.0"
def classFactory(iface):
	from GatherPlugin import GatherPlugin
	return GatherPlugin(iface)
