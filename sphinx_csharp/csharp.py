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
                                'virtual', 'volatile', 'ref'])

PARAM_MODIFIERS_RE_SIMPLE = '|'.join(['this', 'ref', 'in', 'out', 'params'])

MODIFIERS_RE = re.compile(r'\s*(?:(?P<modifiers>(?:\s*(?:' + MODIFIERS_RE_SIMPLE + r'))*)\s+)?')
# MODIFIERS_RE with parameter modifiers
PARAM_MODIFIERS_RE = re.compile(r'\s*(?:(?P<modifiers>(?:\s*(?:' + PARAM_MODIFIERS_RE_SIMPLE + r'))*)\s+)?\s*')


TYPE_RE = re.compile(r'(?:template(?P<templates><\s*.+\s*>))?\s*'
                     r'(?P<fulltype>(?P<type>[^\s<\[{*&?]+)\s*(?P<generics><\s*.+\s*>)?\s*'
                     r'(?P<array>(\[,*\])*)?\s*(?P<ptr>[*&?])?)\??')

TYPE_OPTIONAL_RE = re.compile(r'(?:template(?P<templates><\s*.+\s*>))?\s*'
                              r'(?:(?P<fulltype>(?P<type>[^\s<\[{*&?]+)\s*(?P<generics><\s*.+\s*>)?\s*'
                              r'(?P<array>(\[,*\])*)?\s*(?P<ptr>[*&?])?)\s+)?\??')

METH_SIG_RE = re.compile(
    r'^' + MODIFIERS_RE.pattern + TYPE_OPTIONAL_RE.pattern +
    r'(?P<fname>[^\s<(]+)\s*'
    r'(?P<genericparams><[^(]+>)?\s*'
    r'\((?P<params>.*)?\)$')

VAR_SIG_RE = re.compile(
    r'^' + MODIFIERS_RE.pattern + TYPE_RE.pattern + r'\s+(?P<name>[^\s<{(=]+)\s*(?:=\s*(?P<value>.+))?$')
VAR_PARAM_SIG_RE = re.compile(
    r'^' + PARAM_MODIFIERS_RE.pattern + TYPE_RE.pattern + r'\s+(?P<name>[^\s<{=]+)\s*(?:=\s*(?P<value>.+))?$')

PROP_SIG_RE = re.compile(
    r'^' + MODIFIERS_RE.pattern + TYPE_RE.pattern + r'\s+(?P<name>[^\s<{(=]+)\s*'
    r'{\s*(?P<getter>get;)?\s*(?P<setter>set;)?\s*}\s*(?:=\s*(?P<value>.+?))?\s*$')

IDXR_SIG_RE = re.compile(
    r'^((?:(?:' + MODIFIERS_RE_SIMPLE +
    r')\s+)*)([^\s]+)\s*this\s*\[\s*((?:[^\s]+)\s+(?:[^\s]+)' +
    r'(?:\s*,\s*(?:[^\s]+)\s+(?:[^\s]+))*)\s*\]\s*' +
    r'{\s*(get;)?\s*(set;)?\s*}$')

INHERITS_RE = re.compile(r'(?:\s*:\s*(?P<inherits>.*))?')
CLASS_SIG_RE = re.compile(r'^' + MODIFIERS_RE.pattern + TYPE_RE.pattern + INHERITS_RE.pattern + r'$')

ATTR_SIG_RE = re.compile(r'^([^\s]+)(\s+\((.*)\))?$')

# Source location of a signature, as a (docname, line) pair
Location = tuple[str, int] | None


class ParamTuple(NamedTuple):
    name: str
    typ: str
    default: str | None
    modifiers: list[str]


class MethodSig(NamedTuple):
    modifiers: list[str]
    return_type: str | None
    name: str
    generic_params: list[str]
    params: list[ParamTuple]


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
    getter: bool
    setter: bool
    default: str | None


class IndexerSig(NamedTuple):
    modifiers: list[str]
    return_type: str
    params: list[ParamTuple]
    getter: bool
    setter: bool


