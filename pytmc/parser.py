'''
TMC, XTI, tsproj parsing utilities
'''
import collections
import logging
import os
import pathlib
import re
import types

import lxml
import lxml.etree

from .code import (determine_block_type, get_pou_call_blocks,
                   program_name_from_declaration, variables_from_declaration)

# Registry of all TwincatItem-based classes
TWINCAT_TYPES = {}
USE_NAME_AS_PATH = object()

logger = logging.getLogger(__name__)
SLN_PROJECT_RE = re.compile(
    r"^Project.*?=\s*\"(.*?)\",\s*\"(.*?)\"\s*,\s*(.*?)\"\s*$",
    re.MULTILINE
)


def parse(fn, *, parent=None):
    '''
    Parse a given tsproj, xti, or tmc file.

    Returns
    -------
    item : TwincatItem
    '''
    fn = case_insensitive_path(fn)

    with open(fn, 'rb') as f:
        tree = lxml.etree.parse(f)

    root = tree.getroot()
    return TwincatItem.parse(root, filename=fn, parent=parent)


def projects_from_solution(fn, *, exclude=None):
    '''
    Find project filenames from a solution.

    Parameters
    ----------
    fn : str, pathlib.Path
        Solution filename
    exclude : list or None
        Exclude certain extensions. Defaults to excluding .tcmproj
    '''
    with open(fn, 'rt') as f:
        solution_text = f.read()

    if exclude is None:
        exclude = ('.tcmproj', )

    projects = [
        pathlib.PureWindowsPath(match[1])
        for match in SLN_PROJECT_RE.findall(solution_text)
    ]

    solution_path = pathlib.Path(fn).parent
    return [(solution_path / pathlib.Path(project)).absolute()
            for project in projects
            if project.suffix not in exclude
            ]


def element_to_class_name(element, *, parent=None):
    '''
    Determine the Python class name for an element

    Parameters
    ----------
    element : lxml.etree.Element

    Returns
    -------
    class_name : str
    base_class : class
    '''

    tag = strip_namespace(element.tag)
    extension = os.path.splitext(element.base)[-1].lower()

    if tag == 'Project':
        if isinstance(parent, TcSmProject):
            return 'TopLevelProject', TwincatItem
        if 'File' in element.attrib:
            # File to be loaded will contain PrjFilePath
            return 'Plc', TwincatItem
        if 'PrjFilePath' in element.attrib:
            return 'Plc', TwincatItem
        if isinstance(parent, (Plc, TcSmItem)):
            return 'PlcProject', TwincatItem
        return 'Project', TwincatItem
    if tag == 'Plc':
        return 'TopLevelPlc', TwincatItem

    if tag == 'Symbol':
        base_type, = element.xpath('BaseType')
        return f'{tag}_' + base_type.text, Symbol

    if extension == '.tmc':
        return tag, _TmcItem

    return tag, TwincatItem


def _determine_path(base_path, name, class_hint):
    '''
    Determine the path to load child XTI items from, given a base path and the
    class load path hint.

    Parameters
    ----------
    base_path : pathlib.Path
        The path from which to start, e.g., the child_load_path of the parent
        object

    name : str
        The name of the parent object, to be used when USE_NAME_AS_PATH is
        specified

    class_hint : pathlib.Path or USE_NAME_AS_PATH
        A hint path as to where to load child objects from
    '''
    if not class_hint:
        return base_path

    path = base_path / (name
                        if class_hint is USE_NAME_AS_PATH
                        else class_hint)

    if path.exists() and path.is_dir():
        return path
    return base_path  # the fallback


