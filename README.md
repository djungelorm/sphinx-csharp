# sphinx-csharp

C# Domain for Sphinx with Breathe integration. Used to create ReadTheDocs style C# documentation.

See [vr-modeling example](https://vr-modeling.readthedocs.io/Assets/Scripts/Libigl/index.html) end-product.

**Idea:**
1. Generate Doxygen xml
1. Convert this to Sphinx using breathe + sphinx-csharp
1. Apply ReadTheDocs theme
1. Write rst using the `cs` domain

## Usage

Install using pip:

```
pip install git+https://github.com/rogerbarton/sphinx-csharp.git
```

To enable the extension, add the following to your conf.py:

```py
extensions = ['sphinx_csharp']
```

See https://github.com/djungelorm/sphinx-csharp/pull/8 for usage/changes from upstream and also [this rst example](https://raw.githubusercontent.com/rogerbarton/sphinx-csharp/master/test/index.rst).

### `conf.py` Options
Various options can be set in the sphinx `conf.py`. See `__init__.py:setup()` for available options. Defaults for external references are indicated or in [`extrefs_data.py`](https://github.com/rogerbarton/sphinx-csharp/blob/master/sphinx_csharp/extrefs_data.py). 
See also `csharp.py:apply_config(cls, config: Config)` for exact defaults. 

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
sphinx_csharp_debug = False
sphinx_csharp_debug_parse = False
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

### Examples and Tests

See build scripts in `test`. This is quite incomplete at the moment. The [vr-modeling example](https://vr-modeling.readthedocs.io/Assets/Scripts/Libigl/index.html) will likely be most useful as a reference.


## Common Bug Sources
- Newer C# syntax that is not supported yet, see regexes at beginning of `csharp.py` for parsing
- Incorrect xml reconstruction in breathe, see `def visit_*` in breathe `render/sphinxrenderer.py`
    - e.g. `visit_variable` will create the signature that is given to `csharp.py` 