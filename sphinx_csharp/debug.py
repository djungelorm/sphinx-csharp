from sphinx.config import Config

from .config import debug_categories


class CSDebug:
    """ The categories of verbose logging that sphinx_csharp_debug turns on """

    parse = False
    xref = False
    external = False

    @classmethod
    def set_config_values(cls, config: Config) -> None:
        """ Initialize debug options from the config """
        categories = debug_categories(config)
        cls.parse = 'parse' in categories
        cls.xref = 'xref' in categories
        cls.external = 'external' in categories
