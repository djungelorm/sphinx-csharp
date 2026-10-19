import pytest

from sphinx_csharp.lexer import tokenize
from sphinx_csharp.parser import (
    Constraint,
    MethodSig,
    ParamTuple,
    TypeSig,
    parse_attr_signature,
    parse_base_type,
    parse_enum_signature,
    parse_enumerator_signature,
    parse_indexer_signature,
    parse_method_signature,
    parse_property_signature,
    parse_record_kind,
    parse_tuple_element,
    parse_type_as_function,
    parse_type_signature,
    parse_variable_signature,
    split_sig,
)


def param(typ, name, default=None, modifiers=()):
    return ParamTuple(name=name, typ=typ, default=default, modifiers=list(modifiers))


@pytest.mark.parametrize('sig, expected', [
    ('List<int>? x', ['List', '<', 'int', '>', '?', 'x']),
    ('global::N.C a=>b', ['global', '::', 'N', '.', 'C', 'a', '=>', 'b']),
    ('@class 1.5f', ['@class', '1', '.', '5f']),
    ('"a\\"b" \'\\\'\' x', ['"a\\"b"', "'\\''", 'x']),
    ('@"C:\\""x""" y', ['@"C:\\""x"""', 'y']),
    ('"abc', ['"abc']),
])
def test_tokenize(sig, expected):
    assert [token.text for token in tokenize(sig)] == expected


@pytest.mark.parametrize('params, expected', [
    ('String a, int b = 1, List<int> c = [1, 2, 3], Dictionary<string, int> d',
     ['String a', 'int b = 1', 'List<int> c = [1, 2, 3]', 'Dictionary<string, int> d']),
    ('a,', ['a']),
    ('a>, b', ['a>', 'b']),
    ('(int, string) a, Foo b = new Foo(1, 2)', ['(int, string) a', 'Foo b = new Foo(1, 2)']),
    ('string a = "x, <y", char b = \',\', int c', ['string a = "x, <y"', "char b = ','", 'int c']),
    ('string a = "\\", b", int c', ['string a = "\\", b"', 'int c']),
    ("char a = '\\'', int b", ["char a = '\\''", 'int b']),
])
def test_split_sig(params, expected):
    assert split_sig(params) == expected


@pytest.mark.parametrize('element, expected', [
    ('int count', ('int', 'count')),
    ('List<int>', ('List<int>', None)),
    ('', None),
])
def test_parse_tuple_element(element, expected):
    assert parse_tuple_element(element) == expected


@pytest.mark.parametrize('base, expected', [
    ('IDisposable', ('IDisposable', None)),
    ('IBase< T >', ('IBase< T >', None)),
    ('Base(x, y)', ('Base', '(x, y)')),
])
def test_parse_base_type(base, expected):
    assert parse_base_type(base) == expected


@pytest.mark.parametrize('sig, expected', [
    ('public class Point(int X)', (['public'], 'class', 'Point(int X)')),
    ('struct Point', ([], 'struct', 'Point')),
    ('Point(int X)', None),
    ('class', None),
])
def test_parse_record_kind(sig, expected):
    assert parse_record_kind(sig) == expected


@pytest.mark.parametrize('sig, expected', [
    ('record struct Point<T>(T X)', ([], 'record struct', 'Point<T>(T X)')),
    ('public record N.Box<T> (T X)', (['public'], 'record', 'N.Box<T> (T X)')),
    ('class Service(ILogger logger)', ([], 'class', 'Service(ILogger logger)')),
    ('record Point', None),
    ('void Foo()', None),
])
def test_parse_type_as_function(sig, expected):
    assert parse_type_as_function(sig) == expected


