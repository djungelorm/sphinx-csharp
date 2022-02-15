namespace OtherNamespace
{
    public class NullableClass
    {
        /// <summary>
        /// Constructor of the class.
        /// </summary>
        public ExampleClass()
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
        /// <param name="bValue">A nullable bool.</param>
        /// <returns>A nullable int.</returns>
        public int? FooBar(bool? bValue)
        {
            return null;
        }
    }
}