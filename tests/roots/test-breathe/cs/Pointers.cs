namespace OtherNamespace
{
    public unsafe struct Pointers
    {
        /// <summary>
        /// A fixed size buffer.
        /// </summary>
        public fixed byte Data[16];

        /// <summary>
        /// A function pointer.
        /// </summary>
        public delegate*<int, int, int> Add;

        /// <summary>
        /// An unmanaged function pointer with a calling convention.
        /// </summary>
        public delegate* unmanaged[Cdecl]<int, void> Callback;

        /// <summary>
        /// A method with pointer parameter and return types.
        /// </summary>
        public int* Offset(int** table, int* start) => start;

        /// <summary>
        /// A method with a function pointer parameter.
        /// </summary>
        public static int Apply(delegate*<int, int> f, int x) => f(x);
    }
}
