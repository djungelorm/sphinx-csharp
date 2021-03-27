using System;
using UnityEngine;

namespace OtherNamespace
{
    /// <summary>
    /// Some text here
    /// </summary>
    /// <remarks>See also <see cref="MyNamespace.MyClass"/>.</remarks>
    public unsafe partial class B : MonoBehaviour
    {
        public GameObject* gameObject;

        public readonly LibiglMesh Mesh;

        /// <summary>
        /// Create a behaviour for the <see cref="MonoBehaviour"/> component.
        /// Every Mesh has one behaviour.
        /// </summary>
        public B(GameObject other)
        {
            
        }

        /// <summary>
        /// Called every frame, the normal Unity Update. 
        /// </summary>
        public Tuple<MyClass, MyClass> Update(ref B b, int a = 0)
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