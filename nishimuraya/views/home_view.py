from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = "nishimuraya/home.html"
