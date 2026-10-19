""" C# signature parser """

import functools
from collections.abc import Callable
from typing import NamedTuple, TypeVar

from docutils import nodes
from sphinx.util import logging

from .debug import CSDebug
from .lexer import Token, tokenize

MODIFIERS = {'public', 'private', 'internal', 'protected', 'abstract', 'async', 'const', 'event', 'delegate', 'extern',
             'new', 'override', 'partial', 'readonly', 'required', 'sealed', 'static', 'unsafe', 'virtual', 'volatile',
             'ref', 'implicit', 'explicit', 'file', 'fixed'}
PARAM_MODIFIERS = {'this', 'ref', 'in', 'out', 'params', 'scoped', 'readonly'}
ACCESSOR_MODIFIERS = {'public', 'private', 'protected', 'internal', 'readonly'}
ACCESSORS = {'get', 'set', 'init', 'add', 'remove'}
# Breathe writes the access level of each base type, as in public IDisposable
BASE_ACCESS = {'public', 'protected', 'private', 'internal', 'virtual'}
CONSTRAINT_KEYWORDS = ['class', 'class?', 'struct', 'notnull', 'unmanaged', 'default', 'new()', 'allows ref struct']

OPENING = {'(', '[', '{'}
CLOSING = {')', ']', '}'}
# The punctuation that can appear in generic arguments, as in Dictionary<string, (int, int?)[]>
TYPE_PUNCTUATION = {'<', '>', ',', '.', '::', '?', '*', '(', ')', '[', ']'}

# Operators, named by their .NET metadata names such as op_Addition
OPERATOR_NAMES = {
    '+': 'Addition', '-': 'Subtraction', '*': 'Multiply', '/': 'Division', '%': 'Modulus',
    '&': 'BitwiseAnd', '|': 'BitwiseOr', '^': 'ExclusiveOr',
    '<<': 'LeftShift', '>>': 'RightShift', '>>>': 'UnsignedRightShift',
    '==': 'Equality', '!=': 'Inequality', '<': 'LessThan', '>': 'GreaterThan',
    '<=': 'LessThanOrEqual', '>=': 'GreaterThanOrEqual',
    '!': 'LogicalNot', '~': 'OnesComplement', '++': 'Increment', '--': 'Decrement', 'true': 'True', 'false': 'False',
    '+=': 'AdditionAssignment', '-=': 'SubtractionAssignment', '*=': 'MultiplicationAssignment',
    '/=': 'DivisionAssignment', '%=': 'ModulusAssignment', '&=': 'BitwiseAndAssignment',
    '|=': 'BitwiseOrAssignment', '^=': 'ExclusiveOrAssignment', '<<=': 'LeftShiftAssignment',
    '>>=': 'RightShiftAssignment', '>>>=': 'UnsignedRightShiftAssignment',
}
# The characters of operator symbols, which the tokenizer returns one at a time
OPERATOR_CHARS = set('+-*/%&|^!~<>=')
# Operators with these symbols and a single parameter are unary
UNARY_OPERATOR_NAMES = {'+': 'UnaryPlus', '-': 'UnaryNegation'}
# Instance increment and decrement operators have no parameters
INSTANCE_OPERATOR_NAMES = {'++': 'IncrementAssignment', '--': 'DecrementAssignment'}
CONVERSION_OPERATORS = ['op_Implicit', 'op_Explicit', 'op_CheckedImplicit', 'op_CheckedExplicit']

# The characters that whitespace around them is optional for, such as the space in Dictionary<string, int>
TIGHT_PUNCTUATION = set(',<>()[]*')
# The last characters of a tuple element type, before the element name, other than name characters
TUPLE_TYPE_END = set('>])?*')
# The parameter modifiers that overloads can differ by
OVERLOAD_PARAM_MODIFIERS = ['ref', 'out', 'in', 'readonly']

# Source location of a signature, as a (docname, line) pair, or the node of a doc field
Location = tuple[str, int] | nodes.Node | None

T = TypeVar('T')


class ParamTuple(NamedTuple):
    name: str
    typ: str
    default: str | None
    modifiers: list[str]


class Constraint(NamedTuple):
    param: str
    constraints: list[str]


class MethodSig(NamedTuple):
    modifiers: list[str]
    return_type: str | None
    name: str
    generic_params: list[str]
    params: list[ParamTuple]
    constraints: list[Constraint]
    # The operator as written, such as "operator +", or "operator" for a conversion
    operator: str | None
    # The constructor initializer, such as base(name)
    initializer: str | None = None


class VariableSig(NamedTuple):
    modifiers: list[str]
    fulltype: str
    typ: str
    generics: list[str]
    name: str
    default: str | None
    # The size of a fixed buffer, such as 16 in fixed byte Data[16]
    size: str | None = None


