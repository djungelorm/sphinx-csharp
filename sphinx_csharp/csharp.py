""" C# sphinx domain """

import re
from collections.abc import Iterable, Iterator, Set
from typing import Any, NamedTuple

from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.builders import Builder
from sphinx.config import Config
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType
from sphinx.environment import BuildEnvironment
from sphinx.locale import _
from sphinx.roles import XRefRole
from sphinx.util import logging
from sphinx.util.nodes import make_refnode

from .debug import CSDebug
from .extrefs import ExternalRefs

MODIFIERS_RE_SIMPLE = '|'.join(['public', 'private', 'internal', 'protected',
                                'abstract', 'async', 'const', 'event', 'delegate',
                                'extern', 'new', 'override', 'partial',
                                'readonly', 'required', 'sealed', 'static', 'unsafe',
                                'virtual', 'volatile', 'ref', 'implicit', 'explicit', 'file'])

PARAM_MODIFIERS_RE_SIMPLE = '|'.join(['this', 'ref', 'in', 'out', 'params', 'scoped', 'readonly'])

MODIFIERS_RE = re.compile(r'\s*(?:(?P<modifiers>(?:\s*(?:' + MODIFIERS_RE_SIMPLE + r'))*)\s+)?')
# MODIFIERS_RE with parameter modifiers, after any attributes such as [NotNull]
PARAM_MODIFIERS_RE = re.compile(r'\s*(?P<attributes>(?:\[[^\]]*\]\s*)*)'
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

IDXR_SIG_RE = re.compile(
    r'^' + MODIFIERS_RE.pattern + TYPE_RE.pattern + r'\s+(?P<interface>[^\s\[]+\.)?this\s*\[(?P<params>.*)\]\s*'
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
    r'^' + MODIFIERS_RE.pattern + r'(?P<keyword>record(?:\s+(?:class|struct))?|class|struct)\s+(?P<sig>.+\))$')
RECORD_KIND_RE = re.compile(r'^' + MODIFIERS_RE.pattern + r'(?P<kind>class|struct)\s+(?P<sig>.+)$')

ENUM_SIG_RE = re.compile(r'^' + MODIFIERS_RE.pattern + r'(?P<name>[^\s:]+)\s*(?::\s*(?P<base>\S+))?$')
ENUMERATOR_SIG_RE = re.compile(r'^(?P<name>[^\s=]+)\s*(?:=\s*(?P<value>.+))?$')

ATTR_SIG_RE = re.compile(r'^([^\s(]+)(\s*\((.*)\))?$')

# Source location of a signature, as a (docname, line) pair
Location = tuple[str, int] | None


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
    modifiers = re.findall(r'\[[^\]]*\]', groups.get('attributes') or '')
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


class CSharpObject(ObjectDescription[str]):
    """ Description of generic C# objects """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.parentname_set = False
        self.parentname_saved: str | None = None
        # The generic parameters this object declares for its content, such as T in class List<T>
        self.generic_names: list[str] = []
        self.generic_names_saved: list[str] = []

    def add_target_and_index(self, name: str, _: str, signode: addnodes.desc_signature) -> None:
        targetname = self.objtype + '-' + name
        if targetname not in self.state.document.ids:
            signode['names'].append(targetname)
            signode['ids'].append(targetname)
            signode['first'] = not self.names
            self.state.document.note_explicit_target(signode)

            objects = self.env.domaindata['cs']['objects']
            key = (self.objtype, name)
            if key in objects:
                logger.warning(f'duplicate description of {self.objtype} {name}, ' +
                               f'other instance in {self.env.doc2path(objects[key])}',
                               location=(self.env.docname, self.lineno))
            objects[key] = self.env.docname

        # Sphinx 7 and 8 keep noindexentry as a separate option
        if 'no-index-entry' not in self.options and 'noindexentry' not in self.options:
            indextext = self.get_index_text(name)
            if indextext:
                self.indexnode['entries'].append(('single', indextext, targetname, '', None))

    def get_index_text(self, name: str) -> str:
        """ The general index entry for an object, such as "MyNamespace.MyClass (C# class)" """
        objtype = CSharpDomain.object_types.get(self.objtype)
        if objtype is None:
            return ''
        return _('%s (C# %s)') % (name, objtype.lname)

    def before_content(self) -> None:
        lastname = self.names and self.names[-1]
        if lastname:
            self.parentname_set = True
            self.parentname_saved = self.env.ref_context.get('cs:parent')
            self.env.ref_context['cs:parent'] = lastname
        else:
            self.parentname_set = False
        self.generic_names_saved = self.env.ref_context.get('cs:generic_names', [])
        self.env.ref_context['cs:generic_names'] = self.generic_names_saved + self.generic_names

    def after_content(self) -> None:
        if self.parentname_set:
            self.env.ref_context['cs:parent'] = self.parentname_saved
        self.env.ref_context['cs:generic_names'] = self.generic_names_saved

    def has_parent(self) -> bool:
        return 'cs:parent' in self.env.ref_context and \
            self.env.ref_context['cs:parent'] is not None

    def get_parent(self) -> str:
        parent: str = self.env.ref_context['cs:parent']
        return parent

    def get_fullname(self, name: str) -> str:
        fullname = name
        if self.has_parent():
            fullname = self.get_parent()+'.'+fullname
        return fullname

    @staticmethod
    def append_modifiers(signode: nodes.Element, modifiers: list[str]) -> None:
        if not modifiers:
            return
        for modifier in modifiers:
            signode += addnodes.desc_annotation(modifier, modifier)
            signode += nodes.Text('\xa0')

    def append_type(self, node: nodes.Element, input_typ: str, ignored_types: list[str] | None = None) -> None:
        """ ignored_types is a list of types to ignore in the generics of this type """
        typ, modifiers, generic_types, _, suffix, _, _, nested = parse_type_signature(
            input_typ, (self.env.docname, self.lineno))

        if modifiers:
            self.append_modifiers(node, modifiers)

        if typ.startswith('('):
            self.append_tuple(node, typ, ignored_types)
        else:
            self.append_type_name(node, typ, ExternalRefs.shorten_type(typ), len(generic_types))
        if generic_types:
            self.append_generics(node, generic_types, ignored_types=ignored_types)

        # Each nested type links to its path without the generic arguments, such as List.Enumerator
        outer, outer_arity = typ, len(generic_types)
        for segment in nested:
            name, _, generics, _, _, _, _, _ = parse_type_signature(segment, (self.env.docname, self.lineno))
            typ += '.' + name
            node += nodes.Text('.')
            tnode = self.append_type_name(node, typ, name, len(generics))
            if tnode is not None:
                tnode['cs:outer'] = outer
                tnode['cs:outer_arity'] = outer_arity
            if generics:
                self.append_generics(node, generics, ignored_types=ignored_types)

        if suffix:
            node += nodes.Text(suffix)

    def append_type_name(self, node: nodes.Element, typ: str, text: str, arity: int) -> addnodes.pending_xref | None:
        """ Adds a reference to a type, with arity generic arguments, unless the type is never linked """
        # The generic parameters of an enclosing type are not linked
        if ExternalRefs.check_ignored_ref(typ) or typ in self.env.ref_context.get('cs:generic_names', []):
            node += addnodes.desc_type(text, text)
            return None

        tnode = addnodes.pending_xref(
            '', refdomain='cs', reftype='type',
            reftarget=typ, modname=None, classname=None)

        # Note: this may not be the correct parent namespace
        if not self.has_parent():
            tnode['cs:parent'] = None
        else:
            tnode['cs:parent'] = self.get_parent()
        tnode['cs:arity'] = arity

        tnode += addnodes.desc_type(text, text)
        node += tnode
        return tnode

    def append_tuple(self, node: nodes.Element, tuple_typ: str, ignored_types: list[str] | None) -> None:
        """ Adds a tuple type, such as (int count, string name), linking the type of each element """
        node += nodes.Text('(')
        for i, element in enumerate(split_sig(tuple_typ[1:-1])):
            if i:
                node += nodes.Text(', ')
            match = TUPLE_ELEMENT_RE.match(element)
            if not match:
                raise invalid_signature('Type', tuple_typ, (self.env.docname, self.lineno))
            if ignored_types and match['type'] in ignored_types:
                node += addnodes.desc_type(match['type'], match['type'])
            else:
                self.append_type(node, match['type'], ignored_types)
            if match['name']:
                node += nodes.Text('\xa0' + match['name'])
        node += nodes.Text(')')

    def append_generics(self, node: nodes.Element, generics: list[str], nolink: bool = False,
                        ignored_types: list[str] | None = None) -> None:
        """ nolink will disable xref's, use for newly declared generics in a class declaration,
         ignore_types is similar, but a list of types to disable xrefs for """
        node += nodes.Text('<')
        for i, typ in enumerate(generics):
            if nolink or ignored_types and typ in ignored_types:
                node += addnodes.desc_type(typ, typ)
            else:
                self.append_type(node, typ, ignored_types=ignored_types)
            if i != len(generics) - 1:
                node += nodes.Text(', ')
        node += nodes.Text('>')

    def append_constraints(self, node: nodes.Element, constraints: list[Constraint], generic_params: list[str]) -> None:
        """ Adds generic constraints, without links to the generic parameters """
        for param, types in constraints:
            node += nodes.Text(' ')
            node += addnodes.desc_annotation('where', 'where')
            node += nodes.Text(' ')
            node += addnodes.desc_type(param, param)
            node += nodes.Text(' : ')
            for i, typ in enumerate(types):
                if i:
                    node += nodes.Text(', ')
                if typ in CONSTRAINT_KEYWORDS:
                    node += addnodes.desc_annotation(typ, typ)
                elif typ in generic_params:
                    node += addnodes.desc_type(typ, typ)
                else:
                    self.append_type(node, typ, generic_params)

    def append_inherits(self, node: nodes.Element, inherits: list[str]) -> None:
        """ Adds inherited types, inherits must be a list of string types """
        node += nodes.Text(' : ')
        for (i, typ) in enumerate(inherits):
            match = BASE_ARGS_RE.match(typ)
            self.append_type(node, match['type'] if match else typ)
            if match:
                node += nodes.Text(match['args'])
            if i != len(inherits) - 1:
                node += nodes.Text(', ')

    def append_parameters(self, node: nodes.Element, params: list[ParamTuple],
                          ignore_types: list[str] | None = None) -> None:
        if ignore_types is None:
            ignore_types = []
        pnodes = addnodes.desc_parameterlist()
        for param in params:
            pnode = addnodes.desc_parameter('', '', noemph=True)
            self.append_parameter(pnode, param, ignore_types)
            pnodes += pnode
        node += pnodes

    def append_parameter(self, node: nodes.Element, param: ParamTuple, ignore_types: list[str]) -> None:
        self.append_modifiers(node, param.modifiers)
        if param.typ in ignore_types:
            node += addnodes.desc_type(param.typ, param.typ)
        else:
            self.append_type(node, param.typ, ignore_types)
        node += nodes.Text('\xa0')
        node += nodes.emphasis(param.name, param.name)
        if param.default is not None:
            default = ' = ' + param.default
            node += nodes.emphasis(default, default)

    @staticmethod
    def append_accessors(node: nodes.Element, accessors: list[str]) -> None:
        if not accessors:
            return
        text = ' '.join(accessor + ';' for accessor in accessors)
        node += nodes.Text(' { ')
        node += addnodes.desc_annotation(text, text)
        node += nodes.Text(' }')

    def append_indexer_parameters(self, node: nodes.Element, params: list[ParamTuple]) -> None:
        # Note: Breathe removes desc_addname nodes from signatures, so the parameters go in the signature itself.
        node += nodes.Text('[')
        for i, param in enumerate(params):
            if i:
                node += nodes.Text(', ')
            self.append_parameter(node, param, [])
        node += nodes.Text(']')

    def handle_indexer_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        modifiers, typ, interface, params, accessors = parse_indexer_signature(sig, (self.env.docname, self.lineno))
        name = interface + '.this' if interface else 'this'
        self.append_modifiers(signode, modifiers)
        self.append_type(signode, typ)
        signode += nodes.Text('\xa0')
        signode += addnodes.desc_name(name, name)
        self.append_indexer_parameters(signode, params)
        self.append_accessors(signode, accessors)
        return self.get_fullname(name + '[]')


    def handle_type_signature(self, sig: str, signode: addnodes.desc_signature, keyword: str) -> str:
        """ Handle a type declaration, such as a class, and return its full name """
        typ, modifiers, generics, inherits, _, constraints, params, _ = parse_type_signature(
            sig, (self.env.docname, self.lineno))

        if modifiers:
            self.append_modifiers(signode, modifiers)

        prefix = keyword + ' '
        signode += addnodes.desc_annotation(prefix, prefix)
        signode += addnodes.desc_name(typ, typ)

        if generics:
            self.append_generics(signode, generics, nolink=True)
        # Variance modifiers such as in T come before the parameter name
        generic_params = [generic.split()[-1] for generic in generics]
        self.generic_names = generic_params
        if params is not None:
            signode += nodes.Text('\xa0')
            self.append_parameters(signode, params, generic_params)
        if inherits:
            self.append_inherits(signode, inherits)
        self.append_constraints(signode, constraints, generic_params)
        return self.get_fullname(typ)

    def reset_objtype(self) -> None:
        """ Undo change_objtype for the previous signature of this directive """
        self.objtype = self.name.rpartition(':')[2]

    def change_objtype(self, signode: addnodes.desc_signature, objtype: str) -> None:
        """ Describe this signature as another object type, such as an indexer passed to the property directive """
        self.objtype = objtype
        # The signatures of a directive share one desc node, which takes the object type of the first
        if not self.names:
            desc = signode.parent
            desc['classes'].remove(desc['objtype'])
            desc['objtype'] = desc['desctype'] = objtype
            desc['classes'].append(objtype)


class CSharpCurrentNamespace(Directive):
    """ Set the current C# namespace """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}

    def run(self) -> list[nodes.Node]:
        env = self.state.document.settings.env
        namespace = self.arguments[0].strip()
        if namespace == 'None':
            env.ref_context.pop('cs:parent', None)
        else:
            env.ref_context['cs:parent'] = namespace
        return []


