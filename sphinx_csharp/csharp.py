""" C# sphinx domain """

import re
from collections import namedtuple
from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx import addnodes
from sphinx.domains import Domain, ObjType
from sphinx.locale import _
from sphinx.directives import ObjectDescription
from sphinx.roles import XRefRole
from sphinx.util.nodes import make_refnode
from sphinx.util import logging

MODIFIERS_RE = '|'.join(['public', 'private', 'internal', 'protected',
                         'abstract', 'async', 'const', 'event',
                         'extern', 'new', 'override', 'partial',
                         'readonly', 'sealed', 'static', 'unsafe',
                         'virtual', 'volatile'])
PARAM_MODIFIERS_RE = '|'.join(['this', 'ref', 'in', 'out', 'params'])

TYPE_RE = r'(?P<fulltype>(?P<type>[^\s<\[{\*&\?]+)\s*(?P<generics><\s*.+\s*>)?\s*(?P<array>\[,*\])?\s*(?:\*|&)?)\??'

METH_SIG_RE = re.compile(
    r'^((?:(?:' + MODIFIERS_RE +
    r')\s+)*)([^\s]+\s+)*([^\s<]+)\s*(<[^\(]+>)?\s*\((.*)\)$')
VAR_SIG_RE = re.compile(
    r'^\s*(?P<modifiers>(?:\s*(?:' + MODIFIERS_RE + r'))*)\s*' + TYPE_RE + '\s+(?P<name>[^\s<{]+)\s*(?:=\s*(?P<value>.+))?$')

PROP_SIG_RE = re.compile(
    r'^([^\s]+\s+)*([^\s]+)\s+([^\s]+)\s*\{\s*(get;)?\s*(set;)?\s*\}$')
IDXR_SIG_RE = re.compile(
    r'^((?:(?:' + MODIFIERS_RE +
    r')\s+)*)([^\s]+)\s*this\s*\[\s*((?:[^\s]+)\s+(?:[^\s]+)' +
    r'(?:\s*,\s*(?:[^\s]+)\s+(?:[^\s]+))*)\s*\]\s*' +
    r'\{\s*(get;)?\s*(set;)?\s*\}$')
PARAM_SIG_RE = re.compile(
    r'^((?:(?:' + PARAM_MODIFIERS_RE +
    r')\s+)*)(.+)\s+([^\s]+)\s*(=\s*(.+))?$')

CLASS_SIG_RE = re.compile(r'^' + TYPE_RE + r'\s*(?P<inherits>:\s*.*)?$')
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
        return sig.strip(), None
    modifiers, return_type, name, generic_types, params = match.groups()
    if params.strip() != '':
        params = split_sig(params)
        params = [parse_param_signature(x) for x in params]
    else:
        params = []

    return modifiers.split(), return_type, name, generic_types, params


def parse_variable_signature(sig):
    """ Parse a variable signature of the form:
        modifier* type name """
    match = VAR_SIG_RE.match(sig.strip())
    if not match:
        logger.warning('Variable signature invalid: ' + sig)
        return sig.strip(), None
    groups = match.groupdict()
    modifiers = groups['modifiers'].split()
    fulltype = groups['fulltype']
    typ = groups['type']
    generics = groups['generics']
    name = groups['name']
    value = groups['value']

    if not generics:
        generics = []

    print(f"matched var: {modifiers, fulltype, typ, generics, name, value}")
    return modifiers, fulltype, typ, generics, name, value


def parse_property_signature(sig):
    """ Parse a property signature of the form:
        modifier* type name { (get;)? (set;)? } """
    match = PROP_SIG_RE.match(sig.strip())
    if not match:
        logger.info(f'Property signature invalid: {sig}, parsing as variable')
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
    return modifiers, typ, name, getter is not None, setter is not None


def parse_indexer_signature(sig):
    """ Parse a indexer signature of the form:
        modifier* type this[params] { (get;)? (set;)? } """
    match = IDXR_SIG_RE.match(sig.strip())
    if not match:
        logger.warning('Indexer signature invalid: ' + sig)
        return sig.strip(), None
    modifiers, return_type, params, getter, setter = match.groups()
    params = split_sig(params)
    params = [parse_param_signature(x) for x in params]
    return (modifiers.split(), return_type, params,
            getter is not None, setter is not None)


def parse_param_signature(sig):
    """ Parse a parameter signature of the form: type name (= default)? """
    match = PARAM_SIG_RE.match(sig.strip())
    if not match:
        logger.warning('Parameter signature invalid, got ' + sig)
        return sig.strip(), None
    groups = match.groups()
    modifiers = groups[0].split()
    typ, name, _, default = groups[-4:]
    return ParamTuple(name=name, typ=typ,
                      default=default, modifiers=modifiers)


