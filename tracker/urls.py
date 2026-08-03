from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('cwiczenia/', views.lista_cwiczen, name='lista_cwiczen'),
    path('cwiczenia/dodaj/', views.dodaj_cwiczenie, name='dodaj_cwiczenie'),
    path('plany/', views.lista_planow, name='lista_planow'),
    path('plany/dodaj/', views.dodaj_plan, name='dodaj_plan'),
    path('plany/<int:pk>/', views.szczegoly_planu, name='szczegoly_planu'),
    path('plany/<int:plan_pk>/dodaj-dzien/', views.dodaj_dzien, name='dodaj_dzien'),
    path('dzien/<int:dzien_pk>/dodaj-cwiczenie/', views.dodaj_cwiczenie_do_dnia, name='dodaj_cwiczenie_do_dnia'),
]