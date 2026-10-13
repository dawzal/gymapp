from django.db.models import Q

from .models import SeriaWpisu, SesjaTreningowa


def oblicz_1rm(ciezar, powtorzenia):
    return round(ciezar * (36 / (37 - powtorzenia)), 2)


def szacowane_1rm(ciezar, powtorzenia):
    if powtorzenia < 1 or powtorzenia > 36:
        return None
    return oblicz_1rm(float(ciezar), powtorzenia)


def wykonane_serie():
    return SeriaWpisu.objects.filter(wykonana=True)


def wczesniejsze_serie(sesja):
    return Q(wpis__sesja__uzytkownik=sesja.uzytkownik) & (
        Q(wpis__sesja__data__lt=sesja.data)
        | Q(wpis__sesja__data=sesja.data, wpis__sesja_id__lt=sesja.pk)
    )


def ostatnie_serie(sesja, cwiczenia_ids):
    serie = (
        wykonane_serie()
        .filter(wczesniejsze_serie(sesja), wpis__cwiczenie_id__in=list(cwiczenia_ids))
        .select_related('wpis__sesja')
        .order_by('-wpis__sesja__data', '-wpis__sesja_id', '-wpis_id', 'pk')
    )
    wynik = {}
    for seria in serie:
        cwiczenie_id = seria.wpis.cwiczenie_id
        if cwiczenie_id not in wynik:
            wynik[cwiczenie_id] = {
                'data': seria.wpis.sesja.data,
                'wpis_id': seria.wpis_id,
                'serie': [],
            }
        if wynik[cwiczenie_id]['wpis_id'] == seria.wpis_id:
            wynik[cwiczenie_id]['serie'].append(seria)
    return wynik


def najlepsze_dla_cwiczen(uzytkownik, cwiczenia_ids):
    dane = wykonane_serie().filter(
        wpis__sesja__uzytkownik=uzytkownik, wpis__cwiczenie_id__in=list(cwiczenia_ids)
    ).values_list('wpis__cwiczenie_id', 'wpis__sesja__data', 'powtorzenia', 'ciezar')
    wynik = {}
    for cwiczenie_id, data, powtorzenia, ciezar in dane:
        pozycja = wynik.setdefault(cwiczenie_id, {'rm': None, 'maks_powtorzen': 0})
        pozycja['maks_powtorzen'] = max(pozycja['maks_powtorzen'], powtorzenia)
        wartosc = szacowane_1rm(ciezar, powtorzenia)
        if wartosc and (pozycja['rm'] is None or wartosc > pozycja['rm']['rm']):
            pozycja['rm'] = {
                'rm': wartosc, 'powtorzenia': powtorzenia, 'ciezar': ciezar, 'data': data,
            }
    return wynik


def rekordy_wpisow(sesja, wpisy):
    cwiczenia_ids = {wpis.cwiczenie_id for wpis in wpisy}
    poprzednie = {}
    historia = wykonane_serie().filter(
        wczesniejsze_serie(sesja), wpis__cwiczenie_id__in=cwiczenia_ids
    ).values_list('wpis__cwiczenie_id', 'powtorzenia', 'ciezar')
    for cwiczenie_id, powtorzenia, ciezar in historia:
        wartosc = szacowane_1rm(ciezar, powtorzenia)
        if wartosc is not None and wartosc > poprzednie.get(cwiczenie_id, 0):
            poprzednie[cwiczenie_id] = wartosc
    wynik = {}
    for wpis in wpisy:
        dotychczasowy = poprzednie.get(wpis.cwiczenie_id)
        if not dotychczasowy:
            continue
        obecny = max(
            (
                szacowane_1rm(s.ciezar, s.powtorzenia) or 0
                for s in wpis.serie.all() if s.wykonana
            ),
            default=0,
        )
        if obecny > dotychczasowy:
            wynik[wpis.pk] = {'poprzedni': dotychczasowy, 'obecny': obecny}
    return wynik


def progres_cwiczenia(uzytkownik, cwiczenie_id, od_daty=None):
    serie = wykonane_serie().filter(
        wpis__sesja__uzytkownik=uzytkownik, wpis__cwiczenie_id=cwiczenie_id)
    if od_daty is not None:
        serie = serie.filter(wpis__sesja__data__gte=od_daty)
    dane = serie.values_list(
        'wpis__sesja__data', 'powtorzenia', 'ciezar').order_by('wpis__sesja__data')
    po_dniach = {}
    for data, powtorzenia, ciezar in dane:
        ciezar = float(ciezar)
        dzien = po_dniach.setdefault(data, {
            'data': data,
            'ciezar': 0.0, 'powt_ciezar': 0,
            'rm': None, 'powt_rm': None, 'ciezar_rm': None,
            'powt_maks': 0,
        })
        dzien['powt_maks'] = max(dzien['powt_maks'], powtorzenia)
        if ciezar > dzien['ciezar'] or (
                ciezar == dzien['ciezar'] and powtorzenia > dzien['powt_ciezar']):
            dzien['ciezar'] = ciezar
            dzien['powt_ciezar'] = powtorzenia
        wartosc = szacowane_1rm(ciezar, powtorzenia)
        if wartosc and (dzien['rm'] is None or wartosc > dzien['rm']):
            dzien['rm'] = wartosc
            dzien['powt_rm'] = powtorzenia
            dzien['ciezar_rm'] = ciezar
    for dzien in po_dniach.values():
        dzien['powt_wykres'] = (
            dzien['powt_rm'] if dzien['powt_rm'] is not None else dzien['powt_maks'])
    return list(po_dniach.values())


def rekordy_uzytkownika(uzytkownik):
    najlepsze = {}
    dane = wykonane_serie().filter(wpis__sesja__uzytkownik=uzytkownik).values_list(
        'wpis__cwiczenie_id', 'wpis__cwiczenie__nazwa', 'wpis__sesja__data',
        'powtorzenia', 'ciezar')
    for cwiczenie_id, nazwa, data, powtorzenia, ciezar in dane:
        wartosc = szacowane_1rm(ciezar, powtorzenia)
        if not wartosc:
            continue
        if cwiczenie_id not in najlepsze or wartosc > najlepsze[cwiczenie_id]['rm']:
            najlepsze[cwiczenie_id] = {
                'nazwa': nazwa, 'data': data, 'powtorzenia': powtorzenia,
                'ciezar': ciezar, 'rm': wartosc,
            }
    return sorted(najlepsze.values(), key=lambda rekord: rekord['nazwa'])


def podsumowanie_sesji(sesja):
    wszystkie = list(SeriaWpisu.objects.filter(wpis__sesja=sesja))
    wykonane = [s for s in wszystkie if s.wykonana]
    return {
        'cwiczenia': sesja.wpisy.count(),
        'serie': len(wykonane),
        'serie_razem': len(wszystkie),
        'powtorzenia': sum(s.powtorzenia for s in wykonane),
        'objetosc': sum(s.powtorzenia * s.ciezar for s in wykonane),
    }


def sredni_czas_treningu(uzytkownik):
    czasy = [
        (koniec - poczatek).total_seconds()
        for poczatek, koniec in SesjaTreningowa.objects.filter(
            uzytkownik=uzytkownik, rozpoczeto__isnull=False, zakonczono__isnull=False
        ).values_list('rozpoczeto', 'zakonczono')
    ]
    if not czasy:
        return None
    return max(1, round(sum(czasy) / len(czasy) / 60))