class TwincatItem:
    _load_path_hint = ''

    def __init__(self, element, *, parent=None, name=None, filename=None):
        '''
        Represents a single TwinCAT project XML Element, for either tsproj,
        xti, tmc, etc.

        Parameters
        ----------
        element : lxml.etree.Element
        parent : TwincatItem, optional
        name : str, optional
        filename : pathlib.Path, optional
        '''
        self.child_load_path = _determine_path(
            filename.parent, name, self._load_path_hint)

        self.attributes = dict(element.attrib)
        self._children = []
        self.children = None  # populated later
        self.comments = []
        self.element = element
        self.filename = filename
        self.name = name
        self.parent = parent
        self.tag = element.tag
        self.text = element.text.strip() if element.text else None

        self._add_children(element)
        self.post_init()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        TWINCAT_TYPES[cls.__name__] = cls

    def post_init(self):
        'Hook for subclasses; called after __init__'
        ...

    @property
    def root(self):
        'The top-level TwincatItem (likely TcSmProject)'
        parent = self
        while parent.parent is not None:
            parent = parent.parent
        return parent

    @property
    def path(self):
        'Path of classes required to get to this instance'
        hier = [self]
        parent = self.parent
        while parent:
            hier.append(parent)
            parent = parent.parent
        return '/'.join(item.__class__.__name__ for item in reversed(hier))

    def find_ancestor(self, cls):
        '''
        Find an ancestor of this instance

        Parameters
        ----------
        cls : TwincatItem
        '''
        parent = self.parent
        while parent and not isinstance(parent, cls):
            parent = parent.parent
        return parent

    def get_relative_path(self, path):
        '''
        Get an absolute path relative to this item

        Returns
        -------
        path : pathlib.Path
        '''
        root = pathlib.Path(self.filename).parent
        rel_path = pathlib.PureWindowsPath(path)
        return (root / rel_path).resolve()

    def find(self, cls, *, recurse=True):
        '''
        Find any descendents that are instances of cls

        Parameters
        ----------
        cls : TwincatItem
        '''
        for child in self._children:
            if isinstance(child, cls):
                yield child
                if not recurse:
                    continue

            yield from child.find(cls, recurse=recurse)

    def _add_children(self, element):
        'A hook for adding all children'
        for child_element in element.iterchildren():
            if isinstance(child_element, lxml.etree._Comment):
                self.comments.append(child_element.text)
                continue
            self._add_child(child_element)

        by_tag = separate_by_classname(self._children)
        self.children = types.SimpleNamespace(**by_tag)
        for key, value in by_tag.items():
            if not hasattr(self, key):
                setattr(self, key, value)

    def _add_child(self, element):
        child = self.parse(element, parent=self, filename=self.filename)
        if child is None:
            return

        self._children.append(child)

        if not hasattr(child, '_squash_children'):
            return

        for grandchild in list(child._children):
            if any(isinstance(grandchild, squashed_type)
                   for squashed_type in child._squash_children):
                self._children.append(grandchild)
                grandchild.container = child
                grandchild.parent = self
                child._children.remove(grandchild)

    @staticmethod
    def parse(element, parent=None, filename=None):
        '''
        Parse an XML element and return a TwincatItem

        Parameters
        ----------
        element : lxml.etree.Element
        parent : TwincatItem, optional
            The parent to assign to the new element
        filename : str, optional
            The filename the element originates from

        Returns
        -------
        item : TwincatItem
        '''

        classname, base = element_to_class_name(element, parent=parent)

        try:
            cls = TWINCAT_TYPES[classname]
        except KeyError:
            # Dynamically create and register new TwincatItem-based types!
            cls = type(classname, (base, ), {})

        if 'File' in element.attrib:
            # This is defined directly in the file. Instantiate it as-is:
            filename = element.attrib['File']
            return cls.from_file(filename, parent=parent)

        # Two ways for names to come in:
        # 1. a child has a tag of 'Name', with its text being our name
        names = [child.text for child in element.iterchildren()
                 if child.tag == 'Name' and child.text]
        name = names[0] if names else None

        # 2. the child has an attribute key 'Name'
        try:
            name = element.attrib['Name'].strip()
        except KeyError:
            ...

        # A special identifier __FILENAME__ means to replace the name
        if name == '__FILENAME__':
            name = filename.stem

        return cls(element, parent=parent, filename=filename, name=name)

    def _repr_info(self):
        '__repr__ information'
        return {
            'name': self.name,
            'attributes': self.attributes,
            'children': self._children,
            'text': self.text,
        }

    def __repr__(self):
        info = ' '.join(f'{key}={value!r}'
                        for key, value in self._repr_info().items()
                        if value)

        return f'<{self.__class__.__name__} {info}>'

    @classmethod
    def from_file(cls, filename, parent):
        base_path = _determine_path(
            base_path=parent.child_load_path,
            name=parent.name,
            class_hint=cls._load_path_hint
        )
        return parse(base_path / filename, parent=parent)


class _TwincatProjectSubItem(TwincatItem):
    '[XTI/TMC/...] A base class for items that appear in virtual PLC projects'

    @property
    def plc(self):
        'The nested project (virtual PLC project) associated with the item'
        return self.find_ancestor(Plc)


class TcModuleClass(_TwincatProjectSubItem):
    '[TMC] The top-level TMC file'
    DataTypes: list

    def get_data_type(self, type_name):
        data_types = self.DataTypes[0].types
        try:
            return data_types[type_name]
        except KeyError:
            return BuiltinDataType(type_name)


