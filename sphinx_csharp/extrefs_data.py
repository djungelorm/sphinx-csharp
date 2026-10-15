class ExternalRefsData:
    """ This class just holds data used for external linking. Keeps data separate from functionality """

    """ Types in these namespaces, or namespaces nested inside them, are shown without their namespace """
    unqualified_namespaces = [
        'System',
    ]

    """ Types and strings to ignore when looking for a reference """
    ignore_xref_types = [
        '*',
        '&',
        'void',
    ]

    """ C# built-in type keywords and the .NET types they alias, which are linked to the Microsoft docs """
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

    """
    Contains recognised types and their namespaces as well as the package name.
    The package name references the key in external_search_pages

    Format the content like this:
    Where Namespace1 is the namespace for the link (which may not match the real namespace)::

        'package': {
            'Namespace1': ['member1', ...],
            ...
        },
        ...
    """
    external_type_map = {
        'msdn': {
            'System': ['Tuple', 'IDisposable', 'ICloneable', 'IComparable', 'Func', 'Action'],
            'System.Collections': ['IEnumerator'],
            'System.Collections.Generic': ['List', 'Dictionary', 'IList', 'IDictionary', 'ISet', 'IEnumerable'],
            'System.IO': ['FileFormatException'],
            'System.Threading': ['Thread'],
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

    """
    Put special cases in here that should be renamed when used in links, use it for generics
    The name is swapped *after* searching EXTERNAL_TYPE_MAP, just before constructing the url link
    """
    external_type_rename = {
        'List': 'List-1',
        'Dictionary': 'Dictionary-2',
        'IList': 'IList-1',
        'IDictionary': 'IDictionary-2',
        'ISet': 'ISet-2',
        'IEnumerable': 'IEnumerable-1',
        'Func': 'Func-1',
    }

    """
    Where do we search for api documentation
    Syntax:
    'package': ('api link', 'fallback search link')
    Use %s for where to substitute item, every link *must* contain this
    """
    external_search_pages = {
        'msdn': ('https://learn.microsoft.com/en-us/dotnet/api/%s',
                 'https://learn.microsoft.com/en-us/search/?scope=.NET&terms=%s'),
        'unity': ('https://docs.unity3d.com/ScriptReference/%s.html',
                  'https://docs.unity3d.com/ScriptReference/30_search.html?q=%s'),
        'unityman': ('https://docs.unity3d.com/Manual/%s.html',
                     'https://docs.unity3d.com/Manual/30_search.html?q=%s'),
    }
