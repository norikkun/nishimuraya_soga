from django.http import Http404
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.views.generic import TemplateView


class NewsDetailView(TemplateView):
    def get_template_names(self):
        slug = self.kwargs["slug"]
        template_name = f"nishimuraya/news/{slug}.html"

        try:
            get_template(template_name)
        except TemplateDoesNotExist as exc:
            raise Http404("News article not found") from exc

        return [template_name]
