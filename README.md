# sphinx-csharp

A Sphinx domain for documenting C# APIs. You can write pages by hand with the `cs` directives, or generate them from C# sources with Doxygen and [Breathe](https://github.com/breathe-doc/breathe).

The documentation is at [djungelorm.github.io/sphinx-csharp](https://djungelorm.github.io/sphinx-csharp).

## Usage

Install the package from PyPI:

```
pip install sphinx-csharp
```

Enable the extension in your `conf.py`:

```py
extensions = ['sphinx_csharp']
```

Then describe your API with the `cs` directives, and link to it with the `cs` roles:

```rst
.. cs:namespace:: Geometry

.. cs:class:: public class Circle : Shape

   .. cs:function:: public double Area ()

The area of a :cs:type:`Circle` is :cs:meth:`Circle.Area`.
```

## Development

The project uses [Hatch](https://hatch.pypa.io). The Breathe tests also need [Doxygen](https://www.doxygen.nl) on the PATH, and the lint check needs the [.NET SDK](https://dotnet.microsoft.com/download).

### Checks

```
hatch run lint:check                   # ruff, and dotnet build on the Breathe sources
hatch run types:check                  # mypy
hatch run package:check                # build dist/, check it with twine, and build with the wheel
hatch build                            # sdist and wheel in dist/
```

### Tests

```
hatch run matrix:all                         # tests and coverage in every environment, in parallel
hatch run matrix:all --python 3.14           # every environment for one Python
hatch run matrix:all --full-breathe 5.1      # every test with Breathe 5.1, and the Breathe tests with the others
hatch run test.py3.14-9.1-5.1:all -k parse   # selected tests in one environment
hatch run test.py3.14-9.1-5.1:corpus         # the corpus test
```

The tests use pytest, and any warning fails them, except the deprecation warnings that Breathe raises:

- `tests/test_parse.py` covers the signature parsers.
- `tests/test_render.py` checks rendered signatures and cross-references.
- `tests/test_projects.py` builds the projects in `tests/roots` in nitpicky mode. `test-breathe` runs Doxygen and Breathe, and is skipped without Doxygen.
- `tests/test_corpus.py` builds Newtonsoft.Json, NodaTime, Polly, MoreLINQ and the CommunityToolkit high performance library through Doxygen and Breathe. pytest leaves it out unless you select it with `-m corpus`.

The environments cover every supported Python, each Sphinx minor version from 7.2, and Breathe 4.35, 4.36, 5.0 and 5.1.

### Snapshots

Each test project compares its rendered signatures with the `signatures.txt` in its directory. After a change to the rendering, rewrite them with Breathe 5 installed:

```
pytest tests/test_projects.py --update-snapshots
```

Doxygen 1.15.0 and 1.9.8 must give the same signatures.

### Corpus Test

The corpus test lists the warnings that Doxygen and Breathe cause for each library and Doxygen version. It fails on any other warning, and on a listed warning that matches no warning of the build. It downloads the libraries into `.cache/corpus`, or the directory in `SPHINX_CSHARP_CORPUS_CACHE`.

### CI

- Every test with Breathe 5.1 and Doxygen 1.15.0.
- The Breathe tests with the other Breathe versions, and with Doxygen 1.9.8 from Ubuntu 24.04.
- Every test on Windows with Python 3.14, Sphinx 9.1, Breathe 5.1 and Doxygen 1.15.0. Sphinx reads serially there, so the parallel build tests skip.
- The corpus test, in a separate job.
- `package:check`. The release publishes the `dist/` that it checks.

### Documentation

```
hatch run docs:build                   # the documentation in docs/_build/html
hatch run docs:serve                   # serve it, and rebuild it on each change
```

### Debugging Breathe Output

A signature that Breathe renders wrongly usually comes from C# syntax that the `Parser` productions in `parser.py` do not accept yet. The other cause is the signature that a `visit_*` method in Breathe's `renderer/sphinxrenderer.py` writes.

## Examples

- The [kRPC C# client documentation](https://krpc.github.io/krpc/latest/csharp.html) is the main example of the `cs` domain in use.
- The [vr-modeling documentation](https://vr-modeling.readthedocs.io/Assets/Scripts/Libigl/index.html) by Roger Barton is generated from C# sources through Doxygen and Breathe. Its [`conf.py`](https://github.com/rogerbarton/vr-modeling/blob/69885cd454935e3c5b54ef5a6b9a94da73575b20/conf.py) shows the options in use.

## Credits

sphinx-csharp was originally written by [djungelorm](https://github.com/djungelorm).

Breathe integration and much of the current parser were contributed by [Roger Barton](https://github.com/rogerbarton) in [#8](https://github.com/djungelorm/sphinx-csharp/pull/8).
