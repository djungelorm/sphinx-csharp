sphinx-csharp
=============

sphinx-csharp is a Sphinx extension that adds a ``cs`` domain for documenting C# APIs. You describe an API in reStructuredText:

.. code-block:: rst

   .. cs:namespace:: Geometry

   .. cs:class:: public class Circle : Shape

      A circle with a center and a radius.

      .. cs:function:: public double Area ()

         The area of the circle.

Sphinx renders it with a link for each type:

.. cs:namespace:: Geometry

.. cs:class:: public class Circle : Shape
   :no-index:

   A circle with a center and a radius.

   .. cs:function:: public double Area ()
      :no-index:

      The area of the circle.

You can also generate the pages from C# sources, with `Doxygen <https://www.doxygen.nl>`_ and `Breathe <https://github.com/breathe-doc/breathe>`_.

Installation
------------

Install the package from PyPI:

.. code-block:: console

   $ pip install sphinx-csharp

Then add the extension to the ``conf.py`` of your project:

.. code-block:: python

   extensions = ['sphinx_csharp']

sphinx-csharp needs Python 3.11 or later, and Sphinx 7.2 or later.

.. toctree::
   :maxdepth: 2

   guide
   changelog
