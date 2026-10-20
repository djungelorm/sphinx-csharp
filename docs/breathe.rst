Doxygen and Breathe
===================

You can generate the pages from C# sources. `Doxygen <https://www.doxygen.nl>`_ reads the sources and the XML documentation comments, and writes XML. `Breathe <https://github.com/breathe-doc/breathe>`_ turns the XML into the directives of the ``cs`` domain.

Setup
-----

Set Doxygen to write XML in your ``Doxyfile``:

.. code-block:: text

   INPUT            = src
   FILE_PATTERNS    = *.cs
   RECURSIVE        = YES
   OUTPUT_DIRECTORY = doxyxml
   GENERATE_XML     = YES
   GENERATE_HTML    = NO
   GENERATE_LATEX   = NO

Run ``doxygen`` in the directory of the ``Doxyfile`` before each Sphinx build. It writes the XML to ``doxyxml/xml``.

Enable Breathe after sphinx-csharp in ``conf.py``, and point it at the XML:

.. code-block:: python

   extensions = ['sphinx_csharp', 'breathe']

   breathe_projects = {'MyLibrary': 'doxyxml/xml'}
   breathe_default_project = 'MyLibrary'

Breathe describes the files of a ``.cs`` project with the ``cs`` domain. Describe a namespace or a class with the Breathe directives:

.. code-block:: rst

   .. doxygennamespace:: MyLibrary
      :members:
      :undoc-members:

   .. doxygenclass:: MyLibrary::Widget
      :members:

Breathe 4.35 or later works, and so do Doxygen 1.9.8 and 1.15.0. The tests of sphinx-csharp build a C# project with each of these versions. They also build C# libraries such as Newtonsoft.Json and NodaTime with Breathe 5.1 and each Doxygen version.

Limitations
-----------

Doxygen and Breathe leave some C# out of the signatures they pass to sphinx-csharp:

- Doxygen drops generic constraints, such as ``where T : class``, and ``protected internal`` members.
- Doxygen drops the members of a record or class with a primary constructor, and a record with a base type.
- Doxygen drops a class with a primary constructor and a base type, and the declarations after it in the same file.
- Doxygen describes a field with a named tuple type, such as ``(int X, int Y) Pos``, as two invalid fields.
- Doxygen drops C# 14 extension blocks and their members.
- Doxygen 1.15.0 puts the members of a type nested in a generic type in the generic type.
- Doxygen 1.9.8 drops a type that has the name of a generic type, such as ``JsonConverter`` beside ``JsonConverter<T>``, and puts its members in the generic type.
- Breathe shows only the ``get`` and ``set`` accessors, without access levels, so ``{ get; private set; }`` and ``{ get; init; }`` render as ``{ get; }``.
- Breathe drops the accessors of events, the underlying types of enums, and the ``ref`` of a ``ref struct``.
- Breathe 4 writes a ``set`` accessor for every property.

Breathe sets its own table of contents entries, so the ``toc_object_entries_show_parents`` option has no effect on its pages.
