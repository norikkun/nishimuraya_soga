from django.urls import path

from .views.views import home

urlpatterns = [
    path("", home, name="home"),
]
