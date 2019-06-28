"""Individual EPICS Database Record creation"""
from collections import OrderedDict
from jinja2 import Environment, PackageLoader


class EPICSRecord:
    """Representation of a single EPICS Record"""
    def __init__(self, pvname, record_type, fields=None, template=None):
        self.pvname = pvname
        self.record_type = record_type
        self.fields = OrderedDict(fields) if fields is not None else {}
        self.template = template or 'asyn_standard_record.jinja2'

        # Load jinja templates
        self.jinja_env = Environment(
            loader=PackageLoader("pytmc", "templates"),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.record_template = self.jinja_env.get_template(
            self.template
        )

    def render(self):
        """Render the provided template"""
        for field, value in list(self.fields.items()):
            self.fields[field] = str(value).strip('"')

        return self.record_template.render(record=self)

    def __repr__(self):
        return f"EPICSRecord({self.pvname!r}, record_type={self.record_type!r})"
