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

A signature longer than `maximum_signature_line_length` puts each parameter on a line of its own, unless the directive has the `:single-line-parameter-list:` option.

Each object in a section also gets an entry in the table of contents, with members nested in their types. The `toc_object_entries_show_parents` option sets how much of the name it shows, and the `:no-contents-entry:` option leaves an object out.

### Namespaces

Set the namespace of the objects that follow with `namespace`, and nest a namespace in it with `namespace-push`:

```rst
.. cs:namespace:: MyNamespace

.. cs:namespace-push:: Inner

.. cs:class:: MyClass

.. cs:namespace-pop::
```

MyClass is then `MyNamespace.Inner.MyClass`. `namespace-pop` restores the namespace from before the last `namespace-push`, and `.. cs:namespace:: None` clears the namespace. Each namespace is a target for the `:cs:namespace:` role, unless the directive has the `:no-index:` option.

### Extension Blocks

Describe the members of a C# 14 extension block in an `extension` directive:

```rst
.. cs:class:: public static StringExtensions

   .. cs:extension:: (string s)

      .. cs:property:: bool IsEmpty { get; }
```

The members belong to the enclosing class, as in `StringExtensions.IsEmpty`. The generic parameters of the block, as in `.. cs:extension:: <T>(IEnumerable<T> source)`, are not linked in its members.

### Doc Fields

Describe parameters, type parameters, return values and exceptions with field lists:

```rst
.. cs:function:: T Find<T> (List<T> items, int start)

   :param items: The items to search.
   :type items: List<T>
   :param int start: The index to start at.
   :typeparam T: The item type.
   :returns: The first item.
   :rtype: T
   :throws ArgumentOutOfRangeException: If start is out of range.
```

The types in the `type`, `rtype` and `throws` fields link like the types in a signature.

### References

A reference links to the object whose name ends with the target, preferring the object in the closest enclosing namespace. Start the target with `~` to show only the last part of the name:

```rst
:cs:meth:`~MyNamespace.MyClass.MyMethod` shows MyMethod.
```

### Overloads

Reference an overload by its parameter types:

```rst
.. cs:function:: void Add (int value)
.. cs:function:: void Add (ref int value, string name)

:cs:meth:`Add` links to the first overload, and :cs:meth:`Add(ref int, string)` to the second.
```

Each overload has a target with its parameter types, such as `function-Add(ref-int,string)`. The first overload in a page also has the target `function-Add`. Indexers use brackets, as in `this[string]`. Conversion operators add their return type, as in `op_Implicit(MyType)~int`.

### Generic Types

Reference a generic type or method with or without its generic arguments:

```rst
:cs:type:`Box` and :cs:type:`Box\<T>` link to Box<T>, and :cs:meth:`Box<T>.Put` to its method Put.
```

A role splits a target that ends in `>` into a title and a target, so `` :cs:type:`Box<T>` `` links to `T` with the title `Box`. In a target that ends in `>`, escape each `<` with a backslash.

The target of a generic type has its number of generic parameters, as in the Microsoft docs, such as `class-Box-1` for Box<T> and `function-Box-1.Put` for its method Put. You can document Box and Box<T> side by side, and `` :cs:type:`Box` `` then links to Box.

### Intersphinx

Link to the C# objects of another project with [intersphinx](https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html):

```py
extensions = ['sphinx_csharp', 'sphinx.ext.intersphinx']
intersphinx_mapping = {'library': ('https://example.com/library/', None)}
```

A reference to an object that the project does not describe then links to the other project, in roles and in signatures. Qualify the target with its namespace, or put the reference inside that namespace. Every role, including `:cs:obj:`, works across projects.

### Warnings

Each warning has a type, so you can silence it with `suppress_warnings` in `conf.py`:

```py
suppress_warnings = ['cs.ambiguous']
```

- `cs.parse`: a signature is invalid, and is shown as written.
- `cs.duplicate`: an object is described more than once.
- `cs.ambiguous`: a reference matches more than one object, and links to the first.
- `cs.external`: an external link is ambiguous, fails the link check, or has no search page for its package.
- `cs.config`: an option has a deprecated name.
- `cs.namespace`: a `namespace-pop` has no `namespace-push` to undo.

### Breathe Limitations

Doxygen and Breathe leave some C# out of the signatures they pass to sphinx-csharp:

- Doxygen drops generic constraints, such as `where T : class`, and `protected internal` members.
- Doxygen drops the members of a record or class with a primary constructor, and a record with a base type.
- Doxygen drops a class with a primary constructor and a base type, and the declarations after it in the same file.
- Doxygen describes a field with a named tuple type, such as `(int X, int Y) Pos`, as two invalid fields.
- Doxygen drops C# 14 extension blocks and their members.
- Doxygen 1.15.0 puts the members of a type nested in a generic type in the generic type. Doxygen 1.9.8 drops a type that has the name of a generic type, such as `JsonConverter` beside `JsonConverter<T>`, and puts its members in the generic type.
- Breathe shows only the `get` and `set` accessors without access levels, so `{ get; private set; }` and `{ get; init; }` render as `{ get; }`.
- Breathe drops the accessors of events, the underlying types of enums, and the `ref` of a `ref struct`.

