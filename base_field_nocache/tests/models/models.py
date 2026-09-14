# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class FakeModelNoCache(models.Model):
    _name = "fake.model.nocache"
    _description = "Fake model for fields' ``nocache`` attribute testing"

    # basic field
    value = fields.Integer(default=42)
    # nocache fields
    nocache_computed = fields.Integer(compute="_compute_nocache_computed", nocache=True)
    nocache_related = fields.Integer(related="value", nocache=True)
    nocache_first = fields.Integer(compute="_compute_nocache_cardinals", nocache=True)
    nocache_second = fields.Integer(compute="_compute_nocache_cardinals", nocache=True)
    # cached fields
    cached_computed = fields.Integer(compute="_compute_cached_computed", nocache=False)
    cached_related = fields.Integer(related="value", nocache=False)

    def _compute_nocache_computed(self):
        for record in self:
            record.nocache_computed = record.value

    def _compute_nocache_cardinals(self):
        for record in self:
            record.nocache_first = record.value + 1
            record.nocache_second = record.value + 2

    @api.depends("value")
    def _compute_cached_computed(self):
        for record in self:
            record.cached_computed = record.value + 3
