.PHONY: dist install test clean

dist:
	python setup.py sdist

install:
	pip install -r requirements.txt
	python setup.py install

test:
	rm -rf out
	pip install pep8 pylint
	pep8 sphinx_csharp/csharp.py
	# FIXME: reenable pylint
	# pylint --rcfile=pylint.rc sphinx_csharp/csharp.py
	sphinx-build -E -n -W test test-output

clean:
	rm -rf build dist test-output *.egg-info
