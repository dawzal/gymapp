from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Cwiczenie
from .forms import CwiczenieForm

@login_required
def dashboard(request):
    return render(request, 'tracker/dashboard.html')

@login_required
def lista_cwiczen(request):
    kategoria = request.GET.get('kategoria', '')
    if kategoria:
        cwiczenia = Cwiczenie.objects.filter(
            czy_publiczne=True, kategoria=kategoria
        )
    else:
        cwiczenia = Cwiczenie.objects.filter(czy_publiczne=True)
    
    return render(request, 'tracker/lista_cwiczen.html', {
        'cwiczenia': cwiczenia,
        'kategoria': kategoria,
        'kategorie': Cwiczenie.KATEGORIE,
    })

@login_required
def dodaj_cwiczenie(request):
    if request.method == 'POST':
        formularz = CwiczenieForm(request.POST)
        if formularz.is_valid():
            cwiczenie = formularz.save(commit=False)
            cwiczenie.dodane_przez = request.user
            cwiczenie.save()
            messages.success(request, 'Ćwiczenie zostało dodane!')
            return redirect('lista_cwiczen')
    else:
        formularz = CwiczenieForm()
    return render(request, 'tracker/dodaj_cwiczenie.html', {
        'formularz': formularz
    })