def parse_type_signature(sig):
    """ Parse a type signature """
    match = CLASS_SIG_RE.match(sig.strip())
    if not match:
        logger.warning('Type signature invalid, got ' + sig)
        return sig.strip(), None, None, None
    groups = match.groupdict()
    typ = groups['type']
    generic_types = groups['generics']
    inherited_types = groups['inherits']
    array = groups['array']

    if not generic_types:
        generic_types = []
    else:
        generic_types = split_sig(generic_types[1:-1])

    if not inherited_types:
        inherited_types = []
    else:
        inherited_types = split_sig(inherited_types.strip()[1:])

    return typ, generic_types, inherited_types, array


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
    return name, params


IGNORE_XREF_TYPES = [
    '*',
    '&',
    'void',
    'string',
    'int',
    'long',
    'uint',
    'ulong',
    'float',
    'double',
    'byte',
    'bool',

    # Unity Types
    'Vector2',
    'Vector3',
    'Vector4',
    'Quaternion',
    'Color',
    'Gradient',
    'Material',
    'Image',
    'Button',
    'Toggle',
    'Sprite',
    'Sprite',
    'Animator',
    'Collider',
    'SphereCollider',
    'Func',
    'Action',
    'UnityAction',
    'Thread',
]

EXTERNAL_XREF_TYPES = {
    'List': 'System.Collections.Generic.List',
    # 'IList': 'System.Collections.Generic.IList',
    'MonoBehaviour': 'UnityEngine',
    'GameObject': 'UnityEngine',
    'Transform': 'UnityEngine',
    # 'RectTransform': 'UnityEngine',
    'InputDevice': 'UnityEngine.XR',
    'InputDeviceCharacteristics': 'UnityEngine.XR',
    'XRController': 'UnityEngine.XR.Interaction.Toolkit',
    'XRRayInteractor': 'UnityEngine.XR.Interaction.Toolkit',
    'XRBaseInteractable': 'UnityEngine.XR.Interaction.Toolkit',
    # 'IEnumarator': '',
    # 'Coroutine': '',
    # 'TMP_Text': '',
    # 'Space': '',
    # 'NativeArray': '',
    # 'MeshRenderer': '',
    # 'MeshFilter': '',
    # 'AssetImportContext': '',
    # 'MeshImportPostprocessor': '',
    # 'VertexAttributeDescriptor': '',
}

EXTERNAL_LINKS = {
    'System.Collections.Generic.List': 'https://docs.microsoft.com/en-us/dotnet/api/system.collections.generic.list-1',  # noqa  # pylint: disable=line-too-long
    'System.Collections.Generic.Dictionary': 'https://docs.microsoft.com/en-us/dotnet/api/system.collections.generic.dictionary-2',  # noqa  # pylint: disable=line-too-long
    'System.Collections.Generic.IList': 'https://docs.microsoft.com/en-us/dotnet/api/system.collections.generic.ilist-1',  # noqa  # pylint: disable=line-too-long
    'System.Collections.Generic.IDictionary': 'https://docs.microsoft.com/en-us/dotnet/api/system.collections.generic.idictionary-2',  # noqa  # pylint: disable=line-too-long
    'System.Collections.Generic.ISet': 'https://docs.microsoft.com/en-us/dotnet/api/system.collections.generic.iset-1',  # noqa  # pylint: disable=line-too-long
    'System.Collections.Generic.IEnumerable': 'https://docs.microsoft.com/en-us/dotnet/api/system.collections.generic.ienumerable-1',  # noqa  # pylint: disable=line-too-long
    'System.Boolean': 'https://docs.microsoft.com/en-us/dotnet/api/system.boolean?view=netcore-3.1',  # noqa  # pylint: disable=line-too-long
    'UnityEngine.MonoBehaviour': 'unityapi/MonoBehaviour',
    'UnityEngine.GameObject': 'unityapi/GameObject',
    'UnityEngine.Transform': 'unityapi/Transform',
    'UnityEngine.XR.Interaction.Toolkit.InputDevice': 'unitypkg/com.unity.xr.interaction.toolkit@0.9/manual/index.html',
    'UnityEngine.XR.InputDevice': 'UnityEngine.XR.Interaction.Toolkit https://docs.unity3d.com/ScriptReference/XR.InputDevice.html',
    'UnityEngine.XR.InputDeviceCharacteristics': 'https://docs.unity3d.com/ScriptReference/XR.InputDeviceCharacteristics.html',
    'UnityEngine.XR.Interaction.Toolkit.XRController': 'https://docs.unity3d.com/Packages/com.unity.xr.interaction.toolkit@0.9/api/UnityEngine.XR.Interaction.Toolkit.XRController.html',
    'UnityEngine.XR.Interaction.Toolkit.XRRayInteractor': 'https://docs.unity3d.com/Packages/com.unity.xr.interaction.toolkit@0.9/api/UnityEngine.XR.Interaction.Toolkit.XRRayInteractor.html',
    'UnityEngine.XR.Interaction.Toolkit.XRBaseInteractable': 'https://docs.unity3d.com/Packages/com.unity.xr.interaction.toolkit@0.9/api/UnityEngine.XR.Interaction.Toolkit.XRBaseInteractable.html',
}


