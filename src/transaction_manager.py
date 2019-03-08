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
		self.db = SerialDatabase() # instance of the serial database object
		self.fn = Functions()
		self.transactions = {} # ordered list of the uncommitted transactions
		self.command_text = {} # same key as transactions, but has the command text
		self.function_names = {
			"begin": self.begin,
			"commit": self.commit,
			"check_commit": self.check_commit, # asks the database whether the transaction could commit, user doesn't see this
			"abort": self.abort,
			#"check_book": self.check_book
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
			return 'begin usage: begin [command]'
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
			return 'Error: invalid command'

		self.i = self.i + 1
		tid = 't' + str(self.i)
		print('Transaction \'', tid, '\' started.')
		t = self.db.begin(self.fn.run(args))
		self.transactions[tid] = t
		self.command_text[tid] = 'begin ' + self.reduce_list_to_string(args)
		return t.read_phase() + ' transaction number: {}'.format(tid) #writing to local cache

	# arg = string transaction_id
	def commit(self,arg):
		if len(arg) != 1:
			return 'commit usage: commit [transaction_id]'
		if arg[0] in self.transactions:
			#self.transactions[arg[0]].read_phase()
			status = self.transactions[arg[0]].validate_and_write_phase(True)
			if status:
				self.transactions.pop(arg[0])
				return 'Transaction {} successfully comitted'.format(arg[0])
			else:
				self.transactions.pop(arg[0])
				return 'Conflict: unable to commit {}, aborting instead.'.format(arg[0])
		else:
			return 'Error: invalid transaction ID'
			
	# arg = string transaction_id
	def check_commit(self,arg):
		if len(arg) != 1:
			return 'commit usage: commit [transaction_id]'
		if arg[0] in self.transactions:
			#self.transactions[arg[0]].read_phase()
			status = self.transactions[arg[0]].validate_and_write_phase(False)
			if status:
				return True
			else:
				return False
		else:
			return False

	# arg = string transaction_id
	def abort(self, arg):
		if len(arg) != 1:
			return 'abort usage: abort [transaction_id]'
		if arg[0] in self.transactions:
			self.transactions.pop(arg[0])
			return 'Transaction {} aborted'.format(arg[0])
		else:
			return 'Error: invalid transaction ID'
	
	# helper function: takes as input a list of strings and returns a concatenated string with spaces between each element
	def reduce_list_to_string(self, list):
		return_string = list[0]
		for string in list[1:]:
			return_string += (' ' + string)
		
		return return_string
	