@pytest.mark.parametrize('sig, expected', [
    ('void Foo()', ([], 'void', 'Foo', [], [])),
    ('public static int Foo(int a, string b = "x")',
     (['public', 'static'], 'int', 'Foo', [], [param('int', 'a'), param('string', 'b', '"x"')])),
    ('MyClass(string a, int b = 1)', ([], None, 'MyClass', [], [param('string', 'a'), param('int', 'b', '1')])),
    ('T Get<T>(int x)', ([], 'T', 'Get', ['T'], [param('int', 'x')])),
    ('List<Dictionary<string, int>> Foo(ref List<T> a = default)',
     ([], 'List<Dictionary<string, int>>', 'Foo', [], [param('List<T>', 'a', 'default', ['ref'])])),
    ('int? Foo(MyClass? b)', ([], 'int?', 'Foo', [], [param('MyClass?', 'b')])),
    ('int[,] Foo(int[,,] a)', ([], 'int[,]', 'Foo', [], [param('int[,,]', 'a')])),
    ('int?[] Foo(int** p, string?[]? s)',
     ([], 'int?[]', 'Foo', [], [param('int**', 'p'), param('string?[]?', 's')])),
    ('byte[][] Foo(out byte[][] d)', ([], 'byte[][]', 'Foo', [], [param('byte[][]', 'd', modifiers=['out'])])),
    ('static void Ext(this string s)', (['static'], 'void', 'Ext', [], [param('string', 's', modifiers=['this'])])),
    ('(int, string) Foo((int a, string b) t)',
     ([], '(int, string)', 'Foo', [], [param('(int a, string b)', 't')])),
    ('Task<(int, int)> Foo(List<(int, int)>? l)',
     ([], 'Task<(int, int)>', 'Foo', [], [param('List<(int, int)>?', 'l')])),
    ('(int x, (int y, int z) inner)[] Foo()', ([], '(int x, (int y, int z) inner)[]', 'Foo', [], [])),
    ('bool Try([NotNullWhen(true)] out string? s, [CallerMemberName] string name="")',
     ([], 'bool', 'Try', [], [param('string?', 's', modifiers=['[NotNullWhen(true)]', 'out']),
                              param('string', 'name', '""', ['[CallerMemberName]'])])),
    ('void Span(scoped ref int a, ref readonly int b, scoped Span< int > c)',
     ([], 'void', 'Span', [], [param('int', 'a', modifiers=['scoped', 'ref']),
                               param('int', 'b', modifiers=['ref', 'readonly']),
                               param('Span< int >', 'c', modifiers=['scoped'])])),
    ('file void Foo()', (['file'], 'void', 'Foo', [], [])),
    ('void Foo(string s = "a, b", char c = \',\')',
     ([], 'void', 'Foo', [], [param('string', 's', '"a, b"'), param('char', 'c', "','")])),
    ('int Foo(params int[] xs)', ([], 'int', 'Foo', [], [param('int[]', 'xs', modifiers=['params'])])),
    ('void Foo(KeyValuePair<int, int> p = new KeyValuePair<int, int>(), int f = 1 << 2 >> 1)',
     ([], 'void', 'Foo', [], [param('KeyValuePair<int, int>', 'p', 'new KeyValuePair<int, int>()'),
                              param('int', 'f', '1 << 2 >> 1')])),
    ('void Foo(int a = 1 << 2, bool b = 1 > 0, int c = x < y ? 1 : 2, bool d = x < y)',
     ([], 'void', 'Foo', [], [param('int', 'a', '1 << 2'), param('bool', 'b', '1 > 0'),
                              param('int', 'c', 'x < y ? 1 : 2'), param('bool', 'd', 'x < y')])),
    ('~MyClass()', ([], None, '~MyClass', [], [])),
    ('((int, (int, int)), int) Foo()', ([], '((int, (int, int)), int)', 'Foo', [], [])),
    ('void Foo([A(X[Y[0]])] int a)', ([], 'void', 'Foo', [], [param('int', 'a', modifiers=['[A(X[Y[0]])]'])])),
    ('void Foo(string s = @"C:\\", int b)',
     ([], 'void', 'Foo', [], [param('string', 's', '@"C:\\"'), param('int', 'b')])),
    ('void Foo([DefaultValue(new[] {1})] int[] a, [Attr("]", \'[\')] int b)',
     ([], 'void', 'Foo', [], [param('int[]', 'a', modifiers=['[DefaultValue(new[] {1})]']),
                              param('int', 'b', modifiers=['[Attr("]", \'[\')]'])])),
])
def test_parse_method(sig, expected):
    assert parse_method_signature(sig, None) == MethodSig(*expected, constraints=[], operator=None)


