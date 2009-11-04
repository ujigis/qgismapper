class Enumerate(object):
	def __init__(self, names_):
		self.names=names_.split()
		for number, name in enumerate(names_.split()):
			setattr(self, name, number)
