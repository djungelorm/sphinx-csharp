""" The sphinx_csharp_* config values """

from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.util import logging

logger = logging.getLogger(__name__)

# The deprecated names of config values, and the names that replace them
RENAMED = {
    'sphinx_csharp_test_links': 'sphinx_csharp_check_external_links',
    'sphinx_csharp_ignore_xref': 'sphinx_csharp_ignore_types',
    'sphinx_csharp_ext_type_map': 'sphinx_csharp_external_type_map',
    'sphinx_csharp_ext_search_pages': 'sphinx_csharp_external_search_pages',
}

# The categories of debug logging that sphinx_csharp_debug turns on
DEBUG_CATEGORIES = ['parse', 'xref', 'external']

# The deprecated debug flags, and the categories that replace them
DEBUG_FLAGS = {
    'sphinx_csharp_debug_parse': 'parse',
    'sphinx_csharp_debug_parse_func': 'parse',
    'sphinx_csharp_debug_parse_var': 'parse',
    'sphinx_csharp_debug_parse_prop': 'parse',
    'sphinx_csharp_debug_parse_attr': 'parse',
    'sphinx_csharp_debug_parse_idxr': 'parse',
    'sphinx_csharp_debug_parse_type': 'parse',
    'sphinx_csharp_debug_xref': 'xref',
    'sphinx_csharp_debug_ext_links': 'external',
}


def add_config_values(app: Sphinx) -> None:
    """ Register the config values, and the deprecated names that are still accepted """
    app.add_config_value('sphinx_csharp_multi_language', False, 'env')
    app.add_config_value('sphinx_csharp_unqualified_namespaces', None, 'env')
    app.add_config_value('sphinx_csharp_ignore_types', None, 'env')
    app.add_config_value('sphinx_csharp_external_type_map', None, 'env')
    app.add_config_value('sphinx_csharp_external_type_rename', None, 'env')
    app.add_config_value('sphinx_csharp_external_search_pages', None, 'env')
    app.add_config_value('sphinx_csharp_check_external_links', False, 'env')
    # Put each parameter on a line of its own in a longer signature, in place of maximum_signature_line_length
    app.add_config_value('sphinx_csharp_maximum_signature_line_length', None, 'env', types=(int, type(None)))
    # True for every category, or a list of categories
    app.add_config_value('sphinx_csharp_debug', False, '', types=(bool, list, tuple))
    for name in RENAMED:
        app.add_config_value(name, None, 'env')
    for name in DEBUG_FLAGS:
        app.add_config_value(name, None, '')


def apply_deprecated_names(config: Config) -> None:
    """ Copy each deprecated config value that is set to the value that replaces it """
    for old, new in RENAMED.items():
        if config[old] is not None:
            warn_deprecated(old, new)
            config[new] = config[old]

    categories = []
    for name, category in DEBUG_FLAGS.items():
        if config[name] is not None:
            warn_deprecated(name, f"sphinx_csharp_debug = ['{category}']")
            if config[name]:
                categories.append(category)
    if categories and config['sphinx_csharp_debug'] is not True:
        config['sphinx_csharp_debug'] = sorted({*(config['sphinx_csharp_debug'] or []), *categories})


def debug_categories(config: Config) -> set[str]:
    """ The categories of debug logging that sphinx_csharp_debug turns on """
    value = config['sphinx_csharp_debug']
    categories = set(DEBUG_CATEGORIES if value is True else value or [])
    unknown = categories - set(DEBUG_CATEGORIES)
    if unknown:
        raise ValueError(f'unknown sphinx_csharp_debug categories {sorted(unknown)}, use {DEBUG_CATEGORIES}')
    return categories


def warn_deprecated(old: str, new: str) -> None:
    logger.warning(f'{old} is deprecated, use {new}', type='cs', subtype='config')
