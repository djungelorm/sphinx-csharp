""" C# signature parser """

import re
from typing import NamedTuple

from docutils import nodes
from sphinx.util import logging

from .debug import CSDebug

MODIFIERS_RE_SIMPLE = '|'.join(['public', 'private', 'internal', 'protected',
                                'abstract', 'async', 'const', 'event', 'delegate',
                                'extern', 'new', 'override', 'partial',
                                'readonly', 'required', 'sealed', 'static', 'unsafe',
                                'virtual', 'volatile', 'ref', 'implicit', 'explicit', 'file'])

PARAM_MODIFIERS_RE_SIMPLE = '|'.join(['this', 'ref', 'in', 'out', 'params', 'scoped', 'readonly'])

MODIFIERS_RE = re.compile(r'\s*(?:(?P<modifiers>(?:\s*(?:' + MODIFIERS_RE_SIMPLE + r'))*)\s+)?')
# An attribute such as [Attr(new[] {1})], with brackets nested one level deep or inside string literals
ATTRIBUTE_RE = re.compile(r'\[(?:[^\[\]"\']|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|\[[^\[\]]*\])*\]')
# MODIFIERS_RE with parameter modifiers, after any attributes such as [NotNull]
PARAM_MODIFIERS_RE = re.compile(r'\s*(?P<attributes>(?:' + ATTRIBUTE_RE.pattern + r'\s*)*)'
                                r'(?:(?P<modifiers>(?:\s*(?:' + PARAM_MODIFIERS_RE_SIMPLE + r'))*)\s+)?\s*')


# A tuple type, with tuples nested one level deep
TUPLE_RE = re.compile(r'\((?:[^()]|\([^()]*\))*\)')
TUPLE_ELEMENT_RE = re.compile(r'^(?P<type>.+?)(?:\s+(?P<name>[A-Za-z_@]\w*))?$')

TYPE_NAME_RE = r'(?P<type>' + TUPLE_RE.pattern + r'|[^\s<\[{*&?(]+)'

# Nullable, pointer and array suffixes in any order, such as int?[] or int**
TYPE_SUFFIX_RE = r'(?P<suffix>(?:\s*(?:[*&?]|\[,*\]))*)'

# The types nested in a generic type, such as .Enumerator in List<int>.Enumerator
TYPE_NESTED_RE = r'(?P<nested>(?:\s*\.\s*[^\s<\[{*&?(.]+\s*(?:<\s*.+?\s*>)?)*)'

TYPE_RE = re.compile(r'(?:template(?P<templates><\s*.+\s*>))?\s*'
                     r'(?P<fulltype>' + TYPE_NAME_RE + r'\s*(?P<generics><\s*.+?\s*>)?' + TYPE_NESTED_RE +
                     TYPE_SUFFIX_RE + r')')

TYPE_OPTIONAL_RE = re.compile(r'(?:template(?P<templates><\s*.+\s*>))?\s*'
                              r'(?:(?P<fulltype>' + TYPE_NAME_RE + r'\s*(?P<generics><\s*.+?\s*>)?' +
                              TYPE_NESTED_RE + TYPE_SUFFIX_RE + r')\s+)?')

# Generic constraints, such as where T : class, new() where U : IFoo<T>
CONSTRAINTS_RE = re.compile(r'(?:\s+where\s+(?P<constraints>.+))?')
CONSTRAINT_KEYWORDS = ['class', 'class?', 'struct', 'notnull', 'unmanaged', 'default', 'new()', 'allows ref struct']

METH_SIG_RE = re.compile(
    r'^' + MODIFIERS_RE.pattern + TYPE_OPTIONAL_RE.pattern +
    r'(?P<fname>[^\s<(]+)\s*'
    r'(?P<genericparams><[^(]+>)?\s*'
    r'\((?P<params>.*?)\)' + CONSTRAINTS_RE.pattern + r'$')

VAR_SIG_RE = re.compile(
    r'^' + MODIFIERS_RE.pattern + TYPE_RE.pattern + r'\s+(?P<name>[^\s<{(=]+)\s*(?:=\s*(?P<value>.+))?$')
