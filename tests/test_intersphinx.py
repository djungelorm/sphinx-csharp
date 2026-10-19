""" Link to the C# objects of another project through intersphinx """

import pytest
from conftest import references, warnings
from sphinx.testing.util import SphinxTestApp

LIBRARY = '''
.. cs:namespace:: Lib

.. cs:class:: Box<T>

   .. cs:function:: void Put (T item)

   .. cs:function:: void Put (T item, int count)

.. cs:class:: Plain

   .. cs:property:: int Count { get; }
'''


@pytest.fixture
def library(tmp_path_factory):
    """ The output directory, with the inventory, of a project that documents the library """
    srcdir = tmp_path_factory.mktemp('library')
    (srcdir / 'conf.py').write_text("extensions = ['sphinx_csharp']\n")
    (srcdir / 'index.rst').write_text(LIBRARY)
    app = SphinxTestApp('html', srcdir=srcdir, confoverrides={'nitpicky': True})
    try:
        app.build()
        assert warnings(app) == []
    finally:
        # Unregister the nodes and directives of the library, before the build that links to it registers them
        app.cleanup()
    return app.outdir


@pytest.mark.parametrize('rst, links', [
    (':cs:type:`Lib.Plain`', {'Lib.Plain': 'class-Lib.Plain'}),
    (':cs:obj:`Lib.Plain`', {'Lib.Plain': 'class-Lib.Plain'}),
    (':cs:prop:`Lib.Plain.Count`', {'Lib.Plain.Count': 'property-Lib.Plain.Count'}),
    (':cs:type:`Lib.Box\\<T>`', {'Lib.Box<T>': 'class-Lib.Box-1'}),
    (':cs:meth:`Lib.Box\\<T>.Put`', {'Lib.Box<T>.Put': 'function-Lib.Box-1.Put'}),
    (':cs:meth:`Lib.Box-1.Put(T,int)`', {'Lib.Box-1.Put(T,int)': 'function-Lib.Box-1.Put(T,int)'}),
    ('.. cs:namespace:: Lib\n\n:cs:type:`Plain` :cs:type:`Box\\<T>`',
     {'Plain': 'class-Lib.Plain', 'Box<T>': 'class-Lib.Box-1'}),
    ('.. cs:namespace:: Lib\n\n:cs:type:`Lib.Box\\<T>`', {'Lib.Box<T>': 'class-Lib.Box-1'}),
    ('.. cs:namespace:: App\n\n:cs:type:`Lib.Box\\<T>` :cs:meth:`Lib.Box\\<T>.Put`',
     {'Lib.Box<T>': 'class-Lib.Box-1', 'Lib.Box<T>.Put': 'function-Lib.Box-1.Put'}),
    ('.. cs:namespace:: App\n\n.. cs:function:: void Foo (Lib.Box<int> box)',
     {'Lib.Box': 'class-Lib.Box-1', 'int': None}),
    ('.. cs:function:: void Foo (Lib.Box<int> box)', {'Lib.Box': 'class-Lib.Box-1', 'int': None}),
])
def test_intersphinx(build, library, rst, links):
    app = build(rst + '\n', extensions=['sphinx_csharp', 'sphinx.ext.intersphinx'],
                intersphinx_mapping={'library': (str(library), None)})
    assert warnings(app) == []
    assert {text: url.partition('#')[2] or None for text, url in references(app).items()} == links
