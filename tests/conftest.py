import copy
from pathlib import Path

import pytest
from docutils import nodes
from sphinx import addnodes

from sphinx_csharp.extrefs import ExternalRefs
from sphinx_csharp.extrefs_data import ExternalRefsData

pytest_plugins = ['sphinx.testing.fixtures']


@pytest.fixture(scope='session')
def rootdir():
    return Path(__file__).parent / 'roots'


@pytest.fixture(autouse=True)
def restore_extrefs():
    """ Restore the class-level external reference state that config values are merged into """
    saved = {name: copy.deepcopy(getattr(ExternalRefsData, name))
             for name in ('shorten_type_prefixes', 'ignore_xref_types', 'external_type_map',
                          'external_type_rename', 'external_search_pages')}
    yield
    for name, value in saved.items():
        setattr(ExternalRefsData, name, value)
    ExternalRefs.extlink_cache.clear()


@pytest.fixture
def build(make_app, tmp_path):
    """ Build a single page project from reStructuredText and return the app """
    def _build(rst, parallel=0, **confoverrides):
        (tmp_path / 'conf.py').write_text("extensions = ['sphinx_csharp']\n")
        (tmp_path / 'index.rst').write_text(rst)
        app = make_app('html', srcdir=tmp_path, parallel=parallel,
                       confoverrides={'nitpicky': True, **confoverrides})
        app.build()
        return app
    return _build


def warnings(app):
    return [line for line in app.warning.getvalue().splitlines() if line.strip()]


def signatures(app):
    """ Map each object id on the index page to its rendered signature text """
    doctree = app.env.get_and_resolve_doctree('index', app.builder, tags=app.tags)
    return {node_id: node.astext().replace('\xa0', ' ')
            for node in doctree.findall(addnodes.desc_signature)
            for node_id in node['ids']}


def references(app, node_id):
    """ Map each linked name in a signature to its internal id or external URL """
    doctree = app.env.get_and_resolve_doctree('index', app.builder, tags=app.tags)
    sig = next(node for node in doctree.findall(addnodes.desc_signature) if node_id in node['ids'])
    return {ref.astext(): ref.get('refid') or ref.get('refuri')
            for ref in sig.findall(nodes.reference)}
