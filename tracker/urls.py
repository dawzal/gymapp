from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('cwiczenia/', views.lista_cwiczen, name='lista_cwiczen'),
    path('cwiczenia/dodaj/', views.dodaj_cwiczenie, name='dodaj_cwiczenie'),
    path('cwiczenia/<int:pk>/edytuj/', views.edytuj_cwiczenie, name='edytuj_cwiczenie'),
    path('plany/', views.lista_planow, name='lista_planow'),
    path('plany/dodaj/', views.dodaj_plan, name='dodaj_plan'),
    path('plany/<int:pk>/', views.szczegoly_planu, name='szczegoly_planu'),
    path('plany/<int:pk>/edytuj/', views.edytuj_plan, name='edytuj_plan'),
    path('plany/<int:plan_pk>/dodaj-dzien/', views.dodaj_dzien, name='dodaj_dzien'),
    path('dzien/<int:dzien_pk>/dodaj-cwiczenie/', views.dodaj_cwiczenie_do_dnia, name='dodaj_cwiczenie_do_dnia'),
    path('kalkulator/', views.kalkulator_1rm, name='kalkulator_1rm'),
    path('dziennik/', views.dziennik, name='dziennik'),
    path('dziennik/dodaj/', views.dodaj_sesje, name='dodaj_sesje'),
    path('dziennik/<int:pk>/', views.szczegoly_sesji, name='szczegoly_sesji'),
    path('dziennik/<int:pk>/edytuj/', views.edytuj_sesje, name='edytuj_sesje'),
    path('statystyki/', views.statystyki, name='statystyki'),
    path('wpis/<int:pk>/edytuj/', views.edytuj_wpis, name='edytuj_wpis'),
    path('cwiczenie-dnia/<int:pk>/edytuj/', views.edytuj_cwiczenie_dnia, name='edytuj_cwiczenie_dnia'),
]