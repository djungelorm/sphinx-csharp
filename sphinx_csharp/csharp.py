""" C# sphinx domain """

from collections.abc import Iterable, Iterator, Set
from typing import Any

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
from sphinx.util.docfields import Field, GroupedField
from sphinx.util.nodes import make_refnode

from .debug import CSDebug
from .extrefs import ExternalRefs
from .parser import (
    BASE_ARGS_RE,
    CONSTRAINT_KEYWORDS,
    CONVERSION_OPERATORS,
    IDXR_SIG_RE,
    RECORD_KIND_RE,
    TYPE_AS_FUNCTION_RE,
    Constraint,
    ParamTuple,
    parse_attr_signature,
    parse_enum_signature,
    parse_enumerator_signature,
    parse_indexer_signature,
    parse_method_signature,
    parse_property_signature,
    parse_type_signature,
    parse_variable_signature,
)
from .render import CSharpGroupedField, CSharpTypedField, CSharpTypeField, TypeRenderer, append_modifiers

logger = logging.getLogger(__name__)


class CSharpObject(ObjectDescription[str]):
    """ Description of generic C# objects """

    doc_field_types = [
        CSharpTypedField('parameter', label=_('Parameters'), names=('param', 'parameter', 'arg', 'argument'),
                         typerolename='type', typenames=('type',), can_collapse=True),
        GroupedField('typeparameter', label=_('Type Parameters'), names=('typeparam', 'tparam'), can_collapse=True),
        Field('returnvalue', label=_('Returns'), has_arg=False, names=('returns', 'return')),
        CSharpTypeField('returntype', label=_('Return type'), has_arg=False, names=('rtype',), bodyrolename='type'),
        CSharpGroupedField('exceptions', label=_('Throws'), rolename='type', names=('throws', 'throw', 'exception'),
                           can_collapse=True),
    ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.parentname_set = False
        self.parentname_saved: str | None = None
        # The generic parameters the signatures declare for the content, such as T in class List<T>
        self.generic_names: list[str] = []
        self.generic_names_saved: list[str] = []

    def add_generic_names(self, names: list[str]) -> None:
        """ Declare generic parameters for the content, which every signature of the directive shares """
        self.generic_names += [name for name in names if name not in self.generic_names]

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

    def get_fullname(self, name: str) -> str:
        parent = self.env.ref_context.get('cs:parent')
        return parent + '.' + name if parent else name

    append_modifiers = staticmethod(append_modifiers)

    def type_renderer(self) -> TypeRenderer:
        return TypeRenderer(self.env, (self.env.docname, self.lineno))

    def append_type(self, node: nodes.Element, input_typ: str, ignored_types: list[str] | None = None) -> None:
        """ ignored_types is a list of types to ignore in the generics of this type """
        self.type_renderer().append_type(node, input_typ, ignored_types)

    def append_generics(self, node: nodes.Element, generics: list[str], nolink: bool = False,
                        ignored_types: list[str] | None = None) -> None:
        """ nolink will disable xref's, use for newly declared generics in a class declaration,
         ignore_types is similar, but a list of types to disable xrefs for """
        self.type_renderer().append_generics(node, generics, nolink, ignored_types)

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

    def append_inherits(self, node: nodes.Element, inherits: list[str], generic_params: list[str]) -> None:
        """ Adds inherited types, inherits must be a list of string types """
        node += nodes.Text(' : ')
        for (i, typ) in enumerate(inherits):
            match = BASE_ARGS_RE.match(typ)
            self.append_type(node, match['type'] if match else typ, generic_params)
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
        self.add_generic_names(generic_params)
        if params is not None:
            signode += nodes.Text('\xa0')
            self.append_parameters(signode, params, generic_params)
        if inherits:
            self.append_inherits(signode, inherits, generic_params)
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
        self.add_generic_names(generic_names)

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
