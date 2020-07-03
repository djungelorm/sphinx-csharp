.. default-domain:: cs

.. namespace:: MyNamespace

.. class:: MyClass

   .. inherits:: System.Collections.Generic.IList<string>
   .. inherits:: System.IDisposable

   This is a class with methods and properties.

   Here are some references to it's methods and properties:

       * :func:`MyClass.MyMethod`
       * :func:`MyMethod`
       * :prop:`MyClass.MyProperty`
       * :prop:`MyProperty`

   .. function:: MyClass (string a, int b = 1, float c = 2.3)

      A constructor for the class.

   .. function:: void MyMethod (string arg)

      A method with a single argument.

      And a reference back to the containing class :type:`MyClass`

   .. function:: void MyMethodDefaultArg (string arg = "foo")

      A method with a default argument value.

   .. function:: void MyMethodDefaultArgs (int x, bool y = true, List<string> arg = [ "foo", "bar", "baz" ], bool z = false)

      A method with default argument values.

   .. function:: void MyMethodNoArgs ()

      A method with no arguments.

   .. function:: void MyMethodTemplatedArg (System.Collections.Generic.IDictionary<string,int> arg)

      A method with a templated argument.

   .. function:: MyClass MyMethodClass (MyClass arg)

      A method with a class as the parameter and return types.

   .. function:: MyEnum MyMethodEnum (MyEnum arg)

      A method with an enum as the parameter and return types.

   .. function:: static int MyStaticMethod (int arg)

      A static method.

   .. function:: int MyMethodHasParamModifiers(ref int arg0, params int[] arg1)

      A method with a parameter modifier.

   .. function:: public static MyMethodHasMultiModifiers()

      A method with multiple method modifiers.

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

   .. indexer:: string this[int i] { get; set; }

   .. indexer:: string this[int i] { get; }

   .. indexer:: virtual string this[int i] { get; set; }

   .. indexer:: string this[int i, MyClass j] { get; set; }

   .. function:: T AGenericMethod<T> (int x)

   .. property:: System.Tuple<int,string> ATupleProperty { get; set; }

.. enum:: MyEnum

   This is an enum.

   .. enumerator:: Foo

      An enumerator value.

   .. enumerator:: Bar
   .. enumerator:: Baz

.. class:: MyGenericClass<T>

   .. function:: void AMethod()

   .. function:: T AGenericMethod<T> (int x)

.. attribute:: MyAttribute1

   An attribute.

.. attribute:: MyAttribute2 (string param1, int param2)

   Another attribute.

Class ref :type:`MyClass`

Method ref: :func:`MyClass.MyMethod`

Property ref: :prop:`MyClass.MyProperty`

Enum ref :type:`MyEnum`

Enum value ref :enumerator:`MyEnum.Foo`

Generic class ref :type:`MyGenericClass`

Generic method ref :func:`MyClass.AGenericMethod`

Generic method in generic class ref :func:`MyGenericClass.AGenericMethod`

Attribute ref :attr:`MyAttribute1`

Attribute ref :attr:`MyAttribute2`

Indexer ref :idxr:`MyClass.this[]`
