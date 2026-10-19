import shutil
import subprocess

import pytest
from conftest import references, signature_lines, warnings

requires_doxygen = pytest.mark.skipif(shutil.which('doxygen') is None, reason='doxygen is not installed')


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


def breathe_project(rootdir, tmp_path):
    """ A copy of the Breathe project, with the XML that Doxygen generates from its sources """
    srcdir = tmp_path / 'breathe'
    shutil.copytree(rootdir / 'test-breathe', srcdir)
    subprocess.run(['doxygen'], cwd=srcdir, check=True)
    return srcdir


@requires_doxygen
def test_breathe(make_app, rootdir, tmp_path):
    breathe = pytest.importorskip('breathe')
    app = make_app('html', srcdir=breathe_project(rootdir, tmp_path), confoverrides={'nitpicky': True})
    app.build()
    assert warnings(app) == []
    expected = (app.srcdir / 'signatures.txt').read_text().splitlines()
    # Note: Breathe 4 writes a set accessor for every property and indexer.
    if int(breathe.__version__.split('.')[0]) < 5:
        expected = [line.replace('{ get; }', '{ get; set; }') for line in expected]
    assert signature_lines(app) == expected


@requires_doxygen
def test_breathe_parallel(make_app, rootdir, tmp_path):
    srcdir = breathe_project(rootdir, tmp_path)
    # Sphinx reads and writes in parallel when a project has more than five documents
    classes = ['MyNamespace::MyClass', 'OtherNamespace::B', 'OtherNamespace::Foo', 'OtherNamespace::Bar',
               'OtherNamespace::Overloads', 'OtherNamespace::Accessors', 'OtherNamespace::Indexer']
    pages = [f'page{i}' for i in range(len(classes))]
    for page, name in zip(pages, classes):
        (srcdir / f'{page}.rst').write_text(f'{name}\n{"=" * len(name)}\n\n.. doxygenclass:: {name}\n   :members:\n')
    (srcdir / 'index.rst').write_text('.. toctree::\n\n' + ''.join(f'   {page}\n' for page in pages) +
                                      '\n:cs:type:`OtherNamespace.Foo` :cs:meth:`OtherNamespace.Overloads.Add`\n')
    app = make_app('html', srcdir=srcdir, parallel=2, confoverrides={'nitpicky': True})
    app.build()
    assert warnings(app) == []
    assert references(app).items() >= {
        'OtherNamespace.Foo': 'page2.html#class-OtherNamespace.Foo',
        'OtherNamespace.Overloads.Add': 'page4.html#function-OtherNamespace.Overloads.Add'}.items()
