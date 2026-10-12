from django.contrib.auth.views import LoginView
from django.urls import path

from . import views

urlpatterns = [
    path('rejestracja/', views.rejestracja, name='rejestracja'),
    path(
        'logowanie/',
        LoginView.as_view(template_name='accounts/logowanie.html', redirect_authenticated_user=True),
        name='logowanie',
    ),
    path('wylogowanie/', views.wylogowanie, name='wylogowanie'),
]
