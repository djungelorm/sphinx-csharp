using System;

namespace OtherNamespace
{
    public interface IShape
    {
        /// <summary>
        /// The number of sides.
        /// </summary>
        int Sides { get; }

        /// <summary>
        /// A vertex of the shape.
        /// </summary>
        int this[int i] { get; }
    }

    public class ExplicitInterfaces : IDisposable, IShape
    {
        /// <summary>
        /// An explicit interface method.
        /// </summary>
        void IDisposable.Dispose() { }

        /// <summary>
        /// An explicit interface property.
        /// </summary>
        int IShape.Sides => 3;

        /// <summary>
        /// An explicit interface indexer.
        /// </summary>
        int IShape.this[int i] => i;
    }
}
