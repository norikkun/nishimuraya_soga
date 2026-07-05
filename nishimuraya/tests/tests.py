from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from nishimuraya.models import ContactInquiry, NewsArticle


class StaffUserMixin:
    staff_password = "StrongPass123"

    def create_staff_user(self, username="site-admin"):
        return get_user_model().objects.create_user(
            username=username,
            password=self.staff_password,
            is_staff=True,
            is_superuser=True,
        )

    def login_staff_user(self, username="site-admin"):
        user = self.create_staff_user(username=username)
        self.client.force_login(user)
        return user


class HomePageTests(StaffUserMixin, TestCase):
    def test_home_page_renders(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "nishimuraya/home.html")

    def test_home_page_shows_latest_four_published_articles(self):
        for day in range(1, 7):
            NewsArticle.objects.create(
                title=f"公開記事{day}",
                content="本文",
                published_at=timezone.make_aware(datetime(2026, 4, day, 12, 0)),
                is_published=True,
            )

        NewsArticle.objects.create(
            title="非公開記事",
            content="本文",
            published_at=timezone.make_aware(datetime(2026, 4, 30, 12, 0)),
            is_published=False,
        )

        response = self.client.get(reverse("home"))

        latest_titles = [article.title for article in response.context["latest_articles"]]
        self.assertEqual(latest_titles, ["公開記事6", "公開記事5", "公開記事4", "公開記事3"])
        self.assertNotContains(response, "非公開記事")

    def test_home_page_does_not_expose_staff_login_link(self):
        response = self.client.get(reverse("home"))

        self.assertNotContains(response, reverse("staff_login"))

    def test_home_page_shows_logout_only_in_header_for_logged_in_user(self):
        self.login_staff_user()

        response = self.client.get(reverse("home"))

        self.assertContains(response, "ログアウト", count=1)
        self.assertContains(response, f'action="{reverse("staff_logout")}"', count=1, html=False)


