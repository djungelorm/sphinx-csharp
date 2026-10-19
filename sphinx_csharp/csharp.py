""" C# sphinx domain """

from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Set
from typing import Any, NamedTuple

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.builders import Builder
from sphinx.config import Config
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType
from sphinx.environment import BuildEnvironment
from sphinx.ext.intersphinx import missing_reference as intersphinx_missing_reference
from sphinx.locale import _
from sphinx.roles import XRefRole
from sphinx.util import logging
from sphinx.util.docfields import Field, GroupedField
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import make_refnode

from .config import apply_deprecated_names
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
    last_name_part,
    normalize_signature,
    overload_type,
    parameter_types,
    parse_attr_signature,
    parse_base_type,
    parse_enum_signature,
    parse_enumerator_signature,
    parse_extension_signature,
    parse_indexer_signature,
    parse_method_signature,
    parse_property_signature,
    parse_type_as_function,
    parse_type_reference,
    parse_type_signature,
    parse_variable_signature,
    remove_arity,
    remove_generic_arguments,
    simple_name,
    split_attributes,
    split_declarators,
    split_sig,
    split_type_keyword,
    target_id,
)
from .render import (
    CSharpGroupedField,
    CSharpTypedField,
    CSharpTypeField,
    TypeRenderer,
    append_default_value,
    append_modifiers,
    keywords,
    punctuation,
    space,
)

