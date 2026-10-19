from pathlib import Path

import pytest
from docutils import nodes
from sphinx import addnodes, version_info

pytest_plugins = ['sphinx.testing.fixtures']



@pytest.fixture(scope='session')
def rootdir():
    return Path(__file__).parent / 'roots'


@pytest.fixture
def build(make_app, tmp_path):
    """ Build a project from reStructuredText for the index and any other pages, and return the app """
    def _build(rst, pages=None, parallel=0, **confoverrides):
        (tmp_path / 'conf.py').write_text("extensions = ['sphinx_csharp']\n")
        (tmp_path / 'index.rst').write_text(rst)
        for name, page in (pages or {}).items():
            (tmp_path / f'{name}.rst').write_text(page)
        app = make_app('html', srcdir=tmp_path, parallel=parallel,
                       confoverrides={'nitpicky': True, **confoverrides})
        app.build()
        return app
    return _build


def resolved_doctree(app):
    # Sphinx 9 deprecates calls without tags, and earlier versions reject the argument
    kwargs = {'tags': app.tags} if version_info >= (9,) else {}
    return app.env.get_and_resolve_doctree('index', app.builder, **kwargs)


# Note: SphinxTestApp.status and SphinxTestApp.warning were added in Sphinx 7.3.
def status(app):
    return app._status.getvalue()


def warnings(app):
    return [line for line in app._warning.getvalue().splitlines() if line.strip()]


def signature_texts(app):
    """ The ids and rendered text of each signature on the index page """
    return [(node['ids'], node.astext().replace('\xa0', ' '))
            for node in resolved_doctree(app).findall(addnodes.desc_signature)]


def signature_lines(app):
    """ Each signature on the index page as its ids and text, in the sorted order of the signatures.txt files """
    return sorted(' '.join(ids) + ' | ' + text for ids, text in signature_texts(app))


def signatures(app):
    """ Map each object id on the index page to its rendered signature text """
    return {node_id: text for ids, text in signature_texts(app) for node_id in ids}


def references(app, node_id=None):
    """ Map each linked name to its target, in one signature or in the whole index page """
    doctree = resolved_doctree(app)
    if node_id is not None:
        doctree = next(node for node in doctree.findall(addnodes.desc_signature) if node_id in node['ids'])
    return {ref.astext(): ref.get('refid') or ref.get('refuri')
            for ref in doctree.findall(nodes.reference) if 'internal' in ref or 'refuri' in ref}
