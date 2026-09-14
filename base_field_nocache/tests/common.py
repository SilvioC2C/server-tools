# Copyright 2026 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.orm.model_classes import add_to_registry
from odoo.tests import TransactionCase


class TestFieldNoCacheCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.build_models(cls._get_models_classes_to_build())

    @classmethod
    def _get_models_classes_to_build(cls):
        from .models.models import FakeModelNoCache

        return [FakeModelNoCache]

    @classmethod
    def build_models(cls, model_classes):
        cr, ctx, registry = cls.cr, cls.env.context, cls.registry
        for model_class in model_classes:
            add_to_registry(registry, model_class)
        model_names = [m._name for m in model_classes]
        registry._setup_models__(cr, model_names)
        registry.init_models(cr, model_names, dict(ctx, models_to_check=True))