VAR_PARAM_SIG_RE = re.compile(
    r'^' + PARAM_MODIFIERS_RE.pattern + TYPE_RE.pattern + r'\s+(?P<name>[^\s<{=]+)\s*(?:=\s*(?P<value>.+))?$')

ACCESSOR_RE = re.compile(r'(?:(?:public|private|protected|internal|readonly)\s+)*(?:get|set|init|add|remove)\s*;')
ACCESSORS_RE = re.compile(r'{\s*(?P<accessors>(?:' + ACCESSOR_RE.pattern + r'\s*)*)}')

# An expression body is a getter, and a trailing semicolon is dropped
PROP_SIG_RE = re.compile(
    r'^' + MODIFIERS_RE.pattern + TYPE_RE.pattern + r'\s+(?P<name>[^\s<{(=]+)\s*'
    r'(?:' + ACCESSORS_RE.pattern + r'\s*(?:=\s*(?P<value>.+?))?|(?P<expr>=>.+?))\s*;?\s*$')

# The parameters may contain brackets one level deep, such as int[] a
IDXR_SIG_RE = re.compile(
    r'^' + MODIFIERS_RE.pattern + TYPE_RE.pattern + r'\s+(?P<interface>[^\s\[]+\.)?this\s*'
    r'\[(?P<params>(?:[^\[\]]|\[[^\[\]]*\])*)\]\s*'
    r'(?:' + ACCESSORS_RE.pattern + r'|(?P<expr>=>.+?))?\s*;?\s*$')

# Operators, named by their .NET metadata names such as op_Addition
OPERATOR_SYMBOL_RE = r'>>>=|>>=|<<=|>>>|\+\+|--|<<|>>|[=!<>]=|[-+*/%&|^]=?|[!~<>]|true|false'
OPERATOR_SIG_RE = re.compile(
    r'^' + MODIFIERS_RE.pattern + TYPE_OPTIONAL_RE.pattern +
    r'operator\s*(?P<checked>checked\s+)?(?P<op>' + OPERATOR_SYMBOL_RE + r')\s*\((?P<params>.*?)\)\s*$')
CONVERSION_SIG_RE = re.compile(
    r'^' + MODIFIERS_RE.pattern + r'operator\s+(?P<checked>checked\s+)?' + TYPE_RE.pattern +
    r'\s*\((?P<params>.*?)\)\s*$')
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
# Operators with these symbols and a single parameter are unary
UNARY_OPERATOR_NAMES = {'+': 'UnaryPlus', '-': 'UnaryNegation'}
# Instance increment and decrement operators have no parameters
INSTANCE_OPERATOR_NAMES = {'++': 'IncrementAssignment', '--': 'DecrementAssignment'}
CONVERSION_OPERATORS = ['op_Implicit', 'op_Explicit', 'op_CheckedImplicit', 'op_CheckedExplicit']

INHERITS_RE = re.compile(r'(?:\s*:\s*(?P<inherits>.*?))?')
# Doxygen names a generic type with its arity, such as Box-1-g for Box<T>
DOXYGEN_ARITY_RE = re.compile(r'-\d+-g(?=\.|$)')

PRIMARY_CONSTRUCTOR_RE = re.compile(r'(?:\s*\((?P<params>.*?)\))?')
CLASS_SIG_RE = re.compile(r'^' + MODIFIERS_RE.pattern + TYPE_RE.pattern + PRIMARY_CONSTRUCTOR_RE.pattern +
                          INHERITS_RE.pattern + CONSTRAINTS_RE.pattern + r'$')
# A base type with arguments for its constructor, such as Base(x)
BASE_ARGS_RE = re.compile(r'^(?P<type>[^(]+?)\s*(?P<args>\(.*\))$')
# Doxygen writes records, and types with primary constructors, as functions
TYPE_AS_FUNCTION_RE = re.compile(
    r'^' + MODIFIERS_RE.pattern + r'(?P<keyword>record(?:\s+(?:class|struct))?|class|struct)\s+'
    r'(?P<sig>[^\s<(]+\s*(?:<[^(]*>)?\s*\(.*)$')
