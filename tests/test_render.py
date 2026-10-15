import pytest
from conftest import references, signatures, warnings
from sphinx import addnodes

from sphinx_csharp.extrefs import ExternalRefs
from sphinx_csharp.extrefs_data import ExternalRefsData

SOURCE = '''
.. cs:namespace:: MyNamespace

.. cs:class:: public MyClass<T> : System.IDisposable

   .. cs:function:: public static int Foo (MyClass a, string b = "x")

   .. cs:function:: static void Ext (this string s)

   .. cs:function:: int? Nullable (MyClass? a)

   .. cs:function:: System.Collections.Generic.List<MyClass> Items ()

   .. cs:property:: string Name { get; set; }

   .. cs:var:: private int count = 0

.. cs:enum:: MyEnum

   .. cs:enumerator:: Bar

.. cs:namespace:: OtherNamespace

.. cs:function:: MyEnum Other (MyClass a)

References: :cs:type:`MyNamespace.MyClass`, :cs:func:`MyNamespace.MyClass.Foo`, :cs:prop:`MyNamespace.MyClass.Name`.
'''


@pytest.fixture
def app(build):
    return build(SOURCE)


def test_no_warnings(app):
    assert warnings(app) == []


@pytest.mark.parametrize('node_id, text', [
    ('class-MyNamespace.MyClass', 'public class MyClass<T> : IDisposable'),
    ('function-MyNamespace.MyClass.Foo', 'public static int Foo (MyClass a, string b = "x")'),
    ('function-MyNamespace.MyClass.Ext', 'static void Ext (this string s)'),
    ('function-MyNamespace.MyClass.Nullable', 'int? Nullable (MyClass? a)'),
    ('function-MyNamespace.MyClass.Items', 'List<MyClass> Items ()'),
    ('property-MyNamespace.MyClass.Name', 'string Name { get; set; }'),
    ('var-MyNamespace.MyClass.count', 'private int count = 0'),
    ('enum-MyNamespace.MyEnum', 'enum MyEnum'),
    ('enumerator-MyNamespace.MyEnum.Bar', 'Bar'),
])
def test_signature(app, node_id, text):
    assert signatures(app)[node_id] == text


MICROSOFT_DOCS = 'https://learn.microsoft.com/en-us/dotnet/api/'


def test_builtin_types_link_to_microsoft_docs(app):
    assert references(app, 'function-MyNamespace.MyClass.Foo') == {
        'int': MICROSOFT_DOCS + 'System.Int32',
        'MyClass': 'class-MyNamespace.MyClass',
        'string': MICROSOFT_DOCS + 'System.String'}


def test_nullable_type_links_to_type(app):
    assert references(app, 'function-MyNamespace.MyClass.Nullable') == {
        'int': MICROSOFT_DOCS + 'System.Int32', 'MyClass': 'class-MyNamespace.MyClass'}


def test_reference_from_other_namespace(app):
    assert references(app, 'function-OtherNamespace.Other') == {
        'MyEnum': 'enum-MyNamespace.MyEnum', 'MyClass': 'class-MyNamespace.MyClass'}


def test_external_reference(app):
    assert references(app, 'function-MyNamespace.MyClass.Items') == {
        'List': MICROSOFT_DOCS + 'System.Collections.Generic.List-1',
        'MyClass': 'class-MyNamespace.MyClass'}


@pytest.mark.parametrize('sig, links', [
    ('void Foo (System.Text.StringBuilder a)', {'StringBuilder': 'System.Text.StringBuilder'}),
    ('void Foo (System.Func<int, string, bool> a)',
     {'Func': 'System.Func-3', 'int': 'System.Int32', 'string': 'System.String', 'bool': 'System.Boolean'}),
    ('void Foo (System.Collections.Generic.Dictionary<string, decimal> a)',
     {'Dictionary': 'System.Collections.Generic.Dictionary-2', 'string': 'System.String',
      'decimal': 'System.Decimal'}),
    ('void Foo (System.Collections.Generic.IList a)', {'IList': 'System.Collections.Generic.IList-1'}),
    ('void Foo (System.Collections.Generic.ISet a)', {'ISet': 'System.Collections.Generic.ISet-1'}),
    ('void Foo ()', {}),
])
def test_system_types_link_to_microsoft_docs(build, sig, links):
    app = build(f'.. cs:function:: {sig}\n')
    assert warnings(app) == []
    assert references(app, 'function-Foo') == {text: MICROSOFT_DOCS + url for text, url in links.items()}


