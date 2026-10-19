""" C# sphinx domain """

from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Set
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
from sphinx.util.docfields import Field, GroupedField
from sphinx.util.nodes import make_refnode

from .debug import CSDebug
from .extrefs import ExternalRefs
from .parser import (
    CONSTRAINT_KEYWORDS,
    CONVERSION_OPERATORS,
    Constraint,
    ParamTuple,
    arity_name,
    generic_type_name,
    is_indexer_signature,
    normalize_signature,
    overload_type,
    parameter_types,
    parse_attr_signature,
    parse_base_type,
    parse_enum_signature,
    parse_enumerator_signature,
    parse_indexer_signature,
    parse_method_signature,
    parse_property_signature,
    parse_record_kind,
    parse_type_as_function,
    parse_type_reference,
    parse_type_signature,
    parse_variable_signature,
    remove_arity,
    remove_generic_arguments,
    target_id,
)
from .render import CSharpGroupedField, CSharpTypedField, CSharpTypeField, TypeRenderer, append_modifiers


class ObjectEntry(NamedTuple):
    docname: str
    # The full name, without the parameters of an overload, and with the arity of each generic type as in N.Box-1
    name: str
    # The full name in the index and search results, such as N.Box<T>
    dispname: str


class ObjectMatch(NamedTuple):
    # The key of the object in the domain data, as (objtype, full name with any overload parameters)
    key: tuple[str, str]
    # The name the reference links to, with the parameters if the target names one overload
    name: str


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
        # The full name of the overload being described, such as N.C.M(int,string)
        self.overload_name: str | None = None
        # The display name of the type being described, such as N.Box<T>
        self.dispname: str | None = None

    def add_generic_names(self, names: list[str]) -> None:
        """ Declare generic parameters for the content, which every signature of the directive shares """
        self.generic_names += [name for name in names if name not in self.generic_names]

    def add_target_and_index(self, name: str, _: str, signode: addnodes.desc_signature) -> None:
        overload_name = self.overload_name or name
        self.overload_name = None
        dispname, self.dispname = self.dispname or remove_arity(name), None
        overload_targetname = targetname = target_id(self.objtype, overload_name)
        document = self.state.document
        if overload_targetname not in document.ids:
            # The first overload in a document also gets the target without parameters, which the index uses
            plain_targetname = target_id(self.objtype, name)
            if plain_targetname != overload_targetname and plain_targetname not in document.ids:
                signode['names'].append(plain_targetname)
                signode['ids'].append(plain_targetname)
                targetname = plain_targetname
            signode['names'].append(overload_targetname)
            signode['ids'].append(overload_targetname)
            signode['first'] = not self.names
            document.note_explicit_target(signode)

            objects = self.env.domaindata['cs']['objects']
            key = (self.objtype, overload_name)
            if key in objects:
                logger.warning(f'duplicate description of {self.objtype} {overload_name}, ' +
                               f'other instance in {self.env.doc2path(objects[key].docname)}',
                               location=(self.env.docname, self.lineno))
            objects[key] = ObjectEntry(self.env.docname, name, dispname)

        # Sphinx 7 and 8 keep noindexentry as a separate option
        indexed = 'no-index-entry' not in self.options and 'noindexentry' not in self.options
        # The index has one entry for the overloads of a method in a document, at the target without parameters
        if indexed and targetname == target_id(self.objtype, name):
            indextext = self.get_index_text(dispname)
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

    def get_overload_fullname(self, name: str, overload_name: str, sig: str,
                              signode: addnodes.desc_signature) -> str:
        """
        Describe one overload of a method or indexer, and return the full name of the method.
        overload_name includes the parameter types, such as M(int,string).
        """
        fullname = self.get_fullname(name)
        self.overload_name = normalize_signature(self.get_fullname(overload_name))
        # Sphinx adds a target for only the first signature of each name in a directive
        if fullname in self.names and 'no-index' not in self.options and 'noindex' not in self.options:
            self.add_target_and_index(fullname, sig, signode)
        return fullname

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
        for (i, inherited) in enumerate(inherits):
            typ, args = parse_base_type(inherited)
            self.append_type(node, typ, generic_params)
            if args:
                node += nodes.Text(args)
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
        return self.get_overload_fullname(name + '[]', f'{name}[{parameter_types(params)}]', sig, signode)

    def handle_type_signature(self, sig: str, signode: addnodes.desc_signature, keyword: str) -> str:
        """ Handle a type declaration, such as a class, and return its full name """
        typ, modifiers, generics, inherits, _, constraints, params, _ = parse_type_signature(
            sig, (self.env.docname, self.lineno))

        if modifiers:
            self.append_modifiers(signode, modifiers)

        prefix = keyword + ' '
        signode += addnodes.desc_annotation(prefix, prefix)
        # Doxygen names generic types with their arity, such as Box-1
        display = remove_arity(typ)
        signode += addnodes.desc_name(display, display)

        if generics:
            self.append_generics(signode, generics, nolink=True)
        # Variance modifiers such as in T come before the parameter name
        generic_params = [generic.split()[-1] for generic in generics]
        self.dispname = remove_arity(self.get_fullname(display)) + \
            ('<' + ', '.join(generic_params) + '>' if generic_params else '')
        self.add_generic_names(generic_params)
        if params is not None:
            signode += nodes.Text('\xa0')
            self.append_parameters(signode, params, generic_params)
        if inherits:
            self.append_inherits(signode, inherits, generic_params)
        self.append_constraints(signode, constraints, generic_params)
        return self.get_fullname(generic_type_name(typ, len(generics)))

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
        record = parse_record_kind(sig)
        if record is None:
            return self.handle_type_signature(sig, signode, 'record')
        modifiers, kind, rest = record
        return self.handle_type_signature(' '.join([*modifiers, rest]), signode, 'record ' + kind)


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
        declaration = parse_type_as_function(sig)
        if declaration is not None:
            modifiers, keyword, rest = declaration
            self.change_objtype(signode, keyword.split()[0])
            return self.handle_type_signature(' '.join([*modifiers, rest]), signode, keyword)

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
            # Conversion operators differ by return type, as in the .NET documentation ids
            overload_name = f'{name}({parameter_types(params)})~{overload_type(return_type)}'
            return self.get_overload_fullname(name, overload_name, sig, signode)

        # Variance modifiers such as out T come before the parameter name
        generic_names = [generic.split()[-1] for generic in generic_params]
        self.add_generic_names(generic_names)

        # Constructors have no return type
        if return_type is not None:
            # Generic type parameters are not linked
            self.append_type(signode, return_type, generic_names)
            signode += nodes.Text('\xa0')

        display_name = operator or name
        signode += addnodes.desc_name(display_name, display_name)

        if generic_params:
            self.append_generics(signode, generic_params, True)
        signode += nodes.Text('\xa0')

        self.append_parameters(signode, params, generic_names)
        self.append_constraints(signode, constraints, generic_names)

        generics = '<' + ','.join(generic_names) + '>' if generic_names else ''
        return self.get_overload_fullname(name, f'{name}{generics}({parameter_types(params)})', sig, signode)


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
        if is_indexer_signature(sig):
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
        'objects': {},  # (objtype, full name with any overload parameters) -> ObjectEntry
    }
    # The version of the objects data, which Sphinx compares with a saved environment
    data_version = 1

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
        for key, entry in dict(self.objects).items():
            if entry.docname == docname:
                del self.objects[key]

    @property
    def objects(self) -> dict[tuple[str, str], ObjectEntry]:
        """ The documented objects, keyed by object type and full name, with the document they are in """
        objects: dict[tuple[str, str], ObjectEntry] = self.data['objects']
        return objects

    def find_objects(self, target: str, parent: str | None, objtypes: Iterable[str],
                     loose: bool = True) -> list[ObjectMatch]:
        """
        Find the objects of the given types that a target refers to from within a parent namespace.
        Without loose, only the target qualified by the parent or an enclosing namespace matches.
        A target without parameters refers to the first overload of a method.
        A generic type has its arity in its name, such as N.Box-1, which generic arguments in a target match.
        A target matches without generic arguments and arity when nothing else does.
        """
        target = normalize_signature(target)
        return self.find_named_objects(target, parent, objtypes, loose, lambda name: name) or \
            self.find_named_objects(arity_name(target), parent, objtypes, loose, lambda name: name) or \
            self.find_named_objects(remove_arity(remove_generic_arguments(target)), parent, objtypes, loose,
                                    lambda name: remove_arity(remove_generic_arguments(name)))

    def object_order(self, key: tuple[str, str]) -> tuple[str, tuple[str, str]]:
        """ The order of objects that is the same in every build, by document and then key """
        return self.objects[key].docname, key

    def find_named_objects(self, target: str, parent: str | None, objtypes: Iterable[str], loose: bool,
                           transform: Callable[[str], str]) -> list[ObjectMatch]:
        """ Find the objects whose names, after a transform, the target refers to """

        def names(key: tuple[str, str]) -> set[str]:
            return {transform(key[1]), transform(self.objects[key].name)}

        def refers_to(name: str) -> bool:
            return name == target or name.endswith('.' + target)

        # The first overload of each method, by document and then name
        first_overloads: dict[tuple[str, str], tuple[str, str]] = {}
        for key in self.objects:
            if key[0] in objtypes and any(refers_to(name) for name in names(key)):
                method = (key[0], self.objects[key].name)
                if method not in first_overloads or self.object_order(key) < self.object_order(first_overloads[method]):
                    first_overloads[method] = key
        # A target with the parameters of an overload links to that overload
        matches = [ObjectMatch(key, key[1] if refers_to(transform(key[1])) else self.objects[key].name)
                   for key in sorted(first_overloads.values(), key=self.object_order)]

        # The parent and each of its enclosing namespaces, innermost first, with the transform of the names
        scopes = []
        if parent:
            parts = parent.split('.')
            scopes = [transform('.'.join(parts[:i])) for i in range(len(parts), 0, -1)]

        # Prefer the target qualified by the closest scope, then an object anywhere inside that scope
        for scope in scopes + ['']:
            exact = [match for match in matches if (scope + '.' + target if scope else target) in names(match.key)]
            if exact:
                return exact
        if not loose:
            return []
        if len(matches) <= 1:
            return matches
        for scope in scopes:
            inside = [match for match in matches if transform(match.key[1]).startswith(scope + '.')]
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

        # The name of a type in a signature, with the arity of each generic type
        name = node.get('cs:name', target)

        # A known external type takes precedence over a local object in an unrelated namespace
        matches = self.find_objects(name, parent, objtypes, loose=False)
        if not matches and not ExternalRefs.check_ignored_ref(target):
            ref = self.resolve_external_xref(typ, target, node, contnode)
            if ref is not None:
                return ref
            matches = self.find_objects(name, parent, objtypes)

        if len(matches) > 1:
            logger.warning(f'ambiguous reference to {target}, matches: {[match.key[1] for match in matches]}',
                           location=node)
        if matches:
            return self.make_refnode(builder, fromdocname, matches[0], contnode)
        if CSDebug.xref:
            logger.info(f'no C# object found for {target}, searched object types {objtypes}', location=node)
        return None

    @staticmethod
    def resolve_external_xref(typ: str, target: str, node: addnodes.pending_xref,
                              contnode: nodes.Element) -> nodes.reference | None:
        """ Link to external documentation, such as the Microsoft docs, or return None if the target is unknown """
        if 'cs:outer' in node:
            return ExternalRefs.get_nested_external_ref(node['cs:outer'], node['cs:outer_arity'],
                                                        target[len(node['cs:outer']) + 1:], typ, contnode)
        # The generic arguments of a type in a role, as in :cs:type:`List\<int>.Enumerator`, give its arity
        sig = parse_type_reference(target)
        if sig is None or sig.suffix:
            return None
        arity = node.get('cs:arity') or len(sig.generics)
        if sig.nested:
            nested = remove_generic_arguments(''.join('.'.join(sig.nested).split()))
            return ExternalRefs.get_nested_external_ref(sig.typ, arity, nested, typ, contnode)
        return ExternalRefs.get_external_ref(sig.typ, typ, contnode, arity)

    def resolve_any_xref(self, env: BuildEnvironment, fromdocname: str, builder: Builder, target: str,
                         node: addnodes.pending_xref,
                         contnode: nodes.Element) -> list[tuple[str, nodes.reference]]:
        matches = self.find_objects(target, node.get('cs:parent'), list(self.object_types))
        return [('cs:' + self.object_types[match.key[0]].roles[0],
                 self.make_refnode(builder, fromdocname, match, contnode))
                for match in matches]

    def make_refnode(self, builder: Builder, fromdocname: str, match: ObjectMatch,
                     contnode: nodes.Element) -> nodes.reference:
        """ Link to an object, or to one overload of it """
        objtype, name = match.key[0], match.name
        entry = self.objects[match.key]
        dispname = entry.dispname if name == entry.name else remove_arity(name)
        title = (self.label + ' ' if ExternalRefs.multi_lang else '') + f'{objtype}: {dispname}'
        return make_refnode(builder, fromdocname, entry.docname, target_id(objtype, name), contnode, title)

    def get_objects(self) -> Iterator[tuple[str, str, str, str, str, int]]:
        overloads = Counter((objtype, entry.name) for (objtype, _), entry in self.objects.items())
        methods = set()
        for objtype, overload_name in sorted(self.objects, key=self.object_order):
            entry = self.objects[objtype, overload_name]
            method = (objtype, entry.name)
            # Search shows the overloads of a method, and otherwise the name without parameters
            overloaded = overloads[method] > 1
            if method not in methods:
                methods.add(method)
                yield entry.name, entry.dispname, objtype, entry.docname, target_id(objtype, entry.name), \
                    -1 if overloaded else 1
            if overload_name != entry.name:
                yield overload_name, remove_arity(overload_name), objtype, entry.docname, \
                    target_id(objtype, overload_name), 1 if overloaded else -1

    def merge_domaindata(self, docnames: Set[str], otherdata: dict[str, Any]) -> None:
        for key, entry in otherdata['objects'].items():
            if entry.docname in docnames:
                self.objects[key] = entry
