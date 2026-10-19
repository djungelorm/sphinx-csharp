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
    # A generic type named with its arity, such as IEqualityComparer-1, takes precedence over the non-generic type.
    external_type_map = {
        'msdn': {
            'System': ['Tuple', 'ValueTuple', 'IDisposable', 'IAsyncDisposable', 'ICloneable', 'IComparable',
                       'Func', 'Action', 'Predicate', 'Comparison', 'AsyncCallback', 'IAsyncResult',
                       'Object', 'String', 'Type', 'Attribute', 'Enum', 'Delegate', 'Array', 'ArraySegment-1',
                       'Nullable', 'Lazy', 'IntPtr', 'Random', 'Guid', 'Uri', 'Version', 'TimeProvider',
                       'DateTime', 'DateTimeOffset', 'DateTimeKind', 'DayOfWeek', 'TimeSpan', 'TimeZoneInfo',
                       'Span-1', 'ReadOnlySpan-1', 'Memory-1', 'ReadOnlyMemory-1',
                       'IObservable-1', 'IObserver-1', 'EventArgs', 'EventHandler',
                       'IEquatable', 'IFormattable', 'IFormatProvider', 'StringComparison',
                       'Exception', 'ArgumentException', 'ArgumentNullException', 'ArgumentOutOfRangeException',
                       'ArrayTypeMismatchException', 'FormatException', 'IndexOutOfRangeException',
                       'InvalidCastException', 'InvalidOperationException', 'NotSupportedException',
                       'NotImplementedException', 'ObjectDisposedException', 'OverflowException',
                       'TimeZoneNotFoundException'],
            'System.TimeZoneInfo': ['AdjustmentRule', 'TransitionTime'],
            'System.Buffers': ['ArrayPool-1', 'IBufferWriter-1', 'IMemoryOwner-1', 'MemoryHandle', 'MemoryManager-1',
                               'ReadOnlySequence-1'],
            'System.Collections': ['IEnumerable', 'IEnumerator', 'ICollection', 'IList', 'IDictionary',
                                   'IEqualityComparer', 'IComparer', 'IDictionaryEnumerator', 'DictionaryEntry'],
            'System.Collections.Concurrent': ['ConcurrentDictionary-2', 'ConcurrentQueue-1'],
            'System.Collections.Generic': ['List', 'Dictionary', 'ISet',
                                           'HashSet', 'Queue', 'Stack', 'LinkedList', 'KeyValuePair',
                                           'IReadOnlyCollection', 'IReadOnlyList', 'IReadOnlyDictionary',
                                           'IEnumerable-1', 'IEnumerator-1', 'ICollection-1', 'IList-1',
                                           'IDictionary-2', 'IEqualityComparer-1', 'IComparer-1',
                                           'IAsyncEnumerable-1', 'Comparer-1', 'EqualityComparer-1',
                                           'KeyNotFoundException'],
            'System.Collections.ObjectModel': ['Collection', 'KeyedCollection', 'ReadOnlyCollection',
                                               'ReadOnlyDictionary-2'],
            'System.ComponentModel': ['INotifyPropertyChanged', 'PropertyChangedEventHandler', 'ITypeDescriptorContext',
                                      'TypeConverter'],
            'System.ComponentModel.DataAnnotations': ['ValidationContext', 'ValidationException'],
            'System.Data': ['DataTable'],
            'System.Diagnostics': ['Stopwatch', 'StackTrace'],
            'System.Diagnostics.CodeAnalysis': ['DynamicallyAccessedMemberTypes'],
            'System.Drawing': ['Rectangle'],
            'System.Globalization': ['CultureInfo', 'DateTimeStyles', 'CompareInfo', 'DateTimeFormatInfo',
                                     'CalendarWeekRule'],
            'System.IO': ['FileFormatException', 'IOException', 'EndOfStreamException', 'Stream', 'TextReader',
                          'TextWriter', 'StringWriter', 'BinaryReader', 'BinaryWriter', 'SeekOrigin'],
            'System.Linq': ['IGrouping-2', 'ILookup-2', 'IOrderedEnumerable-1'],
            'System.Linq.Expressions': ['Expression', 'LambdaExpression', 'ParameterExpression'],
            'System.Numerics': ['BigInteger'],
            'System.Reflection': ['Assembly', 'BindingFlags', 'MemberInfo', 'MemberTypes', 'MethodBase',
                                  'MethodInfo', 'ConstructorInfo', 'PropertyInfo', 'FieldInfo', 'ParameterInfo'],
            'System.Resources': ['ResourceManager'],
            'System.Runtime.ExceptionServices': ['ExceptionDispatchInfo'],
            'System.Runtime.InteropServices': ['GCHandle', 'Marshal'],
            'System.Runtime.Serialization': ['StreamingContext', 'SerializationBinder', 'SerializationInfo'],
            'System.Runtime.Serialization.Formatters': ['FormatterAssemblyStyle'],
            'System.Text': ['StringBuilder', 'Encoding'],
            'System.Text.RegularExpressions': ['Regex', 'RegexOptions'],
            'System.Threading': ['Thread', 'ThreadLocal-1', 'CancellationToken', 'CancellationTokenRegistration',
                                 'CancellationTokenSource', 'SemaphoreSlim', 'SpinLock'],
            'System.Threading.Tasks': ['Task', 'ValueTask', 'TaskCompletionSource', 'TaskScheduler'],
            'System.Xml': ['XmlDateTimeSerializationMode', 'XmlQualifiedName', 'XmlReader', 'XmlWriter'],
            'System.Xml.Schema': ['XmlSchema', 'XmlSchemaAttribute', 'XmlSchemaComplexType', 'XmlSchemaSet',
                                  'XmlSchemaSimpleType', 'XmlSchemaType'],
            'System.Xml.Serialization': ['IXmlSerializable'],
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
        'ISet': 'ISet-1',
        'Func': 'Func-1',
        'HashSet': 'HashSet-1',
        'Queue': 'Queue-1',
        'Stack': 'Stack-1',
        'LinkedList': 'LinkedList-1',
        'KeyValuePair': 'KeyValuePair-2',
        'IReadOnlyCollection': 'IReadOnlyCollection-1',
        'IReadOnlyList': 'IReadOnlyList-1',
        'IReadOnlyDictionary': 'IReadOnlyDictionary-2',
        'Lazy': 'Lazy-1',
        'IEquatable': 'IEquatable-1',
        'Predicate': 'Predicate-1',
        'Comparison': 'Comparison-1',
        'Collection': 'Collection-1',
        'KeyedCollection': 'KeyedCollection-2',
        'ReadOnlyCollection': 'ReadOnlyCollection-1',
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
