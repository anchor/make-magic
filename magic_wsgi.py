#! /usr/bin/env python

'''Run the make-magic httpd API'''

import lib.httpd

application = lib.httpd.get_wsgi_application()
