"""
Description:
	The background process to communicate with the arduino, CSH LDAP, 
	and the	front end GUI. This includes the LDAP classes and the Thread 
	that is run from the front end to deal with all the communication. 
	The thread takes input from the arduino to update LDAP and the GUI.
Author:
	JD <jd@csh.rit.edu>
"""

from threading import Thread
from wx.lib.pubsub import Publisher
from datetime import datetime, timedelta
import wx
import time
import ldap
import socket

def logging(errorMessage, e=None):
	"""
	Logs all messages to include both error messages and normal info messages.
		All logs are placed in logs/<date>.log so everyday has its own file
	Parameters:
		errorMessage: the message to report
		e: the stacktrack if aviable for the error message
	"""
	timeStamp = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
	day = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d')
	f = open("logs/" + day + ".log", "a")

	f.write(timeStamp + ": " + errorMessage + "\n")
	#print errorMessage
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
		self.host = "ldaps://ldap.csh.rit.edu:636"
		self.base_dn = "uid=" + f.readline()[:-1] + ",ou=Users,dc=csh,dc=rit,dc=edu"
		self.password = f.readline()[:-1]
		f.close()

		try:
			ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_DEMAND)
			ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, "ca-cert.crt")
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
		search_filter = "uid=" + str(uid)
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
			logging("Info: successful search for " + str(uid))
			return result_set[0][0]
		except ldap.LDAPError, e:
			logging("Error: could not search through the LDAP server", e)
		except IndexError, e:
			logging("Error: list index out of range for user data")
		except Exception, e:
			logging("Error: unkown error", e)
		

	def getUsersInformation(self, uid):
		"""
		Gets the user's drink credits and their drink admin status
		Parameters:
			uid: the user ID to get the drink credits for
		Returns:
			- amount of drink credits
			- the drink admin status
			or None if it errors out
		"""
		try:
			if not uid:
				logging("Error: User ID is None")
				return
			data = self.search(uid)[1]
			amount = int(data['roomNumber'][0])
			drinkAdmin = int(data['drinkAdmin'][0])
			if drinkAdmin == 1:
				drinkAdmin = True
			else:
				drinkAdmin = False
			logging("Info: Successful fetch of " + str(uid) + "'s drink credits: " + str(amount))
			return amount, drinkAdmin
		except Exception, e:
			logging("Error: could not get drink credits for uid: " + str(uid), e)
	
	def incUsersCredits(self, uid, amount):
		"""
		Increments the user's drink credits by the given amount. The users drink
			credits are refetched everytime so that if their balance increases 
			are decreases between the fetch and the increment, it does not
			cause any problems. This could be exploited by fetching the user's
			drink credits, buying a drink and then adding to their balance. This
			would make it so the drink did not cost the user anything.
		Parameters:
			uid: the user's ID to search for
			amount: the amount to increase the user's drink credits by
		"""
		try:
			data = self.getUsersInformation(uid)
			if not data:
				return
			old_amount = int(data[0])
			new_amount = old_amount + amount
			dn = "uid=" + uid + ",dc=csh,dc=rit,dc=edu"
			mod_attrs = [(ldap.MOD_REPLACE, 'roomNumber', str(new_amount))]
			self.conn.modify_s(self.base_dn, mod_attrs)
			logging("Info: Successful modifying " + uid  + "'s drink credits from " + str(old_amount) + " to " + str(new_amount))
			return new_amount
		
		except Exception, e:
			logging("Error: could not increment by " + str(amount) + " for uid: " + str(uid), e)
	def close(self):
		self.conn.unbind()

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
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	try:
		s.connect((TCP_ADDRESS, TCP_PORT))
		s.send(iButtonId + '\n')
		data = s.recv(BUFFER_SIZE).rstrip()
		logging("Info: Successful TCP request to " + TCP_ADDRESS + " to get user: " + data)
		return data
	except socket.error, e:
		logging("Error: could not instantiate a socket to " + TCP_ADDRESS + " and send and recieve user data", e)
	finally:
		s.close()
