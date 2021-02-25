from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0004_tenant_allowed_client_origins"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="max_channel_count",
            field=models.IntegerField(default=-1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="tenant",
            name="max_sku_count",
            field=models.IntegerField(default=-1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="tenant",
            name="max_staff_user_count",
            field=models.IntegerField(default=-1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="tenant",
            name="max_warehouse_count",
            field=models.IntegerField(default=-1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="tenant",
            name="project_id",
            field=models.IntegerField(default=-1),
            preserve_default=False,
        ),
    ]
