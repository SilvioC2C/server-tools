# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import functools
import warnings

from odoo.orm import registry

from .utils import monkey_patch

# --------------------------------------------------------------------------------------
# Computed fields check
# --------------------------------------------------------------------------------------


@monkey_patch(registry.Registry)
def field_computed(self):
    # OVERRIDE: log a warning if a compute method sets values for both cached and
    # non-cached fields
    computed = field_computed.super.func(self)
    for field, fields in computed.items():
        if len(set(f.nocache for f in fields)) != 1:
            fnames1 = ", ".join(f.name for f in fields if not f.nocache)
            fnames2 = ", ".join(f.name for f in fields if f.nocache)
            warnings.warn(
                f"{field.model_name}: inconsistent 'nocache' for fields,"
                f" accessing {fnames1} may recompute and update {fnames2}."
                f" Use distinct compute methods for cached and non-cached fields.",
                stacklevel=1,
            )
    return computed


# ``monkey_patch()`` replaced the ``@functools.cached_property`` wrapper: restore it
_field_computed = functools.cached_property(field_computed)
_field_computed.__set_name__(registry.Registry, "field_computed")
registry.Registry.field_computed = _field_computed