class OwnerA(TwincatItem):
    '[XTI] For a Link between VarA and VarB, this is the parent of VarA'


class OwnerB(TwincatItem):
    '[XTI] For a Link between VarA and VarB, this is the parent of VarB'


class Link(TwincatItem):
    '[XTI] Links between NC/PLC/IO'
    def post_init(self):
        self.a = (self.find_ancestor(OwnerA).name, self.attributes.get('VarA'))
        self.b = (self.find_ancestor(OwnerB).name, self.attributes.get('VarB'))
        self.link = [self.a, self.b]

    def __repr__(self):
        return f'<Link a={self.a} b={self.b}>'


class TopLevelProject(TwincatItem):
    '[tsproj] Containing Io, System, Motion, TopLevelPlc, etc.'

    @property
    def ams_id(self):
        '''
        The AMS ID of the configured target
        '''
        return self.attributes.get('TargetNetId', '')

    @property
    def target_ip(self):
        '''
        A guess of the target IP, based on the AMS ID
        '''
        ams_id = self.ams_id
        if ams_id.endswith('.1.1'):
            return ams_id[:-4]
        return ams_id  # :(


class PlcProject(TwincatItem):
    ...


class TcSmProject(TwincatItem):
    '[tsproj] A top-level TwinCAT tsproj'
    def post_init(self):
        self.top_level_plc, = list(self.find(TopLevelPlc, recurse=False))

    @property
    def plcs(self):
        'The virtual PLC projects contained in this TcSmProject'
        yield from self.top_level_plc.projects.values()

    @property
    def plcs_by_name(self):
        'The virtual PLC projects in a dictionary keyed by name'
        return {plc.name: plc for plc in self.plcs}

    @property
    def plcs_by_link_name(self):
        'The virtual PLC projects in a dictionary keyed by link name'
        return {plc.link_name: plc for plc in self.plcs}


class TcSmItem(TwincatItem):
    '''
    [XTI] Top-level container for XTI files

    Visual Studio-level configuration changes the project layout significantly,
    with individual XTI files being created for axes, PLCs, etc. instead of
    updating the original tsproj file.

    The additional, optional, level of indirection here can make walking the
    tree frustrating. So, we squash these TcSmItems - skipping over them in the
    hierarchy - and pushing its children into its parent.

    The original container `TcSmItem` is accessible in those items through the
    `.container` attribute.
    '''
    _squash_children = [TwincatItem]


class TopLevelPlc(TwincatItem):
    '[XTI] Top-level PLC, contains one or more projects'

    PlcProjectContainer: list

    def post_init(self):
        # TODO: this appears to cover all bases, but perhaps it could be
        # refactored out
        if hasattr(self, 'Plc'):
            projects = self.Plc
        elif hasattr(self, 'TcSmItem'):
            projects = self.TcSmItem[0].PlcProject
        else:
            raise RuntimeError('Unable to find project?')

        self.projects = {
            project.name: project
            for project in projects
        }

        self.projects_by_link_name = {
            project.link_name: project
            for project in projects
        }

        # Fix to squash hack: squashed Mappings belong to the individual
        # projects, not this TopLevelPlc
        for mapping in getattr(self, 'Mappings', []):
            for project in projects:
                if project.filename == mapping.filename:
                    self._children.remove(mapping)
                    project.Mappings = [mapping]
                    project._children.append(mapping)
                    continue


