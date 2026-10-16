import shutil
import subprocess

import pytest
from conftest import warnings


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
