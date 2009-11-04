# -*- coding: utf-8 -*-
def name():
	return "Data player plugin"
def description():
	return "Replays data previously gathered by gatherer plugin"
def version():
	return "Version 0.1"
def qgisMinimumVersion():
	return "1.0.0"
def classFactory(iface):
	from PlayerPlugin import PlayerPlugin
	return PlayerPlugin(iface)
