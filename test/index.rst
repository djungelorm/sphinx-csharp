.. default-domain:: csharp

.. class:: MyClass

   This is a class with methods and properties.

   Here are some references to it's methods and properties:

       * :meth:`MyClass.MyMethod`
       * :meth:`MyMethod`
       * :prop:`MyClass.MyProperty`
       * :prop:`MyProperty`

   .. method:: MyClass (string a, int b = 1, float c = 2.3)

      A constructor for the class.

   .. method:: void MyMethod (string arg)

      A method with a single argument.

      And a reference back to the containing class :type:`MyClass`

   .. method:: void MyMethodDefaultArg (string arg = "foo")

      A method with a default argument value.

   .. method:: void MyMethodNoArgs ()

      A method with no arguments.

   .. method:: void MyMethodTemplatedArg (System.Collections.Generic.IDictionary<string,int> arg)

      A method with a templated argument.

   .. method:: MyClass MyMethodClass (MyClass arg)

      A method with a class as the parameter and return types.

   .. method:: MyEnum MyMethodEnum (MyEnum arg)

      A method with an enum as the parameter and return types.

   .. method:: static int MyStaticMethod (int arg)

      A static method.

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

   .. property:: System.Collections.Generic.IList<string> ListProperty { get; set; }

   .. property:: System.Collections.Generic.IList<System.Collections.Generic.IList<string>> ListProperty { get; set; }

   .. property:: System.Collections.Generic.IList<System.Collections.Generic.IDictionary<string,System.Collections.Generic.IList<string>>> ListProperty { get; set; }

   .. property:: byte ByteProperty { get; set; }

   .. property:: byte[] ByteArrayProperty { get; set; }

.. enum:: MyEnum

   This is an enum.

   .. value:: Foo

      An enumerator value.

   .. value:: Bar
   .. value:: Baz


Class ref :type:`MyClass`

Method ref: :meth:`MyClass.MyMethod`

Property ref: :prop:`MyClass.MyProperty`

Property2 ref: :prop:`MyClass.MyProperty2`

Enum ref :type:`MyEnum`

Enum value ref :enum:`MyEnum.Foo`
