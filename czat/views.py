import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .kontekst import zbuduj_kontekst
from .klient import BladCzatu, czat_skonfigurowany, zapytaj_model
from .models import WiadomoscCzatu

LIMIT_WYSWIETLANYCH = 50


def wyslane_dzisiaj(uzytkownik):
    return WiadomoscCzatu.objects.filter(
        uzytkownik=uzytkownik, rola='user', utworzono__date=timezone.localdate()
    ).count()


def ostatnie_wiadomosci(uzytkownik, ile):
    wiadomosci = list(
        WiadomoscCzatu.objects.filter(uzytkownik=uzytkownik).order_by('-pk')[:ile])
    wiadomosci.reverse()
    return wiadomosci


@login_required
def czat(request):
    return render(request, 'czat/czat.html', {
        'historia': ostatnie_wiadomosci(request.user, LIMIT_WYSWIETLANYCH),
        'skonfigurowany': czat_skonfigurowany(),
        'pozostalo': max(0, settings.CZAT_DZIENNY_LIMIT - wyslane_dzisiaj(request.user)),
        'maks_znakow': settings.CZAT_MAKS_ZNAKOW,
    })


@login_required
@require_POST
def wyslij(request):
    if not czat_skonfigurowany():
        return JsonResponse({'blad': 'Czat nie jest skonfigurowany.'}, status=503)
    try:
        dane = json.loads(request.body)
        tresc = dane['tresc']
        if not isinstance(tresc, str):
            raise TypeError
        tresc = tresc.strip()
        uzyj_danych = bool(dane.get('uzyj_danych', False))
    except (ValueError, KeyError, TypeError):
        return JsonResponse({'blad': 'Niepoprawne dane.'}, status=400)
    if not tresc:
        return JsonResponse({'blad': 'Wpisz pytanie.'}, status=400)
    if len(tresc) > settings.CZAT_MAKS_ZNAKOW:
        return JsonResponse(
            {'blad': f'Wiadomość jest za długa (maksymalnie {settings.CZAT_MAKS_ZNAKOW} znaków).'},
            status=400)
    if wyslane_dzisiaj(request.user) >= settings.CZAT_DZIENNY_LIMIT:
        return JsonResponse(
            {'blad': 'Wykorzystano dzienny limit wiadomości. Wróć jutro.'}, status=429)

    poprzednie = ostatnie_wiadomosci(request.user, settings.CZAT_HISTORIA)
    while poprzednie and poprzednie[0].rola != 'user':
        poprzednie.pop(0)
    historia = [{'role': w.rola, 'content': w.tresc} for w in poprzednie]
    historia.append({'role': 'user', 'content': tresc})
    kontekst = zbuduj_kontekst(request.user) if uzyj_danych else ''

    try:
        odpowiedz = zapytaj_model(historia, kontekst)
    except BladCzatu as blad:
        return JsonResponse({'blad': blad.komunikat}, status=blad.status)

    with transaction.atomic():
        WiadomoscCzatu.objects.create(uzytkownik=request.user, rola='user', tresc=tresc)
        WiadomoscCzatu.objects.create(
            uzytkownik=request.user, rola='assistant', tresc=odpowiedz)
    return JsonResponse({
        'odpowiedz': odpowiedz,
        'pozostalo': max(0, settings.CZAT_DZIENNY_LIMIT - wyslane_dzisiaj(request.user)),
    })


@login_required
@require_POST
def wyczysc(request):
    WiadomoscCzatu.objects.filter(uzytkownik=request.user).delete()
    return redirect('czat')