class TypeSig(NamedTuple):
    typ: str
    modifiers: list[str]
    generics: list[str]
    inherits: list[str]
    array: str | None
    ptr: str | None


class AttrSig(NamedTuple):
    name: str
    params: list[ParamTuple]


logger = logging.getLogger(__name__)


def split_sig(params: str) -> list[str]:
    """
    Split a list of parameters/types by commas,
    whilst respecting brackets.

    For example:
      String arg0, int arg2 = 1, List<int> arg3 = [1, 2, 3]
      => ['String arg0', 'int arg2 = 1', 'List<int> arg3 = [1, 2, 3]']
    """
    result = []
    current = ''
    level = 0
    for char in params:
        if char in ('<', '{', '['):
            level += 1
        elif char in ('>', '}', ']'):
            level -= 1
        if char != ',' or level > 0:
            current += char
        elif char == ',' and level == 0:
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


def parse_method_signature(sig: str, location: Location) -> MethodSig:
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

    result = MethodSig(modifiers, return_type, groups['fname'], generic_params, params)
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
    modifiers = groups['modifiers'].split() if groups['modifiers'] else []
    # The templates group is the Doxygen form of the generics
    generics = split_generics(groups['generics'] or groups['templates'])

    result = VariableSig(modifiers, groups['fulltype'].strip(), groups['type'], generics,
                         groups['name'], groups['value'])
    if CSDebug.parse_var:
        logger.info(f"parsed var: {tuple(result)}")
    return result


def parse_property_signature(sig: str, location: Location) -> PropertySig:
    """ Parse a property signature of the form:
        modifier* type name { (get;)? (set;)? } """
    match = PROP_SIG_RE.match(sig.strip())
    if not match:
        if CSDebug.parse_prop:
            logger.info(f'Property signature not valid, falling back to variable: {sig}', location=location)
        var = parse_variable_signature(sig, location)
        return PropertySig(var.modifiers, var.fulltype, var.name, False, False, var.default)

    groups = match.groupdict()
    modifiers = groups['modifiers'].split() if groups['modifiers'] else []
    result = PropertySig(modifiers, groups['fulltype'].strip(), groups['name'],
                         groups['getter'] is not None, groups['setter'] is not None, groups['value'])
    if CSDebug.parse_prop:
        logger.info(f"parsed prop: {tuple(result)}")
    return result


