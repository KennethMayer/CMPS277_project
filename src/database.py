# database skeleton to test shell and transaction manager layer.

class database:
	def __init__(self):
		self.datastore = {}
	
	def read(self, isbn):
		if isbn in self.datastore:
			if len(self.datastore[isbn]) == 0:
				return False
			return self.datastore[isbn]
		return False
			
	def write(self, isbn, listings):
		self.datastore[isbn] = listings;
		return True
