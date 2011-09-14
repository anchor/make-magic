#! /usr/bin/env python

'''lint for sets of items

There are many things that really shouldn't exist with a set of items. One
of the biggest is that the dependencies should form a directed acyclic graph,
with absolutely no cycles. 

e.g. given the set of items {a.b,c}, if a depends on b, b depends on c, 
and c depends on a, there is a cycle in the dependency graph, which means 
there is no valid order to satisfy the dependencies in:


   a  ->  b  ->  c
   ^             |
   `-------------'

   Fig 1: Badness


This set of lint tools helps check for this and more.  The bigger the set of
items and the more complex the dependencies in them, the more likely it
is that humans are going to miss something.  This is no substitute for
humans putting in the correct data in the first place (like all lint tools,
this isn't going to pick up most errors, just some of them), but it should
help pick up some dire ones
'''

import core.bits

class LintError(Exception): pass

def check_dependencies_are_instances(item):
	'''check that the item, contents, and dependencies of the item, are instances not classes

	This is very important for task instances. You should never mix references between
	Item instances in a task and the classes that they are built from. Obvious as this
	seems, with the way that marshalling and unmarshalling happens, it is possible if there
	are bugs in the loader or marshaller

	We could check that they were instances of BaseItem, but that would be pretty un-pythonic

	raises LintError if the item is of type 'type'
	raises LintError unless all members of item.depends are not of type 'type'
	raises LintError unless all members of item.contents are not of type 'type'
	'''
	if type(item) == type:
		raise LintError("item is not an instance type",item)
	for dep in item.depends:
		if type(dep) == type:
			raise LintError("item dependency is not an instance type",item,dep)

	contains = getattr(item, 'contains', None)
	if contains is not None:
		for dep in item.contains:
			if type(dep) == type:
				raise LintError("group content is not an instance type",item,dep)


def check_predicate_returns_boolean(item):
	'''return true iff an item's predicate returns something True or False

	TODO: Figure out if this is a good idea. It's not very pythonic
	'''
	ret = item.predicate([])
	if ret is not True and ret is not False:
		raise LintError('item predicate does not return True or False', item, item.predicate)

if __name__ == "__main__":
	class TestItem(object):
		predicate = lambda x: True
		depends = ()
		
	try: # should fail
		check_dependencies_are_instances(TestItem)
		raise Exception("Didn't catch obvious lint error")
	except LintError: pass

	# Should be fine
	check_dependencies_are_instances(TestItem())
	
	try: # should fail
		testinst = TestItem()
		testinstb = TestItem()
		testinst.depends = (testinstb, TestItem)
		check_dependencies_are_instances(testinst)
		raise Exception("Didn't catch obvious lint error")
	except LintError: pass

	# Should be fine
	testinst = TestItem()
	testinstb = TestItem()
	testinst.depends = (testinstb,)
	check_dependencies_are_instances(testinst)

	try: # should fail
		testinst = TestItem()
		testinstb = TestItem()
		testinst.contains = (testinstb, TestItem)
		check_dependencies_are_instances(testinst)
		raise Exception("Didn't catch obvious lint error")
	except LintError: pass

	# Should be fine
	testinst = TestItem()
	testinstb = TestItem()
	testinst.contains = (testinstb,)
	check_dependencies_are_instances(testinst)

	try: # should fail
		testinst = TestItem()
		testinst.predicate = lambda x: "Oh joy"
		check_predicate_returns_boolean(testinst)
		raise Exception("Didn't catch obvious lint error")
	except LintError: pass

	# SHould be fine
	testinst = TestItem()
	testinst.predicate = lambda x: True
	check_predicate_returns_boolean(testinst)
	testinst.predicate = lambda x: False
	check_predicate_returns_boolean(testinst)