class PropertySig(NamedTuple):
    modifiers: list[str]
    typ: str
    name: str
    accessors: list[str]
    default: str | None


class IndexerSig(NamedTuple):
    modifiers: list[str]
    return_type: str
    interface: str | None
    params: list[ParamTuple]
    accessors: list[str]


class TypeSig(NamedTuple):
    typ: str
    modifiers: list[str]
    generics: list[str]
    inherits: list[str]
    suffix: str
    constraints: list[Constraint]
    # The primary constructor parameters, or None if the type has no primary constructor
    params: list[ParamTuple] | None
    nested: list[str]


class EnumSig(NamedTuple):
    modifiers: list[str]
    name: str
    base: str | None


class EnumeratorSig(NamedTuple):
    name: str
    value: str | None


class ExtensionSig(NamedTuple):
    generic_params: list[str]
    # The parameter of the type that the members extend, such as string s, with an empty name if it has none
    receiver: ParamTuple
    constraints: list[Constraint]


class AttrSig(NamedTuple):
    name: str
    params: list[ParamTuple]
    generic_params: list[str]


class ParsedType(NamedTuple):
    # The type as written, such as List< int >[]
    fulltype: str
    # The name before any generic arguments, such as List, or a tuple type
    name: str
    generics: list[str]
    # The types nested in a generic type, such as Enumerator in List<int>.Enumerator
    nested: list[str]
    # Nullable, pointer and array suffixes, such as ?[]
    suffix: str


logger = logging.getLogger(__name__)


class ParseError(Exception):
    """ A signature that does not match the grammar """


def is_name(token: Token | None) -> bool:
    """ Whether a token is a name or keyword """
    return token is not None and token.kind == 'word' and not token.text[0].isdigit()


def generic_arguments_end(tokens: list[Token], index: int) -> int | None:
    """
    The index after the generic arguments that the < at index opens, as in List<int>, or None if the < is an operator,
    as in 1 < 2. Generic arguments follow a name, and hold only names and type punctuation.
    """
    if index == 0 or not is_name(tokens[index - 1]):
        return None
    depth = 0
    for end in range(index, len(tokens)):
        token = tokens[end]
        depth += (token.text == '<') - (token.text == '>')
        if depth == 0:
            return end + 1
        if not is_name(token) and token.text not in TYPE_PUNCTUATION:
            return None
    return None


