test:
	./test.py
	./junktest.py
	./gjunktest.py

test-anchor-import:
	cat doc/anchor_checklist.json | ./import_anchor_json.py 

ta: test-anchor-import

break-anchor-import:
	# Wait for non-deterministic behaviour
	rm /tmp/diffed; while [ ! -s /tmp/diffed ]; do echo try >&2; python -t ./debug_anchor_import.py > /tmp/next; diff -U9999999 /tmp/last /tmp/next > /tmp/diffed; mv /tmp/last /tmp/last.bak; mv /tmp/next /tmp/last; done; diff -u /tmp/last.bak /tmp/last | less
