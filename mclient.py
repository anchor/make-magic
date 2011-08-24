#! /usr/bin/env python

'''overly simple command line client to access the magic HTTP API

TODO: Make useful as something other than an unintuitive debugging tool
'''

import sys
import requests
import random

base_url = 'http://localhost:4554/'

class CLIhandler(object):
	def cmd_tasks(self):
		print requests.get(base_url+'task').content
	def cmd_task_create(self, json_task_data):
		print requests.post(base_url+'task/create', headers={'Content-Type':'application/json'}, data=json_task_data).content
	def cmd_metadata(self, uuid):
		print requests.get(base_url+'task/'+uuid+'/metadata').content
	def cmd_update_metadata(self, uuid, json_item_data):
		print requests.get(base_url+'task/'+uuid+'/metadata').content
		print
		print requests.post(base_url+'task/'+uuid+'/metadata', headers={'Content-Type':'application/json'}, data=json_item_data).content
	def cmd_task(self, uuid):
		print requests.get(base_url+'task/'+uuid).content
	def cmd_item(self, uuid, item):
		print requests.get(base_url+'task/'+uuid+'/'+item).content
	def cmd_item_state(self, uuid, item):
		print requests.get(base_url+'task/'+uuid+'/'+item+'/state').content
	def cmd_update_item(self, uuid, item, json_item_data):
		print requests.get(base_url+'task/'+uuid+'/'+item).content
		print
		print requests.post(base_url+'task/'+uuid+'/'+item, headers={'Content-Type':'application/json'}, data=json_item_data).content
	def cmd_update_item_state(self, uuid, item, old_state, new_state):
		'''Example state update
		This is a good example of where we can do item updates that will only work if the item
		is in the same state as we think it is by passing a 'onlyif' dict.
		
		Also, if we are doing something like changing state to lock an item for work, we want to
		make sure that if someone else is doing the same, we have a way of figuring out who actually
		got the lock (simply checking if the state changed is not enough information as someone else
		may be trying to change the state to the same thing; If we're both changing it to IN_PROGRESS,
		we don't want to both assume that we were the one to change it to that)

		We guard against this by setting an attribute to a random value, and checking when we get
		a response that that random value is what we expect.  There is nothing magical about the
		attribute we set, but if all workers don't use the same attribute name, it's not going to be
		as useful.  This should only be a problem if you're using different worker codebases against
		the same task
		'''
		# show the existing state just for demonstration purposes. We don't actually use it
		print "existing state:",
		self.cmd_item_state(uuid,item)
		token = random.randint(1,2**48)
		updatewith = '{"state": "%s", "_change_state_token": %d, "onlyif": {"state": "%s"}}' % (new_state, token, old_state)
		print "updating request:",updatewith
		print requests.post(base_url+'task/'+uuid+'/'+item, headers={'Content-Type':'application/json'}, data=updatewith).content
	def cmd_items_ready(self, uuid):
		print requests.get(base_url+'task/'+uuid+'/available').content
	def cmd_task_delete(self, uuid):
		print requests.delete(base_url+'task/'+uuid).content

	commands = property(lambda self: [n[4:] for n in dir(self) if n[:4] == 'cmd_'])
	def call(self, cmd, *args):  return getattr(self, 'cmd_'+cmd)(*args)

if __name__ == '__main__':
	clih = CLIhandler()
	if len(sys.argv) < 2:
		print >> sys.stderr, sys.argv[0],'[',' | '.join(clih.commands),']'
	else:
		clih.call(sys.argv[1], *sys.argv[2:])