@pytest.mark.parametrize('directive, sig', [
    ('function', 'void Foo (int)'),
    ('property', 'int'),
    ('class', '<T>'),
])
def test_invalid_signature_is_shown_as_written(build, directive, sig):
    app = build(f'.. cs:{directive}:: {sig}\n')
    assert len(warnings(app)) == 1
    assert 'signature invalid' in warnings(app)[0]
    doctree = app.env.get_and_resolve_doctree('index', app.builder, tags=app.tags)
    assert next(doctree.findall(addnodes.desc_signature)).astext() == sig


@pytest.mark.parametrize('namespaces, text', [
    (None, 'MyCompany.Tools.Widget Foo ()'),
    (['MyCompany'], 'Widget Foo ()'),
    (['MyCompany.Tools'], 'Widget Foo ()'),
    (['MyCompany.Other'], 'MyCompany.Tools.Widget Foo ()'),
    (['MyComp'], 'MyCompany.Tools.Widget Foo ()'),
])
def test_unqualified_namespaces(build, namespaces, text):
    app = build('.. cs:class:: MyCompany.Tools.Widget\n\n.. cs:function:: MyCompany.Tools.Widget Foo ()\n',
                sphinx_csharp_unqualified_namespaces=namespaces)
    assert signatures(app)['function-Foo'] == text


def test_ref_and_value_roles(build):
    app = build(SOURCE + '\nMore: :cs:ref:`MyNamespace.MyClass`, :cs:value:`MyNamespace.MyEnum.Bar`.\n')
    assert warnings(app) == []
    refs = references(app)
    assert refs['MyNamespace.MyClass'] == 'class-MyNamespace.MyClass'
    assert refs['MyNamespace.MyEnum.Bar'] == 'enumerator-MyNamespace.MyEnum.Bar'


def test_any_role(build):
    app = build('Title\n=====\n\n.. _foo:\n\nSection\n-------\n\n'
                '.. cs:class:: MyNamespace.Widget\n\n'
                'See :any:`foo` and :any:`MyNamespace.Widget`.\n')
    assert warnings(app) == []
    assert references(app)['MyNamespace.Widget'] == 'class-MyNamespace.Widget'


def test_unresolved_reference_without_nitpicky(build):
    app = build('See :cs:type:`Missing`.\n', nitpicky=False)
    assert warnings(app) == []


def test_unresolved_reference_with_nitpicky(build):
    app = build('See :cs:type:`Missing`.\n')
    assert len(warnings(app)) == 1
    assert 'cs:type reference target not found: Missing' in warnings(app)[0]


AMBIGUOUS = '''
.. cs:namespace:: A.Inner

.. cs:class:: Foo

.. cs:namespace:: B.Inner

.. cs:class:: Foo

.. cs:namespace:: B

.. cs:function:: Foo FromB ()

.. cs:namespace:: C

.. cs:function:: Foo FromC ()
'''


def test_reference_prefers_enclosing_namespace(build):
    app = build(AMBIGUOUS)
    assert references(app, 'function-B.FromB') == {'Foo': 'class-B.Inner.Foo'}


def test_ambiguous_reference(build):
    app = build(AMBIGUOUS)
    assert len(warnings(app)) == 1
    assert "ambiguous reference to Foo, matches: ['A.Inner.Foo', 'B.Inner.Foo']" in warnings(app)[0]


def test_parallel_build(build):
    pages = {f'page{i}': f'Page {i}\n======\n\n.. cs:class:: Page{i}Class\n' for i in range(6)}
    toctree = '.. toctree::\n\n' + ''.join(f'   {name}\n' for name in pages)
    rst = toctree + '\n' + ''.join(f':cs:type:`Page{i}Class` ' for i in range(6)) + '\n'
    app = build(rst, pages=pages, parallel=2)
    assert warnings(app) == []
    assert references(app)['Page3Class'] == 'page3.html#class-Page3Class'


def test_config_is_not_merged_twice(build):
    build(SOURCE, sphinx_csharp_ignore_xref=['Foo'])
    build(SOURCE, sphinx_csharp_ignore_xref=['Foo'])
    assert ExternalRefs.ignore_xref_types.count('Foo') == 1
    assert 'Foo' not in ExternalRefsData.ignore_xref_types
