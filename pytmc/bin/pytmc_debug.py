"""
"pytmc-debug" is a Qt interface that shows information about how pytmc
interprets TwinCAT3 .tmc files.
"""

import argparse
import logging
import sys

from qtpy import QtWidgets
from qtpy.QtCore import Qt, Signal

import pytmc
from .pytmc import process, LinterError


description = __doc__


def _grep_record_names(text):
    if not text:
        return []

    records = [line.rstrip('{')
               for line in text.splitlines()
               if line.startswith('record')
               ]

    def split_rtyp(line):
        line = line.split('record(', 1)[1].rstrip('")')
        rtyp, record = line.split(',', 1)
        record = record.strip('"\'')
        return f'{record} ({rtyp})'

    return [split_rtyp(record)
            for record in records
            ]


class TmcSummary(QtWidgets.QMainWindow):
    '''
    pytmc debug interface

    Parameters
    ----------
    tmc : TmcFile
        The tmc file to inspect
    '''

    record_selected = Signal(object)

    def __init__(self, tmc):
        super().__init__()
        self.tmc = tmc
        self.records = {record: record.render_record()
                        for record in tmc.all_RecordPackages
                        }

        self.setWindowTitle(f'pytmc-debug summary - {tmc.filename}')

        self.main_frame = QtWidgets.QFrame()
        self.layout = QtWidgets.QGridLayout()
        self.main_frame.setLayout(self.layout)
        self.setCentralWidget(self.main_frame)

        self.record_list = QtWidgets.QListWidget()
        self.layout.addWidget(self.record_list, 0, 0, 3, 1)

        self.record_text = QtWidgets.QTextEdit()
        self.record_text.setFontFamily('Courier New')
        self.layout.addWidget(self.record_text, 0, 1)

        self.chain_info = QtWidgets.QListWidget()
        self.layout.addWidget(self.chain_info, 1, 1)

        self.config_info = QtWidgets.QTableWidget()
        self.layout.addWidget(self.config_info, 2, 1)

        self.record_list.currentItemChanged.connect(
            self._item_selected)

        self.record_selected.connect(self._update_config_info)
        self.record_selected.connect(self._update_chain_info)
        self.record_selected.connect(self._update_record_text)

        self._update_records()

    def _item_selected(self, current, previous):
        'Slot - new record in list selected'
        record = current.data(Qt.UserRole)
        self.record_selected.emit(record)

    def _update_config_info(self, record):
        'Slot - update config information when a new record is selected'
        self.config_info.clear()
        self.config_info.setRowCount(len(record.cfg.config))

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
        for row, line in enumerate(record.cfg.config):
            add_dict_to_table(row, line)

        self.config_info.setHorizontalHeaderLabels(list(columns))

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

    def _update_records(self):
        self.record_list.clear()

        items = [
            (' / '.join(_grep_record_names(db_text)) or 'Unknown', record)
            for record, db_text in self.records.items()
        ]
        for names, record in sorted(items, key=lambda item: item[0]):
            item = QtWidgets.QListWidgetItem(names)
            item.setData(Qt.UserRole, record)
            self.record_list.addItem(item)


def show_qt_interface(tmc):
    '''
    Show the results of tmc processing in a Qt gui

    Parameters
    ----------
    tmc : TmcFile
        The tmc file to show
    '''

    for pkg in tmc.all_RecordPackages:
        chain = pkg.chain
        print(pkg.render_record())
        print(chain, pkg.origin_chain)
        print(pkg.cfg)
        break

    app = QtWidgets.QApplication([])
    interface = TmcSummary(tmc)
    interface.show()
    sys.exit(app.exec_())


def main():
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        'tmc_file', metavar="INPUT", type=str,
        help='Path to interpreted .tmc file'
    )

    parser.add_argument(
        '--dbd',
        '-d',
        default=None,
        type=str,
        help=('Specify an expanded .dbd file for validating fields '
              '(requires pyPDB)')
    )

    args = parser.parse_args()

    tmc = pytmc.TmcFile(args.tmc_file)

    try:
        process(tmc, dbd_file=args.dbd, allow_errors=True,
                show_error_context=True)
    except LinterError:
        ...

    show_qt_interface(tmc)


if __name__ == '__main__':
    main()
