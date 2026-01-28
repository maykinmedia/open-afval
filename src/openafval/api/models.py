import binascii
import os

from django.db import models
from django.utils.translation import gettext_lazy as _

from phonenumber_field.modelfields import PhoneNumberField


class Application(models.Model):  # noqa: DJ008
    token = models.CharField(_("token"), max_length=40)
    contact_person = models.CharField(
        _("contact person"),
        max_length=200,
        help_text=_(
            "Name of the person to contact about this application and the associated credentials."
        ),
        blank=True,
    )
    email = models.EmailField(
        _("email"),
        help_text=_(
            "Email of the person to contact about this application and the associated credentials."
        ),
        blank=True,
    )
    phone_number = PhoneNumberField(
        _("phone number"),
        help_text=_(
            "Phonenumber of the person contact about this application and the "
            "associated credentials."
        ),
        blank=True,
    )
    last_modified = models.DateTimeField(
        _("last modified"),
        auto_now=True,
        help_text=_("Last date when the token was modified"),
    )
    created = models.DateTimeField(
        _("created"), auto_now_add=True, help_text=_("Date when the token was created")
    )

    class Meta:
        verbose_name = _("application API key")
        verbose_name_plural = _("application API keys")

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_token()
        return super().save(*args, **kwargs)

    def generate_token(self):
        return binascii.hexlify(os.urandom(20)).decode()
