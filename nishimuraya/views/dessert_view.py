from django.views.generic import TemplateView


class DessertView(TemplateView):
    template_name = "nishimuraya/dessert.html"
