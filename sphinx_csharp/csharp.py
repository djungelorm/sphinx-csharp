import re
from collections import namedtuple

from docutils import nodes
from sphinx import addnodes
from sphinx.domains import Domain, ObjType
from sphinx.locale import l_, _
from sphinx.directives import ObjectDescription
from sphinx.roles import XRefRole
from sphinx.util.nodes import make_refnode
from sphinx.util.compat import Directive

meth_sig_re = re.compile(r'^([^\s]+\s+)*([^\s<]+)\s*(<[^\(]+>)?\s*\((.*)\)$')
prop_sig_re = re.compile(r'^([^\s]+\s+)*([^\s]+)\s+([^\s]+)\s*\{\s*(get;)?\s*(set;)?\s*\}$')
param_sig_re = re.compile(r'^([^\s]+)\s+([^\s]+)\s*(=\s*([^\s]+))?$')
type_sig_re = re.compile(r'^([^\s<\[]+)\s*(<.+>)?\s*(\[\])?$')
attr_sig_re = re.compile(r'^([^\s]+)(\s+\((.*)\))?$')
ParamTuple = namedtuple('ParamTuple', ['name', 'type', 'default'])

def split_sig(params):
    """
    Split a list of parameters/types by commas, whilst respecting angle brackets
    For example:
      String arg0, int arg2 = 1, Dictionary<int,int> arg3
      => ['String arg0', 'int arg2 = 1', 'Dictionary<int,int> arg3']
    """
    result = []
    current = ''
    level = 0
    for c in params:
        if c == '<':
            level += 1
        elif c == '>':
            level -= 1
        if c != ',' or level > 0:
            current += c
        elif c == ',' and level == 0:
            result.append(current)
            current = ''
    if current.strip() != '':
        result.append(current)
    return result

def parse_method_signature(sig):
    """ Parse a method signature of the form: modifier* type name (params) """
    m = meth_sig_re.match(sig.strip())
    if not m:
        raise RuntimeError('Method signature invalid: ' + sig)
    groups = m.groups()
    if groups[0] is not None:
        modifiers = [x.strip() for x in groups[:-4]]
        groups = groups[-4:]
    else:
        modifiers = []
        groups = groups[1:]
    typ, name, generic_types, params = groups
    if params.strip() != '':
        params = split_sig(params)
        params = [parse_param_signature(x) for x in params]
    else:
        params = []
    return (modifiers, typ, name, generic_types, params)

def parse_property_signature(sig):
    """ Parse a property signature of the form: modifier* type name { (get;)? (set;)? } """
    m = prop_sig_re.match(sig.strip())
    if not m:
        raise RuntimeError('Property signature invalid: ' + sig)
    groups = m.groups()
    if groups[0] is not None:
        modifiers = [x.strip() for x in groups[:-4]]
        groups = groups[-4:]
    else:
        modifiers = []
        groups = groups[1:]
    typ, name, getter, setter = groups
    return (modifiers, typ, name, getter is not None, setter is not None)

def parse_param_signature(sig):
    """ Parse a parameter signature of the form: type name (= default)? """
    m = param_sig_re.match(sig.strip())
    if not m:
        raise RuntimeError('Parameter signature invalid, got ' + sig)
    type,name,_,default = m.groups()
    return ParamTuple(name=name, type=type, default=default)

def parse_type_signature(sig):
    """ Parse a type signature """
    m = type_sig_re.match(sig.strip())
    if not m:
        raise RuntimeError('Type signature invalid, got ' + sig)
    groups = m.groups()
    type = groups[0]
    generic_types = groups[1]
    if not generic_types:
        generic_types = []
    else:
        generic_types = split_sig(generic_types[1:-1])
    is_array = (groups[2] is not None)
    return type,generic_types,is_array

def parse_attr_signature(sig):
    """ Parse an attribute signature """
    m = attr_sig_re.match(sig.strip())
    if not m:
        raise RuntimeError('Attribute signature invalid, got ' + sig)
    name,_,params = m.groups()
    if params != None and params.strip() != '':
        params = split_sig(params)
        params = [parse_param_signature(x) for x in params]
    else:
        params = []
    return (name, params)

msdn_value_types = {
    'string': 'System.String',
    'int': 'System.Int32',
    'long': 'System.Int64',
    'uint': 'System.UInt32',
    'ulong': 'System.UInt64',
    'float': 'System.Single',
    'double': 'System.Double',
    'byte': 'System.Byte',
    'bool': 'System.Boolean'
}

msdn_link_map = {
    'System.Collections.Generic.IList': '5y536ey6',
    'System.Collections.Generic.IDictionary': 's4ys34ea',
    'System.Collections.Generic.ISet': 'dd412081'
}

