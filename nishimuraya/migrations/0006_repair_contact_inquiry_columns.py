# Generated manually to align older contact inquiry tables with the current model.

from django.db import migrations


def repair_contact_inquiry_columns(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    schema_editor.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'nishimuraya_contactinquiry'
                  AND column_name = 'is_handled'
            ) THEN
                ALTER TABLE nishimuraya_contactinquiry
                    ADD COLUMN is_handled boolean;
            END IF;

            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'nishimuraya_contactinquiry'
                  AND column_name = 'is_confirmed'
            ) THEN
                UPDATE nishimuraya_contactinquiry
                SET is_handled = is_confirmed
                WHERE is_handled IS NULL;
            END IF;

            UPDATE nishimuraya_contactinquiry
            SET is_handled = false
            WHERE is_handled IS NULL;

            ALTER TABLE nishimuraya_contactinquiry
                ALTER COLUMN is_handled SET DEFAULT false;
            ALTER TABLE nishimuraya_contactinquiry
                ALTER COLUMN is_handled SET NOT NULL;

            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'nishimuraya_contactinquiry'
                  AND column_name = 'handled_at'
            ) THEN
                ALTER TABLE nishimuraya_contactinquiry
                    ADD COLUMN handled_at timestamp with time zone NULL;
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'nishimuraya_contactinquiry'
                  AND column_name = 'updated_at'
            ) THEN
                ALTER TABLE nishimuraya_contactinquiry
                    ADD COLUMN updated_at timestamp with time zone;
            END IF;

            UPDATE nishimuraya_contactinquiry
            SET updated_at = created_at
            WHERE updated_at IS NULL;

            ALTER TABLE nishimuraya_contactinquiry
                ALTER COLUMN updated_at SET NOT NULL;

            IF NOT EXISTS (
                SELECT 1
                FROM pg_indexes
                WHERE tablename = 'nishimuraya_contactinquiry'
                  AND indexdef LIKE '%(is_handled)%'
            ) THEN
                CREATE INDEX nishimuraya_contactinquiry_is_handled_idx
                    ON nishimuraya_contactinquiry (is_handled);
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM pg_indexes
                WHERE tablename = 'nishimuraya_contactinquiry'
                  AND indexdef LIKE '%(created_at)%'
            ) THEN
                CREATE INDEX nishimuraya_contactinquiry_created_at_idx
                    ON nishimuraya_contactinquiry (created_at);
            END IF;

            ALTER TABLE nishimuraya_contactinquiry
                DROP COLUMN IF EXISTS is_confirmed;
            ALTER TABLE nishimuraya_contactinquiry
                DROP COLUMN IF EXISTS gmail_last_synced_at;
            ALTER TABLE nishimuraya_contactinquiry
                DROP COLUMN IF EXISTS gmail_thread_id;
        END $$;
        """
    )


class Migration(migrations.Migration):

    dependencies = [
        ("nishimuraya", "0005_contactinquiry"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    repair_contact_inquiry_columns,
                    reverse_code=migrations.RunPython.noop,
                ),
            ],
            state_operations=[],
        ),
    ]
