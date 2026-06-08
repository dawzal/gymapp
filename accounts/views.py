from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages

def rejestracja(request):
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

def logowanie(request):
    if request.method == 'POST':
        formularz = AuthenticationForm(data=request.POST)
        if formularz.is_valid():
            uzytkownik = formularz.get_user()
            login(request, uzytkownik)
            return redirect('dashboard')
    else:
        formularz = AuthenticationForm()
    return render(request, 'accounts/logowanie.html', {'formularz': formularz})

def wylogowanie(request):
    logout(request)
    return redirect('logowanie')