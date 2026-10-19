.. default-domain:: cs

.. namespace:: MyNamespace

.. class:: MyClass

   .. inherits:: System.Collections.Generic.IList<string>
   .. inherits:: System.IDisposable
   .. inherits:: System.IO.FileFormatException

   This is a class with methods and properties.

   Here are some references to it's methods and properties:

       * :func:`MyClass.MyMethod`
       * :func:`MyMethod`
       * :prop:`MyClass.MyProperty`
       * :prop:`MyProperty`

   .. function:: MyClass (string a, int b = 1, float c = 2.3)

      A constructor for the class.

   .. function:: MyClass (string a) : this(a, 2)

      A constructor that calls another constructor.

   .. function:: void MyMethod (string arg)

      A method with a single argument.

      And a reference back to the containing class :type:`MyClass`

   .. function:: void MyMethod (string arg, ref int count)

      An overload of :func:`MyMethod`, with its own target :func:`MyMethod(string, ref int)`.

   .. function:: T MyMethodWithFields<T> (System.Collections.Generic.IList<T> items, int index)

      A method with documented parameters.

      :param items: The items.
      :type items: System.Collections.Generic.IList<T>
      :param int index: The index of the item.
      :typeparam T: The item type.
      :returns: The item at the index.
      :rtype: T
      :throws System.ArgumentOutOfRangeException: If the index is out of range.

   .. function:: void MyMethodDefaultArg (string arg = "foo")

   .. function:: void MyMethodDefaultArgWithComma (string arg = "foo, bar", char sep = ',')

      A method with a default argument value.

   .. function:: void MyMethodDefaultArgs (int x, bool y = true, List<string> arg = [ "foo", "bar", "baz" ], bool z = false)

      A method with default argument values.

   .. function:: void MyMethodExpressionDefaults (int flags = 1 << 2, bool less = 1 < 2, string path = @"C:\", [MyAttribute3(Values[0])] int x)

      A method with expressions in its default values and attributes.

   .. function:: void MyMethodNoArgs ()
      :no-index-entry:

      A method with no arguments, left out of the general index.

   .. function:: void MyMethodTemplatedArg (System.Collections.Generic.IDictionary<string,int> arg)

      A method with a templated argument.

   .. function:: void MyMethodTwoDArrayArg (int[][] arg)

      A method with two-dimensional array argument.

   .. function:: int[][] MyMethod2DArrayReturn ()

      A method returning a two-dimensional array

   .. function:: int[,] MyMethodMultiDimArray (int[,,] arg)

      A method with multi-dimensional array parameter and return types.

   .. function:: int? MyMethodNullable (MyClass? arg)

   .. function:: MyClass?[] MyMethodNullableElements (int** ptr, string?[]? arg)

      A method with nullable parameter and return types.

   .. function:: unsafe int *MyMethodPointers (int **table, int *start)

      A method with pointer types written next to the names.

   .. function:: MyClass MyMethodClass (MyClass arg)

      A method with a class as the parameter and return types.

   .. function:: MyEnum MyMethodEnum (MyEnum arg)

      A method with an enum as the parameter and return types.

   .. function:: [System.Obsolete("Use MyMethod")] void MyObsoleteMethod ()

      A method with an attribute.

   .. function:: int MyExpressionMethod (int arg) => arg * 2;

      A method with an expression body, which is not shown.

   .. function:: static extern int MyExternMethod (int arg);

      A method copied from source, with a trailing semicolon.

   .. function:: static int MyStaticMethod (int arg)

      A static method.

   .. function:: int MyMethodHasParamModifiers(ref int arg0, params int[] arg1)

   .. function:: bool MyMethodHasParamAttributes([NotNullWhen(true)] out string? arg0, scoped ref readonly int arg1)

      A method with a parameter modifier.

   .. function:: public static MyMethodHasMultiModifiers()

      A method with multiple method modifiers.

   .. function:: void System.IDisposable.Dispose ()

      An explicit interface implementation.

   .. function:: System.Collections.Generic.IEnumerator<string> System.Collections.Generic.IEnumerable<string>.GetEnumerator ()

   .. property:: string MyProperty { get; set; }

      A read/write property.

   .. property:: string MyReadOnlyProperty { get; }

      A read only property.

   .. property:: string MyWriteOnlyProperty { set; }

      A write only property.

   .. property:: static string MyStaticProperty { get; set; }

      A static property.

   .. property:: MyClass MyClassProperty { get; set; }

      A read/write property with a class type.

   .. property:: MyEnum MyEnumProperty { get; set; }

      A read/write property with an enum type.

   .. property:: System.Collections.Generic.List<string> ListProperty { get; set; }

   .. property:: System.Collections.Generic.IList<string> IListProperty { get; set; }

   .. property:: System.Collections.Generic.List<System.Collections.Generic.List<string>> ListProperty { get; set; }

   .. property:: System.Collections.Generic.IList<System.Collections.Generic.IList<string>> IListProperty { get; set; }

   .. property:: System.Collections.Generic.IList<System.Collections.Generic.Dictionary<string,System.Collections.Generic.List<string>>> ListProperty { get; set; }

   .. property:: System.Collections.Generic.IList<System.Collections.Generic.IDictionary<string,System.Collections.Generic.IList<string>>> IListProperty { get; set; }

   .. property:: byte ByteProperty { get; set; }

   .. property:: byte[] ByteArrayProperty { get; set; }

   .. property:: bool? NullableProperty { get; set; }

   .. property:: MyEnum? NullableEnumProperty { get; set; }

   .. property:: string InitProperty { get; init; }

   .. property:: string PrivateSetProperty { get; private set; }

   .. property:: int ExpressionProperty => 1

   .. indexer:: string this[int i] { get; set; }

   .. indexer:: string this[int i] { get; }

   .. indexer:: virtual string this[int i] { get; set; }

   .. indexer:: string this[int i, MyClass j] { get; set; }

   .. indexer:: string this[int i, MyClass j, int k] { get; protected set; }

   .. indexer:: string this[System.Collections.Generic.IDictionary<string, int> map, int offset = 0] { get; }

   .. event:: public System.EventHandler Changed

   .. event:: public System.EventHandler Closed { add; remove; }

   .. function:: T AGenericMethod<T> (int x)

   .. function:: T? AGenericNullableMethod<T> (T[] items)

   .. property:: System.Tuple<int,string> ATupleProperty { get; set; }

   .. property:: (int count, MyClass item) AValueTupleProperty { get; }

   .. function:: ((int, (int, MyClass)), int) ANestedTupleMethod ()

   .. function:: (int, string)[] ATupleMethod ((MyClass a, (int b, int c) d) arg, System.Collections.Generic.List<(int, MyEnum)> items)

.. enum:: MyEnum

   This is an enum.

   .. enumerator:: Foo

      An enumerator value.

   .. enumerator:: Bar
   .. enumerator:: Baz

.. enum:: [System.Flags] public MyFlags : byte

   .. enumerator:: None = 0

   .. enumerator:: First = 1

   .. enumerator:: All = First | 2

.. class:: MyGenericClass<T> where T : MyClass, new()

   .. function:: void AMethod()

   .. function:: T AGenericMethod<T> (int x)

   .. class:: Nested

   .. function:: MyGenericClass<int>.Nested GetNested ()

   .. function:: System.Collections.Generic.List<int>.Enumerator GetEnumerator ()

   .. function:: T GetFirst (System.Collections.Generic.IEnumerable<T> items)

   .. function:: U AConstrainedMethod<U> (U x) where U : System.IComparable<U>

.. attribute:: MyAttribute1

   An attribute.

.. attribute:: MyAttribute2 (string param1, int param2)

.. attribute:: MyAttribute3(string param1, bool param2 = false)

   Another attribute.

.. attribute:: MyGenericAttribute<T> (T value)

   A generic attribute.

.. enumerator:: MyFlags.Second = 2

.. _references:

References
----------

Type ref :type:`MyClass`

Class ref :class:`MyClass`

Class ref :class:`MyClass2`

Struct ref :struct:`MyStruct`

Interface ref :interface:`MyInterface`

Method ref: :func:`MyClass.MyMethod`

Overload ref: :func:`MyClass.MyMethod(string,ref int)`

Property ref: :prop:`MyClass.MyProperty`

Enum ref :type:`MyEnum`

Enum value ref :enumerator:`MyEnum.Foo`

Generic class ref :type:`MyGenericClass`

Generic class ref with arguments :type:`MyGenericClass\<T>`

Generic method ref with arguments :func:`MyGenericClass\<int>.AGenericMethod\<T>`

Generic method ref :func:`MyClass.AGenericMethod`

Generic method in generic class ref :func:`MyGenericClass.AGenericMethod`

Attribute ref :attr:`MyAttribute1`

Attribute ref :attr:`MyAttribute2`

Generic attribute ref :attr:`MyGenericAttribute`

Indexer ref :idxr:`MyClass.this[]`

Any object ref :obj:`MyClass.MyMethod`

Section ref :ref:`references`


More Tests
----------

.. record:: MyPoint(int X, int Y)

.. record:: readonly struct MySize(int Width, int Height)

.. class:: MyService(MyClass client, int timeout = 30) : MyClass(client)

.. delegate:: public void MyHandler(object sender, MyClass item)

.. delegate:: TResult MyFactory<in T, out TResult>(T arg)

.. struct:: MyVector

   .. function:: public static MyVector operator +(MyVector a, MyVector b)

   .. function:: public static bool operator ==(MyVector a, MyVector b)

   .. function:: public static explicit operator MyVector(double d)

.. namespace:: OtherNamespace

.. struct:: public MyStruct < T, U > : IList
.. interface:: public MyInterface < T, U > : IList

.. namespace:: OtherNamespace.Subspace


.. class:: public unsafe MyClass2 < T , U > : Dictionary, MyInterface

   .. function:: public MyStruct MyFunc ( ref int a = 3, float b, ref GameObject c, ref List < GameObject > d = default)

   .. var:: private int a = 0

   .. var:: private MyEnum a = MyEnum.Bar

   .. var:: private static const List < MyInterface > GenericVar

   .. var:: private static const List < MyInterface > TwoGenericBrackets = new List < MyInterface > ()

   .. function:: private List < MyInterface<int, float> > GenericsGaloreFunc <T, U> (ref List <T> a = default,  List < MyInterface<int, float> > b = default)

   .. function:: private T ReturnGeneric < T, U > (int a = 0)

.. namespace:: OtherNamespace.Expressions

.. class:: Expression

.. namespace:: OtherNamespace.Subspace

.. function:: void CompileExpression (Expression<Func<int>> e)
