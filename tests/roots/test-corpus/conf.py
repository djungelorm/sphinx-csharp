project = 'Corpus Test'
version = ''

master_doc = 'index'
source_suffix = '.rst'
extensions = ['sphinx_csharp', 'breathe']

breathe_default_project = 'corpus'
breathe_projects = {'corpus': '_doxygen/xml'}
breathe_show_enumvalue_initializer = True

