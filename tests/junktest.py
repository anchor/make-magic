#! /usr/bin/env python
from core.deptools import *
from breakfast import *

# Pure python defined item test code
#
# Tests that we can define items in pure python code and have the marshallers
# convert it back and forth several times to simple dicts and JSON without
# any loss of information
#
# THIS IS NOT AN EXAMPLE OF GENERAL USAGE!
#
# TODO: Move this into unit testing

coffee_drinker = breakfast_task_factory.task_from_requirements( ('coffee','hugs') )
caffeine_free = breakfast_task_factory.task_from_requirements( ('hugs',) )

ds = DigraphDependencyStrategy

print coffee_drinker
for item in ds.iterate_item_dependencies(coffee_drinker.goal):
	print item

print
print caffeine_free
for item in ds.iterate_item_dependencies(caffeine_free.goal):
	print item

# Marshalling

import core.marshal
import lib.loaders
import json

print "\nconverting breakfast task to json:"
ic = core.marshal.ItemConverter()
objitems = map(ic.itemclass_to_itemdict, breakfast_task_factory.classes)

jsondata = json.dumps(objitems)
print jsondata


print "\nimporting back in"
task_factory = lib.loaders.JSONItemLoader.load_item_classes_from_string(jsondata)
for c in task_factory.classes:
	print c()

print "\nand back again"
objitems = map(ic.itemclass_to_itemdict, breakfast_task_factory.classes)
jsondata = json.dumps(objitems)
task_factory = lib.loaders.JSONItemLoader.load_item_classes_from_string(jsondata)

print "\nNow trying another pruning example:"
another_caffeine_free = task_factory.task_from_requirements( [] )
for item in ds.iterate_item_dependencies(another_caffeine_free.goal):
	print item
