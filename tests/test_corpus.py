""" Build the documentation of large C# libraries with Doxygen and Breathe """

import codecs
import hashlib
import os
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path
from typing import NamedTuple

import pytest
from conftest import warnings


class Corpus(NamedTuple):
    name: str
    url: str
    sha256: str
    # The top directory of the archive, and the library sources in it without the tests
    root: str
    sources: str
    # The types that never resolve. Most are generic parameters that Doxygen writes in base types.
    nitpick_ignore: list[str | tuple[str, str]] = []
    # Parts of the first lines of the warnings that Doxygen and Breathe cause
    known_warnings: list[str | tuple[str, str]] = []
    suppress_warnings: list[str] = []


# An entry for one Doxygen version is a (version, entry) pair, and an entry for both is a string
OLD = '1.9.8'
NEW = '1.15.0'

# Breathe writes a C# using alias as a C++ type alias
USING_ALIAS = 'Invalid C++ declaration'
# Doxygen 1.15.0 puts the members of a type nested in a generic type in the generic type. Doxygen 1.9.8 puts the
# members of a type in the generic type of the same name, such as JsonConverter in JsonConverter<T>.
DUPLICATE = 'duplicate description of '
ENUMERABLES = 'CommunityToolkit.HighPerformance.Enumerables'

CORPORA = [
    # Generics, attributes, overloads, nullable types and operators
    Corpus('newtonsoft', 'https://github.com/JamesNK/Newtonsoft.Json/archive/refs/tags/13.0.4.tar.gz',
           '71fb8eda5ee37ab3405ea5df6c2a9490716e411db82e6c0878132bdf29aedb17',
           'Newtonsoft.Json-13.0.4', 'Src/Newtonsoft.Json',
           # ReadType is an internal enum that Doxygen 1.9.8 leaves out of its namespace
           nitpick_ignore=['T', (OLD, 'ReadType'), (NEW, 'TKey'), (NEW, 'TElement'), (NEW, 'TEnumeratorKey'),
                           (NEW, 'TEnumeratorValue')],
           known_warnings=[USING_ALIAS, (OLD, DUPLICATE + 'function Newtonsoft.Json.JsonConverter-1.')]),
    # Structs, operators, conversions, nested types and XML serialization
    Corpus('nodatime', 'https://github.com/nodatime/nodatime/archive/refs/tags/3.3.0.tar.gz',
           'bc729687e2e0f662c7cb5e80273267320dd69ade20c3645e50f6b4d8817b0311',
           'nodatime-3.3.0', 'src/NodaTime',
           nitpick_ignore=['T', (OLD, 'TResult'), (OLD, 'TBucket')],
           # Doxygen garbles a tuple return type with element names and a lambda in a field initializer. Doxygen
           # 1.9.8 drops the dot in a nested base type, and writes a reference without a target.
           known_warnings=['Method signature invalid: long int nanoseconds ToUnixTimeSecondsAndNanoseconds',
                           'WindowsMapping.PrimaryMapping.ToDictionary(pair=> pair.Key',
                           (OLD, '>IPostPatternParseFormatAction'), (OLD, "undefined label: ''"),
                           (NEW, DUPLICATE + 'var NodaTime.Text.CompositePatternBuilder-1.'),
                           (NEW, DUPLICATE + 'var NodaTime.Text.Patterns.SteppedPatternBuilder-2.')]),
    # Modern C#, with file-scoped namespaces, records, init accessors and async methods
    Corpus('polly', 'https://github.com/App-vNext/Polly/archive/refs/tags/8.8.0.tar.gz',
           '1d7a8b5a742ddfdcf6126e3f53e5928c4f9b71e0abac17eb1cc90b77e14eceb5',
           'Polly-8.8.0', 'src/Polly.Core',
           # Doxygen drops the generic parameters of the generic methods of a generic class, and garbles a base type
           nitpick_ignore=['TResult', 'BridgeComponentBase', (OLD, 'T'), (OLD, 'TKey')],
           # Doxygen merges a constructor with an initializer or an expression body into the next member
           known_warnings=['Method signature invalid: BrokenCircuitException(',
                           'Method signature invalid: TimeoutRejectedException(SerializationInfo info',
                           'Variable signature invalid: BridgeComponent(',
                           'Variable signature invalid: HedgingPredicateArguments(',
                           'Variable signature invalid: Outcome(Exception exception)',
                           'Variable signature invalid: TimeoutRejectedException(TimeSpan timeout)',
                           (NEW, DUPLICATE + 'var Polly.Registry.ResiliencePipelineRegistry-1.'),
                           (NEW, DUPLICATE + 'function Polly.Registry.ResiliencePipelineRegistry-1.DisposeAsync()'),
                           (OLD, DUPLICATE + 'var Polly.ResiliencePipeline-1.'),
                           (OLD, DUPLICATE + 'function Polly.ResiliencePipeline-1.'),
                           (OLD, DUPLICATE + 'function Polly.ResiliencePipelineBuilder-1.'),
                           (OLD, DUPLICATE + 'function Polly.Simmy.ChaosStrategy-1.'),
                           (OLD, DUPLICATE + 'function Polly.Utils.Pipeline.BridgeComponent-1.')]),
    # Spans, ref structs, pointers and unsafe code
    Corpus('toolkit', 'https://github.com/CommunityToolkit/dotnet/archive/refs/tags/v8.4.2.tar.gz',
           '0df05beae045ed4e8692f6cf7d129d66204dd3738605032341f11e828524181b',
           'dotnet-8.4.2', 'src/CommunityToolkit.HighPerformance',
           nitpick_ignore=[(OLD, 'T')],
           # Doxygen makes a member from an expression body
           known_warnings=[USING_ALIAS, 'Method signature invalid: implicit ReadOnlyMemory2D< T > (ref memory)',
                           (NEW, DUPLICATE + f'var {ENUMERABLES}.ReadOnlySpanEnumerable-1.'),
                           (NEW, DUPLICATE + f'var {ENUMERABLES}.SpanEnumerable-1.')]),
    # Extension methods, many overloads, tuples and generic delegates
    Corpus('morelinq', 'https://github.com/morelinq/MoreLINQ/archive/refs/tags/v4.4.0.tar.gz',
           '7d1301895802c4c570f524355bccd13ba3473cbdc4d0b71ef7db8d72ff28da66',
           'MoreLINQ-4.4.0', 'MoreLinq',
           # Doxygen garbles tuple return types with element names, and a query expression
           nitpick_ignore=['T', 'TCardinality'],
           known_warnings=[USING_ALIAS, 'Method signature invalid: bool T Value Some< T >',
                           'Method signature invalid: TCardinality? T Value TrySingle< T, TCardinality >',
                           'Method signature invalid: IEnumerable< T > IEnumerable< T > False Partition< T >',
                           'Method signature invalid: IEnumerable< KeyValuePair< int, TSource > > TSource '
                           '(e.Value.Index'],
           # Doxygen escapes > in the code examples
           suppress_warnings=['misc.highlighting_failure']),
]