RECORD_KIND_RE = re.compile(r'^' + MODIFIERS_RE.pattern + r'(?P<kind>class|struct)\s+(?P<sig>.+)$')

ENUM_SIG_RE = re.compile(r'^' + MODIFIERS_RE.pattern + r'(?P<name>[^\s:]+)\s*(?::\s*(?P<base>\S+))?$')
ENUMERATOR_SIG_RE = re.compile(r'^(?P<name>[^\s=]+)\s*(?:=\s*(?P<value>.+))?$')

ATTR_SIG_RE = re.compile(r'^([^\s(]+)(\s*\((.*)\))?$')

# Source location of a signature, as a (docname, line) pair, or the node of a doc field
Location = tuple[str, int] | nodes.Node | None


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


class VariableSig(NamedTuple):
    modifiers: list[str]
    fulltype: str
    typ: str
    generics: list[str]
    name: str
    default: str | None


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


class AttrSig(NamedTuple):
    name: str
    params: list[ParamTuple]


logger = logging.getLogger(__name__)


def split_sig(params: str, separator: str = ',') -> list[str]:
    """
    Split a list of parameters/types by commas, or another separator,
    whilst respecting brackets.

    For example:
      String arg0, int arg2 = 1, List<int> arg3 = [1, 2, 3]
      => ['String arg0', 'int arg2 = 1', 'List<int> arg3 = [1, 2, 3]']
    """
    result = []
    current = ''
    level = 0
    # The quote character of the string or char literal we are in
    quote = None
    escaped = False
    for char in params:
        if quote:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == quote:
                quote = None
        elif char in ('"', "'"):
            quote = char
        elif char in ('<', '{', '[', '('):
            level += 1
        elif char in ('>', '}', ']', ')'):
            level -= 1
        if char != separator or level > 0 or quote:
            current += char
        else:
            result.append(current.strip())
            current = ''
    if current.strip() != '':
        result.append(current.strip())
    return result


def split_generics(generics: str | None) -> list[str]:
    """ Split a <...> generic argument list, or return an empty list if there is none """
    if not generics:
        return []
    # Remove outermost < > brackets
    return split_sig(generics[1:-1])


def parse_params(params: str | None, location: Location) -> list[ParamTuple]:
    """ Parse a comma-separated parameter list """
    if params is None or params.strip() == '':
        return []
    return [parse_param_signature(x, location) for x in split_sig(params)]


def invalid_signature(kind: str, sig: str, location: Location) -> ValueError:
    """ Log an invalid signature and return a ValueError, which Sphinx handles by showing the signature as written """
    logger.warning(f'{kind} signature invalid: {sig}', location=location)
    return ValueError(f'{kind} signature invalid: {sig}')


def parse_constraints(constraints: str | None, location: Location) -> list[Constraint]:
    """ Parse the generic constraints after the first where, such as "T : class, new() where U : IFoo" """
    if not constraints:
        return []
    result = []
    for clause in re.split(r'\s+where\s+', constraints):
        param, sep, types = clause.partition(':')
        if not sep or not param.strip() or not types.strip():
            raise invalid_signature('Constraint', clause, location)
        result.append(Constraint(param.strip(), [' '.join(typ.split()) for typ in split_sig(types)]))
    return result


def parse_operator_signature(sig: str, location: Location) -> MethodSig | None:
    """ Parse an operator or conversion operator signature, or return None if it is neither """
    operator_match = OPERATOR_SIG_RE.match(sig.strip())
    match = operator_match or CONVERSION_SIG_RE.match(sig.strip())
    if match is None:
        return None
    conversion = operator_match is None

    groups = match.groupdict()
    modifiers = groups['modifiers'].split() if groups['modifiers'] else []
    return_type = groups['fulltype'].strip() if groups['fulltype'] else None
    params = parse_params(groups['params'], location)
    checked = 'checked ' if groups['checked'] else ''

    if conversion:
        # Doxygen drops the explicit keyword from conversion operators
        if 'implicit' not in modifiers and 'explicit' not in modifiers:
            modifiers.append('explicit')
        name = 'Implicit' if 'implicit' in modifiers else 'Explicit'
        operator = ('operator ' + checked).strip()
    else:
        op = groups['op']
        if len(params) == 1 and op in UNARY_OPERATOR_NAMES:
            name = UNARY_OPERATOR_NAMES[op]
        elif not params and op in INSTANCE_OPERATOR_NAMES:
            name = INSTANCE_OPERATOR_NAMES[op]
        else:
            name = OPERATOR_NAMES[op]
        operator = 'operator ' + checked + op

    name = 'op_' + ('Checked' if checked else '') + name
    return MethodSig(modifiers, return_type, name, [], params, [], operator)


