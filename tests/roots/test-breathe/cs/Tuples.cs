using System.Collections.Generic;
using System.Threading.Tasks;

namespace OtherNamespace
{
    public class Tuples
    {
        /// <summary>
        /// A method with tuple parameters, and a tuple in its generic return type.
        /// </summary>
        public Task<(int, string)> Combine((int count, string name) pair, List<(int, Bar)> items)
        {
            return Task.FromResult(pair);
        }
    }
}