@pytest.mark.parametrize('sig, expected', [
    ('public static V operator +(V a, V b)', (['public', 'static'], 'V', 'op_Addition', 'operator +', 2)),
    ('static V operator-(V a)', (['static'], 'V', 'op_UnaryNegation', 'operator -', 1)),
    ('static V operator - (V a, V b)', (['static'], 'V', 'op_Subtraction', 'operator -', 2)),
    ('static bool operator ==(V a, V b)', (['static'], 'bool', 'op_Equality', 'operator ==', 2)),
    ('static bool operator<=(V a, V b)', (['static'], 'bool', 'op_LessThanOrEqual', 'operator <=', 2)),
    ('static V operator >>>(V a, int b)', (['static'], 'V', 'op_UnsignedRightShift', 'operator >>>', 2)),
    ('static bool operator true(V a)', (['static'], 'bool', 'op_True', 'operator true', 1)),
    ('static V operator checked +(V a, V b)', (['static'], 'V', 'op_CheckedAddition', 'operator checked +', 2)),
    ('static V operator ++(V a)', (['static'], 'V', 'op_Increment', 'operator ++', 1)),
    ('void operator ++()', ([], 'void', 'op_IncrementAssignment', 'operator ++', 0)),
    ('void operator +=(V b)', ([], 'void', 'op_AdditionAssignment', 'operator +=', 1)),
    ('void operator >>>=(int b)', ([], 'void', 'op_UnsignedRightShiftAssignment', 'operator >>>=', 1)),
    ('public static implicit operator int(V a)',
     (['public', 'static', 'implicit'], 'int', 'op_Implicit', 'operator', 1)),
    ('static explicit operator checked V(int a)',
     (['static', 'explicit'], 'V', 'op_CheckedExplicit', 'operator checked', 1)),
    ('static explicit operator List<int>(V a)', (['static', 'explicit'], 'List<int>', 'op_Explicit', 'operator', 1)),
    # Doxygen drops explicit, and writes implicit in place of the return type
    (' V operator+ (V a, V b)', ([], 'V', 'op_Addition', 'operator +', 2)),
    ('static operator V (int a)', (['static', 'explicit'], 'V', 'op_Explicit', 'operator', 1)),
    ('implicit operator int (V a)', (['implicit'], 'int', 'op_Implicit', 'operator', 1)),
])
def test_parse_operator(sig, expected):
    result = parse_method_signature(sig, None)
    assert (result.modifiers, result.return_type, result.name, result.operator, len(result.params)) == expected


def test_parse_method_doxygen_template():
    assert parse_method_signature('template<T> void Foo(T a)', None) == \
        MethodSig([], 'void', 'Foo', ['T'], [param('T', 'a')], [], None)


@pytest.mark.parametrize('sig, expected', [
    ('T Foo<T>(T x) where T : notnull', [Constraint('T', ['notnull'])]),
    ('void Foo<T, U>(T a, U b = default) where T : class, new() where U : IComparable<U>, IFoo',
     [Constraint('T', ['class', 'new()']), Constraint('U', ['IComparable<U>', 'IFoo'])]),
    ('void Foo<T>(Func<T> f = null) where T : Dictionary<string, (int, int)>',
     [Constraint('T', ['Dictionary<string, (int, int)>'])]),
    ('void Foo<T>() where T : allows  ref struct', [Constraint('T', ['allows ref struct'])]),
])
def test_parse_method_constraints(sig, expected):
    assert parse_method_signature(sig, None).constraints == expected