def get_msdn_ref(app, name, text):
    """ Try and create a reference to a type on MSDN """
    in_msdn = False
    if name in msdn_value_types:
        name = msdn_value_types[name]
        in_msdn = True
    if name.startswith('System.'):
        in_msdn = True
    if in_msdn:
        link = name.split('<')[0]
        if link in msdn_link_map:
            link = msdn_link_map[link]
        else:
            link = link.lower()
        url = 'https://msdn.microsoft.com/en-us/library/'+link+'.aspx'
        node = nodes.reference(name, shorten_type(text))
        node['refuri'] = url
        node['reftitle'] = name
        return node
    else:
        return None

shorten_type_prefixes = [
    'System.',
    'System.Collections.Generic.'
]

def shorten_type(type):
    """ Shorten a type. E.g. drops 'System.' """
    n = 0
    for prefix in shorten_type_prefixes:
        if type.startswith(prefix):
            if len(prefix) > n:
                n = len(prefix)
    return type[n:]

class CSharpObject(ObjectDescription):
    """ Description of generic C# objects """

    def add_target_and_index(self, name, sig, signode):
        targetname = self.objtype + '-' + name
        if targetname not in self.state.document.ids:
            signode['names'].append(targetname)
            signode['ids'].append(targetname)
            signode['first'] = (not self.names)
            self.state.document.note_explicit_target(signode)

            objects = self.env.domaindata['csharp']['objects']
            key = (self.objtype, name)
            if key in objects:
                self.env.warn(self.env.docname,
                              'duplicate description of %s %s, ' %
                              (self.objtype, name) +
                              'other instance in ' +
                              self.env.doc2path(objects[key]),
                              self.lineno)
            objects[key] = self.env.docname
        indextext = self.get_index_text(self.objtype, name)
        if indextext:
            self.indexnode['entries'].append(('single', indextext, targetname, ''))

    def get_index_text(self, objectname, name):
        if self.objtype == 'directive':
            return _('%s (directive)') % name
        elif self.objtype == 'role':
            return _('%s (role)') % name
        return ''

    def before_content(self):
        lastname = self.names and self.names[-1]
        if lastname:
            self.parentname_set = True
            self.parentname_saved = self.env.ref_context.get('csharp:parent')
            self.env.ref_context['csharp:parent'] = lastname
        else:
            self.parentname_set = False

    def after_content(self):
        if self.parentname_set:
            self.env.ref_context['csharp:parent'] = self.parentname_saved

    def has_parent(self):
        return 'csharp:parent' in self.env.ref_context and \
            self.env.ref_context['csharp:parent'] != None

    def get_parent(self):
        return self.env.ref_context['csharp:parent']

    def get_fullname(self, name):
        fullname = name
        if self.has_parent():
            fullname = self.get_parent()+'.'+fullname
        return fullname

    def append_modifiers(self, signode, modifiers):
        if len(modifiers) == 0:
            return
        for modifier in modifiers:
            signode += nodes.emphasis(modifier, modifier)
            signode += nodes.Text(u' ')

    def append_type(self, node, type):
        type,generic_types,is_array = parse_type_signature(type)
        tnode = addnodes.pending_xref(
            '', refdomain='csharp', reftype='type',
            reftarget=type, modname=None, classname=None)
        if not self.has_parent():
            tnode['csharp:parent'] = None
        else:
            tnode['csharp:parent'] = self.get_parent()
        tnode += nodes.Text(shorten_type(type))
        node += tnode
        if len(generic_types) > 0:
            node += nodes.Text('<')
            for i,type in enumerate(generic_types):
                self.append_type(node, type)
                if i != len(generic_types)-1:
                    node += nodes.Text(', ')
            node += nodes.Text('>')
        if is_array: node += nodes.Text('[]')

    def append_parameters(self, node, params):
        pnodes = addnodes.desc_parameterlist()
        for param in params:
            pnode = addnodes.desc_parameter('', '', noemph=True)
            self.append_type(pnode, param.type)
            pnode += nodes.Text(u' ')
            pnode += nodes.emphasis(param.name, param.name)
            if param.default is not None:
                default = u' = ' + param.default
                pnode += nodes.emphasis(default, default)
            pnodes += pnode
        node += pnodes

class CSharpCurrentNamespace(Directive):
    """ Set the current C# namespace """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}

    def run(self):
        env = self.state.document.settings.env
        namespace = self.arguments[0].strip()
        if namespace == 'None':
            env.ref_context.pop('csharp:parent', None)
        else:
            env.ref_context['csharp:parent'] = namespace
        return []

