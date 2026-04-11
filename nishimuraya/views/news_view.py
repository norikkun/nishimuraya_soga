from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.files.base import File
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from ..forms import NewsArticleForm
from ..models import NewsArticle
from ..storages import news_static_image_storage


PREVIEW_SESSION_KEY = "news_article_previews"
PREVIEW_UPLOAD_DIR = "news-previews"


class NewsAdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = reverse_lazy("staff_login")

    def test_func(self):
        return self.request.user.is_staff


class PaginationWindowMixin:
    page_window = 3

    def get_visible_page_numbers(self, page_obj):
        start_page = max(1, page_obj.number - self.page_window)
        end_page = min(page_obj.paginator.num_pages, page_obj.number + self.page_window)
        return list(range(start_page, end_page + 1))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj = context.get("page_obj")
        visible_page_numbers = (
            self.get_visible_page_numbers(page_obj) if page_obj and context.get("is_paginated") else []
        )
        if visible_page_numbers:
            first_visible_page = visible_page_numbers[0]
            last_visible_page = visible_page_numbers[-1]
            context["show_first_page_link"] = first_visible_page > 1
            context["show_leading_ellipsis"] = first_visible_page > 2
            context["show_last_page_link"] = last_visible_page < page_obj.paginator.num_pages
            context["show_trailing_ellipsis"] = (
                last_visible_page < page_obj.paginator.num_pages - 1
            )
        else:
            context["show_first_page_link"] = False
            context["show_leading_ellipsis"] = False
            context["show_last_page_link"] = False
            context["show_trailing_ellipsis"] = False
        context["visible_page_numbers"] = visible_page_numbers
        return context


class NewsArticleLookupMixin:
    def get_lookup_queryset(self):
        return NewsArticle.objects.all()

    def get_object(self, queryset=None):
        url_key = self.kwargs["url_key"]

        try:
            created_at_text, article_id_text = url_key.split("-", 1)
            created_at_date = datetime.strptime(created_at_text, "%Y%m%d").date()
            article_id = int(article_id_text)
        except (TypeError, ValueError) as exc:
            raise Http404("News article not found") from exc

        lookup_queryset = queryset or self.get_lookup_queryset()
        return get_object_or_404(
            lookup_queryset,
            pk=article_id,
            created_at__date=created_at_date,
        )


class NewsArchiveView(PaginationWindowMixin, ListView):
    model = NewsArticle
    template_name = "nishimuraya/news_article_list.html"
    context_object_name = "articles"
    paginate_by = 10

    def get_selected_year(self):
        year_text = self.request.GET.get("year", "").strip()
        if not year_text or not year_text.isdigit():
            return None
        return int(year_text)

    def get_base_queryset(self):
        return NewsArticle.objects.filter(is_published=True).order_by("-published_at", "-id")

    def get_queryset(self):
        queryset = self.get_base_queryset()
        selected_year = self.get_selected_year()
        if selected_year is not None:
            queryset = queryset.filter(published_at__year=selected_year)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_year = self.get_selected_year()
        is_news_admin = self.request.user.is_authenticated and self.request.user.is_staff
        context["selected_year"] = selected_year
        context["year_query"] = f"year={selected_year}&" if selected_year else ""
        context["available_years"] = [
            year.year
            for year in self.get_base_queryset().dates("published_at", "year", order="DESC")
        ]
        context["draft_count"] = (
            NewsArticle.objects.filter(is_published=False).count() if is_news_admin else None
        )
        return context


class NewsDraftListView(NewsAdminRequiredMixin, PaginationWindowMixin, ListView):
    model = NewsArticle
    template_name = "nishimuraya/news_article_draft_list.html"
    context_object_name = "articles"
    paginate_by = 5

    def get_queryset(self):
        return NewsArticle.objects.filter(is_published=False).order_by("-updated_at", "-id")


class NewsDetailView(NewsArticleLookupMixin, DetailView):
    model = NewsArticle
    template_name = "nishimuraya/news_article_detail.html"
    context_object_name = "article"

    def get_lookup_queryset(self):
        return NewsArticle.objects.filter(is_published=True)


