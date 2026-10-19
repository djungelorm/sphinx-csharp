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
    ('class-MyNamespace.MyClass-1', 'public class MyClass<T> : IDisposable'),
    ('function-MyNamespace.MyClass-1.Foo', 'public static int Foo (MyClass a, string b = "x")'),
    ('function-MyNamespace.MyClass-1.Ext', 'static void Ext (this string s)'),
    ('function-MyNamespace.MyClass-1.Nullable', 'int? Nullable (MyClass? a)'),
    ('function-MyNamespace.MyClass-1.Items', 'List<MyClass> Items ()'),
    ('property-MyNamespace.MyClass-1.Name', 'string Name { get; set; }'),
    ('var-MyNamespace.MyClass-1.count', 'private int count = 0'),
    ('enum-MyNamespace.MyEnum', 'enum MyEnum'),
    ('enumerator-MyNamespace.MyEnum.Bar', 'Bar'),
])
def test_signature(app, node_id, text):
    assert signatures(app)[node_id] == text


MICROSOFT_DOCS = 'https://learn.microsoft.com/en-us/dotnet/api/'


def test_builtin_types_link_to_microsoft_docs(app):
    assert references(app, 'function-MyNamespace.MyClass-1.Foo') == {
        'int': MICROSOFT_DOCS + 'System.Int32',
        'MyClass': 'class-MyNamespace.MyClass-1',
        'string': MICROSOFT_DOCS + 'System.String'}


def test_nullable_type_links_to_type(app):
    assert references(app, 'function-MyNamespace.MyClass-1.Nullable') == {
        'int': MICROSOFT_DOCS + 'System.Int32', 'MyClass': 'class-MyNamespace.MyClass-1'}


def test_reference_from_other_namespace(app):
    assert references(app, 'function-OtherNamespace.Other') == {
        'MyEnum': 'enum-MyNamespace.MyEnum', 'MyClass': 'class-MyNamespace.MyClass-1'}


def test_external_reference(app):
    assert references(app, 'function-MyNamespace.MyClass-1.Items') == {
        'List': MICROSOFT_DOCS + 'System.Collections.Generic.List-1',
        'MyClass': 'class-MyNamespace.MyClass-1'}


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
    assert refs['MyNamespace.MyClass'] == 'class-MyNamespace.MyClass-1'
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


@pytest.mark.parametrize('target', ['Missing', 'int[]'])
def test_unresolved_reference_with_nitpicky(build, target):
    app = build(f'See :cs:type:`{target}`.\n')
    assert len(warnings(app)) == 1
    assert f'cs:type reference target not found: {target}' in warnings(app)[0]


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


def test_reference_with_generic_arguments(build):
    # A role splits a target ending in > into a title and a target, unless the < is escaped
    app = build('.. cs:class:: Box<T>\n\n   .. cs:function:: void Put<U> (U u)\n\n'
                '   .. cs:indexer:: int System.Collections.Generic.IList<int>.this[int i]\n\n'
                ':cs:type:`Box\\<T>` :cs:meth:`Box<T>.Put` :cs:meth:`Box.Put\\<U>` :cs:meth:`Box<int>.Put<U>(U)` '
                ':cs:idxr:`Box.System.Collections.Generic.IList<int>.this[]` :cs:type:`List\\<int>` '
                ':cs:type:`System.Collections.Generic.Dictionary\\<string, int>`\n\n'
                ':cs:meth:`Box<int[]>.Put` :cs:type:`System.Func\\<(int, string)>` '
                ':cs:type:`System.Collections.Generic.Dictionary\\<string, int[]>`\n\n'
                ':cs:type:`System.Collections.Generic.Dictionary\\<int, string>.KeyCollection` '
                ':cs:type:`System.Collections.Generic.List\\<int>.Enumerator\\<T>`\n')
    assert warnings(app) == []
    assert references(app) == {
        'Box<T>': 'class-Box-1', 'Box<T>.Put': 'function-Box-1.Put', 'Box.Put<U>': 'function-Box-1.Put',
        'Box<int>.Put<U>(U)': 'function-Box-1.Put<U>(U)',
        'Box.System.Collections.Generic.IList<int>.this[]':
            'indexer-Box-1.System.Collections.Generic.IList<int>.this[]',
        'List<int>': MICROSOFT_DOCS + 'System.Collections.Generic.List-1',
        'System.Collections.Generic.Dictionary<string, int>':
            MICROSOFT_DOCS + 'System.Collections.Generic.Dictionary-2',
        'int': MICROSOFT_DOCS + 'System.Int32',
        'Box<int[]>.Put': 'function-Box-1.Put', 'System.Func<(int, string)>': MICROSOFT_DOCS + 'System.Func-1',
        'System.Collections.Generic.Dictionary<string, int[]>':
            MICROSOFT_DOCS + 'System.Collections.Generic.Dictionary-2',
        'System.Collections.Generic.Dictionary<int, string>.KeyCollection':
            MICROSOFT_DOCS + 'System.Collections.Generic.Dictionary-2.KeyCollection',
        'System.Collections.Generic.List<int>.Enumerator<T>':
            MICROSOFT_DOCS + 'System.Collections.Generic.List-1.Enumerator'}


