#! /usr/bin/env python 

'''visualisation tools for make-magic'''

def write_dot_from_items(items, outfile):
	'''generate dot file output for dependencies amongst supplied items
	writes output to a supplied file already opened for writing.

	Does not have any idea what a group is and will treat it just like anything else
	'''
	print >> outfile, 'digraph depgraph {'
	for item in items:
		print '\tname = "%s";' % (item.name,)
		for dep in item.depends:
			print '\t\t"%s" -> "%s";' % (item.name, dep.name)
	print >> outfile, '}'

def write_dot_from_itemdata(items, outfile, ignore_completed=False):
	'''generate dot file output for dependencies amongst supplied items
	writes output to a supplied file already opened for writing.

	Does not have any idea what a group is and will treat it just like anything else
	'''
	if ignore_completed:
		completed = set(item['name'] for item in items if item['state'] == 'COMPLETE')
	print >> outfile, 'digraph depgraph {'
	for item in items:
		if ignore_completed and item['name'] in completed:
			continue
		print '\tname = "%s";' % (item['name'],)
		for dep in item.get('depends',[]):
			if ignore_completed and dep in completed:
				continue
			print '\t\t"%s" -> "%s";' % (item['name'], dep)
	print >> outfile, '}'

if __name__ == '__main__':
	import sys
	import json
	# Take input from task json on stdin
	taskdata = json.load(sys.stdin)
	write_dot_from_itemdata(taskdata['items'], sys.stdout, ignore_completed=True)
