from django.views.generic import TemplateView


class NewsArchiveView(TemplateView):
    template_name = "nishimuraya/news.html"
