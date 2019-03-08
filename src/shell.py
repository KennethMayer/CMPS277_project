import sys
import socket as s

class shell:
	def __init__(self):
		return
		
	def run(self, host, port):
		print('host name: {}'.format(host))
		print('port number: {}'.format(port))
		
		print('Welcome to our Bookstore Database shell.')
		print('For a list of commands you can run, type \'help\'.')
		command = ''
		while True:
			self.socket = s.socket(s.AF_INET, s.SOCK_STREAM)
			self.socket.connect((host, port))
			command = sys.stdin.readline()
			command = command[:len(command)-1]
			if command == 'exit' or command == 'quit':
				self.exit_command()
			elif command == 'help':
				self.help_command()
			elif command.split()[0] == 'executefile':
				if(len(command.split()) >= 2):
					self.file_command(command.split()[1], mysocket)
				else:
					print('executefile: usage: executefile [filename]')
			else:
				self.socket.sendall(('client ' + command).encode())
				print(self.socket.recv(4096).decode('utf-8'))
				self.socket.close()
	
	def exit_command(self):
		print('Bye!')
		self.socket.close()
		exit()
	
	# args = string filename
	def file_command(self, filename, mysocket):
		print('You wanted to execute the commands in filename: {}'.format(filename))
		f = open(filename);
		for line in f:
			self.socket.sendall(('client ' + line).encode())
			print(self.socket.recv(4096).decode('utf-8'))
			self.socket.close()

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
	sh.run('localhost', int(sys.argv[1]));

main()
