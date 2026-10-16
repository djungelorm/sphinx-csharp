from io import StringIO

import pytest
from conftest import references, resolved_doctree, signatures, status, warnings
from docutils import nodes
from sphinx import addnodes
from sphinx.errors import ExtensionError

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
    ('void Foo (Type a)', {'Type': 'System.Type'}),
    ('void Foo (Exception a)', {'Exception': 'System.Exception'}),
    ('void Foo (HashSet<int> a)', {'HashSet': 'System.Collections.Generic.HashSet-1', 'int': 'System.Int32'}),
    ('void Foo (Task<string> a)', {'Task': 'System.Threading.Tasks.Task-1', 'string': 'System.String'}),
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
    doctree = resolved_doctree(app)
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


def test_obj_and_value_roles(build):
    app = build(SOURCE + '\nMore: :cs:obj:`MyNamespace.MyClass`, :cs:value:`MyNamespace.MyEnum.Bar`.\n')
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


def test_std_ref_role_with_default_domain(build):
    app = build('.. default-domain:: cs\n\nTitle\n=====\n\n.. _foo:\n\nSection\n-------\n\nSee :ref:`foo`.\n')
    assert warnings(app) == []
    assert references(app)['Section'] == 'foo'


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


EXTERNAL_NAME = '''
.. cs:namespace:: Lib.Expressions

.. cs:class:: Expression

.. cs:function:: void FromLib (Expression e)

.. cs:namespace:: App

.. cs:function:: void FromApp (Expression<System.Func<int>> e)
'''


def test_reference_prefers_enclosing_namespace_over_external_type(build):
    app = build(EXTERNAL_NAME)
    assert references(app, 'function-Lib.Expressions.FromLib') == {'Expression': 'class-Lib.Expressions.Expression'}


def test_reference_prefers_external_type_over_other_namespace(build):
    app = build(EXTERNAL_NAME)
    assert warnings(app) == []
    assert references(app, 'function-App.FromApp') == {
        'Expression': MICROSOFT_DOCS + 'System.Linq.Expressions.Expression-1',
        'Func': MICROSOFT_DOCS + 'System.Func-1',
        'int': MICROSOFT_DOCS + 'System.Int32'}


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


def index_entries(app):
    """ The general index entries on the index page, as (text, target id) pairs """
    doctree = app.env.get_doctree('index')
    return [(text, target) for node in doctree.findall(addnodes.index) for _, text, target, _, _ in node['entries']]


def test_index_entries(app):
    entries = index_entries(app)
    assert ('MyNamespace.MyClass (C# class)', 'class-MyNamespace.MyClass') in entries
    assert ('MyNamespace.MyClass.Foo (C# function)', 'function-MyNamespace.MyClass.Foo') in entries
    assert ('MyNamespace.MyEnum.Bar (C# enumerator)', 'enumerator-MyNamespace.MyEnum.Bar') in entries
    assert len(entries) == 10


@pytest.mark.parametrize('option', ['no-index-entry', 'noindexentry'])
def test_no_index_entry(build, option):
    app = build(f'.. cs:class:: Shown\n\n.. cs:class:: Hidden\n   :{option}:\n\n'
                '.. cs:class:: Derived\n\n   .. cs:inherits:: Shown\n')
    assert warnings(app) == []
    assert index_entries(app) == [('Shown (C# class)', 'class-Shown'), ('Derived (C# class)', 'class-Derived')]


@pytest.mark.parametrize('sig, text', [
    ('string this[int i] { get; set; }', 'string this[int i] { get; set; }'),
    ('string this[int i, MyClass j] { get; }', 'string this[int i, MyClass j] { get; }'),
    ('int this[int i] { set; }', 'int this[int i] { set; }'),
    ('int this[int i] { get; private init; }', 'int this[int i] { get; private init; }'),
    ('int this[params int[] i, int j = 0] { get; }', 'int this[params int[] i, int j = 0] { get; }'),
    ('int this[System.Collections.Generic.List<int> i] => 1', 'int this[List<int> i] { get; }'),
])
def test_indexer_signature(build, sig, text):
    app = build(f'.. cs:class:: MyClass\n\n   .. cs:indexer:: {sig}\n')
    assert warnings(app) == []
    assert signatures(app)['indexer-MyClass.this[]'] == text


def test_explicit_interface_indexer(build):
    app = build('.. cs:class:: MyClass\n\n   .. cs:indexer:: int IList<int>.this[int i] { get; }\n')
    assert warnings(app) == []
    assert signatures(app)['indexer-MyClass.IList<int>.this[]'] == 'int IList<int>.this[int i] { get; }'


