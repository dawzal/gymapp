from django.db.models import Q

from .models import SeriaWpisu, SesjaTreningowa


def oblicz_1rm(ciezar, powtorzenia):
    return round(ciezar * (36 / (37 - powtorzenia)), 2)


def szacowane_1rm(ciezar, powtorzenia):
    if powtorzenia < 1 or powtorzenia > 36:
        return None
    return oblicz_1rm(float(ciezar), powtorzenia)


def wczesniejsze_serie(sesja):
    return Q(wpis__sesja__uzytkownik=sesja.uzytkownik) & (
        Q(wpis__sesja__data__lt=sesja.data)
        | Q(wpis__sesja__data=sesja.data, wpis__sesja_id__lt=sesja.pk)
    )


def ostatnie_serie(sesja, cwiczenia_ids):
    serie = (
        SeriaWpisu.objects
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


def rekordy_wpisow(sesja, wpisy):
    cwiczenia_ids = {wpis.cwiczenie_id for wpis in wpisy}
    poprzednie = {}
    historia = SeriaWpisu.objects.filter(
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
            (szacowane_1rm(s.ciezar, s.powtorzenia) or 0 for s in wpis.serie.all()),
            default=0,
        )
        if obecny > dotychczasowy:
            wynik[wpis.pk] = {'poprzedni': dotychczasowy, 'obecny': obecny}
    return wynik


def progres_cwiczenia(uzytkownik, cwiczenie_id, limit=30):
    dane = SeriaWpisu.objects.filter(
        wpis__sesja__uzytkownik=uzytkownik, wpis__cwiczenie_id=cwiczenie_id
    ).values_list('wpis__sesja__data', 'powtorzenia', 'ciezar').order_by('wpis__sesja__data')
    po_dniach = {}
    for data, powtorzenia, ciezar in dane:
        dzien = po_dniach.setdefault(data, {'maks_ciezar': 0.0, 'maks_1rm': 0.0})
        dzien['maks_ciezar'] = max(dzien['maks_ciezar'], float(ciezar))
        wartosc = szacowane_1rm(ciezar, powtorzenia)
        if wartosc is not None:
            dzien['maks_1rm'] = max(dzien['maks_1rm'], wartosc)
    punkty = [{'data': data, **wartosci} for data, wartosci in po_dniach.items()]
    return punkty[-limit:]


def rekordy_uzytkownika(uzytkownik):
    najlepsze = {}
    dane = SeriaWpisu.objects.filter(wpis__sesja__uzytkownik=uzytkownik).values_list(
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
    serie = list(SeriaWpisu.objects.filter(wpis__sesja=sesja))
    podsumowanie = {
        'cwiczenia': sesja.wpisy.count(),
        'serie': len(serie),
        'powtorzenia': sum(s.powtorzenia for s in serie),
        'objetosc': sum(s.powtorzenia * s.ciezar for s in serie),
    }
    return podsumowanie


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
