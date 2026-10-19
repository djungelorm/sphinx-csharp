from importlib.metadata import version
from typing import TYPE_CHECKING

from sphinx.application import Sphinx

from .config import add_config_values
from .csharp import CSharpDomain

# Note: ExtensionMetadata was added in Sphinx 7.3.
if TYPE_CHECKING:
    from sphinx.util.typing import ExtensionMetadata


def setup(app: Sphinx) -> 'ExtensionMetadata':
    """ Setup called by sphinx when the module is added to the extensions list in conf.py """

    # Register domain
    app.add_domain(CSharpDomain)
    app.connect('config-inited', CSharpDomain.apply_config)
    # Before intersphinx, which resolves a missing reference at the default priority of 500
    app.connect('missing-reference', CSharpDomain.missing_reference, priority=400)

    add_config_values(app)

    return {
        'version': version('sphinx-csharp'),
        'env_version': 1,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