class Plc(TwincatItem):
    '[tsproj] A project which contains Plc, Io, Mappings, etc.'
    _load_path_hint = pathlib.Path('_Config') / 'PLC'

    def post_init(self):
        self.link_name = (self.Instance[0].name
                          if hasattr(self, 'Instance')
                          else self.name)

        self.namespaces = {}
        self.project_path = self.get_relative_path(
            self.attributes['PrjFilePath'])
        self.tmc_path = self.get_relative_path(
            self.attributes['TmcFilePath'])
        self.project = (parse(self.project_path, parent=self)
                        if self.project_path.exists()
                        else None)
        self.tmc = (parse(self.tmc_path, parent=self)
                    if self.tmc_path.exists()
                    else None)

        self.source_filenames = [
            self.project.get_relative_path(compile.attributes['Include'])
            for compile in self.find(Compile)
            if 'Include' in compile.attributes
        ]

        self.source = {
            str(fn.relative_to(self.project.filename.parent)):
            parse(fn, parent=self)
            for fn in self.source_filenames
        }

        def get_source_items(attr):
            for plc_obj in self.source.values():
                try:
                    source_obj = getattr(plc_obj, attr, [None])[0]
                except IndexError:
                    continue

                if source_obj and source_obj.name:
                    yield (source_obj.name, source_obj)

        self.pou_by_name = dict(sorted(get_source_items('POU')))
        self.gvl_by_name = dict(sorted(get_source_items('GVL')))
        self.dut_by_name = dict(sorted(get_source_items('DUT')))

        self.namespaces.update(self.pou_by_name)
        self.namespaces.update(self.gvl_by_name)
        self.namespaces.update(self.dut_by_name)

    @property
    def links(self):
        return [link
                for mapping in self.Mappings
                for link in mapping.find(Link, recurse=False)
                ]

    @property
    def port(self):
        '''
        The ADS port for the project
        '''
        return self.attributes.get('AmsPort', '')

    @property
    def ams_id(self):
        '''
        The AMS ID of the configured target
        '''
        return self.find_ancestor(TopLevelProject).ams_id
        return self.attributes.get('TargetNetId', '')

    @property
    def target_ip(self):
        '''
        A guess of the target IP, based on the AMS ID
        '''
        return self.find_ancestor(TopLevelProject).target_ip

    def find(self, cls, *, recurse=True):
        yield from super().find(cls, recurse=recurse)
        if self.project is not None:
            yield from self.project.find(cls, recurse=recurse)

        for _, ns in self.namespaces.items():
            if isinstance(ns, cls):
                yield ns

        if self.tmc is not None:
            yield from self.tmc.find(cls, recurse=recurse)

    def get_source_code(self):
        'Get the full source code, DUTs, GVLs, and then POUs'
        source_items = (
            list(self.dut_by_name.items()) +
            list(self.gvl_by_name.items()) +
            list(self.pou_by_name.items())
        )

        return '\n'.join(
            item.get_source_code()
            for item in source_items
            if hasattr(item, 'get_source_code')
        )


class Compile(TwincatItem):
    '''
    [XTI] A code entry in a nested/virtual PLC project

    File to load is marked with 'Include'
    May be TcTTO, TcPOU, TcDUT, GVL, etc.
    '''


class _TmcItem(_TwincatProjectSubItem):
    '[TMC] Any item found in a TMC file'
    @property
    def tmc(self):
        'The TcModuleClass (TMC) associated with the item'
        return self.find_ancestor(TcModuleClass)


class DataTypes(_TmcItem):
    '[TMC] Container of DataType'
    def post_init(self):
        self.types = {
            dtype.qualified_type: dtype
            for dtype in self.find(DataType)
        }

        self.types['Tc2_System.T_MaxString'] = T_MaxString()


class Type(_TmcItem):
    '[TMC] DataTypes/DataType/SubItem/Type'

    @property
    def qualified_type(self):
        'The base type, including the namespace'
        namespace = self.attributes.get("Namespace", None)
        return f'{namespace}.{self.text}' if namespace else self.text


class EnumInfo(_TmcItem):
    '[TMC] Enum values, strings, and associated comments'
    Text: list
    Enum: list
    Comment: list

    @property
    def enum_text(self):
        return self.Text[0].text

    @property
    def enum_value(self):
        try:
            return self.Enum[0].text
        except AttributeError:
            ...

        logger.warning(
            'Encountered a known issue with the TwinCAT-generated TMC file: '
            '%s is missing an Enum value in section %s; this may cause '
            'database generation errors.', self.parent.name, self.path
        )
        return ''

    @property
    def enum_comment(self):
        return self.Comment[0].text if hasattr(self, 'Comment') else ''


class ArrayInfo(_TmcItem):
    '[TMC] Array information for a DataType or Symbol'
    LBound: list
    UBound: list
    Elements: list

    def post_init(self):
        lbound = (int(self.LBound[0].text)
                  if hasattr(self, 'LBound')
                  else 0)

        elements = (int(self.Elements[0].text)
                    if hasattr(self, 'Elements')
                    else 1)

        ubound = (int(self.UBound[0].text)
                  if hasattr(self, 'UBound')
                  else lbound + elements - 1)

        self.bounds = (lbound, ubound)
        self.elements = elements


class ExtendsType(_TmcItem):
    '[TMC] A marker of inheritance / extension, found on DataType'

    @property
    def qualified_type(self):
        if 'Namespace' in self.attributes:
            return f'{self.attributes["Namespace"]}.{self.text}'
        return self.text


