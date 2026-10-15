class ExternalRefsData:
    """ Default data for external links, which ExternalRefs.apply_config merges with the config values """

    # Types in these namespaces, or namespaces nested inside them, are shown without their namespace
    unqualified_namespaces = [
        'System',
    ]

    # Types and strings that are never linked
    ignore_xref_types = [
        '*',
        '&',
        'void',
    ]

    # C# built-in type keywords and the .NET types they alias, which link to the Microsoft docs
    builtin_types = {
        'bool': 'System.Boolean',
        'byte': 'System.Byte',
        'sbyte': 'System.SByte',
        'char': 'System.Char',
        'decimal': 'System.Decimal',
        'double': 'System.Double',
        'float': 'System.Single',
        'int': 'System.Int32',
        'uint': 'System.UInt32',
        'nint': 'System.IntPtr',
        'nuint': 'System.UIntPtr',
        'long': 'System.Int64',
        'ulong': 'System.UInt64',
        'short': 'System.Int16',
        'ushort': 'System.UInt16',
        'object': 'System.Object',
        'string': 'System.String',
    }

    # Known external types, by package and then namespace. The package is a key in external_search_pages.
    # The namespace is the one used in the link, which may differ from the real namespace.
    external_type_map = {
        'msdn': {
            'System': ['Tuple', 'IDisposable', 'ICloneable', 'IComparable', 'Func', 'Action',
                       'Type', 'Attribute', 'Enum', 'Delegate', 'Array', 'Nullable', 'Lazy',
                       'Guid', 'DateTime', 'TimeSpan', 'Uri', 'EventArgs', 'EventHandler',
                       'IEquatable', 'IFormattable',
                       'Exception', 'ArgumentException', 'ArgumentNullException', 'ArgumentOutOfRangeException',
                       'InvalidOperationException', 'NotSupportedException', 'NotImplementedException',
                       'ObjectDisposedException'],
            'System.Collections': ['IEnumerator'],
            'System.Collections.Generic': ['List', 'Dictionary', 'IList', 'IDictionary', 'ISet', 'IEnumerable',
                                           'HashSet', 'Queue', 'Stack', 'LinkedList', 'KeyValuePair',
                                           'ICollection', 'IReadOnlyCollection', 'IReadOnlyList',
                                           'IReadOnlyDictionary'],
            'System.IO': ['FileFormatException', 'IOException'],
            'System.Linq.Expressions': ['Expression', 'LambdaExpression'],
            'System.Text': ['StringBuilder'],
            'System.Threading': ['Thread'],
            'System.Threading.Tasks': ['Task'],
            'System.Runtime.InteropServices': ['GCHandle', 'Marshal'],
        },
        'unity': {
            '': ['MonoBehaviour', 'ScriptableObject',
                 'GameObject', 'Transform', 'RectTransform',
                 'Mesh', 'MeshRenderer', 'MeshFilter', 'Animator',
                 'Collider', 'SphereCollider', 'BoxCollider',
                 'Material', 'Sprite',
                 'Vector2', 'Vector3', 'Vector4', 'Quaternion', 'Color', 'Gradient',
                 'Coroutine', 'Space', 'LayerMask', 'Layer',
                 'AssetPostprocessor',
                 ],
        },
    }

    # Names to use in links in place of type names, such as for generic types.
    # The rename applies after the lookup in external_type_map.
    external_type_rename = {
        'List': 'List-1',
        'Dictionary': 'Dictionary-2',
        'IList': 'IList-1',
        'IDictionary': 'IDictionary-2',
        'ISet': 'ISet-1',
        'IEnumerable': 'IEnumerable-1',
        'Func': 'Func-1',
        'HashSet': 'HashSet-1',
        'Queue': 'Queue-1',
        'Stack': 'Stack-1',
        'LinkedList': 'LinkedList-1',
        'KeyValuePair': 'KeyValuePair-2',
        'ICollection': 'ICollection-1',
        'IReadOnlyCollection': 'IReadOnlyCollection-1',
        'IReadOnlyList': 'IReadOnlyList-1',
        'IReadOnlyDictionary': 'IReadOnlyDictionary-2',
        'Lazy': 'Lazy-1',
        'IEquatable': 'IEquatable-1',
    }

    # Documentation URLs for each package, as (API page, fallback search page).
    # Each URL contains %s, which is replaced with the type name.
    external_search_pages = {
        'msdn': ('https://learn.microsoft.com/en-us/dotnet/api/%s',
                 'https://learn.microsoft.com/en-us/search/?scope=.NET&terms=%s'),
        'unity': ('https://docs.unity3d.com/ScriptReference/%s.html',
                  'https://docs.unity3d.com/ScriptReference/30_search.html?q=%s'),
        'unityman': ('https://docs.unity3d.com/Manual/%s.html',
                     'https://docs.unity3d.com/Manual/30_search.html?q=%s'),
    }
