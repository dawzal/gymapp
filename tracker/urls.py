from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('cwiczenia/', views.lista_cwiczen, name='lista_cwiczen'),
    path('cwiczenia/dodaj/', views.dodaj_cwiczenie, name='dodaj_cwiczenie'),
]