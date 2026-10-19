import shutil
import subprocess

import pytest
from conftest import references, requires_parallel, signature_lines, warnings

requires_doxygen = pytest.mark.skipif(shutil.which('doxygen') is None, reason='doxygen is not installed')


def check_snapshot(request, lines, path, expected=lambda line: line):
    """
    Compare signature lines with a signatures.txt file, after expected maps each line of the file,
    or write them to the file with --update-snapshots
    """
    if request.config.getoption('update_snapshots'):
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    assert lines == [expected(line) for line in path.read_text(encoding='utf-8').splitlines()]


@pytest.mark.sphinx('html', testroot='basic', confoverrides={'nitpicky': True})
def test_basic(app, request, rootdir):
    app.build()
    assert warnings(app) == []
    check_snapshot(request, signature_lines(app), rootdir / 'test-basic' / 'signatures.txt')


@pytest.mark.parametrize('buildername, pattern', [
    ('text', '*.txt'), ('latex', '*.tex'), ('man', '*.1'), ('singlehtml', '*.html')])
def test_basic_builders(make_app, rootdir, tmp_path, buildername, pattern):
    srcdir = tmp_path / 'basic'
    shutil.copytree(rootdir / 'test-basic', srcdir)
    app = make_app(buildername, srcdir=srcdir, confoverrides={'nitpicky': True})
    app.build()
    assert warnings(app) == []
    assert any('MyMethodClass' in path.read_text(encoding='utf-8') for path in app.outdir.glob(pattern))


@pytest.fixture(scope='module')
def doxygen_project(rootdir, tmp_path_factory):
    """ A copy of the Breathe project, with the XML that Doxygen generates from its sources """
    srcdir = tmp_path_factory.mktemp('doxygen') / 'breathe'
    shutil.copytree(rootdir / 'test-breathe', srcdir)
    subprocess.run(['doxygen'], cwd=srcdir, check=True)
    return srcdir


def breathe_project(doxygen_project, tmp_path):
    """ A copy of the Breathe project and its XML for one build """
    srcdir = tmp_path / 'breathe'
    shutil.copytree(doxygen_project, srcdir)
    return srcdir


@requires_doxygen
def test_breathe(make_app, request, rootdir, doxygen_project, tmp_path):
    breathe = pytest.importorskip('breathe')
    app = make_app('html', srcdir=breathe_project(doxygen_project, tmp_path), confoverrides={'nitpicky': True})
    app.build()
    assert warnings(app) == []
    path = rootdir / 'test-breathe' / 'signatures.txt'
    # Note: Breathe 4 writes a set accessor for every property and indexer.
    if int(breathe.__version__.split('.')[0]) < 5:
        if request.config.getoption('update_snapshots'):
            pytest.skip('the snapshot is for Breathe 5')
        check_snapshot(request, signature_lines(app), path, lambda line: line.replace('{ get; }', '{ get; set; }'))
    else:
        check_snapshot(request, signature_lines(app), path)


@requires_doxygen
@requires_parallel
def test_breathe_parallel(make_app, doxygen_project, tmp_path):
    pytest.importorskip('breathe')
    srcdir = breathe_project(doxygen_project, tmp_path)
    # Sphinx 8.0 and earlier read in parallel only when a project has more than five documents
    classes = ['MyNamespace::MyClass', 'OtherNamespace::B', 'OtherNamespace::Foo', 'OtherNamespace::Bar',
               'OtherNamespace::Overloads', 'OtherNamespace::Accessors', 'OtherNamespace::Indexer']
    pages = [f'page{i}' for i in range(len(classes))]
    for page, name in zip(pages, classes):
        (srcdir / f'{page}.rst').write_text(f'{name}\n{"=" * len(name)}\n\n.. doxygenclass:: {name}\n   :members:\n',
                                            encoding='utf-8')
    (srcdir / 'index.rst').write_text('.. toctree::\n\n' + ''.join(f'   {page}\n' for page in pages) +
                                      '\n:cs:type:`OtherNamespace.Foo` :cs:meth:`OtherNamespace.Overloads.Add`\n',
                                      encoding='utf-8')
    app = make_app('html', srcdir=srcdir, parallel=2, confoverrides={'nitpicky': True})
    app.build()
    assert warnings(app) == []
    assert references(app).items() >= {
        'OtherNamespace.Foo': 'page2.html#class-OtherNamespace.Foo',
        'OtherNamespace.Overloads.Add': 'page4.html#function-OtherNamespace.Overloads.Add'}.items()