def parse_method_signature(sig: str, location: Location) -> MethodSig:
    """ Parse a method signature of the form: modifier* type name (params),
        or an operator signature such as: modifier* type operator + (params) """
    result = parse_operator_signature(sig, location) or parse_named_method_signature(sig, location)
    if CSDebug.parse_func:
        logger.info(f"parsed func: {tuple(result)}")
    return result


def parse_named_method_signature(sig: str, location: Location) -> MethodSig:
    """ Parse a method signature of the form: modifier* type name (params) """
    match = METH_SIG_RE.match(sig.strip())
    if not match:
        raise invalid_signature('Method', sig, location)

    groups = match.groupdict()
    modifiers = groups['modifiers'].split() if groups['modifiers'] else []
    return_type = groups['fulltype'].strip() if groups['fulltype'] else None
    # Doxygen writes generic parameters as a C++ template prefix
    generic_params = split_generics(groups['genericparams'] or groups['templates'])
    params = parse_params(groups['params'], location)
    constraints = parse_constraints(groups['constraints'], location)
    return MethodSig(modifiers, return_type, groups['fname'], generic_params, params, constraints, None)

    match = METH_SIG_RE.match(sig.strip())
    if not match:
        raise invalid_signature('Method', sig, location)

    groups = match.groupdict()
    modifiers = groups['modifiers'].split() if groups['modifiers'] else []
    return_type = groups['fulltype'].strip() if groups['fulltype'] else None
    # Doxygen writes generic parameters as a C++ template prefix
    generic_params = split_generics(groups['genericparams'] or groups['templates'])
    params = parse_params(groups['params'], location)

    constraints = parse_constraints(groups['constraints'], location)

    result = MethodSig(modifiers, return_type, groups['fname'], generic_params, params, constraints, None)
    if CSDebug.parse_func:
        logger.info(f"parsed func: {tuple(result)}")
    return result


def parse_variable_signature(sig: str, location: Location, is_param: bool = False) -> VariableSig:
    """
    Parse a variable signature of the form:
    modifier* type name = value
    is_param: interpret as parameter? uses parameter modifiers
    """
    match = (VAR_PARAM_SIG_RE if is_param else VAR_SIG_RE).match(sig.strip())
    if not match:
        raise invalid_signature('Parameter' if is_param else 'Variable', sig, location)

    groups = match.groupdict()
    modifiers = ATTRIBUTE_RE.findall(groups.get('attributes') or '')
    modifiers += groups['modifiers'].split() if groups['modifiers'] else []
    # The templates group is the Doxygen form of the generics
    generics = split_generics(groups['generics'] or groups['templates'])

    result = VariableSig(modifiers, groups['fulltype'].strip(), groups['type'], generics,
                         groups['name'], groups['value'])
    if CSDebug.parse_var:
        logger.info(f"parsed var: {tuple(result)}")
    return result


def parse_accessors(accessors: str) -> list[str]:
    """ Split the body of an accessor list, such as "get; private set;", into accessors """
    return [' '.join(accessor.split()) for accessor in accessors.split(';') if accessor.strip()]


