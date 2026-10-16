from django.urls import path

from . import views

urlpatterns = [
    path('czat/', views.czat, name='czat'),
    path('czat/wyslij/', views.wyslij, name='czat_wyslij'),
    path('czat/wyczysc/', views.wyczysc, name='czat_wyczysc'),
]