def test_reference_prefers_enclosing_namespace(build):
    app = build(AMBIGUOUS)
    assert references(app, 'function-B.FromB') == {'Foo': 'class-B.Inner.Foo'}


def test_ambiguous_reference(build):
    app = build(AMBIGUOUS)
    assert len(warnings(app)) == 1
    assert "ambiguous reference to Foo, matches: ['A.Inner.Foo', 'B.Inner.Foo']" in warnings(app)[0]


@pytest.mark.parametrize('rst, target', [
    ('.. cs:function:: void Use (Outcome<int> a)', 'class-Outcome-1'),
    ('.. cs:function:: void Use (Outcome a)', 'class-Outcome'),
    (':cs:type:`Outcome\\<T>`', 'class-Outcome-1'),
    (':cs:type:`Outcome`', 'class-Outcome'),
])
def test_generic_and_non_generic_type(build, rst, target):
    app = build('.. cs:class:: static Outcome\n\n.. cs:class:: Outcome<TResult>\n\n' + rst + '\n')
    assert warnings(app) == []
    assert [ref for ref in references(app).values() if 'Outcome' in ref] == [target]


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


def test_overload_reference_is_stable_across_builds(build, make_app, tmp_path):
    pages = {'a': 'A\n=\n\n.. cs:function:: void Foo (int a)\n', 'b': 'B\n=\n\n.. cs:function:: void Foo (string a)\n'}
    app = build('.. toctree::\n\n   a\n   b\n\n:cs:meth:`Foo`\n', pages=pages)
    assert references(app)['Foo'] == 'a.html#function-Foo'
    # Rereading page a moves its overload after the overload on page b in the domain data
    (tmp_path / 'a.rst').write_text(pages['a'] + '\nChanged.\n')
    app = make_app('html', srcdir=tmp_path, confoverrides={'nitpicky': True})
    app.build()
    assert references(app)['Foo'] == 'a.html#function-Foo'


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
    assert ('MyNamespace.MyClass<T> (C# class)', 'class-MyNamespace.MyClass-1') in entries
    assert ('MyNamespace.MyClass.Foo (C# function)', 'function-MyNamespace.MyClass-1.Foo') in entries
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