class Parser:
    """ A recursive descent parser over the tokens of a signature """

    def __init__(self, sig: str) -> None:
        self.sig = sig
        self.tokens = tokenize(sig)
        self.pos = 0

    def peek(self, offset: int = 0) -> Token | None:
        index = self.pos + offset
        return self.tokens[index] if index < len(self.tokens) else None

    def at(self, *texts: str, offset: int = 0) -> bool:
        """ Whether the next token, or the token at offset, is one of texts """
        token = self.peek(offset)
        return token is not None and token.text in texts

    def accept(self, text: str) -> bool:
        """ Skip the next token if it is text, and return whether it was """
        if self.at(text):
            self.pos += 1
            return True
        return False

    def expect(self, text: str) -> None:
        if not self.accept(text):
            raise ParseError

    def expect_end(self) -> None:
        if self.pos < len(self.tokens):
            raise ParseError

    def adjacent(self, offset: int = 0) -> bool:
        """ Whether the token at offset follows the previous token without whitespace """
        index = self.pos + offset
        return 0 < index < len(self.tokens) and self.tokens[index - 1].end == self.tokens[index].start

    def text(self, start: int, end: int | None = None) -> str:
        """ The signature text of the tokens from start up to end, by default up to the next token """
        end = self.pos if end is None else end
        return self.sig[self.tokens[start].start:self.tokens[end - 1].end] if start < end else ''

    def rest(self) -> str:
        """ The text of the remaining tokens, which must be at least one """
        if self.peek() is None:
            raise ParseError
        start, self.pos = self.pos, len(self.tokens)
        return self.text(start)

    def name(self) -> str:
        if not is_name(self.peek()):
            raise ParseError
        self.pos += 1
        return self.tokens[self.pos - 1].text

    def group(self, open_text: str, close_text: str) -> None:
        """ Skip a group such as [Attr(1)] that starts at the next token, with the groups nested in it """
        if not self.at(open_text):
            raise ParseError
        depth = 0
        for index in range(self.pos, len(self.tokens)):
            text = self.tokens[index].text
            depth += (text == open_text) - (text == close_text)
            if depth == 0:
                self.pos = index + 1
                return
        raise ParseError

    def modifiers(self, keywords: set[str]) -> list[str]:
        """ The modifiers, such as public static, that come before a type or a name """
        result = []
        while self.at(*keywords) and (is_name(self.peek(1)) or self.at('(', '?', offset=1)):
            result.append(self.name())
        return result

    def misplaced_nullable(self) -> str:
        """ The nullable marker that Doxygen writes after the modifiers of some types, as in override? object """
        if self.at('?') and self.peek(1) and not self.adjacent(1):
            self.pos += 1
            return '?'
        return ''

    def attributes(self) -> list[str]:
        """ The attributes, such as [NotNull], before a declaration or a parameter """
        result = []
        while self.at('['):
            start = self.pos
            self.group('[', ']')
            result.append(self.text(start))
        return result

    def generic_args(self) -> list[str]:
        """ The generic arguments or parameters, such as int and string in <int, string>, if there are any """
        if not self.at('<'):
            return []
        start = self.pos
        self.group('<', '>')
        return split_sig(self.text(start + 1, self.pos - 1))

    def templates(self) -> list[str]:
        """ The generic parameters that Doxygen writes as a C++ template prefix, such as template<T> """
        if self.at('template') and self.at('<', offset=1):
            self.pos += 1
            return self.generic_args()
        return []

    def name_part(self) -> str:
        """ A name in a qualified name, without the -g in the arity that Doxygen writes, such as Box-1 for Box-1-g """
        name = self.name()
        # The arity of a generic type, such as -1 in Box-1
        arity = self.peek(1)
        if self.at('-') and self.adjacent() and self.adjacent(1) and arity and arity.text.isdecimal():
            name += '-' + arity.text
            self.pos += 2
            if self.at('-') and self.adjacent() and self.adjacent(1) and self.at('g', offset=1):
                self.pos += 2
        return name

    def qualified_name(self) -> str:
        """ A name such as System.String or global::System.String """
        name = self.name_part()
        while self.at('.', '::') and is_name(self.peek(1)):
            name += self.tokens[self.pos].text
            self.pos += 1
            name += self.name_part()
        return name

    def generic_qualified_name(self) -> str:
        """ A qualified name in generic outer types, such as Outer<T>.Color, without whitespace """
        name = self.qualified_name()
        while self.at('<'):
            start = self.pos
            self.group('<', '>')
            name += ''.join(self.text(start).split())
            self.expect('.')
            name += '.' + self.qualified_name()
        return name

    def function_pointer(self) -> str:
        """ The start of a function pointer type, such as delegate* unmanaged[Cdecl] before <int, void> """
        start = self.pos
        self.pos += 2
        if (self.accept('managed') or self.accept('unmanaged')) and self.at('['):
            self.group('[', ']')
        if not self.at('<'):
            raise ParseError
        return self.text(start)

    def type(self) -> ParsedType:
        """
        A type such as List<int>.Enumerator[], a tuple type such as (int a, string b)?, or a function pointer type
        such as delegate* unmanaged[Cdecl]<int, void>
        """
        start = self.pos
        if self.at('('):
            self.group('(', ')')
            name = self.text(start)
        elif self.at('delegate') and self.at('*', offset=1):
            name = self.function_pointer()
        else:
            name = self.qualified_name()
        generics = self.generic_args()
        nested = []
        while generics and self.at('.') and is_name(self.peek(1)):
            self.pos += 1
            segment = self.pos
            self.name_part()
            self.generic_args()
            nested.append(self.text(segment))
        suffix = ''
        while True:
            if self.at('*', '&', '?'):
                suffix += self.tokens[self.pos].text
                self.pos += 1
            elif self.at('['):
                # An array rank, such as [,]
                commas = 1
                while self.at(',', offset=commas):
                    commas += 1
                if not self.at(']', offset=commas):
                    break
                suffix += '[' + ',' * (commas - 1) + ']'
                self.pos += commas + 1
            else:
                break
        return ParsedType(self.text(start), name, generics, nested, suffix)

    def member_name(self) -> tuple[str, str]:
        """ The explicit interface and name of a member, such as IList<int>. and Add in IList< int >. Add """
        interface = ''
        while True:
            start = self.pos
            name = self.name()
            if name == 'operator':
                raise ParseError
            if self.at('<'):
                self.group('<', '>')
                if not self.at('.'):
                    # The generic parameters of a method
                    self.pos = start + 1
            if not self.accept('.'):
                return interface, name
            interface += ''.join(self.text(start).split())

    def value(self, close: str) -> str:
        """ A default value, up to the comma or the bracket close that ends it """
        return self.expression((',', close))

    def expression(self, ends: tuple[str, ...]) -> str:
        """ An expression, up to one of the tokens that ends it outside brackets """
        start = self.pos
        depth = 0
        while (token := self.peek()) is not None and not (depth == 0 and token.text in ends):
            # Generic arguments, as in new KeyValuePair<int, int>(), as opposed to a comparison such as 1 < 2
            if token.text == '<' and (end := generic_arguments_end(self.tokens, self.pos)) is not None:
                self.pos = end
                continue
            if token.text in OPENING:
                depth += 1
            elif token.text in CLOSING:
                depth -= 1
            self.pos += 1
        if self.pos == start:
            raise ParseError
        return self.text(start)

    def param(self, close: str, unnamed: bool = False) -> ParamTuple:
        """
        A parameter, such as [NotNull] ref int x = 0, up to the comma or the bracket close that ends it.
        With unnamed, the parameter name is optional, as in the receiver of extension(string).
        """
        modifiers = self.attributes() + self.modifiers(PARAM_MODIFIERS)
        typ = self.type()
        name = '' if unnamed and self.at(close) else self.name()
        default = self.value(close) if self.accept('=') else None
        return ParamTuple(name, typ.fulltype, default, modifiers)

    def params(self, close: str) -> list[ParamTuple]:
        """ The parameters after an opening bracket, up to the bracket close that ends them """
        result: list[ParamTuple] = []
        while not self.accept(close):
            if result:
                self.expect(',')
            result.append(self.param(close))
        return result

    def constraints(self) -> list[Constraint]:
        """ The generic constraints, such as where T : class, new() where U : IFoo<T> """
        result = []
        while self.accept('where'):
            start = self.pos
            while self.peek() is not None and not self.at('where', ':', '=>'):
                self.pos += 1
            param = self.text(start)
            self.expect(':')
            types = self.pos
            while self.peek() is not None and not self.at('where', '=>'):
                self.pos += 1
            if not param or types == self.pos:
                raise ParseError
            result.append(Constraint(param, [' '.join(typ.split()) for typ in split_sig(self.text(types))]))
        return result

    def accessors(self) -> list[str]:
        """ The accessors in braces, such as get and private set in { get; private set; }, without their bodies """
        self.expect('{')
        result = []
        while not self.accept('}'):
            start = self.pos
            while self.at(*ACCESSOR_MODIFIERS):
                self.pos += 1
            if not self.at(*ACCESSORS):
                raise ParseError
            self.pos += 1
            result.append(' '.join(token.text for token in self.tokens[start:self.pos]))
            # A body, as in get { return x; } or get => x;
            if self.at('{'):
                self.group('{', '}')
                continue
            if self.accept('=>'):
                self.expression((';',))
            self.expect(';')
        return result

    def expression_body(self) -> None:
        """ Skip an expression body, such as => x * 2 """
        if self.accept('=>'):
            self.rest()

    def operator_symbol(self) -> str | None:
        """ An operator symbol such as + or >>=, or None if the next token does not start one """
        if self.at('true', 'false'):
            return self.name()
        end = self.pos
        while end < len(self.tokens) and self.tokens[end].text in OPERATOR_CHARS and \
                (end == self.pos or self.tokens[end - 1].end == self.tokens[end].start):
            end += 1
        symbol = ''.join(token.text for token in self.tokens[self.pos:end])
        if symbol not in OPERATOR_NAMES:
            return None
        self.pos = end
        return symbol

    def operator(self, modifiers: list[str], nullable: str) -> MethodSig:
        """ An operator, such as V operator +(V a, V b), or a conversion operator, after the modifiers """
        return_type = None if self.at('operator') else self.type().fulltype + nullable
        self.expect('operator')
        checked = 'checked ' if self.accept('checked') else ''
        op = self.operator_symbol()
        if op is None:
            # A conversion operator names its type after the operator keyword
            if return_type is not None:
                raise ParseError
            return_type = self.type().fulltype
            operator = ('operator ' + checked).strip()
        elif return_type is None:
            raise ParseError
        else:
            operator = 'operator ' + checked + op
        self.expect('(')
        params = self.params(')')
        if op is None:
            # Doxygen drops the explicit keyword from conversion operators
            if 'implicit' not in modifiers and 'explicit' not in modifiers:
                modifiers.append('explicit')
            name = 'Implicit' if 'implicit' in modifiers else 'Explicit'
        elif len(params) == 1 and op in UNARY_OPERATOR_NAMES:
            name = UNARY_OPERATOR_NAMES[op]
        elif not params and op in INSTANCE_OPERATOR_NAMES:
            name = INSTANCE_OPERATOR_NAMES[op]
        else:
            name = OPERATOR_NAMES[op]
        self.expression_body()
        return MethodSig(modifiers, return_type, 'op_' + ('Checked' if checked else '') + name, [], params, [],
                         operator)

    def method(self) -> MethodSig:
        """ A method, constructor, delegate or operator """
        modifiers = self.modifiers(MODIFIERS)
        nullable = self.misplaced_nullable()
        templates = self.templates()
        start = self.pos
        try:
            return self.operator(list(modifiers), nullable)
        except ParseError:
            self.pos = start
        try:
            return_type: str | None = self.type().fulltype + nullable
            interface, name = self.member_name()
            generic_params = self.generic_args()
            self.expect('(')
        except ParseError:
            # A constructor or finalizer has no return type
            self.pos = start
            return_type = None
            finalizer = '~' if self.accept('~') else ''
            interface, name = self.member_name()
            name = finalizer + name
            generic_params = self.generic_args()
            self.expect('(')
        params = self.params(')')
        initializer = None
        if self.accept(':'):
            initializer_start = self.pos
            if not self.at('this', 'base') or not self.at('(', offset=1):
                raise ParseError
            self.pos += 1
            self.group('(', ')')
            initializer = self.text(initializer_start)
        constraints = self.constraints()
        self.expression_body()
        return MethodSig(modifiers, return_type, interface + name, generic_params or templates, params, constraints,
                         None, initializer)

    def variable(self) -> VariableSig:
        """ A field, constant or event, such as public const int X = 1 """
        modifiers = self.modifiers(MODIFIERS)
        nullable = self.misplaced_nullable()
        templates = self.templates()
        typ = self.type()
        interface, name = self.member_name()
        size = None
        if 'fixed' in modifiers:
            start = self.pos
            self.group('[', ']')
            size = self.text(start + 1, self.pos - 1)
        default = self.rest() if self.accept('=') else None
        return VariableSig(modifiers, typ.fulltype + nullable, typ.name, typ.generics or templates, interface + name,
                           default, size)

    def property(self) -> PropertySig:
        """ A property or event with accessors, or a property with an expression body """
        modifiers = self.modifiers(MODIFIERS)
        nullable = self.misplaced_nullable()
        self.templates()
        typ = self.type()
        interface, name = self.member_name()
        default = None
        if self.at('=>'):
            accessors = ['get']
            self.expression_body()
        else:
            accessors = self.accessors()
            if self.accept('='):
                default = self.rest()
        return PropertySig(modifiers, typ.fulltype + nullable, interface + name, accessors, default)

    def indexer(self, parse_params: bool = True) -> IndexerSig:
        """ An indexer, such as int this[int i] { get; }, optionally without parsing the parameters """
        modifiers = self.modifiers(MODIFIERS)
        nullable = self.misplaced_nullable()
        self.templates()
        typ = self.type()
        interface, name = self.member_name()
        if name != 'this' or not self.at('['):
            raise ParseError
        params = []
        if parse_params:
            self.pos += 1
            params = self.params(']')
            if not params:
                raise ParseError
        else:
            self.group('[', ']')
        accessors = []
        if self.at('=>'):
            accessors = ['get']
            self.expression_body()
        elif self.at('{'):
            accessors = self.accessors()
        return IndexerSig(modifiers, typ.fulltype + nullable, interface[:-1] or None, params, accessors)

    def type_signature(self) -> TypeSig:
        """ A type declaration, such as public Box<T>(T x) : IFoo where T : struct, or a type such as int[] """
        modifiers = self.modifiers(MODIFIERS)
        templates = self.templates()
        typ = self.type()
        params = self.params(')') if self.accept('(') else None
        inherits = []
        if self.accept(':'):
            start = self.pos
            while self.peek() is not None and not self.at('where'):
                self.pos += 1
            inherits = split_sig(self.text(start))
            if not inherits:
                raise ParseError
        constraints = self.constraints()
        return TypeSig(typ.name, modifiers, typ.generics or templates, inherits, typ.suffix, constraints, params,
                       typ.nested)

    def enum(self) -> EnumSig:
        """ An enum, such as public Color : byte """
        modifiers = self.modifiers(MODIFIERS)
        name = self.generic_qualified_name()
        base = self.qualified_name() if self.accept(':') else None
        return EnumSig(modifiers, name, base)

    def enumerator(self) -> EnumeratorSig:
        """ An enum value, such as Red = 1 """
        name = self.generic_qualified_name()
        return EnumeratorSig(name, self.rest() if self.accept('=') else None)

    def extension(self) -> ExtensionSig:
        """ An extension block, such as extension<T>(IEnumerable<T> source) where T : notnull, or extension(string) """
        self.accept('extension')
        generic_params = self.generic_args()
        self.expect('(')
        receiver = self.param(')', unnamed=True)
        self.expect(')')
        return ExtensionSig(generic_params, receiver, self.constraints())

    def attribute(self) -> AttrSig:
        """ An attribute class, such as MyAttr<T>(T a) """
        name = self.qualified_name()
        generic_params = self.generic_args()
        params = self.params(')') if self.accept('(') else []
        return AttrSig(name, params, generic_params)


