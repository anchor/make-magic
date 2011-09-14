#! /usr/bin/env python 
from collections import deque,defaultdict
from itertools import ifilter
import digraphtools

from core.bits import Item,Group

def unbound(func):
	'''always return the underlying function from a bound method'''
	return getattr(func, 'im_func', func)

class BaseDependencyStrategy:
	'''Base class for strategies for dependency resolution'''
	@classmethod
	def iterate_pruned_item_dependencies(cls, requirements, item):
		'''return an ordered list of dependencies for an item such that an items dependencies are before it in the list
		prunted based on predicate
		Not used, but left here because at some point it might be needed to do 
		this in a way that does not alter the items at all (as per the below filter)'''
		raise NotImplementedError

	@classmethod
	def iterate_item_dependencies(cls, item):
		'''return an ordered list of dependencies for an item such that an items dependencies are before it in the list'''
		raise NotImplementedError

	@classmethod
	def make_group_dependencies_explicit(cls, item):
		'''applying dependencies of groups to those it contains'''
		raise NotImplementedError
	
	@classmethod
	def filter_dependency_graph(cls, requirements, item):
		'''filter items in the dependency graph INPLACE based on the supplied requirements
		It's highly recommended you only do this on item instances and not classes as
		it alters or the depends attribute on all items in the supplied DAG '''
		raise NotImplementedError

	@classmethod
	def item_factory(cls, goal_item):
		'''instantiate all items in a dependency tree from an end-goal item

		for every instance in the dependency tree, the depends attribute on the instance overriding the class
		returns an instance of the end-goal where all recursively all dependencies are item instances
		'''
		raise NotImplementedError

	@classmethod
	def early_iter_all_items(cls, item):
		'''get a list of all times, including all groups, contents and dependencies of same
		before groups are unrolled into something that can be represented by a digraph we
		need a way of getting all items, including traversing group contents
		'''
		raise NotImplementedError