def parse_property_signature(sig: str, location: Location) -> PropertySig:
    """ Parse a property or event signature of the form:
        modifier* type name { accessor* } (= value)? or modifier* type name => expression """
    match = PROP_SIG_RE.match(sig.strip())
    if not match:
        if CSDebug.parse_prop:
            logger.info(f'Property signature not valid, falling back to variable: {sig}', location=location)
        var = parse_variable_signature(sig, location)
        return PropertySig(var.modifiers, var.fulltype, var.name, [], var.default)

    groups = match.groupdict()
    modifiers = groups['modifiers'].split() if groups['modifiers'] else []
    accessors = ['get'] if groups['expr'] else parse_accessors(groups['accessors'])
    result = PropertySig(modifiers, groups['fulltype'].strip(), groups['name'], accessors, groups['value'])
    if CSDebug.parse_prop:
        logger.info(f"parsed prop: {tuple(result)}")
    return result


def parse_indexer_signature(sig: str, location: Location) -> IndexerSig:
    """ Parse a indexer signature of the form:
        modifier* type (interface.)?this[params] ({ accessor* } | => expression)? """
    match = IDXR_SIG_RE.match(sig.strip())
    if not match or not match['params'].strip():
        raise invalid_signature('Indexer', sig, location)

    groups = match.groupdict()
    modifiers = groups['modifiers'].split() if groups['modifiers'] else []
    interface = groups['interface'][:-1] if groups['interface'] else None
    accessors = ['get'] if groups['expr'] else parse_accessors(groups['accessors'] or '')
    result = IndexerSig(modifiers, groups['fulltype'].strip(), interface,
                        parse_params(groups['params'], location), accessors)
    if CSDebug.parse_idxr:
        logger.info(f"parsed idxr: {tuple(result)}")
    return result


def parse_param_signature(sig: str, location: Location) -> ParamTuple:
    """ Parse a parameter signature of the form: modifier type name (= default)?
        Interprets as a variable with different modifiers """
    var = parse_variable_signature(sig, location, True)
    return ParamTuple(name=var.name, typ=var.fulltype, default=var.default, modifiers=var.modifiers)


def parse_type_signature(sig: str, location: Location) -> TypeSig:
    """ Parse a type declaration or usage signature """
    match = CLASS_SIG_RE.match(sig.strip()) if sig else None
    if not match:
        raise invalid_signature('Type', sig, location)

    groups = match.groupdict()
    modifiers = groups['modifiers'].split() if groups['modifiers'] else []
    # The templates group is the Doxygen form of the generics
    generics = split_generics(groups['generics'] or groups['templates'])
    inherits = split_sig(groups['inherits']) if groups['inherits'] else []

    constraints = parse_constraints(groups['constraints'], location)
    params = None if groups['params'] is None else parse_params(groups['params'], location)

    suffix = ''.join(groups['suffix'].split())
    nested = split_sig(groups['nested'].strip()[1:], '.') if groups['nested'] else []
    typ = DOXYGEN_ARITY_RE.sub('', groups['type'])
    result = TypeSig(typ, modifiers, generics, inherits, suffix, constraints, params, nested)
    if CSDebug.parse_type:
        logger.info(f"parsed type: {tuple(result)}")
    return result


def parse_enum_signature(sig: str, location: Location) -> EnumSig:
    """ Parse an enum signature of the form: modifier* name (: type)? """
    match = ENUM_SIG_RE.match(sig.strip())
    if not match:
        raise invalid_signature('Enum', sig, location)
    modifiers = match['modifiers'].split() if match['modifiers'] else []
    return EnumSig(modifiers, match['name'], match['base'])


def parse_enumerator_signature(sig: str, location: Location) -> EnumeratorSig:
    """ Parse an enum value signature of the form: name (= value)? """
    match = ENUMERATOR_SIG_RE.match(sig.strip())
    if not match:
        raise invalid_signature('Enumerator', sig, location)
    return EnumeratorSig(match['name'], match['value'])


def parse_attr_signature(sig: str, location: Location) -> AttrSig:
    """ Parse an attribute signature """
    match = ATTR_SIG_RE.match(sig.strip())
    if not match:
        raise invalid_signature('Attribute', sig, location)
    name, _, params = match.groups()

    result = AttrSig(name, parse_params(params, location))
    if CSDebug.parse_attr:
        logger.info(f"parsed attr: {tuple(result)}")
    return result
