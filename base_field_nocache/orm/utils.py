# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# Copied as-is from Odoo's ``base_sparse_field/models/fields.py``
def monkey_patch(cls):
    """Return a method decorator to monkey-patch the given class."""

    def decorate(func):
        name = func.__name__
        func.super = getattr(cls, name)
        setattr(cls, name, func)
        return func

    return decorate
