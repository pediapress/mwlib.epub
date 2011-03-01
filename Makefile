all:: MANIFEST.in

MANIFEST.in:: 
	./make_manifest.py

clean::
	git clean -xfd
