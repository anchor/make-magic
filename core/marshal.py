#! /usr/bin/env python

'''Marshal in and out of internal object representations

Internally, we use the object types defined in core.bits,
however we need some way of getting stuff in and out of that format
both for IPC, and so that people don't have to write their
item definitions in Python[0].  We also need to be able to talk in 
different formats to build APIs with.

To do this, we're going to use a simple, data based common format that
should be able to be represented in several different formats (e.g.
python objects, json, xml etc). Bonus points for being able to use 
off-the-shelf encoders and decoders.

The internal format for item classes is based is a list of dicts in
the form:

items = [
   { 'name':         'itemname',                           # required
     'depends':      ['itemname2', 'itemname43', 'groupname']  # optional
     'description':  'multi-line description of the item', # optional
     'if':           '<predicate definition>'              # optional
   },

   { 'name':         'itemname2',
     'depends':      []
   },

   { 'group':        'groupname',                          # required
     'contains':     ['itemname43', itemname32','groupname5']  # required
     'depends':      ['itemname47', 'groupname2' ...]      # optional
     'description':  'multi-line description of the item', # optional
     'if':           '<predicate definition>'              # optional
   },
   ...
]

where all dependencies refered to must be defined in the list.
This is equivalent to the internal definition:

	class itemname(bits.Item):
		description = 'multi-line description of the item'
		depends = (itemname2, itemname43, groupname)
		predicate = <callable that returns True iff predicate holds over passed requirements>

	class itemname2(bits.Item):
		pass

	class groupname(bits.Group):
		description = 'multi-line description of the item'
		depends = (itemname47, groupname2)
		contains = (itemname43, itemname32, groupname5)
		predicate = <callable that returns True iff predicate holds over passed requirements>

	items = [ itemname, itemname2, groupname ]

Item instances are represented in the same way, but the dicts can have 
extra key/value pairs for item state and metadata. These are available
as as a dict as the 'data' property on the python object instances.

Group instances are not currently able to be marshalled; Only classes.
Groups should be reduced out during the process of Task creation.

Predicate definitions as strings are currently as defined in the digraphtools.predicate module
We use the PredicateContainsFactory to generate the predicates. This also allows us to marshal
them back and forward pretty easily from strings

[0] Although it's extensible inside so that you can do things like
write predicates in pure python, the whole system has to be usable
by someone that doesn't know a line of python.
'''
import core.bits
from digraphtools.predicate import PredicateContainsFactory

class ItemConverter(object):
	'''Convert items to and from Item objects
	'''

	identifier_chrs = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890_")
	reserved_keys = set(('name','group','depends','description','contains','if'))
	def normalise_item_name(self, name):
		'''return a passed string that can be used as a python class name'''
		name = str(name)
		name = filter(self.identifier_chrs.__contains__, name)
		if name[:1].isdigit(): 
			name = '_'+name
		return name

	def predicate_string_to_callable(self, predicate):
		'''turn a predicate into a callable'''
		pf = PredicateContainsFactory()
		pred = pf.predicate_from_string(predicate)
		pred._predicate_string = predicate  # Save for marshalling back the other way
		return pred

	def predicate_callable_to_string(self, predicate):
		'''turn a predicate into a callable'''
		if hasattr(predicate, '_predicate_string'):
			return predicate._predicate_string	# Restore previous knowledge. Mwahahahah
		raise ValueError('Cannot marshal strange predicate into a string.')

	def itemdict_to_group(self, itemdict):
		'''return a Group subclass from an item dict datastructure
		This does not unroll dependencies or group contents from strings into classes
		pre: itemdict is valid
		'''
		assert not itemdict.has_key('name')
		name = self.normalise_item_name(itemdict['group'])
		attrs = dict(contains=itemdict['contains'])
		if itemdict.has_key('depends'): attrs['depends'] = tuple(itemdict['depends'])
		if itemdict.has_key('description'): attrs['description'] = itemdict['description']
		if itemdict.has_key('if'): attrs['predicate'] = self.predicate_string_to_callable(itemdict['if'])
		return type.__new__(type, name, (core.bits.Group,), attrs)
		
	def itemdict_to_item_class(self, itemdict):
		'''return an Item subclass from an item dict datastructure
		This does not unroll item dependencies from strings into classes

		pre: itemdict is valid
		'''
		if itemdict.has_key('group'): 
			return self.itemdict_to_group(itemdict)

		name = self.normalise_item_name(itemdict['name'])
		if name == 'TaskComplete':
			itemsuper = core.bits.TaskComplete
		else:
			itemsuper = core.bits.Item
		attrs = dict()
		if itemdict.has_key('depends'): attrs['depends'] = tuple(itemdict['depends'])
		if itemdict.has_key('description'): attrs['description'] = itemdict['description']
		if itemdict.has_key('if'): attrs['predicate'] = self.predicate_string_to_callable(itemdict['if'])
		return type.__new__(type, name, (itemsuper,), attrs)

	def itemdict_to_item_instance(self, itemdict):
		cl = self.itemdict_to_item_class(itemdict)
		data = dict((k,v) for k,v in itemdict.items() if k not in self.reserved_keys)
		return cl(data=data)

	def itemclass_to_itemdict(self, item):
		'''return an item dict datastructure from an Item or Group subclass'''
		if issubclass(item,core.bits.Group):
			itemdict = dict(group=item.__name__, contains=[c.__name__ for c in item.contains])
		else:
			itemdict = dict(name=item.__name__)
		if item.depends: itemdict['depends'] = list(d.__name__ for d in item.depends)
		if item.description: itemdict['description'] = item.description
		if item.predicate != core.bits.BaseItem.predicate:
			# This might fail if someone has put their own callable in as a predicate
			# That's okay; it just means they can't marshal their classes back to json
			itemdict['if'] = self.predicate_callable_to_string(item.predicate)
		return itemdict

	def item_to_itemdict(self, item):
		'''return an item dict datastructure from an Item instance
		Note: Does not work on groups and does not convert predicates
		'''
		assert not isinstance(item, core.bits.Group)
		itemdict = dict(name=item.name)
		itemdict.update(dict((k,v) for k,v in item.data.items() if k not in self.reserved_keys))
		if item.description: itemdict['description'] = item.description
		if len(item.depends):
			itemdict['depends'] = [d.name for d in item.depends]
		return itemdict

class TaskConverter(ItemConverter):
	def taskdict_to_task(self, taskdict):
		# turn the items into instances
		items = map(self.itemdict_to_item_instance, taskdict['items'])

		# reference them to each other correctly
		item_by_name = dict((item.name,item) for item in items)
		for item in items:
			item.depends = tuple(item_by_name[dep] for dep in item.depends)

		# Find the goal node
		metadata = taskdict['metadata']
		goal = item_by_name['TaskComplete']
		requirements = metadata['requirements']
		uuid = metadata['uuid']
		return core.bits.Task(items, requirements, goal, uuid, metadata)