class CSharpNamespacePlain(CSharpObject):
    """ Visual rendering of a C# namespace,
     without updating the parent like the directive CSharpCurrentNamespace.
     Used by breathe. """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        prefix = 'namespace' + ' '
        signode += addnodes.desc_annotation(prefix, prefix)
        signode += addnodes.desc_name(sig, sig)

        return sig


class CSharpType(CSharpObject):
    """ Description of a C# type declaration, such as a class """

    keyword = ''

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        return self.handle_type_signature(sig, signode, self.keyword)


class CSharpClass(CSharpType):
    """ Description of a C# class """
    keyword = 'class'


class CSharpStruct(CSharpType):
    """ Description of a C# struct """
    keyword = 'struct'


class CSharpInterface(CSharpType):
    """ Description of a C# interface """
    keyword = 'interface'


class CSharpRecord(CSharpType):
    """ Description of a C# record, or a record class or record struct if the signature starts with class or struct """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        match = RECORD_KIND_RE.match(sig.strip())
        if not match:
            return self.handle_type_signature(sig, signode, 'record')
        modifiers = match['modifiers'] + ' ' if match['modifiers'] else ''
        return self.handle_type_signature(modifiers + match['sig'], signode, 'record ' + match['kind'])


class CSharpInherits(CSharpObject):
    """ Description of a type that a C# type inherits from """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        signode += nodes.Text(' : ')
        self.append_type(signode, sig)
        return self.get_fullname(sig)


