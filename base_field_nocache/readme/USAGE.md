Computed and related fields can be declared with ``nocache=True``.


    from odoo import fields, models


    class MyModel(models.Model):
        _name = "my.model"

        source = fields.Integer()
        computed = fields.Integer(compute="_compute_computed", nocache=True)
        related = fields.Integer(related="source", nocache=True)

        # NB: no need for ``@api.depends()`` on nocache fields:
        # dependencies are ignored anyway
        def _compute_computed(self):
            for record in self:
                record.computed = record.source


For ordinary fields (``nocache=False``), Odoo's normal field behavior is preserved.

For fields declared with ``nocache=True``:

* the field must be computed or related;
* the field must not be stored;
* the field cannot have an inverse method;
* a cached value is removed before the normal field getter runs;
* the value produced by the normal getter is removed from the cache again before
  returning to the caller;
* consequently, every field access recomputes/resolves the value;
* the field contributes no dependencies to the registry;
* a cached, computed field cannot depend on a nocache field;
* a cached, related field cannot traverse a nocache field.

The cache is only used temporarily while Odoo's normal computation machinery runs.
The module does not call the compute method directly, so Odoo's regular compute and
dependency machinery remain in use.

There is one intentional consequence of using Odoo's normal computation machinery:
Odoo can protect fields while a compute method is running. A ``nocache`` field accessed
while it is protected follows Odoo's normal protection semantics rather than
recursively forcing another computation.

A nocache field must be non-stored, and either computed or related. The following
fields are invalid:

    # Not computed nor related
    value = fields.Integer(nocache=True)
    # Computed/related and stored
    computed = fields.Integer(compute="_compute_computed", nocache=True, store=True)
    related = fields.Integer(related="value", nocache=True, store=True)

A non-cached field cannot have an inverse method:

    # This declaration raises a ``ValueError``
    value = fields.Integer(
        compute="_compute_value",
        inverse="_inverse_value",
        nocache=True,
    )


A non-cached field has no registered dependencies because its value is never
retained in the ORM cache.

Conversely, a cached field must not depend on a non-cached field.

For example, the following computed and related fields will trigger a ``ValueError``:

    value_nocache = fields.Integer(compute="_compute_value_nocache", nocache=True)
    value_computed_cached = fields.Integer(compute="_compute_value_cached")
    value_related_cached = fields.Integer(related="value_nocache")

    def _compute_value_nocache(self):
        ...

    @api.depends("value_nocache")
    def _compute_value_cached(self):
        ...