def get_external_ref(name: str) -> (bool, nodes):
    """ Try and create a reference to a type on MSDN
    returns: bool true if the node should be ignored, Node None when a type was not found """
    if name in IGNORE_XREF_TYPES:
        return True, None

    is_external = False
    fullname = name
    if name in EXTERNAL_XREF_TYPES:
        is_external = True
        fullname = EXTERNAL_XREF_TYPES[name]

        # i.e. append name itself if it is not a built in type (e.g. bool)
        if not fullname.startswith('System.'):
            fullname += '.' + name

    if is_external or name.startswith('System.') or name.startswith('UnityEngine.'):
        link = EXTERNAL_LINKS.get(fullname.split('<', 1)[0], None)

        if not link:
            logger.warning(f"Failed finding link for external type: {fullname} (short: {name})\n"
                           f"Have you added it to EXTERNAL_XREF_TYPES but not EXTERNAL_LINKS?\n"
                           f"You may want to add this to IGNORE_XREF_TYPES otherwise.")

            return True, None

        if link.startswith('msdn/'):
            url = 'https://docs.microsoft.com/en-us/dotnet/api' + link[len('msdn'):]
        elif link.startswith('unityapi/'):
            url = 'https://docs.unity3d.com/ScriptReference' + link[len('unityapi'):]
        elif link.startswith('unitypkg/'):
            url = 'https://docs.unity3d.com/Packages' + link[len('unitypkg'):]
        elif link.startswith('unityman/'):
            url = 'https://docs.unity3d.com/Manual' + link[len('unityman'):]
        else:
            url = link

        node = nodes.reference(fullname, shorten_type(name))
        node['refuri'] = url
        node['reftitle'] = name

        return False, node
    return False, None