def for_doxygen(entries, version):
    """ The entries for a Doxygen version, from entries that are strings or (version, entry) pairs """
    return [entry if isinstance(entry, str) else entry[1] for entry in entries
            if isinstance(entry, str) or entry[0] == version]


def doxygen_version():
    """ The version of the corpus entries that the installed Doxygen matches """
    version = subprocess.run(['doxygen', '--version'], check=True, capture_output=True, text=True).stdout.split()[0]
    return OLD if tuple(int(part) for part in version.split('.')[:2]) < (1, 10) else NEW


def download(corpus):
    """ Download the archive of a library into the cache, check it, and return its path """
    cache = Path(os.environ.get('SPHINX_CSHARP_CORPUS_CACHE', Path(__file__).parent.parent / '.cache' / 'corpus'))
    path = cache / (corpus.root + '.tar.gz')
    if path.exists():
        content = path.read_bytes()
    else:
        with urllib.request.urlopen(corpus.url, timeout=60) as response:
            content = response.read()
    digest = hashlib.sha256(content).hexdigest()
    assert digest == corpus.sha256, f'{corpus.url} has sha256 {digest}, expected {corpus.sha256}. Delete {path} ' \
        'if it is in the cache.'
    if not path.exists():
        cache.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return path


def extract_sources(corpus, dest):
    """ Extract the C# sources of a library """
    prefix = corpus.root + '/' + corpus.sources + '/'
    with tarfile.open(download(corpus)) as tar:
        for member in tar:
            if member.isfile() and member.name.startswith(prefix) and member.name.endswith('.cs'):
                data = tar.extractfile(member).read()
                if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
                    data = data.decode('utf-16').encode()
                # Doxygen copies invalid UTF-8 into its XML, which Breathe then fails to parse
                try:
                    data.decode()
                except UnicodeDecodeError:
                    data = data.decode('latin-1').encode()
                path = dest / member.name.removeprefix(prefix)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)


def messages(app):
    """ The first line of each message of a build """
    return [line for line in warnings(app) if any(level in line for level in ('WARNING:', 'ERROR:', 'CRITICAL:'))]


@pytest.mark.corpus
@pytest.mark.skipif(shutil.which('doxygen') is None, reason='doxygen is not installed')
@pytest.mark.parametrize('corpus', CORPORA, ids=[corpus.name for corpus in CORPORA])
# Doxygen nests paragraphs with text in them, which Breathe warns about as it parses
@pytest.mark.filterwarnings('ignore:Warning on line:UserWarning')
def test_corpus(make_app, rootdir, tmp_path, corpus):
    pytest.importorskip('breathe')
    srcdir = tmp_path / corpus.name
    shutil.copytree(rootdir / 'test-corpus', srcdir)
    extract_sources(corpus, srcdir / 'src')
    subprocess.run(['doxygen'], cwd=srcdir, check=True)
    app = make_app('html', srcdir=srcdir, confoverrides={
        'nitpicky': True,
        'suppress_warnings': corpus.suppress_warnings,
    })
    app.build()
    version = doxygen_version()
    known = for_doxygen(corpus.known_warnings, version) + \
        [f'reference target not found: {name} [' for name in for_doxygen(corpus.nitpick_ignore, version)]
    found = messages(app)
    assert [message for message in found if not any(entry in message for entry in known)] == []
    # A fix removes its entry from the list, as a fix of a known bug removes its xfail marker
    assert [entry for entry in known if not any(entry in message for message in found)] == []
