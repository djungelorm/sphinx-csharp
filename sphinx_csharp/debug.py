class CSDebug:
    """ Contains all debug variables for sphinx_csharp """

    # Config Flags
    all = False
    parse = False
    parse_func = False
    parse_var = False
    parse_prop = False
    parse_attr = False
    parse_idxr = False
    parse_type = False
    xref = False
    ext_links = False

    # State related
    has_printed_test_links = False
    has_printed_xref_objects = False

    @classmethod
    def add_config_values(cls, app):
        """ Register the config values and set default values """
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

    @classmethod
    def set_config_values(cls, config):
        """ Initialize debug options from the config """
        cls.all = config['sphinx_csharp_debug']
        cls.parse = cls.all or config['sphinx_csharp_debug_parse']
        cls.parse_func = cls.all or cls.parse or config['sphinx_csharp_debug_parse_func']
        cls.parse_var = cls.all or cls.parse or config['sphinx_csharp_debug_parse_var']
        cls.parse_prop = cls.all or cls.parse or config['sphinx_csharp_debug_parse_prop']
        cls.parse_attr = cls.all or cls.parse or config['sphinx_csharp_debug_parse_attr']
        cls.parse_idxr = cls.all or cls.parse or config['sphinx_csharp_debug_parse_idxr']
        cls.parse_type = cls.all or cls.parse or config['sphinx_csharp_debug_parse_type']
        cls.xref = cls.all or config['sphinx_csharp_debug_xref']
        cls.ext_links = cls.all or config['sphinx_csharp_debug_ext_links']
