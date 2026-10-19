Configuration
=============

sphinx-csharp reads these options from ``conf.py``.

External Links
--------------

A type that the project does not describe links to external documentation, if sphinx-csharp knows it. The ``System`` types link to the Microsoft documentation:

.. code-block:: rst

   .. cs:function:: List<string> Split (string text)

.. cs:function:: List<string> Split (string text)
   :no-index:

Add the types of another library with ``sphinx_csharp_external_type_map``, and the pages that document them with ``sphinx_csharp_external_search_pages``:

.. code-block:: python

   sphinx_csharp_external_search_pages = {
       'widgets': ('https://example.com/api/%s.html', 'https://example.com/search?q=%s'),
   }
   sphinx_csharp_external_type_map = {
       'widgets': {
           'Widgets.Controls': ['Button', 'Slider'],
       },
   }

Each package has a page URL and a search URL, each with ``%s`` in place of the type. A generic type in the map has its number of generic parameters, as in ``IComparer-1``, and takes precedence over a type of the same name without them. The values you set add to the defaults in `extrefs_data.py <https://github.com/djungelorm/sphinx-csharp/blob/main/sphinx_csharp/extrefs_data.py>`_.

.. confval:: sphinx_csharp_external_type_map

   The types of each external package, by namespace. Default: common .NET types as ``msdn``, and Unity types as ``unity``.

.. confval:: sphinx_csharp_external_search_pages

   The page URL and the search URL of each external package. Default: the Microsoft documentation as ``msdn``, and the Unity scripting reference and manual as ``unity`` and ``unityman``.

.. confval:: sphinx_csharp_external_type_rename

   Names to use in the URL of a type in place of its name, such as ``{'NativeArray': 'NativeArray_1'}``. Default: the names of common generic types with their number of generic parameters, such as ``List-1`` for ``List``.

.. confval:: sphinx_csharp_unqualified_namespaces

   Namespaces whose types show without their namespace, such as ``['UnityEngine']``. The namespaces nested in them also count. Default: ``System`` and its namespaces.

.. confval:: sphinx_csharp_ignore_types

   Types that never link, such as ``['Vector2']``. Default: ``void``.

.. confval:: sphinx_csharp_check_external_links

   Whether to request each external link as the build writes it, and use the search URL for a link that fails. The first connection error stops the checks. Default: ``False``.

Other Options
-------------

.. confval:: sphinx_csharp_maximum_signature_line_length

   The length of a signature that puts each parameter on a line of its own. Default: ``None``, which uses the ``maximum_signature_line_length`` option of Sphinx.

.. confval:: sphinx_csharp_multi_language

   Whether link titles start with ``C#``, as in ``C# class: Geometry.Shape``, for a project that documents several languages. Default: ``False``.

.. confval:: sphinx_csharp_debug

   Log verbose debug output, for every category with ``True``, or for a list of the categories ``parse``, ``xref`` and ``external``. Default: ``False``.

Warnings
--------

Each warning has a type, so you can silence it with ``suppress_warnings``:

.. code-block:: python

   suppress_warnings = ['cs.ambiguous']

.. list-table::
   :header-rows: 1

   * - Type
     - Warning
   * - ``cs.parse``
     - A signature is invalid, and shows as written.
   * - ``cs.duplicate``
     - An object is described more than once. References link to the description in the first page by name.
   * - ``cs.ambiguous``
     - A reference matches more than one object, and links to the first.
   * - ``cs.external``
     - An external link is ambiguous, fails the link check, or has no search page for its package.
   * - ``cs.config``
     - An option has an old name, which still works.
   * - ``cs.namespace``
     - A ``namespace-pop`` has no ``namespace-push`` to undo.

Run Sphinx with ``-n``, or set ``nitpicky = True``, to warn about each reference that links to nothing.
