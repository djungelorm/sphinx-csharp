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
    assert {'function-OtherNamespace.Overloads.Add(int)',
            'function-OtherNamespace.Overloads.Add(ref-int,Dictionary<string,int>)',
            'indexer-OtherNamespace.Overloads.this[string]',
            'function-OtherNamespace.Overloads.op_Implicit(Overloads)~string'} <= set(signatures(app))