class CSharpMethod(CSharpObject):
    """ Description of a C# method """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        self.reset_objtype()
        match = TYPE_AS_FUNCTION_RE.match(sig.strip())
        if match:
            keyword = ' '.join(match['keyword'].split())
            self.change_objtype(signode, keyword.split()[0])
            modifiers = match['modifiers'] + ' ' if match['modifiers'] else ''
            return self.handle_type_signature(modifiers + match['sig'], signode, keyword)

        modifiers, return_type, name, generic_params, params, constraints, operator = parse_method_signature(
            sig, (self.env.docname, self.lineno))
        if self.objtype == 'delegate' and 'delegate' not in modifiers:
            modifiers.append('delegate')
        if 'delegate' in modifiers and self.objtype != 'delegate':
            self.change_objtype(signode, 'delegate')
        self.append_modifiers(signode, modifiers)

        # A conversion operator names its type after the operator keyword
        if operator is not None and return_type is not None and name in CONVERSION_OPERATORS:
            signode += addnodes.desc_name(operator, operator)
            signode += nodes.Text('\xa0')
            self.append_type(signode, return_type)
            signode += nodes.Text('\xa0')
            self.append_parameters(signode, params)
            return self.get_fullname(name)

        # Variance modifiers such as out T come before the parameter name
        generic_names = [generic.split()[-1] for generic in generic_params]

        # Constructors have no return type
        if return_type is not None:
            # Generic type parameters are not linked
            if return_type in generic_names:
                signode += addnodes.desc_type(return_type, return_type)
            else:
                self.append_type(signode, return_type, generic_names)
            signode += nodes.Text('\xa0')

        display_name = operator or name
        signode += addnodes.desc_name(display_name, display_name)

        if generic_params:
            self.append_generics(signode, generic_params, True)
        signode += nodes.Text('\xa0')

        self.append_parameters(signode, params, generic_names)
        self.append_constraints(signode, constraints, generic_names)

        return self.get_fullname(name)