class DataType(_TmcItem):
    '[TMC] A DataType with SubItems, likely representing a structure'
    Name: list
    EnumInfo: list
    SubItem: list

    @property
    def qualified_type(self):
        name_attrs = self.Name[0].attributes
        if 'Namespace' in name_attrs:
            return f'{name_attrs["Namespace"]}.{self.name}'
        return self.name

    @property
    def base_type(self):
        base_type = getattr(self, 'BaseType', [None])[0]
        if base_type is None:
            return None
        return self.tmc.get_data_type(base_type.text)

    @property
    def is_complex_type(self):
        return True

    def walk(self, condition=None):
        if self.is_enum:
            # Ensure something is yielded for this type - it doesn't
            # appear possible to have SubItems or use ExtendsType
            # in this case.
            yield []
            return

        extends_types = [
            self.tmc.get_data_type(ext_type.qualified_type)
            for ext_type in getattr(self, 'ExtendsType', [])
        ]
        for extend_type in extends_types:
            yield from extend_type.walk(condition=condition)

        if hasattr(self, 'SubItem'):
            for subitem in self.SubItem:
                for item in subitem.walk(condition=condition):
                    yield [subitem] + item

    @property
    def enum_dict(self):
        return {int(item.enum_value): item.enum_text
                for item in getattr(self, 'EnumInfo', [])}

    @property
    def is_enum(self):
        return len(getattr(self, 'EnumInfo', [])) > 0

    @property
    def is_array(self):
        return len(getattr(self, 'ArrayInfo', [])) > 0

    @property
    def is_string(self):
        return False

    @property
    def array_info(self):
        try:
            return self.ArrayInfo[0]
        except (AttributeError, IndexError):
            return None

    @property
    def length(self):
        array_info = self.array_info
        return array_info.elements if array_info else 1


class SubItem(_TmcItem):
    '[TMC] One element of a DataType'
    Type: list

    @property
    def data_type(self):
        return self.tmc.get_data_type(self.qualified_type_name)

    @property
    def array_info(self):
        try:
            return self.ArrayInfo[0]
        except (AttributeError, IndexError):
            return None

    @property
    def type(self):
        'The base type'
        return self.Type[0].text

    @property
    def qualified_type_name(self):
        'The base type, including the namespace'
        type_ = self.Type[0]
        namespace = type_.attributes.get("Namespace", None)
        return f'{namespace}.{type_.text}' if namespace else type_.text

    def walk(self, condition=None):
        if condition is None or condition(self):
            yield from self.data_type.walk(condition=condition)


class Module(_TmcItem):
    '''
    [TMC] A Module

    Contains generated symbols, data areas, and miscellaneous properties.
    '''

    @property
    def ads_port(self):
        'The ADS port assigned to the Virtual PLC'
        try:
            return self._ads_port
        except AttributeError:
            app_prop, = [prop for prop in self.find(Property)
                         if prop.name == 'ApplicationName']
            port_text = app_prop.value
            self._ads_port = int(port_text.split('Port_')[1])

        return self._ads_port


class Property(_TmcItem):
    '''
    [TMC] A property containing a key/value pair

    Examples of TMC properties::

          ApplicationName (used for the ADS port)
          ChangeDate
          GeneratedCodeSize
          GlobalDataSize
    '''
    Value: list

    @property
    def key(self):
        'The property key name'
        return self.name

    @property
    def value(self):
        'The property value text'
        return self.Value[0].text if hasattr(self, 'Value') else self.text

    def __repr__(self):
        return f'<Property {self.key}={self.value!r}>'


class DataArea(_TmcItem):
    '[TMC] Container that holds symbols'


class BuiltinDataType:
    '[TMC] A built-in data type such as STRING, INT, REAL, etc.'
    def __init__(self, typename, *, length=1):
        if '(' in typename:
            typename, length = typename.split('(')
            length = int(length.rstrip(')'))

        self.name = typename
        self.length = length

    @property
    def is_complex_type(self):
        return False

    @property
    def enum_dict(self):
        return {int(item.enum_value): item.enum_text
                for item in getattr(self, 'EnumInfo', [])}

    @property
    def is_enum(self):
        return len(getattr(self, 'EnumInfo', [])) > 0

    @property
    def is_string(self):
        return self.name == 'STRING'

    @property
    def is_array(self):
        # TODO: you can have an array of STRING(80), for example
        # the length would be reported as 80 here, and the DataType would have
        # ArrayInfo
        return self.length > 1 and not self.is_string

    def walk(self, condition=None):
        yield []


class T_MaxString(BuiltinDataType):
    def __init__(self):
        super().__init__(typename='STRING', length=255)


