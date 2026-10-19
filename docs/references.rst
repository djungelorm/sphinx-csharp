References
==========

The roles link to the objects that the directives describe:

.. code-block:: rst

   :cs:type:`Geometry.Shape` has the method :cs:meth:`Geometry.Shape.Area`.

:cs:type:`Geometry.Shape` has the method :cs:meth:`Geometry.Shape.Area`.

Roles
-----

Each role links to the objects of some directives:

.. list-table::
   :header-rows: 1

   * - Role
     - Links to
   * - ``:cs:type:``
     - classes, structs, interfaces, records, enums and delegates
   * - ``:cs:class:``, ``:cs:struct:``, ``:cs:interface:``, ``:cs:record:``, ``:cs:enum:``, ``:cs:delegate:``
     - the objects of the directive with the same name
   * - ``:cs:meth:`` or ``:cs:func:``
     - methods, constructors, operators and delegates
   * - ``:cs:var:``, ``:cs:prop:``, ``:cs:event:``
     - fields, properties and events
   * - ``:cs:member:``
     - methods, fields, properties and events
   * - ``:cs:idxr:``
     - indexers
   * - ``:cs:enumerator:`` or ``:cs:value:``
     - enum values
   * - ``:cs:attr:``
     - attributes
   * - ``:cs:namespace:``
     - namespaces
   * - ``:cs:obj:``
     - every kind of object

The ``:any:`` role also links to C# objects.

Name Resolution
---------------

A target links to the object whose full name ends with it. When several objects match, the target links to the object in the closest enclosing namespace or type:

.. code-block:: rst

   .. cs:namespace:: Geometry

   :cs:type:`Point` links to Geometry.Point, from anywhere in the namespace.

A target resolves to the first of these that it matches:

#. An object of the project whose full name is the target, or the target qualified by the current namespace or type, or by one enclosing it.
#. A type in the external type map, such as a .NET or Unity type, which links to its external documentation. :doc:`configuration` describes how to add other libraries.
#. Any object of the project whose name ends with the target.

Start a target with ``~`` to show only the last part of the name:

.. code-block:: rst

   :cs:meth:`~Geometry.Shape.Area` shows Area.

:cs:meth:`~Geometry.Shape.Area` shows Area.

Overloads
---------

A target without parameters links to the first overload of a method. Give the parameter types to link to one overload:

.. code-block:: rst

   :cs:meth:`Geometry.Polygon.Polygon(Point[])` and
   :cs:meth:`Geometry.Polygon.Polygon(IEnumerable<Point>)`

:cs:meth:`Geometry.Polygon.Polygon(Point[])` and
:cs:meth:`Geometry.Polygon.Polygon(IEnumerable<Point>)`

The parameter types include the ``ref``, ``out`` and ``in`` modifiers, as in ``TryGetPoint(int, out Point?)``. An indexer takes its parameter types in brackets, as in ``this[int]``. A conversion operator adds its type after a tilde, as in ``op_Explicit(Polygon)~Point[]``. A static constructor of ``Shape`` is named ``static Shape``.

Generic Types
-------------

A target names a generic type with or without its generic arguments:

.. code-block:: rst

   :cs:type:`Geometry.Layer` and :cs:type:`Geometry.Layer\<T>`

:cs:type:`Geometry.Layer` and :cs:type:`Geometry.Layer\<T>`

.. note::

   A role reads a target that ends in ``>`` as a title and a target, as in ``:cs:type:`title <target>```. Escape the ``<`` of a target that ends in ``>`` with a backslash.

You can document a type and a generic type of the same name, such as ``Box`` and ``Box<T>``. A target without generic arguments links to the type without generic parameters.

Targets
-------

Each object has a target, which is the anchor of its link. The target is the object type and the full name, with the number of generic parameters of each generic type, as in the Microsoft documentation:

.. list-table::
   :header-rows: 1

   * - Object
     - Target
   * - ``class Layer<T>``
     - ``class-Geometry.Layer-1``
   * - ``double Area ()``
     - ``function-Geometry.Shape.Area``
   * - ``Polygon (params Point[] points)``
     - ``function-Geometry.Polygon.Polygon(Point[])``

A method has a target with its parameter types for each overload. The first overload in a page also has the target without parameters.

Intersphinx
-----------

Link to the C# objects of another project with `intersphinx <https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html>`_:

.. code-block:: python

   extensions = ['sphinx_csharp', 'sphinx.ext.intersphinx']
   intersphinx_mapping = {'library': ('https://example.com/library/', None)}

A reference to an object that your pages do not describe then links to the other project, in roles and in signatures. Qualify the target with its namespace, or put the reference inside the namespace. Every role works across projects, including ``:cs:obj:``.