class SimpleDependencyStrategy(BaseDependencyStrategy):
	'''Reasonably generic strategy for working with dependencies
	Requires implementation of some things by other strategies

	FIXME: THIS CLASS SHOULD NEVER ACTUALLY BE USED AND SHOULD BE REMOVED ASAP

	Most of the code in it is evil, some of it actually broken (although not
	called), and the calls that are depended on should be rewritten in a sane way.

	Having this code here is dangerous as people might try to call it directly.
	'''

	@classmethod
	def iterate_pruned_item_dependencies(cls, requirements, item, seen=None):
		'''return an ordered list of dependencies for an item such that an items dependencies are before it in the list
		This is equivalent to treating the dependencies as a DAG and traversing while:
			- reducing it to a tree by ignoring any nodes seen in the traversal
			- pruning branches where the requirements do not meet an item's predicate
			- doing a post-order traversal to maintain the invaraint that a node's
			  dependencies preceed it in the traversal.
		'''
		if seen is None: seen = set()
		if item in seen: raise StopIteration
		seen.add(item)
		filtereddeps = ifilter(lambda i: unbound(i.predicate)(requirements), item.depends)
		for dep in filtereddeps:
			for cdep in cls.iterate_pruned_item_dependencies(requirements,dep,seen):
				yield cdep
		yield item

	@classmethod
	def iterate_item_dependencies(cls, item, seen=None):
		if seen is None: seen = set()
		if item in seen: raise StopIteration
		seen.add(item)
		for dep in item.depends:
			for cdep in cls.iterate_item_dependencies(dep,seen):
				yield cdep
		yield item

	@classmethod
	def early_iter_all_items(cls, item, seen=None):
		'''get a list of all times, including all groups, contents and dependencies of same
		before groups are unrolled into soemthing that can be represented by a digraph we
		need a way of getting all items, including traversing group contents
		'''
		if seen is None: seen = set()
		if item in seen: raise StopIteration
		seen.add(item)
		for dep in item.depends:
			for cdep in cls.early_iter_all_items(dep,seen):
				yield cdep
		if isinstance(item,Group) or type(item) == type and issubclass(item,Group):
			for member in item.contains:
				for cdep in cls.early_iter_all_items(member,seen):
					yield cdep
		yield item

	@classmethod
	def filter_dependency_graph(cls, requirements, items):
		'''filter items in the dependency graph INPLACE based on the supplied requirements
		It's highly recommended you only do this on item instances and not classes as
		it alters or the depends attribute on all items in the supplied DAG '''

		keptitems = set(filter(lambda i: unbound(i.predicate)(requirements), items))
		droppeditems = set(items).difference(keptitems)

		for survivor in keptitems:
			# Drop references to filtered instances
			survivor.depends = tuple(dep for dep in survivor.depends if dep in keptitems)
			# Do the same for groups
			if hasattr(survivor,'contains'):
				survivor.contains = tuple(k for k in survivor.contains if k in keptitems)

		# Drop references from filtered instances
		# Although this shouldn't matter, it actually does help make subtle errors more obvious
		# if this code itself is broken
		for dropped in droppeditems: 
			dropped.depends = None

		assert keptitems.isdisjoint(droppeditems)
		return keptitems

	@classmethod
	def instantiate_items(cls, items):
		'''returns a map from classes to instances'''
		# Pre: All items, including all deps, are in 'items'
		instancemap = dict((item, item()) for item in items) # Only ever instantiate each item once
		iteminstances = map(instancemap.get, items)
		for inst in iteminstances:
			inst.depends = tuple(map(instancemap.get, inst.depends))
			if isinstance(inst,Group):
				inst.contains = tuple(map(instancemap.get, inst.contains))
		return instancemap

	@classmethod
	def item_factory(cls, goal_item):
		'''instantiate all items in a dependency tree from an end-goal item

		for every instance in the dependency tree, the depends attribute on the instance overriding the class
		returns an instance of the end-goal where all recursively all dependencies are item instances
		'''
		# Flatten the dep graph to a topsort, instantiate all items, then override depends attributes
		items = set(cls.early_iter_all_items(goal_item))
		instancemap = cls.instantiate_items(items)
		return instancemap[goal_item]

	@classmethod
	def make_group_dependencies_explicit(cls, item):
		items = set(cls.early_iter_all_items(item))	# Gotta catch them all
		items = cls.make_group_dependencies_explicit_for_items(items)
		assert item in items
		return item

	@classmethod
	def make_group_dependencies_explicit_for_items(cls, items):
		allitems = items
		items = set(k for k in allitems if isinstance(k,Item) or type(k) == type and issubclass(k,Item))
		groups = set(k for k in allitems if isinstance(k,Group) or type(k) == type and issubclass(k,Group))
		origitems,origgroups = set(items),set(groups)	# For later testing
		assert allitems == items.union(groups)
		assert items.isdisjoint(groups)

		contained_by = defaultdict(set)

		# First find out what groups an item is contained by
		def iter_group_contents(group):
			for k in group.contains:
				if k in groups: 
					for kk in iter_group_contents(k): yield kk
				else: yield k
		for group in groups:
			for k in iter_group_contents(group):
				contained_by[k].add(group)

		# Item dependencies are the explicit dependencies of the items themselves
		# plus the dependencies of the groups they are contained by
		for item,ingroups in contained_by.items(): 
			assert ingroups.issubset(groups)
			new_deps = set(item.depends)
			for g in ingroups:
				new_deps.update(g.depends)
			item.depends = tuple(new_deps)

		# Now the dependencies of the items inside groups are unrolled, reduce any
		# references of groups to the contents of the groups

		# First do the group contents themselves recursively, and store as sets
		for group in groups:
			group.contains = set(group.contains)
			while not group.contains.isdisjoint(groups):
				for containedgroup in group.contains.intersection(groups):
					assert containedgroup != group
					group.contains.update(containedgroup.contains)
					group.contains.remove(containedgroup)

		# Now that for group.contains has been reduced to non-group items,
		# replace any reference to groups in the dependencies of any item with
		# the contents of that group
		for item in items.difference(groups):
			assert item not in groups
			if not groups.isdisjoint(item.depends):
				item.depends = set(item.depends)
				for groupdep in item.depends.intersection(groups):
					item.depends.update(groupdep.contains)
					item.depends.remove(groupdep)
				item.depends = tuple(item.depends)
			assert groups.isdisjoint(item.depends)

		assert items == origitems
		assert groups == origgroups
		assert allitems == items.union(groups)
		assert items.isdisjoint(groups)
		assert items == allitems.difference(groups)

		return items


not_none = lambda n: n is not None

