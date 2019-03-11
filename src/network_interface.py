'''
This is responsible for interfacing with both clients and with other replicas of the system to
coordinate the necessary network operations. It can call upon the transaction manager to execute a transaction
(either from an SMR request from another replica or a client), it can also perform the necessary steps to accomplish
a commit request (with pbft or 2pc protocol).
'''

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15

from transaction_manager import transaction_manager
import socket as s
import threading as t
import sys

'''
class that describes logged messages that we've received. The log is purged after every operation
'''
class log_entry:
	def __init__(self, digest, message_body,  message_type='', sender='', timestamp=0, client_request=b'', view_number=0, sequence_number=0, request_digest=b'', receiver = '', decision=0):
		self.digest = digest # this is the signed digest of the logged message. Every message has a signed digest
		self.message_body = message_body # this is the part of the message that is hashed and signed. Every message has a body.
		self.message_type = message_type # identifies the kind of message this was
		# 'r' = client request
		# 'e' = response to client
		# 'pp' = pre-prepare
		# 'p' = prepare
		# 'c' = commit
		self.sender = sender # applicable to messages received from clients, identifies the client
		self.timestamp = timestamp # the timestamp of the client request
		self.view_number = view_number # the view number that the message was sent in
		self.sequence_number=sequence_number # the sequence number that the message was sent in
		self.request_digest=request_digest # this is the digest of the client request (in a bytes object)
		self.receiver = receiver # the identifier of the replica that received the message
		self.client_request = client_request # the commit operation that the client wanted performed
		self.decision = decision
	
	def print_self(self):
		pass
		#print('digest: {}'.format(self.digest))
		#print('message_type: {}'.format(self.message_type))
		#print('sender: {}'.format(self.sender))
		#print('timestamp: {}'.format(self.timestamp))
		#print('view number: {}'.format(self.view_number))
		#print('sequence number: {}'.format(self.sequence_number))
		#print('receiver: {}'.format(self.receiver))
		#print('client request: {}'.format(self.client_request))

