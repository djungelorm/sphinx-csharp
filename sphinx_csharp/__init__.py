from sphinx.application import Sphinx
from sphinx_csharp.csharp import CSharpDomain


def setup(app: Sphinx) -> None:
    """ Setup called by sphinx when the module is added to the extensions list in conf.py """

    # Register domain
    app.add_domain(CSharpDomain)

    # Add variables available in conf.py
    app.add_config_value('sphinx_csharp_test_links', False, 'env')
    app.add_config_value('sphinx_csharp_ignore_xref', None, 'env')
    app.add_config_value('sphinx_csharp_ext_type_map', None, 'env')
    app.add_config_value('sphinx_csharp_external_type_rename', None, 'env')
    app.add_config_value('sphinx_csharp_ext_search_pages', None, 'env')

    # Debug
    app.add_config_value('sphinx_csharp_debug', False, '')
    app.add_config_value('sphinx_csharp_debug_parse', False, '')
    app.add_config_value('sphinx_csharp_debug_parse_func', False, '')
    app.add_config_value('sphinx_csharp_debug_parse_var', False, '')
    app.add_config_value('sphinx_csharp_debug_parse_prop', False, '')
    app.add_config_value('sphinx_csharp_debug_parse_attr', False, '')
    app.add_config_value('sphinx_csharp_debug_parse_idxr', False, '')
    app.add_config_value('sphinx_csharp_debug_parse_type', False, '')
    app.add_config_value('sphinx_csharp_debug_xref', False, '')
    app.add_config_value('sphinx_csharp_debug_ext_links', False, '')

    # Register callbacks
    app.connect('config-inited', CSharpDomain.apply_config)
