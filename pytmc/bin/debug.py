"""
"pytmc-debug" is a Qt interface that shows information about how pytmc
interprets TwinCAT3 .tmc files.
"""

import argparse
import logging
import pathlib
import sys

from qtpy import QtWidgets
from qtpy.QtCore import Qt, Signal

import pytmc
from .db import process


DESCRIPTION = __doc__
logger = logging.getLogger(__name__)


def _grep_record_names(text):
    if not text:
        return []

    records = [line.rstrip('{')
               for line in text.splitlines()
               if line.startswith('record')   # regular line
               or line.startswith('. record')  # linted line
               or line.startswith('X record')  # linted error line
               ]

    def split_rtyp(line):
        line = line.split('record(', 1)[1].rstrip('")')
        rtyp, record = line.split(',', 1)
        record = record.strip('"\' ')
        return f'{record} ({rtyp})'

    return [split_rtyp(record)
            for record in records
            ]


def _annotate_record_text(linter_results, record_text):
    if not record_text:
        return record_text
    if not linter_results or not (linter_results.warnings or
                                  linter_results.errors):
        return record_text

    lines = [([], line)
             for line in record_text.splitlines()]

    for item in linter_results.warnings + linter_results.errors:
        try:
            lint_md, line = lines[item['line'] - 1]
        except IndexError:
            continue

        if item in linter_results.warnings:
            lint_md.append('X Warning: {}'.format(item['message']))
        else:
            lint_md.append('X Error: {}'.format(item['message']))

    display_lines = []
    for lint_md, line in lines:
        if not lint_md:
            display_lines.append(f'. {line}')
        else:
            display_lines.append(f'X {line}')
            for lint_line in lint_md:
                display_lines.append(lint_line)

    return '\n'.join(display_lines)