class CSharpDelegate(CSharpMethod):
    """ Description of a C# delegate """


class CSharpVariable(CSharpObject):
    """ Description of a C# variable """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        modifiers, fulltype, _, _, name, default_value = parse_variable_signature(sig, (self.env.docname, self.lineno))

        self.append_modifiers(signode, modifiers)
        self.append_type(signode, fulltype)
        signode += nodes.Text('\xa0')
        signode += addnodes.desc_name(name, name)

        if default_value:
            signode += nodes.Text(' = ')
            signode += nodes.Text(default_value)

        return self.get_fullname(name)


class CSharpProperty(CSharpObject):
    """ Description of a C# property """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        self.reset_objtype()
        # Doxygen writes indexers as properties named this[...]
        if IDXR_SIG_RE.match(sig.strip()):
            self.change_objtype(signode, 'indexer')
            return self.handle_indexer_signature(sig, signode)

        modifiers, typ, name, accessors, default_val = parse_property_signature(
            sig, (self.env.docname, self.lineno))

        self.append_modifiers(signode, modifiers)
        self.append_type(signode, typ)
        signode += nodes.Text('\xa0')
        signode += addnodes.desc_name(name, name)
        self.append_accessors(signode, accessors)
        if default_val is not None:
            signode += nodes.Text(' = ' + default_val)
        return self.get_fullname(name)


