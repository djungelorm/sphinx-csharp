import pytest
from conftest import references, signatures, warnings

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


def test_builtin_types_are_not_linked(app):
    assert references(app, 'function-MyNamespace.MyClass.Foo') == {'MyClass': 'class-MyNamespace.MyClass'}


def test_nullable_type_links_to_type(app):
    assert references(app, 'function-MyNamespace.MyClass.Nullable') == {'MyClass': 'class-MyNamespace.MyClass'}


def test_reference_from_other_namespace(app):
    assert references(app, 'function-OtherNamespace.Other') == {
        'MyEnum': 'enum-MyNamespace.MyEnum', 'MyClass': 'class-MyNamespace.MyClass'}


def test_external_reference(app):
    assert references(app, 'function-MyNamespace.MyClass.Items') == {
        'List': 'https://docs.microsoft.com/en-us/dotnet/api/System.Collections.Generic.List-1',
        'MyClass': 'class-MyNamespace.MyClass'}


@pytest.mark.xfail(reason=':any: references produce a warning for each C# role')
def test_any_role(build):
    app = build('Title\n=====\n\n.. _foo:\n\nSection\n-------\n\nSee :any:`foo`.\n')
    assert warnings(app) == []


def test_parallel_build(build):
    pages = {f'page{i}': f'Page {i}\n======\n\n.. cs:class:: Page{i}Class\n' for i in range(6)}
    toctree = '.. toctree::\n\n' + ''.join(f'   {name}\n' for name in pages)
    rst = toctree + '\n' + ''.join(f':cs:type:`Page{i}Class` ' for i in range(6)) + '\n'
    app = build(rst, pages=pages, parallel=2)
    assert warnings(app) == []


def test_config_is_not_merged_twice(build):
    build(SOURCE, sphinx_csharp_ignore_xref=['Foo'])
    build(SOURCE, sphinx_csharp_ignore_xref=['Foo'])
    assert ExternalRefs.ignore_xref_types.count('Foo') == 1
    assert 'Foo' not in ExternalRefsData.ignore_xref_types
