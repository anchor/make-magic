#! /usr/bin/env python

from uuid import uuid4

class Scheme(object):
	def __init__(self, items):
		self.items = items

class BaseItem(object):
	description = ""
	depends = ()
	predicate = lambda task: True
	name = property(lambda self: self.__class__.__name__)
	def __repr__(self):
		return '<'+self.name+'('+self.__class__.__bases__[0].__name__+') instance>'

class Item(BaseItem):
	INCOMPLETE = 'INCOMPLETE'
	FAILED = 'FAILED'
	IN_PROGRESS = 'IN_PROGRESS'
	CANNOT_AUTOMATE = 'CANNOT_AUTOMATE'
	COMPLETE = 'COMPLETE'

	allowed_states = set((INCOMPLETE,FAILED,IN_PROGRESS,CANNOT_AUTOMATE,COMPLETE))
	def __init__(self, data=None):
		if data == None:
			data = dict(state=self.INCOMPLETE)
		self.data = data
	def isComplete(self): 
		return self.data['state'] == self.COMPLETE

class TaskComplete(Item):
	'''sentinal task that contains all items required for completion'''
	def __init__(self, goals=None, data=None):
		if goals != None:
			self.depends = tuple(goals)
		if len(self.depends) == 0:
			raise ValueError('MUST provide goals to create TaskComplete')
		Item.__init__(self,data)

class DataItem(Item):
	def __init__(self):
		Item.__init__(self)
		self.data = None

class Group(BaseItem):
	'''"logical" groups containing items
	groups are sets of items that cannot be started until the group's dependencies are satisfied.

	This sounds perfectly sane until you realise that what you're actually
	doing is defining every item in the group to be dependent on every dependency of the
	group.  As groups can contain groups, every item in the whole graph is actually
	dependent on all dependencies of any groups that contain it, any groups that contain that
	group, and so on recursively.  This is actually a digraph not a chain so a naive implementation
	to see which groups contain an item is not going to work.

	Groups make intuitive sense to humans, and make things so much more hackish to implement.
	They do make it easier for humans to build the original set of dependencies, at the expense
	of using somewhat of a shotgun approach in dependencies at times.  It can also be used to
	effectively partition the dependency digraph through critical nodes.

	One solution to applying dependencies of groups to those it contains is to:
		- For every group, find the group contents plus the contents of any groups
		  contained by the group recursively
		- For each item, add to it's dependencies the union of the set of dependencies of all
		  groups it is contained in.
		  
	Once that is complete, it is then (if needed) possible to perform a reduction to remove the
	groups. A simple implementation would be to for each group, find each dependency on that group
	and replace it with the contents of the group.

	Groups are currently not serialised and stored as state; They should be removed as quickly
	as possible after task creation
	'''
	contains = NotImplemented

class Task(object):
	def __init__(self, items, requirements, goal, uuid=None, data=None):
		if uuid == None:
			uuid = str(uuid4())
		if data == None:
			data = dict()
		self.uuid, self.items, self.requirements, self.data = uuid, items, requirements, data
		assert isinstance(goal, TaskComplete)
		self.goal = goal
	def __repr__(self):
		return "Task(uuid='%s')" % (self.uuid,)
