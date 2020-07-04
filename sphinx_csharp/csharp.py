""" C# sphinx domain """

from .debug import CSDebug

import re
from collections import namedtuple
from typing import List

import requests
from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.domains import Domain, ObjType
from sphinx.locale import _
from sphinx.directives import ObjectDescription
from sphinx.roles import XRefRole
from sphinx.util.nodes import make_refnode
from sphinx.util import logging

MODIFIERS_RE_SIMPLE = '|'.join(['public', 'private', 'internal', 'protected',
                                'abstract', 'async', 'const', 'event', 'delegate',
                                'extern', 'new', 'override', 'partial',
                                'readonly', 'sealed', 'static', 'unsafe',
                                'virtual', 'volatile', 'ref'])

PARAM_MODIFIERS_RE_SIMPLE = '|'.join(['this', 'ref', 'in', 'out', 'params'])

MODIFIERS_RE = r'\s*(?:(?P<modifiers>(?:\s*(?:' + MODIFIERS_RE_SIMPLE + r'))*)\s+)?'
# Exaclty the same but with param modifiers
PARAM_MODIFIERS_RE = r'\s*(?:(?P<modifiers>(?:\s*(?:' + PARAM_MODIFIERS_RE_SIMPLE + r'))*)\s+)?\s*'


TYPE_RE = r'(?:template(?P<templates><\s*.+\s*>))?\s*' \
          r'(?P<fulltype>(?P<type>[^\s<\[{\*&\?]+)\s*(?P<generics><\s*.+\s*>)?\s*' \
          r'(?P<array>\[,*\])?\s*(?P<ptr>\*|&)?)\??'

TYPE_OPTIONAL_RE = r'(?:template(?P<templates><\s*.+\s*>))?\s*' \
          r'(?:(?P<fulltype>(?P<type>[^\s<\[{\*&\?]+)\s*(?P<generics><\s*.+\s*>)?\s*' \
          r'(?P<array>\[,*\])?\s*(?P<ptr>\*|&)?)\s+)?\??'

METH_SIG_RE = re.compile(
    r'^' + MODIFIERS_RE + TYPE_OPTIONAL_RE + r'(?P<fname>[^\s<(]+)\s*'
                                    r'(?P<genericparams><[^\(]+>)?\s*'
                                    r'\((?P<params>.*)?\)$')

VAR_SIG_RE = re.compile(
    r'^' + MODIFIERS_RE + TYPE_RE + '\s+(?P<name>[^\s<{]+)\s*(?:=\s*(?P<value>.+))?$')
VAR_PARAM_SIG_RE = re.compile(
    r'^' + PARAM_MODIFIERS_RE + TYPE_RE + '\s+(?P<name>[^\s<{]+)\s*(?:=\s*(?P<value>.+))?$')

PROP_SIG_RE = re.compile(
    r'^([^\s]+\s+)*([^\s]+)\s+([^\s]+)\s*\{\s*(get;)?\s*(set;)?\s*\}$')

IDXR_SIG_RE = re.compile(
    r'^((?:(?:' + MODIFIERS_RE_SIMPLE +
    r')\s+)*)([^\s]+)\s*this\s*\[\s*((?:[^\s]+)\s+(?:[^\s]+)' +
    r'(?:\s*,\s*(?:[^\s]+)\s+(?:[^\s]+))*)\s*\]\s*' +
    r'\{\s*(get;)?\s*(set;)?\s*\}$')
#
# PARAM_SIG_RE = re.compile(
#     r'^((?:(?:' + PARAM_MODIFIERS_RE +
#     r')\s+)*)(.+)\s+([^\s]+)\s*(=\s*(.+))?$')

INHERITS_RE = r'(?:\s*:\s*(?P<inherits>.*))?'
CLASS_SIG_RE = re.compile(r'^' + MODIFIERS_RE + TYPE_RE + INHERITS_RE + r'$')

ATTR_SIG_RE = re.compile(r'^([^\s]+)(\s+\((.*)\))?$')

ParamTuple = namedtuple('ParamTuple', ['name', 'typ', 'default', 'modifiers'])

logger = logging.getLogger(__name__)


