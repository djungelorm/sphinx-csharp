.PHONY: dist install test clean

dist:
	python setup.py sdist

install:
	python -B setup.py install

test:
	rm -rf out
	pip install pycodestyle pylint
	pycodestyle sphinx_csharp/csharp.py
	# FIXME: reenable pylint
	# pylint --rcfile=pylint.rc sphinx_csharp/csharp.py
	sphinx-build -E -n -W test test-output

clean:
	rm -rf build dist test-output *.egg-info
