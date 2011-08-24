#! /usr/bin/env python

import unittest2 as unittest
import digraphtools
import digraphtools.topsort as topsort

import core.bits as bits
import core.deptools as deptools
import core.store

class BitTests(unittest.TestCase):
	def testTask(self):
		task = bits.Task(tuple(), None, bits.TaskComplete(['fnord']))
		task = bits.Task(('fish','heads'), None, bits.TaskComplete(['fnord']))

class GraphStrategyTests(unittest.TestCase):
	def setUp(self):
		class C(bits.Item): pass
		class B(bits.Item): depends = (C,)
		class A(bits.Item): depends = (B,C)
		self.A,self.B,self.C = A,B,C
	def test_get_graph(self):
		A,B,C = self.A,self.B,self.C
		g = deptools.GraphDependencyStrategy.get_graph(A)
		ref = [A,[ [B,[ [C, []] ]], [C, []] ]]	# Reasons to not use this representation
		self.assertEqual(g,ref)
	def test_iterate_item_dependencies(self):
		toporder = deptools.GraphDependencyStrategy.iterate_item_dependencies(self.A)
		self.assertEqual(list(toporder), [self.C,self.B,self.A])
	def test_item_factory(self):
		a = deptools.GraphDependencyStrategy.item_factory(self.A)
		self.assertIsInstance(a, self.A)
		clstoporder = deptools.GraphDependencyStrategy.iterate_item_dependencies(self.A)
		insttoporder = deptools.GraphDependencyStrategy.iterate_item_dependencies(a)
		for cls,inst in zip(clstoporder,insttoporder):
			self.assertIsInstance(inst,cls)

class DigraphStrategyTests(unittest.TestCase):
	def setUp(self):
		class C(bits.Item): pass
		class B(bits.Item): depends = (C,)
		class A(bits.Item): depends = (B,C)
		self.A,self.B,self.C = A,B,C
	def test_iterate_item_dependencies(self):
		toporder = deptools.DigraphDependencyStrategy.iterate_item_dependencies(self.A)
		self.assertEqual(list(toporder), [self.C,self.B,self.A])
	def test_item_factory(self):
		a = deptools.DigraphDependencyStrategy.item_factory(self.A)
		self.assertIsInstance(a, self.A)
		clstoporder = deptools.DigraphDependencyStrategy.iterate_item_dependencies(self.A)
		insttoporder = deptools.DigraphDependencyStrategy.iterate_item_dependencies(a)
		for cls,inst in zip(clstoporder,insttoporder):
			self.assertIsInstance(inst,cls)
	def test_find_goal_nodes(self):
		goals = deptools.DigraphDependencyStrategy.find_goal_nodes([self.A,self.B,self.C])
		self.assertEqual(set([self.A]), goals)

class SimpleStrategyTests(unittest.TestCase):
	def setUp(self):
		class C(bits.Item): pass
		class B(bits.Item): depends = (C,)
		class A(bits.Item): depends = (B,C)
		self.A,self.B,self.C = A,B,C
	def test_iterate_item_dependencies(self):
		toporder = deptools.SimpleDependencyStrategy.iterate_item_dependencies(self.A)
		self.assertEqual(list(toporder), [self.C,self.B,self.A])

class TopsortTests(unittest.TestCase):
	def test_vr_topsort(self):
	        n = 5
        	partial_order = [(1,2), (2,3), (1,5)]
		g = digraphtools.graph_from_edges(digraphtools.from_partial_order(partial_order))
        	grid = topsort.partial_order_to_grid(partial_order,n)
        	for le in topsort.vr_topsort(n,grid):
			digraphtools.verify_partial_order(digraphtools.iter_partial_order(g), le)

class StoreTests(unittest.TestCase):
	sample_json = '[{"name": "wake_up"}, {"depends": ["wake_up"], "name": "get_up"}, {"depends": ["get_up"], "name": "make_coffee"}, {"depends": ["make_coffee"], "name": "drink_coffee"}, {"depends": ["get_up"], "name": "make_breakfast"}, {"depends": ["make_breakfast"], "name": "eat_breakfast"}, {"depends": ["get_up", "eat_breakfast", "make_coffee"], "name": "walk_out_door"}, {"depends": ["walk_out_door", "eat_breakfast", "drink_coffee"], "name": "go_to_work", "description": "Leave to go to work"}]'
	def _dont_test_memorystore(self):
		uuid = '123456'
		ms = core.store.MemoryStore()
		self.assertFalse(ms.exists(uuid))
		self.assertFalse(ms.exists(uuid, 'items'))
		ms.new_task(uuid)
		self.assertTrue(ms.exists(uuid))
		self.assertFalse(ms.exists(uuid, 'items'))
		ms.store(uuid, 'items', self.sample_json)
		self.assertEqual(ms.retrieve(uuid, 'items'), self.sample_json)

if __name__ == '__main__':
	unittest.main()