@pytest.mark.parametrize('sig, expected', [
    ('string P { get; set; }', ([], 'string', 'P', ['get', 'set'], None)),
    ('(int a, int b) P { get; }', ([], '(int a, int b)', 'P', ['get'], None)),
    ('static string P { get; }', (['static'], 'string', 'P', ['get'], None)),
    ('int? P { get; set; }', ([], 'int?', 'P', ['get', 'set'], None)),
    ('public int[,] P { get; }', (['public'], 'int[,]', 'P', ['get'], None)),
    ('List<int> P { get; set; } = new List<int>()', ([], 'List<int>', 'P', ['get', 'set'], 'new List<int>()')),
    ('Dictionary<string, int> P { get; }', ([], 'Dictionary<string, int>', 'P', ['get'], None)),
    ('public virtual int P { set; }', (['public', 'virtual'], 'int', 'P', ['set'], None)),
    ('public required string P { get; set; }', (['public', 'required'], 'string', 'P', ['get', 'set'], None)),
    ('int P {get;set;}', ([], 'int', 'P', ['get', 'set'], None)),
    ('int P { get; init; }', ([], 'int', 'P', ['get', 'init'], None)),
    ('int P { get; private set; }', ([], 'int', 'P', ['get', 'private set'], None)),
    ('int P { protected  internal get; set; }', ([], 'int', 'P', ['protected internal get', 'set'], None)),
    ('int P { readonly get; }', ([], 'int', 'P', ['readonly get'], None)),
    ('int P { set; get; }', ([], 'int', 'P', ['set', 'get'], None)),
    ('int P { get; set; } = 5;', ([], 'int', 'P', ['get', 'set'], '5')),
    ('int P => 1', ([], 'int', 'P', ['get'], None)),
    ('int P => x > 0;', ([], 'int', 'P', ['get'], None)),
    ('EventHandler E { add; remove; }', ([], 'EventHandler', 'E', ['add', 'remove'], None)),
    ('int P', ([], 'int', 'P', [], None)),
    ('int P = 1', ([], 'int', 'P', [], '1')),
    ('int P;', ([], 'int', 'P', [], None)),
])
def test_parse_property(sig, expected):
    assert parse_property_signature(sig, None) == expected


@pytest.mark.parametrize('sig, expected', [
    ('private int a = 0', (['private'], 'int', 'int', [], 'a', '0')),
    ('static const List<MyInterface> GenericVar',
     (['static', 'const'], 'List<MyInterface>', 'List', ['MyInterface'], 'GenericVar', None)),
    ('MyEnum? e', ([], 'MyEnum?', 'MyEnum', [], 'e', None)),
    ('int[,] grid', ([], 'int[,]', 'int', [], 'grid', None)),
    ('static readonly (int, int) T', (['static', 'readonly'], '(int, int)', '(int, int)', [], 'T', None)),
    ('template<T> T x', ([], 'T', 'T', ['T'], 'x', None)),
    ('int x;', ([], 'int', 'int', [], 'x', None)),
])
def test_parse_variable(sig, expected):
    assert parse_variable_signature(sig, None) == expected


