from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Cwiczenie, PlanTreningowy, DzienPlanTreningowego, CwiczenieDnia
from .forms import CwiczenieForm, PlanTreningowyForm, CwiczenieDniaForm

@login_required
def dashboard(request):
    moje_plany = PlanTreningowy.objects.filter(uzytkownik=request.user)[:3]
    ostatnie_cwiczenia = Cwiczenie.objects.filter(czy_publiczne=True)[:6]
    return render(request, 'tracker/dashboard.html', {
        'moje_plany': moje_plany,
        'ostatnie_cwiczenia': ostatnie_cwiczenia,
    })

@login_required
def lista_cwiczen(request):
    kategoria = request.GET.get('kategoria', '')
    if kategoria:
        cwiczenia = Cwiczenie.objects.filter(czy_publiczne=True, kategoria=kategoria)
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
    return render(request, 'tracker/dodaj_cwiczenie.html', {'formularz': formularz})

@login_required
def lista_planow(request):
    moje_plany = PlanTreningowy.objects.filter(uzytkownik=request.user)
    publiczne_plany = PlanTreningowy.objects.filter(czy_publiczny=True).exclude(uzytkownik=request.user)
    return render(request, 'tracker/lista_planow.html', {
        'moje_plany': moje_plany,
        'publiczne_plany': publiczne_plany,
    })

@login_required
def dodaj_plan(request):
    if request.method == 'POST':
        formularz = PlanTreningowyForm(request.POST)
        if formularz.is_valid():
            plan = formularz.save(commit=False)
            plan.uzytkownik = request.user
            plan.save()
            messages.success(request, 'Plan treningowy został utworzony!')
            return redirect('szczegoly_planu', pk=plan.pk)
    else:
        formularz = PlanTreningowyForm()
    return render(request, 'tracker/dodaj_plan.html', {'formularz': formularz})

@login_required
def szczegoly_planu(request, pk):
    plan = get_object_or_404(PlanTreningowy, pk=pk, uzytkownik=request.user)
    dni = plan.dni.all()
    return render(request, 'tracker/szczegoly_planu.html', {
        'plan': plan,
        'dni': dni,
        'dni_tygodnia': DzienPlanTreningowego.DNI,
    })

@login_required
def dodaj_dzien(request, plan_pk):
    plan = get_object_or_404(PlanTreningowy, pk=plan_pk, uzytkownik=request.user)
    if request.method == 'POST':
        dzien_nazwa = request.POST.get('dzien')
        if dzien_nazwa:
            dzien, created = DzienPlanTreningowego.objects.get_or_create(
                plan=plan,
                dzien=dzien_nazwa,
                defaults={'kolejnosc': plan.dni.count()}
            )
            if created:
                messages.success(request, 'Dodano dzień do planu!')
            else:
                messages.info(request, 'Ten dzień już istnieje w planie.')
            return redirect('szczegoly_planu', pk=plan.pk)
    return redirect('szczegoly_planu', pk=plan.pk)

@login_required
def dodaj_cwiczenie_do_dnia(request, dzien_pk):
    dzien = get_object_or_404(DzienPlanTreningowego, pk=dzien_pk, plan__uzytkownik=request.user)
    if request.method == 'POST':
        formularz = CwiczenieDniaForm(request.POST)
        if formularz.is_valid():
            cwiczenie_dnia = formularz.save(commit=False)
            cwiczenie_dnia.dzien = dzien
            cwiczenie_dnia.save()
            messages.success(request, 'Ćwiczenie dodane do planu!')
            return redirect('szczegoly_planu', pk=dzien.plan.pk)
    else:
        formularz = CwiczenieDniaForm()
    return render(request, 'tracker/dodaj_cwiczenie_do_dnia.html', {
        'formularz': formularz,
        'dzien': dzien,
    })