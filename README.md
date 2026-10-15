# sphinx-csharp

A Sphinx domain for documenting C# APIs, with support for generating the documentation from Doxygen output through [Breathe](https://github.com/breathe-doc/breathe).

The [vr-modeling documentation](https://vr-modeling.readthedocs.io/Assets/Scripts/Libigl/index.html) is an example of the end result:

1. Doxygen generates XML from the C# sources.
1. Breathe and sphinx-csharp convert the XML to Sphinx documentation.
1. Hand-written pages use the `cs` domain directly.

## Usage

Install using pip:

```
pip install sphinx-csharp
```

Enable the extension in your `conf.py`:

```py
extensions = ['sphinx_csharp']
```

See [`test/basic/index.rst`](https://github.com/djungelorm/sphinx-csharp/blob/master/test/basic/index.rst) for examples of the `cs` directives and roles.

### `conf.py` Options
The options below can be set in `conf.py`. They are registered in [`__init__.py`](https://github.com/djungelorm/sphinx-csharp/blob/master/sphinx_csharp/__init__.py), and the defaults for external references are in [`extrefs_data.py`](https://github.com/djungelorm/sphinx-csharp/blob/master/sphinx_csharp/extrefs_data.py). Values you set are merged with these defaults.

Here are the default values for all available options:

```py
# Are other languages used in the sphinx project, if yes add language (domain) prefix to reference labels
sphinx_csharp_multi_language = False

# Should generated external links be tested for validity
sphinx_csharp_test_links = False

# Remove these common prefixes from labels
sphinx_csharp_shorten_type_prefixes = [
    'System.',
    'System.IO',
    ...
]

# Do not create cross references for these standard/build-in types
sphinx_csharp_ignore_xref = [
    'string',
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

See also [this example](https://github.com/rogerbarton/vr-modeling/blob/69885cd454935e3c5b54ef5a6b9a94da73575b20/conf.py).

## Development

The project uses [Hatch](https://hatch.pypa.io). The Breathe test also needs [Doxygen](https://www.doxygen.nl) on the PATH.

```
hatch run lint:check            # ruff
hatch run test:all              # both test projects on every supported Python
hatch run +py=3.14 test:basic   # one test project on one Python
hatch build                     # sdist and wheel in dist/
```

The test projects are Sphinx builds in nitpicky mode with warnings treated as errors. `test/basic` uses hand-written directives, and `test/breathe` renders the C# sources in `test/breathe/cs` through Doxygen and Breathe.

### Common Bug Sources
- Newer C# syntax that is not supported yet, see regexes at beginning of `csharp.py` for parsing
- Incorrect xml reconstruction in breathe, see `def visit_*` in breathe `render/sphinxrenderer.py`
    - e.g. `visit_variable` will create the signature that is given to `csharp.py`

## Credits

Breathe integration and much of the current parser were contributed by [Roger Barton](https://github.com/rogerbarton) in [#8](https://github.com/djungelorm/sphinx-csharp/pull/8).
