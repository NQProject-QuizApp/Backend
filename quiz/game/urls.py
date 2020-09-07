from django.urls import path

from . import views


urlpatterns = [
    path('requests_form_debug', views.index, name='index'),
]
