Directives
==========

Each directive describes one kind of C# declaration. Write the signature as it appears in C# source, with any attributes and modifiers:

.. code-block:: rst

   .. cs:function:: [Obsolete] public static Point Parse (string text)

The examples on this page describe a small ``Geometry`` library. Each example shows the reStructuredText, then the result.

.. tip::

   Put ``.. default-domain:: cs`` at the top of a page to write ``.. class::`` in place of ``.. cs:class::``.

Namespaces
----------

The ``namespace`` directive sets the namespace of the declarations that follow it:

.. code-block:: rst

   .. cs:namespace:: Geometry

.. cs:namespace:: Geometry

The namespace stays set until the end of the page, or the next ``namespace`` directive. Clear it with ``.. cs:namespace:: None``.

``namespace-push`` nests a namespace in the current one, and ``namespace-pop`` returns to the namespace from before it:

.. code-block:: rst

   .. cs:namespace-push:: Drawing

   .. cs:class:: Canvas

   .. cs:namespace-pop::

.. cs:namespace-push:: Drawing

.. cs:class:: Canvas

.. cs:namespace-pop::

The full name of Canvas is ``Geometry.Drawing.Canvas``. Each namespace is a target for the ``:cs:namespace:`` role, unless the directive has the ``:no-index:`` option.

Types
-----

The ``class``, ``struct``, ``interface`` and ``record`` directives describe types. Nest the members of a type in its directive:

.. code-block:: rst

   .. cs:class:: public abstract class Shape : IComparable<Shape>

      The base class of every shape.

      .. cs:function:: public abstract double Area ()

.. cs:class:: public abstract class Shape : IComparable<Shape>

   The base class of every shape.

   .. cs:function:: public abstract double Area ()

A generic type has generic parameters and constraints, and a type can have a primary constructor:

.. code-block:: rst

   .. cs:class:: public class Layer<T>(string name) where T : Shape

   .. cs:struct:: public readonly struct Point (double X, double Y)

   .. cs:interface:: public interface IScalable

   .. cs:record:: public record Size (double Width, double Height)

   .. cs:record:: public record struct Bounds (Point Min, Point Max)

.. cs:class:: public class Layer<T>(string name) where T : Shape

.. cs:struct:: public readonly struct Point (double X, double Y)

.. cs:interface:: public interface IScalable

.. cs:record:: public record Size (double Width, double Height)

.. cs:record:: public record struct Bounds (Point Min, Point Max)

``.. cs:record::`` takes a ``class`` or ``struct`` keyword, as in ``record struct``. The ``inherits`` directive adds a base type to the type it is nested in:

.. code-block:: rst

   .. cs:class:: public class Circle

      .. cs:inherits:: Shape

.. cs:class:: public class Circle

   .. cs:inherits:: Shape

Enums
-----

The ``enum`` directive describes an enum, and ``enumerator`` describes each of its values:

.. code-block:: rst

   .. cs:enum:: public Color : byte

      .. cs:enumerator:: Red = 1

      .. cs:enumerator:: Green = 2

.. cs:enum:: public Color : byte

   .. cs:enumerator:: Red = 1

   .. cs:enumerator:: Green = 2

Methods
-------

The ``function`` directive describes methods, constructors, finalizers and operators:

.. code-block:: rst

   .. cs:class:: public class Polygon : Shape

      .. cs:function:: public Polygon (params Point[] points)

      .. cs:function:: public Polygon (IEnumerable<Point> points) : this(points.ToArray())

      .. cs:function:: public override double Area ()

      .. cs:function:: public bool TryGetPoint (int index, [NotNullWhen(true)] out Point? point)

      .. cs:function:: public T Find<T> (Func<Point, T> map) where T : notnull

      .. cs:function:: public static Polygon operator + (Polygon a, Point offset)

      .. cs:function:: public static explicit operator Point[] (Polygon polygon)

.. cs:class:: public class Polygon : Shape

   .. cs:function:: public Polygon (params Point[] points)

   .. cs:function:: public Polygon (IEnumerable<Point> points) : this(points.ToArray())

   .. cs:function:: public override double Area ()

   .. cs:function:: public bool TryGetPoint (int index, [NotNullWhen(true)] out Point? point)

   .. cs:function:: public T Find<T> (Func<Point, T> map) where T : notnull

   .. cs:function:: public static Polygon operator + (Polygon a, Point offset)

   .. cs:function:: public static explicit operator Point[] (Polygon polygon)