class Symbol(_TmcItem):
    '''
    [TMC] A basic Symbol type

    This is dynamically subclassed into new classes for ease of implementation
    and searching.  For example, a function block defined as `FB_MotionStage`
    will become `Symbol_FB_MotionStage`.
    '''

    BitOffs: list
    BitSize: list
    BaseType: list

    @property
    def type_name(self):
        'The base type'
        return self.BaseType[0].text

    @property
    def qualified_type_name(self):
        'The base type, including the namespace'
        type_ = self.BaseType[0]
        namespace = type_.attributes.get("Namespace", None)
        return f'{namespace}.{type_.text}' if namespace else type_.text

    @property
    def data_type(self):
        return self.tmc.get_data_type(self.qualified_type_name)

    @property
    def module(self):
        'The TMC Module containing the Symbol'
        return self.find_ancestor(Module)

    @property
    def info(self):
        return dict(name=self.name,
                    bit_size=self.BitSize[0].text,
                    type=self.type_name,
                    qualified_type_name=self.qualified_type_name,
                    bit_offs=self.BitOffs[0].text,
                    module=self.module.name,
                    is_pointer=self.is_pointer,
                    array_bounds=self.array_bounds,
                    summary_type_name=self.summary_type_name,
                    )

    def walk(self, condition=None):
        if condition is None or condition(self):
            for item in self.data_type.walk(condition=condition):
                yield [self] + item

    @property
    def array_info(self):
        try:
            return self.ArrayInfo[0]
        except (AttributeError, IndexError):
            return None

    @property
    def array_bounds(self):
        try:
            return self.array_info.bounds
        except (AttributeError, IndexError):
            return None

    def get_links(self, *, strict=False):
        sym_name = '^' + self.name.lower()
        dotted_name = sym_name + '.'
        plc = self.plc
        plc_name = plc.link_name
        for link in plc.links:
            if any(owner == plc_name and
                   (var.lower().endswith(sym_name) or
                    not strict and dotted_name in var.lower())
                   for owner, var in link.link):
                yield link

    @property
    def is_pointer(self):
        type_ = self.BaseType[0]
        pointer_info = type_.attributes.get("PointerTo", None)
        return bool(pointer_info)

    @property
    def summary_type_name(self):
        summary = self.qualified_type_name
        if self.is_pointer:
            summary = 'POINTER TO ' + summary
        array_bounds = self.array_bounds
        if array_bounds:
            summary = 'ARRAY[{}..{}] OF '.format(*array_bounds) + summary
        return summary


class Symbol_DUT_MotionStage(Symbol):
    '[TMC] A customized Symbol, representing only DUT_MotionStage'
    def _repr_info(self):
        '__repr__ information'
        repr_info = super()._repr_info()
        # Add on the NC axis name
        try:
            repr_info['nc_axis'] = self.nc_axis.name
        except Exception as ex:
            repr_info['nc_axis'] = repr(ex)

        return repr_info

    @property
    def program_name(self):
        '`Main` of `Main.M1`'
        return self.name.split('.')[0]

    @property
    def motor_name(self):
        '`M1` of `Main.M1`'
        return self.name.split('.')[1]

    @property
    def nc_to_plc_link(self):
        '''
        The Link for NcToPlc

        That is, how the NC axis is connected to the DUT_MotionStage
        '''
        expected = '^' + self.name.lower() + '.axis.nctoplc'
        links = [link
                 for link in self.plc.find(Link, recurse=False)
                 if expected in link.a[1].lower()
                 ]

        if not links:
            raise RuntimeError(f'No NC link to DUT_MotionStage found for '
                               f'{self.name!r}')
        link, = links
        return link

    @property
    def nc_axis(self):
        'The NC `Axis` associated with the DUT_MotionStage'
        link = self.nc_to_plc_link
        parent_name = link.parent.name.split('^')
        if parent_name[0] == 'TINC':
            parent_name = parent_name[1:]

        task_name, axis_section, axis_name = parent_name

        nc, = list(nc for nc in self.root.find(NC, recurse=False)
                   if nc.SafTask[0].name == task_name)
        nc_axis = nc.axis_by_name[axis_name]
        # link nc_axis and FB_MotionStage?
        return nc_axis


class GVL(_TwincatProjectSubItem):
    '[TcGVL] A Global Variable List'

    @property
    def declaration(self):
        'The declaration code; i.e., the top portion in visual studio'
        return self.Declaration[0].text

    def get_source_code(self, *, close_block=True):
        'The full source code - declaration only in the case of a GVL'
        return self.declaration


