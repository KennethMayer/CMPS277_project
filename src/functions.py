## functions.py
## Kenneth Mayer and Muhammad Saber
## Implements the functions for accessing our simple distributed bookstore system.

## NOTE: API listing is in the project documentation on google docs

from database import CachingDatabaseWrapper, Transaction

class Functions:
	def __init__(self):
		self.function_names = {
			"add_book": self.add_book,
			"check_book": self.check_book,
			"buy_book": self.buy_book,
			"remove_book": self.remove_book
		}

	# run a command and return the result
	# @arg1: self
	# @arg2: a string that represents a shell command
	def run(self, command):
		#tokens = command.split()
		function = command[0]
		if function in self.function_names:
			return self.function_names[function](command[1:])
		return 'Error: invalid command'

	# for all API functions:
	# @arg1: self
	# @arg2: argument list for the function
	# args = string isbn
	def check_book(self, args):
		def txn(dab: CachingDatabaseWrapper):
			listings = dab.read(args[0])
			if listings != False:
				return 'check_book: Found the following listings: {}'.format(listings)
			else:
				return 'check_book: Couldn\'t find any listings associated with that ISBN.'
				
		return txn
	
	# args = string isbn, string owner, int price
	def add_book(self, args):
		def txn(dab: CachingDatabaseWrapper):
			listings = dab.read(args[0])
			if listings != False: # key already exists in the database
				price = int(args[2])
				listings.append((args[1], price))
				dab.write(args[0],listings)
				return 'add_book: successfully updated book {} under {}\'s name at price {}.'.format(args[0],args[1],args[2])
			else:
				price = int(args[2])
				listings = [(args[1], price)]
				dab.write(args[0], listings)
				return 'add_book: successfully added book {} under {}\'s name at price {}.'.format(args[0], args[1], args[2])

		return txn

	# args = string isbn, string owner, int balance
	def buy_book(self, args):
		def txn(dab: CachingDatabaseWrapper):
			found = False
			listings = dab.read(args[0])
			if listings != False:
				# now that we have the vector, we need to check if the specified owner is in it
				for pair in listings:
					if pair[0] == args[1]:
						balance = int(args[2])
						price = int(pair[1])
						found = True
						if balance >= price:
							listings.remove(pair)
							dab.write(args[0], listings)
							return 'Bought book {} from {} for {}.'.format(args[0], pair[0], pair[1])
							break
						else:
							return 'Book costs {}, but you only have {}.'.format(pair[1], balance)
							break
			if (not found):
				return 'Could not find any listing for book {}.'.format(args[0])

		return txn

	# args = string isbn, string caller
	def remove_book(self, args):
		def txn(dab: CachingDatabaseWrapper):
			listings = dab.read(args[0])
			if listings != False:
				found = False
				# now that we have the vector, we need to check if the person calling the function is in it
				for pair in listings:
					if pair[0] == args[1]:
						found = True
						listings.remove(pair)
						dab.write(args[0], listings)
						return 'Removed book {} owned by {} from listings.'.format(args[0], args[1])
						break
				if(not found):
					return 'Could not find a listing for book {} by owner {}.'.format(args[0], args[1])
			else:
				return 'Could not find any listing for book {}.'.format(args[0])

		return txn
