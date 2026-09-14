from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("afval", "0006_containerlocation_container_search_trgm"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="lediging",
            index=models.Index(
                fields=["klant", "geleegd_op_datum"], name="lediging_klant_datum_idx"
            ),
        ),
    ]