def parse_indexer_signature(sig: str, location: Location) -> IndexerSig:
    """ Parse a indexer signature of the form:
        modifier* type this[params] { (get;)? (set;)? } """
    match = IDXR_SIG_RE.match(sig.strip())
    if not match:
        raise invalid_signature('Indexer', sig, location)

    modifiers, return_type, params, getter, setter = match.groups()
    result = IndexerSig(modifiers.split(), return_type, parse_params(params, location),
                        getter is not None, setter is not None)
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

    result = TypeSig(groups['type'], modifiers, generics, inherits, groups['array'], groups['ptr'])
    if CSDebug.parse_type:
        logger.info(f"parsed type: {tuple(result)}")
    return result


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

        indextext = self.get_index_text(name)
        if indextext:
            self.indexnode['entries'].append(
                ('single', indextext, targetname, ''))

    def get_index_text(self, name: str) -> str:
        if self.objtype == 'directive':
            return _('%s (directive)') % name
        if self.objtype == 'role':
            return _('%s (role)') % name
        return ''

    def before_content(self) -> None:
        lastname = self.names and self.names[-1]
        if lastname:
            self.parentname_set = True
            self.parentname_saved = self.env.ref_context.get('cs:parent')
            self.env.ref_context['cs:parent'] = lastname
        else:
            self.parentname_set = False

    def after_content(self) -> None:
        if self.parentname_set:
            self.env.ref_context['cs:parent'] = self.parentname_saved

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
        typ, modifiers, generic_types, _, array, ptr = parse_type_signature(
            input_typ, (self.env.docname, self.lineno))

        if modifiers:
            self.append_modifiers(node, modifiers)

        typ_short = ExternalRefs.shorten_type(typ)
        if ExternalRefs.check_ignored_ref(typ):
            node += addnodes.desc_type(typ_short, typ_short)
        else:
            tnode = addnodes.pending_xref(
                '', refdomain='cs', reftype='type',
                reftarget=typ, modname=None, classname=None)

            # Note: this may not be the correct parent namespace
            if not self.has_parent():
                tnode['cs:parent'] = None
            else:
                tnode['cs:parent'] = self.get_parent()
            tnode['cs:arity'] = len(generic_types)

            tnode += addnodes.desc_type(typ_short, typ_short)
            node += tnode

        if generic_types:
            self.append_generics(node, generic_types, ignored_types=ignored_types)
        if array:
            node += nodes.Text(array)
        if ptr:
            node += nodes.Text(ptr)

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

    def append_inherits(self, node: nodes.Element, inherits: list[str]) -> None:
        """ Adds inherited types, inherits must be a list of string types """
        node += nodes.Text(' : ')
        for (i, typ) in enumerate(inherits):
            self.append_type(node, typ)
            if i != len(inherits) - 1:
                node += nodes.Text(', ')

    def append_parameters(self, node: nodes.Element, params: list[ParamTuple],
                          ignore_types: list[str] | None = None) -> None:
        if ignore_types is None:
            ignore_types = []
        pnodes = addnodes.desc_parameterlist()
        for param in params:
            pnode = addnodes.desc_parameter('', '', noemph=True)

            self.append_modifiers(pnode, param.modifiers)

            if ignore_types and param.typ in ignore_types:
                pnode += addnodes.desc_type(param.typ, param.typ)
            else:
                self.append_type(pnode, param.typ, ignore_types)
            pnode += nodes.Text('\xa0')
            pnode += nodes.emphasis(param.name, param.name)
            if param.default is not None:
                default = ' = ' + param.default
                pnode += nodes.emphasis(default, default)
            pnodes += pnode
        node += pnodes

    def append_indexer_parameters(self, node: nodes.Element, params: list[ParamTuple]) -> None:
        pnodes = addnodes.desc_addname()
        pnodes += nodes.Text('[')

        for param in params:
            if pnodes.children:
                pnodes += nodes.Text(', ')

            self.append_type(pnodes, param.typ)
            pnodes += nodes.Text('\xa0')
            pnodes += nodes.emphasis(param.name, param.name)

        pnodes += nodes.Text(']')
        node += pnodes


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
        typ, modifiers, generics, inherits, _, _ = parse_type_signature(sig, (self.env.docname, self.lineno))

        if modifiers:
            self.append_modifiers(signode, modifiers)

        prefix = self.keyword + ' '
        signode += addnodes.desc_annotation(prefix, prefix)
        signode += addnodes.desc_name(typ, typ)

        if generics:
            self.append_generics(signode, generics, nolink=True)
        if inherits:
            self.append_inherits(signode, inherits)
        return self.get_fullname(typ)


class CSharpClass(CSharpType):
    """ Description of a C# class """
    keyword = 'class'


class CSharpStruct(CSharpType):
    """ Description of a C# struct """
    keyword = 'struct'


class CSharpInterface(CSharpType):
    """ Description of a C# interface """
    keyword = 'interface'


class CSharpInherits(CSharpObject):
    """ Description of a type that a C# type inherits from """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        signode += nodes.Text(' : ')
        self.append_type(signode, sig)
        return self.get_fullname(sig)


