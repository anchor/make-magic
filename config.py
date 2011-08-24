#! /usr/bin/env python
'''config file for make-magic

This is currently written in pure python, but should be pretty
easy to deal with

You can also override things in local_config.py
'''

# Where do we read our item definitions from
#
items_file = 'doc/sample_items.json'


# MongoDB database to store information about tasks in
mongodb_server = 'localhost'
mongodb_port = 27017
mongodb_database = 'magic' 

# Where the webserver should listen
httpd_listen_address = '127.0.0.1'
httpd_listen_port = 4554


# Attempt to import a local config to override stuff
try:
	from local_config import *
except: 
	pass
