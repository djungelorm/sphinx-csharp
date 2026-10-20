from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING

from sphinx.application import Sphinx
from sphinx.config import Config

from .config import add_config_values
from .csharp import CSharpDomain

# Note: ExtensionMetadata was added in Sphinx 7.3.
if TYPE_CHECKING:
    from sphinx.util.typing import ExtensionMetadata


def add_stylesheet(app: Sphinx, config: Config) -> None:
    """ Add the stylesheet of the package to the HTML pages, when sphinx_csharp_compact_layout is on """
    if config.sphinx_csharp_compact_layout:
        config.html_static_path = [*config.html_static_path, str(Path(__file__).parent / 'static')]
        app.add_css_file('sphinx_csharp.css')


def setup(app: Sphinx) -> 'ExtensionMetadata':
    """ Setup called by sphinx when the module is added to the extensions list in conf.py """

    # Register domain
    app.add_domain(CSharpDomain)
    app.connect('config-inited', CSharpDomain.apply_config)
    app.connect('config-inited', add_stylesheet)
    # Before intersphinx, which resolves a missing reference at the default priority of 500
    app.connect('missing-reference', CSharpDomain.missing_reference, priority=400)

    add_config_values(app)

    return {
        'version': version('sphinx-csharp'),
        'env_version': 1,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
