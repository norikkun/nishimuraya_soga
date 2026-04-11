from django.views.generic import TemplateView

from ..models import NewsArticle


class HomeView(TemplateView):
    template_name = "nishimuraya/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["latest_articles"] = NewsArticle.objects.filter(is_published=True).order_by(
            "-published_at",
            "-id",
        )[:4]
        return context