def split_sig(params):
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


def parse_method_signature(sig):
    """ Parse a method signature of the form: modifier* type name (params) """
    match = METH_SIG_RE.match(sig.strip())
    if not match:
        logger.warning('Method signature invalid: ' + sig)
        return sig.strip(), None, None, None, None, None

    groups = match.groupdict()
    modifiers = groups['modifiers']
    return_type = groups['fulltype']
    name = groups['fname']
    generic_params = groups['genericparams']
    params = groups['params']

    if not modifiers:
        modifiers = []
    else:
        modifiers = modifiers.split()

    if return_type:
        return_type = return_type.strip()

    if params.strip() != '':
        params = split_sig(params)
        params = [parse_param_signature(x) for x in params]
    else:
        params = []

    if CSDebug.parse_func:
        logger.info(f"parsed func: {modifiers, return_type, name, generic_params, params}")
    return modifiers, return_type, name, generic_params, params


def parse_variable_signature(sig, is_param=False):
    """
    Parse a variable signature of the form:
    modifier* type name
    is_param: interpret as parameter? uses parameter modifiers
    """
    match = (VAR_PARAM_SIG_RE if is_param else VAR_SIG_RE).match(sig.strip())
    if not match:
        logger.warning(('Parameter' if is_param else 'Variable') + ' signature invalid: ' + sig)
        return sig.strip(), None, None, None, None, None
    groups = match.groupdict()
    modifiers = groups['modifiers']
    fulltype = groups['fulltype'].strip()
    typ = groups['type']
    generics = groups['generics']
    if not generics:
        generics = groups['templates']
    name = groups['name']
    default_value = groups['value']

    if not modifiers:
        modifiers = []
    else:
        modifiers = modifiers.split()

    if not generics:
        generics = []
    else:
        # Remove outermost < > brackets
        generics = split_sig(generics[1:-1])

    if CSDebug.parse_var:
        logger.info(f"parsed var: {modifiers, fulltype, typ, generics, name, default_value}")
    return modifiers, fulltype, typ, generics, name, default_value


def parse_property_signature(sig):
    """ Parse a property signature of the form:
        modifier* type name { (get;)? (set;)? } """
    match = PROP_SIG_RE.match(sig.strip())
    if not match:
        logger.info(f'Property signature not valid, falling back to variable: {sig}')
        modifiers, fulltype, typ, generics, name, value = parse_variable_signature(sig)
        return modifiers, fulltype, name, False, False
    groups = match.groups()
    if groups[0] is not None:
        modifiers = [x.strip() for x in groups[:-4]]
        groups = groups[-4:]
    else:
        modifiers = []
        groups = groups[1:]
    typ, name, getter, setter = groups

    if CSDebug.parse_prop:
        logger.info(f"parsed prop: {modifiers, typ, name, getter is not None, setter is not None}")
    return modifiers, typ, name, getter is not None, setter is not None


def parse_indexer_signature(sig):
    """ Parse a indexer signature of the form:
        modifier* type this[params] { (get;)? (set;)? } """
    match = IDXR_SIG_RE.match(sig.strip())
    if not match:
        logger.warning('Indexer signature invalid: ' + sig)
        # TODO: return a better default value?
        return sig.strip(), None, None, False, False
    modifiers, return_type, params, getter, setter = match.groups()
    params = split_sig(params)
    params = [parse_param_signature(x) for x in params]

    if CSDebug.parse_idxr:
        logger.info(f"parsed idxr: {modifiers.split(), return_type, params, getter is not None, setter is not None}")

    return modifiers.split(), return_type, params, getter is not None, setter is not None


def parse_param_signature(sig):
    """ Parse a parameter signature of the form: type name (= default)?
        Interprets as a variable with different modifiers """
    modifiers, fulltype, typ, generics, name, default_value = parse_variable_signature(sig, True)
    if not fulltype:
        logger.warning('Parameter signature invalid, got ' + sig)
        return ParamTuple(sig.strip(), None, None, None)

    return ParamTuple(name=name, typ=fulltype, default=default_value, modifiers=modifiers)


