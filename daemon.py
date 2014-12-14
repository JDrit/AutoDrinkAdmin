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
import requests

def heart_beat(self):
    """
    Used for the thread that talks to the arduino to tell
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
    def __init__(self, config_file_name):
        self.user_id = None
        self.config_file = config_file_name
        Thread.__init__(self)
        self.start()

    def new_user(self):
        """
        Tells the gui a user's information when a new iButton is pressed. The
            Publisher message has to be run in a seperate method so that
            it will be run in the main thread by the GUI thread.
        """
        try:
            self.user_id, drink_credits, admin_status = connector.user_info(
                    self.current_ibutton)
            self.logged_in = True
            self.ser.write('a')
            Publisher.sendMessage('updateNewUser',
                    (self.user_id, drink_credits, admin_status))
        except Exception as e:
            connector.logging('Exception getting new user information', e = e)
            wx.CallAfter(self.append_log,
                "Could not get user's information, please contact a drink admin")

    def append_log(self, message):
        """
        Adds log messages to the GUI. The Publisher messgage has to be run in a
            seperate method so that it will be run in the main thread by the
            GUI thread.
        Parameters:
            message: the log message to add to the gui
        """
        Publisher.sendMessage("appendLog", message)

    def append_money(self, message):
        Publisher.sendMessage("appendMoney", message)

    def money_added(self, amount, new_amount):
        """
        Tells the GUI when money is added to the user's account.
            This has to be run in a seperate method so that it will
            be run in the main thread by the GUI.
        Parameter:
            amount: the amount of drink credits added
            user_id: the user that the credits were added to
            new_amount: the new amount of credits that the user has
        """
        Publisher.sendMessage("updateMoneyAdded",
                (new_amount, "Added %d drink credits to %s's account" % (amount, self.user_id)))

    def logout_button(self):
        """
        Called when the logout button is pressed
        """
        connector.logging("Info: %s pressed the logout button" % self.user_id)
        wx.CallAfter(self.log_user_out)

    def log_user_out(self):
        """
        Used to reset all the variables when a user logs out of Auto Drink Admin.
            This then calls the gui to wipe the screen of all the user's data.
            This has to be in its own method so that it can be run by the main
            GUI thread.
        """
        self.current_ibutton = None
        self.logged_in = False
        self.ser.write("l")
        Publisher.sendMessage("updateLogout")

    def run(self):
        """
        Runs a loop, to read input from the arduino and communicates
            to the GUI to update the user's information
        """
        self.current_ibutton = None
        self.logged_in = False
        config = ConfigParser.ConfigParser()
        config.read(self.config_file)
        logout_time = config.getint("daemon", "timeout")

        self.ser = serial.Serial(
            port = config.get("daemon", "port"),
            baudrate = 9600,
            timeout = 0
        )
        if self.ser.isOpen():
            self.ser.close()
        self.ser.open()

        last_money_time = datetime.now()  # last time money was entered
        money_cache = 0                   # the amount of money cached on the machine

        # starts the heart beat for the arduino
        heart_beat_thread = Thread(target=heart_beat, args = (self,))
        heart_beat_thread.start()

        while True:
            data = self.ser.readline(999).upper()
            if len(data) > 1: # if there is input from the arduino
                data_code = data[0]
                data_section = data[2:-2]

                connector.logging('Input: input from arduino: %s' % data)
                if data_code == 'I': # iButton input
                    # money is still be counted
                    if datetime.now() - last_money_time < timedelta(seconds = 3):
                        wx.CallAfter(self.append_log, "Please wait a second...")
                    if not self.logged_in:
                        self.current_ibutton = data_section
                        wx.CallAfter(self.new_user)
                    elif self.current_ibutton == data_section:
                        # current user signed in
                        pass
                    else:
                        wx.CallAfter(self.append_log, 'Log out first')
                elif data_code == 'M':
                    last_money_time = datetime.now()
                    money_cache += int(data_section)
                    connector.logging('money added %d' % money_cache)
                else:
                    connector.logging('Error: invalid input: %s' % data)

            if datetime.now() - last_money_time > timedelta(seconds = 2) and money_cache:
                connector.logging('money incr')
                new_credits = connector.increment_credits(
                        self.user_id, money_cache)
                wx.CallAfter(self.money_added, money_cache, new_credits)
                money_cache = 0

            elif (datetime.now() - last_money_time > timedelta(seconds = logout_time) and
                    self.logged_in):
                connector.logging('Info: logging %s out due to timeout' % self.user_id)
                wx.CallAfter(self.log_user_out)

            time.sleep(0.5) # needed or else the inputs will not be read correctly

