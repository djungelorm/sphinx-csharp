using System.Collections.Generic;

namespace OtherNamespace
{
    public class Overloads
    {
        /// <summary>
        /// An overload with one parameter.
        /// </summary>
        public void Add(int value) { }

        /// <summary>
        /// An overload with a ref parameter and a generic parameter type.
        /// </summary>
        public void Add(ref int value, Dictionary<string, int> map) { }

        /// <summary>
        /// An indexer overload.
        /// </summary>
        public int this[int index] => index;

        /// <summary>
        /// Another indexer overload.
        /// </summary>
        public int this[string key] => key.Length;

        /// <summary>
        /// A conversion overload.
        /// </summary>
        public static implicit operator int(Overloads o) => 0;

        /// <summary>
        /// Another conversion overload.
        /// </summary>
        public static implicit operator string(Overloads o) => "";
    }
}
