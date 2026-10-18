using System;

namespace OtherNamespace
{
    public class Accessors
    {
        /// <summary>
        /// A property set only during initialization.
        /// </summary>
        public int InitProperty { get; init; }

        /// <summary>
        /// A property with a private setter.
        /// </summary>
        public int PrivateSetProperty { get; private set; }

        /// <summary>
        /// An expression-bodied property.
        /// </summary>
        public int ExpressionProperty => 1;

        /// <summary>
        /// An event with explicit accessors.
        /// </summary>
        public event EventHandler Changed { add { } remove { } }
    }
}
