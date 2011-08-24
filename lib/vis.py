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


if __name__ == '__main__':
	import sys
	write_dot_from_items([], sys.stdout)
