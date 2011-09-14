#! /usr/bin/env python

'''Loader of item groups'''

import json

import core.marshal
import core.deptools
from core.bits import *

# FIXME: Need to implement predicate and requirement stuff and
#        all that implies!

class TaskFactory(object):
	'''Factory to generate tasks'''
	def __init__(self, classes, dependency_strategy=core.deptools.DigraphDependencyStrategy):
		self.classes = classes
		self.dependency_strategy = dependency_strategy

	def task_from_requirements(self, requirements):
		'''This is to create a new task given a set of requirements
		'''
		# Instantiate items
		items = self.dependency_strategy.instantiate_items(self.classes)
		items = set(items.values())	# TODO: Fix instantiate_items return. this is unintuitive

		# Filter out things that aren't for this task
		items = self.dependency_strategy.filter_dependency_graph(requirements, items)

		# Define a clear goal node that all existing goals depend on
		goal = TaskComplete(self.dependency_strategy.find_goal_nodes(items))
		items.add(goal)
		assert set(self.dependency_strategy.early_iter_all_items(goal)) == items
		assert goal.name == 'TaskComplete'

		# Unroll groups
		items = self.dependency_strategy.make_group_dependencies_explicit_for_items(items)
		assert goal in items

		# Create task for great justice
		return Task(items, requirements, goal)

class ObjectItemLoader(object):
	'''Load in items defined by python objects and make a TaskFactory from them'''

	@classmethod
	def taskfactory_from_objects(self, objects):
		''''process class items represented by simple python objects and return a TaskFactory'''
		classes = []
		marsh = core.marshal.ItemConverter()
		for o in objects:
			self.check_sanity(o)
			classes.append(marsh.itemdict_to_item_class(o))

		# Have dependencies refer to the classes they depend on, not just the names
		# FIXME: This should probably be in the marshaller module
		class_dict = dict((cls.__name__, cls) for cls in classes)
		for cls in classes:
			# TODO: Warn more sanely about dependencies on non-existant items
			cls.depends = tuple(class_dict[c] for c in cls.depends)
			if issubclass(cls, Group):
				cls.contains = tuple(class_dict[c] for c in cls.contains)

		return TaskFactory(classes)

	@classmethod
	def check_sanity(self, objdict):
		'''check that objdict is actually in the correct form
		if objdict isn't in the correct form for marshalling, raise
		a ValueError'''
		name,group = objdict.get('name'),objdict.get('group')
		if not name and not group: 
			raise ValueError('dict has neither name nor group keys',objdict)
		if name and group:
			raise ValueError('dict has both name and group keys')
		if group:
			contains = objdict.get('contains')
			if not contains:
				raise ValueError('group dict has no contains key')
			if len(contains) == 0:
				raise ValueError('group contains list is empty')
		return True

class JSONItemLoader(ObjectItemLoader):
	'''Load in items defined by some json and make a TaskFactory from them'''

	@classmethod
	def load_item_classes_from_file(cls, f):
		''''load json items from a file and return a TaskFactory'''
		return cls.taskfactory_from_objects(json.load(f))

	@classmethod
	def load_item_classes_from_string(cls, data):
		''''load json items from a file and return a TaskFactory'''
		return cls.taskfactory_from_objects(json.loads(data))
