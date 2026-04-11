import html
import re
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from django.db import migrations


TIME_ZONE = ZoneInfo("Asia/Tokyo")


def clean_text(value):
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"<br\s*/?>", "\n", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"<[^>]+>", "", normalized)
    normalized = html.unescape(normalized).replace("\xa0", " ")
    lines = [line.strip() for line in normalized.split("\n")]
    return "\n".join(line for line in lines if line)


def parse_legacy_article(file_path):
    raw = file_path.read_text(encoding="utf-8")

    date_match = re.search(
        r'<time class="news-detail-date" datetime="([0-9-]+)">',
        raw,
    )
    title_match = re.search(r"<h2>(.*?)</h2>", raw, flags=re.DOTALL)
    content_match = re.search(
        r'<p class="news-detail-lead">(.*?)</p>',
        raw,
        flags=re.DOTALL,
    )

    if not (date_match and title_match and content_match):
        raise ValueError(f"Could not parse legacy news article: {file_path}")

    published_date = datetime.strptime(date_match.group(1), "%Y-%m-%d").date()
    published_at = datetime.combine(published_date, time(hour=12), tzinfo=TIME_ZONE)

    return {
        "title": clean_text(title_match.group(1)),
        "content": clean_text(content_match.group(1)),
        "published_at": published_at,
        "created_at": published_at,
        "updated_at": published_at,
    }


def import_legacy_news_articles(apps, schema_editor):
    NewsArticle = apps.get_model("nishimuraya", "NewsArticle")
    template_dir = (
        Path(__file__).resolve().parents[2]
        / "templates"
        / "nishimuraya"
        / "news"
    )

    for file_path in sorted(template_dir.glob("*.html")):
        article_data = parse_legacy_article(file_path)
        existing_article = NewsArticle.objects.filter(
            title=article_data["title"],
            published_at__date=article_data["published_at"].date(),
        ).first()

        if existing_article:
            continue

        article = NewsArticle.objects.create(
            title=article_data["title"],
            content=article_data["content"],
            image=None,
            published_at=article_data["published_at"],
            is_published=True,
        )
        NewsArticle.objects.filter(pk=article.pk).update(
            created_at=article_data["created_at"],
            updated_at=article_data["updated_at"],
        )


class Migration(migrations.Migration):
    dependencies = [
        ("nishimuraya", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            import_legacy_news_articles,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
