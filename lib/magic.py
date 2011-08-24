#! /usr/bin/env python

'''main python API for make-magic

This is where most of the magic happens. Any APIs you write (e.g. for HTTP)
may very well just call this much of the time
'''

import config

from core.store import Store
from core.marshal import ItemConverter,TaskConverter
from lib.loaders import JSONItemLoader
from core.deptools import DigraphDependencyStrategy
from core.bits import Item

class Magic(object):
	def __init__(self,store_factory=Store,dependency_strategy=DigraphDependencyStrategy):
		# Load items
		self.load_items()
		self.store = store_factory()
		self.dependency_strategy = dependency_strategy

	def load_items(self):
		itemsf = open(config.items_file)
		self.taskfactory = JSONItemLoader.load_item_classes_from_file(itemsf)
		itemsf.close()

	reload_items = load_items

	#
	# This stuff is pretty easy. Get information about existing tasks
	# and update them: Just pass it off to the storage module
	#
	def get_tasks(self):
		return self.store.get_tasks()
	def get_task(self, uuid):
		metadata = self.store.metadata(uuid)
		items = self.store.items(uuid)
		if not metadata and not items:
			raise KeyError('uuid '+str(uuid)+' not found')
		return {'items': items, 'metadata': metadata}
	def get_item(self, uuid, itemname):
		item = self.store.item(uuid, itemname)
		if item is None:
			raise KeyError(uuid+'/'+itemname)
		return item
	def get_metadata(self, uuid):
		metadata = self.store.metadata(uuid)
		if not metadata:
			raise KeyError('uuid '+str(uuid)+' not found')
		return metadata
	def update_item(self, uuid, name, updatedict, onlyif={}):
		cannot_update = set(('name','depends','if'))
		onlyif = dict(onlyif)
		for k,v in updatedict.items():
			if k in cannot_update:
				raise ValueError('cannot modify item attribute "%s"' %(k,))
		if 'onlyif' in updatedict:
			if not getattr(updatedict['onlyif'], 'items', None): 
				raise ValueError('can only set "onlyif" to a dictionary')
			onlyif.update(updatedict['onlyif'])
			updatedict.pop('onlyif')
		if 'state' in updatedict:
			if updatedict['state'] not in Item.allowed_states:
				raise ValueError('can only change state to '+','.join(Item.allowed_states))
		return self.store.update_item(uuid,name,updatedict,onlyif)
	def update_item_state(self, uuid, name, oldstate, newstate):
		'''helper to update a state with a guard against the old one
		WARNING: This actually sucks quite a bit. It doesn't guard against race conditions
		from multiple agents.  This is deliberately not exposed to the HTTP interface for
		that reason.
		'''
		return self.update_item(uuid, name, {'state': newstate}, {'state': oldstate})
	def update_task_metadata(self, uuid, updatedict, onlyif={}):
		if 'uuid' in updatedict and uuid != updatedict['uuid']:
			raise ValueError('cannot change uuid for a task')
		return self.store.update_metadata(uuid,updatedict,onlyif)
	def delete_task(self, uuid):
		self.store.delete_task(uuid)

	#
	# Creating a new task is almost as easy!
	#
	def create_task(self, task_data):
		if 'requirements' not in task_data:
			raise ValueError('No requirements supplied to create task')
		task = self.taskfactory.task_from_requirements(task_data['requirements'])

		# FIXME: Should be in core.marshal
		# This is also an awful hack
		task.data.update(task_data)
		ic = ItemConverter()
		items = [ic.item_to_itemdict(item) for item in task.items]

		# Save!
		self.store.new_task(task.uuid, items, metadata=task.data)
		return self.get_task(task.uuid)

	#
	#  What can we do?
	#
	def ready_to_run(self, uuid):
		'''return all the items that we can run'''
		task = self.get_task(uuid)
		converter = TaskConverter()
		task = converter.taskdict_to_task(task)
		ready =  self.dependency_strategy.ready_to_run(task.items)
		# FIXME: Evil, Evil hack
		if 'TaskComplete' in (r.name for r in ready):
			self.update_item(uuid, 'TaskComplete', {'data': {'state': 'COMPLETED'}})
			return self.ready_to_run(uuid)
		ready =  self.dependency_strategy.ready_to_run(task.items)
		return [converter.item_to_itemdict(item) for item in ready]
