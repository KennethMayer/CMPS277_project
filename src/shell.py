import sys
from transaction_manager import transaction_manager

class shell:
	def __init__(self):
		self.tm = transaction_manager()

	def run(self):
		print('Welcome to the bookstore database shell.')
		print('For a list of commands you can run, type \'help\'.')
		command = ''
		while(True):
			command = sys.stdin.readline()
			command = command[:len(command)-1]
			if command == 'exit' or command == 'quit':
				self.exit_command()
			if command == 'help':
				self.help_command()
			else:
				print(self.tm.run(command))

	def exit_command(self):
		print('Bye!')
		exit();

	def help_command(self):
		print('List of command usages:')
		print('begin add_book [ISBN] [owner] [price]')
		print('begin check_book [ISBN]')
		print('begin buy_book [ISBN] [owner] [balance]')
		print('begin remove_book [ISBN] [caller]')
		print('commit [transaction_id]')
		print('abort [transaction_id]')
		print('quit')
		print('help')

def main():
	sh = shell()
	sh.run();

main()
