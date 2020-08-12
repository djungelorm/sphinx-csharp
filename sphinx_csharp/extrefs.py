from .debug import CSDebug
from .extrefs_data import ExternalRefsData
import requests
from typing import cast
from sphinx.config import Config
from sphinx.util import logging
from docutils import nodes

logger = logging.getLogger(__name__)


class ExternalRefs:
    """ Resolves links to external non-sphinx documentation, e.g. MSDN or Unity.
    All data is stored in a separate file in the class ExternalRefsData """

    extlink_cache = {}
    test_links = False
    multi_lang = False

    @classmethod
    def apply_config(cls, config: Config):
        """ Read in the config variables and merge them with the defaults """

        cls.test_links = config['sphinx_csharp_test_links']
        cls.multi_lang = config['sphinx_csharp_multi_language']

        # *Merge* config values with the default values
        if config['sphinx_csharp_shorten_type_prefixes'] is not None:
            ExternalRefsData.shorten_type_prefixes += config['sphinx_csharp_shorten_type_prefixes']

        if config['sphinx_csharp_ignore_xref'] is not None:
            ExternalRefsData.ignore_xref_types += config['sphinx_csharp_ignore_xref']

        if config['sphinx_csharp_external_type_rename'] is not None:
            ExternalRefsData.external_type_rename.update(config['sphinx_csharp_external_type_rename'])

        if config['sphinx_csharp_ext_search_pages'] is not None:
            ExternalRefsData.external_search_pages.update(config['sphinx_csharp_ext_search_pages'])

        if config['sphinx_csharp_ext_type_map'] is not None:
            a = ExternalRefsData.external_type_map
            b = cast(type(a), config['sphinx_csharp_ext_type_map'])

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

    @classmethod
    def check_ignored_ref(cls, name: str) -> bool:
        """ Checks if the target is a built-in type or other ignored strings """
        return name in ExternalRefsData.ignore_xref_types

    @classmethod
    def shorten_type(cls, typ: str) -> str:
        """ Shorten a type. E.g. drops 'System.' """
        # Find largest prefix that matches
        offset = 0
        for prefix in ExternalRefsData.shorten_type_prefixes:
            if typ.startswith(prefix):
                if len(prefix) > offset:
                    offset = len(prefix)

        # remove trailing dot
        if typ[offset] == '.':
            offset += 1
        return typ[offset:]

    @classmethod
    def get_external_ref(cls, name: str, objtype: str) -> nodes:
        """
        Looks in the predefined external targets and adds the link if it is found
        returns: None if unsuccessful
        """
        input_name = name

        def create_node(fullname: str, name: str, url: str) -> nodes:
            """ Small local helper function """
            node = nodes.reference(fullname, name)
            node['refuri'] = url
            node['reftitle'] = ('C# ' if cls.multi_lang else '') + f'{objtype}: {fullname}'

            return node

        # Use existing link if we have already determined it, for performance
        if name in cls.extlink_cache:
            if CSDebug.ext_links:
                logger.info(f"found in extlink_cache for {name}")
            return create_node(cls.extlink_cache[input_name][0],
                               cls.extlink_cache[input_name][1],
                               cls.extlink_cache[input_name][2])

        # Start search in the ExternalRefsData.external_type_map
        fullname = name
        name_split = name.rsplit('.', 1)
        if len(name_split) == 2:
            # We also have the namespace in the name
            parent, name = name_split
            matches = [(pkg, namespace) for pkg in ExternalRefsData.external_type_map
                       for namespace in ExternalRefsData.external_type_map[pkg]
                       if name in ExternalRefsData.external_type_map[pkg][namespace]
                       and namespace.endswith(parent)]
            if len(matches) > 1:
                # Enforce exact match if there are several
                matches_strict = [i for i in matches if i[1] == parent]
                if len(matches_strict) >= 1:
                    matches = matches_strict
        else:
            # search all namespaces
            parent = None
            matches = [(pkg, namespace) for pkg in ExternalRefsData.external_type_map
                       for namespace in ExternalRefsData.external_type_map[pkg]
                       if name in ExternalRefsData.external_type_map[pkg][namespace]]

        if not matches:
            return None

        if len(matches) > 1:
            logger.warning(f"ambiguous external reference for '{fullname}' using first, "
                           f"found matches: {matches}")

        pkg, parent = matches[0]

        link_name = name
        if name in ExternalRefsData.external_type_rename:
            link_name = ExternalRefsData.external_type_rename[name]

        if parent:
            # Skip for empty strings
            fullname = f'{pkg} ~> {parent}.{name}'
        else:
            fullname = f'{pkg} ~> {name}'

        try:
            apilink = ExternalRefsData.external_search_pages[pkg][0] % fullname
        except KeyError:
            logger.warning(
                f"external links package does not have any links set in EXTERNAL_SEARCH_PAGES, package: {pkg}, "
                f"target fullname: {fullname}")
            return None

        apilink_status_code = 0
        if cls.test_links:
            if not CSDebug.has_printed_test_links:
                CSDebug.has_printed_test_links = True
                logger.info("csharp: external link testing is enabled")
            try:
                apilink_status_code = requests.get(apilink, timeout=3).status_code
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                cls.test_links = False

        if not cls.test_links or apilink_status_code < 400:
            url = apilink
        else:
            # Use search link or homepage instead
            logger.warning(f"invalid API link, using fallback, "
                           f"status_code={apilink_status_code}, apilink={apilink}")
            url = ExternalRefsData.external_search_pages[pkg][1] % fullname

        name = cls.shorten_type(name)
        node = create_node(fullname, name, url)

        # Store result in cache dict
        cls.extlink_cache[input_name] = fullname, name, url

        if CSDebug.ext_links:
            logger.info(f"found external link: {input_name, fullname, name, url}")
        return node
