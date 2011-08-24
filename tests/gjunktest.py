#! /usr/bin/env python
from core.deptools import *
from groupedbfast import *

coffee_drinker = WageSlave( wants=('coffee','hugs') )
caffeine_free = WageSlave()

dm = DependencyMagic(DigraphDependencyStrategy)

root = dm.make_new_dep_graph(coffee_drinker.will[0])
items = dm.strategy.early_iter_all_items(root)
print "goal nodes are",dm.strategy.find_goal_nodes(items),"\n"


for i in dm.item_list_for_task(coffee_drinker):
	print i

print 

for i in dm.item_list_for_task(caffeine_free):
	print i

