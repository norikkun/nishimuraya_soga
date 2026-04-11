from django.contrib import admin

from .models import NewsArticle


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "published_at", "is_published", "created_at")
    list_filter = ("is_published", "published_at")
    search_fields = ("title", "content")
    ordering = ("-published_at", "-id")
    readonly_fields = ("published_at", "created_at", "updated_at", "url_segment_display")
    fields = (
        "title",
        "content",
        "image",
        "published_at",
        "is_published",
        "url_segment_display",
        "created_at",
        "updated_at",
    )

    @admin.display(description="URL識別子")
    def url_segment_display(self, obj):
        return obj.url_segment or "-"
