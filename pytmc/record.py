"""Individual EPICS Database Record creation"""
from jinja2 import Environment, PackageLoader


class EPICSRecord:
    """Representation of a single EPICS Record"""
    def __init__(self, pvname, record_type, fields=None, template=None):
        self.pvname = pvname
        self.record_type = record_type
        self.fields = dict(fields) or dict()
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

    def render_template(self):
        """Render the provided template"""
        return self.record_template.render(record=self)

    def __repr__(self):
        return f"EPICSRecord ({self.pvname}, RTYP={self.record_type})"