class CSharpEvent(CSharpObject):
    """ Description of a C# event """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        modifiers, fulltype, name, accessors, default_value = parse_property_signature(
            sig, (self.env.docname, self.lineno))

        prefix = 'event' + ' '
        signode += addnodes.desc_annotation(prefix, prefix)

        self.append_modifiers(signode, modifiers)
        self.append_type(signode, fulltype)
        signode += nodes.Text('\xa0')
        signode += addnodes.desc_name(name, name)
        self.append_accessors(signode, accessors)

        if default_value:
            signode += nodes.Text(' = ')
            signode += nodes.Text(default_value)

        return self.get_fullname(name)


class CSharpIndexer(CSharpObject):
    """ Description of a C# indexer """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        return self.handle_indexer_signature(sig, signode)


class CSharpEnum(CSharpObject):
    """ Description of a C# enum """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        modifiers, name, base = parse_enum_signature(sig, (self.env.docname, self.lineno))
        self.append_modifiers(signode, modifiers)
        prefix = 'enum' + ' '
        signode += addnodes.desc_annotation(prefix, prefix)
        signode += addnodes.desc_name(name, name)
        if base:
            signode += nodes.Text(' : ')
            self.append_type(signode, base)
        return self.get_fullname(name)


class CSharpEnumValue(CSharpObject):
    """ Description of a C# enum value """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        name, value = parse_enumerator_signature(sig, (self.env.docname, self.lineno))
        signode += addnodes.desc_name(name, name)
        if value:
            signode += nodes.Text(' = ' + value)
        return self.get_fullname(name)


