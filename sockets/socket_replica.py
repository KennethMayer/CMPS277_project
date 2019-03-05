'''
The replica maintains up to 2n sockets. The first n sockets are server sockets through which other replicas can
communicate with it. The last n sockets are client sockets through which it communicates to the other replicas.
n=number of other replicas (in this case 3)
'''

import socket as s
import threading as t

class ReplicaCommunication:
	def __init__(self, hostport, portlist):
		self.host = ''
		self.hostport = hostport # hostport is the port is the port that the host listens on
		self.ports = portlist # portlist[0] is the port for the first other replica; array of size 3
		self.hsock0 = s.socket(s.AF_INET, s.SOCK_STREAM)
		self.hsock1 = s.socket(s.AF_INET, s.SOCK_STREAM)
		self.hsock2 = s.socket(s.AF_INET, s.SOCK_STREAM)
		
		self.hsock0.set_timeout(0) # 10 second timeout
		self.hsock1.set_timeout(0) # no timeout for testing purposes
		self.hsock2.set_timeout(0)
		
		self.hsock0.bind(self.host, self.hostport)
		self.hsock1.bind(self.host, self.hostport)
		self.hsock2.bind(self.host, self.hostport)
		
		self.pending_messages = [] # list of all the things that we've received, but that we haven't dealt with
	
	def listen_on_all(self):
		try:
			thread0 = t.thread(group=None, target=self.listen_func, name='thread0', args=('thread0', self.hsock0), kwargs={})
			thread1 = t.thread(group=None, target=self.listen_func, name='thread1', args=('thread1', self.hsock1), kwargs={})
			thread2 = t.thread(group=None, target=self.listen_func, name='thread2', args=('thread2', self.hsock2), kwargs={})
		except:
			print("listen_on_all: unable to start thread")
			return
		finally:
			thread0.run()
			thread1.run()
			thread2.run()
	
	def listen_func(self, threadname, sockfd):
		print("{} has started to listen.".format(threadname))
		sockfd.listen(1)
		(conn, address) = sockfd.accept()
		print('{} has connected to {}', addr, threadname)
		while(1): # while loop makes sure we receive all the data (if it was more than 4096 bytes)
			data = conn.recv(4096) # receive a buffer of size 4096
			if not data: break
			conn.sendall(data) # echo the data back
		conn.close
		
	def send_to_all(self, data):
		# create three client sockets
		csock0 = s.socket(s.AF_INET, s.SOCK_STREAM)
		csock1 = s.socket(s.AF_INET, s.SOCK_STREAM)
		csock2 = s.socket(s.AF_INET, s.SOCK_STREAM)
		
		csock0.set_timeout(0) # 10 second timeout
		csock1.set_timeout(0) # no timeout for testing purposes
		csock2.set_timeout(0)
		
		try:
			thread0 = t.thread(group=None, target=self.send_func, name='thread0', args=('thread0', self.csock0, 1, data), kwargs={})
			thread1 = t.thread(group=None, target=self.send_func, name='thread1', args=('thread1', self.csock1, 2, data), kwargs={})
			thread2 = t.thread(group=None, target=self.send_func, name='thread2', args=('thread2', self.csock2, 3, data), kwargs={})
		except:
			print("send_to_all: unable to start thread")
			return
		finally:
			thread0.run()
			thread1.run()
			thread2.run()
		
	def send_func(self, threadname, sockfd, portnum, data):
		print("{} has started to send.".format(threadname))
		sockfd.connect('localhost', self.portlist[portnum])
		sockfd.sendall(data.encode)
		while(1):
			data = sockfd.recv(4096)
			if not data: break
		sockfd.close