@pytest.mark.parametrize('sig, expected', [
    ('MyClass', ('MyClass', [], [], [], '')),
    ('file sealed MyClass', ('MyClass', ['file', 'sealed'], [], [], '')),
    ('public sealed MyClass<T, U> : Base, IFoo', ('MyClass', ['public', 'sealed'], ['T', 'U'], ['Base', 'IFoo'], '')),
    ('List<int>', ('List', [], ['int'], [], '')),
    ('int[,]', ('int', [], [], [], '[,]')),
    ('int?', ('int', [], [], [], '?')),
    ('(int, string)?', ('(int, string)', [], [], [], '?')),
    ('Foo*', ('Foo', [], [], [], '*')),
    ('int**', ('int', [], [], [], '**')),
    ('int?[]', ('int', [], [], [], '?[]')),
    ('string?[]?', ('string', [], [], [], '?[]?')),
    ('List<int> [] []', ('List', [], ['int'], [], '[][]')),
    ('template<T> Bar', ('Bar', [], ['T'], [], '')),
    ('template<T> Box-1-g', ('Box', [], ['T'], [], '')),
    ('Outer-2-g.Inner-1-g<U>', ('Outer.Inner', [], ['U'], [], '')),
    ('(int, (int, (int, int)))?', ('(int, (int, (int, int)))', [], [], [], '?')),
])
def test_parse_type(sig, expected):
    assert parse_type_signature(sig, None) == TypeSig(*expected, constraints=[], params=None, nested=[])


@pytest.mark.parametrize('sig, expected', [
    ('MyClass<T> where T : IFoo', ('MyClass', [], ['T'], [], '', [Constraint('T', ['IFoo'])])),
    ('MyClass<T> where T : IComparable<T>',
     ('MyClass', [], ['T'], [], '', [Constraint('T', ['IComparable<T>'])])),
    ('MyClass<T, U> : Base<T>, IFoo where T : new() where U : struct',
     ('MyClass', [], ['T', 'U'], ['Base<T>', 'IFoo'], '',
      [Constraint('T', ['new()']), Constraint('U', ['struct'])])),
])
def test_parse_type_constraints(sig, expected):
    assert parse_type_signature(sig, None) == TypeSig(*expected, params=None, nested=[])


@pytest.mark.parametrize('sig, expected', [
    ('List<int>.Enumerator', ('List', ['int'], ['Enumerator'], '')),
    ('Outer<T>.Middle.Inner<U, V>[]', ('Outer', ['T'], ['Middle', 'Inner<U, V>'], '[]')),
    ('Dictionary< string, List<int> > . KeyCollection?',
     ('Dictionary', ['string', 'List<int>'], ['KeyCollection'], '?')),
])
def test_parse_nested_type(sig, expected):
    result = parse_type_signature(sig, None)
    assert (result.typ, result.generics, result.nested, result.suffix) == expected


@pytest.mark.parametrize('sig, expected', [
    ('Point(int X, int Y)', [param('int', 'X'), param('int', 'Y')]),
    ('Empty()', []),
    ('Named<T>(T Name) : Base(Name), IFoo where T : notnull', [param('T', 'Name')]),
    ('Service(ILogger<Service> logger, int timeout = 30)',
     [param('ILogger<Service>', 'logger'), param('int', 'timeout', '30')]),
])
def test_parse_primary_constructor(sig, expected):
    assert parse_type_signature(sig, None).params == expected