class GraphDependencyStrategy(SimpleDependencyStrategy):
	'''deal with item dependencies by treating them as a directed acyclic graph
	a graph is represented as a 2tuple of a node, and a list of nodes connected to it's outgoing edges

	graphs calls are generally passed by goal node, with dependencies on the goal being 
	it's outgoing edges

	FIXME: THIS CLASS SHOULD NEVER ACTUALLY BE USED AND SHOULD BE REMOVED ASAP

	Having this code here is dangerous as people might try to call it. Theoretically
	nothing should be called in it and it is only used as a reference point for testing
	'''

	@classmethod
	def get_graph(cls, item, seen=None):
		'''return a DAG from a base item and a set of requirements
		items are pruned from the graph if their predicates are false for the requirements
		'''
		if seen is None: seen = dict()
		if item in seen: return seen[item]
		branches = []
		seen[item] = [item, branches]
		for dep in item.depends:
			branch = cls.get_graph(dep, seen)
			if branch: 
				branches.append(branch)
		return seen[item]

	@classmethod
	def get_pruned_graph(cls, requirements, item, seen=None):
		'''return a DAG from a base item and a set of requirements
		items are pruned from the graph if their predicates are false for the requirements
		'''
		if seen is None: seen = dict()
		if item in seen: return seen[item]
		branches = []
		seen[item] = [item, branches]
		for dep in filter(lambda i: unbound(i.predicate)(requirements), item.depends):
			branch = cls.get_pruned_graph(requirements, dep, seen)
			if branch: 
				branches.append(branch)
		return seen[item]

	@classmethod
	def tree_from_graph(cls, graph, seen=None):
		'''convert a DAG into a arborescence by removing edges to seen nodes'''
		node,connected = graph
		if seen is None: seen=set()
		if node in seen: return None
		seen.add(node)
		connected = [cls.tree_from_graph(sub,seen) for sub in connected]
		return [ node,filter(not_none,connected) ]


	@classmethod
	def postorder_traversal(cls, tree):
		'''traverse tree post-order and return a list of nodes'''
		root,branches = tree
		ret = map(cls.postorder_traversal,branches)
		return sum(ret,[]) + [root]
		
	@classmethod
	def iterate_pruned_item_dependencies(cls, requirements, item):
		tree = cls.tree_from_graph( cls.get_pruned_graph(requirements,item) )
		return cls.postorder_traversal(tree)

	@classmethod
	def iterate_item_dependencies(cls, item):
		tree = cls.tree_from_graph( cls.get_graph(item) )
		return cls.postorder_traversal(tree)


class DigraphDependencyStrategy(SimpleDependencyStrategy):
	@classmethod
	def edges_from_item_deps(cls, item):
		'''iterates over dependency edges with transiability from item'''
		tovisit = deque([item])
		while len(tovisit):
			item = tovisit.pop()
			for dep in item.depends:
				yield (item,dep)
			tovisit.extendleft(item.depends)

	@classmethod
	def graph_from_item_deps(cls, item):
		return digraphtools.graph_from_edges( cls.edges_from_item_deps(item) )

	@classmethod
	def iterate_item_dependencies(cls, item):
		g = cls.graph_from_item_deps(item)
		return digraphtools.dfs_topsort_traversal(g, item)

	@classmethod
	def graph_from_items(cls, items):
		# pre: all items in graph are passed
		def edges_from_items(items):
			for i in items:
				for d in i.depends: yield (i,d)
		return digraphtools.graph_from_edges( edges_from_items(items) )

	@classmethod
	def find_goal_nodes(cls, items):
		'''return the set of all nodes that aren't depended on'''
		graph = cls.graph_from_items(items)
		start_nodes,dependencies = zip(*list(digraphtools.iter_edges(graph)))
		return set(start_nodes).difference(dependencies)

	@classmethod
	def needed_dependencies(cls, graph, item):
		'''return which of an item's dependencies are incomplete'''
		return [dep for dep in graph[item] if dep.data['state'] != dep.COMPLETE]

	@classmethod
	def ready_to_run(cls, items):
		'''return items that are incomplete who have no uncompleted dependencies'''
		graph = cls.graph_from_items(items)
		incomplete =  [item for item in items if item.data['state'] == item.INCOMPLETE]
		return [item for item in incomplete if len(cls.needed_dependencies(graph,item)) == 0]

class DeprecatedDependencyMagic(object):
	#TODO: Figure out the object structure for *Magic. Likely it shouldn't even be in this module
	def __init__(self, strategy=DigraphDependencyStrategy):
		self.strategy = strategy
	def make_new_dep_graph(self, goal_node):
		goal_node = self.strategy.item_factory(goal_node)
		self.strategy.make_group_dependencies_explicit(goal_node)
		return goal_node
	def item_list_for_task(self, task):
		# FIXME: Doesn't look at all goal nodes. If we want only 1 goal node we should enforce it
		goal = self.make_new_dep_graph(task.will[0])
		goal = self.strategy.filter_dependency_graph(task.wants, goal)
		return self.strategy.iterate_item_dependencies(goal)
