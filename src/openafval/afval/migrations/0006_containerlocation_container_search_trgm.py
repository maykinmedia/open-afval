import django.contrib.postgres.indexes
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("afval", "0005_alter_container_afval_type"),
    ]

    operations = [
        TrigramExtension(),
        migrations.AddIndex(
            model_name="containerlocation",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["adres"],
                name="containerlocation_adres_trgm",
                opclasses=["gin_trgm_ops"],
            ),
        ),
        migrations.AddIndex(
            model_name="container",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["public_container_id"],
                name="container_public_id_trgm",
                opclasses=["gin_trgm_ops"],
            ),
        ),
    ]
