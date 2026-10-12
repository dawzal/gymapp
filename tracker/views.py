import json
import math
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    CwiczenieForm, CwiczeniePlanuForm, NowyWpisForm, PlanTreningowyForm, SeriaFormSet,
    SesjaForm, WpisForm,
)
from .models import (
    Cwiczenie, CwiczeniePlanu, PlanTreningowy, SeriaWpisu, SesjaTreningowa, WpisDziennika,
)


def pokaz_formularz(request, formularz, tytul, przycisk, anuluj, podtytul='', przycisk_kolejny=''):
    return render(request, 'formularz.html', {
        'formularz': formularz,
        'tytul': tytul,
        'podtytul': podtytul,
        'przycisk': przycisk,
        'przycisk_kolejny': przycisk_kolejny,
        'anuluj': anuluj,
    })


def usun_obiekt(request, obiekt, tytul, opis, ostrzezenie, anuluj, po_usunieciu, komunikat):
    if request.method == 'POST':
        obiekt.delete()
        messages.success(request, komunikat)
        return redirect(po_usunieciu)
    return render(request, 'potwierdz_usuniecie.html', {
        'tytul': tytul,
        'opis': opis,
        'ostrzezenie': ostrzezenie,
        'anuluj': anuluj,
    })


@login_required
def dashboard(request):
    moje_plany = PlanTreningowy.objects.filter(uzytkownik=request.user).annotate(
        liczba_cwiczen=Count('cwiczenia')
    )[:6]
    sesje = SesjaTreningowa.objects.filter(uzytkownik=request.user)
    ostatnia_sesja = sesje.annotate(
        liczba_cwiczen=Count('wpisy')
    ).order_by('-data', '-pk').first()
    poczatek_tygodnia = timezone.localdate() - timedelta(days=6)
    return render(request, 'tracker/dashboard.html', {
        'moje_plany': moje_plany,
        'ostatnia_sesja': ostatnia_sesja,
        'sesje_w_tygodniu': sesje.filter(data__gte=poczatek_tygodnia).count(),
    })


@login_required
def lista_cwiczen(request):
    kategoria = request.GET.get('kategoria', '')
    cwiczenia = Cwiczenie.dostepne_dla(request.user).select_related('dodane_przez')
    if kategoria:
        cwiczenia = cwiczenia.filter(kategoria=kategoria)
    return render(request, 'tracker/lista_cwiczen.html', {
        'cwiczenia': cwiczenia,
        'kategoria': kategoria,
        'kategorie': Cwiczenie.KATEGORIE,
    })


@login_required
def dodaj_cwiczenie(request):
    formularz = CwiczenieForm(request.POST or None)
    if formularz.is_valid():
        cwiczenie = formularz.save(commit=False)
        cwiczenie.dodane_przez = request.user
        cwiczenie.save()
        messages.success(request, 'Ćwiczenie zostało dodane!')
        return redirect('lista_cwiczen')
    return pokaz_formularz(
        request, formularz, 'Dodaj nowe ćwiczenie', 'Zapisz ćwiczenie', reverse('lista_cwiczen'))


@login_required
def edytuj_cwiczenie(request, pk):
    cwiczenie = get_object_or_404(Cwiczenie, pk=pk, dodane_przez=request.user)
    formularz = CwiczenieForm(request.POST or None, instance=cwiczenie)
    if formularz.is_valid():
        formularz.save()
        messages.success(request, 'Ćwiczenie zostało zaktualizowane!')
        return redirect('lista_cwiczen')
    return pokaz_formularz(
        request, formularz, f'Edytuj ćwiczenie: {cwiczenie.nazwa}', 'Zapisz zmiany',
        reverse('lista_cwiczen'))


@login_required
def lista_planow(request):
    moje_plany = PlanTreningowy.objects.filter(uzytkownik=request.user).annotate(
        liczba_cwiczen=Count('cwiczenia')
    )
    return render(request, 'tracker/lista_planow.html', {'moje_plany': moje_plany})


