# -*- coding: utf-8 -*-
def name():
	return "Data gather plugin"
def description():
	return "Gathers data from GPS/camera/mic... and exports it for later use"
def version():
	return "Version 0.1"
def qgisMinimumVersion():
	return "1.0.0"
def classFactory(iface):
	from GatherPlugin import GatherPlugin
	return GatherPlugin(iface)
