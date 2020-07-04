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

    # Register callbacks
    app.connect('config-inited', CSharpDomain.apply_config)
