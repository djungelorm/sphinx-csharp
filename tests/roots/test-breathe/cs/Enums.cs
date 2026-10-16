namespace OtherNamespace
{
    /// <summary>
    /// An enum with an underlying type and values.
    /// </summary>
    public enum Color : byte
    {
        /// <summary>Red.</summary>
        Red = 1,

        /// <summary>Green.</summary>
        Green = 2,

        /// <summary>Red and green.</summary>
        Yellow = Red | Green,
    }
}
