from django.contrib import admin
from django.utils import timezone

from .models import ContactInquiry, NewsArticle


@admin.register(ContactInquiry)
class ContactInquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "is_handled", "created_at", "handled_at")
    list_filter = ("is_handled", "created_at", "handled_at")
    search_fields = ("name", "email", "phone", "message")
    ordering = ("is_handled", "-created_at", "-id")
    readonly_fields = ("created_at", "updated_at", "handled_at")
    fields = (
        "name",
        "email",
        "phone",
        "message",
        "is_handled",
        "handled_at",
        "created_at",
        "updated_at",
    )

    def save_model(self, request, obj, form, change):
        if "is_handled" in form.changed_data:
            obj.handled_at = timezone.now() if obj.is_handled else None
        super().save_model(request, obj, form, change)


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