def test_explicit_interface_members(build):
    # Doxygen writes a space after the interface of an explicit implementation
    app = build('.. cs:class:: MyClass\n\n'
                '   .. cs:function:: System.Collections.Generic.IEnumerator< int > '
                'System.Collections.Generic.IEnumerable< int >. GetEnumerator ()\n\n'
                '   .. cs:property:: int IShape. Sides {get;}\n\n'
                '   .. cs:property:: int IShape. this[int i] {get;}\n\n'
                ':cs:meth:`MyClass.System.Collections.Generic.IEnumerable<int>.GetEnumerator`\n')
    assert warnings(app) == []
    assert signatures(app) == {
        'class-MyClass': 'class MyClass',
        'function-MyClass.System.Collections.Generic.IEnumerable<int>.GetEnumerator':
            'IEnumerator<int> System.Collections.Generic.IEnumerable<int>.GetEnumerator ()',
        'function-MyClass.System.Collections.Generic.IEnumerable<int>.GetEnumerator()':
            'IEnumerator<int> System.Collections.Generic.IEnumerable<int>.GetEnumerator ()',
        'property-MyClass.IShape.Sides': 'int IShape.Sides { get; }',
        'indexer-MyClass.IShape.this[]': 'int IShape.this[int i] { get; }',
        'indexer-MyClass.IShape.this[int]': 'int IShape.this[int i] { get; }',
    }
    assert references(app)['MyClass.System.Collections.Generic.IEnumerable<int>.GetEnumerator'] == \
        'function-MyClass.System.Collections.Generic.IEnumerable<int>.GetEnumerator'


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
    ('public System.EventHandler Changed', 'public event EventHandler Changed',
     {'EventHandler': 'System.EventHandler'}),
    ('public event System.EventHandler? Changed', 'public event EventHandler? Changed',
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
    assert signatures(app)['class-MyClass-2'] == \
        'class MyClass<T, U> : IDisposable where T : class, new() where U : IFoo<T>'
    assert references(app, 'class-MyClass-2') == {
        'IDisposable': MICROSOFT_DOCS + 'System.IDisposable', 'IFoo': 'interface-IFoo-1'}
    assert signatures(app)['interface-IFoo-1'] == 'interface IFoo<in T> where T : notnull'
    assert references(app, 'interface-IFoo-1') == {}


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
    ('record', 'class Point<T>(T X) : Base(X), System.IDisposable where T : notnull', 'record-Point-1',
     'record class Point<T> (T X) : Base(X), IDisposable where T : notnull'),
    ('class', 'Service(Base logger, int timeout = 30) : Base(logger)', 'class-Service',
     'class Service (Base logger, int timeout = 30) : Base(logger)'),
    ('struct', 'Empty()', 'struct-Empty', 'struct Empty ()'),
    # Doxygen writes records, and types with primary constructors, as functions
    ('function', 'record Point (int X, int Y)', 'record-Point', 'record Point (int X, int Y)'),
    ('function', 'readonly record  struct Point (int X, int Y)', 'record-Point',
     'readonly record struct Point (int X, int Y)'),
    ('function', 'record class Point< T > (T X)', 'record-Point-1', 'record class Point<T> (T X)'),
    ('function', 'class Point (int X)', 'class-Point', 'class Point (int X)'),
    ('function', 'record Point (int X) : System.IDisposable', 'record-Point', 'record Point (int X) : IDisposable'),
    ('function', 'record Point<T> (T X) : Base(X) where T : struct', 'record-Point-1',
     'record Point<T> (T X) : Base(X) where T : struct'),
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
    app = build(f'.. cs:{directive}:: {sig}\n\n'
                ':cs:delegate:`Handler` :cs:type:`Handler` :cs:func:`Handler` :cs:meth:`Handler`\n')
    assert warnings(app) == []
    assert signatures(app)['delegate-Handler'] == text
    assert references(app)['Handler'] == 'delegate-Handler'
    assert index_entries(app) == [('Handler (C# delegate)', 'delegate-Handler')]


def test_object_type_of_each_signature(build):
    app = build('.. cs:function:: delegate void A ()\n'
                '                 void B ()\n'
                '                 delegate void C ()\n\n'
                '.. cs:property:: int this[int i] { get; }\n               int P { get; }\n')
    assert warnings(app) == []
    assert signatures(app)['delegate-A'] == 'delegate void A ()'
    assert signatures(app)['function-B'] == 'void B ()'
    assert signatures(app)['delegate-C'] == 'delegate void C ()'
    assert signatures(app)['indexer-this[]'] == 'int this[int i] { get; }'
    assert signatures(app)['property-P'] == 'int P { get; }'


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


def test_pointer_next_to_name(build):
    # Doxygen writes pointer parameters as int **p
    app = build('.. cs:function:: int *Foo (int **p, int * q)\n')
    assert warnings(app) == []
    assert signatures(app)['function-Foo(int**,int*)'] == 'int* Foo (int** p, int* q)'


def test_parameter_attributes_and_modifiers(build):
    app = build('.. cs:function:: bool Try ([NotNullWhen(true)] out string? s, scoped ref readonly int i)\n')
    assert warnings(app) == []
    assert signatures(app)['function-Try'] == \
        'bool Try ([NotNullWhen(true)] out string? s, scoped ref readonly int i)'


def test_generic_attribute(build):
    app = build('.. cs:attribute:: MyAttr<T> (T value, int count)\n\n:cs:attr:`MyAttr`\n')
    assert warnings(app) == []
    assert signatures(app)['attribute-MyAttr'] == 'MyAttr<T> (T value, int count)'
    assert references(app) == {'int': MICROSOFT_DOCS + 'System.Int32', 'MyAttr': 'attribute-MyAttr'}


def test_constructor_initializer(build):
    app = build('.. cs:class:: C\n\n   .. cs:function:: public C (int a) : base(a, "x")\n')
    assert warnings(app) == []
    assert signatures(app)['function-C.C'] == 'public C (int a) : base(a, "x")'


def test_expression_body(build):
    app = build('.. cs:function:: int Twice (int x) => x * 2;\n')
    assert warnings(app) == []
    assert signatures(app)['function-Twice'] == 'int Twice (int x)'


@pytest.mark.parametrize('directive, sig, node_id, text', [
    ('function', '[Obsolete("Use Bar")] void Foo ()', 'function-Foo', '[Obsolete("Use Bar")] void Foo ()'),
    ('function', '[Serializable] record Point (int X)', 'record-Point', '[Serializable] record Point (int X)'),
    ('class', '[Serializable][Obsolete] public MyClass', 'class-MyClass',
     '[Serializable] [Obsolete] public class MyClass'),
    ('record', '[Serializable] Point(int X)', 'record-Point', '[Serializable] record Point (int X)'),
    ('var', '[NonSerialized] int x', 'var-x', '[NonSerialized] int x'),
    ('property', '[JsonIgnore] int P { get; }', 'property-P', '[JsonIgnore] int P { get; }'),
    ('property', '[IndexerName("Item")] int this[int i] { get; }', 'indexer-this[]',
     '[IndexerName("Item")] int this[int i] { get; }'),
    ('indexer', '[IndexerName("Item")] int this[int i] { get; }', 'indexer-this[]',
     '[IndexerName("Item")] int this[int i] { get; }'),
    ('event', '[field: NonSerialized] System.EventHandler Changed', 'event-Changed',
     '[field: NonSerialized] event EventHandler Changed'),
    ('enum', '[Flags] Color', 'enum-Color', '[Flags] enum Color'),
    ('enumerator', '[Obsolete] Red', 'enumerator-Red', '[Obsolete] Red'),
])
def test_declaration_attributes(build, directive, sig, node_id, text):
    app = build(f'.. cs:{directive}:: {sig}\n')
    assert warnings(app) == []
    assert signatures(app)[node_id] == text


def test_unclosed_attribute(build):
    app = build('.. cs:function:: [Obsolete void Foo ()\n')
    assert len(warnings(app)) == 1
    assert 'Method signature invalid: [Obsolete void Foo ()' in warnings(app)[0]


def test_trailing_semicolon(build):
    app = build('.. cs:function:: partial void Foo ();\n\n.. cs:var:: const int X = 1;\n\n'
                '.. cs:event:: System.EventHandler Changed;\n')
    assert warnings(app) == []
    assert signatures(app) == {'function-Foo': 'partial void Foo ()', 'function-Foo()': 'partial void Foo ()',
                               'var-X': 'const int X = 1', 'event-Changed': 'event EventHandler Changed'}


def test_default_value_with_comma(build):
    app = build('.. cs:function:: void Join (string sep = ", ", char quote = \'"\')\n')
    assert warnings(app) == []
    assert signatures(app)['function-Join'] == 'void Join (string sep = ", ", char quote = \'"\')'


def test_default_values_and_attributes_with_brackets(build):
    app = build('.. cs:function:: void Foo (int a = 1 << 2, bool b = x < y, string s = @"C:\\", [A(X[Y[0]])] int c)\n')
    assert warnings(app) == []
    assert signatures(app)['function-Foo'] == \
        'void Foo (int a = 1 << 2, bool b = x < y, string s = @"C:\\", [A(X[Y[0]])] int c)'


def test_nested_tuple(build):
    app = build('.. cs:class:: MyClass\n\n.. cs:function:: ((int, (int, MyClass)), int) Pair ()\n')
    assert warnings(app) == []
    assert signatures(app)['function-Pair'] == '((int, (int, MyClass)), int) Pair ()'
    assert references(app, 'function-Pair') == {'int': MICROSOFT_DOCS + 'System.Int32', 'MyClass': 'class-MyClass'}


def test_qualified_enumerator(build):
    app = build('.. cs:enum:: Color\n\n.. cs:enumerator:: Color.Red = 1\n\n:cs:enumerator:`Color.Red`\n')
    assert warnings(app) == []
    assert signatures(app)['enumerator-Color.Red'] == 'Color.Red = 1'
    assert references(app)['Color.Red'] == 'enumerator-Color.Red'


def test_nested_type_in_generic_type(build):
    app = build('.. cs:class:: Outer<T>\n\n   .. cs:class:: Inner\n\n   .. cs:class:: Pair<U>\n\n'
                '.. cs:function:: Outer<int>.Inner Local ()\n\n'
                '.. cs:function:: Outer<int>.Pair<string>[] LocalGeneric ()\n\n'
                '.. cs:function:: System.Collections.Generic.List<int>.Enumerator Qualified ()\n\n'
                '.. cs:function:: Dictionary<string, int>.KeyCollection Unqualified ()\n')
    assert warnings(app) == []
    assert signatures(app)['function-Local'] == 'Outer<int>.Inner Local ()'
    assert references(app, 'function-Local') == {
        'Outer': 'class-Outer-1', 'int': MICROSOFT_DOCS + 'System.Int32', 'Inner': 'class-Outer-1.Inner'}
    assert signatures(app)['function-LocalGeneric'] == 'Outer<int>.Pair<string>[] LocalGeneric ()'
    assert references(app, 'function-LocalGeneric')['Pair'] == 'class-Outer-1.Pair-1'
    assert signatures(app)['function-Qualified'] == 'List<int>.Enumerator Qualified ()'
    assert references(app, 'function-Qualified') == {
        'List': MICROSOFT_DOCS + 'System.Collections.Generic.List-1', 'int': MICROSOFT_DOCS + 'System.Int32',
        'Enumerator': MICROSOFT_DOCS + 'System.Collections.Generic.List-1.Enumerator'}
    assert references(app, 'function-Unqualified')['KeyCollection'] == \
        MICROSOFT_DOCS + 'System.Collections.Generic.Dictionary-2.KeyCollection'


def test_nested_type_in_unknown_or_ignored_type(build):
    app = build('.. cs:function:: Missing<int>.Inner Foo ()\n\n.. cs:function:: Skip<int>.Inner Bar ()\n',
                sphinx_csharp_ignore_xref=['Skip', 'Skip.Inner'])
    assert len(warnings(app)) == 2
    assert 'Missing' in warnings(app)[0] and 'Missing.Inner' in warnings(app)[1]
    assert signatures(app)['function-Bar'] == 'Skip<int>.Inner Bar ()'


def test_nested_type_named_without_outer_arity(build):
    # Doxygen 1.9.8 names a type nested in a generic type without the arity of the outer type
    app = build('.. cs:struct:: Span2D.Enumerator\n\n.. cs:struct:: Other.Enumerator\n\n'
                '.. cs:class:: Span2D<T>\n\n   .. cs:function:: Enumerator GetEnumerator ()\n')
    assert warnings(app) == []
    assert references(app, 'function-Span2D-1.GetEnumerator') == {'Enumerator': 'struct-Span2D.Enumerator'}


def test_enclosing_type_generic_parameter_is_not_linked(build):
    app = build('.. cs:class:: MyList<T>\n\n   .. cs:function:: T Get (System.Collections.Generic.List<T> items)\n\n'
                '   .. cs:class:: Node\n\n      .. cs:property:: T Value { get; }\n\n'
                '.. cs:class:: Other\n\n   .. cs:function:: void Take (T a)\n')
    # T is only a generic parameter inside MyList
    assert len(warnings(app)) == 1
    assert 'reference target not found: T' in warnings(app)[0]
    assert references(app, 'function-MyList-1.Get') == {'List': MICROSOFT_DOCS + 'System.Collections.Generic.List-1'}
    assert references(app, 'property-MyList-1.Node.Value') == {}


def test_generic_parameter_in_base_type_is_not_linked(build):
    app = build('.. cs:struct:: Pair<T> : System.IEquatable<Pair<T>>, System.Collections.Generic.IEnumerable<T>\n')
    assert warnings(app) == []
    assert references(app, 'struct-Pair-1') == {
        'IEquatable': MICROSOFT_DOCS + 'System.IEquatable-1', 'Pair': 'struct-Pair-1',
        'IEnumerable': MICROSOFT_DOCS + 'System.Collections.Generic.IEnumerable-1'}


DOC_FIELDS_SOURCE = '''
.. cs:class:: MyClass

   .. cs:function:: T Find<T> (System.Collections.Generic.List<T> items, int start)

      :param items: The items to search.
      :type items: System.Collections.Generic.List<T>
      :param int start: The index to start at.
      :typeparam T: The item type.
      :returns: The first item.
      :rtype: T
      :throws System.ArgumentOutOfRangeException: If start is out of range.
      :throws MyClass: Never.
'''


def test_doc_fields(build):
    app = build(DOC_FIELDS_SOURCE)
    assert warnings(app) == []
    doctree = resolved_doctree(app)
    fields = {field[0].astext(): field[1].astext().replace('\xa0', ' ') for field in doctree.findall(nodes.field)}
    assert fields['Parameters'] == 'items (List<T>) – The items to search.\n\nstart (int) – The index to start at.'
    assert fields['Type Parameters'] == 'T – The item type.'
    assert fields['Returns'] == 'The first item.'
    assert fields['Return type'] == 'T'
    assert fields['Throws'] == 'ArgumentOutOfRangeException – If start is out of range.\n\nMyClass – Never.'
    assert references(app) == {
        'List': MICROSOFT_DOCS + 'System.Collections.Generic.List-1', 'int': MICROSOFT_DOCS + 'System.Int32',
        'ArgumentOutOfRangeException': MICROSOFT_DOCS + 'System.ArgumentOutOfRangeException',
        'MyClass': 'class-MyClass'}


def test_doc_field_with_generic_parameter_of_any_signature(build):
    app = build('.. cs:function:: T Get<T> ()\n                 void Get (int i)\n\n   :rtype: T\n')
    assert warnings(app) == []
    assert references(app) == {'int': MICROSOFT_DOCS + 'System.Int32'}


def test_doc_field_type_with_modifiers(build):
    app = build('.. cs:function:: ref readonly int Foo ()\n\n   :rtype: ref readonly int\n')
    assert warnings(app) == []
    fields = {field[0].astext(): field[1].astext().replace('\xa0', ' ')
              for field in resolved_doctree(app).findall(nodes.field)}
    assert fields['Return type'] == 'ref readonly int'


def test_doc_field_with_invalid_type(build):
    app = build('.. cs:function:: void Foo (int a)\n\n   :param a: The value.\n   :type a: <int>\n')
    assert len(warnings(app)) == 1
    assert 'Type signature invalid: <int>' in warnings(app)[0]


def test_doc_field_with_unresolved_type(build):
    app = build('.. cs:function:: void Foo ()\n\n   :rtype: Missing\n   :throws Unknown: Never.\n')
    assert len(warnings(app)) == 2
    assert 'index.rst:3: WARNING: cs:type reference target not found: Missing' in warnings(app)[0]
    assert 'index.rst:4: WARNING: cs:type reference target not found: Unknown' in warnings(app)[1]


@pytest.mark.parametrize('sig', ['void Foo<T> (T a)', 'T? Foo<T> (T[] a, T? b)', 'T[] Foo<T> ((T, int) a)'])
def test_generic_parameter_type_is_not_linked(build, sig):
    app = build(f'.. cs:function:: {sig}\n')
    assert warnings(app) == []
    assert signatures(app)['function-Foo'] == sig
    assert set(references(app, 'function-Foo')) <= {'int'}


def test_namespace_none_clears_namespace(build):
    app = build('.. cs:namespace:: MyNamespace\n\n.. cs:namespace:: None\n\n.. cs:class:: Bar\n')
    assert 'class-Bar' in signatures(app)


def test_duplicate_description(build):
    app = build('.. toctree::\n\n   page\n\n.. cs:class:: Foo\n', pages={'page': 'Page\n====\n\n.. cs:class:: Foo\n'})
    assert len(warnings(app)) == 1
    assert 'duplicate description of class Foo' in warnings(app)[0]


OVERLOADS_SOURCE = '''
.. cs:class:: C

   .. cs:function:: void Foo (int a)

   .. cs:function:: void Foo (ref int a, Dictionary<string, int> b)

   .. cs:function:: void Foo<T> (T a)

   .. cs:function:: void Foo ((int count, string name) pair)

   .. cs:function:: static implicit operator int (C c)

   .. cs:function:: static implicit operator string (C c)

   .. cs:function:: static implicit operator (int x, int y) (C c)

   .. cs:indexer:: string this[int i] { get; }

   .. cs:indexer:: string this[string key] { get; }

:cs:meth:`plain <C.Foo>`, :cs:meth:`int <C.Foo(int)>`, :cs:meth:`ref <C.Foo(ref int, Dictionary<string, int>)>`,
:cs:meth:`generic <C.Foo<T>(T)>`, :cs:meth:`string <C.op_Implicit(C)~string>`, :cs:idxr:`indexer <C.this[]>`,
:cs:idxr:`key <C.this[string]>`, :any:`any <C.Foo>`, :cs:meth:`tuple <C.Foo((int, string))>`,
:cs:meth:`pair <C.op_Implicit(C)~(int, int)>`
'''


def test_overloads(build):
    app = build(OVERLOADS_SOURCE)
    assert warnings(app) == []
    assert set(signatures(app)) == {
        'class-C', 'function-C.Foo', 'function-C.Foo(int)', 'function-C.Foo(ref-int,Dictionary<string,int>)',
        'function-C.Foo<T>(T)', 'function-C.Foo((int,string))', 'function-C.op_Implicit',
        'function-C.op_Implicit(C)~int', 'function-C.op_Implicit(C)~string', 'function-C.op_Implicit(C)~(int,int)',
        'indexer-C.this[]', 'indexer-C.this[int]', 'indexer-C.this[string]'}
    assert signatures(app)['function-C.Foo'] == 'void Foo (int a)'
    assert references(app).items() >= {
        'plain': 'function-C.Foo', 'int': 'function-C.Foo(int)',
        'ref': 'function-C.Foo(ref-int,Dictionary<string,int>)', 'generic': 'function-C.Foo<T>(T)',
        'string': 'function-C.op_Implicit(C)~string', 'indexer': 'indexer-C.this[]',
        'key': 'indexer-C.this[string]', 'any': 'function-C.Foo', 'tuple': 'function-C.Foo((int,string))',
        'pair': 'function-C.op_Implicit(C)~(int,int)'}.items()


def test_overloads_in_one_directive(build):
    app = build('.. cs:function:: void Foo (int a)\n'
                '                 void Foo (string a)\n\n'
                ':cs:meth:`plain <Foo>` and :cs:meth:`string <Foo(string)>`\n')
    assert warnings(app) == []
    assert set(signatures(app)) == {'function-Foo', 'function-Foo(int)', 'function-Foo(string)'}
    assert index_entries(app) == [('Foo (C# function)', 'function-Foo')]
    assert references(app).items() >= {'plain': 'function-Foo', 'string': 'function-Foo(string)'}.items()


def test_overloads_on_other_pages(build):
    pages = {'page1': 'Page 1\n======\n\n.. cs:function:: void Foo (int a)\n',
             'page2': 'Page 2\n======\n\n.. cs:function:: void Foo (string a)\n'}
    app = build('.. toctree::\n\n   page1\n   page2\n\n'
                ':cs:meth:`plain <Foo>` and :cs:meth:`string <Foo(string)>`\n', pages=pages)
    assert warnings(app) == []
    assert references(app).items() >= {'plain': 'page1.html#function-Foo',
                                       'string': 'page2.html#function-Foo(string)'}.items()


def test_duplicate_overload(build):
    app = build('.. toctree::\n\n   page\n\n.. cs:function:: void Foo (int a)\n',
                pages={'page': 'Page\n====\n\n.. cs:function:: void Foo (int b)\n'})
    assert len(warnings(app)) == 1
    assert 'duplicate description of function Foo(int)' in warnings(app)[0]


def test_overloads_in_inventory(build):
    app = build('.. cs:function:: void Foo (int a)\n\n.. cs:function:: void Bar (int a)\n\n'
                '.. cs:function:: void Bar (string a)\n')
    assert sorted(app.env.get_domain('cs').get_objects()) == [
        ('Bar', 'Bar', 'function', 'index', 'function-Bar', -1),
        ('Bar(int)', 'Bar(int)', 'function', 'index', 'function-Bar(int)', 1),
        ('Bar(string)', 'Bar(string)', 'function', 'index', 'function-Bar(string)', 1),
        ('Foo', 'Foo', 'function', 'index', 'function-Foo', 1),
        ('Foo(int)', 'Foo(int)', 'function', 'index', 'function-Foo(int)', -1)]


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
