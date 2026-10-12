from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST


def rejestracja(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        formularz = UserCreationForm(request.POST)
        if formularz.is_valid():
            uzytkownik = formularz.save()
            login(request, uzytkownik)
            messages.success(request, 'Konto zostało utworzone!')
            return redirect('dashboard')
    else:
        formularz = UserCreationForm()
    return render(request, 'accounts/rejestracja.html', {'formularz': formularz})


@require_POST
def wylogowanie(request):
    logout(request)
    return redirect('logowanie')