def try_parse(sig: str, production: Callable[[Parser], T]) -> T | None:
    """ Parse a signature with a production, or return None if the signature does not match it """
    parser = Parser(sig)
    try:
        result = production(parser)
        parser.expect_end()
    except ParseError:
        return None
    return result


def parse(kind: str, sig: str, location: Location, production: Callable[[Parser], T]) -> T:
    """ Parse a signature with a production, or log a warning and raise a ValueError if it does not match it """
    result = try_parse(strip_semicolon(sig), production)
    if result is None:
        raise invalid_signature(kind, sig, location)
    return result


def split_sig(params: str, separator: str = ',') -> list[str]:
    """
    Split a list of parameters/types by commas, or another separator,
    while respecting brackets.

    For example:
      String arg0, int arg2 = 1, List<int> arg3 = [1, 2, 3]
      => ['String arg0', 'int arg2 = 1', 'List<int> arg3 = [1, 2, 3]']
    """
    result = []
    start = level = 0
    tokens = tokenize(params)
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.text == '<' and (end := generic_arguments_end(tokens, index)) is not None:
            index = end
            continue
        if token.text in OPENING:
            level += 1
        elif token.text in CLOSING:
            level -= 1
        elif token.text == separator and level <= 0:
            result.append(params[start:token.start].strip())
            start = token.end
        index += 1
    if params[start:].strip():
        result.append(params[start:].strip())
    return result


