# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from .common import TestFieldNoCacheCommon


class TestIrModelFieldsNoCache(TestFieldNoCacheCommon):
    """Tests for ``ir.model.fields`` records declared with ``nocache=True``"""

    def _get(self, model_name: str, field_name: str | None = None):
        if field_name is None:
            return self.env["ir.model"]._get(model_name)
        return self.env["ir.model.fields"]._get(model_name, field_name)

    def test_ir_model_fields_nocache_from_field(self):
        """Check ``ir.model.fields`` correctly mirrors ``fields.Field.nocache``"""
        model_name, field_name = "fake.model.nocache", "nocache_computed"
        imf = self._get(model_name, field_name)
        self.assertTrue(imf.nocache)

    def test_field_nocache_from_ir_model_fields(self):
        """Check ``fields.Field.nocache`` correctly mirrors ``ir.model.fields``"""
        model_name, field_name = "fake.model.nocache", "x_nocache_computed"
        imf = self.env["ir.model.fields"].create(
            {
                "model_id": self._get(model_name).id,
                "name": field_name,
                "field_description": field_name,
                "state": "manual",
                "nocache": True,
                "store": False,
                "ttype": "integer",
                "compute": "for rec in self: rec.x_nocache_computed = 10",
            }
        )
        # NB: ``ir.model.fields.write()`` doesn't update existing fields, but generates
        # new fields with updated attributes that replace the ones that exist already;
        # therefore, after the ``write()`` occurs, we need to access the ``_fields``
        # attribute again to make sure we get the newest field
        model = self.env[model_name]
        self.assertTrue(model._fields[field_name].nocache)
        imf.nocache = False
        self.assertFalse(model._fields[field_name].nocache)
