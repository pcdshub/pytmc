'''
TMC, XTI, tsproj parsing utilities
'''
import collections
import logging
import os
import pathlib
import types

import lxml
import lxml.etree

from .code import (get_pou_call_blocks, program_name_from_declaration,
                   variables_from_declaration)
# Registry of all TwincatItem-based classes
TWINCAT_TYPES = {}
USE_FILE_AS_PATH = object()

logger = logging.getLogger(__name__)


def parse(fn, *, parent=None):
    '''
    Parse a given tsproj, xti, or tmc file.

    Returns
    -------
    item : TwincatItem
    '''
    fn = case_insensitive_path(fn)

    with open(fn, 'rt') as f:
        tree = lxml.etree.parse(f)

    root = tree.getroot()
    return TwincatItem.parse(root, filename=fn, parent=parent)


def element_to_class_name(element):
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
    if tag == 'TcSmItem':
        return f'{tag}_' + element.attrib['ClassName'], TcSmItem
    if tag == 'Symbol':
        base_type, = element.xpath('BaseType')
        return f'{tag}_' + base_type.text, Symbol
    if os.path.splitext(element.base)[-1].lower() == '.tmc':
        return tag, _TmcItem
    return tag, TwincatItem


class TwincatItem:
    _load_path = ''

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
        self.attributes = dict(element.attrib)
        self.children = []
        self.comments = []
        self.children_by_tag = None
        self.element = element
        self.filename = filename
        self.name = name
        self.parent = parent
        self.tag = element.tag
        self.text = element.text.strip() if element.text else None

        self._add_children(element)
        self.post_init()
        if self.name == '__FILENAME__':
            self.name = self.filename.stem

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
    def qualified_path(self):
        'Path of classes required to get to this instance'
        hier = [self]
        parent = self.parent
        while parent:
            hier.append(parent)
            parent = parent.parent
        return '/'.join(strip_namespace(item.__class__.__name__)
                        for item in reversed(hier))

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

    def find(self, cls):
        '''
        Find any descendents that are instances of cls

        Parameters
        ----------
        cls : TwincatItem
        '''
        for child in self.children:
            if isinstance(child, cls):
                yield child
            yield from child.find(cls)

    def _add_children(self, element):
        'A hook for adding all children'
        for child in element.iterchildren():
            self._add_child(child)

        by_tag = separate_children_by_tag(self.children)
        self.children_by_tag = types.SimpleNamespace(**by_tag)
        for key, value in by_tag.items():
            if not hasattr(self, key):
                setattr(self, key, value)

    def _add_child(self, element):
        'Add a single child to the list of children'
        if isinstance(element, lxml.etree._Comment):
            self.comments.append(element.text)
            return

        child = self.parse(element, parent=self, filename=self.filename)
        self.children.append(child)

        # Two ways for names to come in:
        # 1. the child has a tag of 'Name', with its text being our name
        if child.tag == 'Name' and child.text and self.parent:
            name = child.text.strip()
            self.name = name

        # 2. the child has an attribute key 'Name'
        try:
            name = child.attributes.pop('Name').strip()
        except KeyError:
            ...
        else:
            child.name = name

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

        classname, base = element_to_class_name(element)

        try:
            cls = TWINCAT_TYPES[classname]
        except KeyError:
            # Dynamically create and register new TwincatItem-based types!
            cls = type(classname, (base, ), {})

        if 'File' in element.attrib:
            # This is defined directly in the file. Instantiate it as-is:
            filename = element.attrib['File']
            return cls.from_file(filename, parent=parent)

        return cls(element, parent=parent, filename=filename)

    def _repr_info(self):
        '__repr__ information'
        return {
            'name': self.name,
            'attributes': self.attributes,
            'children': self.children,
            'text': self.text,
        }

    def __repr__(self):
        info = ' '.join(f'{key}={value!r}'
                        for key, value in self._repr_info().items()
                        if value)

        return f'<{self.__class__.__name__} {info}>'

    @classmethod
    def from_file(cls, filename, parent):
        if cls._load_path is USE_FILE_AS_PATH:
            parent_root = pathlib.Path(parent.filename).parent
            full_path = (parent_root / pathlib.Path(parent.filename).stem /
                         filename)
        else:
            project = parent.find_ancestor(Project)
            project_root = pathlib.Path(project.filename).parent
            full_path = project_root / cls._load_path / filename
        return parse(full_path, parent=parent)


class _TwincatProjectSubItem(TwincatItem):
    '[XTI/TMC/...] A base class for items that appear in virtual PLC projects'

    @property
    def project(self):
        'The nested project (virtual PLC project) associated with the item'
        # TODO this is wrong... can't consistently find Mappings...
        ancestor = self.find_ancestor(TcSmItem_CNestedPlcProjDef)
        return ancestor if ancestor else self.find_ancestor(Plc)


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
    '[XTC] For a Link between VarA and VarB, this is the parent of VarA'
    ...


