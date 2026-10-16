import shutil
import subprocess

import breathe
import pytest
from conftest import signatures, warnings


@pytest.mark.sphinx('html', testroot='basic', confoverrides={'nitpicky': True})
def test_basic(app):
    app.build()
    assert warnings(app) == []


@pytest.mark.skipif(shutil.which('doxygen') is None, reason='doxygen is not installed')
# Note: Passing srcdir copies the test root in every supported Sphinx version.
@pytest.mark.sphinx('html', testroot='breathe', srcdir='breathe', confoverrides={'nitpicky': True})
def test_breathe(app):
    subprocess.run(['doxygen'], cwd=app.srcdir, check=True)
    app.build()
    assert warnings(app) == []
    # Note: Breathe 4 writes a set accessor for every property and indexer.
    accessors = '{ get; set; }' if int(breathe.__version__.split('.')[0]) < 5 else '{ get; }'
    assert signatures(app)['indexer-OtherNamespace.Indexer.this[]'] == \
        'string this[Dictionary<string, int> map, int offset = 0] ' + accessors
    assert signatures(app)['class-OtherNamespace.Box'] == 'class Box<T>'
    assert 'function-OtherNamespace.Box.First' in signatures(app)


@pytest.mark.skipif(shutil.which('dotnet') is None, reason='dotnet is not installed')
def test_breathe_sources_compile(rootdir, tmp_path):
    shutil.copytree(rootdir / 'test-breathe', tmp_path, dirs_exist_ok=True)
    subprocess.run(['dotnet', 'build', '-nologo'], cwd=tmp_path, check=True)