def parse_type_signature(sig):
    """ Parse a type signature """
    match = CLASS_SIG_RE.match(sig.strip())
    if not match:
        logger.warning('Type signature invalid, got ' + sig)
        return sig.strip(), None, None, None, None
    groups = match.groupdict()
    typ = groups['type']
    generics = groups['generics']
    if not generics:
        # In case where input is from doxygen, it is in C++ style
        generics = groups['templates']
    inherited_types = groups['inherits']
    array = groups['array']
    ptr = groups['ptr']

    if not generics:
        generics = []
    else:
        # Remove outermost < > brackets
        generics = split_sig(generics[1:-1])

    if not inherited_types:
        inherited_types = []
    else:
        inherited_types = split_sig(inherited_types)

    if CSDebug.parse_type:
        logger.info(f"parsed type: {typ, generics, inherited_types, array}")
    return typ, generics, inherited_types, array, ptr


def parse_attr_signature(sig):
    """ Parse an attribute signature """
    match = ATTR_SIG_RE.match(sig.strip())
    if not match:
        logger.warning('Attribute signature invalid, got ' + sig)
        return sig.strip(), None
    name, _, params = match.groups()
    if params is not None and params.strip() != '':
        params = split_sig(params)
        params = [parse_param_signature(x) for x in params]
    else:
        params = []

    if CSDebug.parse_attr:
        logger.info(f"parsed attr: {name, params}")
    return name, params


SHORTEN_TYPE_PREFIXES = [
    'System.',
    'System.Collections.Generic.',
]


def shorten_type(typ):
    """ Shorten a type. E.g. drops 'System.' """
    offset = 0
    for prefix in SHORTEN_TYPE_PREFIXES:
        if typ.startswith(prefix):
            if len(prefix) > offset:
                offset = len(prefix)
    return typ[offset:]


class CSharpObject(ObjectDescription):
    """ Description of generic C# objects """

    def __init__(self, *args, **kwargs):
        super(CSharpObject, self).__init__(*args, **kwargs)
        self.parentname_set = None
        self.parentname_saved = None

    def add_target_and_index(self, name, _, signode):
        targetname = self.objtype + '-' + name
        if targetname not in self.state.document.ids:
            signode['names'].append(targetname)
            signode['ids'].append(targetname)
            signode['first'] = (not self.names)
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

    def get_index_text(self, name):
        if self.objtype == 'directive':
            return _('%s (directive)') % name
        if self.objtype == 'role':
            return _('%s (role)') % name
        return ''

    def before_content(self):
        lastname = self.names and self.names[-1]
        if lastname:
            self.parentname_set = True
            self.parentname_saved = self.env.ref_context.get('cs:parent')
            self.env.ref_context['cs:parent'] = lastname
        else:
            self.parentname_set = False

    def after_content(self):
        if self.parentname_set:
            self.env.ref_context['cs:parent'] = self.parentname_saved

    def has_parent(self):
        return 'cs:parent' in self.env.ref_context and \
            self.env.ref_context['cs:parent'] is not None

    def get_parent(self):
        return self.env.ref_context['cs:parent']

    def get_fullname(self, name):
        fullname = name
        if self.has_parent():
            fullname = self.get_parent()+'.'+fullname
        return fullname

    @staticmethod
    def append_modifiers(signode, modifiers):
        if not modifiers:
            return
        for modifier in modifiers:
            signode += addnodes.desc_annotation(modifier, modifier)

    def append_type(self, node, input_typ):
        typ, generic_types, inherited_types, array, ptr = parse_type_signature(input_typ)
        tnode = addnodes.pending_xref(
            '', refdomain='cs', reftype='type',
            reftarget=typ, modname=None, classname=None)

        # Note: this may not be the correct parent namespace
        if not self.has_parent():
            tnode['cs:parent'] = None
        else:
            tnode['cs:parent'] = self.get_parent()

        typ_short = shorten_type(typ)
        tnode += addnodes.desc_type(typ_short, typ_short)
        node += tnode

        if generic_types:
            self.append_generics(node, generic_types)
        if array:
            node += nodes.Text(array)
        if ptr:
            node += nodes.Text(ptr)

    def append_generics(self, node, generics: List[str], nolink=False):
        """ nolink will disable xref's, use for newly declared generics in a class declaration """
        node += nodes.Text('<')
        for i, typ in enumerate(generics):
            if nolink:
                node += addnodes.desc_type(typ, typ)
            else:
                self.append_type(node, typ)
            if i != len(generics) - 1:
                node += nodes.Text(', ')
        node += nodes.Text('>')

    def append_inherits(self, node, inherits: List[str]):
        """ Adds inherited types, inherits must be a list of string types """
        node += nodes.Text(' : ')
        for (i, typ) in enumerate(inherits):
            self.append_type(node, typ)
            if i != len(inherits) - 1:
                node += nodes.Text(', ')

    def append_parameters(self, node, params):
        pnodes = addnodes.desc_parameterlist()
        for param in params:
            pnode = addnodes.desc_parameter('', '', noemph=True)

            self.append_modifiers(pnode, param.modifiers)

            self.append_type(pnode, param.typ)
            pnode += nodes.Text('\xa0')
            pnode += nodes.emphasis(param.name, param.name)
            if param.default is not None:
                default = ' = ' + param.default
                pnode += nodes.emphasis(default, default)
            pnodes += pnode
        node += pnodes

    def append_indexer_parameters(self, node, params):
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

    def run(self):
        env = self.state.document.settings.env
        namespace = self.arguments[0].strip()
        if namespace == 'None':
            env.ref_context.pop('cs:parent', None)
        else:
            env.ref_context['cs:parent'] = namespace
        return []