def test_property_directive_with_indexer(build):
    # Breathe passes indexers from Doxygen to the property directive
    app = build('.. cs:class:: MyClass\n\n   .. cs:property:: string this[string s, int j=0] {get;}\n\n'
                ':cs:idxr:`MyClass.this[]`\n')
    assert warnings(app) == []
    assert signatures(app)['indexer-MyClass.this[]'] == 'string this[string s, int j = 0] { get; }'
    assert references(app)['MyClass.this[]'] == 'indexer-MyClass.this[]'
    assert ('MyClass.this[] (C# indexer)', 'indexer-MyClass.this[]') in index_entries(app)


@pytest.mark.parametrize('sig, text', [
    ('int P { get; init; }', 'int P { get; init; }'),
    ('int P {get;private  set;}', 'int P { get; private set; }'),
    ('int P => 1', 'int P { get; }'),
    ('int P { get; set; } = 5;', 'int P { get; set; } = 5'),
    ('int P', 'int P'),
])
def test_property_signature(build, sig, text):
    app = build(f'.. cs:property:: {sig}\n')
    assert warnings(app) == []
    assert signatures(app)['property-P'] == text


@pytest.mark.parametrize('sig, text, links', [
    ('System.EventHandler Changed { add; remove; }', 'event EventHandler Changed { add; remove; }',
     {'EventHandler': 'System.EventHandler'}),
    ('public System.EventHandler Changed', 'event public EventHandler Changed',
     {'EventHandler': 'System.EventHandler'}),
    ('System.Action Done = null', 'event Action Done = null', {'Action': 'System.Action'}),
])
def test_event_signature(build, sig, text, links):
    app = build(f'.. cs:event:: {sig}\n')
    assert warnings(app) == []
    node_id = next(iter(signatures(app)))
    assert signatures(app)[node_id] == text
    assert references(app, node_id) == {name: MICROSOFT_DOCS + url for name, url in links.items()}


@pytest.mark.parametrize('sig, text, links', [
    ('(int, MyClass) Pair ()', '(int, MyClass) Pair ()',
     {'int': MICROSOFT_DOCS + 'System.Int32', 'MyClass': 'class-MyClass'}),
    ('(int count, (string a, MyClass b) inner)[] Nested ()', '(int count, (string a, MyClass b) inner)[] Nested ()',
     {'int': MICROSOFT_DOCS + 'System.Int32', 'string': MICROSOFT_DOCS + 'System.String', 'MyClass': 'class-MyClass'}),
    ('void Take (System.Collections.Generic.List<(int, MyClass)>? items)', 'void Take (List<(int, MyClass)>? items)',
     {'List': MICROSOFT_DOCS + 'System.Collections.Generic.List-1', 'int': MICROSOFT_DOCS + 'System.Int32',
      'MyClass': 'class-MyClass'}),
    ('(T, MyClass) Generic<T> ((T a, int b) t)', '(T, MyClass) Generic<T> ((T a, int b) t)',
     {'MyClass': 'class-MyClass', 'int': MICROSOFT_DOCS + 'System.Int32'}),
])
def test_tuple_signature(build, sig, text, links):
    app = build(f'.. cs:class:: MyClass\n\n.. cs:function:: {sig}\n')
    assert warnings(app) == []
    node_id = next(key for key in signatures(app) if key.startswith('function-'))
    assert signatures(app)[node_id] == text
    assert references(app, node_id) == links


def test_invalid_tuple_element(build):
    app = build('.. cs:function:: (int, , string) Foo ()\n')
    assert len(warnings(app)) == 1
    assert 'Type signature invalid: (int, , string)' in warnings(app)[0]


def test_type_constraints(build):
    app = build('.. cs:class:: MyClass<T, U> : System.IDisposable where T : class, new() where U : IFoo<T>\n\n'
                '.. cs:interface:: IFoo<in T> where T : notnull\n')
    assert warnings(app) == []
    assert signatures(app)['class-MyClass'] == \
        'class MyClass<T, U> : IDisposable where T : class, new() where U : IFoo<T>'
    assert references(app, 'class-MyClass') == {
        'IDisposable': MICROSOFT_DOCS + 'System.IDisposable', 'IFoo': 'interface-IFoo'}
    assert signatures(app)['interface-IFoo'] == 'interface IFoo<in T> where T : notnull'
    assert references(app, 'interface-IFoo') == {}


