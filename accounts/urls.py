from django.urls import path
from . import views

urlpatterns = [
    path('rejestracja/', views.rejestracja, name='rejestracja'),
    path('logowanie/', views.logowanie, name='logowanie'),
    path('wylogowanie/', views.wylogowanie, name='wylogowanie'),
]