class CSharpClass(CSharpObject):
    """ Description of a C# class """

    def handle_signature(self, sig, signode):
        typ, generics, inherits, _, _ = parse_type_signature(sig)
        prefix = 'class' + ' '
        signode += addnodes.desc_annotation(prefix, prefix)
        signode += addnodes.desc_name(typ, typ)

        if generics:
            self.append_generics(signode, generics, nolink=True)
        if inherits:
            self.append_inherits(signode, inherits)
        return self.get_fullname(typ)


class CSharpStruct(CSharpObject):
    """ Description of a C# class """

    def handle_signature(self, sig, signode):
        typ, generics, inherits, _, _ = parse_type_signature(sig)
        prefix = 'struct' + ' '
        signode += addnodes.desc_annotation(prefix, prefix)
        signode += addnodes.desc_name(typ, typ)

        if generics:
            self.append_generics(signode, generics, nolink=True)
        if inherits:
            self.append_inherits(signode, inherits)
        return self.get_fullname(typ)


class CSharpInterface(CSharpObject):
    """ Description of a C# interface """

    def handle_signature(self, sig, signode):
        typ, generics, inherits, _, _ = parse_type_signature(sig)
        prefix = 'interface' + ' '
        signode += addnodes.desc_annotation(prefix, prefix)
        signode += addnodes.desc_name(typ, typ)

        if generics:
            self.append_generics(signode, generics, nolink=True)
        if inherits:
            self.append_inherits(signode, inherits)
        return self.get_fullname(typ)


class CSharpInherits(CSharpObject):
    """ Description of an inherited C# struct """

    def handle_signature(self, sig, signode):
        typ, _, _, _, _ = parse_type_signature(sig)
        signode += nodes.Text(': ')
        self.append_type(signode, sig)
        return self.get_fullname(typ)


class CSharpMethod(CSharpObject):
    """ Description of a C# method """

    def handle_signature(self, sig, signode):
        modifiers, return_type, name, generic_params, params = parse_method_signature(sig)
        self.append_modifiers(signode, modifiers)

        # note: constructors don't have a return type
        if return_type is not None:
            if generic_params and return_type in generic_params:
                signode += nodes.Text(return_type)
            else:
                self.append_type(signode, return_type)
            signode += nodes.Text('\xa0')

        signode += addnodes.desc_name(name, name)

        if generic_params is not None:
            signode += nodes.Text(generic_params)
        signode += nodes.Text('\xa0')

        self.append_parameters(signode, params)

        return self.get_fullname(name)


