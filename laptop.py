"""
This is the code that runs on the Auto Drink Admin server to resd in from the 
	Arduino and binds to CSH LDAP to modify users' drink credits
Author: Joseph Batchik <jd@csh.rit.edu>
Date: March 13, 2013
"""
import serial
import ldap

class PyLDAP():
"""
The class that connects to the CSH LDAP server to search / modify user's drink
	credits
"""
	
	def __init__(self):
		"""
		Sets up a connection to the LDAP server
		"""
		self.host = "ldap://ldap.csh.rit.edu"
		self.base_dn = "uid=,ou=Users,dc=csh,dc=rit,dc=edu"
		self.password = ""
		try:
			self.conn = ldap.initialize(self.host)
			self.conn.simple_bind_s(self.base_dn, self.password)
		except ldap.LDAPError, e:
			print e
	
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
			while 1:
				result_type, result_data = self.conn.result(ldap_result_id, 0)
				if result_data == []:
					break
				else:
					if result_type == ldap.RES_SEARCH_ENTRY:
						result_set.append(result_data)
			return result_set
		except ldap.LDAPError, e:
			print "Error: could not search through the LDAP server"
			print "\tError: " + str(e)


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
			return self.search(uid)[0][0][1]['drinkBalance'][0]
		except Exception, e:
			print "Error: could not get drink credits for uid: " + uid
			print "\tError: " + str(e)
	
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
			mod_attrs = [(ldap.MOD_REPLACE, 'drinkBalance', str(new_amount))]
			self.conn.modify_s(self.base_dn, mod_attrs)
			
		except Exception, e:
			print "Error: could not increment by " + str(amount) + " for uid: " + str(uid)
			print "\tError: " + str(e)
	

def setupSerial():
	ser = serial.Serial(
		port = '/dev/ttyUSB1',
		baudrate = 9600,
		parity = serial.PARITY_ODD,
		stopbits = serial.STOPBITS_TWO,
		bytesize = serial.SEVENBITS,
	)
	return ser

	
if __name__ == "__main__":

	con = PyLDAP()
	print con.search("")
	print con.getUsersCredits("")
	con.incUsersCredits("", 4)
