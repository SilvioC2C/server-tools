# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo.orm import fields

from .utils import monkey_patch

_logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------------------
# Field definition
# --------------------------------------------------------------------------------------

# Make ``nocache`` a real Field attribute so that it is accepted by
# ``Field._get_attrs()`` and participates in inherited field definitions.
fields.Field.nocache = False


# --------------------------------------------------------------------------------------
# Field attributes validation
# --------------------------------------------------------------------------------------


@monkey_patch(fields.Field)
def _get_attrs(self, model_class, name):
    # OVERRIDE: raise errors on hard inconsistencies, override attributes on soft ones
    # (and log what happens in that case)
    attrs = _get_attrs.super(self, model_class, name)
    if attrs.get("nocache"):
        # Hard inconsistencies => raise error asap
        # We won't override these attributes, as they may end up in silent errors, e.g.:
        # we could override ``inverse=None`` on non-cached fields, but somewhere
        # in the code we may have ``self.non_cached_field = some_value`` and expect that
        # line to trigger the ``inverse`` method, only to find out nothing was ever
        # triggered. Better to have a breaking error at startup than a hard-to-debug
        # silent error at runtime.
        errors = []
        if not (attrs.get("compute") or attrs.get("related")):
            errors.append("must be computed or related")
        if attrs.get("store"):
            errors.append("can't be stored")
        if attrs.get("inverse"):
            errors.append("can't be inversed")
        if errors:
            if len(errors) > 1:
                errors[-1] = f"and {errors[-1]}"
            err_msg = ", ".join(errors)
            raise ValueError(f"Invalid non-cached field definition: {self} {err_msg}.")
        # Soft overrides => force-clear + warn to keep declared attrs truthful
        # These attributes make no sense on non-cached fields.
        for attribute, value in [
            ("default", None),
            ("prefetch", False),
            ("recursive", False),
            ("required", False),
            ("_depends", ()),
            ("_depends_context", ()),
        ]:
            if (old_value := attrs.get(attribute)) not in (value, None):
                _logger.warning(
                    f"Overriding non-cached field {self} attribute '{attribute}' from"
                    f" '{old_value}' to '{value}'."
                )
                attrs[attribute] = value
    return attrs


# --------------------------------------------------------------------------------------
# Dependencies setup, validation and resolution
# --------------------------------------------------------------------------------------


# ``get_depends()`` is used at model setup to build registry's ``field_depends``
# and ``field_depends_context`` attributes
@monkey_patch(fields.Field)
def get_depends(self, model):
    # OVERRIDE: non-cached fields have no dependencies (prevent redundant cache
    # invalidation for fields that already have no cached values)
    return ((), ()) if self.nocache else get_depends.super(self, model)


# ``resolve_depends()`` is used by the registry to create the fields' trigger trees
# that are parsed by models' ``_modified()``
@monkey_patch(fields.Field)
def resolve_depends(self, registry):
    # OVERRIDE: non-cached fields can't be declared as dependencies for cached fields,
    # and they themselves should have no dependency
    if not self.nocache:
        for field_seq in resolve_depends.super(self, registry):
            for field in field_seq:
                if field.nocache:
                    path = ".".join(f.name for f in field_seq)
                    raise ValueError(
                        f"Invalid {self} dependency: {field} (in '{path}') is not"
                        f" cached, but {self} is."
                    )
            yield field_seq


# --------------------------------------------------------------------------------------
# Related fields
# --------------------------------------------------------------------------------------


@monkey_patch(fields.Field)
def setup_related(self, model):
    # OVERRIDE: related fields checks
    setup_related.super(self, model)

    # Related fields can acquire an inverse field in ``Field.setup_related()`` when
    # ``readonly=False``; this cannot be detected in ``_get_attrs()``, where an explicit
    # inverse field is the only one visible
    if self.nocache and self.inverse:
        raise ValueError(
            f"Invalid non-cached field definition: {self} can't be inversed."
        )

    # Check that cached, related fields do not depend on non-cached fields
    if not self.nocache:
        model_name = self.model_name
        for name in self.related.split("."):
            field = model.pool[model_name]._fields[name]
            if field.nocache:
                raise ValueError(
                    f"Invalid {self} related field: {field} is not cached "
                    f"(used in 'related={self.related}')."
                )
            model_name = field.comodel_name


# --------------------------------------------------------------------------------------
# Getter
# --------------------------------------------------------------------------------------


@monkey_patch(fields.Field)
def __get__(self, record, owner=None):
    # OVERRIDE: make sure to remove non-cached fields' values from the cache before and
    # after getter is called
    if not (self.nocache and record):
        return __get__.super(self, record, owner)
    # We fetch all records to prefetch to make sure the cache contains no info at all
    # about this field
    records = record | self._to_prefetch(record)
    records.invalidate_recordset([self.name])
    try:
        return __get__.super(self, record, owner)
    finally:
        # NB: 2 (or more) non-cached fields might be recomputed by the same compute
        # method; if that happens, we need to invalidate the cache of them all to
        # prevent inconsistent behaviors
        fields_with_same_compute_method = records.env.registry.field_computed[self]
        if self not in fields_with_same_compute_method:
            fields_with_same_compute_method.insert(0, self)
        for field in fields_with_same_compute_method:
            if field.nocache:
                records.invalidate_recordset([field.name])
