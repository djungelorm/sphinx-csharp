using System.Collections.Generic;

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
    }
}