@login_required
def dodaj_plan(request):
    formularz = PlanTreningowyForm(request.POST or None)
    if formularz.is_valid():
        plan = formularz.save(commit=False)
        plan.uzytkownik = request.user
        plan.save()
        messages.success(request, 'Plan treningowy został utworzony!')
        return redirect('szczegoly_planu', pk=plan.pk)
    return pokaz_formularz(
        request, formularz, 'Utwórz nowy plan treningowy', 'Utwórz plan', reverse('lista_planow'))


@login_required
def szczegoly_planu(request, pk):
    plan = get_object_or_404(PlanTreningowy, pk=pk, uzytkownik=request.user)
    cwiczenia = plan.cwiczenia.select_related('cwiczenie')
    return render(request, 'tracker/szczegoly_planu.html', {'plan': plan, 'cwiczenia': cwiczenia})


@login_required
@require_POST
def zmien_kolejnosc(request, plan_pk):
    plan = get_object_or_404(PlanTreningowy, pk=plan_pk, uzytkownik=request.user)
    try:
        identyfikatory = [int(pk) for pk in json.loads(request.body)['kolejnosc']]
    except (ValueError, KeyError, TypeError):
        return JsonResponse({'blad': 'Niepoprawne dane.'}, status=400)
    cwiczenia = {c.pk: c for c in plan.cwiczenia.all()}
    if sorted(identyfikatory) != sorted(cwiczenia):
        return JsonResponse({'blad': 'Lista ćwiczeń nie pasuje do planu.'}, status=400)
    for pozycja, pk in enumerate(identyfikatory):
        cwiczenia[pk].kolejnosc = pozycja
    CwiczeniePlanu.objects.bulk_update(cwiczenia.values(), ['kolejnosc'])
    return JsonResponse({'ok': True})


@login_required
def edytuj_plan(request, pk):
    plan = get_object_or_404(PlanTreningowy, pk=pk, uzytkownik=request.user)
    formularz = PlanTreningowyForm(request.POST or None, instance=plan)
    if formularz.is_valid():
        formularz.save()
        messages.success(request, 'Plan treningowy został zaktualizowany!')
        return redirect('szczegoly_planu', pk=plan.pk)
    return pokaz_formularz(
        request, formularz, f'Edytuj plan: {plan.nazwa}', 'Zapisz zmiany',
        reverse('szczegoly_planu', args=[plan.pk]))


@login_required
def usun_plan(request, pk):
    plan = get_object_or_404(PlanTreningowy, pk=pk, uzytkownik=request.user)
    return usun_obiekt(
        request, plan,
        tytul='Usuń plan',
        opis=f'Czy na pewno chcesz usunąć plan treningowy "{plan.nazwa}"?',
        ostrzezenie='Ta operacja jest nieodwracalna. Wszystkie ćwiczenia w tym planie zostaną usunięte.',
        anuluj=reverse('szczegoly_planu', args=[plan.pk]),
        po_usunieciu='lista_planow',
        komunikat='Plan treningowy został usunięty!',
    )


@login_required
def dodaj_cwiczenie_do_planu(request, plan_pk):
    plan = get_object_or_404(PlanTreningowy, pk=plan_pk, uzytkownik=request.user)
    formularz = CwiczeniePlanuForm(request.POST or None, uzytkownik=request.user)
    if formularz.is_valid():
        cwiczenie_planu = formularz.save(commit=False)
        cwiczenie_planu.plan = plan
        cwiczenie_planu.save()
        messages.success(request, 'Ćwiczenie dodane do planu!')
        if 'dodaj_kolejne' in request.POST:
            return redirect('dodaj_cwiczenie_do_planu', plan_pk=plan.pk)
        return redirect('szczegoly_planu', pk=plan.pk)
    return pokaz_formularz(
        request, formularz, f'Dodaj ćwiczenie do planu: {plan.nazwa}', 'Dodaj ćwiczenie',
        reverse('szczegoly_planu', args=[plan.pk]),
        przycisk_kolejny='Dodaj i dodaj kolejne')


