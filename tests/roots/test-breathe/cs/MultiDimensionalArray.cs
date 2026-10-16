namespace MyNamespace
{
    public class MultiDimensionalArray
    {
        /// <summary>
        /// A method with a jagged array parameter.
        /// </summary>
        public void JaggedArray(out byte[][] data)
        {
            data = [];
        }

        /// <summary>
        /// A method with multi-dimensional array parameter and return types.
        /// </summary>
        public int[,] MultiDimensionalArrayMethod(int[,,] data)
        {
            return new int[0, 0];
        }
    }
}