@pytest.mark.parametrize('sig, expected', [
    ('string this[int i] { get; set; }', ([], 'string', None, [param('int', 'i')], ['get', 'set'])),
    ('virtual string this[int i, MyClass j] { get; }',
     (['virtual'], 'string', None, [param('int', 'i'), param('MyClass', 'j')], ['get'])),
    ('string this[int i] { get; private init; }', ([], 'string', None, [param('int', 'i')], ['get', 'private init'])),
    ('Dictionary<string, int> this[List<int> a, Dictionary<string, int> b] { get; }',
     ([], 'Dictionary<string, int>', None, [param('List<int>', 'a'), param('Dictionary<string, int>', 'b')], ['get'])),
    ('int this[params int[] i] { get; }', ([], 'int', None, [param('int[]', 'i', modifiers=['params'])], ['get'])),
    ('int this[in int i, int j = 0] { get; }',
     ([], 'int', None, [param('int', 'i', modifiers=['in']), param('int', 'j', '0')], ['get'])),
    ('int? this[int i] { get; }', ([], 'int?', None, [param('int', 'i')], ['get'])),
    ('ref int this[int i] { get; }', (['ref'], 'int', None, [param('int', 'i')], ['get'])),
    ('int IList<int>.this[int i] { get; }', ([], 'int', 'IList<int>', [param('int', 'i')], ['get'])),
    ('int this[int i] => i;', ([], 'int', None, [param('int', 'i')], ['get'])),
    ('int this[[A(X[0])] int[] i] { get; }',
     ([], 'int', None, [param('int[]', 'i', modifiers=['[A(X[0])]'])], ['get'])),
    ('int this[int i] => items[i];', ([], 'int', None, [param('int', 'i')], ['get'])),
    ('int this[[NotNull] int[] i] => i[0];',
     ([], 'int', None, [param('int[]', 'i', modifiers=['[NotNull]'])], ['get'])),
    ('int this[int i]', ([], 'int', None, [param('int', 'i')], [])),
    ('string this[string s, int j=0] {get;}',
     ([], 'string', None, [param('string', 's'), param('int', 'j', '0')], ['get'])),
])
def test_parse_indexer(sig, expected):
    assert parse_indexer_signature(sig, None) == expected


@pytest.mark.parametrize('sig, expected', [
    ('Color', ([], 'Color', None)),
    ('public Color : byte', (['public'], 'Color', 'byte')),
    ('internal Flags:System.UInt16', (['internal'], 'Flags', 'System.UInt16')),
    ('Outer< T >.Color', ([], 'Outer<T>.Color', None)),
])
def test_parse_enum(sig, expected):
    assert parse_enum_signature(sig, None) == expected


@pytest.mark.parametrize('sig, expected', [
    ('Red', ('Red', None)),
    ('Red = 1', ('Red', '1')),
    ('All=Red | Green', ('All', 'Red | Green')),
    ('Color.Red = 1', ('Color.Red', '1')),
])
def test_parse_enumerator(sig, expected):
    assert parse_enumerator_signature(sig, None) == expected


@pytest.mark.parametrize('sig, expected', [
    ('MyAttr', ('MyAttr', [])),
    ('MyAttr (string a, int b)', ('MyAttr', [param('string', 'a'), param('int', 'b')])),
    ('Obsolete(string message, bool error = false)',
     ('Obsolete', [param('string', 'message'), param('bool', 'error', 'false')])),
    ('MyAttr<T>(T a)', ('MyAttr<T>', [param('T', 'a')])),
])
def test_parse_attribute(sig, expected):
    assert parse_attr_signature(sig, None) == expected


@pytest.mark.parametrize('parse, sig', [
    (parse_method_signature, '(int, string Foo()'),
    (parse_method_signature, 'void Foo(int)'),
    (parse_method_signature, 'V operator =(V a)'),
    (parse_method_signature, 'T Foo<T(int a)'),
    (parse_method_signature, 'void Foo(int a = )'),
    (parse_method_signature, 'C(int a) : Foo(a)'),
    (parse_variable_signature, 'int[3] x'),
    (parse_variable_signature, 'int x ='),
    (parse_property_signature, 'int'),
    (parse_variable_signature, 'int'),
    (parse_indexer_signature, 'string this[] { get; }'),
    (parse_indexer_signature, 'string this[int] { get; }'),
    (parse_indexer_signature, 'string this[int i] { fetch; }'),
    (parse_property_signature, 'int P { get }'),
    (parse_type_signature, '<T>'),
    (parse_type_signature, None),
    (parse_type_signature, 'MyClass<T> where T'),
    (parse_method_signature, 'void Foo<T>() where : IFoo'),
    (parse_attr_signature, 'A B C'),
    (parse_enum_signature, 'Color Shade'),
    (parse_enumerator_signature, '= 1'),
])
def test_parse_invalid(parse, sig):
    with pytest.raises(ValueError, match='signature invalid'):
        parse(sig, None)