def split_generics(generics: str) -> list[str]:
    """ Split a <...> generic argument list """
    # Remove outermost < > brackets
    return split_sig(generics[1:-1])


def normalize_signature(sig: str) -> str:
    """ Remove optional whitespace from a name or signature, such as M(int, string) to M(int,string) """
    result = ''
    previous = None
    for token in tokenize(sig):
        if previous is not None and previous.end < token.start and \
                previous.text not in TIGHT_PUNCTUATION and token.text not in TIGHT_PUNCTUATION:
            result += ' '
        result += token.text
        previous = token
    return result


def parameters_start(name: str) -> int:
    """ The index of the parameters in an overload name, such as the ( in Box<int[]>.Put(int), or the name length """
    depth = 0
    for i, char in enumerate(name):
        if char == '<':
            depth += 1
        elif char == '>':
            depth -= 1
        elif char in '([' and depth == 0:
            return i
    return len(name)


def without_generic_arguments(part: str) -> str:
    """ Remove the generic arguments from one part of a name, such as <T> from Box<T> """
    start, end = part.find('<'), part.rfind('>')
    return part if start < 0 or end < start else part[:start] + part[end + 1:]


# Reference resolution calls this on every object name for each target that misses
@functools.cache
def remove_generic_arguments(name: str) -> str:
    """ Remove the generic arguments from a name, except an overload's, as in Box<T>.Put<U>(U) to Box.Put<U>(U) """
    end = parameters_start(name)
    parts = split_sig(name[:end], '.')
    return '.'.join(part if i == len(parts) - 1 and end < len(name) else without_generic_arguments(part)
                    for i, part in enumerate(parts)) + name[end:]