# The object types whose qualified names nest in the TOC, as N.Outer.Inner does
TYPE_OBJTYPES = {'namespace', 'class', 'struct', 'interface', 'enum', 'record', 'delegate'}


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

    option_spec = {**ObjectDescription.option_spec, 'single-line-parameter-list': directives.flag}

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
        objects = self.env.domaindata['cs']['objects']
        key = (self.objtype, overload_name)
        # A namespace can have a description in each page that makes it current
        if key in objects and self.objtype != 'namespace':
            logger.warning(f'duplicate description of {self.objtype} {overload_name}, ' +
                           f'other instance in {self.env.doc2path(objects[key].docname)}',
                           location=(self.env.docname, self.lineno), type='cs', subtype='duplicate')
        document = self.state.document
        if overload_targetname in document.ids:
            return
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
        domain: CSharpDomain = self.env.get_domain('cs')  # type: ignore[assignment]
        domain.add_object(key, ObjectEntry(self.env.docname, name, dispname))

        # Sphinx 7 and 8 keep noindexentry as a separate option
        indexed = 'no-index-entry' not in self.options and 'noindexentry' not in self.options
        # The index has one entry for the overloads of a method in a document, at the target without parameters
        if indexed and targetname == target_id(self.objtype, name):
            self.indexnode['entries'].append(('single', self.get_index_text(dispname), targetname, '', None))

    def get_index_text(self, name: str) -> str:
        """ The general index entry for an object, such as "MyNamespace.MyClass (C# class)" """
        # Note: Breathe can describe an object as a method, which is not an object type of the domain.
        objtype = CSharpDomain.object_types.get(self.objtype)
        return _('%s (C# %s)') % (name, objtype.lname if objtype else self.objtype)

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

    def get_parent(self) -> str | None:
        """ The namespace or type that qualifies the name of the object """
        parent: str | None = self.env.ref_context.get('cs:parent')
        return parent

    def get_fullname(self, name: str) -> str:
        parent = self.get_parent()
        return parent + '.' + name if parent else name

    def describe_name(self, signode: addnodes.desc_signature, name: str) -> str:
        """
        Finish a signature, and return the full name of the object it describes.
        A signature with a target calls this last. It notes the parts of the name for the TOC,
        and puts each parameter on a line of its own in a long signature.
        """
        parent = self.get_parent()
        # The TOC nests the entry of a member in the entry of its type, and IFoo.Bar is one member
        parts = split_sig(name, '.') if self.objtype in TYPE_OBJTYPES else [name]
        signode['cs:toc_parts'] = (*(split_sig(parent, '.') if parent else []), *parts)
        max_length = self.config.sphinx_csharp_maximum_signature_line_length or \
            self.config.maximum_signature_line_length or 0
        if 'single-line-parameter-list' not in self.options and len(signode.astext()) > max_length > 0:
            for parameters in signode.findall(addnodes.desc_parameterlist):
                parameters['multi_line_parameter_list'] = True
        return self.get_fullname(name)

    def _object_hierarchy_parts(self, sig_node: addnodes.desc_signature) -> tuple[str, ...]:
        parts: tuple[str, ...] = sig_node.get('cs:toc_parts', ())
        return parts

    def _toc_entry_name(self, sig_node: addnodes.desc_signature) -> str:
        parts = sig_node['_toc_parts']
        if not parts:
            return ''
        show_parents = self.config.toc_object_entries_show_parents
        if show_parents == 'hide':
            parts = parts[-1:]
        elif show_parents == 'domain':
            # The name within the current namespace, such as MyClass.MyMethod, as every full name starts with it
            parts = parts[len(split_sig(self.env.ref_context.get('cs:namespace') or '', '.')):]
        parens = '()' if self.objtype == 'function' and self.config.add_function_parentheses else ''
        return '.'.join(remove_arity(part) for part in parts) + parens

    def get_overload_fullname(self, name: str, overload_name: str, sig: str,
                              signode: addnodes.desc_signature) -> str:
        """
        Describe one overload of a method or indexer, and return the full name of the method.
        overload_name includes the parameter types, such as M(int,string).
        """
        fullname = self.describe_name(signode, name)
        self.overload_name = normalize_signature(self.get_fullname(overload_name))
        # Sphinx adds a target for only the first signature of each name in a directive
        if fullname in self.names and 'no-index' not in self.options and 'noindex' not in self.options:
            self.add_target_and_index(fullname, sig, signode)
        return fullname

    def append_attributes(self, signode: addnodes.desc_signature, sig: str) -> str:
        """ Adds the attributes at the start of a declaration, and returns the rest of the signature """
        attributes, sig = split_attributes(sig)
        self.append_modifiers(signode, attributes)
        return sig

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
            node += space()
            node += keywords('where')
            node += addnodes.desc_type(param, param)
            self.append_colon(node)
            for i, typ in enumerate(types):
                if i:
                    node += punctuation(',')
                    node += space()
                if typ in CONSTRAINT_KEYWORDS:
                    node += addnodes.desc_sig_keyword(typ, typ)
                elif typ in generic_params:
                    node += addnodes.desc_type(typ, typ)
                else:
                    self.append_type(node, typ, generic_params)

    def append_inherits(self, node: nodes.Element, inherits: list[str], generic_params: list[str]) -> None:
        """ Adds inherited types, inherits must be a list of string types """
        self.append_colon(node)
        for (i, inherited) in enumerate(inherits):
            if i:
                node += punctuation(',')
                node += space()
            typ, args = parse_base_type(inherited)
            self.append_type(node, typ, generic_params)
            if args:
                node += nodes.Text(args)

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
        if param.name:
            node += space()
            node += addnodes.desc_sig_name(param.name, param.name)
        if param.default is not None:
            append_default_value(node, param.default)

    @staticmethod
    def append_colon(node: nodes.Element) -> None:
        """ Adds the colon before base types, a constraint or a constructor initializer """
        node += space()
        node += punctuation(':')
        node += space()

    @staticmethod
    def append_accessors(node: nodes.Element, accessors: list[str]) -> None:
        """ Adds accessors, such as { get; private set; } """
        if not accessors:
            return
        node += space()
        node += punctuation('{')
        annotation = addnodes.desc_annotation()
        for accessor in accessors:
            for word in accessor.split():
                annotation += space()
                annotation += addnodes.desc_sig_keyword(word, word)
            annotation += punctuation(';')
        node += annotation
        node += space()
        node += punctuation('}')

    def append_indexer_parameters(self, node: nodes.Element, params: list[ParamTuple]) -> None:
        # Note: Breathe removes desc_addname nodes from signatures, so the parameters go in the signature itself.
        node += punctuation('[')
        for i, param in enumerate(params):
            if i:
                node += punctuation(',')
                node += space()
            self.append_parameter(node, param, [])
        node += punctuation(']')

    def handle_indexer_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        modifiers, typ, interface, params, accessors = parse_indexer_signature(sig, (self.env.docname, self.lineno))
        name = interface + '.this' if interface else 'this'
        self.append_modifiers(signode, modifiers)
        self.append_type(signode, typ)
        signode += space()
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

        signode += keywords(keyword)
        # Doxygen names generic types with their arity, such as Box-1
        display = remove_arity(typ)
        signode += addnodes.desc_name(display, display)

        if generics:
            self.append_generics(signode, generics, nolink=True)
        # Variance modifiers such as in T come before the parameter name
        generic_params = [generic.split()[-1] for generic in generics]
        self.add_generic_names(generic_params)
        if params is not None:
            signode += space()
            self.append_parameters(signode, params, generic_params)
        if inherits:
            self.append_inherits(signode, inherits, generic_params)
        self.append_constraints(signode, constraints, generic_params)
        # Set after the signature parses, as add_target_and_index takes it and runs only for a signature that renders
        self.dispname = remove_arity(self.get_fullname(display)) + \
            ('<' + ', '.join(generic_params) + '>' if generic_params else '')
        return self.describe_name(signode, generic_type_name(typ, len(generics)))

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


