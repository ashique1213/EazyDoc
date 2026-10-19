from django.db import migrations


def apply_postgres_exclusion_constraint(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")
        cursor.execute("""
            ALTER TABLE appointments_appointment
            ADD CONSTRAINT prevent_overlapping_doctor_appointments
            EXCLUDE USING gist (
                doctor_id WITH =,
                tstzrange(start_at, end_at, '[)') WITH &&
            ) WHERE (status IN ('CONFIRMED', 'PENDING_CONFIRMATION', 'COMPLETED'));
        """)


def remove_postgres_exclusion_constraint(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE appointments_appointment
            DROP CONSTRAINT IF EXISTS prevent_overlapping_doctor_appointments;
        """)


class Migration(migrations.Migration):
    dependencies = [
        ("appointments", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            apply_postgres_exclusion_constraint,
            remove_postgres_exclusion_constraint,
        ),
    ]
