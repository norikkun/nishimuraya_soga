from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nishimuraya", "0002_import_legacy_news_articles"),
    ]

    operations = [
        migrations.AlterField(
            model_name="newsarticle",
            name="is_published",
            field=models.BooleanField(default=False, verbose_name="公開中"),
        ),
        migrations.AlterField(
            model_name="newsarticle",
            name="published_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True, verbose_name="公開日時"),
        ),
    ]