def parameter_types(params: list[ParamTuple]) -> str:
    """ The parameter types that tell overloads apart, such as ref int,string """
    return ','.join(' '.join([modifier for modifier in param.modifiers if modifier in OVERLOAD_PARAM_MODIFIERS] +
                             [overload_type(param.typ)]) for param in params)


def overload_type(typ: str) -> str:
    """ A type as it appears in an overload id, without tuple element names, such as (int,int) for (int a,int b) """
    tokens = tokenize(typ)
    result = ''
    start = 0
    for previous, token, following in zip(tokens, tokens[1:], tokens[2:]):
        if is_name(token) and previous.end < token.start and following.text in (',', ')') and \
                (previous.text[-1] in TUPLE_TYPE_END or
                 previous.kind == 'word' and previous.text not in PARAM_MODIFIERS):
            result += typ[start:previous.end]
            start = token.end
    return result + typ[start:]


@functools.cache
def arity_name(name: str) -> str:
    """ Write generic arguments as arity, except an overload's, such as Box-1.Put<U>(U) for Box<T>.Put<U>(U) """
    end = parameters_start(name)
    parts = split_sig(name[:end], '.')

    def part_name(part: str) -> str:
        start = part.find('<')
        return part if start < 0 else part[:start].rstrip() + f'-{len(split_generics(part[start:]))}'

    return '.'.join(part if i == len(parts) - 1 and end < len(name) else part_name(part)
                    for i, part in enumerate(parts)) + name[end:]