def test_method_constraints(build):
    app = build('.. cs:class:: MyClass\n\n.. cs:function:: T Make<T, U> (U u) where T : MyClass, U where U : struct\n')
    assert warnings(app) == []
    assert signatures(app)['function-Make'] == 'T Make<T, U> (U u) where T : MyClass, U where U : struct'
    assert references(app, 'function-Make') == {'MyClass': 'class-MyClass'}


@pytest.mark.parametrize('sig, node_id, text', [
    ('public static Vector operator + (Vector a, Vector b)', 'function-Vector.op_Addition',
     'public static Vector operator + (Vector a, Vector b)'),
    ('static bool operator <(Vector a, Vector b)', 'function-Vector.op_LessThan',
     'static bool operator < (Vector a, Vector b)'),
    ('public static implicit operator double (Vector v)', 'function-Vector.op_Implicit',
     'public static implicit operator double (Vector v)'),
    ('static operator Vector (double d)', 'function-Vector.op_Explicit',
     'static explicit operator Vector (double d)'),
])
def test_operator_signature(build, sig, node_id, text):
    app = build(f'.. cs:struct:: Vector\n\n   .. cs:function:: {sig}\n\n'
                f':cs:meth:`Vector.{node_id.split(".")[-1]}`\n')
    assert warnings(app) == []
    assert signatures(app)[node_id] == text
    assert references(app)[f'Vector.{node_id.split(".")[-1]}'] == node_id


@pytest.mark.parametrize('directive, sig, node_id, text', [
    ('record', 'public Point(int X, int Y)', 'record-Point', 'public record Point (int X, int Y)'),
    ('record', 'readonly struct Point(int X, int Y)', 'record-Point', 'readonly record struct Point (int X, int Y)'),
    ('record', 'class Point<T>(T X) : Base(X), System.IDisposable where T : notnull', 'record-Point',
     'record class Point<T> (T X) : Base(X), IDisposable where T : notnull'),
    ('class', 'Service(Base logger, int timeout = 30) : Base(logger)', 'class-Service',
     'class Service (Base logger, int timeout = 30) : Base(logger)'),
    ('struct', 'Empty()', 'struct-Empty', 'struct Empty ()'),
    # Doxygen writes records, and types with primary constructors, as functions
    ('function', 'record Point (int X, int Y)', 'record-Point', 'record Point (int X, int Y)'),
    ('function', 'readonly record  struct Point (int X, int Y)', 'record-Point',
     'readonly record struct Point (int X, int Y)'),
    ('function', 'record class Point< T > (T X)', 'record-Point', 'record class Point<T> (T X)'),
    ('function', 'class Point (int X)', 'class-Point', 'class Point (int X)'),
])
def test_record_signature(build, directive, sig, node_id, text):
    app = build(f'.. cs:class:: Base\n\n.. cs:{directive}:: {sig}\n')
    assert warnings(app) == []
    assert signatures(app)[node_id] == text
    if 'Base' in text:
        assert references(app, node_id)['Base'] == 'class-Base'


def test_record_role_and_index_entry(build):
    app = build('.. cs:record:: Point(int X, int Y)\n\n:cs:record:`Point`\n')
    assert warnings(app) == []
    assert references(app)['Point'] == 'record-Point'
    assert index_entries(app) == [('Point (C# record)', 'record-Point')]


def test_enum_signature(build):
    app = build('.. cs:enum:: public Color : byte\n\n   .. cs:enumerator:: Red = 1\n\n   .. cs:enumerator:: Green\n\n'
                ':cs:enumerator:`Color.Red`\n')
    assert warnings(app) == []
    assert signatures(app)['enum-Color'] == 'public enum Color : byte'
    assert references(app, 'enum-Color') == {'byte': MICROSOFT_DOCS + 'System.Byte'}
    assert signatures(app)['enumerator-Color.Red'] == 'Red = 1'
    assert signatures(app)['enumerator-Color.Green'] == 'Green'
    assert references(app)['Color.Red'] == 'enumerator-Color.Red'


@pytest.mark.parametrize('directive, sig, text', [
    ('delegate', 'public void Handler (object sender, int e)', 'public delegate void Handler (object sender, int e)'),
    ('delegate', 'delegate void Handler (object sender, int e)', 'delegate void Handler (object sender, int e)'),
    # Breathe passes delegates from Doxygen to the function directive
    ('function', 'delegate void Handler (object sender, int e)', 'delegate void Handler (object sender, int e)'),
])
def test_delegate_signature(build, directive, sig, text):
    app = build(f'.. cs:{directive}:: {sig}\n\n:cs:delegate:`Handler` :cs:type:`Handler`\n')
    assert warnings(app) == []
    assert signatures(app)['delegate-Handler'] == text
    assert references(app)['Handler'] == 'delegate-Handler'
    assert index_entries(app) == [('Handler (C# delegate)', 'delegate-Handler')]