class ST(_TwincatProjectSubItem):
    '[TcDUT/TcPOU] Structured text'


class Implementation(_TwincatProjectSubItem):
    '[TcDUT/TcPOU] Code implementation'


class Declaration(_TwincatProjectSubItem):
    '[TcDUT/TcPOU/TcGVL] Code declaration'


class DUT(_TwincatProjectSubItem):
    '[TcDUT] Data unit type (DUT)'

    @property
    def declaration(self):
        'The declaration code; i.e., the top portion in visual studio'
        return self.Declaration[0].text

    def get_source_code(self, *, close_block=True):
        'The full source code - declaration only in the case of a DUT'
        return self.declaration


class Action(_TwincatProjectSubItem):
    '[TcPOU] Code declaration for actions'

    @property
    def source_code(self):
        return f'''\
ACTION {self.name}:
{self.implementation or ''}
END_ACTION'''

    @property
    def implementation(self):
        'The implementation code; i.e., the bottom portion in visual studio'
        impl = self.Implementation[0]
        if hasattr(impl, 'ST'):
            # NOTE: only ST for now
            return impl.ST[0].text


class POU(_TwincatProjectSubItem):
    '[XTI] A Program Organization Unit'

    # TODO: may fail when mixed with ladder logic?
    Declaration: list
    Implementation: list

    def get_fully_qualified_name(self, name):
        if '.' in name:
            first, rest = name.split('.', 1)
            if (first == self.name or first in self.project.namespaces):
                return name

        return f'{self.name}.{name}'

    @property
    def declaration(self):
        'The declaration code; i.e., the top portion in visual studio'
        return self.Declaration[0].text

    @property
    def implementation(self):
        'The implementation code; i.e., the bottom portion in visual studio'
        impl = self.Implementation[0]
        if hasattr(impl, 'ST'):
            return impl.ST[0].text

    @property
    def actions(self):
        'The action implementations (zero or more)'
        return list(getattr(self, 'Action', []))

    def get_source_code(self, *, close_block=True):
        'The full source code - declaration, implementation, and actions'
        source_code = [self.declaration or '',
                       self.implementation or '',
                       ]

        if close_block:
            source_code.append('')
            closing = {
                'function_block': 'END_FUNCTION_BLOCK',
                'program': 'END_PROGRAM',
                'function': 'END_FUNCTION',
                'action': 'END_ACTION',
            }
            source_code.append(
                closing.get(determine_block_type(self.declaration),
                            '# pytmc: unknown block type')
            )

        # TODO: actions defined outside of the block?
        for action in self.actions:
            source_code.append(action.source_code)

        return '\n'.join(source_code)

    @property
    def call_blocks(self):
        'A dictionary of all implementation call blocks'
        return get_pou_call_blocks(self.declaration, self.implementation)

    @property
    def program_name(self):
        'The program name, determined from the declaration'
        return program_name_from_declaration(self.declaration)

    @property
    def variables(self):
        'A dictionary of variables defined in the POU'
        return variables_from_declaration(self.declaration)


class AxisPara(TwincatItem):
    '''
    [XTI] Axis Parameters

    Has information on units, acceleration, deadband, etc.
    '''


class NC(TwincatItem):
    '[tsproj or XTI] Top-level NC'
    _load_path_hint = pathlib.Path('_Config') / 'NC'

    def post_init(self):
        # Axes can be stored directly in the tsproj:
        self.axes = getattr(self, 'Axis', [])

        self.axis_by_id = {
            int(axis.attributes['Id']): axis
            for axis in self.axes
        }

        self.axis_by_name = {
            axis.name: axis
            for axis in self.axes
        }


class Axis(TwincatItem):
    '[XTI] A single NC axis'
    _load_path_hint = pathlib.Path('Axes')

    @property
    def axis_number(self):
        return int(self.attributes['Id'])

    @property
    def units(self):
        try:
            for axis_para in getattr(self, 'AxisPara', []):
                for general in getattr(axis_para, 'General', []):
                    if 'UnitName' in general.attributes:
                        return general.attributes['UnitName']
        except Exception:
            logger.exception('Unable to determine EGU for Axis %s', self)

        # 'mm' is the default in twincat if unspecified. defaults are not saved
        # in the xti files:
        return 'mm'

    def summarize(self):
        yield from self.attributes.items()
        for param in self.find(AxisPara, recurse=False):
            yield from param.attributes.items()
            for child in param._children:
                for key, value in child.attributes.items():
                    yield f'{child.tag}:{key}', value

        for encoder in getattr(self, 'Encoder', []):
            for key, value in encoder.summarize():
                yield f'Enc:{key}', value