class TmcSummary(QtWidgets.QMainWindow):
    '''
    pytmc debug interface

    Parameters
    ----------
    tmc : TmcFile
        The tmc file to inspect
    '''

    item_selected = Signal(object)

    def __init__(self, tmc, dbd):
        super().__init__()
        self.tmc = tmc
        self.chains = {}
        self.records = {}

        records, self.exceptions = process(tmc, allow_errors=True,
            allow_no_pragma=True)
        print(records)

        for record in records:
            self.chains[record.tcname] = record
            try:
                record_text = record.render()
                linter_results = (pytmc.linter.lint_db(dbd, record_text)
                                  if dbd and record_text else None)
                record_text = _annotate_record_text(linter_results,
                                                    record_text)
            except Exception as ex:
                record_text = (
                    f'!! Linter failure: {ex.__class__.__name__} {ex}'
                    f'\n\n{record_text}'
                )
                logger.exception('Linter failure')

            self.records[record] = record_text

        self.setWindowTitle(f'pytmc-debug summary - {tmc.filename}')

        self._mode = 'chains'

        # Left part of the window
        self.left_frame = QtWidgets.QFrame()
        self.left_layout = QtWidgets.QVBoxLayout()
        self.left_frame.setLayout(self.left_layout)

        self.item_view_type = QtWidgets.QComboBox()
        self.item_view_type.addItem('Chains')
        self.item_view_type.addItem('Records')
        self.item_view_type.addItem('Chains w/o Records')
        self.item_view_type.currentTextChanged.connect(self._update_view_type)
        self.item_list = QtWidgets.QListWidget()

        self.left_layout.addWidget(self.item_view_type)
        self.left_layout.addWidget(self.item_list)

        # Right part of the window
        self.right_frame = QtWidgets.QFrame()
        self.right_layout = QtWidgets.QVBoxLayout()
        self.right_frame.setLayout(self.right_layout)

        self.record_text = QtWidgets.QTextEdit()
        self.record_text.setFontFamily('Courier New')
        self.chain_info = QtWidgets.QListWidget()
        self.config_info = QtWidgets.QTableWidget()

        self.right_layout.addWidget(self.record_text)
        self.right_layout.addWidget(self.chain_info)
        self.right_layout.addWidget(self.config_info)

        self.frame_splitter = QtWidgets.QSplitter()
        self.frame_splitter.setOrientation(Qt.Horizontal)
        self.frame_splitter.addWidget(self.left_frame)
        self.frame_splitter.addWidget(self.right_frame)

        self.top_splitter = self.frame_splitter
        if self.exceptions:
            self.error_list = QtWidgets.QTextEdit()
            self.error_list.setReadOnly(True)

            for ex in self.exceptions:
                self.error_list.append(f'({ex.__class__.__name__}) {ex}\n')

            self.error_splitter = QtWidgets.QSplitter()
            self.error_splitter.setOrientation(Qt.Vertical)
            self.error_splitter.addWidget(self.frame_splitter)
            self.error_splitter.addWidget(self.error_list)
            self.top_splitter = self.error_splitter

        self.setCentralWidget(self.top_splitter)
        self.item_list.currentItemChanged.connect(self._item_selected)

        self.item_selected.connect(self._update_config_info)
        self.item_selected.connect(self._update_chain_info)
        self.item_selected.connect(self._update_record_text)

        self._update_item_list()

    def _item_selected(self, current, previous):
        'Slot - new list item selected'
        if current is None:
            return

        record = current.data(Qt.UserRole)
        if isinstance(record, pytmc.record.RecordPackage):
            self.item_selected.emit(record)
        elif isinstance(record, str):  # {chain: record}
            chain = record
            record = self.chains[chain]
            self.item_selected.emit(record)

    def _update_config_info(self, record):
        'Slot - update config information when a new record is selected'
        chain = record.chain

        self.config_info.clear()
        self.config_info.setRowCount(len(chain.chain))

        def add_dict_to_table(row, d):
            for key, value in d.items():
                key = str(key)
                if key not in columns:
                    columns[key] = max(columns.values()) + 1 if columns else 0
                self.config_info.setItem(
                    row, columns[key], QtWidgets.QTableWidgetItem(str(value))
                )
                if isinstance(value, dict):
                    add_dict_to_table(row, value)

        columns = {}

        items = zip(chain.config['pv'], chain.item_to_config.items())
        for row, (pv, (item, config)) in enumerate(items):
            info_dict = dict(pv=pv)
            info_dict.update({k: v for k, v in config.items() if k != 'field'})
            add_dict_to_table(row, info_dict)
            fields = config.get('field', {})
            add_dict_to_table(row, {f'field_{k}': v
                                    for k, v in fields.items()
                                    if k != 'field'}
                              )

        self.config_info.setHorizontalHeaderLabels(list(columns))
        self.config_info.setVerticalHeaderLabels(
            list(item.name for item in chain.item_to_config))

        self.config_info.setColumnCount(
            max(columns.values()) + 1
            if columns else 0
        )

    def _update_record_text(self, record):
        'Slot - update record text when a new record is selected'
        self.record_text.setText(self.records[record])

    def _update_chain_info(self, record):
        'Slot - update chain information when a new record is selected'
        self.chain_info.clear()
        for chain in record.chain.chain:
            self.chain_info.addItem(str(chain))

    def _update_view_type(self, name):
        self._mode = name.lower()
        self._update_item_list()

    def _update_item_list(self):
        self.item_list.clear()
        if self._mode == 'chains':
            items = self.chains.items()
        elif self._mode == 'records':
            items = [
                (' / '.join(_grep_record_names(db_text)) or 'Unknown', record)
                for record, db_text in self.records.items()
            ]
        elif self._mode == "chains w/o records":
            items = self.chains.items()
            logger.warning("Not Implemented")
        else:
            return
        for name, record in sorted(items,
                                   key=lambda item: item[0]):
            item = QtWidgets.QListWidgetItem(name)
            item.setData(Qt.UserRole, record)
            self.item_list.addItem(item)


def create_debug_gui(tmc, dbd=None):
    '''
    Show the results of tmc processing in a Qt gui

    Parameters
    ----------
    tmc : TmcFile, str, pathlib.Path
        The tmc file to show
    dbd : DbdFile, optional
        The dbd file to lint against
    '''

    if isinstance(tmc, (str, pathlib.Path)):
        tmc = pytmc.parser.parse(tmc)

    if dbd is not None and not isinstance(dbd, pytmc.linter.DbdFile):
        dbd = pytmc.linter.DbdFile(dbd)

    return TmcSummary(tmc, dbd)


def build_arg_parser(parser=None):
    if parser is None:
        parser = argparse.ArgumentParser()

    parser.description = DESCRIPTION
    parser.formatter_class = argparse.RawTextHelpFormatter

    parser.add_argument(
        'tmc_file', metavar="INPUT", type=str,
        help='Path to .tmc file'
    )

    parser.add_argument(
        '-d', '--dbd',
        default=None,
        type=str,
        help=('Specify an expanded .dbd file for validating fields '
              '(requires pyPDB)')
    )

    return parser


def main(tmc_file, *, dbd=None):
    app = QtWidgets.QApplication([])
    interface = create_debug_gui(tmc_file, dbd)
    interface.show()
    sys.exit(app.exec_())
