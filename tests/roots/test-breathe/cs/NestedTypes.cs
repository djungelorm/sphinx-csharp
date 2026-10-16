using System.Collections.Generic;

namespace OtherNamespace
{
    public class NestedTypes
    {
        /// <summary>
        /// A method returning a type nested in a generic type.
        /// </summary>
        public List<int>.Enumerator GetEnumerator()
        {
            return new List<int>().GetEnumerator();
        }
    }
}
