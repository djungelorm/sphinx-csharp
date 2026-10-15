project = 'Breathe Test'
version = ''

master_doc = 'index'
source_suffix = '.rst'
extensions = ['sphinx_csharp', 'breathe']

breathe_default_project = 'test-project'
breathe_projects = {'test-project': "_doxygen/xml"}

pygments_style = 'sphinx'

# Debug options
sphinx_csharp_debug = False
sphinx_csharp_debug_parse = False
sphinx_csharp_debug_parse_func = False
sphinx_csharp_debug_parse_var = False
sphinx_csharp_debug_parse_prop = False
sphinx_csharp_debug_parse_attr = False
sphinx_csharp_debug_parse_idxr = False
sphinx_csharp_debug_parse_type = False
sphinx_csharp_debug_xref = False
sphinx_csharp_debug_ext_links = False
