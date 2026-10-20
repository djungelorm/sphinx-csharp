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

- Doxygen drops generic constraints, such as ``where T : class``.
- Doxygen describes ``protected internal`` members as internal members, which Breathe leaves out.
- Doxygen drops the members of a record, and a record with a base type (:doxygen:`10087`).
- Doxygen 1.15.0 and earlier drop the members of a class with a primary constructor. With a base type, they drop the class and the declarations after it in the same file (:doxygen:`10594`, fixed in 1.16.0).
- Doxygen describes a field with a named tuple type, such as ``(int X, int Y) Pos``, as two invalid fields.
- Doxygen drops C# 14 extension blocks and their members.
- Doxygen 1.15.0 and later put the members of a type nested in a generic type in the generic type.
- Doxygen 1.9.8 drops a type that has the name of a generic type, such as ``JsonConverter`` beside ``JsonConverter<T>``, and puts its members in the generic type (:doxygen:`8803`, fixed in 1.13.2).
- Doxygen describes an ``init`` accessor as a missing ``set`` accessor, so ``{ get; init; }`` renders as ``{ get; }``.
- Doxygen drops the ``ref`` of a ``ref struct``.
- Breathe shows the ``get`` and ``set`` accessors without access levels, so ``{ get; private set; }`` renders as ``{ get; }``.
- Breathe drops the accessors of events and the underlying types of enums.
- Breathe 4 writes a ``set`` accessor for every property (:breathe:`967`, fixed in 5.0).

Breathe sets its own table of contents entries, so the ``toc_object_entries_show_parents`` option has no effect on its pages.
