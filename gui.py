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
import argparse
import daemon
import ConfigParser
import os
import connector

class AdminPopup(wx.PopupWindow):
    """
    The popup dialog used to display the admin settings, such as open and close,
        amount of money in box, etc.
    """

    def __init__(self, parent, style, daemon, config_file):
        self.daemon = daemon
        wx.PopupWindow.__init__(self, parent, style)
        panel = self.panel = wx.Panel(self)
        title_font = wx.Font(40, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        reg_font = wx.Font(22, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)

        width, height = wx.DisplaySize()
        self.SetSize((width * .9, height * .9))
        wx.CallAfter(self.Refresh)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.admin_title = wx.StaticText(panel, -1, "Admin Panel", style=wx.ALIGN_CENTER)
        self.admin_title.SetFont(title_font)
        sizer.Add(self.admin_title, 1, wx.EXPAND|wx.ALL, 25)

        self.money_log = wx.StaticText(panel, -1,
                "$%s in machine" % '{0:.02f}'.format(
                    connector.money_in_machine() / 100))
        self.money_log.SetFont(reg_font)
        sizer.Add(self.money_log, 1, wx.EXPAND|wx.ALL, 25)

        self.reset_but = wx.Button(self.panel, -1, "RESET COUNTER")
        self.reset_but.SetFont(title_font)
        self.reset_but.Bind(wx.EVT_BUTTON, self.reset_button)
        sizer.Add(self.reset_but, 1, wx.EXPAND|wx.CENTER|wx.ALL, 20)

        self.close_but = wx.Button(self.panel, -1, "EXIT")
        self.close_but.SetFont(title_font)
        self.close_but.Bind(wx.EVT_BUTTON, self.close_button)
        sizer.Add(self.close_but, 1, wx.EXPAND|wx.ALL, 20)

        panel.SetSizerAndFit(sizer, wx.EXPAND)
        self.SetBestFittingSize()
        self.Center()

    def reset_button(self, event):
        """
        Used to reset the counter of how much money is in Auto Drink Admin
        """
        connector.reset_money_log()
        self.money_log.SetLabel("Money in Machine: $0.00")

    def close_button(self, event):
        self.Show(False)

class GUI(wx.Frame):
    """
    Main GUI for the UI
    """
    def __init__(self, config_file):
        wx.Frame.__init__(self,
            None,
            wx.ID_ANY,
            "Auto Drink Admin"
        )
        self.config_file = config_file
        self.panel = wx.Panel(self, wx.ID_ANY)
        self.ShowFullScreen(True) # sets the gui to full screeen
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        title_font = wx.Font(40, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_BOLD)
        reg_font = wx.Font(22, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_BOLD)
        log_font = wx.Font(18, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_BOLD)

        title_bar = wx.BoxSizer(wx.HORIZONTAL)
        jpg = wx.Image('csh_logo.jpg', wx.BITMAP_TYPE_JPEG).ConvertToBitmap()

        title_bar.Add(wx.StaticBitmap(self.panel, -1, jpg), 0,
                wx.ALIGN_LEFT|wx.ALL, 10)
        title_text = wx.StaticText(self.panel, -1, "Auto Drink Admin")
        title_text.SetFont(title_font)
        title_bar.Add(title_text, 1, wx.ALIGN_CENTER|wx.ALL, 10)
        title_bar.Add(wx.StaticBitmap(self.panel, -1, jpg), 0,
                wx.ALIGN_RIGHT|wx.ALL, 10)

        self.sizer.Add(title_bar, 2, wx.EXPAND|wx.ALL, 5)

        self.user_text = wx.StaticText(self.panel, -1, "    User: ________")
        self.user_text.SetFont(reg_font)
        self.sizer.Add(self.user_text, 0, wx.ALL, 10)

        self.credits_text = wx.StaticText(self.panel, -1, "Credits: ________")
        self.credits_text.SetFont(reg_font)
        self.sizer.Add(self.credits_text, 0, wx.ALL, 10)

        self.logout_but = wx.Button(self.panel, -1, "LOGOUT")
        self.logout_but.SetFont(title_font)
        self.logout_but.Bind(wx.EVT_BUTTON, self.logout_button)
        self.sizer.Add(self.logout_but, 1, wx.ALL|wx.EXPAND, 10)

        self.admin_but = wx.Button(self.panel, -1, "ADMIN")
        self.admin_but.SetFont(title_font)
        self.admin_but.Bind(wx.EVT_BUTTON, self.admin_button)
        self.sizer.Add(self.admin_but, 1, wx.ALL|wx.EXPAND, 10)

        self.log_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.log_text = wx.StaticText(self.panel, -1, "Log:")
        self.log_text.SetFont(log_font)
        self.log_sizer.Add(self.log_text, 90, wx.TOP|wx.LEFT, 20)

        self.money_text = wx.StaticText(self.panel, -1, "Money:")
        self.money_text.SetFont(log_font)
        self.log_sizer.Add(self.money_text, 10, wx.TOP, 20)

        self.sizer.Add(self.log_sizer, 10, wx.TOP|wx.LEFT, 20)

        self.panel.SetSizerAndFit(self.sizer)
        self.money_text.Layout()

        Publisher().subscribe(self.append_log, "appendLog")
        Publisher().subscribe(self.append_money, "appendMoney")
        Publisher().subscribe(self.update_logout, "updateLogout")
        Publisher().subscribe(self.new_user, "updateNewUser")
        Publisher().subscribe(self.money_added, "updateMoneyAdded")

        config = ConfigParser.ConfigParser()
        config.read(config_file)

        self.money_log_name = config.get('connector', 'moneyLog')
        self.api_key = config.get('connector', 'apiKey')



        connector.init(self.money_log_name, self.api_key)

        self.daemon = daemon.CommThread(config_file)

    def logout_button(self, event):
        """
        Used when the logout button is pressed. This talks to the background thread
            owned by the GUI.
        """
        self.daemon.logout_button()

    def admin_button(self, event):
        win = AdminPopup(self.GetTopLevelParent(), wx.SIMPLE_BORDER,
                self.daemon, self.config_file)
        btn = event.GetEventObject()
        pos = btn.ClientToScreen( (0,0) )
        sz =  btn.GetSize()
        win.Show(True)

    def append_log(self, message):
        """
        Used to append a log message to the log when the background thread gets
            an update.
        Parameters:
            message: the message to add to the log
        """
        self.log_text.SetLabel("Log:\n- " + message.data +
                self.log_text.GetLabel()[4:])

    def append_money(self, message):
        self.money_text.SetLabel("Money:\n- " + message.data +
                self.money_text.GetLabel()[6:])

    def new_user(self, t):
        """
        Used when the background thread gets a new user to log in. This is used to
            clear the screen and display the new user's information
        Parameters:
            t: the tuple of the new user's data, (user's id , user's credits)
        """
        tup = t.data
        self.user_text.SetLabel("    User: " + tup[0])
        self.credits_text.SetLabel("Credits: " + str(tup[1]))
        self.admin_but.Show(tup[2])
        self.logout_but.Show()
        self.log_text.SetLabel("Log:\n- " + tup[0] +
                " has successfully been logged in")

    def money_added(self, t):
        """
        Used when the background thread has added money to the user's account and
            wants to display it on the GUI.
        Parameters:
            t: the tuple of the data, (user's new credits , message log)
        """
        tup = t.data
        self.credits_text.SetLabel("Credits: " + str(tup[0]))
        self.log_text.SetLabel("Log:\n- " + tup[1] + self.log_text.GetLabel()[4:])
        self.money_text.SetLabel("Money:")

    def update_logout(self, n=None):
        """
        Used when the background thread has logged the current user
            out and wants to wipe the screen of the user's information
        Parameters:
            n: nothing placeholder for the required parameter that
                needs to be passed
        """
        self.credits_text.SetLabel("Credits: ________")
        self.user_text.SetLabel("    User: ________")
        self.log_text.SetLabel("Log:")
        self.money_text.SetLabel("Money:")
        self.admin_but.Hide()
        self.logout_but.Hide()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
            description = 'Start the Auto Drink Admin program')
    parser.add_argument('--config', type=str, help='The config file to use',
            default='config')
    args = parser.parse_args()
    app = wx.PySimpleApp()
    if not os.path.exists(args.config):
        print('Error: No Config File')
    else:
        frame = GUI(args.config).Show()
        app.MainLoop()

