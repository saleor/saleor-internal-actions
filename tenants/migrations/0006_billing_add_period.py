from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0005_billing_limitations"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="allowance_period",
            field=models.CharField(max_length=20, default="monthly"),
            preserve_default=False,
        ),
    ]
