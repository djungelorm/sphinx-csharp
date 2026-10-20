Migration from 0.1
==================

Version 1.0 renames the domain, some directives and roles, and the targets of objects.

Domain
------

The domain is ``cs``, in place of ``csharp``:

.. code-block:: rst

   .. default-domain:: cs

   .. cs:class:: MyClass

   See :cs:type:`MyClass`.

Directives and Roles
--------------------

.. list-table::
   :header-rows: 1

   * - 0.1
     - 1.0
   * - ``.. csharp:method::``
     - ``.. cs:function::``
   * - ``.. csharp:value::``
     - ``.. cs:enumerator::``
   * - ``:csharp:enum:``, for an enum value
     - ``:cs:enumerator:`` or ``:cs:value:``
   * - ``:csharp:meth:``, ``:csharp:type:`` and the other roles
     - ``:cs:meth:``, ``:cs:type:`` and the other roles

.. note::

   ``:cs:enum:`` links to an enum type. In 0.1, ``:csharp:enum:`` linked to an enum value.

Targets
-------

The target of an object starts with its object type, as in 0.1. Some object types and names change:

.. list-table::
   :header-rows: 1

   * - 0.1
     - 1.0
   * - ``method-MyClass.Add``
     - ``function-MyClass.Add``, and ``function-MyClass.Add(int)`` for the overload
   * - ``value-Color.Red``
     - ``enumerator-Color.Red``
   * - ``class-Box``, for ``Box<T>``
     - ``class-Box-1``

A link to an anchor in pages built with 0.1 needs the new target.

.. seealso::

   :doc:`references` describes the targets.

Option Names
------------

Forks of sphinx-csharp before 1.0 named some options of ``conf.py`` differently. The old names still work, with a ``cs.config`` warning:

.. list-table::
   :header-rows: 1

   * - Old name
     - Name in 1.0
   * - ``sphinx_csharp_test_links``
     - ``sphinx_csharp_check_external_links``
   * - ``sphinx_csharp_ignore_xref``
     - ``sphinx_csharp_ignore_types``
   * - ``sphinx_csharp_ext_type_map``
     - ``sphinx_csharp_external_type_map``
   * - ``sphinx_csharp_ext_search_pages``
     - ``sphinx_csharp_external_search_pages``
   * - ``sphinx_csharp_debug_parse`` and ``sphinx_csharp_debug_parse_*``
     - ``sphinx_csharp_debug = ['parse']``
   * - ``sphinx_csharp_debug_xref``
     - ``sphinx_csharp_debug = ['xref']``
   * - ``sphinx_csharp_debug_ext_links``
     - ``sphinx_csharp_debug = ['external']``
