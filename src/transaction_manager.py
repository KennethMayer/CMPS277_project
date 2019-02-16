## transaction_manager.py
## Kenneth Mayer and Muhammad Saber
## Implements the transaction manager for our simple distributed bookstore system. This is responsible
## for accessing the database when prompted by commands from our user interface, the shell.

## NOTE: API listing is in the project documentation on google docs

from src import database

class transaction_manager:
	# initialize an empty database
	def __init__(self):
		self.database = database(); #instance of the database object
		self.transactions = []; #ordered list of the uncommitted transactions
		self.function_names = { ## POTENTIAL PROBLEM: may need to define the functions before putting them in the dictionary, not sure in the case of a class
			"add_book": add_book,
			"check_book": check_book,
			"buy_book": buy_book,
			"remove_book": remove_book,
			"begin": begin, # implement later
			"commit": commit, # implement later
			"abort": abort # implement later
		}
		
	# run a command and return the result
	# @arg1: self
	# @arg2: a string that represents a shell command
	def run(self, command):
		tokens = command.split(' ')
		function = tokens[0]
		if function in self.function_names:
			return self.function(tokens[1:])
		return 'Error: invalid command'
	
	# for all API functions:
	# @arg1: self
	# @arg2: argument list for the function
	
	# args = string isbn, string owner, int price
	def add_book(self, args):
		if len(args) != 3:
			return 'add_book: usage: add_book isbn owner price'
		try:
			int(args[2])
		except ValueError:
			return 'add_book: price argument must be an integer'
		if listings = database.read(args[0]) != False: # key already exists in the database
			listings.append((args[1], args[2]))
		else:
			listings = (args[1], args[2])
		if database.write(args[0], listings) != False:
			return 'add_book: successfully added book {} under {}\'s name at price {}.'.format(args[0], args[1], args[2])
		else:
			return 'Couldn\'t write new value to database.'
	
	# args = string isbn
	def check_book(self, args):
		if len(args) != 1
			return 'check_book: usage: check_book isbn'
		if listings = database.read(args[0]) != False:
			return 'Found the following listings: {}'.format(listings)
		else
			return 'Couldn\'t find any listings associated with that ISBN.'
	
	# args = string isbn, string owner, int balance
	def buy_book(self, args):
		if len(args) != 2
			return 'buy_book: usage: buy_book ISBN balance'
		try
			balance = int(args[2])
		except ValueError:
			return 'buy_book: balance argument must be an integer'
		if listings = database.read(args[0]) != False:
			# now that we have the vector, we need to check if the specified owner is in it
			for owner, price in enumerate(listings):
				if owner == args[1]:
					if balance >= price:
						listings.remove((owner, price))
						if database.write(args[0], listings) != False:
							return 'Bought book {} from {} for {}.'.format(args[0], owner, price)
						else:
							return 'Listing exists, but write operation failed.'
					else:
						return 'Book costs {}, but you only have {}.'.format(price, balance)
			return 'Could not find a listing for book {} by owner {}.'.format(args[0], args[1])
		else:
			return 'Could not find any listing for book {}.'.format(args[0])
					
	# args = string isbn, string caller
	def remove_book(self, args):
	