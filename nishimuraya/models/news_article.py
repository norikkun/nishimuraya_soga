from django.db import models
from django.urls import reverse
from django.utils import timezone

from ..storages import news_static_image_storage


class NewsArticle(models.Model):
    title = models.CharField("タイトル", max_length=200)
    content = models.TextField("内容")
    image = models.ImageField(
        "写真",
        storage=news_static_image_storage,
        upload_to="news/",
        blank=True,
        null=True,
        help_text="写真がない記事は空のままで登録できます。",
    )
    published_at = models.DateTimeField("公開日時", blank=True, null=True, db_index=True)
    is_published = models.BooleanField("公開中", default=False)
    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        verbose_name = "お知らせ"
        verbose_name_plural = "お知らせ"
        ordering = ["-published_at", "-id"]

    def __str__(self) -> str:
        return self.title

    @property
    def status_label(self) -> str:
        return "公開中" if self.is_published else "下書き"

    @property
    def url_segment(self) -> str:
        if self.pk is None or self.created_at is None:
            return ""

        created_at = (
            timezone.localtime(self.created_at)
            if timezone.is_aware(self.created_at)
            else self.created_at
        )
        return f"{created_at:%Y%m%d}-{self.pk}"

    def get_absolute_url(self) -> str:
        return reverse("news_detail", kwargs={"url_key": self.url_segment})

    def save(self, *args, **kwargs):
        if self.is_published:
            if self.published_at is None:
                self.published_at = timezone.now()
        else:
            self.published_at = None
        super().save(*args, **kwargs)
