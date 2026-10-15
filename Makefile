.PHONY: dist install test lint test-basic test-breathe clean

dist:
	python setup.py sdist

install:
	python -B setup.py install

test: lint test-basic test-breathe

lint:
	pycodestyle sphinx_csharp
	pylint --rcfile=pylint.rc sphinx_csharp

test-basic:
	python -m sphinx -E -n -W test/basic test-output/basic

test-breathe:
	cd test/breathe && doxygen
	python -m sphinx -E -n -W test/breathe test-output/breathe

clean:
	rm -rf build dist test-output test/breathe/_doxygen *.egg-info
