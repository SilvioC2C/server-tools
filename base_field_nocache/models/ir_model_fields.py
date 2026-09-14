# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import fields, models


class IrModelFields(models.Model):
    _inherit = "ir.model.fields"

    nocache = fields.Boolean()

    def _reflect_field_params(self, field, model_id):
        # OVERRIDE: set ``nocache`` from ``fields.Field`` object to ``ir.model.fields``
        values = super()._reflect_field_params(field, model_id)
        values["nocache"] = field.nocache
        return values

    def _instanciate_attrs(self, field_data):
        # OVERRIDE: set ``nocache`` from ``ir.model.fields`` to ``fields.Field`` object
        attrs = super()._instanciate_attrs(field_data)
        attrs["nocache"] = bool(field_data.get("nocache"))
        return attrs