Write several overloads in one directive, one signature on each line:

.. code-block:: rst

   .. cs:function:: public void Scale (double factor)
                    public void Scale (double x, double y)

The ``delegate`` directive describes a delegate:

.. code-block:: rst

   .. cs:delegate:: public delegate void ShapeChanged (Shape shape)

.. cs:delegate:: public delegate void ShapeChanged (Shape shape)

Fields, Properties and Events
-----------------------------

The ``var``, ``property`` and ``event`` directives describe fields, properties and events:

.. code-block:: rst

   .. cs:class:: public class Grid

      .. cs:var:: public const int MaxSize = 1024

      .. cs:var:: private readonly int rows, columns

      .. cs:property:: public int Count { get; private set; }

      .. cs:property:: public double Spacing { get => field; set => field = Math.Max(value, 0); }

      .. cs:event:: public event EventHandler? Changed

.. cs:class:: public class Grid

   .. cs:var:: public const int MaxSize = 1024

   .. cs:var:: private readonly int rows, columns

   .. cs:property:: public int Count { get; private set; }

   .. cs:property:: public double Spacing { get => field; set => field = Math.Max(value, 0); }

   .. cs:event:: public event EventHandler? Changed

A field that declares several variables, as in ``int rows, columns``, describes each variable. Accessors show their access level, and leave out their bodies.

Indexers
--------

The ``indexer`` directive describes an indexer:

.. code-block:: rst

   .. cs:class:: public class Path

      .. cs:indexer:: public Point this[int index] { get; set; }

.. cs:class:: public class Path

   .. cs:indexer:: public Point this[int index] { get; set; }

Attributes
----------

The ``attribute`` directive describes an attribute class, with its constructor parameters:

.. code-block:: rst

   .. cs:attribute:: UnitsAttribute (string name)

.. cs:attribute:: UnitsAttribute (string name)

Extension Blocks
----------------

The ``extension`` directive describes a C# 14 extension block. Its members belong to the enclosing static class:

.. code-block:: rst

   .. cs:class:: public static class ShapeExtensions

      .. cs:extension:: (Shape shape)

         .. cs:property:: public bool IsEmpty { get; }

.. cs:class:: public static class ShapeExtensions

   .. cs:extension:: (Shape shape)

      .. cs:property:: public bool IsEmpty { get; }

The full name of IsEmpty is ``Geometry.ShapeExtensions.IsEmpty``. The generic parameters of a block, as in ``<T>(IEnumerable<T> source)``, are not linked in its members.

Doc Fields
----------

Describe parameters, type parameters, return values and exceptions with field lists:

.. code-block:: rst

   .. cs:function:: public static T Largest<T> (IReadOnlyList<T> shapes, int start = 0) where T : Shape

      :param shapes: The shapes to search.
      :param int start: The index to start at.
      :typeparam T: The type of shape.
      :returns: The shape with the largest area.
      :rtype: T
      :throws ArgumentOutOfRangeException: If start is past the end of the list.

.. cs:function:: public static T Largest<T> (IReadOnlyList<T> shapes, int start = 0) where T : Shape

   :param shapes: The shapes to search.
   :param int start: The index to start at.
   :typeparam T: The type of shape.
   :returns: The shape with the largest area.
   :rtype: T
   :throws ArgumentOutOfRangeException: If start is past the end of the list.

The types in the ``type``, ``rtype`` and ``throws`` fields link like the types in a signature.

Options
-------

Describe an object with options after its signature:

.. code-block:: rst

   .. cs:function:: void Draw (Canvas canvas, Color color, int x, int y, int width, int height)
      :single-line-parameter-list:
      :no-index-entry:

Every directive that describes an object takes these options:

``:no-index:``
   Leave the object out of the index and the domain, so references do not link to it.

``:no-index-entry:``
   Leave the object out of the general index only.

``:no-contents-entry:``
   Leave the object out of the table of contents.

``:single-line-parameter-list:``
   Keep the parameters on one line, however long the signature.

``namespace`` and ``namespace-push`` take only ``:no-index:``, and ``namespace-pop`` takes no options.

A signature longer than the ``maximum_signature_line_length`` option of Sphinx puts each parameter on a line of its own.

Each object in a section gets an entry in the table of contents, with members nested in their types. The ``toc_object_entries_show_parents`` option of Sphinx sets how much of each name the entry shows.
