import pytest

from sphinx_csharp.csharp import (
    ParamTuple,
    parse_attr_signature,
    parse_indexer_signature,
    parse_method_signature,
    parse_property_signature,
    parse_type_signature,
    parse_variable_signature,
    split_sig,
)


def param(typ, name, default=None, modifiers=()):
    return ParamTuple(name=name, typ=typ, default=default, modifiers=list(modifiers))


@pytest.mark.parametrize('params, expected', [
    ('String a, int b = 1, List<int> c = [1, 2, 3], Dictionary<string, int> d',
     ['String a', 'int b = 1', 'List<int> c = [1, 2, 3]', 'Dictionary<string, int> d']),
    ('a,', ['a']),
    ('a>, b', ['a>', 'b']),
    ('(int, string) a, Foo b = new Foo(1, 2)', ['(int, string) a', 'Foo b = new Foo(1, 2)']),
])
def test_split_sig(params, expected):
    assert split_sig(params) == expected


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
    ('byte[][] Foo(out byte[][] d)', ([], 'byte[][]', 'Foo', [], [param('byte[][]', 'd', modifiers=['out'])])),
    ('static void Ext(this string s)', (['static'], 'void', 'Ext', [], [param('string', 's', modifiers=['this'])])),
    ('(int, string) Foo((int a, string b) t)',
     ([], '(int, string)', 'Foo', [], [param('(int a, string b)', 't')])),
    ('Task<(int, int)> Foo(List<(int, int)>? l)',
     ([], 'Task<(int, int)>', 'Foo', [], [param('List<(int, int)>?', 'l')])),
    ('(int x, (int y, int z) inner)[] Foo()', ([], '(int x, (int y, int z) inner)[]', 'Foo', [], [])),
    ('int Foo(params int[] xs)', ([], 'int', 'Foo', [], [param('int[]', 'xs', modifiers=['params'])])),
])
def test_parse_method(sig, expected):
    assert parse_method_signature(sig, None) == expected


def test_parse_method_doxygen_template():
    assert parse_method_signature('template<T> void Foo(T a)', None) == ([], 'void', 'Foo', ['T'], [param('T', 'a')])


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
])
def test_parse_variable(sig, expected):
    assert parse_variable_signature(sig, None) == expected


@pytest.mark.parametrize('sig, expected', [
    ('MyClass', ('MyClass', [], [], [], '', None)),
    ('public sealed MyClass<T, U> : Base, IFoo',
     ('MyClass', ['public', 'sealed'], ['T', 'U'], ['Base', 'IFoo'], '', None)),
    ('List<int>', ('List', [], ['int'], [], '', None)),
    ('int[,]', ('int', [], [], [], '[,]', None)),
    ('int?', ('int', [], [], [], '', '?')),
    ('(int, string)?', ('(int, string)', [], [], [], '', '?')),
    ('Foo*', ('Foo', [], [], [], '', '*')),
    ('template<T> Bar', ('Bar', [], ['T'], [], '', None)),
])
def test_parse_type(sig, expected):
    assert parse_type_signature(sig, None) == expected


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
    ('int this[int i]', ([], 'int', None, [param('int', 'i')], [])),
    ('string this[string s, int j=0] {get;}',
     ([], 'string', None, [param('string', 's'), param('int', 'j', '0')], ['get'])),
])
def test_parse_indexer(sig, expected):
    assert parse_indexer_signature(sig, None) == expected


@pytest.mark.parametrize('sig, expected', [
    ('MyAttr', ('MyAttr', [])),
    ('MyAttr (string a, int b)', ('MyAttr', [param('string', 'a'), param('int', 'b')])),
])
def test_parse_attribute(sig, expected):
    assert parse_attr_signature(sig, None) == expected


@pytest.mark.parametrize('parse, sig', [
    (parse_method_signature, '(int, string Foo()'),
    (parse_method_signature, 'void Foo(int)'),
    (parse_property_signature, 'int'),
    (parse_variable_signature, 'int'),
    (parse_indexer_signature, 'string this[] { get; }'),
    (parse_indexer_signature, 'string this[int] { get; }'),
    (parse_indexer_signature, 'string this[int i] { fetch; }'),
    (parse_property_signature, 'int P { get }'),
    (parse_type_signature, '<T>'),
    (parse_type_signature, None),
    (parse_attr_signature, 'A B C'),
])
def test_parse_invalid(parse, sig):
    with pytest.raises(ValueError, match='signature invalid'):
        parse(sig, None)
