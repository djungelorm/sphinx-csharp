import os
from importlib.metadata import version as package_version

project = 'sphinx-csharp'
author = 'djungelorm'
copyright = '2015-2026, djungelorm'
release = package_version('sphinx-csharp')

extensions = ['sphinx.ext.extlinks', 'sphinx_csharp']
exclude_patterns = ['_build']

# Links to the issues and pull requests that track the limitations of Doxygen and Breathe
extlinks = {
    'doxygen': ('https://github.com/doxygen/doxygen/issues/%s', 'doxygen#%s'),
    'breathe': ('https://github.com/breathe-doc/breathe/issues/%s', 'breathe#%s'),
}

# The folder of the site that the docs workflow publishes to: x.y.z for a release tag, dev for main
site = 'https://djungelorm.github.io/sphinx-csharp'
subpath = os.environ.get('DOCS_FOLDER', 'dev')

html_theme = 'pydata_sphinx_theme'
html_title = f'sphinx-csharp {release}'
html_baseurl = f'{site}/{subpath}/'
html_theme_options = {
    'logo': {'text': 'sphinx-csharp'},
    'switcher': {'json_url': f'{site}/switcher.json', 'version_match': subpath},
    'check_switcher': False,
    'show_version_warning_banner': True,
    'navbar_end': ['version-switcher', 'theme-switcher', 'navbar-icon-links'],
    'icon_links': [
        {'name': 'GitHub', 'url': 'https://github.com/djungelorm/sphinx-csharp', 'icon': 'fa-brands fa-github'},
    ],
}

# The home page and the changelog have no section to navigate
html_sidebars = {'index': [], 'changelog': []}

# The examples link every type, so a broken link fails the build
nitpicky = True
