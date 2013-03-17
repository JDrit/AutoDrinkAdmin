"""
Description:
	The main program to run for the Auto Drink Admin server. This starts up the GUI
	and then calls the background thread used to communciate with the arduino
	and LDAP. This shows the user their name and credits and displays a log
	that gives messages when the user is authenticated and adds money.
Author: 
	JD <jd@csh.rit.edu>
"""
import wx
from wx.lib.pubsub import Publisher
import readerThread

class GUI(wx.Frame):
	
	def __init__(self):
		wx.Frame.__init__(self, 
			None, 
			wx.ID_ANY, 
			"Auto Drink Admin"
		)
		panel = wx.Panel(self, wx.ID_ANY)
		self.ShowFullScreen(True) # sets the gui to full screeen
		sizer = wx.BoxSizer(wx.VERTICAL)
		title_font = wx.Font(44, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
		reg_font = wx.Font(22, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
		
		title_bar = wx.BoxSizer(wx.HORIZONTAL)
		jpg = wx.Image('csh_logo.jpg', wx.BITMAP_TYPE_JPEG).ConvertToBitmap()

		title_bar.Add(wx.StaticBitmap(panel, -1, jpg), 0, wx.ALIGN_LEFT|wx.ALL, 10)
		title_text = wx.StaticText(panel, -1, "Auto Drink Admin")
		title_text.SetFont(title_font)
		title_bar.Add(title_text, 2, wx.ALIGN_CENTER, 0)
		title_bar.Add(wx.StaticBitmap(panel, -1, jpg), 0, wx.ALIGN_RIGHT|wx.ALL, 10)

		sizer.Add(title_bar, 2, wx.EXPAND|wx.ALL, 20)
			
		self.user_text = wx.StaticText(panel, -1, "    User: ________",)
		self.user_text.SetFont(reg_font)
		sizer.Add(self.user_text, 0, wx.ALL, 20)

		self.credits_text = wx.StaticText(panel, -1, "Credits: ________")
		self.credits_text.SetFont(reg_font)
		sizer.Add(self.credits_text, 0, wx.ALL, 20)
		
		self.logout_but = wx.Button(panel, -1, "LOGOUT")
		self.logout_but.SetFont(reg_font)
		self.logout_but.Bind(wx.EVT_BUTTON, self.logoutButton)
		sizer.Add(self.logout_but, 1, wx.ALL|wx.EXPAND, 20)

		self.log_text = wx.StaticText(panel, -1, "Log:")
		self.log_text.SetFont(reg_font)
		sizer.Add(self.log_text, 10, wx.ALL, 20)

		panel.SetSizerAndFit(sizer)

		# sets up the listeners to listen for the messages from the background thread
		Publisher().subscribe(self.appendLog, "appendLog")
		Publisher().subscribe(self.updateLogout, "updateLogout")
		Publisher().subscribe(self.newUser, "updateNewUser")
		Publisher().subscribe(self.moneyAdded, "updateMoneyAdded")
		self.bgThread = readerThread.CommThread()

	def logoutButton(self, event):
		"""
		Used when the logout button is pressed. This talks to the background thread
			owned by the GUI.
		"""
		self.bgThread.logoutButton()

	def appendLog(self, message):
		"""
		Used to append a log message to the log when the background thread gets
			an update.
		Parameters:
			message: the message to add to the log
		"""
		self.log_text.SetLabel("Log:\n- " + message.data + self.log_text.GetLabel()[4:])
	
	def newUser(self, t):
		"""
		Used when the background thread gets a new user to log in. This is used to
			clear the screen and display the new user's information
		Parameters:
			t: the tuple of the new user's data, (user's id , user's credits)
		"""
		tup = t.data
		self.user_text.SetLabel("    User: " + tup[0])
		self.credits_text.SetLabel("Credits: " + str(tup[1]))
		self.log_text.SetLabel("Log:\n- " + tup[0] + " has successfully been logged in")
	
	def moneyAdded(self, t):
		"""
		Used when the background thread has added money to the user's account and
			wants to display it on the GUI.
		Parameters:
			t: the tuple of the data, (user's new credits , message log)
		"""
		tup = t.data
		self.credits_text.SetLabel("Credits: " + str(tup[0]))
		self.log_text.SetLabel("Log:\n- " + tup[1] + self.log_text.GetLabel()[4:])
			
	def updateLogout(self, n=None):
		"""
		Used when the background thread has logged the current user out and wants to
			wipe the screen of the user's information
		Parameters:
			n: nothing placeholder for the required parameter that needs to be passed
		"""
		self.credits_text.SetLabel("Credits: ________")
		self.user_text.SetLabel("    User: ________")
		self.log_text.SetLabel("Log:")

if __name__ == "__main__":
	app = wx.PySimpleApp()
	frame = GUI().Show()
	app.MainLoop()

