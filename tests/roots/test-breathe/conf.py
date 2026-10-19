project = 'Breathe Test'
version = ''

master_doc = 'index'
source_suffix = '.rst'
extensions = ['sphinx_csharp', 'breathe']

breathe_default_project = 'test-project'
breathe_projects = {'test-project': "_doxygen/xml"}
breathe_show_enumvalue_initializer = True

pygments_style = 'sphinx'
