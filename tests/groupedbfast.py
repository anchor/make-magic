#!/usr/bin/env python

import lib.loaders
from core.bits import *
from core.marshal import ItemConverter
from digraphtools.predicate import predicate

want_coffee = ItemConverter().predicate_string_to_callable(' coffee ')
assert want_coffee(['coffee','tv']) == True
assert want_coffee(['fish','tv']) == False

# Items 
class wake_up(Item):
	pass

class get_up(Item):
	depends = (wake_up,)

class make_breakfast(Item):
	depends = (get_up,)

class eat_breakfast(Item):
	depends = (make_breakfast,)

class make_coffee(Item):
	depends = (get_up,)
	predicate = want_coffee

class drink_coffee(Item):
	depends = (make_coffee,)
	predicate = want_coffee

class have_breakfast(Group):
	depends = (get_up,)
	contains = (eat_breakfast, drink_coffee)

class walk_out_door(Item):
	depends = (get_up, have_breakfast)

class go_to_work(Item):
	description = 'Leave to go to work'
	depends = (walk_out_door,)

# Tasks

items = [wake_up, get_up, have_breakfast, make_breakfast, eat_breakfast, make_coffee, drink_coffee, walk_out_door, go_to_work]
breakfast_task_factory = lib.loaders.TaskFactory(items)
