from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from .models import Cwiczenie, PlanTreningowy, CwiczeniePlanu, SesjaTreningowa, WpisDziennika
from .forms import CwiczenieForm, PlanTreningowyForm, CwiczeniePlanuForm, SesjaForm, WpisForm


@login_required
def dashboard(request):
    moje_plany = PlanTreningowy.objects.filter(uzytkownik=request.user)[:3]
    return render(request, 'tracker/dashboard.html', {
        'moje_plany': moje_plany,
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
def edytuj_cwiczenie(request, pk):
    cwiczenie = get_object_or_404(Cwiczenie, pk=pk, dodane_przez=request.user)
    if request.method == 'POST':
        formularz = CwiczenieForm(request.POST, instance=cwiczenie)
        if formularz.is_valid():
            formularz.save()
            messages.success(request, 'Ćwiczenie zostało zaktualizowane!')
            return redirect('lista_cwiczen')
    else:
        formularz = CwiczenieForm(instance=cwiczenie)
    return render(request, 'tracker/edytuj_cwiczenie.html', {'formularz': formularz, 'cwiczenie': cwiczenie})


@login_required
def lista_planow(request):
    moje_plany = PlanTreningowy.objects.filter(uzytkownik=request.user)
    return render(request, 'tracker/lista_planow.html', {
        'moje_plany': moje_plany,
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
    cwiczenia = plan.cwiczenia.all()
    return render(request, 'tracker/szczegoly_planu.html', {
        'plan': plan,
        'cwiczenia': cwiczenia,
    })


@login_required
def dodaj_cwiczenie_do_planu(request, plan_pk):
    plan = get_object_or_404(PlanTreningowy, pk=plan_pk, uzytkownik=request.user)
    if request.method == 'POST':
        formularz = CwiczeniePlanuForm(request.POST)
        if formularz.is_valid():
            cwiczenie_planu = formularz.save(commit=False)
            cwiczenie_planu.plan = plan
            cwiczenie_planu.save()
            messages.success(request, 'Ćwiczenie dodane do planu!')
            return redirect('szczegoly_planu', pk=plan.pk)
    else:
        formularz = CwiczeniePlanuForm()
    return render(request, 'tracker/dodaj_cwiczenie_do_planu.html', {
        'formularz': formularz,
        'plan': plan,
    })


@login_required
def edytuj_cwiczenie_planu(request, pk):
    cwiczenie_planu = get_object_or_404(CwiczeniePlanu, pk=pk, plan__uzytkownik=request.user)
    if request.method == 'POST':
        formularz = CwiczeniePlanuForm(request.POST, instance=cwiczenie_planu)
        if formularz.is_valid():
            formularz.save()
            messages.success(request, 'Ćwiczenie zostało zaktualizowane!')
            return redirect('szczegoly_planu', pk=cwiczenie_planu.plan.pk)
    else:
        formularz = CwiczeniePlanuForm(instance=cwiczenie_planu)
    return render(request, 'tracker/edytuj_cwiczenie_planu.html', {
        'formularz': formularz,
        'cwiczenie_planu': cwiczenie_planu,
    })


@login_required
def usun_cwiczenie_planu(request, pk):
    cwiczenie_planu = get_object_or_404(CwiczeniePlanu, pk=pk, plan__uzytkownik=request.user)
    plan_pk = cwiczenie_planu.plan.pk
    if request.method == 'POST':
        cwiczenie_planu.delete()
        messages.success(request, 'Ćwiczenie zostało usunięte z planu!')
        return redirect('szczegoly_planu', pk=plan_pk)
    return render(request, 'tracker/usun_cwiczenie_planu.html', {'cwiczenie_planu': cwiczenie_planu})


@login_required
def edytuj_plan(request, pk):
    plan = get_object_or_404(PlanTreningowy, pk=pk, uzytkownik=request.user)
    if request.method == 'POST':
        formularz = PlanTreningowyForm(request.POST, instance=plan)
        if formularz.is_valid():
            formularz.save()
            messages.success(request, 'Plan treningowy został zaktualizowany!')
            return redirect('szczegoly_planu', pk=plan.pk)
    else:
        formularz = PlanTreningowyForm(instance=plan)
    return render(request, 'tracker/edytuj_plan.html', {'formularz': formularz, 'plan': plan})


@login_required
def usun_plan(request, pk):
    plan = get_object_or_404(PlanTreningowy, pk=pk, uzytkownik=request.user)
    if request.method == 'POST':
        plan.delete()
        messages.success(request, 'Plan treningowy został usunięty!')
        return redirect('lista_planow')
    return render(request, 'tracker/usun_plan.html', {'plan': plan})


@login_required
def dziennik(request):
    sesje = SesjaTreningowa.objects.filter(uzytkownik=request.user)
    return render(request, 'tracker/dziennik.html', {'sesje': sesje})


@login_required
def dodaj_sesje(request):
    if request.method == 'POST':
        formularz = SesjaForm(request.POST)
        if formularz.is_valid():
            sesja = formularz.save(commit=False)
            sesja.uzytkownik = request.user
            sesja.save()
            messages.success(request, 'Sesja treningowa dodana!')
            return redirect('szczegoly_sesji', pk=sesja.pk)
    else:
        formularz = SesjaForm()
    return render(request, 'tracker/dodaj_sesje.html', {'formularz': formularz})


@login_required
def szczegoly_sesji(request, pk):
    sesja = get_object_or_404(SesjaTreningowa, pk=pk, uzytkownik=request.user)
    wpisy = sesja.wpisy.all()
    if request.method == 'POST':
        formularz = WpisForm(request.POST)
        if formularz.is_valid():
            wpis = formularz.save(commit=False)
            wpis.sesja = sesja
            wpis.save()
            messages.success(request, 'Ćwiczenie zapisane!')
            return redirect('szczegoly_sesji', pk=sesja.pk)
    else:
        formularz = WpisForm()
    return render(request, 'tracker/szczegoly_sesji.html', {
        'sesja': sesja,
        'wpisy': wpisy,
        'formularz': formularz,
    })


@login_required
def edytuj_sesje(request, pk):
    sesja = get_object_or_404(SesjaTreningowa, pk=pk, uzytkownik=request.user)
    if request.method == 'POST':
        formularz = SesjaForm(request.POST, instance=sesja)
        if formularz.is_valid():
            formularz.save()
            messages.success(request, 'Sesja została zaktualizowana!')
            return redirect('szczegoly_sesji', pk=sesja.pk)
    else:
        formularz = SesjaForm(instance=sesja)
    return render(request, 'tracker/edytuj_sesje.html', {'formularz': formularz, 'sesja': sesja})


@login_required
def usun_sesje(request, pk):
    sesja = get_object_or_404(SesjaTreningowa, pk=pk, uzytkownik=request.user)
    if request.method == 'POST':
        sesja.delete()
        messages.success(request, 'Sesja treningowa została usunięta!')
        return redirect('dziennik')
    return render(request, 'tracker/usun_sesje.html', {'sesja': sesja})


@login_required
def edytuj_wpis(request, pk):
    wpis = get_object_or_404(WpisDziennika, pk=pk, sesja__uzytkownik=request.user)
    if request.method == 'POST':
        formularz = WpisForm(request.POST, instance=wpis)
        if formularz.is_valid():
            formularz.save()
            messages.success(request, 'Wpis został zaktualizowany!')
            return redirect('szczegoly_sesji', pk=wpis.sesja.pk)
    else:
        formularz = WpisForm(instance=wpis)
    return render(request, 'tracker/edytuj_wpis.html', {
        'formularz': formularz,
        'wpis': wpis,
    })


@login_required
def usun_wpis(request, pk):
    wpis = get_object_or_404(WpisDziennika, pk=pk, sesja__uzytkownik=request.user)
    sesja_pk = wpis.sesja.pk
    if request.method == 'POST':
        wpis.delete()
        messages.success(request, 'Wpis został usunięty!')
        return redirect('szczegoly_sesji', pk=sesja_pk)
    return render(request, 'tracker/usun_wpis.html', {'wpis': wpis})


@login_required
def kalkulator_1rm(request):
    wynik = None
    if request.method == 'POST':
        try:
            ciezar = float(request.POST.get('ciezar', 0))
            powtorzenia = int(request.POST.get('powtorzenia', 0))
            if ciezar > 0 and 1 <= powtorzenia <= 36:
                wynik = round(ciezar * (36 / (37 - powtorzenia)), 2)
            else:
                messages.error(request, 'Podaj prawidłowe wartości!')
        except ValueError:
            messages.error(request, 'Podaj liczby!')
    return render(request, 'tracker/kalkulator_1rm.html', {'wynik': wynik})


@login_required
def statystyki(request):
    sesje = SesjaTreningowa.objects.filter(uzytkownik=request.user)
    liczba_sesji = sesje.count()
    wpisy = WpisDziennika.objects.filter(sesja__uzytkownik=request.user)
    liczba_wpisow = wpisy.count()
    ulubione_cwiczenia = wpisy.values(
        'cwiczenie__nazwa'
    ).annotate(
        liczba=Count('id')
    ).order_by('-liczba')[:5]
    dane_wykres = sesje.values('data').annotate(
        liczba_cwiczen=Count('wpisy')
    ).order_by('data')[:10]
    return render(request, 'tracker/statystyki.html', {
        'liczba_sesji': liczba_sesji,
        'liczba_wpisow': liczba_wpisow,
        'ulubione_cwiczenia': ulubione_cwiczenia,
        'dane_wykres': dane_wykres,
    })

@login_required
def rozpocznij_trening(request, plan_pk):
    plan = get_object_or_404(PlanTreningowy, pk=plan_pk, uzytkownik=request.user)
    if request.method == 'POST':
        with transaction.atomic():
            sesja = SesjaTreningowa.objects.create(
                uzytkownik=request.user,
                data=timezone.localdate(),
                nazwa=f"Trening: {plan.nazwa}",
            )
            WpisDziennika.objects.bulk_create([
                WpisDziennika(
                    sesja=sesja,
                    cwiczenie=c.cwiczenie,
                    serie=c.serie,
                    powtorzenia=c.powtorzenia,
                    ciezar=c.ciezar,
                )
                for c in plan.cwiczenia.select_related('cwiczenie')
            ])
        messages.success(request, f'Rozpoczęto trening: {plan.nazwa}!')
        return redirect('szczegoly_sesji', pk=sesja.pk)
    return render(request, 'tracker/rozpocznij_trening.html', {'plan': plan})
