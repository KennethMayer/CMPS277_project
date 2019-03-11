from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15

import sys
import socket as s
import datetime as d
import time

class shell:
	def __init__(self, mode=0, private_key_file='0', name='client0', timed=0):
		self.mode = mode # 0 = 2pc, 1 = pbft
		self.name = name # 'client0'
		self.timed = timed
		if private_key_file is not '0':
			self.private_key = RSA.import_key(open(private_key_file).read())
			self.keylist = { # other public keys, read from a file
			'replica0': RSA.import_key(open('keyfiles/public1').read()),
			'replica1': RSA.import_key(open('keyfiles/public2').read()),
			'replica2': RSA.import_key(open('keyfiles/public3').read()),
			'replica3': RSA.import_key(open('keyfiles/public4').read()),
			'client0': RSA.import_key(open('keyfiles/public5').read()),
			}
			
		self.portlist = { # hardcoded
		'replica0': 50006,
		'client0': 50004,
		'replica2': 50002,
		'replica3': 50003,
		'replica1': 50001,
		'client1': 50005,
		}
		return
		
	def run(self, host, port):
		print('host name: {}'.format(host))
		print('port number: {}'.format(port))
		
		print('Welcome to our Bookstore Database shell.')
		print('For a list of commands you can run, type \'help\'.')
		command = ''
		while True:
			self.socket = s.socket(s.AF_INET, s.SOCK_STREAM)
			self.socket.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)
			self.socket.settimeout(10)
			self.socket.connect((host, port))
			command = sys.stdin.readline()
			command = command[:len(command)-1]
			if command == 'exit' or command == 'quit':
				self.exit_command()
			elif command == 'help':
				self.help_command()
			elif command.split()[0] == 'executefile':
				if(len(command.split()) >= 2):
					self.file_command(command.split()[1], port)
				else:
					print('executefile: usage: executefile [filename]')
			else:
				if self.mode == 0:
					if self.timed:
						start = time.time()
					self.socket.sendall(('client ' + command).encode())
				else:
					x = d.datetime.now()
					timestamp = time.mktime(x.timetuple()) # Unix time in seconds
					timestamp = int(timestamp)
					message = 'r {} {} {}'.format(self.name, timestamp, command).encode()
					# print(message)
					message_digest = SHA256.new(message)
					# print(message_digest.digest())
					message_digest = pkcs1_15.new(self.private_key).sign(message_digest)
					message = message_digest + b' ' + message
					print('Creating a socket to listen for responses from the other replicas')
					responsesocket = s.socket(s.AF_INET, s.SOCK_STREAM)
					responsesocket.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)
					responsesocket.bind(('', self.portlist['client0']))
					responsesocket.listen(1)
					responsesocket.settimeout(10)
					if self.timed:
						start = time.time()
					self.socket.sendall(message)
				response = self.socket.recv(4096)
				try:
					string_response = response.decode()
				except:
					string_response = response[129:].decode()
				print('Response from replica0: {}'.format(string_response))
				if self.mode == 1:
					for i in range(3):
						try:
							conn, addr = responsesocket.accept()
							response = conn.recv(4096)
							string_response = response[129:].decode()
							print('We got a response: {}'.format(string_response))
						except:
							print('One replica timed out.')
						else:
							conn.close()
					responsesocket.close()
				if self.timed:
					end = time.time()
					print('That request took {} seconds'.format(end-start))
				print('about to close socket')
				self.socket.close()

	def exit_command(self):
		print('Bye!')
		self.socket.close()
		exit()
	
	# args = string filename
	def file_command(self, filename, port):
		print('You wanted to execute the commands in filename: {}'.format(filename))
		f = open(filename);
		if self.timed:
			start = time.time()
		for line in f:
			command = line[:len(line)-1]
			if self.mode == 0:
				self.socket.sendall(('client ' + command).encode())
			else:
				x = d.datetime.now()
				timestamp = time.mktime(x.timetuple()) # Unix time in seconds
				timestamp = int(timestamp)
				message = 'r {} {} {}'.format(self.name, timestamp, command).encode()
				print('Executefile: {}'.format(message))
				# print(message)
				message_digest = SHA256.new(message)
				# print(message_digest.digest())
				message_digest = pkcs1_15.new(self.private_key).sign(message_digest)
				message = message_digest + b' ' + message
				print('Creating a socket to listen for responses from the other replicas')
				responsesocket = s.socket(s.AF_INET, s.SOCK_STREAM)
				responsesocket.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)
				responsesocket.bind(('', self.portlist['client0']))
				responsesocket.listen(1)
				responsesocket.settimeout(10)
				self.socket.sendall(message)
			response = self.socket.recv(4096)
			try:
				string_response = response.decode()
			except:
				string_response = response[129:].decode()
			print('Response from replica0: {}'.format(string_response))
			if self.mode == 1:
				for i in range(3):
					try:
						conn, addr = responsesocket.accept()
						response = conn.recv(4096)
						string_response = response[129:].decode()
						print('We got a response: {}'.format(string_response))
					except:
						print('One replica timed out.')
					else:
						conn.close()
				responsesocket.close()
			print('about to close socket')
			self.socket.close()
			self.socket = s.socket(s.AF_INET, s.SOCK_STREAM)
			self.socket.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)
			self.socket.settimeout(10)
			self.socket.connect(('localhost', port))
		if self.timed:
			end = time.time()
			print('The executefile operation took: {} seconds'.format(end-start))
		
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
	argc = len(sys.argv)
	if argc < 2:
		print('Usage: py shell.py [port] [mode] [private_key_file] [name] [timed]')
		return
	if argc > 2:
		mode = int(sys.argv[2])
		if argc > 3:
			private_key_file = sys.argv[3]
			if argc > 4:
				name = sys.argv[4]
				if argc > 5:
					timed = int(sys.argv[5])
					sh = shell(mode, private_key_file, name, timed)
				else:
					sh = shell(mode, private_key_file, name)
			else:
				sh = shell(mode, private_key_file)
		else:
			sh = shell(mode)
	else:
		sh = shell()
		
	sh.run('localhost', int(sys.argv[1]));

main()
