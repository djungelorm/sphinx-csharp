import shutil
import subprocess

import breathe
import pytest
from conftest import signature_lines, warnings


@pytest.mark.sphinx('html', testroot='basic', confoverrides={'nitpicky': True})
def test_basic(app):
    app.build()
    assert warnings(app) == []
    assert signature_lines(app) == (app.srcdir / 'signatures.txt').read_text().splitlines()


@pytest.mark.parametrize('buildername', ['text', 'latex', 'man', 'singlehtml'])
def test_basic_builders(make_app, rootdir, tmp_path, buildername):
    srcdir = tmp_path / 'basic'
    shutil.copytree(rootdir / 'test-basic', srcdir)
    app = make_app(buildername, srcdir=srcdir, confoverrides={'nitpicky': True})
    app.build()
    assert warnings(app) == []


@pytest.mark.skipif(shutil.which('doxygen') is None, reason='doxygen is not installed')
# Note: Passing srcdir copies the test root in every supported Sphinx version.
@pytest.mark.sphinx('html', testroot='breathe', srcdir='breathe', confoverrides={'nitpicky': True})
def test_breathe(app):
    subprocess.run(['doxygen'], cwd=app.srcdir, check=True)
    app.build()
    assert warnings(app) == []
    expected = (app.srcdir / 'signatures.txt').read_text().splitlines()
    # Note: Breathe 4 writes a set accessor for every property and indexer.
    if int(breathe.__version__.split('.')[0]) < 5:
        expected = [line.replace('{ get; }', '{ get; set; }') for line in expected]
    assert signature_lines(app) == expected
