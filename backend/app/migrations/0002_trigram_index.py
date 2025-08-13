from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("app", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS pg_trgm;"),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS app_datarow_data_trgm_idx "
            "ON app_datarow USING gin ((data::text) gin_trgm_ops);"
        ),
    ]