class network_interface:
	# the init function creates our initial socket
	def __init__(self, name, replicated = 1, mode = 0, private_key_file=None, fail = 0):
		print('This network node\'s name: {}'.format(name))
		print('Is the network replicated: {}'.format(replicated))
		print('Which mode are we using: {}'.format(mode))
		self.mode = mode # 0: 2pc mode, 1: pbft mode
		self.name = name # might be 'replica0'
		self.replicated = replicated # are we replicating?
		self.fail = fail # used to simulate some failures
		if fail:
			print('SIMULATING A FAILED NODE')
		
		if private_key_file is not None:
			self.private_key = RSA.import_key(open(private_key_file).read())
			self.keylist = { # other public keys, read from a file
			'replica0': RSA.import_key(open('keyfiles/public1').read()),
			'replica1': RSA.import_key(open('keyfiles/public2').read()),
			'replica2': RSA.import_key(open('keyfiles/public3').read()),
			'replica3': RSA.import_key(open('keyfiles/public4').read()),
			'client0': RSA.import_key(open('keyfiles/public5').read()),
			}
		
		self.portlist = { # hardcoded
		'replica0': (50006, 50007), # the second is used in the commit phase
		'client0': 50004,
		'replica2': (50002, 50008),
		'replica3': (50003, 50009),
		'replica1': (50001, 50010),
		'client1': 50005,
		}
		
		self.main_socket = s.socket(s.AF_INET, s.SOCK_STREAM)
		self.main_socket.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)
		self.tm = transaction_manager()
		
		self.sem = t.Semaphore(1) # while a transaction or a commit request is in progress, we can't service anything else
		self.prepare_sem = t.Semaphore(1)
		
		self.twopc_phase = 0 # state variable: 0 = waiting for commit request, 1 = waiting for verdict
		self.current_tid = '' # the tid of the transaction that we're voting on whether to commit or not
		self.current_decision = 1 # what have we decided for the current transaction (if we're the leader)
		
		self.pbft_phase = 0 # 0 = waiting for pre-prepare, 1 = waiting for prepare, 2 = waiting for commit
		self.pbft_log = [] # list of messages we've accepted
		self.prepare_fail_count = 0
		self.commit_response_conn = [] # server connections over which we send commit messages
		self.prepare_response_conn = [] # client connections over which we receive commit messages
		self.last_reply = None # the last reply we sent to the client
		self.view_number = 0
		self.sequence_number = 0
		
		self.listen_for_connections(self.portlist[name][0])
		
	def listen_for_connections(self, port):
		self.main_socket.bind(('', port)) # '' is any host name
		print('port number: {}'.format(port))
		self.main_socket.listen(3)
		while True:
			self.main_socket.settimeout(None)
			print('Main loop')
			conn, addr = self.main_socket.accept()
			print('Accepted connection')
			if self.mode == 0: # 2pc can be done this way
				newthread = t.Thread(group=None, name='thread0', target=self.twopc_process_data, args=('thread0', conn), kwargs={})
				newthread.start()
			else: # start the pbft process in serial
				self.pbft_process_data('serial', conn)

	def pbft_process_data(self, threadname, conn):
		print('receive_data: {} has started to receive.'.format(threadname))
		try:
			data = conn.recv(4096)
			#print('This is the data we got from the client: {}'.format(data))
		except:
			conn.close()
			return
		# we've received our buffer, now we need to parse it
		self.sem.acquire()
		message = data[129:] # trim the digest and a space
		signature = data[:128]
		#print(signature)
		try: # if this is successful, it's a message from a client
			message = message.decode('utf-8')
			split_data = message.split() # split it along spaces
			sender_name = split_data[1]
		except UnicodeDecodeError: # if not, it's a pre-prepare from a leader
			sender_name = 'replica0' # hacky, but gets the job done; replica0 is always the leader
		#print('We received: {}'.format(sender_name))
		if sender_name.find('client') != -1: # the message has with some identifier that tells us whether it came from a replica or client
			if self.pbft_phase == 0:
				timestamp = int(split_data[2])
				client_key = self.keylist[sender_name] # gets the public key of the client that sent this
				# now we need to verify the message signature and check the resulting digest.
				digest = SHA256.new(message.encode()) # the client message
				# print(digest.digest())
				try:
					pkcs1_15.new(client_key).verify(digest, signature)
					#print('We verified the signature of a request message from {}'.format(sender_name))
				except (ValueError, TypeError):
					#print('We received a request message, but its signature was invalid')
					conn.sendall('The message you sent was corrupted. Please resend'.encode())
					conn.close
					self.sem.release()
					return
				start_tn = 128+1+len(split_data[0])+1 + len(split_data[1])+1 + len(split_data[2])+1
				requested_command = data[start_tn-1:].decode()
				#print('This is the command that we wanted to execute: {}'.format(requested_command))
				# first, we need to send the pre-prepare to all the other replicas, then wait for at least two valid responses
				timeout_count = 0
				prepare_count = 0
				message = 'pp {} {}'.format(self.view_number, self.sequence_number).encode()
				message = digest.digest() + b' ' + message
				##print('This is the message before we add the signed digest to it')
				##print(message)
				message_digest = SHA256.new(message) # create the message digest
				message_digest = pkcs1_15.new(self.private_key).sign(message_digest)
				##print(len(message_digest))
				# sign the digest
				message = message_digest + b' ' + message + b' ' + data # the final pre-prepare message
				self.pbft_log.append(self.generate_log_entry(message, 'pp')) # insert the pre-prepare into our log
				commit_socket = s.socket(s.AF_INET, s.SOCK_STREAM) # start listening on the port that the backups use to send the commit
				commit_socket.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)
				commit_socket.bind(('', self.portlist[self.name][1]))
				commit_socket.listen(3)
				for key in self.portlist:
					if key != self.name and key.find('replica') != -1: # don't message ourselves or a client
						newsocket = s.socket(s.AF_INET, s.SOCK_STREAM)
						newsocket.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)
						newsocket.settimeout(10)
						try:
							#print('trying to connect to replica: {}'.format(key))
							newsocket.connect(('localhost', self.portlist[key][0]))
						except:
							#print('We failed to connect to replica: {}'.format(key))
							timeout_count += 1
							continue
						newsocket.sendall(message)
						response = newsocket.recv(4096) # response is a prepare message
						response_content = response[129:] # trim the digest and a space
						##print('We received the following prepare message content: {}'.format(response_content))
						##print('This is the entire prepare message: {}'.format(response))
						response_signature = response[:128]
						request_digest = response[129:161]
						response_digest = SHA256.new(response_content) # compute the digest
						#print('We believe that the prepare message is from: {}'.format(key))
						replica_key = self.keylist[key]
						try:
							pkcs1_15.new(replica_key).verify(response_digest, response_signature)
							#print('We successfully verified a prepare message signature')
						except (ValueError, TypeError):
							timeout_count += 1 # increment the failure count
							#print('We received a prepare message, but its signature was incorrect')
						else:
							p_log_entry = self.generate_log_entry(response, 'p')
							pp_log_entry = self.return_log_entries('pp')
							assert len(pp_log_entry) == 1 # should only be one
							if self.verify_prepare_message(pp_log_entry[0], p_log_entry):
								self.pbft_log.append(p_log_entry)
								#print('Successfully added a prepare message to the log')
								prepare_count += 1
							else:
								print('Got a prepare message, but it was in the wrong view')
						newsocket.close()
				# now we have prepare messages from each backup
				if timeout_count <= 1:
					if prepare_count >= 3:
						# we can start the commit phase
						if requested_command.split()[0] == 'commit': # the request is for an actual commission, so check if we can commit
							can_commit = self.tm.run('check_commit ' + requested_command.split()[1]) # the second part is the tid
							if can_commit == True:
								can_commit = 1
							else:
								can_commit = 0
						else:
							can_commit = 1 # we aren't actually committing, so just vote that we can
						message = 'c {} {} {} {}'.format(self.view_number, self.sequence_number, self.name, can_commit).encode()
						message = digest.digest() + b' ' + message # digest is the digest of the original client request
						message = pkcs1_15.new(self.private_key).sign(SHA256.new(message)) + b' ' + message 
						for key in self.portlist:
							if key != self.name and key.find('replica') != -1: # don't message ourselves or a client
								newsocket = s.socket(s.AF_INET, s.SOCK_STREAM)
								newsocket.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)
								newsocket.settimeout(10)
								try:
									#print('Commit Phase: trying to connect to: {}'.format(key))
									newsocket.connect(('localhost', self.portlist[key][0]))
								except:
									#print('Commit Phase: {} timed out'.format(key))
									timeout_count += 1
									continue
								#print('Sending the following commit message: {}'.format(message))
								newsocket.sendall(message) # there is no response to this message
								newsocket.close()
						# now we need to open a server-side socket to each replica and see whether they committed
						commit_fail_count = 0
						commit_success_count = 0
						
						self.main_socket.listen(3)
						self.main_socket.settimeout(10)
						for i in range(3): # the number of other replicas
							#print('getting commit messages from other replicas')
							try:
								replicaconn, addr = commit_socket.accept()
								commit_message = replicaconn.recv(4096)
							except:
								#print('timed out when receiving commit responses from other replicas')
								commit_fail_count += 1
							else:
								replicaconn.close()
							commit_message_digest = commit_message[:128]
							request_message_digest = commit_message[129:161]
							commit_message_body = commit_message[162:]
							#print('The commit message had this body: {}'.format(commit_message_body))
							commit_message_body_split = commit_message[162:].decode().split()
							sender_name = commit_message_body_split[3]
							# now we need to verify the message's signed digest
							hash = SHA256.new(commit_message[129:])
							try:
								pkcs1_15.new(self.keylist[sender_name]).verify(hash, commit_message_digest)
								#print('We verified the signature of a commit message from {}'.format(sender_name))
							except (ValueError, TypeError):
								#print('We received a commit message from {} but its signature was incorrect'.format(sender_name))
								commit_fail_count+=1
							else:
								if int(commit_message_body_split[4]) == 1: # the replica wanted to commit
									commit_success_count += 1
								else:
									commit_fail_count += 1
						commit_socket.close()
						#print('Number of successful commit messages: {}'.format(commit_success_count))
						#print('Number of failed commit messages: {}'.format(commit_fail_count))
						if commit_fail_count <= 1: # successfully committed
							command_output = self.tm.run(requested_command)
							message = 'e {} {} {} {} Output: {}'.format('client0', timestamp, self.view_number, self.name, command_output).encode()
						else:
							message = 'e {} {} {} {} Output: {}'.format('client0', timestamp, self.view_number, self.name, 'There was an error. Cannot perform operation.').encode()
						self.sequence_number += 1
						if self.last_reply is not None: # this means we sent something to the client before; we check to see if its timestamp was higher
							if timestamp > self.last_reply.timestamp: # clear to reply
								# now we sign the message
								message_digest = pkcs1_15.new(self.private_key).sign(SHA256.new(message))
								message = message_digest + b' ' + message
								self.last_reply = self.generate_log_entry(message, 'e')
								conn.sendall(message) # send the final message
						else: # just send it
								message_digest = pkcs1_15.new(self.private_key).sign(SHA256.new(message))
								message = message_digest + b' ' + message
								self.last_reply = self.generate_log_entry(message, 'e')
								conn.sendall(message)
						self.pbft_log = []
					else:
						#print('Not enough prepare messages. We cannot commit')
						self.pbft_log = [] # remove all entries from the log
				else:
					#print('Too many backups timed out. We cannot commit.')
					self.pbft_log = [] # remove all entries from the log
			else:
				return_data = 'Cannot process transaction. Commission in progress. Try again in a moment.'
				conn.sendall(return_data.encode())
		elif sender_name.find('replica') != -1: # request to commit the transaction it sent
			if self.pbft_phase == 0:
				# first we need to verify the digest of the pp message
				client_message = self.return_client_message(data)
				client_message_start = data.find(client_message) # the client message is not part of the signed digest
				##print('This is what is about to be hashed and verified (pp): {}'.format(data[129:client_message_start]))
				signed_digest = SHA256.new(data[129:client_message_start-1])
				replica_key = self.keylist[sender_name]
				try:
					pkcs1_15.new(replica_key).verify(signed_digest, signature)
					#print('We verified the signature of a pre-prepare message from {}.'.format(sender_name))
				except (ValueError, TypeError):
					#print('We failed to verify the signature of a pre-prepare message from {}'.format(sender_name))
					conn.close()
					self.sem.release()
					return
				# next, we verify that the digest of the client request message is correct
				message_digest = data[129:161] # the message digest, d in the paper
				client_message_signature = client_message[:128]
				client_message_split = client_message[129:].decode().split()
				##print('This is the client message: {}'.format(client_message))
				##print('this is the split message: {}'.format(client_message_split))
				client_name = client_message_split[1]
				timestamp = int(client_message_split[2]) # use this later
				command_offset = 128+1+ len(client_message_split[0])+1 + len(client_message_split[1])+1 + len(client_message_split[2])+1
				requested_command = client_message[command_offset:].decode()
				client_message_digest = SHA256.new(client_message[129:])
				##print('For the prepare stage, this is the digest of piggybacked message: {}'.format(client_message[:128]))
				##print('This is the entire client message: {}'.format(client_message))
				client_key = self.keylist[client_name]
				try:
					pkcs1_15.new(client_key).verify(client_message_digest, client_message_signature)
					#print('We verified the signature of the piggybacked client message')
				except (ValueError, TypeError):
					#print('We failed to verify the signature of piggybacked client message')
					conn.close()
					self.sem.release()
					return
				# now we need to verify the digest d is for the message that was sent
				if message_digest == SHA256.new(client_message[129:]).digest():
					#print('The message digest matches the sent digest, d')
					pp_message = data[162:client_message_start].decode().split() # the pp message, other than the digest and the piggybacked message
					#print('This is the pre-prepare message alone: {}'.format(pp_message))
					if int(pp_message[1]) == self.view_number and int(pp_message[2]) == self.sequence_number:
						# we need to put the pre-prepare into our log
						log_entry = self.generate_log_entry(data, 'pp')
						self.pbft_log.append(log_entry)
						# finally, we can enter the prepare stage. We start by sending a prepare message to all other replicas
						prepare_message = 'p {} {} {}'.format(self.view_number, self.sequence_number, self.name).encode()
						prepare_message = message_digest + b' ' + prepare_message
						##print('About to send a prepare message. This is what is being signed: {}'.format(prepare_message))
						prepare_signed_digest = pkcs1_15.new(self.private_key).sign(SHA256.new(prepare_message))
						prepare_message = prepare_signed_digest + b' ' + prepare_message
						# first, send the message to the leader
						#print('Sending prepare message to the leader')
						conn.sendall(prepare_message)
						conn.close()
						# now send the message to each replica
						fail_count = 0
						commit_count = 0
						# in this stage, we start two threads to accept other prepare messages, while sending our prepare messages to the other backups
						self.prepare_sem.acquire()
						commitsocket = s.socket(s.AF_INET, s.SOCK_STREAM)
						commitsocket.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)
						commitsocket.bind(('', self.portlist[self.name][1])) # listen on our other port for commit messages
						commitsocket.listen(1)
						for key in self.portlist:
							if key != self.name and key.find('replica') != -1 and key != sender_name: # don't message ourselves or a client, and don't open a socket to the leader, we've already replied to it
								# we need to listen for connections from another client, then try to connect to another one
								newthread = t.Thread(group=None, name='thread0', target=self.receive_prepare, args=(commitsocket,), kwargs={})
								newthread.start()
								newsocket = s.socket(s.AF_INET, s.SOCK_STREAM) # client-side socket
								newsocket.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)
								newsocket.settimeout(10)
								try:
									#print('Prepare phase: trying to connect to port: {}'.format(self.portlist[key][1]))
									newsocket.connect(('localhost', self.portlist[key][1]))
								except:
									#print('Prepare phase: We failed to connect to port: {}'.format(self.portlist[key][1]))
									newsocket.close()
									fail_count += 1
									continue
								newsocket.sendall(prepare_message)
								self.prepare_response_conn.append(newsocket) # save these to get responses from them later
								self.prepare_sem.acquire()
						self.prepare_sem.release()
						commit_decision = 1
						if self.prepare_fail_count > 1: # we cannot commit for sure
							#print('More than one prepare message missing: cannot commit')
							commit_decision = 0
						else:
							# now we need to check the integrity of the messages we received
							prepare_entries = self.return_log_entries('p')
							for entry in prepare_entries:
								signed_digest = entry.digest
								request_digest = entry.request_digest
								message_body = entry.message_body
								sender = entry.receiver
								# verify the signature
								message_hash = SHA256.new(message_body)
								try:
									pkcs1_15.new(self.keylist[sender]).verify(message_hash, signed_digest)
									#print('Attempting to verify a prepare message signature')
								except (ValueError, TypeError):
									#print('Could not verify a prepare message signature')
									self.prepare_fail_count += 1
						# now we are in the commit phase
						if self.prepare_fail_count > 1 or commit_decision == 0:
							#print('We are voting not to commit because we did not get enough prepared messages')
							commit_decision = 0
						else:
							# we check if we want to commit it ourselves
							if(requested_command.split()[0] == 'commit'): # an actual commit message, so we have check if we can commit it first
								can_commit = self.tm.run('check_commit '+requested_command.split()[1]) # the second part is the tid
								if can_commit and self.fail==0:
									commit_decision = 1
								else:
									commit_decision = 0
							else:
								if self.fail:
									commit_decision = 0
								else:
									commit_decision = 1
						commit_message = 'c {} {} {} {}'.format(self.view_number, self.sequence_number, self.name, commit_decision).encode()
						commit_message = message_digest + b' ' + commit_message
						# sign the commit message
						commit_message_digest = pkcs1_15.new(self.private_key).sign(SHA256.new(commit_message))
						commit_message = commit_message_digest + b' ' + commit_message
						# we still have connections open to the other replicas that sent us the prepare message. We now send them our decision
						#print('We are responding to prepare messages over {} connections'.format(len(self.commit_response_conn)))
						assert len(self.commit_response_conn) <= 2
						no_votes = 0
						# now, we wait for responses from the ones we successfully sent prepare messages to (the threads we started above handle this on other replicas)
						#print('This is the number of connections that we can get commits from: {}'.format(len(self.prepare_response_conn)))
						self.prepare_sem.acquire()
						for socket, sendconn in zip(self.prepare_response_conn, self.commit_response_conn):
							newthread = t.Thread(group=None, name='thread0', target=self.send_commit, args=(commit_message, sendconn), kwargs={})
							newthread.start()
							commit_decision = socket.recv(4096) # these are received from the threads we started above on other replicas
							#print('received the commit decision')
							# check the signature and the vote
							##print('Entire commit message: {}'.format(commit_decision))
							commit_signature = commit_decision[:128]
							##print('Commit signature: {}'.format(commit_signature))
							message_digest = commit_decision[129:161]
							commit_message_body = commit_decision[129:]
							##print('Commit message body: {}'.format(commit_message_body))
							commit_message_split = commit_decision[161:].decode().split()
							#print('Commit message split: {}'.format(commit_message_split))
							replica_key = self.keylist[commit_message_split[3]]
							try:
								pkcs1_15.new(replica_key).verify(SHA256.new(commit_message_body), commit_signature)
								#print('We verified the signature of a commit message')
							except:
								#print('We failed to verify the signature of a commit message')
								no_votes += 1
							else:
								if int(commit_message_split[4]) != 1:
									no_votes += 1
							self.prepare_sem.acquire()
							socket.close()
							sendconn.close()
						self.prepare_sem.release()
						self.prepare_response_conn = []
						self.commit_response_conn = []
						# now we need to receive a commit message from the leader, which is the last commit message we need to receive. We assume that the leader cannot fail.
						self.main_socket.listen(3)
						conn, addr = self.main_socket.accept()
						leader_commit_msg = conn.recv(4096)
						message_digest = leader_commit_msg[:128] # signed digest of the commit message
						request_digest = leader_commit_msg[129:161] # unsigned digest of the original request m
						message_string = leader_commit_msg[162:].decode().split() # the rest of the commit message
						message_hash = SHA256.new(leader_commit_msg[129:])
						try:
							#print('Leader purported name: {}'.format(sender_name))
							pkcs1_15.new(self.keylist[sender_name]).verify(message_hash, message_digest)
						except (ValueError, TypeError):
							#print('We received a commit message from the leader, but its signature was incorrect')
							no_votes += 1
						conn.close()
						
						# finally, we send a commit message to the leader and to any replicas that didn't send us a prepare message (most likely they failed) (implement that later)
						#print('about to send commit message to leader')
						leadersocket = s.socket(s.AF_INET, s.SOCK_STREAM)
						leadersocket.connect(('localhost', self.portlist['replica0'][1]))
						#print('connected to leadersocket')
						leadersocket.sendall(commit_message)
						leadersocket.close()
						
						if no_votes <= 1: # we succeeded, perform and commit the operation, then open a client-side socket to the client and tell them (when they connect)
							command_output = self.tm.run(requested_command)
							message = 'e {} {} {} {} Output: {}'.format(client_name, timestamp, self.view_number, self.name, command_output).encode()
						else: # we failed, send a response indicating this:
							message = 'e {} {} {} {} Output: {}'.format(client_name, timestamp, self.view_number, self.name, 'There was an error. Cannot perform operation.').encode()
						self.sequence_number += 1
						if self.last_reply is not None:
							if timestamp > self.last_reply.timestamp:
								# now we sign the message
								message_digest = pkcs1_15.new(self.private_key).sign(SHA256.new(message))
								message = message_digest + b' ' + message
								self.last_reply = self.generate_log_entry(message, 'e')
								clientsocket = s.socket(s.AF_INET, s.SOCK_STREAM)
								clientsocket.settimeout(10)
								#try:
								clientsocket.connect(('localhost', self.portlist['client0']))
								clientsocket.sendall(message)
								#except:
								#	#print('Client did not get the response.')
								clientsocket.close()
							else:
								print('Cannot send the response, as there was a timestamp before')
						else: # just send it
							# now we sign the message
							message_digest = pkcs1_15.new(self.private_key).sign(SHA256.new(message))
							message = message_digest + b' ' + message
							self.last_reply = self.generate_log_entry(message, 'e')
							clientsocket = s.socket(s.AF_INET, s.SOCK_STREAM)
							clientsocket.settimeout(10)
							#try:
							clientsocket.connect(('localhost', self.portlist['client0']))
							clientsocket.sendall(message)
							#except:
							#	#print('Client did not get the response.')
							clientsocket.close()
					else:
						#print('We received a pre-prepare message, but the view or sequence number was wrong.')
						conn.close()
						self.sem.release()
						return
				else:
					#print('The digest for piggybacked message was incorrect')
					conn.close()
					self.sem.release()
					return
		else:
			conn.sendall('receive_data: Message identifier unknown.'.encode())
		conn.close()
		self.sem.release()
	
	# non-leader sockets use this to receive prepare messages. The leader gets them as a response through client-side sockets that it opens
	def receive_prepare(self, commitsocket):
		# accept on the main socket
		try:
			conn, addr = commitsocket.accept()
			conn.settimeout(10)
			prepare_message = conn.recv(4096)
		except:
			#print('receive_prepare thread timed out')
			self.prepare_fail_count += 1
		else:
			log_entry = self.generate_log_entry(prepare_message, 'p')
			self.commit_response_conn.append(conn) # up to two connections are in here
		# keep the connection open to send the commit response
		self.prepare_sem.release()
	
	# non-leader sockets use this to send commit messages as a response to server-side sockets that sent them a prepare message
	def send_commit(self, commit_message, conn):
		#print('send_commit: is the conn blocking? {}'.format(conn.getblocking()))
		#print('Here is what send_commit is sending: {}'.format(commit_message))
		try:
			conn.sendall(commit_message)
		except:
			print('send_commit thread timed out')
		else:
			conn.close()
		self.prepare_sem.release()
	
	# leader sockets use this to receive commit messages from the backups
	def receive_commit(self):
		try:
			#print('accepting new connections to send commits')
			conn, addr = self.main_socket.accept()
			conn.settimeout(10)
			commit_message = conn.recv(4096)
		except:
			#print('receive_commit thread timed out')
			self.commit_fail_count += 1
		else:
			conn.close()
			log_entry = self.generate_log_entry(commit_message, 'c')
			if log_entry.decision == 0: # if it is zero
				self.commit_fail_count += 1
			else:
				# check the signature of the message
				hash = SHA256.new(log_entry.message_body)
				try: 
					pkcs1_15.new(self.keylist[log_entry.receiver]).verify(log_entry.digest, hash)
					#print('We verified the signature of a commit message from a backup.')
				except (ValueError, TypeError):
					#print('We failed to verify the signature of a commit message from a backup')
					self.commit_fail_count += 1
				else:
					if log_entry.decision == 1:
						self.commit_success_count += 1
					else:
						self.commit_fail_count += 1
	
	def twopc_process_data(self, threadname, conn):
		print('receive_data: {} has started to receive.'.format(threadname))
		data = conn.recv(4096)
		if not data:
			conn.close()
			return
		# we've received our buffer, now we need to parse it
		self.sem.acquire()
		data = data.decode('utf-8')
		split_data = data.split() # split it along spaces
		#print('We received: {}'.format(split_data[0]))
		
		if split_data[0].find('client') != -1: # the message begins with some identifier that tells us whether it came from a replica or client
			if self.twopc_phase == 0:
				data = data[len(split_data[0])+1:] # 6 = length of "client" + 1
				data_copy = data.split()
				if data_copy[0] != 'commit' or self.replicated == 0: # if we aren't committing (or if we only have one replica), just run the transaction
					return_data = self.tm.run(data)
					conn.sendall(return_data.encode())
				else: # otherwise, we need to do atomic commit
					self.current_tid = data_copy[1]
					can_commit = self.tm.run('check_commit ' + data_copy[1]) # data_copy[1] is tid
					if can_commit: # if we can commit, vote on the commission of txn
						# open sockets to all the other replicas
						for key in self.portlist:
							if key != self.name and key.find('replica') != -1: # don't message ourselves or a client
								newsocket = s.socket(s.AF_INET, s.SOCK_STREAM)
								#print('trying to connect to port: {}'.format(self.portlist[key][0]))
								newsocket.connect(('localhost', self.portlist[key][0]))
								#print(self.tm.command_text)
								newsocket.sendall((self.name + ' ' + self.tm.command_text[data_copy[1]]).encode())
								response = newsocket.recv(4096).decode('utf-8').split()
								#print('response: {}'.format(response))
								if response[1] == '0':
									self.current_decision = 0
								newsocket.close()
						
						# we have the decision, now carry it out
						if self.current_decision == 1:
							#print('Leader is committing')
							return_data = self.tm.run('commit ' + data_copy[1])
							conn.sendall(return_data.encode())
						else:
							#print('Leader is not committing')
							return_data = 'Other replicas were not able to commit the transaction. ' + self.tm.run('abort ' + data_copy[1])
							conn.sendall(return_data.encode())
						
						# open the sockets again to send the decision
						for key in self.portlist:
							if key != self.name and key.find('replica') != -1: # don't message ourselves or a client
								newsocket = s.socket(s.AF_INET, s.SOCK_STREAM)
								newsocket.connect(('localhost', self.portlist[key][0]))
								newsocket.sendall((self.name + ' {}'.format(self.current_decision)).encode()) # send the decision. We don't care if they get it.
								newsocket.close()
						self.current_decision = 1
					else: # otherwise, just abort and don't tell the replicas
						return_data = self.tm.run('commit ' + data_copy[1]) # this will just abort
						conn.sendall(return_data.encode())
			else:
				return_data = 'Cannot process transaction. Commission in progress. Try again in a moment.'
				conn.sendall(return_data.encode())
		elif split_data[0].find('replica') != -1: # request to commit the transaction it sent
			data = data[len(split_data[0])+1:]
			#print('What command did we get: {}'.format(data))
			if self.twopc_phase == 0:
				return_data = self.tm.run(data)
				#print('return_data: {}'.format(return_data))
				return_data = return_data.split()
				self.current_tid = return_data[len(return_data)-1]
				can_commit = self.tm.run('check_commit ' + self.current_tid)
				if can_commit:
					#print('Can commit the replicated transaction')
					conn.sendall((self.name + ' 1').encode())
					self.twopc_phase = 1	  
					
				else:
					#print('Cannot commit the replicated transaction')
					conn.sendall((self.name + ' 0').encode())
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
		
	# takes a bytes message to be inserted into the log, formats it into a log entry and insterts it
	def generate_log_entry(self, log_message, message_type):
		if message_type == 'r':
			#print('adding request message to the log')
			digest = log_message[:128]
			message_body = log_message[129:]
			split_message = log_message[129:].decode().split()
			sender = split_message[1]
			timestamp = int(split_message[2])
			start = 32+1+len(message_type)+1+len(split_message[1])+1+len(split_message[2])+1
			client_request = log_message[start-1:]
			#print('We have the following client_request that is going to be added {}'.format(client_request))
			new = log_entry(digest=digest, message_body=message_body, message_type=message_type, sender=sender, timestamp=timestamp, client_request=client_request)
			new.print_self()
		elif message_type == 'e':
			#print('adding response message to the log')
			digest = log_message[:128]
			message_body = log_message[129:]
			split_message = log_message[129:].decode().split()
			sender = split_message[1]
			timestamp = int(split_message[2])
			view_number = int(split_message[3])
			receiver = split_message[4]
			new = log_entry(digest=digest, message_body=message_body, message_type=message_type, sender=sender, timestamp=timestamp, view_number=view_number, receiver=receiver)
			new.print_self()
		elif message_type == 'pp':
			#print('adding pre-prepare message to the log')
			digest = log_message[:128]
			client_request = self.return_client_message(log_message)
			message_body = log_message[162:log_message.find(client_request)]
			request_digest = log_message[129:161]
			client_request = self.return_client_message(log_message)
			#print(log_message)
			split_message = log_message[162:log_message.find(client_request)].decode().split()
			view_number = int(split_message[1])
			sequence_number = int(split_message[2])
			#print('We have the following client_request that is going to be added {}'.format(client_request))
			new = log_entry(digest = digest, message_body=message_body, message_type=message_type, request_digest=request_digest, view_number=view_number, sequence_number=sequence_number, client_request=client_request)
			new.print_self()
		elif message_type == 'p':
			#print('adding prepare message to the log')
			digest = log_message[:128]
			message_body = log_message[162:]
			request_digest = log_message[129:161]
			split_message = log_message[162:].decode().split()
			view_number = int(split_message[1])
			sequence_number = int(split_message[2])
			receiver = split_message[3]
			new = log_entry(digest=digest, message_body=message_body, message_type=message_type, request_digest=request_digest, view_number=view_number, sequence_number=sequence_number, receiver=receiver)
			new.print_self
		elif message_type == 'c':
			#print('adding commit message to log')
			digest = log_message[:128]
			message_body = log_message[162:]
			request_digest = log_message[129:161]
			split_message = log_message[162:].decode().split()
			#print('split commit message: {}'.format(split_message))
			view_number = int(split_message[1])
			sequence_number = int(split_message[2])
			receiver = split_message[3]
			decision = int(split_message[4])
			new = log_entry(digest=digest, message_body=message_body, message_type=message_type, request_digest=request_digest, view_number=view_number, decision=decision, receiver=receiver)
			new.print_self()
	
		return new

	# this function returns all log entries of the specified type. Remember that each time we commit or abort a transaction, the log is purged
	def return_log_entries(self, message_type):
		sublog = []
		for entry in self.pbft_log:
			if entry.message_type == message_type:
				sublog.append(entry)
		return sublog
	
	# to verify the prepare message, it has to have the same sequence number and digest as the pre-prepare
	def verify_prepare_message(self, pp_log_entry, p_log_entry):
		if pp_log_entry.sequence_number == p_log_entry.sequence_number and pp_log_entry.request_digest == p_log_entry.request_digest:
			return True
		return False
	
	# extract the original message from a pre-prepare message
	def return_client_message(self, message):
		# the client message is after space 2 and before the token ' pp '
		# FIXME: there's a problem if the client message includes the token ' pp '
		spaces_count = 0
		location = 0
		message_location = 0
		pp_location = message.find(b'pp')
		for c in message[pp_location:]:
			if c == 32:
				#print('found a space')
				spaces_count += 1
				if spaces_count == 3:
					message_location = pp_location+location+1
					break
			location += 1
		#print(message[message_location:])
		return message[message_location:]
	
def main():
	#argv[1] = name
	argc = len(sys.argv)
	if argc < 2:
		print('Usage: py network_interface.py [name] [replicated] [mode] [private_key_file] [fail]')
		return
	name = sys.argv[1] # name = replica[n]
	if argc > 2:
		replicated = int(sys.argv[2])
		if argc > 3:
			mode = int(sys.argv[3])
			if argc > 4:
				private_key_file = sys.argv[4]
				if argc > 5:
					fail = int(sys.argv[5])
					ni = network_interface(name, replicated, mode, private_key_file, fail)
				else:
					ni = network_interface(name, replicated, mode, private_key_file)
			else:
				ni = network_interface(name, replicated, mode)
		else:
			ni = network_interface(name, replicated)
	else:
		ni = network_interface(name)
	
main()