class EncPara(TwincatItem):
    '''
    [XTI] Encoder parameters

    Includes such parameters as ScaleFactorNumerator, ScaleFactorDenominator,
    and so on.
    '''


class Encoder(TwincatItem):
    '''
    [XTI] Encoder

    Contains EncPara, Vars, Mappings, etc.
    '''
    def summarize(self):
        yield 'EncType', self.attributes['EncType']
        for param in self.find(EncPara, recurse=False):
            yield from param.attributes.items()
            for child in param._children:
                for key, value in child.attributes.items():
                    yield f'{child.tag}:{key}', value


class Device(TwincatItem):
    '[XTI] Top-level IO device container'
    _load_path_hint = pathlib.Path('_Config') / 'IO'

    def __init__(self, element, *, parent=None, name=None, filename=None):
        super().__init__(element, parent=parent, name=name, filename=filename)


class Box(TwincatItem):
    '[XTI] A box / module'
    _load_path_hint = USE_NAME_AS_PATH


class RemoteConnections(TwincatItem):
    '[StaticRoutes] Routes contained in the TwinCat configuration'
    def post_init(self):
        def to_dict(child):
            return {
                item.tag: item.text
                for item in child._children
            }

        def keyed_on(key):
            return {
                getattr(child, key)[0].text: to_dict(child)
                for child in self._children
                if hasattr(child, key)
            }

        self.by_name = keyed_on('Name')
        self.by_address = keyed_on('Address')
        self.by_ams_id = keyed_on('NetId')


class _ArrayItemProxy:
    '''
    A TwincatItem proxy that represents a single element of an array value.

    Adjusts 'name' such that access from EPICS will refer to the correct index.

    Parameters
    ----------
    item : TwincatItem
        The item to mirror
    index : int
        The array index to use
    '''

    def __init__(self, item, index):
        self.__dict__.update(
            name=f'{item.name}[{index}]',
            item=item,
            _index=index,
        )

    def __getattr__(self, attr):
        return getattr(self.__dict__['item'], attr)

    def __setattr__(self, attr, value):
        return setattr(self.__dict__['item'], attr, value)


def _make_fake_item(name, parent=None, item_name=None, *, text=None,
                    attrib=None):
    """Make a fake TwincatItem, for debugging/testing purposes."""
    cls = TWINCAT_TYPES[name]
    filename = (parent.filename
                if parent is not None
                else pathlib.Path(__file__))

    attrib = attrib or {}
    if 'name' not in attrib:
        attrib['name'] = item_name or name

    elem = lxml.etree.Element(cls.__name__, attrib=attrib)
    elem.text = text or ''
    item = cls(element=elem,
               name=attrib['name'],
               parent=parent, filename=filename)
    return item


def case_insensitive_path(path):
    '''
    Match a path in a case-insensitive manner, returning the actual filename as
    it exists on the host machine

    Required on Linux to find files in a case-insensitive way. Not required on
    OSX/Windows, but platform checks are not done here.

    Parameters
    ----------
    path : pathlib.Path or str
        The case-insensitive path

    Returns
    -------
    path : pathlib.Path or str
        The case-corrected path

    Raises
    ------
    FileNotFoundError
        When the file can't be found
    '''
    path = pathlib.Path(path)
    if path.exists():
        return path.resolve()

    new_path = pathlib.Path(path.parts[0])
    for part in path.parts[1:]:
        if not (new_path / part).exists():
            all_files = {fn.lower(): fn
                         for fn in os.listdir(new_path)}
            try:
                part = all_files[part.lower()]
            except KeyError:
                raise FileNotFoundError(
                    f'{path} does not exist ({part!r} not in {new_path!r})'
                ) from None
        new_path = new_path / part

    return new_path.resolve()


def separate_by_classname(children):
    '''
    Take in a list of `TwincatItem`, categorize each by their class name (based
    on XML tag), and return a dictionary keyed on that.

    For example::

        <a> <a> <b> <b>

    Would become::

        {'a': [<a>, <a>],
         'b': [<b>, <b>]
         }

    Parameters
    ----------
    children : list
        list of TwincatItem

    Returns
    -------
    dict
        Categorized children
    '''
    d = collections.defaultdict(list)
    for child in children:
        d[child.__class__.__name__].append(child)

    return d


def strip_namespace(tag):
    'Strip off {{namespace}} from: {{namespace}}tag'
    return lxml.etree.QName(tag).localname
