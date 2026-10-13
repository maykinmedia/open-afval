from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("afval", "0010_lediging_gewicht_decimal"),
    ]

    operations = [
        migrations.AlterField(
            model_name="container",
            name="afval_type",
            field=models.CharField(
                help_text="Het type afval dat de container bevat",
                max_length=255,
                verbose_name="afvaltype",
            ),
        ),
    ]