class CSharpAttribute(CSharpObject):
    """ Description of a C# attribute """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        name, params = parse_attr_signature(sig, (self.env.docname, self.lineno))
        signode += addnodes.desc_name(name, name)
        if params:
            signode += nodes.Text('\xa0')
            self.append_parameters(signode, params)
        return self.get_fullname(name)


class CSharpXRefRole(XRefRole):
    def process_link(self, env: BuildEnvironment, refnode: nodes.Element, has_explicit_title: bool,
                     title: str, target: str) -> tuple[str, str]:
        refnode['cs:parent'] = env.ref_context.get('cs:parent')
        return super().process_link(
            env, refnode, has_explicit_title, title, target)


class CSharpDomain(Domain):
    """ C# domain """
    name = 'cs'
    label = 'C#'

    # Object types and the roles that reference them
    object_types = {
        'namespace': ObjType(_('namespace'), 'namespace'),

        # Types
        'class': ObjType(_('class'), 'class', 'type'),
        'struct': ObjType(_('struct'), 'struct', 'type'),
        'interface': ObjType(_('interface'), 'interface', 'type'),
        'enum': ObjType(_('enum'), 'enum', 'type'),
        'record': ObjType(_('record'), 'record', 'type'),
        # Breathe passes delegates to the function directive
        'delegate': ObjType(_('delegate'), 'delegate', 'type', 'func', 'meth'),

        'function': ObjType(_('function'), 'function', 'func', 'meth', 'member'),

        'var': ObjType(_('var'), 'var', 'member'),
        'property': ObjType(_('property'), 'prop', 'member'),
        'event': ObjType(_('event'), 'event', 'member'),

        'enumerator': ObjType(_('enumerator'), 'enumerator', 'value'),
        'attribute': ObjType(_('attribute'), 'attr'),
        'indexer': ObjType(_('indexer'), 'idxr'),
    }
    directives = {
        'namespace': CSharpCurrentNamespace,

        'class': CSharpClass,
        'struct': CSharpStruct,
        'interface': CSharpInterface,
        'record': CSharpRecord,
        'inherits': CSharpInherits,

        'function': CSharpMethod,
        'delegate': CSharpDelegate,

        'var': CSharpVariable,
        'property': CSharpProperty,
        'event': CSharpEvent,

        'enum': CSharpEnum,
        'enumerator': CSharpEnumValue,
        'attribute': CSharpAttribute,
        'indexer': CSharpIndexer,
    }
    # See https://www.sphinx-doc.org/en/master/usage/restructuredtext/roles.html
    roles = {
        'namespace': CSharpXRefRole(),

        'class': CSharpXRefRole(),
        'struct': CSharpXRefRole(),
        'interface': CSharpXRefRole(),
        'record': CSharpXRefRole(),
        'delegate': CSharpXRefRole(),

        'func': CSharpXRefRole(),
        'meth': CSharpXRefRole(),

        'var': CSharpXRefRole(),
        'prop': CSharpXRefRole(),
        'event': CSharpXRefRole(),
        'member': CSharpXRefRole(),

        'enum': CSharpXRefRole(),
        'enumerator': CSharpXRefRole(),
        'value': CSharpXRefRole(),
        'attr': CSharpXRefRole(),
        'idxr': CSharpXRefRole(),

        'type': CSharpXRefRole(),
        'obj': CSharpXRefRole(),
    }
    initial_data = {
        'objects': {},  # (objtype, fullname) -> docname
    }

    @staticmethod
    def apply_config(_app: "Sphinx", config: Config) -> None:
        """ Read in the config variables, called once the config is initialized (this is a callback) """

        try:
            CSDebug.set_config_values(config)
            ExternalRefs.apply_config(config)
        except Exception as e:
            # Sphinx omits the cause when it reports an ExtensionError, so we log it here
            logger.error(f"Error in CSharpDomain.apply_config(): {e}, \nCheck that your config variables are correct.")
            raise

    def clear_doc(self, docname: str) -> None:
        for (typ, name), doc in dict(self.objects).items():
            if doc == docname:
                del self.objects[typ, name]

    @property
    def objects(self) -> dict[tuple[str, str], str]:
        """ The documented objects, keyed by object type and full name, with the document they are in """
        objects: dict[tuple[str, str], str] = self.data['objects']
        return objects

    def find_objects(self, target: str, parent: str | None, objtypes: Iterable[str],
                     loose: bool = True) -> list[tuple[str, str]]:
        """
        Find the objects of the given types that a target refers to from within a parent namespace.
        Without loose, only the target qualified by the parent or an enclosing namespace matches.
        """
        matches = [key for key in self.objects
                   if key[0] in objtypes and (key[1] == target or key[1].endswith('.' + target))]

        # The parent and each of its enclosing namespaces, innermost first
        scopes = []
        if parent:
            parts = parent.split('.')
            scopes = ['.'.join(parts[:i]) for i in range(len(parts), 0, -1)]

        # Prefer the target qualified by the closest scope, then an object anywhere inside that scope
        for scope in scopes + ['']:
            exact = [key for key in matches if key[1] == (scope + '.' + target if scope else target)]
            if exact:
                return exact
        if not loose:
            return []
        if len(matches) <= 1:
            return matches
        for scope in scopes:
            inside = [key for key in matches if key[1].startswith(scope + '.')]
            if inside:
                return inside
        return matches

    def resolve_xref(self, env: BuildEnvironment, fromdocname: str, builder: Builder, typ: str, target: str,
                     node: addnodes.pending_xref, contnode: nodes.Element) -> nodes.reference | None:
        if target is None:
            # Breathe creates references without a target
            target = contnode.astext()

        objtypes = list(self.object_types) if typ == 'obj' else self.objtypes_for_role(typ) or []
        parent = node.get('cs:parent')

        # A known external type takes precedence over a local object in an unrelated namespace
        matches = self.find_objects(target, parent, objtypes, loose=False)
        if not matches and not ExternalRefs.check_ignored_ref(target):
            if 'cs:outer' in node:
                ref = ExternalRefs.get_nested_external_ref(node['cs:outer'], node['cs:outer_arity'],
                                                           target[len(node['cs:outer']) + 1:], typ, contnode)
            else:
                ref = ExternalRefs.get_external_ref(target, typ, contnode, node.get('cs:arity', 0))
            if ref is not None:
                return ref
            matches = self.find_objects(target, parent, objtypes)

        if len(matches) > 1:
            logger.warning(f'ambiguous reference to {target}, matches: {[name for _, name in matches]}',
                           location=node)
        if matches:
            objtype, name = matches[0]
            return self.make_refnode(builder, fromdocname, objtype, name, contnode)
        if CSDebug.xref:
            logger.info(f'no C# object found for {target}, searched object types {objtypes}', location=node)
        return None

    def resolve_any_xref(self, env: BuildEnvironment, fromdocname: str, builder: Builder, target: str,
                         node: addnodes.pending_xref,
                         contnode: nodes.Element) -> list[tuple[str, nodes.reference]]:
        matches = self.find_objects(target, node.get('cs:parent'), list(self.object_types))
        return [('cs:' + self.object_types[objtype].roles[0],
                 self.make_refnode(builder, fromdocname, objtype, name, contnode))
                for objtype, name in matches]

    def make_refnode(self, builder: Builder, fromdocname: str, objtype: str, name: str,
                     contnode: nodes.Element) -> nodes.reference:
        title = (self.label + ' ' if ExternalRefs.multi_lang else '') + f'{objtype}: {name}'
        return make_refnode(builder, fromdocname, self.objects[objtype, name],
                            objtype + '-' + name, contnode, title)

    def get_objects(self) -> Iterator[tuple[str, str, str, str, str, int]]:
        for (typ, name), docname in self.objects.items():
            yield name, name, typ, docname, typ + '-' + name, 1

    def merge_domaindata(self, docnames: Set[str], otherdata: dict[str, Any]) -> None:
        for key, docname in otherdata['objects'].items():
            if docname in docnames:
                self.objects[key] = docname