@functools.cache
def remove_arity(name: str) -> str:
    """ Remove the arity of the generic types in a name, as in Box-1.Put(T) to Box.Put(T) """
    end = parameters_start(name)

    def without_arity(part: str) -> str:
        head, _, arity = part.rpartition('-')
        return head if arity.isdecimal() else part

    return '.'.join(without_arity(part) for part in name[:end].split('.')) + name[end:]


def is_function_pointer(typ: str) -> bool:
    """ Whether a type name is a function pointer, such as delegate* unmanaged[Cdecl] """
    return typ.startswith('delegate') and typ.removeprefix('delegate').lstrip().startswith('*')


def generic_type_name(typ: str, arity: int) -> str:
    """ The name of a type with its arity, such as Box-1 for Box<T>, unless Doxygen has given the arity """
    return typ if not arity or typ.endswith(f'-{arity}') else f'{typ}-{arity}'


def target_id(objtype: str, name: str) -> str:
    """ The node id of an object, such as function-N.C.M(ref-int,string) """
    return objtype + '-' + name.replace(' ', '-')


def split_attributes(sig: str) -> tuple[list[str], str]:
    """ Split the attributes from the start of a declaration, such as [Obsolete] in [Obsolete] void Foo() """
    parser = Parser(sig)
    attributes = []
    while parser.at('['):
        start = parser.pos
        try:
            parser.group('[', ']')
        except ParseError:
            # The parser reports the unclosed bracket
            break
        attributes.append(parser.text(start))
    token = parser.peek()
    return attributes, sig[token.start:].strip() if token else ''


def split_declarators(sig: str) -> list[str]:
    """
    Split a field or event that declares several variables, such as int x = 1, y, into a declaration for each, such as
    int x = 1 and int y. Returns the signature unchanged if it declares one variable, or does not parse.
    """
    parser = Parser(strip_semicolon(sig))
    declarators = []
    try:
        parser.attributes()
        parser.modifiers(MODIFIERS)
        parser.misplaced_nullable()
        parser.templates()
        parser.type()
        prefix = parser.sig[:parser.tokens[parser.pos].start] if parser.peek() else ''
        while True:
            start = parser.pos
            parser.name()
            # The size of a fixed buffer
            if parser.at('['):
                parser.group('[', ']')
            if parser.accept('='):
                parser.expression((',',))
            declarators.append(prefix + parser.text(start))
            if not parser.accept(','):
                break
        parser.expect_end()
    except ParseError:
        return [sig]
    return declarators if len(declarators) > 1 else [sig]


def strip_semicolon(sig: str) -> str:
    """ Remove whitespace and a trailing semicolon from a signature copied from source, such as void Foo(); """
    return sig.strip().removesuffix(';').rstrip()


def invalid_signature(kind: str, sig: str, location: Location) -> ValueError:
    """ Log an invalid signature and return a ValueError, which Sphinx handles by showing the signature as written """
    logger.warning(f'{kind} signature invalid: {sig}', location=location)
    return ValueError(f'{kind} signature invalid: {sig}')


def parse_method_signature(sig: str, location: Location) -> MethodSig:
    """ Parse a method signature of the form: modifier* type name (params),
        or an operator signature such as: modifier* type operator + (params) """
    result = parse('Method', sig, location, Parser.method)
    if CSDebug.parse_func:
        logger.info(f"parsed func: {tuple(result)}")
    return result


def parse_variable_signature(sig: str, location: Location) -> VariableSig:
    """ Parse a variable signature of the form: modifier* type name = value """
    result = parse('Variable', sig, location, Parser.variable)
    if CSDebug.parse_var:
        logger.info(f"parsed var: {tuple(result)}")
    return result


def parse_property_signature(sig: str, location: Location) -> PropertySig:
    """ Parse a property or event signature of the form:
        modifier* type name { accessor* } (= value)? or modifier* type name => expression """
    result = try_parse(strip_semicolon(sig), Parser.property)
    if result is None:
        if CSDebug.parse_prop:
            logger.info(f'Property signature not valid, falling back to variable: {sig}', location=location)
        var = parse_variable_signature(sig, location)
        return PropertySig(var.modifiers, var.fulltype, var.name, [], var.default)
    if CSDebug.parse_prop:
        logger.info(f"parsed prop: {tuple(result)}")
    return result


def is_indexer_signature(sig: str) -> bool:
    """ Whether a signature is an indexer, such as int this[int i] { get; } """
    return try_parse(strip_semicolon(sig), lambda parser: parser.indexer(parse_params=False)) is not None