@login_required
def edytuj_cwiczenie_planu(request, pk):
    cwiczenie_planu = get_object_or_404(
        CwiczeniePlanu.objects.select_related('plan', 'cwiczenie'),
        pk=pk, plan__uzytkownik=request.user)
    formularz = CwiczeniePlanuForm(
        request.POST or None, instance=cwiczenie_planu, uzytkownik=request.user)
    if formularz.is_valid():
        formularz.save()
        messages.success(request, 'Ćwiczenie zostało zaktualizowane!')
        return redirect('szczegoly_planu', pk=cwiczenie_planu.plan.pk)
    return pokaz_formularz(
        request, formularz, f'Edytuj ćwiczenie: {cwiczenie_planu.cwiczenie.nazwa}', 'Zapisz zmiany',
        reverse('szczegoly_planu', args=[cwiczenie_planu.plan.pk]),
        podtytul=f'Plan: {cwiczenie_planu.plan.nazwa}')


@login_required
def usun_cwiczenie_planu(request, pk):
    cwiczenie_planu = get_object_or_404(
        CwiczeniePlanu.objects.select_related('plan', 'cwiczenie'),
        pk=pk, plan__uzytkownik=request.user)
    plan_pk = cwiczenie_planu.plan.pk
    return usun_obiekt(
        request, cwiczenie_planu,
        tytul='Usuń ćwiczenie z planu',
        opis=f'Czy na pewno chcesz usunąć ćwiczenie "{cwiczenie_planu.cwiczenie.nazwa}" z planu "{cwiczenie_planu.plan.nazwa}"?',
        ostrzezenie='Ta operacja jest nieodwracalna.',
        anuluj=reverse('szczegoly_planu', args=[plan_pk]),
        po_usunieciu=reverse('szczegoly_planu', args=[plan_pk]),
        komunikat='Ćwiczenie zostało usunięte z planu!',
    )


@login_required
def gotowe_plany(request):
    plany = PlanTreningowy.objects.filter(uzytkownik__isnull=True).prefetch_related(
        'cwiczenia__cwiczenie'
    ).order_by('poziom', 'nazwa')
    return render(request, 'tracker/gotowe_plany.html', {'plany': plany})


@login_required
def uzyj_gotowego_planu(request, pk):
    szablon = get_object_or_404(PlanTreningowy, pk=pk, uzytkownik__isnull=True)
    if request.method != 'POST':
        return redirect('gotowe_plany')
    with transaction.atomic():
        kopia = szablon.kopiuj_dla(request.user)
    messages.success(request, f'Plan "{kopia.nazwa}" został dodany do Twoich planów. Możesz go dowolnie edytować.')
    return redirect('szczegoly_planu', pk=kopia.pk)


@login_required
def rozpocznij_trening(request, plan_pk):
    plan = get_object_or_404(PlanTreningowy, pk=plan_pk, uzytkownik=request.user)
    if request.method != 'POST':
        return redirect('szczegoly_planu', pk=plan.pk)
    cwiczenia = list(plan.cwiczenia.select_related('cwiczenie'))
    if not cwiczenia:
        messages.error(request, 'Plan nie zawiera jeszcze ćwiczeń.')
        return redirect('szczegoly_planu', pk=plan.pk)
    with transaction.atomic():
        sesja = SesjaTreningowa.objects.create(
            uzytkownik=request.user,
            data=timezone.localdate(),
            nazwa=f"Trening: {plan.nazwa}",
        )
        serie = []
        for c in cwiczenia:
            wpis = WpisDziennika.objects.create(
                sesja=sesja, cwiczenie=c.cwiczenie, notatki=c.notatki)
            serie.extend(
                SeriaWpisu(wpis=wpis, powtorzenia=c.powtorzenia, ciezar=c.ciezar)
                for _ in range(c.serie)
            )
        SeriaWpisu.objects.bulk_create(serie)
    messages.success(request, f'Rozpoczęto trening: {plan.nazwa}!')
    return redirect('szczegoly_sesji', pk=sesja.pk)


@login_required
def dziennik(request):
    sesje = SesjaTreningowa.objects.filter(uzytkownik=request.user).annotate(
        liczba_cwiczen=Count('wpisy')
    )
    return render(request, 'tracker/dziennik.html', {'sesje': sesje})