class OwnerB(TwincatItem):
    '[XTC] For a Link between VarA and VarB, this is the parent of VarB'
    ...


class Link(TwincatItem):
    '[XTI] Links between NC/PLC/IO'
    def post_init(self):
        self.a = (self.find_ancestor(OwnerA).name, self.attributes.get('VarA'))
        self.b = (self.find_ancestor(OwnerB).name, self.attributes.get('VarB'))


class Project(TwincatItem):
    '[tsproj] A project which contains Plc, Io, Mappings, etc.'
    _load_path = pathlib.Path('_Config') / 'PLC'

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


class TcSmProject(TwincatItem):
    '[tsproj] A top-level TwinCAT tsproj'
    @property
    def plcs(self):
        'The nested projects (virtual PLC project) contained in this Project'
        return [plc for plc in self.find(Plc)
                if plc.project is not None]


class TcSmItem(TwincatItem):
    '''
    [XTI] Top-level container for XTI files

    Further broken down into classes such as `TcSmItem_CNcSafTaskDef`, the
    latter portion being derived from the `ClassName` attribute in the XML
    file.
    '''
    ...


class Plc(TwincatItem):
    '[XTI] A Plc Project'

    Project: list

    def post_init(self):
        self.namespaces = {}
        if hasattr(self, 'Project'):
            proj = self.Project[0]
        else:
            self.project = None
            self.tmc = None
            # Some <Plc>s are merely containers for nested project
            # definitions in separate XTI files. Ignore those for now, as
            # they will be loaded later.
            return

        self.project_path = self.get_relative_path(
            proj.attributes['PrjFilePath'])
        self.tmc_path = self.get_relative_path(
            proj.attributes['TmcFilePath'])
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

        self.pou_by_name = {
            plc_obj.POU[0].program_name: plc_obj.POU[0]
            for plc_obj in self.source.values()
            if hasattr(plc_obj, 'POU')
            and plc_obj.POU[0].program_name
        }

        self.gvl_by_name = {
            plc_obj.GVL[0].name: plc_obj.GVL[0]
            for plc_obj in self.source.values()
            if hasattr(plc_obj, 'GVL')
            and plc_obj.GVL[0].name
        }

        self.namespaces.update(self.pou_by_name)
        self.namespaces.update(self.gvl_by_name)

    def find(self, cls):
        yield from super().find(cls)
        if self.project is not None:
            yield from self.project.find(cls)

        for _, ns in self.namespaces.items():
            if isinstance(ns, cls):
                yield ns

        if self.tmc is not None:
            yield from self.tmc.find(cls)


class TcSmItem_CNestedPlcProjDef(TcSmItem, Plc):
    '''
    [XTI] Nested PLC project definition (i.e., a virtual PLC project)

    Contains POUs and a parsed version of the tmc
    '''
    ...


class Compile(TwincatItem):
    '''
    [XTI] A code entry in a nested/virtual PLC project

    File to load is marked with 'Include'
    May be TcTTO, TcPOU, TcDUT, GVL, etc.
    '''
    ...


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
        return self.Enum[0].text

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
                  else lbound + elements)

        self.bounds = (lbound, ubound)
        self.elements = elements


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

    def walk(self):
        if not hasattr(self, 'SubItem'):
            yield [self]
        else:
            for subitem in self.SubItem:
                for item in subitem.walk():
                    yield [self, subitem] + item

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
    def type(self):
        'The base type'
        return self.Type[0].text

    @property
    def qualified_type_name(self):
        'The base type, including the namespace'
        type_ = self.Type[0]
        namespace = type_.attributes.get("Namespace", None)
        return f'{namespace}.{type_.text}' if namespace else type_.text

    def walk(self):
        yield from self.data_type.walk()


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


class BuiltinDataType:
    '[TMC] A built-in data type such as STRING, INT, REAL, etc.'
    def __init__(self, typename, *, length=1):
        if '(' in typename:
            typename, length = typename.split('(')
            length = int(length.rstrip(')'))

        self.name = typename
        self.length = length

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

    def walk(self):
        yield []


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
        'The Module containing the Symbol'
        return self.find_ancestor(Module)

    @property
    def info(self):
        return dict(name=self.name,
                    bit_size=self.BitSize[0].text,
                    type=self.type_name,
                    qualified_type_name=self.qualified_type_name,
                    bit_offs=self.BitOffs[0].text,
                    module=self.module.name,
                    )

    def walk(self):
        for item in self.data_type.walk():
            yield [self] + item

    @property
    def array_info(self):
        try:
            return self.ArrayInfo[0]
        except (AttributeError, IndexError):
            return None


