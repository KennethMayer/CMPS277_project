## transaction_manager.py
## Kenneth Mayer and Muhammad Saber
## Implements the transaction manager for our simple distributed bookstore system. This is responsible
## for accessing the database when prompted by commands from our user interface, the shell.

## NOTE: API listing is in the project documentation on google docs

from database import CachingDatabaseWrapper, Transaction
from serial_database import SerialDatabase
from functions import Functions

class transaction_manager:
	# initialize an empty database
	def __init__(self):
		self.i = 0
		self.db = SerialDatabase(); # instance of the serial database object
		self.fn = Functions()
		self.transactions = {}; # ordered list of the uncommitted transactions
		self.function_names = {
			"begin": self.begin,
			"commit": self.commit,
			"abort": self.abort,
		}
		
	# run a command and return the result
	# @arg1: self
	# @arg2: a string that represents a shell command
	def run(self, command):
		tokens = command.split()
		function = tokens[0]
		if function in self.function_names:
			return self.function_names[function](tokens[1:])
		return 'Error: invalid command'
	
	# for all API functions:
	# @arg1: self
	# @arg2: argument list for the function
	
	# args = string command
	def begin(self,args):
		if len(args) == 0:
			return'begin usage: begin command'
		# command error checking
		if(args[0] == 'add_book'):
			if len(args) != 4:
				return 'add_book: usage: add_book [ISBN] [owner] [price]'
			try:
				price = int(args[3])
			except ValueError:
				return 'add_book price argument must be an integer'

		elif(args[0] == 'check_book'):
			if len(args) != 2:
				return 'check_book usage: check_book [ISBN]'

		elif(args[0] == 'buy_book'):
			if len(args) != 4:
				return 'buy_book: usage: buy_book [ISBN] [owner] [balance]'
			try:
				balance = int(args[3])
			except ValueError:
				return 'buy_book: balance argument must be an integer'

		elif(args[0] == 'remove_book'):
			if len(args) != 3:
				return 'remove_book usage: remove_book [ISBN] [caller]'

		else:
			return'Error: invalid command'

		self.i = self.i + 1
		tid = 't' + str(self.i)
		print('Transaction \'', tid, '\' started.')
		t = self.db.begin(self.fn.run(args))
		t.read_phase()	#writing to local cache
		self.transactions[tid] = t

	# arg = string transaction_id
	def commit(self,arg):
		if len(arg) != 1:
			print('commit usage: commit [transaction_id]')
		if arg[0] in self.transactions:
			status = self.transactions[arg[0]].validate_and_write_phase()
			if status:
				print('Transaction ', arg[0], ' successfully comitted')
				self.transactions.pop(arg[0])
			else:
				print('Error: unable to commit ', arg[0], ', aborting instead.')
				self.transactions.pop(arg[0])
		else:
			print('Error: invalid transaction ID')

	# arg = string transaction_id
	def abort(self, arg):
		if len(arg) != 1:
			print('abort usage: abort [transaction_id]')
		if arg[0] in self.transactions:
			self.transactions.pop(arg[0])
			print('Transaction', arg[0], ' aborted')
		else:
			print('Error: invalid transaction ID')

"""
        # args = string isbn
        def check_book(self, args):
                if len(args) != 1:
                        return 'check_book usage: check_book [ISBN]'
		else:
	                listings = self.db.read(args[0])
                        if listings != False:
				return 'Found the following listings: {}'.format(listings)
                        else:
                                return 'Couldn\'t find any listings associated with that ISBN.'
"""
