using MyNamespace;

namespace OtherNamespace
{
    public class NullableClass
    {
        /// <summary>
        /// Constructor of the class.
        /// </summary>
        public NullableClass()
        {
        }

        /// <summary>
        /// A nullable bool value.
        /// </summary>
        public bool? BNullableBool { get; set; }

        /// <summary>
        /// A nullable type value.
        /// </summary>
        public Bar? NNullableInt { get; set; }

        /// <summary>
        /// A nullable function.
        /// </summary>
        /// <param name="bValue">A nullable MyClass.</param>
        /// <returns>A nullable int.</returns>
        public int? FooBar(MyClass? bValue)
        {
            return null;
        }

        /// <summary>
        /// A method with nullable array elements.
        /// </summary>
        public string?[] NullableElements(int?[] values)
        {
            return [];
        }

        /// <summary>
        /// A nullable readonly field.
        /// </summary>
        public readonly object? ReadonlyField;

        /// <summary>
        /// A nullable static property.
        /// </summary>
        public static int? StaticProperty { get; set; }

        /// <summary>
        /// A nullable static method.
        /// </summary>
        public static int? StaticMethod()
        {
            return null;
        }

        /// <summary>
        /// A nullable virtual method.
        /// </summary>
        public virtual string? VirtualMethod()
        {
            return null;
        }

        /// <summary>
        /// A nullable virtual indexer.
        /// </summary>
        public virtual string? this[int index] => null;
    }

    public class DerivedNullableClass : NullableClass
    {
        /// <summary>
        /// A nullable override.
        /// </summary>
        public override string? VirtualMethod()
        {
            return null;
        }
    }
}