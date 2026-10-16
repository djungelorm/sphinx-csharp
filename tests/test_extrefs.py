import pytest
import requests
from conftest import references, status, warnings

from sphinx_csharp.debug import CSDebug
from sphinx_csharp.extrefs import ExternalRefs

MICROSOFT_DOCS = 'https://learn.microsoft.com/en-us/dotnet/api/'
MICROSOFT_SEARCH = 'https://learn.microsoft.com/en-us/search/?scope=.NET&terms='


def links(build, typ, **confoverrides):
    """ Build a function taking a parameter of the given type, and return its links and the app """
    app = build(f'.. cs:function:: void Foo ({typ} a)\n', **confoverrides)
    return references(app, 'function-Foo'), app


def test_type_map_config(build):
    refs, app = links(build, 'System.Foo.Bar', sphinx_csharp_ext_type_map={'msdn': {'System.Foo': ['Bar']}})
    assert warnings(app) == []
    assert refs == {'Bar': MICROSOFT_DOCS + 'System.Foo.Bar'}


def test_qualified_name_prefers_exact_namespace(build):
    refs, app = links(build, 'Foo.Bar', sphinx_csharp_ext_type_map={'msdn': {'Lib.Foo': ['Bar'], 'Foo': ['Bar']}})
    assert warnings(app) == []
    assert refs == {'Foo.Bar': MICROSOFT_DOCS + 'Foo.Bar'}


@pytest.mark.parametrize('typ, namespaces, url', [
    ('Foo.Bar', {'A.Foo': ['Bar'], 'B.Foo': ['Bar']}, 'A.Foo.Bar'),
    ('Bar', {'A': ['Bar'], 'B': ['Bar']}, 'A.Bar'),
])
def test_ambiguous_external_reference(build, typ, namespaces, url):
    refs, app = links(build, typ, sphinx_csharp_ext_type_map={'msdn': namespaces})
    assert len(warnings(app)) == 1
    assert f"ambiguous external reference for '{typ}'" in warnings(app)[0]
    assert refs == {typ: MICROSOFT_DOCS + url}


def test_package_without_search_page(build):
    app = build('.. cs:function:: void Foo (Bar a)\n', nitpicky=False,
                sphinx_csharp_ext_type_map={'nopkg': {'N': ['Bar']}})
    assert len(warnings(app)) == 1
    assert 'external links package does not have any links set' in warnings(app)[0]
    assert references(app, 'function-Foo') == {}


def test_debug_logging(build):
    app = build('.. cs:function:: int Foo (int a)\n', sphinx_csharp_debug_ext_links=True)
    log = status(app)
    assert 'found external link' in log
    assert 'found in extlink_cache for int' in log


class Response:
    def __init__(self, status_code):
        self.status_code = status_code


@pytest.mark.parametrize('status_code, url', [
    (200, MICROSOFT_DOCS + 'System.Int32'),
    (404, MICROSOFT_SEARCH + 'System.Int32'),
])
def test_link_testing(build, monkeypatch, status_code, url):
    monkeypatch.setattr(CSDebug, 'has_printed_test_links', False)
    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: Response(status_code))
    refs, app = links(build, 'int', sphinx_csharp_test_links=True)
    assert refs == {'int': url}
    assert 'external link testing is enabled' in status(app)
    assert any('invalid API link' in line for line in warnings(app)) == (status_code == 404)


def test_link_testing_without_connection(build, monkeypatch):
    def get(*args, **kwargs):
        raise requests.exceptions.ConnectionError
    monkeypatch.setattr(CSDebug, 'has_printed_test_links', True)
    monkeypatch.setattr(requests, 'get', get)
    refs, app = links(build, 'int', sphinx_csharp_test_links=True)
    assert warnings(app) == []
    assert 'external link testing is enabled' not in status(app)
    assert refs == {'int': MICROSOFT_DOCS + 'System.Int32'}
    assert not ExternalRefs.test_links
