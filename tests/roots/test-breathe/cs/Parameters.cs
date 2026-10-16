using System.Diagnostics.CodeAnalysis;
using System.Runtime.CompilerServices;

namespace OtherNamespace
{
    public ref struct Parameters
    {
        /// <summary>
        /// A method with parameter attributes.
        /// </summary>
        public bool TryGet([NotNullWhen(true)] out string? value, [CallerMemberName] string caller = "")
        {
            value = caller;
            return true;
        }

        /// <summary>
        /// A method with scoped and ref readonly parameters.
        /// </summary>
        public int Read(scoped ref int a, ref readonly int b)
        {
            return a + b;
        }
    }
}
