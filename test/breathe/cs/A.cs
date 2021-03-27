using System;
using UI;
using UnityEngine;
using XrInput;
using Object = UnityEngine.Object;

namespace MyNamespace
{
    /// <summary>
    /// This is a <c>partial</c> class, meaning it is split between several files.
    /// </summary>
    /// <remarks>See also <see cref="OtherNamespace.B"/>.</remarks>
    public unsafe partial class MyClass : IDisposable
    {
        public GameObject* gameObject;

        public readonly LibiglMesh Mesh;

        /// <summary>
        /// Create a behaviour for the <see cref="MonoBehaviour"/> component.
        /// Every Mesh has one behaviour.
        /// </summary>
        public MyClass(GameObject other)
        {
            
        }

        /// <summary>
        /// Called every frame, the normal Unity Update. 
        /// </summary>
        public void Update()
        {
            
        }

        /// <summary>
        /// Called on the main thread.
        /// </summary>
        public void PreExecute()
        {
            
        }
    }
}