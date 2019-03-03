import sys
from transaction_manager import transaction_manager

class shell:
	def __init__(self):
		self.tm = transaction_manager()

	def run(self):
		print('Welcome to our Bookstore Database shell.')
		print('For a list of commands you can run, type \'help\'.')
		command = ''
		while(True):
			command = sys.stdin.readline()
			command = command[:len(command)-1]
			if command == 'exit' or command == 'quit':
				self.exit_command()
			elif command == 'help':
				self.help_command()
			elif command.split()[0] == 'executefile':
				if(len(command.split()) >= 2):
					self.file_command(command.split()[1])
				else:
					print('executefile: usage: executefile [filename]')
			else:
				print(self.tm.run(command))

	def exit_command(self):
		print('Bye!')
		exit();
	
	# args = string filename
	def file_command(self, filename):
		print('You wanted to execute the commands in filename: {}'.format(filename))
		f = open(filename);
		for line in f:
			print(self.tm.run(line))

	def help_command(self):
		print('List of command usages:')
		print('begin add_book [ISBN] [owner] [price]')
		print('begin buy_book [ISBN] [owner] [balance]')
		print('begin remove_book [ISBN] [caller]')
		print('check_book [ISBN]')
		print('commit [transaction_id]')
		print('abort [transaction_id]')
		print('executefile [filename]')
		print('quit')
		print('help')

def main():
	sh = shell()
	sh.run();

main()
