#!/usr/bin/env python

"""
This is the code that runs on the Auto Drink Admin server to resd in from the 
	Arduino and binds to CSH LDAP to modify users' drink credits
Author: JD <jd@csh.rit.edu>
Date: March 13, 2013
"""
import serial
import ldap
import socket
import datetime
import time

def logging(errorMessage, e=None):
	timeStamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
	day = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d')
	f = open("logs/" + day + ".log", "a")

	f.write(timeStamp + ": " + errorMessage + "\n")
	if not e == None:
		f.write("\t" + str(e) + "\n")
	f.close()

class PyLDAP():
	"""
	The class that connects to the CSH LDAP server to search / modify user's drink
		credits
	"""
	
	def __init__(self):
		"""
		Sets up a connection to the LDAP server
		"""
		f = open("config")
		self.host = "ldap://ldap.csh.rit.edu"
		self.base_dn = "uid=" + f.readline()[:-1] + ",ou=Users,dc=csh,dc=rit,dc=edu"
		self.password = f.readline()[:-1]
		f.close()

		try:
			self.conn = ldap.initialize(self.host)
			self.conn.simple_bind_s(self.base_dn, self.password)
		except ldap.LDAPError, e:
			logging("Error: could not bind to the host: " + self.host + " with base: " + self.base_dn, e)
	
	def search(self, uid):
		"""
		Searches through LDAP to get the data for the given user id
		Parameters:
			uid: the user ID to look for
		Returns:
			the data stored in LDAP for the given user, None if there
			is an error searching LDAP
		"""
		search_dn = "dc=csh,dc=rit,dc=edu"
		search_scope = ldap.SCOPE_SUBTREE
		search_filter = "uid=" + uid
		result_set = []

		try:
			ldap_result_id = self.conn.search(search_dn, search_scope, search_filter, None)
			while True:
				result_type, result_data = self.conn.result(ldap_result_id, 0)
				if result_data == []:
					break
				else:
					if result_type == ldap.RES_SEARCH_ENTRY:
						result_set.append(result_data)
			return result_set[0][0]
		except ldap.LDAPError, e:
			logging("Error: could not search through the LDAP server", e)
		except IndexError, e:
			logging("Error: list index out of range for user data")
		except Exception, e:
			logging("Error: unkown error", e)


	def getUsersCredits(self, uid):
		"""
		Gets the user's drink credits
		Parameters:
			uid: the user ID to get the drink credits for
		Returns:
			the number of drink credits for the user, or None if there is an
			error while searching
		"""
		try:
			return int(self.search(uid)[1]['roomNumber'][0])
			return self.search(uid)[1]['drinkBalance'][0]
		except Exception, e:
			logging("Error: could not get drink credits for uid: " + uid, e)
	
	def incUsersCredits(self, uid, amount):
		"""
		Increments the user's drink credits by the given amount
		Parameters:
			uid: the user's ID to search for
			amount: the amount to increase the user's drink credits by
		"""
		try:
			new_amount = int(self.getUsersCredits(uid)) + amount
			dn = "uid=" + uid + ",dc=csh,dc=rit,dc=edu"
			mod_attrs = [(ldap.MOD_REPLACE, 'roomNumber', str(new_amount))]
			self.conn.modify_s(self.base_dn, mod_attrs)
			logging("Added " + amount + " to " + uid)
		except Exception, e:
			logging("Error: could not increment by " + str(amount) + " for uid: " + str(uid), e)
	def close():
		con.unbind()

def getUserId(iButtonId):
	"""
	Finds out the user's uid from their iButtonId by connecting to
		totoro and using Russ's iButton2uid script
	Parameters:
		iButtonId: the iButton id of the user to search for
	Returns:
		The uid of the user if they exist, else it returns None
	"""
	TCP_ADDRESS = "totoro.csh.rit.edu"
	TCP_PORT = 56123
	BUFFER_SIZE = 1024
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect((TCP_ADDRESS, TCP_PORT))
		s.send(iButtonId + '\n')
		data = s.recv(BUFFER_SIZE)
		logging("Got user " + data + " from iButton")
		return data	
	except socket.error, e:
		logging("Error: could not instantiate a sockey to " + TCP_ADDRESS + " and send and recieve user data", e)
	finally:
		s.close()


def setupSerial(loutoutTime):
	ser = serial.Serial(
		port = '/dev/ttyUSB1',
		baudrate = 9600,
		parity = serial.PARITY_ODD,
		stopbits = serial.STOPBITS_TWO,
		bytesize = serial.SEVENBITS,
		timeout=logoutTime
	)
	ser.open()
	return ser


def main():
	currentIButtonId = ""
	userId = ""
	addMoney = 0
	logouttime = 180 # logout time
	#ser = setupSerial(logoutTime)
	loggedIn = False
	

	while True:

		line = ser.readline():
		logging("input from arduino: " + line)
		if line.startswith('i:'): # iButton
			if currentIButtonId == line[2:]: # logout
				loggedIn = False
			else:
				loggedIn = True
				currentIButtonId = line[2:]
				userId = getUserId(currentIButtonId)
		elif line.startswith('m:'): # money
			addMoney = int(line[2:])
			conn = PyLDAP()
			conn.incUsersCredits(userId, addMoney)
			conn.close()
		else:
			logging("improper format of input from arduino: " + line)

		if not loggedIn:
			logging("logging user " + userId + " out")
			ser.write("l:") # tells the arduino to stop taking money from the user
	

	
if __name__ == "__main__":
	
	getUserId("")
	#con = PyLDAP()
	#print con.search("jd")
	#print con.getUsersCredits("jd")
	#con.incUsersCredits("jd", 4)
