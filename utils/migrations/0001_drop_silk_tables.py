from django.db import migrations

# django-silk was removed from INSTALLED_APPS (it was profiling 100% of
# production requests with the binary function profiler, causing the
# performance problems it was meant to help diagnose). Its tables are
# orphaned now that the app is gone, so drop them directly by name rather
# than through the ORM. IF EXISTS makes this a no-op on any environment
# that never had silk migrated (e.g. a fresh database).
DROP_SILK_TABLES_SQL = """
DROP TABLE IF EXISTS silk_profile_queries CASCADE;
DROP TABLE IF EXISTS silk_profile CASCADE;
DROP TABLE IF EXISTS silk_response CASCADE;
DROP TABLE IF EXISTS silk_sqlquery CASCADE;
DROP TABLE IF EXISTS silk_request CASCADE;
"""


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql=DROP_SILK_TABLES_SQL,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