SHORTEN_TYPE_PREFIXES = [
    'System.',
    'System.Collections.Generic.'
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
            signode += nodes.emphasis(modifier, modifier)
            signode += nodes.Text(u' ')

    def append_type(self, node, typ):
        typ, generic_types, inherited_types, array = parse_type_signature(typ)
        tnode = addnodes.pending_xref(
            '', refdomain='cs', reftype='type',
            reftarget=typ, modname=None, classname=None)

        # Note: this may not be the correct parent namespace
        if not self.has_parent():
            tnode['cs:parent'] = None
        else:
            tnode['cs:parent'] = self.get_parent()
        tnode += nodes.Text(shorten_type(typ))
        node += tnode
        if generic_types:
            node += nodes.Text('<')
            for i, typ_param in enumerate(generic_types):
                self.append_type(node, typ_param)
                if i != len(generic_types)-1:
                    node += nodes.Text(', ')
            node += nodes.Text('>')
        if array:
            node += nodes.Text(array)

    def append_inherits(self, node, inherits):
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
            pnode += nodes.Text(u' ')
            pnode += nodes.emphasis(param.name, param.name)
            if param.default is not None:
                default = u' = ' + param.default
                pnode += nodes.emphasis(default, default)
            pnodes += pnode
        node += pnodes

    def append_indexer_parameters(self, node, params):
        pnodes = addnodes.desc_addname()
        pnodes += nodes.Text('[')

        for param in params:
            if pnodes.children:
                pnodes += nodes.Text(u', ')

            self.append_type(pnodes, param.typ)
            pnodes += nodes.Text(u' ')
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
        typ, generics, inherits, _ = parse_type_signature(sig)
        prefix = 'class' + ' '
        signode += addnodes.desc_annotation(prefix, prefix)
        signode += addnodes.desc_name(typ, typ)

        if inherits:
            self.append_inherits(signode, inherits)
        return self.get_fullname(typ)


class CSharpStruct(CSharpObject):
    """ Description of a C# class """

    def handle_signature(self, sig, signode):
        typ, generics, inherits, _ = parse_type_signature(sig)
        prefix = 'struct' + ' '
        signode += addnodes.desc_annotation(prefix, prefix)
        signode += addnodes.desc_name(typ, typ)

        if inherits:
            self.append_inherits(signode, inherits)
        return self.get_fullname(typ)


class CSharpInterface(CSharpObject):
    """ Description of a C# interface """

    def handle_signature(self, sig, signode):
        typ, generics, inherits, _ = parse_type_signature(sig)
        prefix = 'interface' + ' '
        signode += addnodes.desc_annotation(prefix, prefix)
        signode += addnodes.desc_name(typ, typ)

        if inherits:
            self.append_inherits(signode, inherits)
        return self.get_fullname(typ)


class CSharpInherits(CSharpObject):
    """ Description of an inherited C# struct """

    def handle_signature(self, sig, signode):
        typ, _, _, _ = parse_type_signature(sig)
        signode += nodes.Text(': ')
        self.append_type(signode, sig)
        return self.get_fullname(typ)


class CSharpMethod(CSharpObject):
    """ Description of a C# method """

    def handle_signature(self, sig, signode):
        modifiers, typ, name, generic_types, params = parse_method_signature(sig)
        self.append_modifiers(signode, modifiers)
        if typ is not None:
            self.append_type(signode, typ)
            signode += nodes.Text(' ')
        signode += addnodes.desc_name(name, name)
        if generic_types is not None:
            signode += nodes.Text(generic_types)
        signode += nodes.Text(' ')
        self.append_parameters(signode, params)
        return self.get_fullname(name)


class CSharpVariable(CSharpObject):
    """ Description of a C# variable """

    def handle_signature(self, sig, signode):
        modifiers, fulltype, _, _, name, _ = parse_variable_signature(sig)

        self.append_modifiers(signode, modifiers)
        self.append_type(signode, fulltype)
        signode += nodes.Text(' ')
        signode += addnodes.desc_name(name, name)
        return self.get_fullname(name)


class CSharpProperty(CSharpObject):
    """ Description of a C# property """

    def handle_signature(self, sig, signode):
        modifiers, typ, name, getter, setter = parse_property_signature(sig)

        self.append_modifiers(signode, modifiers)
        if typ:
            self.append_type(signode, typ)
        signode += nodes.Text(' ')
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


class CSharpIndexer(CSharpObject):
    """ Description of a C# indexer """

    def handle_signature(self, sig, signode):
        modifiers, typ, params, getter, setter = parse_indexer_signature(sig)
        self.append_modifiers(signode, modifiers)
        self.append_type(signode, typ)
        signode += nodes.Text(' ')
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
        desc_name = 'enum %s' % sig
        signode += addnodes.desc_name(desc_name, desc_name)
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
            signode += nodes.Text(' ')
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
        'class':     ObjType(_('class'), 'type', 'class'),
        'struct':    ObjType(_('struct'), 'type', 'struct'),
        'function':    ObjType(_('function'), 'function', 'meth', 'func', 'type'),
        'member':     ObjType(_('member'), 'member', 'var'),
        'var':     ObjType(_('var'), 'var', 'member', 'type'),
        'property':  ObjType(_('property'), 'prop'),
        'enum':      ObjType(_('enum'), 'type', 'enum'),
        'enumerator': ObjType(_('enumerator'), 'enumerator'),
        'attribute': ObjType(_('attribute'), 'attr'),
        'indexer':   ObjType(_('indexer'), 'idxr'),
    }
    directives = {
        'class':     CSharpClass,
        'struct':    CSharpStruct,
        'interface': CSharpClass,
        'inherits':  CSharpInherits,
        'function':  CSharpMethod,
        'member':    CSharpVariable,
        'var':       CSharpVariable,
        'property':  CSharpProperty,
        'enum':      CSharpEnum,
        'enumerator': CSharpEnumValue,
        'attribute': CSharpAttribute,
        'indexer':   CSharpIndexer,
        'namespace': CSharpCurrentNamespace,
    }
    roles = {
        'type': CSharpXRefRole(),
        'class': CSharpXRefRole(),
        'struct': CSharpXRefRole(),
        'meth': CSharpXRefRole(),
        'func': CSharpXRefRole(),
        'var': CSharpXRefRole(),
        'member': CSharpXRefRole(),
        'prop': CSharpXRefRole(),
        'enum': CSharpXRefRole(),
        'enumerator': CSharpXRefRole(),
        'attr': CSharpXRefRole(),
        'idxr': CSharpXRefRole(),
    }
    initial_data = {
        'objects': {},  # fullname -> docname, objtype
    }

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
                   if key[1].endswith(target) and key[0] in objtypes}

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
            ignore_ref, ref = get_external_ref(tgt)
            if ignore_ref:
                return None
            if ref is not None:
                return ref

        # 3. Found no local objects that match
        if len(objects) == 0:
            logger.warning(f"Failed to find xref for: {target}, no objects found that end like this, "
                           f"searched in object types: {objtypes}")
                           # f", filter1: {[i for i in self.data['objects'] if i[1].endswith(target)]}"
                           # f", filter2: {[i for i in self.data['objects'] if i[0] in objtypes]}")
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

                    return make_refnode(builder, fromdocname,
                                        objects[match_objtype, match_tgt],
                                        match_objtype + '-' + match_tgt,
                                        contnode, match_tgt + ' ' + match_objtype)

        logger.warning(f"Failed to find xref for: {targets}, searched in object types: {objtypes}, parents: {parents}")

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
