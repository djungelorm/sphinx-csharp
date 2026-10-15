from importlib.metadata import version

from sphinx.application import Sphinx

from .csharp import CSharpDomain
from .debug import CSDebug


def setup(app: Sphinx) -> dict:
    """ Setup called by sphinx when the module is added to the extensions list in conf.py """

    # Register domain
    app.add_domain(CSharpDomain)
    app.connect('config-inited', CSharpDomain.apply_config)

    # Add variables available in conf.py
    app.add_config_value('sphinx_csharp_test_links', False, 'env')
    app.add_config_value('sphinx_csharp_multi_language', False, 'env')
    app.add_config_value('sphinx_csharp_unqualified_namespaces', None, 'env')
    app.add_config_value('sphinx_csharp_ignore_xref', None, 'env')
    app.add_config_value('sphinx_csharp_ext_type_map', None, 'env')
    app.add_config_value('sphinx_csharp_external_type_rename', None, 'env')
    app.add_config_value('sphinx_csharp_ext_search_pages', None, 'env')

    CSDebug.add_config_values(app)

    return {
        'version': version('sphinx-csharp'),
        'env_version': 1,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
