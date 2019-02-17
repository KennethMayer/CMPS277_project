# database skeleton to test shell and transaction manager layer.

class database:
	def __init__(self):
		self.datastore = {}
	
	def read(self, isbn):
		return [('krmayer', 18)] # hardcoded for tests
		
	def write(self, isbn, listings):
		return True
