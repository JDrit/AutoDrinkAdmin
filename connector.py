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
import ConfigParser
import wx
import time
import ldap
import socket
import MySQLdb

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
	print errorMessage, e
	if not e == None:
		f.write("\t" + str(e) + "\n")
	f.close()

class PyLDAP():
	"""
	The class that connects to the CSH LDAP server to search / modify user's drink
		credits
	"""

	def __init__(self, configFileName):
		"""
		Sets up a connection to the LDAP server
		"""
		self.configFile = configFileName
		config = ConfigParser.ConfigParser()
		config.read(self.configFile)
		self.host = config.get("LDAP", "host")
		self.bind_dn = config.get("LDAP", "bind_dn")
		self.user_dn = config.get("LDAP", "user_dn")
		self.password = config.get("LDAP", "password")
		self.creditsField = 'drinkBalance' # the field that stores users' drink credits

		try:
			if not config.get("LDAP", "cert") == "": # if there is a cert to use
				#ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_DEMAND)
				#ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, config.get("LDAP", "cert"))
				pass
			self.conn = ldap.initialize(self.host)
			self.conn.simple_bind_s(self.bind_dn, self.password)
		except ldap.LDAPError, e:
			logging("Error: could not bind to the host: " + self.host + " with bind: " + self.bind_dn, e)

	def search(self, uid):
		"""
		Searches through LDAP to get the data for the given user id
		Parameters:
			uid: the user ID to look for
		Returns:
			the data stored in LDAP for the given user, None if there
			is an error searching LDAP
		"""
		search_scope = ldap.SCOPE_SUBTREE
		search_filter = "uid=" + str(uid)
		result_set = []

		try:
			ldap_result_id = self.conn.search(self.user_dn, search_scope, search_filter, None)
			while True:
				result_type, result_data = self.conn.result(ldap_result_id, 0)
				if result_data == []:
					break
				else:
					if result_type == ldap.RES_SEARCH_ENTRY:
						result_set.append(result_data)
			if result_set == []:
				logging("Error: " + str(uid) + " does not exist in the LDAP server")
				return
			logging("Info: successful search for " + str(uid))
			return result_set[0][0]
		except ldap.LDAPError, e:
			logging("Error: LDAP error while searching for " + str(uid), e)
		except Exception, e:
			logging("Error: unkown error while searching for " + str(uid), e)


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
			if not data:
				logging("Error: no LDAP data for " + str(uid))
				return
			amount = int(data[self.creditsField][0])
			drinkAdmin = (int(data['drinkAdmin'][0]) == 1)
			logging("Info: Successful fetch of " + str(uid) + "'s drink credits: " + str(amount) + " and drink admin status")
			return amount, drinkAdmin
		except ldap.LDAPError, e:
			logging("Error: LDAP error while trying to get " + str(uid) + "'s information", e)
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
		Returns:
			the new amount of drink credits for the person if the change was successful,
				None if the change failed
		"""
		try:
			data = self.getUsersInformation(uid)
			if not data:
				logging("Error: could not increment " + str(uid) + "'s drink credits since could not get LDAP data for user")
				return
			old_amount = int(data[0])
			new_amount = old_amount + amount
			mod_attrs = [(ldap.MOD_REPLACE, self.creditsField, str(new_amount))]
			self.conn.modify_s("uid=" + uid + "," + self.user_dn, mod_attrs)
			enterSQLLog(uid, amount, self.configFile)
			logging("Info: Successful increment of " + uid  + "'s drink credits from " + str(old_amount) + " to " + str(new_amount))
			return new_amount
		except ldap.INSUFFICIENT_ACCESS, e:
			logging("Error: Insufficient access to increments the drink credits for " + str(uid) + " by " + str(amount) ,e)
		except ldap.LDAPError, e:
			logging("Error: LDAP error while trying to increment " + str(uid) + "'s by " + str(amount), e)
		except Exception, e:
			logging("Error: could not increment by " + str(amount) + " for uid: " + str(uid), e)

	def setUsersCredits(self, uid, amount):
		"""
		Sets the user's drink credits to a given amount
		Parameters:
			uid: the user ID for the person to have their drink balance changed
			amount: the amount of drink credits to set the person's balance to
		Returns:
			the new amount of drink credits for the user if the LDAP change was successful,
				None if the change failed
		"""
		try:
			mod_attrs = [(ldap.MOD_REPLACE, self.creditsField, str(amount))]
			self.conn.modify_s("uid=" + uid + "," + self.user_dn, mod_attrs)
			logging("Info: Successful set of " + str(uid) + "'s drink credits to " + str(amount))
			return amount
		except ldap.INSUFFICIENT_ACCESS, e:
			logging("Error: Insufficient access to set the " + str(uid) + "'s drink credits to " + str(amount), e)
		except ldap.NO_SUCH_OBJECT, e:
			logging("Error: the user " + str(uid) + " does not exist in LDAP", e)
		except ldap.LDAPError, e:
			logging("Error: LDAP error while trying to set " + str(uid) + "'s drink credits to " + str(amount), e)
		except Exception, e:
			Logging("Error: could not set " + str(uid) + "'s drink credits to " + str(amount), e)

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
	# the configs used to connect to Russ's script
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

def enterSQLLog(user, amount, configFile):
	"""
	Enters the log into the log database table for the drink data
	Parameters:
		user: the username of the person who entered money
		amount: the amount added to the account
	"""
	print user, amount, configFile
	try:
		config = ConfigParser.ConfigParser()
		config.read(configFile)
		conn = MySQLdb.connect(config.get("SQL", "host"),
                config.get("SQL", "username"),
                config.get("SQL", "password"),
                config.get("SQL", "database"))
		cur = conn.cursor()
		sql = "INSERT INTO " + config.get("SQL", "table") + \
			"(username, admin, amount, direction, reason) \
			VALUES ('%s', '%s', '%d', '%s', '%s')" % \
			(user, config.get("SQL", "adminName"), amount, 'in', 'add_money')
		cur.execute(sql)
		conn.commit()
		cur.close()
		conn.close()
	except MySQLdb.Error, e:
		logging("Error: could not log to database", e)
	except Exception, e:
		logging("Error: could not write to database", e)