class CSharpMethod(CSharpObject):
    """ Description of a C# method """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        modifiers, return_type, name, generic_params, params = parse_method_signature(
            sig, (self.env.docname, self.lineno))
        self.append_modifiers(signode, modifiers)

        # Constructors have no return type
        if return_type is not None:
            # Generic type parameters are not linked
            if generic_params and return_type in generic_params:
                signode += addnodes.desc_type(return_type, return_type)
            else:
                self.append_type(signode, return_type)
            signode += nodes.Text('\xa0')

        signode += addnodes.desc_name(name, name)

        if generic_params:
            self.append_generics(signode, generic_params, True)
        signode += nodes.Text('\xa0')

        self.append_parameters(signode, params, generic_params)

        return self.get_fullname(name)


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
        modifiers, typ, name, getter, setter, default_val = parse_property_signature(
            sig, (self.env.docname, self.lineno))

        self.append_modifiers(signode, modifiers)
        self.append_type(signode, typ)
        signode += nodes.Text('\xa0')
        signode += addnodes.desc_name(name, name)
        signode += nodes.Text(' { ')
        extra = []
        if getter:
            extra.append('get;')
        if setter:
            extra.append('set;')
        extra_str = ' '.join(extra)
        signode += addnodes.desc_annotation(extra_str, extra_str)
        signode += nodes.Text(' }')
        if default_val is not None:
            signode += nodes.Text(' = ' + default_val)
        return self.get_fullname(name)


class CSharpEvent(CSharpObject):
    """ Description of a C# event """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        modifiers, fulltype, _, _, name, default_value = parse_variable_signature(sig, (self.env.docname, self.lineno))

        prefix = 'event' + ' '
        signode += addnodes.desc_annotation(prefix, prefix)

        self.append_modifiers(signode, modifiers)
        self.append_type(signode, fulltype)
        signode += nodes.Text('\xa0')
        signode += addnodes.desc_name(name, name)

        if default_value:
            signode += nodes.Text(' = ')
            signode += nodes.Text(default_value)

        return self.get_fullname(name)


class CSharpIndexer(CSharpObject):
    """ Description of a C# indexer """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        modifiers, typ, params, getter, setter = parse_indexer_signature(sig, (self.env.docname, self.lineno))
        self.append_modifiers(signode, modifiers)
        self.append_type(signode, typ)
        signode += nodes.Text('\xa0')
        signode += addnodes.desc_name('this[]', 'this')
        self.append_indexer_parameters(signode, params)
        signode += nodes.Text(' { ')
        extra = []
        if getter:
            extra.append('get;')
        if setter:
            extra.append('set;')
        extra_str = ' '.join(extra)
        signode += addnodes.desc_annotation(extra_str, extra_str)
        signode += nodes.Text(' }')
        return self.get_fullname('this[]')


class CSharpEnum(CSharpObject):
    """ Description of a C# enum """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        prefix = 'enum' + ' '
        signode += addnodes.desc_annotation(prefix, prefix)
        signode += addnodes.desc_name(sig, sig)
        return self.get_fullname(sig)


class CSharpEnumValue(CSharpObject):
    """ Description of a C# enum value """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        name = sig
        signode += addnodes.desc_name(name, name)
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
        'inherits': CSharpInherits,

        'function': CSharpMethod,

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
        'ref': CSharpXRefRole(),
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

    def find_objects(self, target: str, parent: str | None, objtypes: Iterable[str]) -> list[tuple[str, str]]:
        """ Find the objects of the given types that a target refers to from within a parent namespace """
        matches = [key for key in self.objects
                   if key[0] in objtypes and (key[1] == target or key[1].endswith('.' + target))]
        if len(matches) <= 1:
            return matches

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

        objtypes = list(self.object_types) if typ == 'ref' else self.objtypes_for_role(typ) or []
        matches = self.find_objects(target, node.get('cs:parent'), objtypes)
        if len(matches) > 1:
            logger.warning(f'ambiguous reference to {target}, matches: {[name for _, name in matches]}',
                           location=node)
        if matches:
            objtype, name = matches[0]
            return self.make_refnode(builder, fromdocname, objtype, name, contnode)

        if ExternalRefs.check_ignored_ref(target):
            return None
        ref = ExternalRefs.get_external_ref(target, typ, contnode, node.get('cs:arity', 0))
        if ref is None and CSDebug.xref:
            logger.info(f'no C# object found for {target}, searched object types {objtypes}', location=node)
        return ref

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
