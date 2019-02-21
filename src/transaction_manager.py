## transaction_manager.py
## Kenneth Mayer and Muhammad Saber
## Implements the transaction manager for our simple distributed bookstore system. This is responsible
## for accessing the database when prompted by commands from our user interface, the shell.

## NOTE: API listing is in the project documentation on google docs

from database import database

class transaction_manager:
	# initialize an empty database
	def __init__(self):
		self.database = database(); # instance of the database object
		self.transactions = []; # ordered list of the uncommitted transactions (not used at this moment)
		self.function_names = { ## POTENTIAL PROBLEM: may need to define the functions before putting them in the dictionary, not sure in the case of a class
			"add_book": self.add_book,
			"check_book": self.check_book,
			"buy_book": self.buy_book,
			"remove_book": self.remove_book,
			#"begin": self.begin, # implement later
			#"commit": self.commit, # implement later
			#"abort": self.abort # implement later
		}
		
	# run a command and return the result
	# @arg1: self
	# @arg2: a string that represents a shell command
	def run(self, command):
		tokens = command.split(' ')
		function = tokens[0]
		if function in self.function_names:
			return self.function_names[function](tokens[1:])
		return 'Error: invalid command'
	
	# for all API functions:
	# @arg1: self
	# @arg2: argument list for the function
	
	# args = string isbn, string owner, int price
	def add_book(self, args):
		if len(args) != 3:
			return 'add_book: usage: add_book [ISBN] [owner] [price]'
		try:
			int(args[2])
		except ValueError:
			return 'add_book price argument must be an integer'
		listings = self.database.read(args[0])
		try:
			price = int(args[2])
		except ValueError:
			return 'add_book: price argument must be an integer'
		if listings != False: # key already exists in the database
			listings.append((args[1], price))
		else:
			listings = [(args[1], price)]
		if self.database.write(args[0], listings) != False:
			return 'add_book: successfully added book {} under {}\'s name at price {}.'.format(args[0], args[1], args[2])
		else:
			return 'Couldn\'t write new value to database.'
	
	# args = string isbn
	def check_book(self, args):
		if len(args) != 1:
			return 'check_book usage: check_book [ISBN]'
		listings = self.database.read(args[0])
		if listings != False:
			return 'Found the following listings: {}'.format(listings)
		else:
			return 'Couldn\'t find any listings associated with that ISBN.'
	
	# args = string isbn, string owner, int balance
	def buy_book(self, args):
		if len(args) != 3:
			return 'buy_book: usage: buy_book [ISBN] [owner] [balance]'
		try:
			balance = int(args[2])
		except ValueError:
			return 'buy_book: balance argument must be an integer'
		listings = self.database.read(args[0])
		if listings != False:
			# now that we have the vector, we need to check if the specified owner is in it
			for pair in listings:
				if pair[0] == args[1]:
					if balance >= pair[1]:
						listings.remove(pair)
						if self.database.write(args[0], listings) != False:
							return 'Bought book {} from {} for {}.'.format(args[0], pair[0], pair[1])
						else:
							return 'Listing exists, but write operation failed.'
					else:
						return 'Book costs {}, but you only have {}.'.format(pair[1], balance)
			return 'Could not find a listing for book {} by owner {}.'.format(args[0], args[1])
		else:
			return 'Could not find any listing for book {}.'.format(args[0])
					
	# args = string isbn, string caller
	def remove_book(self, args):
		if len(args) != 2:
			return 'remove_book usage: remove_book [ISBN] [caller]'
		listings = self.database.read(args[0])
		if listings != False:
			# now that we have the vector , we need check if the person calling the function is in it
			for pair in listings:
				if pair[0] == args[1]:
					listings.remove(pair)
					if self.database.write(args[0], listings) != False:
						return 'Removed book {} owned by {} from listings.'.format(args[0], args[1])
					else:
						return 'You own the book, but write operation failed.'
			return 'Could not find a listing for book {} by owner {}.'.format(args[0], args[1])
		else:
			return 'Could not find any listing for book {}.'.format(args[0])
	