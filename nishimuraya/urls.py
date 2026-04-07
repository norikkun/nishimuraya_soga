from django.urls import path

from .views import (
    ContactThanksView,
    ContactView,
    DessertView,
    DrinkView,
    FoodView,
    HomeView,
    LunchView,
    NewsArchiveView,
    NewsDetailView,
    RecruitView,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("index.html", HomeView.as_view(), name="index"),
    path("food.html", FoodView.as_view(), name="food"),
    path("drink.html", DrinkView.as_view(), name="drink"),
    path("dessert.html", DessertView.as_view(), name="dessert"),
    path("lunch.html", LunchView.as_view(), name="lunch"),
    path("recruit.html", RecruitView.as_view(), name="recruit"),
    path("contact.html", ContactView.as_view(), name="contact"),
    path("contact-thanks.html", ContactThanksView.as_view(), name="contact_thanks"),
    path("news.html", NewsArchiveView.as_view(), name="news_archive"),
    path("news/<slug:slug>.html", NewsDetailView.as_view(), name="news_detail"),
]
