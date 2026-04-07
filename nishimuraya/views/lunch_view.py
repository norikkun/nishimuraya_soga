from django.views.generic import TemplateView


class LunchView(TemplateView):
    template_name = "nishimuraya/lunch.html"
