namespace OtherNamespace
{
    public struct Vector
    {
        /// <summary>
        /// Adds two vectors.
        /// </summary>
        public static Vector operator +(Vector a, Vector b) => a;

        /// <summary>
        /// Negates a vector.
        /// </summary>
        public static Vector operator -(Vector a) => a;

        /// <summary>
        /// Whether the vector is non-zero.
        /// </summary>
        public static bool operator true(Vector a) => true;

        /// <summary>
        /// Whether the vector is zero.
        /// </summary>
        public static bool operator false(Vector a) => false;

        /// <summary>
        /// Converts a vector to its length.
        /// </summary>
        public static implicit operator double(Vector a) => 0;

        /// <summary>
        /// Converts a length to a vector.
        /// </summary>
        public static explicit operator Vector(double d) => default;
    }
}
