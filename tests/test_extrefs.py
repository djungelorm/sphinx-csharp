import http.client
import urllib.error
import urllib.request
from email.message import Message
from unittest.mock import MagicMock

import pytest
from conftest import references, status, warnings

from sphinx_csharp.extrefs import ExternalRefs

MICROSOFT_DOCS = 'https://learn.microsoft.com/en-us/dotnet/api/'
MICROSOFT_SEARCH = 'https://learn.microsoft.com/en-us/search/?scope=.NET&terms='


def links(build, typ, **confoverrides):
    """ Build a function taking a parameter of the given type, and return its links and the app """
    app = build(f'.. cs:function:: void Foo ({typ} a)\n', **confoverrides)
    return references(app, 'function-Foo'), app


def test_type_map_config(build):
    refs, app = links(build, 'System.Foo.Bar', sphinx_csharp_external_type_map={'msdn': {'System.Foo': ['Bar']}})
    assert warnings(app) == []
    assert refs == {'Bar': MICROSOFT_DOCS + 'System.Foo.Bar'}


def test_qualified_name_prefers_exact_namespace(build):
    refs, app = links(build, 'Foo.Bar', sphinx_csharp_external_type_map={'msdn': {'Lib.Foo': ['Bar'], 'Foo': ['Bar']}})
    assert warnings(app) == []
    assert refs == {'Foo.Bar': MICROSOFT_DOCS + 'Foo.Bar'}


def test_namespace_matches_whole_names(build):
    app = build('.. cs:function:: void Foo (O.Stream a)\n')
    assert len(warnings(app)) == 1
    assert 'reference target not found: O.Stream' in warnings(app)[0]


@pytest.mark.parametrize('typ, namespaces, url', [
    ('Foo.Bar', {'A.Foo': ['Bar'], 'B.Foo': ['Bar']}, 'A.Foo.Bar'),
    ('Bar', {'A': ['Bar'], 'B': ['Bar']}, 'A.Bar'),
])
def test_ambiguous_external_reference(build, typ, namespaces, url):
    refs, app = links(build, typ, sphinx_csharp_external_type_map={'msdn': namespaces})
    assert len(warnings(app)) == 1
    assert f"ambiguous external reference for '{typ}'" in warnings(app)[0]
    assert refs == {typ: MICROSOFT_DOCS + url}


@pytest.mark.parametrize('typ, url', [
    ('IEqualityComparer', 'System.Collections.IEqualityComparer'),
    ('IEqualityComparer<int>', 'System.Collections.Generic.IEqualityComparer-1'),
    ('IEnumerator<int>', 'System.Collections.Generic.IEnumerator-1'),
    ('IEnumerable', 'System.Collections.IEnumerable'),
    ('IEnumerable<int>', 'System.Collections.Generic.IEnumerable-1'),
    ('IList', 'System.Collections.IList'),
    ('IList<int>', 'System.Collections.Generic.IList-1'),
    ('ICollection', 'System.Collections.ICollection'),
    ('IDictionary<int, int>', 'System.Collections.Generic.IDictionary-2'),
    ('Collection', 'System.Collections.ObjectModel.Collection-1'),
])
def test_generic_type_with_arity(build, typ, url):
    refs, app = links(build, typ)
    assert warnings(app) == []
    assert refs[typ.partition('<')[0]] == MICROSOFT_DOCS + url


def test_package_without_search_page(build):
    app = build('.. cs:function:: void Foo (Bar a)\n', nitpicky=False,
                sphinx_csharp_external_type_map={'nopkg': {'N': ['Bar']}})
    assert len(warnings(app)) == 1
    assert 'external links package does not have any links set' in warnings(app)[0]
    assert references(app, 'function-Foo') == {}


def test_debug_logging(build):
    app = build('.. cs:function:: int Foo (int a)\n', sphinx_csharp_debug=['external'])
    log = status(app)
    assert 'found external link' in log
    assert 'found in extlink_cache for int' in log


def urlopen(status_code, error=None):
    """ A replacement for urlopen that responds with a status code, or raises error if the status code is None """
    def _urlopen(url, timeout):
        if status_code is None:
            raise error or urllib.error.URLError('connection refused')
        if status_code >= 400:
            raise urllib.error.HTTPError(url, status_code, 'Not Found', Message(), None)
        response = MagicMock()
        response.__enter__.return_value.status = status_code
        return response
    return _urlopen


@pytest.mark.parametrize('status_code, url', [
    (200, MICROSOFT_DOCS + 'System.Int32'),
    (404, MICROSOFT_SEARCH + 'System.Int32'),
])
def test_link_testing(build, monkeypatch, status_code, url):
    monkeypatch.setattr(urllib.request, 'urlopen', urlopen(status_code))
    app = build('.. cs:function:: void Foo (int a, string b)\n', sphinx_csharp_check_external_links=True)
    assert len(warnings(app)) == (2 if status_code == 404 else 0)
    assert all('invalid API link' in line for line in warnings(app))
    assert status(app).count('external link testing is enabled') == 1
    assert references(app, 'function-Foo')['int'] == url


@pytest.mark.parametrize('error', [
    urllib.error.URLError('connection refused'),
    http.client.RemoteDisconnected('closed'),
    http.client.InvalidURL('control character'),
    http.client.IncompleteRead(b''),
])
def test_link_testing_without_connection(build, monkeypatch, error):
    monkeypatch.setattr(urllib.request, 'urlopen', urlopen(None, error))
    refs, app = links(build, 'int', sphinx_csharp_check_external_links=True)
    assert warnings(app) == []
    assert refs == {'int': MICROSOFT_DOCS + 'System.Int32'}
    assert not ExternalRefs.check_links
