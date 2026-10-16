import pytest

from sphinx_csharp.csharp import (
    Constraint,
    MethodSig,
    ParamTuple,
    TypeSig,
    parse_attr_signature,
    parse_enum_signature,
    parse_enumerator_signature,
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
    ('int?[] Foo(int** p, string?[]? s)',
     ([], 'int?[]', 'Foo', [], [param('int**', 'p'), param('string?[]?', 's')])),
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
    ('MyClass', ('MyClass', [], [], [], '')),
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
])
def test_parse_type(sig, expected):
    assert parse_type_signature(sig, None) == TypeSig(*expected, constraints=[], params=None)


@pytest.mark.parametrize('sig, expected', [
    ('MyClass<T> where T : IFoo', ('MyClass', [], ['T'], [], '', [Constraint('T', ['IFoo'])])),
    ('MyClass<T> where T : IComparable<T>',
     ('MyClass', [], ['T'], [], '', [Constraint('T', ['IComparable<T>'])])),
    ('MyClass<T, U> : Base<T>, IFoo where T : new() where U : struct',
     ('MyClass', [], ['T', 'U'], ['Base<T>', 'IFoo'], '',
      [Constraint('T', ['new()']), Constraint('U', ['struct'])])),
])
def test_parse_type_constraints(sig, expected):
    assert parse_type_signature(sig, None) == TypeSig(*expected, params=None)


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
])
def test_parse_enum(sig, expected):
    assert parse_enum_signature(sig, None) == expected


@pytest.mark.parametrize('sig, expected', [
    ('Red', ('Red', None)),
    ('Red = 1', ('Red', '1')),
    ('All=Red | Green', ('All', 'Red | Green')),
])
def test_parse_enumerator(sig, expected):
    assert parse_enumerator_signature(sig, None) == expected


@pytest.mark.parametrize('sig, expected', [
    ('MyAttr', ('MyAttr', [])),
    ('MyAttr (string a, int b)', ('MyAttr', [param('string', 'a'), param('int', 'b')])),
])
def test_parse_attribute(sig, expected):
    assert parse_attr_signature(sig, None) == expected


@pytest.mark.parametrize('parse, sig', [
    (parse_method_signature, '(int, string Foo()'),
    (parse_method_signature, 'void Foo(int)'),
    (parse_method_signature, 'V operator =(V a)'),
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
