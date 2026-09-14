# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo import fields

from .common import TestFieldNoCacheCommon
from .models.models import FakeModelNoCache


class TestFieldNoCache(TestFieldNoCacheCommon):
    """Tests for fields declared with ``nocache=True``.

    These tests validate:

        1- attribute rules: must be computed/related, cannot be stored, cannot have an
           inverse method
        2- dependency behavior: no registered dependencies, interactions with cached
           fields
        3- related-field semantics
        4- the ORM cache interactions: values are ignored/cleared so every access
           recomputes or resolves the value
    """

    def assertInCache(self, record, field):
        self.assertTrue(self.env.cache.contains(record, field))

    def assertNotInCache(self, record, field):
        self.assertFalse(self.env.cache.contains(record, field))

    # Field definition

    def test_nocache_is_false_by_default(self):
        """Ensures field attribute ``nocache`` is ``False`` by default"""
        field = self.env["fake.model.nocache"]._fields["value"]
        self.assertFalse(field.nocache)

    # Attributes validation for nocache

    def test_nocache_must_be_computed_or_related(self):
        """Ensures a nocache field without compute or related attrs raises error"""
        field = fields.Integer(nocache=True)
        with self.assertRaisesRegex(ValueError, r"must be computed or related"):
            field._get_attrs(FakeModelNoCache, "invalid")

    def test_nocache_cannot_be_stored(self):
        """Ensures a computed, nocache field cannot be stored"""
        field = fields.Integer(compute="_compute_invalid", store=True, nocache=True)
        with self.assertRaisesRegex(ValueError, r"can't be stored"):
            field._get_attrs(FakeModelNoCache, "invalid")

    def test_nocache_cannot_have_inverse(self):
        """Ensures a computed, nocache field cannot be inversed"""
        field = fields.Integer(
            compute="_compute_invalid", inverse="_inverse_invalid", nocache=True
        )
        with self.assertRaisesRegex(ValueError, r"can't be inversed"):
            field._get_attrs(FakeModelNoCache, "invalid")

    def _test_nocache_attrs(self, field: fields.Field):
        self.assertTrue(field.nocache)
        self.assertFalse(field.store)
        self.assertFalse(field.default)
        self.assertFalse(field.prefetch)
        self.assertFalse(field.recursive)
        self.assertFalse(field.required)
        self.assertFalse(field._depends)
        self.assertFalse(field._depends_context)

    def test_computed_nocache_field_attributes(self):
        """Checks computed, nocache fields overridden attributes"""
        field = self.env["fake.model.nocache"]._fields["nocache_computed"]
        self.assertTrue(field.compute)
        self._test_nocache_attrs(field)

    def test_related_nocache_field(self):
        """Checks related, nocache fields overridden attributes"""
        field = self.env["fake.model.nocache"]._fields["nocache_related"]
        self.assertTrue(field.related)
        self._test_nocache_attrs(field)

    # Dependency registration and resolution

    def test_dependencies_of_nocache_field_are_empty(self):
        """Ensures nocache fields don't contribute to registry dependencies"""
        model, registry = self.env["fake.model.nocache"], self.env.registry
        for field in model._fields.values():
            if field.nocache:
                self.assertEqual(field.get_depends(model), ((), ()))
                self.assertFalse(next(field.resolve_depends(registry), None))

    def test_cached_field_cannot_depend_on_nocache_field(self):
        """Ensures cached fields can't depend on nocache fields"""
        model, registry = self.env["fake.model.nocache"], self.env.registry
        for fname in ("cached_computed", "cached_related"):
            field = model._fields[fname]
            original = registry.field_depends[field]
            registry.field_depends[field] = ["nocache_computed"]
            try:
                with self.assertRaisesRegex(ValueError, r"Invalid .* dependency"):
                    list(field.resolve_depends(registry))
            finally:
                registry.field_depends[field] = original

    def test_cached_related_field_cannot_depend_on_nocache_field(self):
        """Ensures related, cached fields cannot depend on nocache fields"""
        field = fields.Integer(related="nocache_computed")
        field._setup_attrs__(FakeModelNoCache, "invalid_related")
        with self.assertRaisesRegex(ValueError, r"not cached.*related="):
            field.setup_related(self.env["fake.model.nocache"])

    def test_related_nocache_cannot_become_reversible(self):
        """Ensures related, reversible fields cannot depend on nocache fields"""
        # NB: ``value`` is a non-computed, non-related field, but ``readonly=False``
        # will automatically assign the newly defined related field an inverse method
        field = fields.Integer(related="value", nocache=True, readonly=False)
        field._setup_attrs__(FakeModelNoCache, "invalid_related")
        with self.assertRaisesRegex(ValueError, r"can't be inversed"):
            field.setup_related(self.env["fake.model.nocache"])

    # Field behavior for nocache fields

    def test_compute_triggered_on_every_access_except_if_protected(self):
        """Reading nocache computed fields triggers the compute methods on every read

        The only exception must be if the field is being protected by the current
        transaction: in that case, the compute method should not be called.
        """
        record = self.env["fake.model.nocache"].create({"value": 42})
        with patch.object(
            FakeModelNoCache,
            "_compute_nocache_computed",
            autospec=True,
            wraps=FakeModelNoCache,
            side_effect=FakeModelNoCache._compute_nocache_computed,
        ) as mock_method:
            self.assertEqual(mock_method.call_count, 0)
            record.read(["nocache_computed"])
            self.assertEqual(mock_method.call_count, 1)
            record.read(["nocache_computed"])
            self.assertEqual(mock_method.call_count, 2)
            with self.env.protecting([record._fields["nocache_computed"]], record):
                record.read(["nocache_computed"])
            self.assertEqual(mock_method.call_count, 2)  # Still same count

    def test_related_triggered_on_every_access_except_if_protected(self):
        """Reading nocache related fields triggers the compute methods on every read

        The only exception must be if the field is being protected by the current
        transaction: in that case, the related method should not be called.
        """
        record = self.env["fake.model.nocache"].create({"value": 42})
        field = record._fields["nocache_related"]
        with patch.object(
            field,
            "compute",
            autospec=True,
            wraps=field,
            side_effect=field.compute,
        ) as mock_method:
            self.assertEqual(mock_method.call_count, 0)
            record.read(["nocache_related"])
            self.assertEqual(mock_method.call_count, 1)
            record.read(["nocache_related"])
            self.assertEqual(mock_method.call_count, 2)
            with self.env.protecting([record._fields["nocache_related"]], record):
                record.read(["nocache_related"])
            self.assertEqual(mock_method.call_count, 2)  # Still same count

    # Getter and cache interaction

    def test_computed_field_existing_cache_is_ignored(self):
        """Ensures cache is ignored when reading nocache, computed fields"""
        record = self.env["fake.model.nocache"].create({"value": 42})
        self.env.cache.set(record, record._fields["nocache_computed"], 999)
        self.assertEqual(record.nocache_computed, 42)

    def test_computed_field_cache_is_empty_after_access(self):
        """Ensures cache is cleared after reading nocache, computed fields"""
        record = self.env["fake.model.nocache"].create({"value": 42})
        record.read(["nocache_computed"])
        self.assertNotInCache(record, record._fields["nocache_computed"])

    def test_related_field_existing_cache_is_ignored(self):
        """Ensures cache is ignored when reading nocache, related fields"""
        record = self.env["fake.model.nocache"].create({"value": 42})
        self.env.cache.set(record, record._fields["nocache_related"], 999)
        self.assertEqual(record.nocache_related, 42)

    def test_related_field_cache_is_empty_after_access(self):
        """Ensures cache is cleared after reading nocache, related fields"""
        record = self.env["fake.model.nocache"].create({"value": 42})
        record.read(["nocache_related"])
        self.assertNotInCache(record, record._fields["nocache_related"])

    def test_nocache_siblings_are_not_left_in_cache(self):
        """Ensures shared compute methods do not leave values in the ORM cache"""
        record = self.env["fake.model.nocache"].create({"value": 10})
        self.assertNotInCache(record, record._fields["nocache_first"])
        self.assertNotInCache(record, record._fields["nocache_second"])
        self.assertEqual(record.nocache_first, 11)
        self.assertNotInCache(record, record._fields["nocache_first"])
        self.assertNotInCache(record, record._fields["nocache_second"])
        self.assertEqual(record.nocache_second, 12)
        self.assertNotInCache(record, record._fields["nocache_first"])
        self.assertNotInCache(record, record._fields["nocache_second"])
