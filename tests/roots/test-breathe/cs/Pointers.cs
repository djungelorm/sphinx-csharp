namespace OtherNamespace
{
    public unsafe struct Pointers
    {
        /// <summary>
        /// A method with pointer parameter and return types.
        /// </summary>
        public int* Offset(int** table, int* start) => start;
    }
}
