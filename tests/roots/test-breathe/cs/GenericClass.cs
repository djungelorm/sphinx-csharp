using System.Collections.Generic;
using System.Diagnostics.CodeAnalysis;

namespace OtherNamespace
{
    /// <summary>
    /// A generic class whose members use its type parameter.
    /// </summary>
    public class Box<T>
    {
        /// <summary>
        /// The boxed values.
        /// </summary>
        public List<T> Values { get; } = [];

        /// <summary>
        /// Returns the first value.
        /// </summary>
        public T First(IEnumerable<T> fallback)
        {
            return Values[0];
        }

        /// <summary>
        /// Creates a value of a type with an attribute on its generic parameter.
        /// </summary>
        public static U Create<[DynamicallyAccessedMembers(DynamicallyAccessedMemberTypes.PublicParameterlessConstructor)] U>()
            where U : new()
        {
            return new U();
        }
    }
}
