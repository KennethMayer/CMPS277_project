import sys
from transaction_manager import transaction_manager

class shell:
	def __init__(self):
		self.tm = transaction_manager()

	def run(self):
		print('Welcome to the bookstore database shell. For a list of commands you can run, type \'help\'.')
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
		print('buy_book [ISBN] [owner] [price]')
		print('check_book [ISBN]')
		print('buy_book [ISBN] [owner] [balance]')
		print('remove_book [ISBN] [caller]')
		print('quit')
		print('help')
		
def main():
	sh = shell()
	sh.run();
	
main()