class CSharpVariable(CSharpObject):
    """ Description of a C# variable """

    def handle_signature(self, sig, signode):
        modifiers, fulltype, _, _, name, default_value = parse_variable_signature(sig)

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

    def handle_signature(self, sig, signode):
        modifiers, typ, name, getter, setter = parse_property_signature(sig)

        self.append_modifiers(signode, modifiers)
        if typ:
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
        return self.get_fullname(name)


class CSharpEvent(CSharpObject):
    """ Description of a C# event """

    def handle_signature(self, sig, signode):
        # Remove namespace for now, I think events are not yet supported by breathe?
        modifiers, fulltype, _, _, name, default_value = parse_variable_signature(sig)

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

    def handle_signature(self, sig, signode):
        modifiers, typ, params, getter, setter = parse_indexer_signature(sig)
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

    def handle_signature(self, sig, signode):
        prefix = 'enum' + ' '
        signode += addnodes.desc_annotation(prefix, prefix)
        signode += addnodes.desc_name(sig, sig)
        return self.get_fullname(sig)


class CSharpEnumValue(CSharpObject):
    """ Description of a C# enum value """

    def handle_signature(self, sig, signode):
        name = sig
        signode += addnodes.desc_name(name, name)
        return self.get_fullname(name)


class CSharpAttribute(CSharpObject):
    """ Description of a C# attribute """

    def handle_signature(self, sig, signode):
        name, params = parse_attr_signature(sig)
        signode += addnodes.desc_name(name, name)
        if params:
            signode += nodes.Text('\xa0')
            self.append_parameters(signode, params)
        return self.get_fullname(name)


class CSharpXRefRole(XRefRole):
    def process_link(self, env, refnode, has_explicit_title, title, target):
        refnode['cs:parent'] = env.ref_context.get('cs:parent')
        return super(CSharpXRefRole, self).process_link(
            env, refnode, has_explicit_title, title, target)


