from django.db import models
from django.urls import reverse
from django.utils import timezone


class ContactInquiry(models.Model):
    name = models.CharField("お名前", max_length=100)
    email = models.EmailField("メールアドレス")
    phone = models.CharField("電話番号", max_length=30, blank=True)
    message = models.TextField("お問い合わせ内容")
    is_handled = models.BooleanField("対応済み", default=False, db_index=True)
    handled_at = models.DateTimeField("対応日時", blank=True, null=True)
    created_at = models.DateTimeField("受付日時", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        verbose_name = "問い合わせ"
        verbose_name_plural = "問い合わせ"
        ordering = ["is_handled", "-created_at", "-id"]

    def __str__(self) -> str:
        created_at = f"{self.created_at:%Y-%m-%d %H:%M}" if self.created_at else "未保存"
        return f"{self.name} / {created_at}"

    @property
    def status_label(self) -> str:
        return "対応済み" if self.is_handled else "未対応"

    @property
    def status_css_class(self) -> str:
        return "is-handled" if self.is_handled else "is-pending"

    @property
    def phone_display(self) -> str:
        return self.phone or "未入力"

    def get_absolute_url(self) -> str:
        return reverse("contact_inquiry_detail", kwargs={"pk": self.pk})

    def set_handled(self, handled: bool) -> None:
        self.is_handled = handled
        self.handled_at = timezone.now() if handled else None
        self.save(update_fields=["is_handled", "handled_at", "updated_at"])