def test_generic_delegate_variance(build):
    app = build('.. cs:delegate:: TResult Factory<in T, out TResult> (T arg) where T : class\n')
    assert warnings(app) == []
    assert signatures(app)['delegate-Factory'] == \
        'delegate TResult Factory<in T, out TResult> (T arg) where T : class'
    assert references(app, 'delegate-Factory') == {}


def test_type_suffixes(build):
    app = build('.. cs:class:: MyClass\n\n.. cs:function:: MyClass?[] Foo (int** p, string?[]? s)\n')
    assert warnings(app) == []
    assert signatures(app)['function-Foo'] == 'MyClass?[] Foo (int** p, string?[]? s)'
    assert references(app, 'function-Foo') == {
        'MyClass': 'class-MyClass', 'int': MICROSOFT_DOCS + 'System.Int32', 'string': MICROSOFT_DOCS + 'System.String'}


def test_parameter_attributes_and_modifiers(build):
    app = build('.. cs:function:: bool Try ([NotNullWhen(true)] out string? s, scoped ref readonly int i)\n')
    assert warnings(app) == []
    assert signatures(app)['function-Try'] == \
        'bool Try ([NotNullWhen(true)] out string? s, scoped ref readonly int i)'


def test_generic_parameter_type_is_not_linked(build):
    app = build('.. cs:function:: void Foo<T> (T a)\n')
    assert warnings(app) == []
    assert signatures(app)['function-Foo'] == 'void Foo<T> (T a)'
    assert references(app, 'function-Foo') == {}


def test_namespace_none_clears_namespace(build):
    app = build('.. cs:namespace:: MyNamespace\n\n.. cs:namespace:: None\n\n.. cs:class:: Bar\n')
    assert 'class-Bar' in signatures(app)


def test_duplicate_description(build):
    app = build('.. toctree::\n\n   page\n\n.. cs:class:: Foo\n', pages={'page': 'Page\n====\n\n.. cs:class:: Foo\n'})
    assert len(warnings(app)) == 1
    assert 'duplicate description of class Foo' in warnings(app)[0]


def test_rebuild_keeps_objects_from_other_pages(build, tmp_path):
    pages = {'page1': 'Page 1\n======\n\n.. cs:class:: Page1Class\n',
             'page2': 'Page 2\n======\n\n.. cs:class:: Page2Class\n'}
    app = build('.. toctree::\n\n   page1\n   page2\n\n:cs:type:`Page1Class`\n', pages=pages)
    (tmp_path / 'page2.rst').write_text('Page 2\n======\n\n.. cs:class:: OtherClass\n')
    app.build()
    assert warnings(app) == []
    assert set(app.env.get_domain('cs').objects) == {('class', 'Page1Class'), ('class', 'OtherClass')}
    assert references(app)['Page1Class'] == 'page1.html#class-Page1Class'


def test_reference_without_target(build):
    app = build('.. cs:class:: Foo\n')
    node = addnodes.pending_xref('', refdomain='cs', reftype='type')
    ref = app.env.get_domain('cs').resolve_xref(app.env, 'index', app.builder, 'type', None, node,
                                                nodes.literal('Foo', 'Foo'))
    assert ref['refid'] == 'class-Foo'


DEBUG_SOURCE = '''
.. cs:class:: MyClass

   .. cs:function:: void Foo (int a)

   .. cs:var:: int count

   .. cs:property:: string Name { get; }

   .. cs:property:: int Plain

   .. cs:indexer:: string this[int i] { get; }

.. cs:attribute:: MyAttr (string a)

See :cs:type:`Missing`.
'''


def test_debug_logging(build):
    app = build(DEBUG_SOURCE, nitpicky=False, sphinx_csharp_debug=True)
    assert warnings(app) == []
    log = status(app)
    for text in ['parsed func:', 'parsed var:', 'parsed prop:', 'falling back to variable: int Plain',
                 'parsed idxr:', 'parsed type:', 'parsed attr:', 'no C# object found for Missing']:
        assert text in log


def test_invalid_config(make_app, tmp_path):
    (tmp_path / 'conf.py').write_text("extensions = ['sphinx_csharp']\n")
    (tmp_path / 'index.rst').write_text('')
    warning = StringIO()
    with pytest.raises(ExtensionError):
        make_app('html', srcdir=tmp_path, warning=warning, confoverrides={'sphinx_csharp_ext_type_map': {'pkg': ['A']}})
    assert 'Error in CSharpDomain.apply_config()' in warning.getvalue()
