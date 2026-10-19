namespace OtherNamespace
{
    /// <summary>
    /// A record with a primary constructor.
    /// </summary>
    public record Point(int X, int Y);

    /// <summary>
    /// A record struct.
    /// </summary>
    public readonly record struct Size(int Width, int Height);

    /// <summary>
    /// A generic record class.
    /// </summary>
    public sealed record class Pair<TFirst, TSecond>(TFirst First, TSecond Second);

    /// <summary>
    /// A generic class with a primary constructor.
    /// </summary>
    public class Holder<T>(T value)
    {
        public T Value { get; } = value;
    }

    /// <summary>
    /// A class with a primary constructor.
    /// </summary>
    public class Service(Bar bar)
    {
        public Bar Bar { get; } = bar;
    }
}
