from django.db import migrations, models
from django.db.models.functions import Cast


def set_public_container_id_from_uuid(apps, schema_editor):
    Container = apps.get_model("afval", "Container")
    Container.objects.update(
        public_container_id=Cast("id", output_field=models.CharField(max_length=64))
    )


class Migration(migrations.Migration):
    dependencies = [
        ("afval", "0002_lediging_kosten"),
    ]

    operations = [
        migrations.AddField(
            model_name="container",
            name="public_container_id",
            field=models.CharField(
                blank=True,
                help_text="De externe container-ID zoals bij de leverancier bekend is.",
                max_length=64,
                verbose_name="public container ID",
            ),
        ),
        migrations.RunPython(
            set_public_container_id_from_uuid,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