class CSharpNamespaceDirective(SphinxDirective):
    """ A directive that changes the current C# namespace """

    has_content = False
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}

    def make_current(self, namespace: str | None) -> None:
        """ Make a namespace current, or clear it if it is None """
        if namespace is None:
            self.env.ref_context.pop('cs:parent', None)
            self.env.ref_context.pop('cs:namespace', None)
        else:
            self.env.ref_context['cs:parent'] = self.env.ref_context['cs:namespace'] = namespace

    def set_namespace(self, namespace: str | None) -> list[nodes.Node]:
        """ Make a namespace current, and add a target for it to the document, or clear it if it is None """
        self.make_current(namespace)
        if namespace is None:
            return []
        targetid = target_id('namespace', namespace)
        document = self.state.document
        if 'no-index' in self.options or 'noindex' in self.options or targetid in document.ids:
            return []
        target = nodes.target('', '', ids=[targetid])
        document.note_explicit_target(target)
        domain: CSharpDomain = self.env.get_domain('cs')  # type: ignore[assignment]
        domain.add_object(('namespace', namespace), ObjectEntry(self.env.docname, namespace, namespace))
        return [target]


class CSharpCurrentNamespace(CSharpNamespaceDirective):
    """ Set the current C# namespace, or clear it with None """

    required_arguments = 1
    option_spec = {'no-index': directives.flag, 'noindex': directives.flag}

    def run(self) -> list[nodes.Node]:
        self.env.ref_context.pop('cs:namespaces', None)
        namespace = self.arguments[0].strip()
        return self.set_namespace(None if namespace == 'None' else namespace)


class CSharpNamespacePush(CSharpNamespaceDirective):
    """ Make a namespace nested in the current namespace current, until namespace-pop """

    required_arguments = 1
    option_spec = {'no-index': directives.flag, 'noindex': directives.flag}

    def run(self) -> list[nodes.Node]:
        parent = self.env.ref_context.get('cs:parent')
        self.env.ref_context['cs:namespaces'] = [*self.env.ref_context.get('cs:namespaces', []), parent]
        name = self.arguments[0].strip()
        return self.set_namespace(f'{parent}.{name}' if parent else name)


class CSharpNamespacePop(CSharpNamespaceDirective):
    """ Make the namespace current that was current before the last namespace-push """

    def run(self) -> list[nodes.Node]:
        namespaces = self.env.ref_context.get('cs:namespaces')
        if not namespaces:
            logger.warning('namespace-pop without a namespace-push', location=self.get_location(),
                           type='cs', subtype='namespace')
            return []
        self.env.ref_context['cs:namespaces'] = namespaces[:-1]
        self.make_current(namespaces[-1])
        return []


class CSharpNamespacePlain(CSharpObject):
    """ Visual rendering of a C# namespace,
     without updating the parent like the directive CSharpCurrentNamespace.
     Used by breathe. """

    def get_parent(self) -> str | None:
        """ None, as Breathe writes the fully qualified name of a namespace """
        return None

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        signode += keywords('namespace')
        signode += addnodes.desc_name(sig, sig)

        return self.describe_name(signode, sig)


