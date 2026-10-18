using System.Collections.Generic;

namespace OtherNamespace
{
    public class Indexer
    {
        /// <summary>
        /// An indexer with a generic parameter type and a default value.
        /// </summary>
        public string this[Dictionary<string, int> map, int offset = 0]
        {
            get => "";
            private set { }
        }
    }
}
