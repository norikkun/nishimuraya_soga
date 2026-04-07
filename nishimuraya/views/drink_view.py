from django.views.generic import TemplateView


class DrinkView(TemplateView):
    template_name = "nishimuraya/drink.html"
