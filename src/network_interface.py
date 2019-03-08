'''
This is responsible for interfacing with both clients and with other replicas of the system to
coordinate the necessary network operations. It can call upon the transaction manager to execute a transaction
(either from an SMR request from another replica or a client), it can also perform the necessary steps to accomplish
a commit request (with pbft or 2pc protocol).
'''

import sys
from transaction_manager import transaction_manager
import socket as s
import threading as t

class network_interface:
	# the init function creates our initial socket
	def __init__(self, port, portlist, mode = 0):
		self.mode = mode # 0: 2pc mode, 1: pbft mode
		self.port = port
		self.portlist = portlist
		
		self.main_socket = s.socket(s.AF_INET, s.SOCK_STREAM)
		self.tm = transaction_manager()
		
		self.sem = t.Semaphore(1) # while a transaction or a commit request is in progress, we can't service anything else
		
		self.twopc_phase = 0 # state variable: 0 = waiting for commit request, 1 = waiting for verdict
		self.current_tid = '' # the tid of the transaction that we're voting on whether to commit or not
		self.current_decision = 1 # what have we decided for the current transaction (if we're the leader)
		
		self.pbft_phase = 0
		
		self.phase_messages = () # list of messages we've received from other replicas during the current phase, but that haven't been dealt with
		self.listen_for_connections(port)
		
	def listen_for_connections(self, port):
		self.main_socket.bind(('', port)) # '' is any host name
		print('port number: {}'.format(port))
		self.main_socket.listen(1)
		while True:
			print('Main loop')
			conn, addr = self.main_socket.accept()
			print('Accepted connection')
			newthread = t.Thread(group=None, name='thread0', target=self.receive_data, args=('thread0', conn), kwargs={})
			newthread.start()
		
	def receive_data(self, threadname, conn):
		print('receive_data: {} has started to receive.'.format(threadname))
		while True:
			print('entering loop')
			data = conn.recv(4096)
			if not data: break
			# we've received our buffer, now we need to parse it
			self.sem.acquire()
			data = data.decode('utf-8')
			split_data = data.split() # split it along spaces
			print(split_data[0])
			if split_data[0] == 'client': # the message begins with some identifier that tells us whether it came from a replica or client
				if self.twopc_phase == 0:
					data = data[6:] # 6 = length of "client" + 1
					data_copy = data.split()
					if data_copy[0] != 'commit' or len(self.portlist) == 1: # if we aren't committing (or if we only have one replica), just run the transaction
						return_data = self.tm.run(data)
						conn.sendall(return_data.encode())
					else: # otherwise, we need to do atomic commit
						self.current_tid = data_copy[1]
						can_commit = self.tm.run('check_commit ' + data_copy[1]) # data_copy[1] is tid
						if can_commit: # if we can commit, vote on the commission of txn
							# open sockets to all the other replicas
							for i in self.portlist:
								if i != self.port: # don't message ourselves
									newsocket = s.socket(s.AF_INET, s.SOCK_STREAM)
									newsocket.connect(('localhost', i))
									print(self.tm.command_text)
									newsocket.sendall(('replica ' + self.tm.command_text[data_copy[1]]).encode())
									response = newsocket.recv(4096).decode('utf-8').split()
									print('Line 75 response: {}'.format(response))
									if response[1] == '0':
										self.current_decision = 0
									newsocket.close()
							
							# we have the decision, now carry it out
							if self.current_decision == 1:
								print('Leader is committing')
								return_data = self.tm.run('commit ' + data_copy[1])
								conn.sendall(return_data.encode())
							else:
								print('Leader is not committing')
								return_data = 'Other replicas were not able to commit the transaction. ' + self.tm.run('abort ' + data_copy[1])
								conn.sendall(return_data.encode())
							
							# open the sockets again to send the decision
							for i in self.portlist:
								if i != self.port: # don't message ourselves
									newsocket = s.socket(s.AF_INET, s.SOCK_STREAM)
									newsocket.connect(('localhost', i))
									newsocket.sendall(('replica {}'.format(self.current_decision)).encode()) # send the decision. We don't care if they get it.
									newsocket.close()
							self.current_decision = 1
						else: # otherwise, just abort and don't tell the replicas
							return_data = self.tm.run('commit ' + data_copy[1]) # this will just abort
							conn.sendall(return_data.encode())
				else:
					return_data = 'Cannot process transaction. Commission in progress. Try again in a moment.'
					conn.sendall(return_data.encode())
			elif split_data[0] == 'replica': # request to commit the transaction it sent
				if self.mode == 0:
					data = data[8:] # 6 = length of "replica" + 1
					print('What command did we get: {}'.format(data))
					if self.twopc_phase == 0:
						return_data = self.tm.run(data)
						print('return_data: {}'.format(return_data))
						return_data = return_data.split()
						self.current_tid = return_data[len(return_data)-1]
						can_commit = self.tm.run('check_commit ' + self.current_tid)
						if can_commit:
							print('Can commit the replicated transaction')
							conn.sendall('replica 1'.encode())
							self.twopc_phase = 1
						else:
							print('Cannot commit the replicated transaction')
							conn.sendall('replica 0'.encode())
							self.twopc_phase = 1
					elif self.twopc_phase == 1:
						data = data.split()
						if len(data) != 1:
							print('2PC response error: commit vote is of wrong length')
						vote = int(data[len(data)-1])
						if vote == 1:
							self.tm.run('commit ' + self.current_tid)
						else:
							self.tm.run('abort ' + self.current_tid)
						self.current_tid = ''
						# no ack
						self.twopc_phase = 0
			else:
				conn.sendall('receive_data: Message identifier unknown.'.encode())
		conn.close()
		self.sem.release()
	
def main():
	#argv[1] = this port argv[2] = otherport0 argv[3] = otherport1...
	portlist = []
	for i in range(len(sys.argv)):
		if i == 1:
			port = int(sys.argv[i])
		elif i > 1:
			portlist.append(int(sys.argv[i]))
	print('Your port: {}'.format(port))
	print('Portlist: {}'.format(portlist))
	ni = network_interface(port, portlist)
	
main()