class CSharpClass(CSharpObject):
    """ Description of a C# class """

    def handle_signature(self, sig, signode):
        type,generic_types,_ = parse_type_signature(sig)
        desc_name = 'class %s' % sig
        signode += addnodes.desc_name(desc_name, desc_name)
        return self.get_fullname(type)

class CSharpMethod(CSharpObject):
    """ Description of a C# method """

    def handle_signature(self, sig, signode):
        modifiers,type,name,generic_types,params = parse_method_signature(sig)
        self.append_modifiers(signode, modifiers)
        if type is not None:
            self.append_type(signode, type)
            signode += nodes.Text(' ')
        signode += addnodes.desc_name(name, name)
        if generic_types != None:
            signode += nodes.Text(generic_types)
        signode += nodes.Text(' ')
        self.append_parameters(signode, params)
        return self.get_fullname(name)

class CSharpProperty(CSharpObject):
    """ Description of a C# property """

    def handle_signature(self, sig, signode):
        modifiers,type,name,getter,setter = parse_property_signature(sig)
        self.append_modifiers(signode, modifiers)
        self.append_type(signode, type)
        signode += nodes.Text(' ')
        signode += addnodes.desc_name(name, name)
        signode += nodes.Text(' { ')
        extra = []
        if getter: extra.append('get;')
        if setter: extra.append('set;')
        extra = ' '.join(extra)
        signode += addnodes.desc_annotation(extra, extra)
        signode += nodes.Text(' }')
        return self.get_fullname(name)

class CSharpEnum(CSharpObject):
    """ Description of a C# enum """

    def handle_signature(self, sig, signode):
        desc_name = 'enum %s' % sig
        signode += addnodes.desc_name(desc_name, desc_name)
        return self.get_fullname(sig)

class CSharpEnumValue(CSharpObject):
    """ Description of a C# enum value """

    def handle_signature(self, sig, signode):
        name = sig
        signode += addnodes.desc_name(name, name)
        return self.get_fullname(name)

class CSharpAttribute(CSharpObject):
    """ Description of a C# attribute """

    def handle_signature(self, sig, signode):
        name,params = parse_attr_signature(sig)
        signode += addnodes.desc_name(name, name)
        if len(params) > 0:
            signode += nodes.Text(' ')
            self.append_parameters(signode, params)
        return self.get_fullname(name)

class CSharpXRefRole(XRefRole):

    def process_link(self, env, refnode, has_explicit_title, title, target):
        refnode['csharp:parent'] = env.ref_context.get('csharp:parent')
        return super(CSharpXRefRole, self).process_link(env, refnode, has_explicit_title, title, target)

class CSharpDomain(Domain):
    """ C# domain """
    name = 'csharp'
    label = 'C#'

    object_types = {
        'class':     ObjType(l_('class'),     'type'),
        'method':    ObjType(l_('method'),    'meth'),
        'property':  ObjType(l_('property'),  'prop'),
        'enum':      ObjType(l_('enum'),      'type'),
        'value':     ObjType(l_('value'),     'enum'),
        'attribute': ObjType(l_('attribute'), 'attr'),
    }
    directives = {
        'namespace': CSharpCurrentNamespace,
        'class':     CSharpClass,
        'method':    CSharpMethod,
        'property':  CSharpProperty,
        'enum':      CSharpEnum,
        'value':     CSharpEnumValue,
        'attribute': CSharpAttribute,
    }
    roles = {
        'type': CSharpXRefRole(),
        'meth': CSharpXRefRole(),
        'prop': CSharpXRefRole(),
        'enum': CSharpXRefRole(),
        'attr': CSharpXRefRole(),
    }
    initial_data = {
        'objects': {},  # fullname -> docname, objtype
    }

    def clear_doc(self, docname):
        for (typ, name), doc in self.data['objects'].items():
            if doc == docname:
                del self.data['objects'][typ, name]

    def resolve_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        targets = [target]
        if node['csharp:parent'] is not None:
            parts = node['csharp:parent'].split('.')
            while len(parts) > 0:
                targets.append('.'.join(parts)+'.'+target)
                parts = parts[:-1]

        objects = self.data['objects']
        objtypes = self.objtypes_for_role(typ)
        for target in targets:
            for objtype in objtypes:
                if (objtype, target) in objects:
                    return make_refnode(builder, fromdocname,
                                        objects[objtype, target],
                                        objtype + '-' + target,
                                        contnode, target + ' ' + objtype)

        for target in targets:
            ref = get_msdn_ref(self.env, target, target)
            if ref is not None:
                return ref

    def get_objects(self):
        for (typ, name), docname in self.data['objects'].items():
            yield name, name, typ, docname, typ + '-' + name, 1

def setup(app):
    app.add_domain(CSharpDomain)
