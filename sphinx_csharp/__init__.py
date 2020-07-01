from sphinx.application import Sphinx
from sphinx_csharp.csharp import CSharpDomain

def setup(app: Sphinx):
    app.add_domain(CSharpDomain)