class CSharpType(CSharpObject):
    """ Description of a C# type declaration, such as a class """

    keyword = ''

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        sig = self.append_attributes(signode, sig)
        # The signature can have the keyword, as in public class Shape
        declaration = split_type_keyword(sig, (self.keyword,))
        if declaration is not None:
            modifiers, _, rest = declaration
            sig = ' '.join([*modifiers, rest])
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
    """ Description of a C# record, or a record class or record struct if the signature has class or struct """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        sig = self.append_attributes(signode, sig)
        record = split_type_keyword(sig, ('record', 'class', 'struct'))
        if record is None:
            return self.handle_type_signature(sig, signode, 'record')
        modifiers, kind, rest = record
        keyword = kind if kind.startswith('record') else 'record ' + kind
        return self.handle_type_signature(' '.join([*modifiers, rest]), signode, keyword)


class CSharpInherits(CSharpObject):
    """ Description of a type that a C# type inherits from """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        self.append_colon(signode)
        self.append_type(signode, sig)
        return self.get_fullname(sig)

    def add_target_and_index(self, name: str, sig: str, signode: addnodes.desc_signature) -> None:
        """ A base type is part of the description of its type, so it has no target or index entry of its own """


class CSharpExtension(CSharpObject):
    """ Description of a C# extension block, such as extension(string s), whose members belong to its static class """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        generic_params, receiver, constraints = parse_extension_signature(sig, (self.env.docname, self.lineno))
        signode += addnodes.desc_sig_keyword('extension', 'extension')
        if generic_params:
            self.append_generics(signode, generic_params, nolink=True)
        generic_names = [generic.split()[-1] for generic in generic_params]
        self.add_generic_names(generic_names)
        signode += space()
        self.append_parameters(signode, [receiver], generic_names)
        self.append_constraints(signode, constraints, generic_names)
        # The name of the enclosing type, which stays the parent of the members
        parent: str = self.env.ref_context.get('cs:parent') or ''
        return parent

    def add_target_and_index(self, name: str, sig: str, signode: addnodes.desc_signature) -> None:
        """ An extension block has no name, so it has no target or index entry """


class CSharpMethod(CSharpObject):
    """ Description of a C# method """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        self.reset_objtype()
        sig = self.append_attributes(signode, sig)
        declaration = parse_type_as_function(sig)
        if declaration is not None:
            modifiers, keyword, rest = declaration
            self.change_objtype(signode, keyword.split()[0])
            return self.handle_type_signature(' '.join([*modifiers, rest]), signode, keyword)

        modifiers, return_type, name, generic_params, params, constraints, operator, initializer = \
            parse_method_signature(sig, (self.env.docname, self.lineno))
        if self.objtype == 'delegate' and 'delegate' not in modifiers:
            modifiers.append('delegate')
        if 'delegate' in modifiers and self.objtype != 'delegate':
            self.change_objtype(signode, 'delegate')
        self.append_modifiers(signode, modifiers)

        # A conversion operator names its type after the operator keyword
        if operator is not None and return_type is not None and name in CONVERSION_OPERATORS:
            signode += addnodes.desc_name(operator, operator)
            signode += space()
            self.append_type(signode, return_type)
            signode += space()
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
            signode += space()

        display_name = operator or name
        signode += addnodes.desc_name(display_name, display_name)

        if generic_params:
            self.append_generics(signode, generic_params, True)
        signode += space()

        self.append_parameters(signode, params, generic_names)
        if initializer:
            self.append_colon(signode)
            signode += nodes.Text(initializer)
        self.append_constraints(signode, constraints, generic_names)

        # A static constructor is not an overload of the instance constructors, so its name has the modifier
        parent = self.env.ref_context.get('cs:parent') or ''
        if return_type is None and 'static' in modifiers and name == remove_arity(parent.rpartition('.')[2]):
            name = 'static ' + name
        generics = '<' + ','.join(generic_names) + '>' if generic_names else ''
        return self.get_overload_fullname(name, f'{name}{generics}({parameter_types(params)})', sig, signode)


class CSharpDelegate(CSharpMethod):
    """ Description of a C# delegate """