@login_required
def dodaj_sesje(request):
    formularz = SesjaForm(request.POST or None, initial={'data': timezone.localdate()})
    if formularz.is_valid():
        sesja = formularz.save(commit=False)
        sesja.uzytkownik = request.user
        sesja.save()
        messages.success(request, 'Sesja treningowa dodana!')
        return redirect('szczegoly_sesji', pk=sesja.pk)
    return pokaz_formularz(
        request, formularz, 'Trening bez planu', 'Zacznij trening', reverse('dziennik'),
        podtytul='Zapisz trening od zera i dodawaj ćwiczenia w trakcie.')


def strona_sesji(request, sesja, formularz, bledny_zestaw=None):
    wpisy = sesja.wpisy.select_related('cwiczenie').prefetch_related('serie')
    karty = []
    for wpis in wpisy:
        if bledny_zestaw is not None and bledny_zestaw.instance.pk == wpis.pk:
            zestaw = bledny_zestaw
        else:
            zestaw = SeriaFormSet(instance=wpis, prefix=f'serie{wpis.pk}')
        karty.append({'wpis': wpis, 'zestaw': zestaw})
    return render(request, 'tracker/szczegoly_sesji.html', {
        'sesja': sesja,
        'karty': karty,
        'formularz': formularz,
    })


@login_required
def szczegoly_sesji(request, pk):
    sesja = get_object_or_404(SesjaTreningowa, pk=pk, uzytkownik=request.user)
    formularz = NowyWpisForm(request.POST or None, uzytkownik=request.user)
    if formularz.is_valid():
        formularz.zapisz(sesja)
        messages.success(request, 'Ćwiczenie dodane do sesji!')
        return redirect('szczegoly_sesji', pk=sesja.pk)
    return strona_sesji(request, sesja, formularz)


@login_required
def zapisz_serie(request, pk):
    wpis = get_object_or_404(
        WpisDziennika.objects.select_related('sesja', 'cwiczenie'),
        pk=pk, sesja__uzytkownik=request.user)
    if request.method != 'POST':
        return redirect('szczegoly_sesji', pk=wpis.sesja.pk)
    zestaw = SeriaFormSet(request.POST, instance=wpis, prefix=f'serie{wpis.pk}')
    if zestaw.is_valid():
        zestaw.save()
        messages.success(request, f'Zapisano serie: {wpis.cwiczenie.nazwa}.')
        return redirect('szczegoly_sesji', pk=wpis.sesja.pk)
    return strona_sesji(
        request, wpis.sesja, NowyWpisForm(uzytkownik=request.user), bledny_zestaw=zestaw)


@login_required
def edytuj_sesje(request, pk):
    sesja = get_object_or_404(SesjaTreningowa, pk=pk, uzytkownik=request.user)
    formularz = SesjaForm(request.POST or None, instance=sesja)
    if formularz.is_valid():
        formularz.save()
        messages.success(request, 'Sesja została zaktualizowana!')
        return redirect('szczegoly_sesji', pk=sesja.pk)
    return pokaz_formularz(
        request, formularz, 'Edytuj sesję treningową', 'Zapisz zmiany',
        reverse('szczegoly_sesji', args=[sesja.pk]))


@login_required
def usun_sesje(request, pk):
    sesja = get_object_or_404(SesjaTreningowa, pk=pk, uzytkownik=request.user)
    return usun_obiekt(
        request, sesja,
        tytul='Usuń sesję',
        opis=f'Czy na pewno chcesz usunąć sesję treningową z dnia {sesja.data:%d.%m.%Y}?',
        ostrzezenie='Ta operacja jest nieodwracalna. Wszystkie wpisy z tej sesji zostaną usunięte.',
        anuluj=reverse('szczegoly_sesji', args=[sesja.pk]),
        po_usunieciu='dziennik',
        komunikat='Sesja treningowa została usunięta!',
    )


