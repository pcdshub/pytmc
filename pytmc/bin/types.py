"""
"pytmc-types" is a Qt interface that shows DataType-related information from a
tmc file.
"""

import argparse
import pathlib
import sys

from qtpy import QtWidgets
from qtpy.QtCore import Qt, Signal

import pytmc


DESCRIPTION = __doc__


def build_arg_parser(parser=None):
    if parser is None:
        parser = argparse.ArgumentParser()

    parser.description = DESCRIPTION
    parser.formatter_class = argparse.RawTextHelpFormatter

    parser.add_argument(
        'tmc_file', metavar="INPUT", type=str,
        help='Path to .tmc file'
    )

    return parser


def find_data_types(tmc):
    yield from tmc.find(pytmc.parser.DataType, recurse=False)


class TmcTypes(QtWidgets.QMainWindow):
    '''
    pytmc debug interface

    Parameters
    ----------
    tmc : TmcFile
        The tmc file to inspect
    '''

    item_selected = Signal(object)

    def __init__(self, tmc):
        super().__init__()
        self.setWindowTitle(str(tmc.filename))

        # Right part of the window
        self.lists = []
        self.types = {}

        self.main_frame = QtWidgets.QFrame()
        self.setCentralWidget(self.main_frame)

        self.layout = QtWidgets.QHBoxLayout()
        self.main_frame.setLayout(self.layout)

        self.item_list = QtWidgets.QListWidget()
        self.layout.addWidget(self.item_list)

        self.item_list.currentItemChanged.connect(self._data_type_selected)

        for dtype in sorted(find_data_types(tmc),
                            key=lambda item: item.name):
            item = QtWidgets.QListWidgetItem(dtype.name)
            item.setData(Qt.UserRole, dtype)
            self.item_list.addItem(item)

    def _data_type_selected(self, current, previous):
        'Slot - new list item selected'
        if current is None:
            return

        dtype = current.data(Qt.UserRole)
        self._set_list_count(1)
        list_widget, = self.lists
        self.types[0] = dtype
        self._update_list_by_index(0)

    def _set_list_count(self, count):
        while len(self.lists) > count:
            list_widget = self.lists.pop(-1)
            list_widget.clear()
            list_widget.setParent(None)
            list_widget.deleteLater()

        while len(self.lists) < count:
            self._add_list()

    def _update_list_by_index(self, idx):
        list_widget = self.lists[idx]
        list_widget.clear()

        dtype = self.types[idx]
        for subitem in getattr(dtype, 'SubItem', []):
            item = QtWidgets.QListWidgetItem(
                f'{subitem.name} : {subitem.data_type.name}')
            item.setData(Qt.UserRole, subitem.data_type)
            list_widget.addItem(item)

    def _add_list(self):
        item_list = QtWidgets.QListWidget()
        self.lists.append(item_list)
        list_index = len(self.lists) - 1
        self.layout.addWidget(item_list)

        def changed(current, previous):
            if current is not None:
                child_dtype = current.data(Qt.UserRole)
                child_index = list_index + 1
                if not hasattr(child_dtype, 'SubItem'):
                    self._set_list_count(child_index)
                else:
                    self._set_list_count(child_index + 1)
                    self.types[child_index] = (
                        child_dtype.data_type
                        if hasattr(child_dtype, 'data_type')
                        else child_dtype)
                    self._update_list_by_index(child_index)

        item_list.currentItemChanged.connect(changed)
        return item_list


def create_types_gui(tmc):
    '''
    Show the data type information gui

    Parameters
    ----------
    tmc : TmcFile, str, pathlib.Path
        The tmc file to show
    '''
    if isinstance(tmc, (str, pathlib.Path)):
        tmc = pytmc.parser.parse(tmc)

    interface = TmcTypes(tmc)
    interface.setMinimumSize(600, 400)
    return interface


def main(tmc_file, *, dbd=None):
    app = QtWidgets.QApplication([])
    interface = create_types_gui(tmc_file)
    interface.show()
    sys.exit(app.exec_())