class CSharpDeclarators(CSharpObject):
    """ Description of a C# field or event, whose declaration can declare several variables, such as int x, y """

    def get_signatures(self) -> list[str]:
        """ The signatures, with a signature for each variable of a declaration """
        return [declaration for sig in super().get_signatures() for declaration in split_declarators(sig)]


class CSharpVariable(CSharpDeclarators):
    """ Description of a C# variable """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        sig = self.append_attributes(signode, sig)
        var = parse_variable_signature(sig, (self.env.docname, self.lineno))
        self.append_modifiers(signode, var.modifiers)
        self.append_type(signode, var.fulltype)
        signode += space()
        signode += addnodes.desc_name(var.name, var.name)
        if var.size is not None:
            signode += punctuation('[')
            signode += nodes.Text(var.size)
            signode += punctuation(']')
        if var.default:
            append_default_value(signode, var.default)
        return self.describe_name(signode, var.name)


class CSharpProperty(CSharpObject):
    """ Description of a C# property """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        self.reset_objtype()
        sig = self.append_attributes(signode, sig)
        # Doxygen writes indexers as properties named this[...]
        if is_indexer_signature(sig):
            self.change_objtype(signode, 'indexer')
            return self.handle_indexer_signature(sig, signode)

        modifiers, typ, name, accessors, default_val = parse_property_signature(
            sig, (self.env.docname, self.lineno))

        self.append_modifiers(signode, modifiers)
        self.append_type(signode, typ)
        signode += space()
        signode += addnodes.desc_name(name, name)
        self.append_accessors(signode, accessors)
        if default_val is not None:
            append_default_value(signode, default_val)
        return self.describe_name(signode, name)


class CSharpEvent(CSharpDeclarators):
    """ Description of a C# event """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        sig = self.append_attributes(signode, sig)
        modifiers, fulltype, name, accessors, default_value = parse_property_signature(
            sig, (self.env.docname, self.lineno))

        self.append_modifiers(signode, [modifier for modifier in modifiers if modifier != 'event'])
        signode += keywords('event')
        self.append_type(signode, fulltype)
        signode += space()
        signode += addnodes.desc_name(name, name)
        self.append_accessors(signode, accessors)
        if default_value:
            append_default_value(signode, default_value)

        return self.describe_name(signode, name)


class CSharpIndexer(CSharpObject):
    """ Description of a C# indexer """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        sig = self.append_attributes(signode, sig)
        return self.handle_indexer_signature(sig, signode)


class CSharpEnum(CSharpObject):
    """ Description of a C# enum """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        sig = self.append_attributes(signode, sig)
        declaration = split_type_keyword(sig, ('enum',))
        if declaration is not None:
            modifiers, _, rest = declaration
            sig = ' '.join([*modifiers, rest])
        modifiers, name, base = parse_enum_signature(sig, (self.env.docname, self.lineno))
        self.append_modifiers(signode, modifiers)
        signode += keywords('enum')
        signode += addnodes.desc_name(name, name)
        if base:
            self.append_colon(signode)
            self.append_type(signode, base)
        return self.describe_name(signode, arity_name(name))


class CSharpEnumValue(CSharpObject):
    """ Description of a C# enum value """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        sig = self.append_attributes(signode, sig)
        name, value = parse_enumerator_signature(sig, (self.env.docname, self.lineno))
        signode += addnodes.desc_name(name, name)
        if value:
            append_default_value(signode, value)
        return self.describe_name(signode, arity_name(name))


class CSharpAttribute(CSharpObject):
    """ Description of a C# attribute """

    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        name, params, generic_params = parse_attr_signature(sig, (self.env.docname, self.lineno))
        signode += addnodes.desc_name(name, name)
        if generic_params:
            self.append_generics(signode, generic_params, nolink=True)
        self.generic_names = generic_params
        if params:
            signode += space()
            self.append_parameters(signode, params, generic_params)
        return self.describe_name(signode, arity_name(generic_type_name(name, len(generic_params))))