@login_required
def edytuj_wpis(request, pk):
    wpis = get_object_or_404(
        WpisDziennika.objects.select_related('sesja', 'cwiczenie'),
        pk=pk, sesja__uzytkownik=request.user)
    formularz = WpisForm(request.POST or None, instance=wpis, uzytkownik=request.user)
    if formularz.is_valid():
        formularz.save()
        messages.success(request, 'Wpis został zaktualizowany!')
        return redirect('szczegoly_sesji', pk=wpis.sesja.pk)
    return pokaz_formularz(
        request, formularz, f'Edytuj wpis: {wpis.cwiczenie.nazwa}', 'Zapisz zmiany',
        reverse('szczegoly_sesji', args=[wpis.sesja.pk]),
        podtytul=f'Sesja: {wpis.sesja.data:%d.%m.%Y}')


@login_required
def usun_wpis(request, pk):
    wpis = get_object_or_404(
        WpisDziennika.objects.select_related('sesja', 'cwiczenie'),
        pk=pk, sesja__uzytkownik=request.user)
    sesja_pk = wpis.sesja.pk
    return usun_obiekt(
        request, wpis,
        tytul='Usuń wpis',
        opis=f'Czy na pewno chcesz usunąć ćwiczenie "{wpis.cwiczenie.nazwa}" wraz z jego seriami z tej sesji?',
        ostrzezenie='Ta operacja jest nieodwracalna.',
        anuluj=reverse('szczegoly_sesji', args=[sesja_pk]),
        po_usunieciu=reverse('szczegoly_sesji', args=[sesja_pk]),
        komunikat='Wpis został usunięty!',
    )


PROCENTY_1RM = [
    (95, 'Siła maksymalna (1-2 powt.)'),
    (85, 'Siła (3-5 powt.)'),
    (75, 'Hipertrofia (8-12 powt.)'),
    (65, 'Wytrzymałość (15+ powt.)'),
    (50, 'Rozgrzewka'),
]


def oblicz_1rm(ciezar, powtorzenia):
    return round(ciezar * (36 / (37 - powtorzenia)), 2)


@login_required
def kalkulator_1rm(request):
    wynik = None
    tabela = []
    if request.method == 'POST':
        try:
            ciezar = float(request.POST.get('ciezar', 0))
            powtorzenia = int(request.POST.get('powtorzenia', 0))
        except ValueError:
            messages.error(request, 'Podaj liczby!')
        else:
            if math.isfinite(ciezar) and 0 < ciezar <= 1000 and 1 <= powtorzenia <= 36:
                wynik = oblicz_1rm(ciezar, powtorzenia)
                tabela = [
                    {'procent': procent, 'ciezar': round(wynik * procent / 100, 1), 'cel': cel}
                    for procent, cel in PROCENTY_1RM
                ]
            else:
                messages.error(request, 'Podaj prawidłowe wartości!')
    return render(request, 'tracker/kalkulator_1rm.html', {'wynik': wynik, 'tabela': tabela})


@login_required
def statystyki(request):
    sesje = SesjaTreningowa.objects.filter(uzytkownik=request.user)
    wpisy = WpisDziennika.objects.filter(sesja__uzytkownik=request.user)
    ulubione_cwiczenia = wpisy.values(
        'cwiczenie__nazwa'
    ).annotate(
        liczba=Count('id')
    ).order_by('-liczba', 'cwiczenie__nazwa')[:5]
    ostatnie_dni = list(
        sesje.values('data').annotate(
            liczba_cwiczen=Count('wpisy')
        ).order_by('-data')[:10]
    )
    ostatnie_dni.reverse()
    return render(request, 'tracker/statystyki.html', {
        'liczba_sesji': sesje.count(),
        'liczba_wpisow': wpisy.count(),
        'liczba_roznych_cwiczen': wpisy.values('cwiczenie').distinct().count(),
        'ulubione_cwiczenia': ulubione_cwiczenia,
        'etykiety_wykresu': [d['data'].isoformat() for d in ostatnie_dni],
        'wartosci_wykresu': [d['liczba_cwiczen'] for d in ostatnie_dni],
    })
