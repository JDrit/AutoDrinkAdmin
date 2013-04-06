import MySQLdb
import sys
import pyLDAP

configFile = "config"

class Logger():
	
	def __init__(self):
		config = ConfigParser.ConfigParser()
		config.read(configFile)
		self.host = config.get("SQL", "host")
		self.username = config.get("SQL", "username")
		self.password = config.get("SQL", "password")
		self.datbase = config.get("SQL", "database")
		
		self.conn = MySQLdb.connect(host, username, password)
		self.cur = con.cursor()
	
	def enterLog(user,
		try:
			self.conn.execute("INSERT INTO ( , , , ) VALUES (%s, %s, %s)", user
			self.conn.commit()
			self.cursor.close()
			self.conn.close()
		except mdb.Error, e:
			pyLDAP.logging("Could not log to database", e)
		
			
