""" Rendering of C# types in signatures and doc fields """

from docutils import nodes
from docutils.parsers.rst.states import Inliner
from docutils.utils import get_source_line
from sphinx import addnodes
from sphinx.environment import BuildEnvironment
from sphinx.util.docfields import Field, GroupedField, TypedField
from sphinx.util.typing import TextlikeNode

from .extrefs import ExternalRefs
from .parser import (
    Location,
    generic_type_name,
    invalid_signature,
    parse_tuple_element,
    parse_type_signature,
    split_sig,
)


def append_modifiers(node: nodes.Element, modifiers: list[str]) -> None:
    """ Adds modifiers such as public static, each followed by a space """
    for modifier in modifiers:
        node += addnodes.desc_annotation(modifier, modifier)
        node += nodes.Text('\xa0')


class TypeRenderer:
    """ Renders types with links, such as List<MyClass>, in signatures and doc fields """

    def __init__(self, env: BuildEnvironment, location: Location) -> None:
        self.env = env
        self.location = location

    def append_type(self, node: nodes.Element, input_typ: str, ignored_types: list[str] | None = None) -> None:
        """ ignored_types is a list of types to ignore in the generics of this type """
        sig = parse_type_signature(input_typ, self.location)
        typ = sig.typ

        if sig.modifiers:
            append_modifiers(node, sig.modifiers)

        # The name with the arity of each generic type, such as Box-1.Inner for Box<int>.Inner
        name = generic_type_name(typ, len(sig.generics))
        if typ.startswith('('):
            self.append_tuple(node, typ, ignored_types)
        else:
            self.append_type_name(node, typ, name, ExternalRefs.shorten_type(typ), len(sig.generics))
        if sig.generics:
            self.append_generics(node, sig.generics, ignored_types=ignored_types)

        # Each nested type links to its path without the generic arguments, such as List.Enumerator
        outer, outer_arity = typ, len(sig.generics)
        for segment in sig.nested:
            inner = parse_type_signature(segment, self.location)
            typ += '.' + inner.typ
            name += '.' + generic_type_name(inner.typ, len(inner.generics))
            node += nodes.Text('.')
            tnode = self.append_type_name(node, typ, name, inner.typ, len(inner.generics))
            if tnode is not None:
                tnode['cs:outer'] = outer
                tnode['cs:outer_arity'] = outer_arity
            if inner.generics:
                self.append_generics(node, inner.generics, ignored_types=ignored_types)

        if sig.suffix:
            node += nodes.Text(sig.suffix)

    def append_type_name(self, node: nodes.Element, typ: str, name: str, text: str,
                         arity: int) -> addnodes.pending_xref | None:
        """
        Adds a reference to a type, with arity generic arguments, unless the type is never linked.
        name is the type with the arity of each generic type, such as Box-1.
        """
        # The generic parameters of an enclosing type are not linked
        if ExternalRefs.check_ignored_ref(typ) or typ in self.env.ref_context.get('cs:generic_names', []):
            node += addnodes.desc_type(text, text)
            return None

        tnode = addnodes.pending_xref(
            '', refdomain='cs', reftype='type',
            reftarget=typ, modname=None, classname=None)

        # Note: this may not be the correct parent namespace
        tnode['cs:parent'] = self.env.ref_context.get('cs:parent')
        tnode['cs:arity'] = arity
        tnode['cs:name'] = name

        tnode += addnodes.desc_type(text, text)
        node += tnode
        return tnode

    def append_tuple(self, node: nodes.Element, tuple_typ: str, ignored_types: list[str] | None) -> None:
        """ Adds a tuple type, such as (int count, string name), linking the type of each element """
        node += nodes.Text('(')
        for i, element in enumerate(split_sig(tuple_typ[1:-1])):
            if i:
                node += nodes.Text(', ')
            parsed = parse_tuple_element(element)
            if parsed is None:
                raise invalid_signature('Type', tuple_typ, self.location)
            typ, name = parsed
            if ignored_types and typ in ignored_types:
                node += addnodes.desc_type(typ, typ)
            else:
                self.append_type(node, typ, ignored_types)
            if name:
                node += nodes.Text('\xa0' + name)
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


class CSharpTypeField(Field):
    """ A doc field whose types, such as List<int> in :type x: List<int>, render like the types in a signature """

    def make_xrefs(self, rolename: str, domain: str, target: str,
                   innernode: type[TextlikeNode] = addnodes.literal_emphasis, contnode: nodes.Node | None = None,
                   env: BuildEnvironment | None = None, inliner: Inliner | None = None,
                   location: nodes.Element | None = None) -> list[nodes.Node]:
        if rolename == 'type' and env is not None and location is not None and \
                issubclass(innernode, nodes.TextElement):
            node = innernode('', '')
            try:
                TypeRenderer(env, location).append_type(node, target)
            except ValueError:
                # The parser has already warned about the type
                return [innernode(target, target)]
            # Unresolved references warn at the field
            source, line = get_source_line(location)
            for ref in node.findall(addnodes.pending_xref):
                ref.source, ref.line = source, line
            return [node]
        return super().make_xrefs(rolename, domain, target, innernode, contnode, env, inliner, location)


class CSharpTypedField(CSharpTypeField, TypedField):
    """ A doc field with a type for each argument, such as :param x: with :type x: """


class CSharpGroupedField(CSharpTypeField, GroupedField):
    """ A doc field whose arguments are types, such as :throws ArgumentException: """