class NewsPreviewSessionMixin:
    def get_preview_store(self):
        return self.request.session.get(PREVIEW_SESSION_KEY, {})

    def save_preview_store(self, store):
        self.request.session[PREVIEW_SESSION_KEY] = store
        self.request.session.modified = True

    def get_preview_payload(self, preview_token):
        return self.get_preview_store().get(preview_token)

    def set_preview_payload(self, preview_token, payload):
        store = self.get_preview_store()
        store[preview_token] = payload
        self.save_preview_store(store)

    def clear_preview_payload(self, preview_token):
        store = self.get_preview_store()
        payload = store.pop(preview_token, None)
        self.save_preview_store(store)
        self.cleanup_temp_upload(payload)
        return payload

    def cleanup_temp_upload(self, payload):
        if not payload:
            return
        temp_path = payload.get("image_temp_path")
        if temp_path and news_static_image_storage.exists(temp_path):
            news_static_image_storage.delete(temp_path)


class NewsEditorMixin(NewsPreviewSessionMixin):
    form_class = NewsArticleForm
    template_name = "nishimuraya/news_article_form.html"

    def get_current_article(self):
        return getattr(self, "object", None)

    def get_cancel_url(self):
        return reverse("news_archive")

    def get_back_link_label(self):
        return "一覧へ戻る"

    def payload_matches_object(self, payload):
        article = self.get_current_article()
        payload_article_id = payload.get("article_id")
        current_article_id = article.pk if article else None
        return payload_article_id == current_article_id

    def get_active_preview_token(self):
        return self.request.GET.get("preview") or self.request.POST.get("preview_token")

    def get_active_preview_payload(self):
        preview_token = self.get_active_preview_token()
        if not preview_token:
            return None

        payload = self.get_preview_payload(preview_token)
        if not payload or not self.payload_matches_object(payload):
            return None
        return payload

    def save_temp_upload(self, uploaded_file):
        filename = Path(uploaded_file.name).name
        temp_path = f"{PREVIEW_UPLOAD_DIR}/{uuid4().hex}-{filename}"
        return news_static_image_storage.save(temp_path, uploaded_file)

    def build_preview_payload(self, form):
        article = self.get_current_article()
        image_value = form.cleaned_data.get("image")
        clear_image = image_value is False
        image_temp_path = None
        image_name = ""

        if hasattr(image_value, "read"):
            image_temp_path = self.save_temp_upload(image_value)
            image_name = Path(image_value.name).name

        existing_image_name = ""
        if article and article.image and not clear_image and image_temp_path is None:
            existing_image_name = article.image.name

        return {
            "article_id": article.pk if article else None,
            "title": form.cleaned_data["title"],
            "content": form.cleaned_data["content"],
            "clear_image": clear_image,
            "existing_image_name": existing_image_name,
            "image_temp_path": image_temp_path,
            "image_name": image_name,
        }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.method == "GET":
            payload = self.get_active_preview_payload()
            if payload:
                kwargs["initial"] = {
                    "title": payload["title"],
                    "content": payload["content"],
                }
        return kwargs

    def get_form_image_preview_context(self):
        payload = self.get_active_preview_payload()
        if payload:
            if payload.get("image_temp_path"):
                return {
                    "url": news_static_image_storage.url(payload["image_temp_path"]),
                    "label": "プレビュー用の写真",
                }
            if payload.get("existing_image_name"):
                return {
                    "url": news_static_image_storage.url(payload["existing_image_name"]),
                    "label": "現在の写真",
                }
            return None

        article = self.get_current_article()
        if article and article.image:
            return {
                "url": article.image.url,
                "label": "現在の写真",
            }
        return None

    def form_valid(self, form):
        preview_token = self.request.POST.get("preview_token") or uuid4().hex
        existing_payload = self.get_preview_payload(preview_token)
        self.cleanup_temp_upload(existing_payload)
        payload = self.build_preview_payload(form)
        self.set_preview_payload(preview_token, payload)
        preview_url = reverse("news_preview", kwargs={"preview_token": preview_token})
        return redirect(preview_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_preview_token"] = self.get_active_preview_token()
        context["form_image_preview"] = self.get_form_image_preview_context()
        context["cancel_url"] = self.get_cancel_url()
        context["back_url"] = context["cancel_url"]
        context["back_label"] = self.get_back_link_label()
        return context


class NewsCreateView(NewsAdminRequiredMixin, NewsEditorMixin, CreateView):
    model = NewsArticle

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "お知らせを作成"
        context["current_status"] = "新規作成"
        return context


class NewsUpdateView(NewsAdminRequiredMixin, NewsArticleLookupMixin, NewsEditorMixin, UpdateView):
    model = NewsArticle
    context_object_name = "article"

    def get_cancel_url(self):
        if self.object.is_published:
            return self.object.get_absolute_url()
        return reverse("news_drafts")

    def get_back_link_label(self):
        if self.object.is_published:
            return "記事詳細へ戻る"
        return "下書き一覧へ戻る"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "お知らせを編集"
        context["current_status"] = self.object.status_label
        return context


class NewsPreviewView(NewsAdminRequiredMixin, NewsPreviewSessionMixin, TemplateView):
    template_name = "nishimuraya/news_article_preview.html"

    def get_payload(self):
        payload = self.get_preview_payload(self.kwargs["preview_token"])
        if not payload:
            raise Http404("Preview data not found")
        return payload

    def build_preview_article(self, payload):
        image_url = None
        if payload.get("image_temp_path"):
            image_url = news_static_image_storage.url(payload["image_temp_path"])
        elif payload.get("existing_image_name"):
            image_url = news_static_image_storage.url(payload["existing_image_name"])

        return SimpleNamespace(
            title=payload["title"],
            content=payload["content"],
            image_url=image_url,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payload = self.get_payload()
        context["article"] = self.build_preview_article(payload)
        context["preview_token"] = self.kwargs["preview_token"]
        return context

    def post(self, request, *args, **kwargs):
        preview_token = self.kwargs["preview_token"]
        payload = self.get_payload()
        action = request.POST.get("action")

        if action == "edit":
            article_id = payload.get("article_id")
            if article_id:
                article = get_object_or_404(NewsArticle, pk=article_id)
                return redirect(f"{reverse('news_update', kwargs={'url_key': article.url_segment})}?preview={preview_token}")
            return redirect(f"{reverse('news_create')}?preview={preview_token}")

        if action not in {"publish", "save_draft"}:
            raise Http404("Unknown preview action")

        article = None
        if payload.get("article_id"):
            article = get_object_or_404(NewsArticle, pk=payload["article_id"])
        else:
            article = NewsArticle()

        article.title = payload["title"]
        article.content = payload["content"]
        article.is_published = action == "publish"

        if payload.get("clear_image"):
            if article.pk and article.image:
                article.image.delete(save=False)
            article.image = None
        elif payload.get("image_temp_path"):
            with news_static_image_storage.open(payload["image_temp_path"], "rb") as temp_file:
                article.image.save(payload["image_name"], File(temp_file), save=False)

        article.save()
        self.clear_preview_payload(preview_token)

        if action == "publish":
            messages.success(request, "お知らせを公開しました。")
            return redirect(article.get_absolute_url())

        if action == "save_draft":
            messages.success(request, "下書きを保存しました。")
            return redirect("news_drafts")


class NewsDeleteView(NewsAdminRequiredMixin, NewsArticleLookupMixin, DeleteView):
    model = NewsArticle
    template_name = "nishimuraya/news_article_confirm_delete.html"
    context_object_name = "article"

    def get_success_url(self):
        if self.object.is_published:
            return reverse("news_archive")
        return reverse("news_drafts")

    def get_cancel_url(self):
        if self.object.is_published:
            return self.object.get_absolute_url()
        return reverse("news_drafts")

    def get_back_label(self):
        if self.object.is_published:
            return "詳細へ戻る"
        return "下書き一覧へ戻る"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = self.get_cancel_url()
        context["back_label"] = self.get_back_label()
        return context


class LegacyNewsDetailRedirectView(View):
    def get(self, request, legacy_slug, *args, **kwargs):
        slug_parts = legacy_slug.split("-")

        if len(slug_parts) != 3 or slug_parts[0] != "news":
            raise Http404("News article not found")

        try:
            article_date = datetime.strptime(slug_parts[1], "%Y%m%d").date()
            article_index = int(slug_parts[2]) - 1
        except ValueError as exc:
            raise Http404("News article not found") from exc

        if article_index < 0:
            raise Http404("News article not found")

        articles = NewsArticle.objects.filter(created_at__date=article_date).order_by("id")

        try:
            article = articles[article_index]
        except IndexError as exc:
            raise Http404("News article not found") from exc

        return HttpResponseRedirect(article.get_absolute_url())
