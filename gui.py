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
			"Auto Drink Admin", 
			style = wx.FULLSCREEN_ALL, 
			size = wx.DisplaySize()
		)
		panel = wx.Panel(self, wx.ID_ANY)
		sizer = wx.BoxSizer(wx.VERTICAL)
		title_font = wx.Font(44, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
		reg_font = wx.Font(22, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
		
		title_text = wx.StaticText(panel, -1, "Auto Drink Admin")
		title_text.SetFont(title_font)
		sizer.Add(title_text, 2, wx.ALIGN_CENTER|wx.ALL, 20)
		
		self.user_text = wx.StaticText(panel, -1, "    User: ________",)
		self.user_text.SetFont(reg_font)
		sizer.Add(self.user_text, 1, wx.ALL, 20)

		self.credits_text = wx.StaticText(panel, -1, "Credits: ________")
		self.credits_text.SetFont(reg_font)
		sizer.Add(self.credits_text, 1, wx.ALL, 20)
		
		self.logout_but = wx.Button(panel, -1, "LOGOUT")
		self.logout_but.SetFont(reg_font)
		self.logout_but.Bind(wx.EVT_BUTTON, self.logoutButton)
		sizer.Add(self.logout_but, 2, wx.ALL|wx.EXPAND, 20)

		self.log_text = wx.StaticText(panel, -1, "Log:")
		self.log_text.SetFont(reg_font)
		sizer.Add(self.log_text, 6, wx.ALL, 20)

		panel.SetSizerAndFit(sizer)

		Publisher().subscribe(self.appendLog, "appendLog")
		Publisher().subscribe(self.updateLogout, "updateLogout")
		Publisher().subscribe(self.newUser, "updateNewUser")
		Publisher().subscribe(self.moneyAdded, "updateMoneyAdded")

		self.bgThread = readerThread.CommThread()

	def logoutButton(self, event):
		self.bgThread.logoutButton()

	def appendLog(self, message):
		self.log_text.SetLabel("Log:\n- " + message.data + self.log_text.GetLabel()[4:])
	
	def newUser(self, t):
		tup = t.data
		self.user_text.SetLabel("    User: " + tup[0])
		self.credits_text.SetLabel("Credits: " + str(tup[1]))
		self.log_text.SetLabel("Log:\n- " + tup[0] + " has successfully been logged in")
	
	def moneyAdded(self, t):
		tup = t.data
		self.credits_text.SetLabel("Credits: " + str(tup[0]))
		self.log_text.SetLabel("Log:\n- " + tup[1] + self.log_text.GetLabel()[4:])
			
	def updateLogout(self, n=None):
		self.credits_text.SetLabel("Credits: ________")
		self.user_text.SetLabel("    User: ________")
		self.log_text.SetLabel("Log:")

if __name__ == "__main__":
	app = wx.PySimpleApp()
	frame = GUI().Show()
	app.MainLoop()

