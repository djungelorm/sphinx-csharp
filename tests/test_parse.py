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


def test_split_sig():
    assert split_sig('String a, int b = 1, List<int> c = [1, 2, 3], Dictionary<string, int> d') == [
        'String a', 'int b = 1', 'List<int> c = [1, 2, 3]', 'Dictionary<string, int> d']


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
    ('int Foo(params int[] xs)', ([], 'int', 'Foo', [], [param('int[]', 'xs', modifiers=['params'])])),
])
def test_parse_method(sig, expected):
    assert parse_method_signature(sig, None) == expected


def test_parse_method_doxygen_template():
    assert parse_method_signature('template<T> void Foo(T a)', None) == ([], 'void', 'Foo', ['T'], [param('T', 'a')])


@pytest.mark.parametrize('sig, expected', [
    ('string P { get; set; }', ([], 'string', 'P', True, True, None)),
    ('static string P { get; }', (['static'], 'string', 'P', True, False, None)),
    ('int? P { get; set; }', ([], 'int?', 'P', True, True, None)),
    ('public int[,] P { get; }', (['public'], 'int[,]', 'P', True, False, None)),
    ('List<int> P { get; set; } = new List<int>()', ([], 'List<int>', 'P', True, True, 'new List<int>()')),
    ('Dictionary<string, int> P { get; }', ([], 'Dictionary<string, int>', 'P', True, False, None)),
    ('public virtual int P { set; }', (['public', 'virtual'], 'int', 'P', False, True, None)),
    ('public required string P { get; set; }', (['public', 'required'], 'string', 'P', True, True, None)),
    ('int P', ([], 'int', 'P', False, False, None)),
    ('int P = 1', ([], 'int', 'P', False, False, '1')),
])
def test_parse_property(sig, expected):
    assert parse_property_signature(sig, None) == expected


@pytest.mark.parametrize('sig, expected', [
    ('private int a = 0', (['private'], 'int', 'int', [], 'a', '0')),
    ('static const List<MyInterface> GenericVar',
     (['static', 'const'], 'List<MyInterface>', 'List', ['MyInterface'], 'GenericVar', None)),
    ('MyEnum? e', ([], 'MyEnum?', 'MyEnum', [], 'e', None)),
    ('int[,] grid', ([], 'int[,]', 'int', [], 'grid', None)),
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
    ('Foo*', ('Foo', [], [], [], '', '*')),
    ('template<T> Bar', ('Bar', [], ['T'], [], '', None)),
])
def test_parse_type(sig, expected):
    assert parse_type_signature(sig, None) == expected


@pytest.mark.parametrize('sig, expected', [
    ('string this[int i] { get; set; }', ([], 'string', [param('int', 'i')], True, True)),
    ('virtual string this[int i, MyClass j] { get; }',
     (['virtual'], 'string', [param('int', 'i'), param('MyClass', 'j')], True, False)),
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
    (parse_method_signature, '(int, string) Foo()'),
    (parse_method_signature, 'void Foo(int)'),
    (parse_property_signature, 'int'),
    (parse_variable_signature, 'int'),
    (parse_indexer_signature, 'string this[] { get; }'),
    (parse_type_signature, '<T>'),
    (parse_type_signature, None),
    (parse_attr_signature, 'A B C'),
])
def test_parse_invalid(parse, sig):
    with pytest.raises(ValueError, match='signature invalid'):
        parse(sig, None)