def parse_indexer_signature(sig: str, location: Location) -> IndexerSig:
    """ Parse a indexer signature of the form:
        modifier* type (interface.)?this[params] ({ accessor* } | => expression)? """
    result = parse('Indexer', sig, location, Parser.indexer)
    if CSDebug.parse_idxr:
        logger.info(f"parsed idxr: {tuple(result)}")
    return result


def parse_type_signature(sig: str | None, location: Location) -> TypeSig:
    """ Parse a type declaration or usage signature """
    result = parse('Type', sig or '', location, Parser.type_signature)
    if CSDebug.parse_type:
        logger.info(f"parsed type: {tuple(result)}")
    return result


def parse_type_reference(target: str) -> TypeSig | None:
    """ Parse the type in a reference target, such as List<int>.Enumerator, or return None if it is not a type """
    typ = try_parse(target, Parser.type)
    return None if typ is None else TypeSig(typ.name, [], typ.generics, [], typ.suffix, [], None, typ.nested)


def parse_tuple_element(element: str) -> tuple[str, str | None] | None:
    """ Split a tuple element into its type and name, such as int and count in int count, or return None if empty """
    tokens = tokenize(element)
    if not tokens:
        return None
    last = tokens[-1]
    if len(tokens) > 1 and is_name(last) and tokens[-2].end < last.start:
        return element[:tokens[-2].end].strip(), last.text
    return element.strip(), None


def parse_base_type(base: str) -> tuple[str, str | None]:
    """ Split a base type that Breathe writes into its type and the arguments to its constructor, if any,
        such as Base and (x) in public Base(x) """
    words = base.split(None, 1)
    while len(words) == 2 and words[0] in BASE_ACCESS:
        base = words[1]
        words = base.split(None, 1)
    # Doxygen 1.9 separates the namespaces of some base types with ::, which is C# syntax only after global
    parts = base.split('::')
    base = parts[0] + ''.join(('::' if previous.endswith('global') else '.') + part
                              for previous, part in zip(parts, parts[1:]))
    parser = Parser(base)
    try:
        parser.type()
    except ParseError:
        return base, None
    token = parser.peek()
    if token is not None and token.text == '(' and base.endswith(')'):
        return base[:token.start].rstrip(), base[token.start:]
    return base, None


def parse_type_keyword(parser: Parser, keywords: tuple[str, ...]) -> tuple[list[str], str, str]:
    """ The modifiers, the keyword such as record struct, and the rest of a type declaration """
    modifiers = parser.modifiers(MODIFIERS)
    start = parser.pos
    if not parser.at(*keywords):
        raise ParseError
    parser.pos += 1
    if parser.at('class', 'struct') and parser.tokens[start].text == 'record':
        parser.pos += 1
    keyword = ' '.join(token.text for token in parser.tokens[start:parser.pos])
    token = parser.peek()
    if token is None:
        raise ParseError
    return modifiers, keyword, parser.sig[token.start:]


def split_type_keyword(sig: str, keywords: tuple[str, ...]) -> tuple[list[str], str, str] | None:
    """ The modifiers, keyword and rest of a type declaration that has one of keywords, such as public, class and
        Point(int X) in public class Point(int X), or None if it has none of them """
    parser = Parser(sig.strip())
    try:
        return parse_type_keyword(parser, keywords)
    except ParseError:
        return None


def parse_type_as_function(sig: str) -> tuple[list[str], str, str] | None:
    """ The modifiers, keyword and rest of a record, or a type with a primary constructor, that Doxygen writes as a
        function, such as record struct and Point(int X) in record struct Point(int X), or None if it is neither """
    parser = Parser(sig.strip())
    try:
        # Note: The name of a generic record also has its generic parameters, so we drop the template prefix.
        parser.templates()
        modifiers, keyword, rest = parse_type_keyword(parser, ('record', 'class', 'struct'))
        parser.qualified_name()
        parser.generic_args()
        parser.expect('(')
    except ParseError:
        return None
    return modifiers, keyword, rest


def parse_enum_signature(sig: str, location: Location) -> EnumSig:
    """ Parse an enum signature of the form: modifier* name (: type)? """
    return parse('Enum', sig, location, Parser.enum)


def parse_enumerator_signature(sig: str, location: Location) -> EnumeratorSig:
    """ Parse an enum value signature of the form: name (= value)? """
    return parse('Enumerator', sig, location, Parser.enumerator)


def parse_extension_signature(sig: str, location: Location) -> ExtensionSig:
    """ Parse an extension block signature of the form: extension? (<generics>)? (param) constraints? """
    return parse('Extension', sig, location, Parser.extension)


def parse_attr_signature(sig: str, location: Location) -> AttrSig:
    """ Parse an attribute signature """
    result = parse('Attribute', sig, location, Parser.attribute)
    if CSDebug.parse_attr:
        logger.info(f"parsed attr: {tuple(result)}")
    return result