class Symbol_FB_MotionStage(Symbol):
    '[TMC] A customized Symbol, representing only FB_MotionStage'
    def _repr_info(self):
        '__repr__ information'
        repr_info = super()._repr_info()
        # Add on the NC axis name
        repr_info.update(nc_axis=self.nc_axis.name)
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
    def pou(self):
        'The POU program associated with the Symbol'
        # TODO: hack
        for pou in self.root.find(POU):
            if pou.name == self.program_name:
                return pou
        # return self.project.pou_by_name[self.program_name]

    @property
    def call_block(self):
        '''
        A dictionary representation of the call

        For example::
            M1(a := 1, b := 2);

        Becomes::
            {'a': '1', 'b': '2'}
        '''
        return self.pou.call_blocks[self.motor_name]

    @property
    def linked_to(self):
        '''
        Where the axis is linked to, determined by the call block in the POU
        where the AXIS_REF is defined

        Returns
        -------
        linked_to : str
            e.g., M1
        linked_to_full : str
            e.g., Main.M1
        '''
        linked_to = self.call_block['stMotionStage']
        return linked_to, self.pou.get_fully_qualified_name(linked_to)

    @property
    def nc_to_plc_link(self):
        '''
        The Link for NcToPlc

        That is, how the NC axis is connected to the FB_MotionStage
        '''
        _, linked_to_full = self.linked_to

        links = [
            link
            for link in self.project.find(Link)
            if f'^{linked_to_full.lower()}' in link.attributes['VarA'].lower()
            and 'NcToPlc' in link.attributes['VarA']
        ]

        if not links:
            raise RuntimeError(f'No NC link to FB_MotionStage found for '
                               f'{self.name!r} (^{linked_to_full})')

        link, = links
        return link

    @property
    def nc_axis(self):
        'The NC `Axis` associated with the FB_MotionStage'
        link = self.nc_to_plc_link
        parent_name = link.parent.name.split('^')
        if parent_name[0] == 'TINC':
            parent_name = parent_name[1:]

        task_name, axis_section, axis_name = parent_name

        nc, = list(nc for nc in self.root.find(NC)
                   if nc.SafTask[0].name == task_name)
        nc_axis = nc.axis_by_name[axis_name]
        # link nc_axis and FB_MotionStage?
        return nc_axis


class GVL(_TwincatProjectSubItem):
    '[XTI] A Global Variable List'
    ...


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
    ...


class NC(TwincatItem):
    '[tsproj or XTI] Top-level NC'
    _load_path = pathlib.Path('_Config') / 'NC'

    def post_init(self):
        # Axes can be stored directly in the tsproj:
        self.axes = getattr(self, 'Axis', [])
        if not self.axes:
            # Or they can be stored in a separate file, 'NC.xti':
            self.axes = [item.Axis[0] for item in getattr(self, 'TcSmItem', [])
                         ]

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
    _load_path = pathlib.Path('_Config') / 'NC' / 'Axes'

    @property
    def axis_number(self):
        return self.attributes['Id']

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
        for param in self.find(AxisPara):
            yield from param.attributes.items()
            for child in param.children:
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
    ...


class Encoder(TwincatItem):
    '''
    [XTI] Encoder

    Contains EncPara, Vars, Mappings, etc.
    '''
    def summarize(self):
        yield 'EncType', self.attributes['EncType']
        for param in self.find(EncPara):
            yield from param.attributes.items()
            for child in param.children:
                for key, value in child.attributes.items():
                    yield f'{child.tag}:{key}', value


class Device(TwincatItem):
    '[XTI] Top-level IO device container'
    _load_path = pathlib.Path('_Config') / 'IO'


class Box(TwincatItem):
    '[XTI] A box / module'
    _load_path = USE_FILE_AS_PATH


class RemoteConnections(TwincatItem):
    '[StaticRoutes] Routes contained in the TwinCat configuration'
    def post_init(self):
        def to_dict(child):
            return {
                item.tag: item.text
                for item in child.children
            }

        def keyed_on(key):
            return {
                getattr(child, key)[0].text: to_dict(child)
                for child in self.children
                if hasattr(child, key)
            }

        self.by_name = keyed_on('Name')
        self.by_address = keyed_on('Address')
        self.by_ams_id = keyed_on('NetId')


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


def separate_children_by_tag(children):
    '''
    Take in a list of `TwincatItem`, categorize each by their XML tag, and
    return a dictionary keyed on tag.

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
        d[child.tag].append(child)

    return d


def strip_namespace(tag):
    'Strip off {{namespace}} from: {{namespace}}tag'
    return lxml.etree.QName(tag).localname