class CSharpDomain(Domain):
    """ C# domain """
    name = 'cs'
    label = 'C#'

    object_types = {
        # 'key': ObjType(_('key in directives?'), 'roles keys that can reference this')
        'namespace': ObjType(_('namespace'), 'namespace'),

        'class': ObjType(_('class'), 'type', 'class'),
        'struct': ObjType(_('struct'), 'type', 'struct'),
        'interface': ObjType(_('interface'), 'type', 'interface'),

        'function': ObjType(_('function'), 'type', 'function', 'func', 'meth'),
        # 'method': ObjType(_('method'), 'type', 'meth'),

        'var': ObjType(_('var'), 'var', 'member', 'type'),
        'property': ObjType(_('property'), 'prop'),
        'event': ObjType(_('event'), 'type', 'event'),
        'member': ObjType(_('member'), 'member', 'var'),

        'enum': ObjType(_('enum'), 'type', 'enum'),
        'enumerator': ObjType(_('enumerator'), 'enumerator'),
        'attribute': ObjType(_('attribute'), 'attr'),
        'indexer': ObjType(_('indexer'), 'idxr'),

    }
    directives = {
        'namespace': CSharpCurrentNamespace,

        'class':     CSharpClass,
        'struct':    CSharpStruct,
        'interface': CSharpClass,
        'inherits':  CSharpInherits,

        'function':  CSharpMethod,
        # 'method':    CSharpMethod,

        'var':       CSharpVariable,
        'property':  CSharpProperty,
        'event':     CSharpEvent,
        'member':    CSharpVariable,

        'enum':      CSharpEnum,
        'enumerator': CSharpEnumValue,
        'attribute': CSharpAttribute,
        'indexer':   CSharpIndexer,
    }
    roles = {
        # 'key, rst to write a reference': 'type of reference'
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
    }
    initial_data = {
        'objects': {},  # fullname -> docname, objtype
    }

    extlink_cache = {}

    # --- External Linking ---

    """ Types and strings to ignore when looking for a reference """
    ignore_xref_types = [
        '*',
        '&',
        'void',

        # Built-in types
        'string',
        'bool',
        'int',
        'long',
        'uint',
        'ulong',
        'float',
        'double',
        'byte',
        'object',
    ]

    """
    Contains recognised types and their namespaces as well as the package name.
    The package name references the key in external_search_pages
    
    Format the content like this:
    Where Namespace1 is the namespace for the link (which may not match the real namespace)::
    
        'package': {
            'Namespace1': ['member1', ...],
            ...
        },
        ...
    """
    external_type_map = {
        'msdn': {
            'System': ['Tuple', 'IDisposable', 'ICloneable', 'IComparable', 'Func', 'Action'],
            'System.Collections': ['IEnumerator'],
            'System.Collections.Generic': ['List', 'Dictionary', 'IList', 'IDictionary', 'ISet', 'IEnumerable'],
            'System.Threading': ['Thread'],
            'System.Runtime.InteropServices': ['GCHandle', 'Marshal'],
        },
        'unity': {
            '': ['MonoBehaviour', 'ScriptableObject',
                 'GameObject', 'Transform', 'RectTransform',
                 'Mesh', 'MeshRenderer', 'MeshFilter', 'Animator',
                 'Collider', 'SphereCollider', 'BoxCollider',
                 'Material', 'Sprite',
                 'Vector2', 'Vector3', 'Vector4', 'Quaternion', 'Color', 'Gradient',
                 'Coroutine', 'Space', 'LayerMask', 'Layer',
                 'AssetPostprocessor',
                 ],
            'XR': ['InputDevice'],
            'Unity.Collections': ['NativeArray'],
            'Experimental.AssetImporters': ['AssetImportContext', 'MeshImportPostprocessor', 'ScriptedImporter'],
            'Rendering': ['VertexAttributeDescriptor'],
            'Events': ['UnityAction'],
        },
        'upm.xrtk': {'UnityEngine.XR.Interaction.Toolkit': ['XRRayInteractor', 'XRBaseInteractable', 'XRController']},
        'upm.tmp': {'TMPro': ['TMP_Text']},
        'upm.ugui': {'': ['Image', 'Button', 'Toggle']},
    }

    """
    Put special cases in here that should be renamed when used in links, use it for generics
    The name is swapped *after* searching EXTERNAL_TYPE_MAP, just before constructing the url link
    """
    external_type_rename = {
        'List': 'List-1',
        'Dictionary': 'Dictionary-2',
        'IList': 'IList-1',
        'IDictionary': 'IDictionary-2',
        'ISet': 'ISet-2',
        'IEnumerable': 'IEnumerable-1',
        'Func': 'Func-1',
    }

    """
    Where do we search for api documentation
    Syntax:
    'package': (api link, fallback search link)
    Use %s for where to substitute item, every link *must* contain this
    """
    external_search_pages = {
        'msdn': ('https://docs.microsoft.com/en-us/dotnet/api/%s',
                 'https://docs.microsoft.com/en-us/search/?category=All&scope=.NET&terms=%s'),
        'unity': ('https://docs.unity3d.com/ScriptReference/%s.html',
                  'https://docs.unity3d.com/ScriptReference/30_search.html?q=%s'),
        'unityman': ('https://docs.unity3d.com/Manual/%s.html',
                     'https://docs.unity3d.com/Manual/30_search.html?q=%s'),
        'upm': ('https://docs.unity3d.com/Packages/%s',
                'https://docs.unity3d.com/Packages/%s'),
    }

    @staticmethod
    def apply_config(app: "Sphinx", config: Config) -> None:
        """ Read in the config variables and merges them with the defaults """

        try:
            CSDebug.set_config_values(config)

            # Initialize external links
            # *Merge* config values with the default values
            if config['sphinx_csharp_ignore_xref'] is not None:
                CSharpDomain.ignore_xref_types += config['sphinx_csharp_ignore_xref']

            if config['sphinx_csharp_external_type_rename'] is not None:
                CSharpDomain.external_type_rename.update(config['sphinx_csharp_external_type_rename'])

            if config['sphinx_csharp_ext_search_pages'] is not None:
                CSharpDomain.external_search_pages.update(config['sphinx_csharp_ext_search_pages'])

            if config['sphinx_csharp_ext_type_map'] is not None:
                a = CSharpDomain.external_type_map
                b = config['sphinx_csharp_ext_type_map']

                # Merge keys in both
                for pkg in set(b).intersection(a):
                    # Add new namespaces
                    for ns in set(b[pkg]).difference(a[pkg]):
                        a[pkg][ns] = b[pkg][ns].copy()

                    # Concat lists for existing namespaces
                    for ns in set(b[pkg]).intersection(a[pkg]):
                        a[pkg][ns] += b[pkg][ns]

                # Add new keys
                for pkg in set(b).difference(a):
                    a[pkg] = b[pkg].copy()

                # logger.info(f"merged external_type_map: {CSharpDomain.external_type_map}")

        except Exception as e:
            # Manually print the error here as sphinx does not do it for ExtensionErrors
            logger.error(f"Error in CSharpDomain.apply_config(): {e}, \nCheck that your config variables are correct.")
            raise

    def clear_doc(self, docname):
        for (typ, name), doc in dict(self.data['objects']).items():
            if doc == docname:
                del self.data['objects'][typ, name]

    def resolve_xref(self, _, fromdocname, builder,
                     typ, target, node, contnode):
        targets = []
        parents = []
        # Search in this namespace, note parent may not be where the target resides
        if node['cs:parent'] is not None:
            parts = node['cs:parent'].split('.')
            while parts:
                targets.append('.'.join(parts)+'.'+target)
                parents.append('.'.join(parts))
                parts = parts[:-1]

        # By adding this last we ensure the list targets is sorted by decreasing string length
        targets.append(target)
        parents.append('')

        # Get all objects that end with the initial target
        objtypes = self.objtypes_for_role(typ)
        objects = {key: val for (key, val) in self.data['objects'].items()
                   # Filter by objtype and check that we end with the target
                   if key[0] in objtypes and key[1].endswith(target) and
                   # that the character before the target is a namespace separator or nothing
                   (len(key[1]) == len(target) or key[1][:-len(target)][-1] == '.')}

        # 1. Found only one item that ends with the target, use this one
        if len(objects) == 1:
            objtype, tgt = next(iter(objects.keys()))
            return make_refnode(builder, fromdocname,
                                objects[objtype, tgt],
                                objtype + '-' + tgt,
                                contnode, tgt + ' ' + objtype)

        # 2. Search recognized built-in/external override types first, e.g. float, bool, void
        #    (currently also all other external types)
        for tgt in targets:
            if self.check_ignored_ref(tgt):
                return None


        # 3. Found no local objects that match
        if len(objects) == 0:
            # 3b Look externally
            ref = self.get_external_ref(target)
            if ref is not None:
                return ref
            logger.warning(f"Failed to find xref for: {target}, no objects found that end like this, "
                           f"searched in object types: {objtypes}")
                           # f", filter1: {[i for i in self.data['objects'] if i[1].endswith(target)]}"
                           # f", filter2: {[i for i in self.data['objects'] if i[0] in objtypes]}")
            if not CSDebug.has_printed_xref_objects:
                CSDebug.has_printed_xref_objects = True
                logger.warning(f"all xref objects: {self.data['objects']}")
            return None

        # 4. Search inside this namespace and its direct parents
        for tgt in targets:
            for objtype in objtypes:
                if (objtype, tgt) in objects:
                    return make_refnode(builder, fromdocname,
                                        objects[objtype, tgt],
                                        objtype + '-' + tgt,
                                        contnode, tgt + ' ' + objtype)

        # 5. Search in other namespaces by closest match starting at the parent namespace
        if len(objects) > 1:
            logger.warning(f"Ambiguous reference to {target}, potential matches: {objects}")

            # Get closest to the parent namespace
            for parent in parents:
                matches = [i for i in objects if i[0][1].startswith(parent)]
                if len(matches) >= 1:
                    match_objtype, match_tgt = matches[0]

                    if CSDebug.xref:
                        logger.info(f"Success finding xref, closest match: {objtype}, {tgt}, matches: {len(matches)}")

                    return make_refnode(builder, fromdocname,
                                        objects[match_objtype, match_tgt],
                                        match_objtype + '-' + match_tgt,
                                        contnode, match_tgt + ' ' + match_objtype)

        # 6. Look externally
        ref = self.get_external_ref(target)
        if ref is not None:
            return ref

        logger.warning(f"Failed to find xref for: {targets}, searched in object types: {objtypes}, parents: {parents}")
        if CSDebug.xref and not CSDebug.has_printed_xref_objects:
            CSDebug.has_printed_xref_objects = False
            logger.warning(f"all xref objects: {objects}")

        return None

    def get_objects(self):
        for (typ, name), docname in self.data['objects'].items():
            yield name, name, typ, docname, typ + '-' + name, 1

    def merge_domaindata(self, docnames, otherdata):
        # TODO: implement to allow parallel builds
        raise NotImplementedError

    def resolve_any_xref(self, env, fromdocname, builder,
                         target, node, contnode):
        raise NotImplementedError

    def check_ignored_ref(self, name: str) -> bool:
        """ Checks if the target is a built-in type or other ignored strings """
        return name in CSharpDomain.ignore_xref_types

    def get_external_ref(self, name: str) -> nodes:
        """
        Looks in the predefined external targets and adds the link if it is found
        returns: None if unsuccessful
        """
        input_name = name

        def create_node(fullname: str, name: str, url: str) -> nodes:
            """ Small local helper function """
            node = nodes.reference(fullname, shorten_type(name))
            node['refuri'] = url
            node['reftitle'] = fullname

            return node

        # Use existing link if we have already determined it, for performance
        if name in CSharpDomain.extlink_cache:
            if CSDebug.ext_links:
                logger.info(f"found in extlink_cache for {name}")
            return create_node(CSharpDomain.extlink_cache[input_name][0],
                               CSharpDomain.extlink_cache[input_name][1],
                               CSharpDomain.extlink_cache[input_name][2])

        # Start search in the CSharpDomain.external_type_map
        fullname = name
        name_split = name.rsplit('.', 1)
        if len(name_split) == 2:
            # We also have the namespace in the name
            parent, name = name_split
            matches = [(pkg, namespace) for pkg in CSharpDomain.external_type_map
                       for namespace in CSharpDomain.external_type_map[pkg]
                       if name in CSharpDomain.external_type_map[pkg][namespace]
                       and namespace.endswith(parent)]
            if len(matches) > 1:
                # Enforce exact match if there are several
                matches_strict = [i for i in matches if i[1] == parent]
                if len(matches_strict) >= 1:
                    matches = matches_strict
        else:
            # search all namespaces
            parent = None
            matches = [(pkg, namespace) for pkg in CSharpDomain.external_type_map
                       for namespace in CSharpDomain.external_type_map[pkg]
                       if name in CSharpDomain.external_type_map[pkg][namespace]]

        if not matches:
            return None

        if len(matches) > 1:
            logger.warning(f"ambiguous external reference for '{fullname}' using first, "
                           f"found matches: {matches}")

        pkg, parent = matches[0]

        link_name = name
        if name in CSharpDomain.external_type_rename:
            link_name = CSharpDomain.external_type_rename[name]

        if parent:
            # Skip for empty strings
            fullname = parent + '.' + link_name

        try:
            apilink = CSharpDomain.external_search_pages[pkg][0] % fullname
        except KeyError:
            logger.warning(
                f"external links package does not have any links set in EXTERNAL_SEARCH_PAGES, package: {pkg}, "
                f"target fullname: {fullname}")
            return None

        test_links = self.env.config['sphinx_csharp_test_links']
        if test_links:
            try:
                apilink_status_code = requests.get(apilink, timeout=3).status_code
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                test_links = False

        if not test_links or apilink_status_code < 400:
            url = apilink
        else:
            # Use search link or homepage instead
            logger.warning(f"invalid API link, using fallback, "
                           f"status_code={apilink_status_code}, apilink={apilink}")
            url = CSharpDomain.external_search_pages[pkg][1] % fullname

        node = create_node(fullname, name, url)

        # Store result in cache dict
        CSharpDomain.extlink_cache[input_name] = fullname, name, url

        if CSDebug.ext_links:
            logger.info(f"found external link: {input_name, fullname, name, url}")
        return node
