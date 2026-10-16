// Stand-ins for the Unity types used by the sources in cs, so they compile without Unity
namespace UnityEngine
{
    public class Object {}

    public class MonoBehaviour : Object {}

    // Note: Unity declares this as a class, a struct allows the pointer fields
    public struct GameObject {}
}

namespace UI {}

namespace XrInput {}
