#! /usr/bin/env python

'''persistant storage of state data

We need some way to keep track of Tasks that are being worked on,
the state of items etc. It would be even cooler if that data was
to hang around when the process was gone.
'''

try: import pymongo
except: pass	# allow import where noone is using the MongoStore

import config
import random

class MongoStore(object):
	'''persistant mongodb store'''

	def __init__(self):
		self.connection = pymongo.Connection(config.mongodb_server,config.mongodb_port)
		self.db = self.connection[config.mongodb_database]
	def get_tasks(self):
		return [name for name in self.db.collection_names() if 'system.' not in name]
	def new_task(self, uuid, items, metadata=None):
		if metadata == None: metadata = {}
		metadata['uuid'] = uuid
		metadata['metadata'] = True
		self.db[uuid].create_index('name')
		self.db[uuid].create_index('metadata')
		self.db[uuid].insert(items)
		self.db[uuid].insert(metadata)
	def _noid(self, item):
		if item is None or '_id' not in item: return item
		del item['_id']
		return item
	def item(self, uuid, name):
		'''get a specific item for a task'''
		return self._noid( self.db[uuid].find_one({'name': name}) )
	def items(self, uuid):
		'''get all the items for a task'''
		# ALL THE THINGS!
		return [self._noid(item) for item in self.db[uuid].find({'name': {'$exists': True},'metadata': {'$exists': False}})]
	def metadata(self, uuid):
		'''get metadata for a task'''
		metadata = self.db[uuid].find_one({'metadata': {'$exists': True}})
		return self._noid(metadata)
	def update_item(self, uuid, name, updatedict, existingstate={}):
		'''updates an item similar to dict.update()

		if 'existingdict' is supplied, the update will only succeed if 
		the items in existingdict match what is in the item already

		returns the contents of the item after the attempt is made. 
		It is up to the caller to check if the update worked or failed.
		'''
		matchon = dict(existingstate)
		matchon['name'] = name
		self.db[uuid].update(matchon, {'$set': updatedict})
		return self.item(uuid, name)
	def update_metadata(self, uuid, updatedict, existingstate={}):
		'''updates a metadata similar to dict.update()

		if 'existingdict' is supplied, the update will only succeed if 
		the items in existingdict match what is in the metadata already

		returns the contents of the metadata after the attempt is made. 
		It is up to the caller to check if the update worked or failed.
		'''
		matchon = dict(existingstate)
		matchon['metadata'] = {'$exists': True}
		self.db[uuid].update(matchon, {'$set': updatedict})
		return self.metadata(uuid)
	def delete_task(self, uuid):
		'''delete a task, all it's items, and all it's metadata

		This is not recoverable.
		'''
		self.db[uuid].drop()

# Define the default Store here
Store = MongoStore
