This module adds a ``nocache`` attribute to Odoo fields.

The attribute can be used when a computed or related field must always be resolved at
access time, and its value should not linger in the Odoo ORM's cache long after being
read.
