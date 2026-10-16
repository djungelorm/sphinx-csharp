namespace OtherNamespace
{
    /// <summary>
    /// A delegate.
    /// </summary>
    public delegate void Handler(object sender, Bar bar);

    /// <summary>
    /// A generic delegate with variant type parameters.
    /// </summary>
    public delegate TResult Factory<in T, out TResult>(T arg);
}
