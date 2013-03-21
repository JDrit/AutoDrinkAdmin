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
import pyLDAP
import serial

class CommThread(Thread):
	"""
	The background thread used to communicate with the arduino and report changes
		to the GUI front end
	"""
	def __init__(self):
		Thread.__init__(self)
		self.start()
		self.once = False
		self.userId = None

	def newUser(self):
		"""
		Tells the gui a user's information when a new iButton is pressed. The  
			Publisher message has to be run in a seperate method so that
			it will be run in the main thread by the GUI thread.
		Parameters:
			userId: the username of the iButton pressed
		"""
		conn = pyLDAP.PyLDAP()
		data = conn.getUsersInformation(self.userId)
		if data[1] or self.userId == "jd":
			admin = True
		else:
			admin = False
		conn.close()
		Publisher.sendMessage("updateNewUser", (self.userId, data[0], admin))
	
	def appendLog(self, message):
		"""
		Adds log messages to the GUI. The Publisher messgage has to be run in a
			seperate method so that it will be run in the main thread by the
			GUI thread.
		Parameters:
			message: the log message to add to the gui
		"""
		Publisher.sendMessage("appendLog", message)
	
	def moneyAdded(self, amount, uid, new_amount):
		"""
		Tells the GUI when money is added to the user's account. This has to be run in a
			seperate method so that it will be run in the main thread by the GUI.
		Parameter:
			amount: the amount of drink credits added
			uiserId: the user that the credits were added to
			new_amount: the new amount of credits that the user has
		"""
		Publisher.sendMessage("updateMoneyAdded", (new_amount, "Added " + str(amount) + " drink credits to " + uid + "'s account"))
	
	def logoutButton(self):
		"""
		Called when the logout button is pressed
		"""
		pyLDAP.logging("Info: " + str(self.userId) + " pressed the logout button")
		wx.CallAfter(self.logUserOut)
	
	def openButton(self):
		if not self.moneyDoorOpen:
			pyLDAP.logging("Info: " + str(self.userId) + " opened the money door")
			self.ser("C")
		else:
			pyLDAP.logging("Info: " + str(self.userId) + " closed the money door")
			self.ser("O")
		self.moneyDoorOpen = not self.moneyDoorOpen
			
	def logUserOut(self):
		"""
		Used to reset all the variables when a user logs out of Auto Drink Admin.
			This then calls the gui to wipe the screen of all the user's data. 
			This has to be in its own method so that it can be run by the main
			GUI thread.
		"""
		self.currentIButtonId = None
		self.userId = None
		self.ser.write("l:")
		Publisher.sendMessage("updateLogout") 

	def run(self):
		"""
		Runs a loop, to read input from the arduino and communicates to the GUI to
			update the user's information
		"""
		self.currentIButtonId = None
		self.moneyDoorOpen = False
		userId = None
		addMoney = 0
		logoutTime = 1
		#self.ser = None
		
		self.ser = serial.Serial(
			port = '/dev/ttyACM0',
			baudrate = 9600,
			#parity = serial.PARITY_ODD,
			#stopbits = serial.STOPBITS_TWO,
			#bytesize = serial.SEVENBITS,
			timeout = 2 
		)
		if self.ser.isOpen():
			self.ser.close()
		
		self.ser.open()
		timeStamp = datetime.now()
		
		while True:
			data = self.ser.read(999)#raw_input("arduino input: ") # self.ser.read(9999)
			if len(data) > 0: # if there is input from the arduino
				if data.startswith('i:'): # iButton input
					if not data[2:].upper() == self.currentIButtonId:
						self.currentIButtonId = data[2:].upper()
						timeStamp = datetime.now()
						self.userId = pyLDAP.getUserId(self.currentIButtonId)
						if not self.userId:
							wx.CallAfter(self.logUserOut)
							wx.CallAfter(self.appendLog, "Could not authenticate user, please contact a drink admin")
						else:
							wx.CallAfter(self.newUser)
				elif data.startswith('m:'): # money input
					addMoney = int(data[2:])
					timeStamp = datetime.now()
					conn = pyLDAP.PyLDAP()
					new_amount = conn.incUsersCredits(userId, addMoney)
					conn.close()
					if not new_amount == None: # good transcation
						wx.CallAfter(self.moneyAdded, addMoney, userId, new_amount)
					else:
						wx.CallAfter(self.logUserOut)
						wx.CallAfter(self.appendLog, "Could not add money to account, place contact a Drink Admin")
				else: # invlaid input
					pyLDAP.logging("Info: invalid input: " + str(data))
			
			# the user has been inactive for too long
			if (datetime.now() - timeStamp) > timedelta(minutes = logoutTime) and self.userId:
				pyLDAP.logging("Info: logging " + str(userId) + " out due to timeout")
				if self.moneyDoorOpen:
					self.moneyDoorOpen = False
					pyLDAP.logging("Info: closing money door due to timeout")
					ser.write("C")
				wx.CallAfter(self.logUserOut)
			
			time.sleep(0.5)
