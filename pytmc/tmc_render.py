'''
tmc_render.py

This file contains the tools for recursively exploring the TwinCAT program
structure, parsing relevant pragmas and rendering the resulting EPICS db file.
'''
import logging
logger = logging.getLogger(__name__)
from jinja2 import Environment, PackageLoader, select_autoescape
import re

class SingleRecordData:
    def __init__(self, pv=None, rec_type=None, fields=None):
        self.pv = pv 
        self.rec_type = rec_type
        self.fields = fields

    def add(self, pv_extra):
        pv_extra = pv_extra.strip(" :")
        self.pv = self.pv + ":" + pv_extra

    @property
    def check_pv(self):
        return True
        

    @property
    def check_rec_type(self):
        return True

    @property
    def check_fields(self):
        return True

    @property
    def check(self):
        return check_pv and check_rec_type and check_fields

class DbRenderAgent:
    def __init__(self, master_list=None, loader=("pytmc","templates"),
                template="EPICS_record_template.db"):
        if master_list == None:
            master_list = []
        self.master_list = master_list
        self.jinja_env = Environment(
            loader = PackageLoader(*loader)
        )
        self.template = self.jinja_env.get_template(template)
