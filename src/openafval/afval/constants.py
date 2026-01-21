from django.db import models
from django.utils.translation import gettext_lazy as _


class AfvalTypeChoices(models.TextChoices):
    GFT = "gft", _("Groente, Fruit en Tuin afval (GFT)")
    RESTAFVAL = "restafval", _("Rest afval (Rest)")
