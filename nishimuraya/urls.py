from django.urls import path

from .views.home_views import HomeView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
]