class ContactViewTests(TestCase):
    def test_contact_page_renders_form(self):
        response = self.client.get(reverse("contact"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'action="/contact/"', html=False)
        self.assertContains(response, 'name="csrfmiddlewaretoken"', html=False)

    def test_contact_form_creates_inquiry_and_redirects(self):
        response = self.client.post(
            reverse("contact"),
            {
                "name": "田中太郎",
                "email": "taro@example.com",
                "phone": "090-1234-5678",
                "message": "貸切利用について相談したいです。",
            },
        )

        self.assertRedirects(response, reverse("contact_thanks"), fetch_redirect_response=False)
        inquiry = ContactInquiry.objects.get()
        self.assertEqual(inquiry.name, "田中太郎")
        self.assertEqual(inquiry.email, "taro@example.com")
        self.assertEqual(inquiry.phone, "090-1234-5678")
        self.assertEqual(inquiry.message, "貸切利用について相談したいです。")
        self.assertFalse(inquiry.is_handled)

    def test_contact_form_with_invalid_email_does_not_create_inquiry(self):
        response = self.client.post(
            reverse("contact"),
            {
                "name": "田中太郎",
                "email": "not-an-email",
                "phone": "",
                "message": "確認用メッセージ",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactInquiry.objects.count(), 0)
        self.assertContains(response, "有効なメールアドレスを入力してください。")


class ContactInquiryAdminViewTests(StaffUserMixin, TestCase):
    def create_inquiry(self, **overrides):
        defaults = {
            "name": "田中太郎",
            "email": "taro@example.com",
            "phone": "090-1234-5678",
            "message": "貸切利用について相談したいです。",
        }
        defaults.update(overrides)
        return ContactInquiry.objects.create(**defaults)

    def test_list_requires_login(self):
        response = self.client.get(reverse("contact_inquiry_list"))

        self.assertRedirects(
            response,
            f"{reverse('staff_login')}?next={reverse('contact_inquiry_list')}",
            fetch_redirect_response=False,
        )

    def test_list_shows_pending_inquiry_and_count_to_staff(self):
        inquiry = self.create_inquiry()
        self.create_inquiry(name="対応済み", email="done@example.com", is_handled=True)
        self.login_staff_user()

        response = self.client.get(reverse("contact_inquiry_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, inquiry.name)
        self.assertContains(response, "未対応 (1)")
        self.assertNotContains(response, "done@example.com")

    def test_list_paginates_five_inquiries(self):
        for index in range(1, 8):
            self.create_inquiry(name=f"問い合わせ{index}", email=f"user{index}@example.com")
        self.login_staff_user()

        first_page = self.client.get(reverse("contact_inquiry_list"))
        second_page = self.client.get(reverse("contact_inquiry_list"), {"page": 2})

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.context["page_obj"].paginator.per_page, 5)
        self.assertEqual(len(first_page.context["page_obj"].object_list), 5)
        self.assertEqual(list(first_page.context["visible_page_numbers"]), [1, 2])
        self.assertContains(first_page, "?status=pending&amp;page=2")
        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(len(second_page.context["page_obj"].object_list), 2)

    def test_detail_shows_all_inquiry_information(self):
        inquiry = self.create_inquiry()
        self.login_staff_user()

        response = self.client.get(inquiry.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "田中太郎")
        self.assertContains(response, "taro@example.com")
        self.assertContains(response, "090-1234-5678")
        self.assertContains(response, "貸切利用について相談したいです。")
        self.assertContains(response, "対応済みにする")
        self.assertContains(response, "https://mail.google.com/mail/?view=cm")
        self.assertContains(response, "to=taro%40example.com")
        self.assertContains(response, "su=%E3%81%8A%E5%95%8F%E3%81%84%E5%90%88%E3%82%8F%E3%81%9B")
        self.assertContains(response, "%E3%80%90%E3%81%8A%E5%95%8F%E3%81%84%E5%90%88%E3%82%8F%E3%81%9B%E5%86%85%E5%AE%B9%E3%80%91")

    def test_toggle_switches_handled_status(self):
        inquiry = self.create_inquiry()
        self.login_staff_user()

        self.client.post(reverse("contact_inquiry_toggle", kwargs={"pk": inquiry.pk}))
        inquiry.refresh_from_db()
        self.assertTrue(inquiry.is_handled)
        self.assertIsNotNone(inquiry.handled_at)

        self.client.post(reverse("contact_inquiry_toggle", kwargs={"pk": inquiry.pk}))
        inquiry.refresh_from_db()
        self.assertFalse(inquiry.is_handled)
        self.assertIsNone(inquiry.handled_at)

    def test_status_endpoint_returns_pending_count(self):
        self.create_inquiry()
        self.create_inquiry(name="対応済み", email="done@example.com", is_handled=True)
        self.login_staff_user()

        response = self.client.get(reverse("contact_inquiry_status"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["pending_count"], 1)
        self.assertEqual(response.json()["total_count"], 2)


class NewsArchiveViewTests(StaffUserMixin, TestCase):
    def test_archive_filters_by_year_and_paginates_ten_articles(self):
        for day in range(1, 13):
            NewsArticle.objects.create(
                title=f"2031記事{day}",
                content="本文",
                published_at=timezone.make_aware(datetime(2031, 1, day, 12, 0)),
                is_published=True,
            )

        for day in range(1, 4):
            NewsArticle.objects.create(
                title=f"2030記事{day}",
                content="本文",
                published_at=timezone.make_aware(datetime(2030, 12, day, 12, 0)),
                is_published=True,
            )

        response = self.client.get(reverse("news_archive"), {"year": 2031})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_year"], 2031)
        self.assertEqual(response.context["page_obj"].paginator.per_page, 10)
        self.assertEqual(len(response.context["page_obj"].object_list), 10)
        self.assertContains(response, "2031年")
        self.assertNotContains(response, "2030記事1")

    def test_archive_second_page_keeps_year_filter(self):
        for day in range(1, 13):
            NewsArticle.objects.create(
                title=f"2032記事{day}",
                content="本文",
                published_at=timezone.make_aware(datetime(2032, 2, day, 12, 0)),
                is_published=True,
            )

        response = self.client.get(reverse("news_archive"), {"year": 2032, "page": 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(len(response.context["page_obj"].object_list), 2)
        self.assertContains(response, "?year=2032&amp;page=1")

    def test_archive_shows_only_current_page_plus_minus_three(self):
        base_datetime = timezone.make_aware(datetime(2034, 1, 1, 12, 0))
        for day in range(1, 81):
            NewsArticle.objects.create(
                title=f"2034記事{day}",
                content="本文",
                published_at=base_datetime + timedelta(days=day - 1),
                is_published=True,
            )

        response = self.client.get(reverse("news_archive"), {"page": 5})

        self.assertEqual(list(response.context["visible_page_numbers"]), [2, 3, 4, 5, 6, 7, 8])

    def test_archive_shows_ellipsis_when_hidden_pages_exist_before_and_after(self):
        base_datetime = timezone.make_aware(datetime(2034, 1, 1, 12, 0))
        for day in range(1, 121):
            NewsArticle.objects.create(
                title=f"2035記事{day}",
                content="本文",
                published_at=base_datetime + timedelta(days=day - 1),
                is_published=True,
            )

        response = self.client.get(reverse("news_archive"), {"page": 6})

        self.assertEqual(list(response.context["visible_page_numbers"]), [3, 4, 5, 6, 7, 8, 9])
        self.assertTrue(response.context["show_first_page_link"])
        self.assertTrue(response.context["show_leading_ellipsis"])
        self.assertTrue(response.context["show_last_page_link"])
        self.assertTrue(response.context["show_trailing_ellipsis"])
        self.assertContains(response, "news-pagination-gap", count=4, html=False)

    def test_archive_hides_admin_actions_from_public_users(self):
        published = NewsArticle.objects.create(
            title="公開記事",
            content="本文",
            published_at=timezone.make_aware(datetime(2033, 1, 1, 12, 0)),
            is_published=True,
        )
        NewsArticle.objects.create(
            title="下書き記事",
            content="本文",
            is_published=False,
        )

        response = self.client.get(reverse("news_archive"))

        self.assertContains(response, published.title)
        self.assertNotContains(response, "下書き記事")
        self.assertNotContains(response, reverse("news_drafts"))
        self.assertNotContains(response, reverse("news_create"))
        self.assertNotContains(response, reverse("news_update", kwargs={"url_key": published.url_segment}))
        self.assertNotContains(response, reverse("news_delete", kwargs={"url_key": published.url_segment}))
        self.assertIsNone(response.context["draft_count"])

    def test_archive_shows_admin_actions_to_staff_user(self):
        published = NewsArticle.objects.create(
            title="公開記事",
            content="本文",
            published_at=timezone.make_aware(datetime(2033, 2, 1, 12, 0)),
            is_published=True,
        )
        NewsArticle.objects.create(
            title="下書き記事",
            content="本文",
            is_published=False,
        )
        self.login_staff_user()

        response = self.client.get(reverse("news_archive"))

        self.assertContains(response, reverse("news_create"))
        self.assertContains(response, reverse("news_drafts"))
        self.assertContains(response, reverse("news_update", kwargs={"url_key": published.url_segment}))
        self.assertContains(response, reverse("news_delete", kwargs={"url_key": published.url_segment}))
        self.assertEqual(response.context["draft_count"], 1)
        self.assertContains(response, "ログアウト", count=1)


class NewsDetailViewTests(StaffUserMixin, TestCase):
    def test_detail_hides_admin_actions_from_public_users(self):
        article = NewsArticle.objects.create(
            title="公開記事",
            content="本文",
            published_at=timezone.make_aware(datetime(2033, 3, 1, 12, 0)),
            is_published=True,
        )

        response = self.client.get(article.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("news_update", kwargs={"url_key": article.url_segment}))
        self.assertNotContains(response, reverse("news_delete", kwargs={"url_key": article.url_segment}))
        self.assertNotContains(response, reverse("news_drafts"))

    def test_detail_shows_admin_actions_to_staff_user(self):
        article = NewsArticle.objects.create(
            title="公開記事",
            content="本文",
            published_at=timezone.make_aware(datetime(2033, 3, 2, 12, 0)),
            is_published=True,
        )
        self.login_staff_user()

        response = self.client.get(article.get_absolute_url())

        self.assertContains(response, reverse("news_update", kwargs={"url_key": article.url_segment}))
        self.assertContains(response, reverse("news_delete", kwargs={"url_key": article.url_segment}))
        self.assertContains(response, reverse("news_drafts"))


class NewsAdminAccessTests(StaffUserMixin, TestCase):
    def test_staff_entry_redirects_to_login(self):
        response = self.client.get(reverse("staff_entry"))

        self.assertRedirects(response, reverse("staff_login"), fetch_redirect_response=False)

    def test_staff_login_redirects_to_drafts_after_successful_login(self):
        user = self.create_staff_user()

        response = self.client.post(
            reverse("staff_login"),
            {"username": user.username, "password": self.staff_password},
        )

        self.assertRedirects(response, reverse("news_drafts"), fetch_redirect_response=False)

    def test_draft_list_requires_login(self):
        response = self.client.get(reverse("news_drafts"))

        self.assertRedirects(
            response,
            f"{reverse('staff_login')}?next={reverse('news_drafts')}",
            fetch_redirect_response=False,
        )

    def test_create_page_requires_login(self):
        response = self.client.get(reverse("news_create"))

        self.assertRedirects(
            response,
            f"{reverse('staff_login')}?next={reverse('news_create')}",
            fetch_redirect_response=False,
        )

    def test_non_staff_user_cannot_access_news_admin_pages(self):
        user = get_user_model().objects.create_user(
            username="general-user",
            password="GeneralPass123",
            is_staff=False,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("news_drafts"))

        self.assertEqual(response.status_code, 403)


class NewsDraftListViewTests(StaffUserMixin, TestCase):
    def setUp(self):
        self.login_staff_user()

    def test_draft_list_shows_drafts_without_detail_links(self):
        draft = NewsArticle.objects.create(
            title="下書き記事",
            content="本文",
            is_published=False,
        )

        response = self.client.get(reverse("news_drafts"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, draft.title)
        self.assertContains(response, reverse("news_update", kwargs={"url_key": draft.url_segment}))
        self.assertNotContains(response, f'href="{draft.get_absolute_url()}"', html=False)

    def test_draft_list_paginates_five_articles_and_shows_second_page(self):
        for number in range(1, 8):
            NewsArticle.objects.create(
                title=f"下書き{number}",
                content="本文",
                is_published=False,
            )

        first_page = self.client.get(reverse("news_drafts"))
        second_page = self.client.get(reverse("news_drafts"), {"page": 2})

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.context["page_obj"].paginator.per_page, 5)
        self.assertEqual(len(first_page.context["page_obj"].object_list), 5)
        self.assertContains(first_page, "?page=2")

        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(second_page.context["page_obj"].number, 2)
        self.assertEqual(len(second_page.context["page_obj"].object_list), 2)

    def test_draft_list_shows_only_current_page_plus_minus_three(self):
        for number in range(1, 41):
            NewsArticle.objects.create(
                title=f"下書き{number}",
                content="本文",
                is_published=False,
            )

        response = self.client.get(reverse("news_drafts"), {"page": 5})

        self.assertEqual(list(response.context["visible_page_numbers"]), [2, 3, 4, 5, 6, 7, 8])

    def test_draft_list_shows_ellipsis_when_hidden_pages_exist_before_and_after(self):
        for number in range(1, 61):
            NewsArticle.objects.create(
                title=f"下書き拡張{number}",
                content="本文",
                is_published=False,
            )

        response = self.client.get(reverse("news_drafts"), {"page": 6})

        self.assertEqual(list(response.context["visible_page_numbers"]), [3, 4, 5, 6, 7, 8, 9])
        self.assertTrue(response.context["show_first_page_link"])
        self.assertTrue(response.context["show_leading_ellipsis"])
        self.assertTrue(response.context["show_last_page_link"])
        self.assertTrue(response.context["show_trailing_ellipsis"])
        self.assertContains(response, "news-pagination-gap", count=4, html=False)

    def test_draft_delete_page_uses_draft_list_for_back_and_cancel_links(self):
        article = NewsArticle.objects.create(
            title="削除前の下書き",
            content="本文",
            is_published=False,
        )

        response = self.client.get(reverse("news_delete", kwargs={"url_key": article.url_segment}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/news/drafts/"', count=2, html=False)
        self.assertNotContains(response, article.get_absolute_url())


class NewsEditorFlowTests(StaffUserMixin, TestCase):
    def setUp(self):
        self.login_staff_user()

    def test_draft_edit_page_uses_draft_list_for_back_and_cancel_links(self):
        article = NewsArticle.objects.create(
            title="下書き編集中",
            content="本文",
            is_published=False,
        )

        response = self.client.get(reverse("news_update", kwargs={"url_key": article.url_segment}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/news/drafts/"', count=2, html=False)
        self.assertNotContains(response, 'href="/news/"', html=False)

    def test_published_edit_page_uses_detail_for_back_and_cancel_links(self):
        article = NewsArticle.objects.create(
            title="公開編集中",
            content="本文",
            published_at=timezone.make_aware(datetime(2035, 1, 1, 12, 0)),
            is_published=True,
        )

        response = self.client.get(reverse("news_update", kwargs={"url_key": article.url_segment}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{article.get_absolute_url()}"', count=2, html=False)
        self.assertNotContains(response, 'href="/news/drafts/"', html=False)

    def test_edit_page_shows_explicit_image_clear_control_copy(self):
        article = NewsArticle.objects.create(
            title="画像付き下書き",
            content="本文",
            is_published=False,
        )
        article.image = "news/sample.jpg"
        article.save(update_fields=["image"])

        response = self.client.get(reverse("news_update", kwargs={"url_key": article.url_segment}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "現在の写真")
        self.assertContains(response, "新しい写真に差し替え")
        self.assertContains(response, "この写真を削除する")

    def test_create_preview_does_not_save_before_publish(self):
        response = self.client.post(
            reverse("news_create"),
            {
                "title": "プレビュー記事",
                "content": "本文",
            },
        )

        self.assertEqual(NewsArticle.objects.count(), 0)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/news/preview/", response.url)

        preview_response = self.client.get(response.url)
        self.assertContains(preview_response, "プレビュー記事")

    def test_preview_publish_creates_article(self):
        preview_response = self.client.post(
            reverse("news_create"),
            {
                "title": "公開候補",
                "content": "本文",
            },
        )
        publish_response = self.client.post(
            preview_response.url,
            {"action": "publish"},
        )

        article = NewsArticle.objects.get(title="公開候補")

        self.assertRedirects(
            publish_response,
            article.get_absolute_url(),
            fetch_redirect_response=False,
        )
        self.assertTrue(article.is_published)
        self.assertIsNotNone(article.published_at)

    def test_preview_can_save_article_as_draft(self):
        preview_response = self.client.post(
            reverse("news_create"),
            {
                "title": "下書き候補",
                "content": "本文",
            },
        )

        draft_response = self.client.post(
            preview_response.url,
            {"action": "save_draft"},
        )

        article = NewsArticle.objects.get(title="下書き候補")

        self.assertRedirects(draft_response, reverse("news_drafts"), fetch_redirect_response=False)
        self.assertFalse(article.is_published)
        self.assertIsNone(article.published_at)

    def test_preview_with_unknown_action_does_not_save_article(self):
        preview_response = self.client.post(
            reverse("news_create"),
            {
                "title": "未保存候補",
                "content": "本文",
            },
        )

        response = self.client.post(preview_response.url, {"action": "unexpected"})

        self.assertEqual(response.status_code, 404)
        self.assertFalse(NewsArticle.objects.filter(title="未保存候補").exists())

    def test_preview_page_has_publish_confirmation_prompt(self):
        preview_response = self.client.post(
            reverse("news_create"),
            {
                "title": "確認ダイアログ候補",
                "content": "本文",
            },
        )

        response = self.client.get(preview_response.url)

        self.assertContains(response, "この内容で公開しますか？")

    def test_edit_preview_does_not_change_saved_article_until_publish(self):
        article = NewsArticle.objects.create(
            title="元タイトル",
            content="元本文",
            published_at=timezone.make_aware(datetime(2034, 1, 1, 12, 0)),
            is_published=True,
        )

        preview_response = self.client.post(
            reverse("news_update", kwargs={"url_key": article.url_segment}),
            {
                "title": "変更後タイトル",
                "content": "変更後本文",
            },
        )

        article.refresh_from_db()
        self.assertEqual(article.title, "元タイトル")
        self.assertEqual(article.content, "元本文")

        publish_response = self.client.post(preview_response.url, {"action": "publish"})

        article.refresh_from_db()
        self.assertRedirects(
            publish_response,
            article.get_absolute_url(),
            fetch_redirect_response=False,
        )
        self.assertEqual(article.title, "変更後タイトル")
        self.assertEqual(article.content, "変更後本文")


class NewsArticleModelTests(TestCase):
    def test_url_segment_uses_created_date_and_id(self):
        article = NewsArticle(
            id=7,
            title="テスト",
            content="本文",
            created_at=datetime(2026, 4, 11, 12, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
        )

        self.assertEqual(article.url_segment, "20260411-7")
        self.assertEqual(article.get_absolute_url(), "/news/20260411-7/")

    def test_save_sets_published_at_when_article_is_published(self):
        article = NewsArticle(title="公開", content="本文", is_published=True)

        article.save()

        self.assertIsNotNone(article.published_at)

    def test_news_image_storage_uses_media_directory(self):
        article = NewsArticle(title="画像保存", content="本文")

        self.assertEqual(
            Path(article.image.storage.location),
            Path(settings.MEDIA_ROOT),
        )
        self.assertEqual(article.image.storage.base_url, "/media/")
