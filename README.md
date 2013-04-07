AutoDrinkAdmin
==============

The program is started by calling the GUI.py which will start the daemon thread.

``` bash
$ python GUI.py
```

## Files:
- Daemon.py: Runs in the background and takes data from the arduino and GUI to update users' 
balances. This listens for input from Serial from the arduino and input from 
the GUI from the user. 

- GUI.py: Uses wxPython to create a GUI for the touch screen. This is updated by the daemon
to display the user's name and balance.

- connector.py:	The libary used to all the LDAP and SQL updates. Adds drink credits to users' 
balances in LDAP. Updates the SQL logs in the drink database.


## Required Python Libaries:
- MySQL-python
- wxPython
- configParser
- python-ldap
- pyserial 