### `conf.py` Options
The options below can be set in `conf.py`. They are registered in [`config.py`](https://github.com/djungelorm/sphinx-csharp/blob/main/sphinx_csharp/config.py), and the defaults for external references are in [`extrefs_data.py`](https://github.com/djungelorm/sphinx-csharp/blob/main/sphinx_csharp/extrefs_data.py). Values you set are merged with these defaults.

Here are all the options. The lists and dictionaries hold example values, which are added to the defaults:

```py
# Are other languages used in the sphinx project, if yes add language (domain) prefix to reference labels
sphinx_csharp_multi_language = False

# Check that each external link exists, and use the search page of its package if it does not
sphinx_csharp_check_external_links = False

# Show types in these namespaces, and in namespaces nested inside them, without their namespace
sphinx_csharp_unqualified_namespaces = [
    'UnityEngine',
]

# Never link these types
sphinx_csharp_ignore_types = [
    'Vector2',
    ...
]

# How to generate external doc links, replace %s with type. Use the format
#    'package name': ('direct link to %s', 'alternate backup link or search page')
sphinx_csharp_external_search_pages = {
    'upm.xrit': ('https://docs.unity3d.com/Packages/com.unity.xr.interaction.toolkit@0.9/api/%s.html',
                 'https://docs.unity3d.com/Packages/com.unity.xr.interaction.toolkit@0.9/?%s'),
    ...
}

# Types that are in an external package. Use the format
#   'package name': {
#      'Namespace1': ['Type1', 'Type2'],
# A generic type named with its arity, such as IComparer-1, takes precedence over a non-generic type
sphinx_csharp_external_type_map = {
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

# Put each parameter on a line of its own in a signature longer than this, in place of maximum_signature_line_length
sphinx_csharp_maximum_signature_line_length = None

# Log verbose debug output, for every category with True, or for a list of 'parse', 'xref' and 'external'
sphinx_csharp_debug = False
```

Earlier versions named some of these options differently. The old names still work, with a `cs.config` warning:

| Old name | New name |
|---|---|
| `sphinx_csharp_test_links` | `sphinx_csharp_check_external_links` |
| `sphinx_csharp_ignore_xref` | `sphinx_csharp_ignore_types` |
| `sphinx_csharp_ext_type_map` | `sphinx_csharp_external_type_map` |
| `sphinx_csharp_ext_search_pages` | `sphinx_csharp_external_search_pages` |
| `sphinx_csharp_debug_parse` and `sphinx_csharp_debug_parse_*` | `sphinx_csharp_debug = ['parse']` |
| `sphinx_csharp_debug_xref` | `sphinx_csharp_debug = ['xref']` |
| `sphinx_csharp_debug_ext_links` | `sphinx_csharp_debug = ['external']` |

## Development

The project uses [Hatch](https://hatch.pypa.io). The Breathe tests also need [Doxygen](https://www.doxygen.nl) on the PATH, and the lint check needs the [.NET SDK](https://dotnet.microsoft.com/download).

```
hatch run lint:check                   # ruff, and dotnet build on the Breathe sources
hatch run types:check                  # mypy
hatch run matrix:all                   # tests and coverage in every environment, in parallel
hatch run matrix:all --python 3.14     # every environment for one Python
hatch run test.py3.14-9.1-5.1:all -k parse   # selected tests in one environment
hatch build                            # sdist and wheel in dist/
```

The tests use pytest. `tests/test_parse.py` covers the signature parsers, and `tests/test_render.py` checks rendered signatures and cross-references. `tests/test_projects.py` builds the projects in `tests/roots` in nitpicky mode and fails on any warning. `test-breathe` renders C# sources through Doxygen and Breathe, and is skipped if Doxygen is not installed. Each project compares its rendered signatures with the `signatures.txt` in its directory. After a change to the rendering, `pytest tests/test_projects.py --update-snapshots` rewrites those files, with Breathe 5 installed. The test environments cover every supported Python, each Sphinx minor version from 7.2, and Breathe 4.35, 4.36, 5.0 and 5.1. CI runs them with Doxygen 1.15.0, and with Doxygen 1.9.8 from Ubuntu 24.04. Both give the same signatures. The lint check compiles the same sources with `dotnet build`. Warnings fail the tests, except the deprecation warnings that Breathe raises.

### Common Bug Sources
- Newer C# syntax that is not supported yet, see the `Parser` productions in `parser.py`
- Incorrect xml reconstruction in breathe, see `def visit_*` in breathe `render/sphinxrenderer.py`
    - e.g. `visit_variable` will create the signature that is given to `csharp.py`

## Examples

- The [kRPC C# client documentation](https://krpc.github.io/krpc/latest/csharp.html) is the main example of the `cs` domain in use.
- The [vr-modeling documentation](https://vr-modeling.readthedocs.io/Assets/Scripts/Libigl/index.html) by Roger Barton is generated from C# sources through Doxygen and Breathe. Its [`conf.py`](https://github.com/rogerbarton/vr-modeling/blob/69885cd454935e3c5b54ef5a6b9a94da73575b20/conf.py) shows the options in use.

## Credits

sphinx-csharp was originally written by [djungelorm](https://github.com/djungelorm).

Breathe integration and much of the current parser were contributed by [Roger Barton](https://github.com/rogerbarton) in [#8](https://github.com/djungelorm/sphinx-csharp/pull/8).