class CSharpXRefRole(XRefRole):
    def process_link(self, env: BuildEnvironment, refnode: nodes.Element, has_explicit_title: bool,
                     title: str, target: str) -> tuple[str, str]:
        refnode['cs:parent'] = env.ref_context.get('cs:parent')
        # Intersphinx shows the title as written, as a local reference does
        refnode['refexplicit'] = True
        # A target that starts with ~ shows only the last part of its name
        if target.startswith('~'):
            target = target[1:]
            if not has_explicit_title:
                title = last_name_part(target)
        return super().process_link(
            env, refnode, has_explicit_title, title, target)


class CSharpDomain(Domain):
    """ C# domain """
    name = 'cs'
    label = 'C#'

    # Object types and the roles that reference them
    object_types = {
        'namespace': ObjType(_('namespace'), 'namespace', 'obj'),

        # Types
        'class': ObjType(_('class'), 'class', 'type', 'obj'),
        'struct': ObjType(_('struct'), 'struct', 'type', 'obj'),
        'interface': ObjType(_('interface'), 'interface', 'type', 'obj'),
        'enum': ObjType(_('enum'), 'enum', 'type', 'obj'),
        'record': ObjType(_('record'), 'record', 'type', 'obj'),
        # Breathe passes delegates to the function directive
        'delegate': ObjType(_('delegate'), 'delegate', 'type', 'func', 'meth', 'obj'),

        'function': ObjType(_('function'), 'function', 'func', 'meth', 'member', 'obj'),

        'var': ObjType(_('var'), 'var', 'member', 'obj'),
        'property': ObjType(_('property'), 'prop', 'member', 'obj'),
        'event': ObjType(_('event'), 'event', 'member', 'obj'),

        'enumerator': ObjType(_('enumerator'), 'enumerator', 'value', 'obj'),
        'attribute': ObjType(_('attribute'), 'attr', 'obj'),
        'indexer': ObjType(_('indexer'), 'idxr', 'obj'),
    }
    directives = {
        'namespace': CSharpCurrentNamespace,
        'namespace-push': CSharpNamespacePush,
        'namespace-pop': CSharpNamespacePop,

        'class': CSharpClass,
        'struct': CSharpStruct,
        'interface': CSharpInterface,
        'record': CSharpRecord,
        'inherits': CSharpInherits,
        'extension': CSharpExtension,

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
        # The other descriptions of the objects that more than one document describes
        'duplicates': {},  # (objtype, full name with any overload parameters) -> list[ObjectEntry]
    }
    # The version of the objects data, which Sphinx compares with a saved environment
    data_version = 1

    def __init__(self, env: BuildEnvironment) -> None:
        super().__init__(env)
        # The keys of the objects by simple name, such as Put for N.Box-1.Put(T), or None until a lookup builds it
        self.object_index: dict[str, list[tuple[str, str]]] | None = None

    @staticmethod
    def missing_reference(app: Sphinx, env: BuildEnvironment, node: addnodes.pending_xref,
                          contnode: nodes.TextElement) -> nodes.reference | None:
        """
        Look a generic target up in other projects with the arity it has in their inventories, as written.
        Intersphinx tries the target as written, such as Lib.Box<T>, and then get_full_qualified_name, which
        qualifies it with the current namespace.
        """
        if node.get('refdomain') != 'cs' or 'sphinx.ext.intersphinx' not in app.extensions:
            return None
        name = arity_name(normalize_signature(node.get('cs:name', node['reftarget'])))
        if name == node['reftarget']:
            return None
        written = node.deepcopy()
        written['reftarget'] = name
        return intersphinx_missing_reference(app, env, written, contnode)

    @staticmethod
    def apply_config(_app: "Sphinx", config: Config) -> None:
        """ Read in the config variables, called once the config is initialized (this is a callback) """

        try:
            apply_deprecated_names(config)
            CSDebug.set_config_values(config)
            ExternalRefs.apply_config(config)
        except Exception as e:
            # Sphinx omits the cause when it reports an ExtensionError, so we log it here
            logger.error(f"Error in CSharpDomain.apply_config(): {e}, \nCheck that your config variables are correct.")
            raise

    def clear_doc(self, docname: str) -> None:
        self.object_index = None
        for key, entries in list(self.duplicates.items()):
            self.duplicates[key] = [entry for entry in entries if entry.docname != docname]
        for key, entry in list(self.objects.items()):
            if entry.docname == docname:
                del self.objects[key]
                # Another document's description of the object takes its place
                for other in self.duplicates.pop(key, []):
                    self.add_object(key, other)
        for key in [key for key, entries in self.duplicates.items() if not entries]:
            del self.duplicates[key]

    @property
    def objects(self) -> dict[tuple[str, str], ObjectEntry]:
        """ The documented objects, keyed by object type and full name, with the document they are in """
        objects: dict[tuple[str, str], ObjectEntry] = self.data['objects']
        return objects

    @property
    def duplicates(self) -> dict[tuple[str, str], list[ObjectEntry]]:
        """ The descriptions of objects that another document also describes, other than those in objects """
        duplicates: dict[tuple[str, str], list[ObjectEntry]] = self.data['duplicates']
        return duplicates

    def add_object(self, key: tuple[str, str], entry: ObjectEntry) -> None:
        """ Add a description of an object. References link to the description in the first document by name. """
        self.object_index = None
        existing = self.objects.get(key)
        if existing is None:
            self.objects[key] = entry
            return
        first, other = sorted([existing, entry], key=lambda description: description.docname)
        self.objects[key] = first
        self.duplicates.setdefault(key, []).append(other)

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
        found = self.find_named_objects(target, parent, objtypes, loose, lambda name: name)
        # A target without generic arguments has no arity form to try
        if not found and arity_name(target) != target:
            found = self.find_named_objects(arity_name(target), parent, objtypes, loose, lambda name: name)
        return found or self.find_named_objects(remove_arity(remove_generic_arguments(target)), parent, objtypes, loose,
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

        if self.object_index is None:
            self.object_index = {}
            for key in self.objects:
                self.object_index.setdefault(simple_name(key[1]), []).append(key)

        # The first overload of each method, by document and then name
        first_overloads: dict[tuple[str, str], tuple[str, str]] = {}
        for key in self.object_index.get(simple_name(target), []):
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

        objtypes = self.objtypes_for_role(typ) or []
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
                           location=node, type='cs', subtype='ambiguous')
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
                                                        target[len(node['cs:outer']) + 1:], typ, contnode, node)
        # The generic arguments of a type in a role, as in :cs:type:`List\<int>.Enumerator`, give its arity
        sig = parse_type_reference(target)
        if sig is None or sig.suffix:
            return None
        arity = node.get('cs:arity') or len(sig.generics)
        if sig.nested:
            nested = remove_generic_arguments(''.join('.'.join(sig.nested).split()))
            return ExternalRefs.get_nested_external_ref(sig.typ, arity, nested, typ, contnode, node)
        return ExternalRefs.get_external_ref(sig.typ, typ, contnode, arity, node)

    def resolve_any_xref(self, env: BuildEnvironment, fromdocname: str, builder: Builder, target: str,
                         node: addnodes.pending_xref,
                         contnode: nodes.Element) -> list[tuple[str, nodes.reference]]:
        matches = self.find_objects(target, node.get('cs:parent'), list(self.object_types))
        return [('cs:' + self.object_types[match.key[0]].roles[0],
                 self.make_refnode(builder, fromdocname, match, contnode))
                for match in matches]

    def get_full_qualified_name(self, node: nodes.Element) -> str:
        """
        The name of a reference as in the inventory, with the arity of each generic type, such as N.Box-1 for Box<T>.
        Intersphinx looks this name up when the target as written is not in an inventory.
        """
        name = arity_name(normalize_signature(node.get('cs:name', node['reftarget'])))
        parent = node.get('cs:parent')
        # A target that starts with the outermost namespace of the parent is already qualified
        if parent and name.split('.')[0] != parent.split('.')[0]:
            name = parent + '.' + name
        return name

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
                if key in self.objects and key[0] != 'namespace':
                    logger.warning(f'duplicate description of {key[0]} {key[1]}, '
                                   f'other instance in {self.env.doc2path(self.objects[key].docname)}',
                                   location=entry.docname, type='cs', subtype='duplicate')
                self.add_object(key, entry)
        for key, entries in otherdata['duplicates'].items():
            for entry in entries:
                if entry.docname in docnames:
                    self.add_object(key, entry)
