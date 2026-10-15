# sphinx-csharp

A Sphinx domain for documenting C# APIs. You can write pages by hand with the `cs` directives, or generate them from C# sources with Doxygen and [Breathe](https://github.com/breathe-doc/breathe):

1. Doxygen generates XML from the C# sources.
1. Breathe and sphinx-csharp convert the XML to Sphinx documentation.

## Usage

Install using pip:

```
pip install sphinx-csharp
```

Enable the extension in your `conf.py`:

```py
extensions = ['sphinx_csharp']
```

See [`tests/roots/test-basic/index.rst`](https://github.com/djungelorm/sphinx-csharp/blob/main/tests/roots/test-basic/index.rst) for examples of the `cs` directives and roles.

Each object gets an entry in the general index, such as `MyNamespace.MyClass (C# class)`. To leave an object out, add the `:no-index-entry:` option:

```rst
.. cs:function:: void Helper ()
   :no-index-entry:
```

### `conf.py` Options
The options below can be set in `conf.py`. They are registered in [`__init__.py`](https://github.com/djungelorm/sphinx-csharp/blob/main/sphinx_csharp/__init__.py), and the defaults for external references are in [`extrefs_data.py`](https://github.com/djungelorm/sphinx-csharp/blob/main/sphinx_csharp/extrefs_data.py). Values you set are merged with these defaults.

Here are all the options. The lists and dictionaries hold example values, which are added to the defaults:

```py
# Are other languages used in the sphinx project, if yes add language (domain) prefix to reference labels
sphinx_csharp_multi_language = False

# Should generated external links be tested for validity
sphinx_csharp_test_links = False

# Show types in these namespaces, and in namespaces nested inside them, without their namespace
sphinx_csharp_unqualified_namespaces = [
    'UnityEngine',
]

# Never link these types
sphinx_csharp_ignore_xref = [
    'Vector2',
    ...
]

# How to generate external doc links, replace %s with type. Use the format
#    'package name': ('direct link to %s', 'alternate backup link or search page')
sphinx_csharp_ext_search_pages = {
    'upm.xrit': ('https://docs.unity3d.com/Packages/com.unity.xr.interaction.toolkit@0.9/api/%s.html',
                 'https://docs.unity3d.com/Packages/com.unity.xr.interaction.toolkit@0.9/?%s'),
    ...
}

# Types that are in an external package. Use the format
#   'package name': {
#      'Namespace1': ['Type1', 'Type2'],
sphinx_csharp_ext_type_map = {
    'unity': {
        '': ['MonoBehaviour', 'ScriptableObject'],
        'XR': ['InputDevice', 'InputDeviceCharacteristics'],
        ...
    },
   ...
}

# [Advanced] Rename type before generating external link. Commonly used for generic types
sphinx_csharp_external_type_rename = {
    'List': 'List-1',
    'NativeArray': 'NativeArray_1',
    ...
}

# Debug options, these enable various verbose logging features.
sphinx_csharp_debug = False # enables all debug options
sphinx_csharp_debug_parse = False # enables all parsing options
sphinx_csharp_debug_parse_func = False
sphinx_csharp_debug_parse_var = False
sphinx_csharp_debug_parse_prop = False
sphinx_csharp_debug_parse_attr = False
sphinx_csharp_debug_parse_idxr = False
sphinx_csharp_debug_parse_type = False
sphinx_csharp_debug_xref = False
sphinx_csharp_debug_ext_links = False
```

## Development

The project uses [Hatch](https://hatch.pypa.io). The Breathe test also needs [Doxygen](https://www.doxygen.nl) on the PATH.

```
hatch run lint:check                   # ruff
hatch run types:check                  # mypy
hatch run test:all                     # tests and coverage on every supported Python
hatch run +py=3.14 test:all -k parse   # selected tests on one Python
hatch build                            # sdist and wheel in dist/
```

The tests use pytest. `tests/test_parse.py` covers the signature parsers, and `tests/test_render.py` checks rendered signatures and cross-references. `tests/test_projects.py` builds the projects in `tests/roots` in nitpicky mode and fails on any warning. `test-breathe` renders C# sources through Doxygen and Breathe, and is skipped if Doxygen is not installed.

### Common Bug Sources
- Newer C# syntax that is not supported yet, see regexes at beginning of `csharp.py` for parsing
- Incorrect xml reconstruction in breathe, see `def visit_*` in breathe `render/sphinxrenderer.py`
    - e.g. `visit_variable` will create the signature that is given to `csharp.py`

## Examples

- The [kRPC C# client documentation](https://krpc.github.io/krpc/latest/csharp.html) is the main example of the `cs` domain in use.
- The [vr-modeling documentation](https://vr-modeling.readthedocs.io/Assets/Scripts/Libigl/index.html) by Roger Barton is generated from C# sources through Doxygen and Breathe. Its [`conf.py`](https://github.com/rogerbarton/vr-modeling/blob/69885cd454935e3c5b54ef5a6b9a94da73575b20/conf.py) shows the options in use.

## Credits

sphinx-csharp was originally written by [djungelorm](https://github.com/djungelorm).

Breathe integration and much of the current parser were contributed by [Roger Barton](https://github.com/rogerbarton) in [#8](https://github.com/djungelorm/sphinx-csharp/pull/8).
