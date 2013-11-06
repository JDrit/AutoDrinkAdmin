"""
Description:
    The background process to communicate with the arduino, CSH LDAP,
    and the front end GUI. This includes the LDAP classes and the Thread
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
import connector
import serial
import ConfigParser

def heart_beat(self):
    """
    This function is used for the thread that talks to the arduino to tell
    the arduino when it should inhibit or not. This is done so that if power is
    cut and everything is rebooted, the readers will not start taking money intil
    the computer is ready to process the money.
    """
    while True:
        self.ser.write("h")
        time.sleep(1)


class CommThread(Thread):

    """
    The background thread used to communicate with the arduino and report changes
        to the GUI front end
    """
    def __init__(self, configFileName):
        self.once = False
        self.userId = None
        self.configFile = configFileName
        Thread.__init__(self)
        self.start()

    def newUser(self):
        """
        Tells the gui a user's information when a new iButton is pressed. The
            Publisher message has to be run in a seperate method so that
            it will be run in the main thread by the GUI thread.
        Parameters:
            userId: the username of the iButton pressed
        """
        try:
            conn = connector.PyLDAP(self.configFile)
            data = conn.getUsersInformation(self.userId)
            admin = (data[1])
            if data[1] or self.userId == "jd":
                admin = True
            else:
                admin = False
            conn.close()
            Publisher.sendMessage("updateNewUser", (self.userId, data[0], admin))
        except Exception, e:
            wx.CallAfter(self.appendLog, "Could not get user's information, please contact a drink admin")

    def appendLog(self, message):
        """
        Adds log messages to the GUI. The Publisher messgage has to be run in a
            seperate method so that it will be run in the main thread by the
            GUI thread.
        Parameters:
            message: the log message to add to the gui
        """
        Publisher.sendMessage("appendLog", message)

    def appendMoney(self, message):
        Publisher.sendMessage("appendMoney", message)

    def moneyAdded(self, amount, new_amount):
        """
        Tells the GUI when money is added to the user's account. This has to be run in a
            seperate method so that it will be run in the main thread by the GUI.
        Parameter:
            amount: the amount of drink credits added
            uiserId: the user that the credits were added to
            new_amount: the new amount of credits that the user has
        """
        Publisher.sendMessage("updateMoneyAdded", (new_amount, "Added " + str(amount) + " drink credits to " + self.userId + "'s account"))

    def logoutButton(self):
        """
        Called when the logout button is pressed
        """
        connector.logging("Info: " + str(self.userId) + " pressed the logout button")
        if not self.logging_out:
            self.logging_out_time = datetime.now() # the timer to measure the 2 second logout wait
            self.logging_out = True
        wx.CallAfter(self.appendLog, "Logging out...")
        #wx.CallAfter(self.logUserOut)

    def logUserOut(self):
        """
        Used to reset all the variables when a user logs out of Auto Drink Admin.
            This then calls the gui to wipe the screen of all the user's data.
            This has to be in its own method so that it can be run by the main
            GUI thread.
        """
        if (datetime.now() - self.last_money > timedelta(seconds = 2)):
            self.currentIButtonId = None
            self.logged_in = False
            self.ser.write("l")
            Publisher.sendMessage("updateLogout")
        else:
            wx.CallAfter(self.appendLog, "Could not log out yet, wait for money transfer to finish")

    def run(self):
        """
        Runs a loop, to read input from the arduino and communicates to the GUI to
            update the user's information
        """
        self.currentIButtonId = None
        self.logged_in = False
        config = ConfigParser.ConfigParser()
        config.read(self.configFile)
        moneyLogName = config.get("Logs", "moneyLog")

        logoutTime = config.getint("Daemon", "timeout")

        self.ser = serial.Serial(
            port = config.get("Daemon", "port"),
            baudrate = 9600,
            timeout = 0
        )
        if self.ser.isOpen():
            self.ser.close()

        self.ser.open()
        timeStamp = datetime.now()        # last time input from the arduino
        self.last_money = datetime.now()  # last time money was entered
        money_update = datetime.now()     # used to update the money log
        money_cache = 0                   # the amount of money cached on the machine
        self.logging_out_time = datetime.now() # the timer to measure the 2 second logout wait
        self.logging_out = False

        # starts the heart beat for the arduino
        heart_beat_thread = Thread(target=heart_beat, args = (self,))
        heart_beat_thread.start()

        while True:
            data = self.ser.readline(999)
            print data
            if len(data) > 1: # if there is input from the arduino
                timeStamp = datetime.now()
                self.logging_out = False # prevents the user from logging out when a input was recieved
                connector.logging("Input: input from arduino: " + data)
                if data.startswith('i:'): # iButton input
                    if (not data[2:-2].upper() == self.currentIButtonId and
                            datetime.now() - self.last_money > timedelta(seconds=2)): # if not currently logged in user
                        if not self.logged_in:
                            self.currentIButtonId = data[2:-2].upper()
                            self.userId = connector.getUserId(self.currentIButtonId)
                            if not self.userId:
                                wx.CallAfter(self.logUserOut)
                                wx.CallAfter(self.appendLog, "Could not authenticate user, please contact a drink admin")
                            else:
                                wx.CallAfter(self.newUser)
                                self.logged_in = True
                                self.ser.write("a")
                        else:
                            wx.CallAfter(self.appendLog, "You need to log out before a new user can log in")
                elif data.startswith('m:'): # money input
                    self.last_money = datetime.now()
                    if money_cache == 0:
                        money_update = datetime.now()
                    money_cache += int(data[2:])
                    if datetime.now() - money_update > timedelta(seconds = 2) and self.logged_in:
                        wx.CallAfter(self.appendMoney, "Counting: " + str(money_cache) + " credits")
                        money_update = datetime.now()
                else: # invalid input
                    connector.logging("Error: invalid input: " + str(data))

            if (datetime.now() - self.last_money > timedelta(seconds = 1)) and money_cache:
                conn = connector.PyLDAP(self.configFile)
                new_amount = conn.incUsersCredits(self.userId, money_cache)
                conn.close()
                try:
                    moneyInMachine = int(open(moneyLogName, "r").read())
                    open(moneyLogName, "w").write(str(moneyInMachine + money_cache))
                except Exception, e:
                    open(moneyLogName, "w").write(str(money_cache))
                if new_amount and self.logged_in: # good transcation
                    wx.CallAfter(self.moneyAdded, money_cache, new_amount)
                elif self.logged_in:
                    wx.CallAfter(self.appendLog, "Could not add money to account, place contact a Drink Admin")
                money_cache = 0

            # the user has been inactive for too long
            elif (datetime.now() - timeStamp) > timedelta(seconds = logoutTime) and self.logged_in:
                connector.logging("Info: logging " + str(self.userId) + " out due to timeout")
                wx.CallAfter(self.logUserOut)

            if self.logging_out and datetime.now() - self.logging_out_time > timedelta(seconds = 2):
                wx.CallAfter(self.logUserOut)




            time.sleep(0.5) # needed or else the inputs will not be read correctly

