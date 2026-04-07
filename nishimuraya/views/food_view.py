from django.views.generic import TemplateView


class FoodView(TemplateView):
    template_name = "nishimuraya/food.html"
