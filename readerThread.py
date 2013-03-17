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
			logging("Info: successful search for " + uid)
			return result_set[0][0]
		except ldap.LDAPError, e:
			logging("Error: could not search through the LDAP server", e)
		except IndexError, e:
			logging("Error: list index out of range for user data")
		except Exception, e:
			logging("Error: unkown error", e)


	def getUsersInformation(self, uid):
		"""
		Gets the user's drink credits and common name
		Parameters:
			uid: the user ID to get the drink credits for
		Returns:
			the number of drink credits for the user and the first common name of the
			user, or None if there is an
			error while searching
		"""
		try:
			data = self.search(uid)[1]
			amount = int(data['roomNumber'][0])
			name = data['cn'][0]
			logging("Info: Successful fetch of " + uid + "'s drink credits: " + str(amount))
			return amount, name
		except Exception, e:
			logging("Error: could not get drink credits for uid: " + uid, e)
	
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
			old_amount = int(data[0])
			name = data[1]
			new_amount = old_amount + amount
			dn = "uid=" + uid + ",dc=csh,dc=rit,dc=edu"
			mod_attrs = [(ldap.MOD_REPLACE, 'roomNumber', str(new_amount))]
			self.conn.modify_s(self.base_dn, mod_attrs)
			logging("Info: Successful modifying " + name  + "'s drink credits from " + str(old_amount) + " to " + str(new_amount))
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

class CommThread(Thread):
	"""
	The background thread used to communicate with the arduino and report changes
		to the GUI front end
	"""
	def __init__(self):
		Thread.__init__(self)
		self.start()
		self.once = False
		self.userId = ""

	def newUser(self, userId):
		"""
		Tells the gui a user's information when a new iButton is pressed. The  
			Publisher message has to be run in a seperate method so that
			it will be run in the main thread by the GUI thread.
		Parameters:
			userId: the username of the iButton pressed
		"""
		conn = PyLDAP()
		data = conn.getUsersInformation(userId)
		self.common_name = data[1]	
		conn.close()
		Publisher.sendMessage("updateNewUser", (data[1], data[0]))
	
	def appendLog(self, message):
		"""
		Adds log messages to the GUI. The Publisher messgage has to be run in a
			seperate method so that it will be run in the main thread by the
			GUI thread.
		Parameters:
			message: the log message to add to the gui
		"""
		Publisher.sendMessage("appendLog", message)
	
	def moneyAdded(self, amount, common_name, new_amount):
		"""
		Tells the GUI when money is added to the user's account. This has to be run in a
			seperate method so that it will be run in the main thread by the GUI.
		Parameter:
			amount: the amount of drink credits added
			uiserId: the user that the credits were added to
			new_amount: the new amount of credits that the user has
		"""
		Publisher.sendMessage("updateMoneyAdded", (new_amount, "Added " + str(amount) + " drink credits to " + common_name + "'s account"))
	
	def logoutButton(self):
		"""
		Called when the logout button is pressed
		"""
		logging("Info: " + self.userId + " pressed the logout button")
		wx.CallAfter(self.logUserOut)
			
	def logUserOut(self):
		"""
		Used to reset all the variables when a user logs out of Auto Drink Admin.
			This then calls the gui to wipe the screen of all the user's data. 
			This has to be in its own method so that it can be run by the main
			GUI thread.
		"""
		self.currentIButtonId = ""
		self.userId = ""
		self.common_name = ""
		#self.ser.write("l:")
		Publisher.sendMessage("updateLogout") 

	def run(self):
		"""
		Runs a loop, to read input from the arduino and communicates to the GUI to
			update the user's information
		"""
		self.currentIButtonId = ""
		self.common_name = ""
		addMoney = 0
		logoutTime = 3
		self.ser = None # setupSerial(logoutTime
		timeStamp = datetime.now()
		
		while True:
			data = raw_input("arduino input: ") # self.ser.read(9999)
			if len(data) > 0: # if there is input from the arduino
				timeStamp = datetime.now()
				if data.startswith('i:'): # iButton input
					if self.currentIButtonId == data[2:]: # log current user out
						logging("Info: Logging " + self.userId + " out due to iButton press")
						wx.CallAfter(self.logUserOut)
					else: # log in new user
						self.currentIButtonId = data[2:]
						self.userId = getUserId(self.currentIButtonId)
						if not self.userId: # invalid userId, stops user from entering money if it can not get UserId
							wx.CallAfter(self.logUserOut)
							wx.CallAfter(self.appendLog, "Could not authenticate user, please contact a drink admin")
						else: # new user has logged in
							wx.CallAfter(self.newUser, self.userId)
				elif data.startswith('m:'): # money input
					addMoney = int(data[2:])
					conn = PyLDAP()
					new_amount = conn.incUsersCredits(self.userId, addMoney)
					conn.close()
					if not new_amount == None: # good transcation
						wx.CallAfter(self.moneyAdded, addMoney, self.common_name, new_amount)
					else:
						wx.CallAfter(self.logUserOut)
						wx.CallAfter(self.appendLog, "Could not add money to account, place contact a Drink Admin")
				else: # invlaid input
					logging("Info: invalid input: " + str(data))
			
			elif (datetime.now() - timeStamp) > timedelta(minutes = logoutTime) and not self.userId == "":
				logging("Info: logging " + self.userId + " out due to timeout")
				wx.CallAfter(self.logUserOut)
			
			time.sleep(0.5)
