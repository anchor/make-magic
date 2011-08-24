#! /usr/bin/env python

'''mudpuppy httpd API interface

This provides a very, very lightweight WSGI based http server 
to expose a JSON based API.

This is by no means the only way to interact with make magic
from the outside world, but it is a convenient way to make a
solid point of demarcation, and give something like mudpuppy
something to talk to.

There is NO user security implemented here. If you want some
(and you really, really do), use your favourite web server's
WSGI interface rather than cherrypy's own one
'''

import cherrypy
import json

import config
import lib.magic

from contextlib import contextmanager

def expose_json(func):
	'''decorate to set Content-Type on return to application/json and to expose to cherrypy'''
	def wrapper(*argc,**argd):
		cherrypy.response.headers['Content-Type'] = 'application/json'
		return func(*argc,**argd)
	wrapper.exposed = True
	return wrapper

@contextmanager
def http_resource():
	'''propogate KeyErrors and ValueErrors as HTTP errors'''
	try:
		yield
	except KeyError as err:
		raise cherrypy.HTTPError(404, str(err)) # Resource not found
	except ValueError as err:
		raise cherrypy.HTTPError(400, str(err)) # Bad request

def simple_error_page(status, message, traceback, version):
	return '{"error": "%s", "message": "%s"}' % (status, message)
def error_page(status, message, traceback, version):
	'''simple error page for HTTP service rather than default overblown HTML one'''
	return '{"error": "%s", "message": "%s",\n"traceback": "%s"}' % (status, message,traceback)

cherrypy.config.update({'error_page.400': simple_error_page,
			'error_page.404': simple_error_page,
			'error_page.405': simple_error_page,
			'error_page.default': error_page
			})

class Task(object):

	@expose_json
	def index(self):
		if cherrypy.request.method == 'GET':
			# List ALL THE TASKS!
			return json.dumps(self.magic.get_tasks(),indent=1)
		raise cherrypy.HTTPError(405)

	@expose_json
	def create(self):
		if cherrypy.request.method == 'POST':
			# TODO: ANY sort of taint checking
			with http_resource():
				taskdata = json.load(cherrypy.request.body)
				task = self.magic.create_task(taskdata)
			return json.dumps(task,indent=1)
		raise cherrypy.HTTPError(405)

	@expose_json
	def default(self, uuid, *args):
		# TODO: replace this horrible, horrible spagetti

		if len(args) == 0:
			if cherrypy.request.method == 'GET':
				with http_resource(): # Show the task
					return json.dumps(self.magic.get_task(uuid), indent=1)
			elif cherrypy.request.method == 'DELETE':
				with http_resource(): # wipe task
					self.magic.delete_task(uuid)
					return '{}'
			else: raise cherrypy.HTTPError(405) # Invalid method

		if args[0] == 'available':
			# return items that we can do now
			if cherrypy.request.method == 'GET':
				with http_resource():
					return json.dumps(self.magic.ready_to_run(uuid), indent=1)
			else: raise cherrypy.HTTPError(405) # Invalid method
		elif args[0] == 'metadata':
			if cherrypy.request.method == 'GET':
				with http_resource():
					return json.dumps(self.magic.get_metadata(uuid), indent=1)
			elif cherrypy.request.method == 'POST':
				with http_resource():
					updatedata = json.load(cherrypy.request.body)
					return json.dumps(self.magic.update_task_metadata(uuid,updatedata), indent=1)

		# Nothing so simple as a single task.
		args = dict(zip(['itemname','attrib'],args))

		if 'attrib' in args:
			# Handle attribute on the item (only state so far)
			if args['attrib'] == 'state':
				if cherrypy.request.method == 'GET':
					with http_resource():
						return self.magic.get_item(uuid,args['itemname'])['state']
			raise cherrypy.HTTPError(405)
		else:
			if cherrypy.request.method == 'GET':
				with http_resource():
					return json.dumps(self.magic.get_item(uuid,args['itemname']), indent=1)
			elif cherrypy.request.method == 'POST':
				# Update stuff in the item
				with http_resource():
					updatedata = json.load(cherrypy.request.body)
					return json.dumps(self.magic.update_item(uuid,args['itemname'],updatedata), indent=1)
		raise cherrypy.HTTPError(405)

class Root(object):
	@cherrypy.expose
	def index(self):
		cherrypy.response.headers['Content-Type'] = 'text/plain'
		return '''make magic httpd API is running and happy
		/task/		GET: list tasks
		/task/		POST: create new task  (takes { 'requirements': [] } at minimum)
		/task/uuid/	GET: show task
'''

def get_cherrypy_root(magiclib):
	'''return the root object to be given to cherrypy

	also defines which URLs work. Fun times :)
	'''
	root = Root()
	root.task = Task()

	# Allow the objects to access magic
	# this may not be the optimal way to do it; might want to start more
	# instances so everything isn't using the same Store connection
	root.magic = magiclib
	root.task.magic = magiclib

	return root

def run_httpd():
	magiclib = lib.magic.Magic() 
	cpconfig = {'global': {'server.socket_host': config.httpd_listen_address, 'server.socket_port': config.httpd_listen_port}}
	cherrypy.quickstart(get_cherrypy_root(magiclib), config=cpconfig)

if __name__ == '__main__':
	run_httpd()
