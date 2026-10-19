import urllib.error
import urllib.request
from collections.abc import Callable

from docutils import nodes
from sphinx.config import Config
from sphinx.util import logging

from .debug import CSDebug
from .extrefs_data import ExternalRefsData

logger = logging.getLogger(__name__)


class ExternalRefs:
    """ Resolves links to external non-sphinx documentation, e.g. MSDN or Unity.
    All data is stored in a separate file in the class ExternalRefsData """

    extlink_cache: dict[tuple[str, int], tuple[str, str]] = {}
    check_links = False
    # Whether the build has logged that the links are checked
    check_links_logged = False
    multi_lang = False
    unqualified_namespaces: list[str] = []
    ignore_xref_types: list[str] = []
    external_type_map: dict[str, dict[str, list[str]]] = {}
    external_type_rename: dict[str, str] = {}
    external_search_pages: dict[str, tuple[str, str]] = {}

    @classmethod
    def apply_config(cls, config: Config) -> None:
        """ Merge the config values with the defaults in ExternalRefsData """
        cls.extlink_cache = {}
        cls.check_links = config['sphinx_csharp_check_external_links']
        cls.check_links_logged = False
        cls.multi_lang = config['sphinx_csharp_multi_language']

        # Start from copies so that the defaults are never modified
        cls.unqualified_namespaces = ExternalRefsData.unqualified_namespaces + \
            (config['sphinx_csharp_unqualified_namespaces'] or [])
        cls.ignore_xref_types = ExternalRefsData.ignore_xref_types + (config['sphinx_csharp_ignore_types'] or [])
        cls.external_type_rename = {**ExternalRefsData.external_type_rename,
                                    **(config['sphinx_csharp_external_type_rename'] or {})}
        cls.external_search_pages = {**ExternalRefsData.external_search_pages,
                                     **(config['sphinx_csharp_external_search_pages'] or {})}

        cls.external_type_map = {pkg: {ns: list(types) for ns, types in namespaces.items()}
                                 for pkg, namespaces in ExternalRefsData.external_type_map.items()}
        for pkg, namespaces in (config['sphinx_csharp_external_type_map'] or {}).items():
            for ns, types in namespaces.items():
                cls.external_type_map.setdefault(pkg, {}).setdefault(ns, []).extend(types)

    @classmethod
    def check_ignored_ref(cls, name: str) -> bool:
        """ Checks if the target is a built-in type or other ignored strings """
        return name in cls.ignore_xref_types

    @classmethod
    def shorten_type(cls, typ: str) -> str:
        """ Drop the namespace from a type in one of the unqualified namespaces, such as System.Text """
        namespace, _, name = typ.rpartition('.')
        if any(namespace == ns or namespace.startswith(ns + '.') for ns in cls.unqualified_namespaces):
            return name
        return typ

    @classmethod
    def get_nested_external_ref(cls, outer: str, arity: int, nested: str, objtype: str, contnode: nodes.Node,
                                location: nodes.Node | None = None) -> nodes.reference | None:
        """
        Link a type nested in an external type, such as Enumerator in List<T>.Enumerator, to the Microsoft docs.
        arity is the number of generic arguments of the outer type.
        """
        ref = cls.get_external_ref(outer, objtype, nodes.Text(''), arity, location)
        # The Microsoft docs name a nested type page by appending it to the page of the outer type
        if ref is None or not ref['refuri'].startswith(cls.external_search_pages['msdn'][0] % ''):
            return None
        node = nodes.reference('', '', internal=False, refuri=ref['refuri'] + '.' + nested,
                               reftitle=ref['reftitle'] + '.' + nested)
        node += contnode
        return node

    @classmethod
    def get_external_ref(cls, name: str, objtype: str, contnode: nodes.Node,  # noqa: PLR0912, PLR0915
                         arity: int = 0, location: nodes.Node | None = None) -> nodes.reference | None:
        """
        Link a type to external documentation, such as the Microsoft docs for System types.
        arity is the number of generic arguments, and location is the reference for warnings.
        Returns None if the type is not recognized.
        """
        cache_key = (name, arity)

        def create_node(fullname: str, url: str) -> nodes.reference:
            node = nodes.reference('', '', internal=False, refuri=url,
                                   reftitle=('C# ' if cls.multi_lang else '') + f'{objtype}: {fullname}')
            node += contnode
            return node

        # Use existing link if we have already determined it, for performance
        if cache_key in cls.extlink_cache:
            if CSDebug.external:
                logger.info(f"found in extlink_cache for {name}")
            return create_node(*cls.extlink_cache[cache_key])

        name = ExternalRefsData.builtin_types.get(name, name)

        # Start search in the external type map
        fullname = name
        # The namespace in the name, if any, which the namespace of a match ends with
        parent, _, name = name.rpartition('.')

        def find(is_member: Callable[[str], object]) -> list[tuple[str, str, str]]:
            return [(pkg, namespace, member) for pkg, namespaces in cls.external_type_map.items()
                    for namespace, members in namespaces.items()
                    if not parent or namespace == parent or namespace.endswith('.' + parent)
                    for member in members if is_member(member)]

        # A generic type can have an entry with its arity, such as IEqualityComparer-1, in another namespace
        matches = (find(f'{name}-{arity}'.__eq__) if arity else []) or find(name.__eq__)
        if not matches and not arity:
            # A generic type without its generic arguments, such as System.Collections.Generic.IList
            matches = find(lambda member: member.startswith(name + '-') and member[len(name) + 1:].isdecimal())
        if parent and len(matches) > 1:
            # Enforce exact match if there are several
            matches_strict = [i for i in matches if i[1] == parent]
            if len(matches_strict) >= 1:
                matches = matches_strict

        if not matches and fullname.startswith('System.'):
            # Any other System type is in the Microsoft docs
            matches = [('msdn', parent, name)]
        if not matches:
            return None

        if len(matches) > 1:
            logger.warning(f"ambiguous external reference for '{fullname}' using first, "
                           f"found matches: {matches}", location=location, type='cs', subtype='external')

        pkg, parent, member = matches[0]

        if member != name:
            link_name = member
        elif pkg == 'msdn' and arity:
            # The Microsoft docs give generic types an arity suffix, such as List-1
            link_name = f'{name}-{arity}'
        else:
            link_name = cls.external_type_rename.get(name, name)

        if parent:
            # Skip for empty strings
            link_name = f'{parent}.{link_name}'
            fullname = f'{pkg} ~> {parent}.{name}'
        else:
            fullname = f'{pkg} ~> {name}'

        try:
            apilink = cls.external_search_pages[pkg][0] % link_name
        except KeyError:
            logger.warning(
                f"external links package does not have any links set in EXTERNAL_SEARCH_PAGES, package: {pkg}, "
                f"target fullname: {fullname}", location=location, type='cs', subtype='external')
            return None

        apilink_status_code = 0
        if cls.check_links:
            if not cls.check_links_logged:
                cls.check_links_logged = True
                logger.info("csharp: external link testing is enabled")
            status = link_status(apilink)
            if status is None:
                cls.check_links = False
            else:
                apilink_status_code = status

        if not cls.check_links or apilink_status_code < 400:
            url = apilink
        else:
            # Use search link or homepage instead
            logger.warning(f"invalid API link, using fallback, "
                           f"status_code={apilink_status_code}, apilink={apilink}",
                           location=location, type='cs', subtype='external')
            url = cls.external_search_pages[pkg][1] % link_name

        cls.extlink_cache[cache_key] = fullname, url
        if CSDebug.external:
            logger.info(f"found external link: {cache_key, fullname, url}")
        return create_node(fullname, url)


def link_status(url: str) -> int | None:
    """ The HTTP status of a link, or None if the server cannot be reached """
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            status: int = response.status
            return status
    except urllib.error.HTTPError as error:
        error.close()
        return error.code
    except (urllib.error.URLError, TimeoutError):
        return None
