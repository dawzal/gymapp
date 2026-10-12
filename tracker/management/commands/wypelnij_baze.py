from django.core.management.base import BaseCommand, CommandError
from tracker.models import Cwiczenie, CwiczeniePlanu, PlanTreningowy


DOBIERZ = 'Dobierz ciężar tak, aby na końcu serii zostawały 2 powtórzenia zapasu.'

GOTOWE_PLANY = [
    (
        'Full Body A - na start',
        'poczatkujacy',
        'Trening całego ciała dla osób zaczynających. Wykonuj na przemian z planem Full Body B, '
        'trzy razy w tygodniu z dniem przerwy.',
        [
            ('Przysiady ze sztangą', 3, 8, 'Zacznij od pustej sztangi. Plecy proste, kolana w linii stóp. ' + DOBIERZ),
            ('Wyciskanie sztangi leżąc', 3, 8, 'Łopatki ściągnięte, stopy mocno na podłodze. Poproś kogoś o asekurację.'),
            ('Wiosłowanie sztangą', 3, 10, 'Tułów lekko pochylony, przyciągaj sztangę do brzucha.'),
            ('Plank', 3, 30, 'Liczba powtórzeń oznacza sekundy utrzymania pozycji.'),
        ],
    ),
    (
        'Full Body B - na start',
        'poczatkujacy',
        'Drugi trening całego ciała dla początkujących. Uzupełnia plan Full Body A.',
        [
            ('Martwy ciąg', 3, 5, 'Plecy proste, sztanga blisko ciała. Technika ważniejsza niż ciężar.'),
            ('Wyciskanie sztangi nad głowę', 3, 8, 'Brzuch napięty, nie wyginaj pleców.'),
            ('Ściąganie drążka wyciągu', 3, 10, 'Ściągaj drążek do górnej części klatki piersiowej.'),
            ('Wypady z hantlami', 3, 10, 'Liczba powtórzeń dotyczy każdej nogi.'),
            ('Brzuszki', 3, 15, 'Nie ciągnij głowy rękami.'),
        ],
    ),
    (
        'Trening w domu - bez sprzętu',
        'poczatkujacy',
        'Prosty trening z masą własnego ciała. Nie wymaga siłowni ani sprzętu.',
        [
            ('Pompki', 3, 10, 'Jeśli to za trudne, wykonuj je z kolan.'),
            ('Brzuszki', 3, 15, 'Wolny, kontrolowany ruch.'),
            ('Plank', 3, 30, 'Liczba powtórzeń oznacza sekundy utrzymania pozycji.'),
            ('Russian twist', 3, 20, 'Liczba powtórzeń dotyczy obu stron łącznie.'),
        ],
    ),
    (
        'Push - klatka, barki, triceps',
        'sredni',
        'Część podziału Push / Pull / Legs: ćwiczenia pchające.',
        [
            ('Wyciskanie sztangi leżąc', 4, 8, DOBIERZ),
            ('Wyciskanie hantli nad głowę', 3, 10, ''),
            ('Rozpiętki z hantlami', 3, 12, 'Lekki ciężar, pełne rozciągnięcie klatki.'),
            ('Unoszenie hantli bokiem', 3, 15, 'Nie bujaj tułowiem.'),
            ('Prostowanie ramion na wyciągu', 3, 12, ''),
        ],
    ),
    (
        'Pull - plecy i biceps',
        'sredni',
        'Część podziału Push / Pull / Legs: ćwiczenia ciągnące.',
        [
            ('Martwy ciąg', 3, 5, 'Rozgrzej się lżejszymi seriami.'),
            ('Podciąganie na drążku', 3, 8, 'Możesz użyć gumy wspomagającej.'),
            ('Wiosłowanie hantlem', 3, 10, 'Liczba powtórzeń dotyczy każdej ręki.'),
            ('Odwrotne rozpiętki', 3, 15, ''),
            ('Uginanie ramion ze sztangą', 3, 10, 'Łokcie przy tułowiu.'),
        ],
    ),
    (
        'Legs - nogi',
        'sredni',
        'Część podziału Push / Pull / Legs: trening nóg.',
        [
            ('Przysiady ze sztangą', 4, 8, DOBIERZ),
            ('Wyciskanie nogami', 3, 10, ''),
            ('Martwy ciąg na prostych nogach', 3, 10, 'Delikatnie ugięte kolana, plecy proste.'),
            ('Uginanie nóg leżąc', 3, 12, ''),
            ('Wspięcia na palce', 4, 15, 'Zatrzymaj się na górze na sekundę.'),
        ],
    ),
]


class Command(BaseCommand):
    help = 'Wypełnia bazę danych domyślnymi ćwiczeniami'

    def handle(self, *args, **kwargs):
        cwiczenia = [
            # Klatka piersiowa
            ('Wyciskanie sztangi leżąc', 'klatka', 'Podstawowe ćwiczenie na klatkę piersiową. Połóż się na ławce, chwyć sztangę na szerokość barków i opuść do klatki.'),
            ('Wyciskanie hantli leżąc', 'klatka', 'Ćwiczenie na klatkę piersiową z hantlami. Daje większy zakres ruchu niż sztanga.'),
            ('Rozpiętki z hantlami', 'klatka', 'Izolowane ćwiczenie na klatkę piersiową. Połóż się na ławce i rozciągaj klatkę.'),
            ('Pompki', 'klatka', 'Klasyczne ćwiczenie z masą ciała na klatkę piersiową i triceps.'),
            ('Wyciskanie na suwnicy', 'klatka', 'Ćwiczenie na maszynie, bezpieczna alternatywa dla wyciskania sztangi.'),

            # Plecy
            ('Martwy ciąg', 'plecy', 'Podstawowe ćwiczenie na plecy i nogi. Podnoś sztangę z podłogi do pozycji stojącej.'),
            ('Wiosłowanie sztangą', 'plecy', 'Ćwiczenie na środkową część pleców. Pochyl się i przyciągaj sztangę do brzucha.'),
            ('Podciąganie na drążku', 'plecy', 'Ćwiczenie z masą ciała na plecy i biceps. Podciągaj się do wysokości brody.'),
            ('Wiosłowanie hantlem', 'plecy', 'Jednostronne ćwiczenie na plecy. Oprzyj kolano na ławce i przyciągaj hantlę.'),
            ('Ściąganie drążka wyciągu', 'plecy', 'Ćwiczenie na maszynie na szerokość pleców.'),

            # Nogi
            ('Przysiady ze sztangą', 'nogi', 'Podstawowe ćwiczenie na nogi. Sztanga na plecach, schodź do równoległości ud z podłogą.'),
            ('Wyciskanie nogami', 'nogi', 'Ćwiczenie na maszynie na czworogłowe uda.'),
            ('Wypady z hantlami', 'nogi', 'Ćwiczenie na nogi i pośladki. Rób duże kroki do przodu z hantlami w rękach.'),
            ('Uginanie nóg leżąc', 'nogi', 'Izolowane ćwiczenie na dwugłowe uda na maszynie.'),
            ('Wspięcia na palce', 'nogi', 'Ćwiczenie na łydki. Stań na krawędzi stopnia i unoś się na palcach.'),
            ('Martwy ciąg na prostych nogach', 'nogi', 'Ćwiczenie na dwugłowe uda i pośladki ze sztangą.'),

            # Barki
            ('Wyciskanie sztangi nad głowę', 'barki', 'Podstawowe ćwiczenie na barki. Wyciskaj sztangę z wysokości barków nad głowę.'),
            ('Wyciskanie hantli nad głowę', 'barki', 'Ćwiczenie na barki z hantlami. Można wykonywać naprzemiennie.'),
            ('Unoszenie hantli bokiem', 'barki', 'Izolowane ćwiczenie na środkową część barków.'),
            ('Unoszenie hantli przodem', 'barki', 'Izolowane ćwiczenie na przednie aktony barków.'),
            ('Odwrotne rozpiętki', 'barki', 'Ćwiczenie na tylne aktony barków. Pochyl się i unoś hantle w bok.'),

            # Biceps
            ('Uginanie ramion ze sztangą', 'biceps', 'Podstawowe ćwiczenie na biceps. Stój prosto i uginaj ramiona ze sztangą.'),
            ('Uginanie ramion z hantlami', 'biceps', 'Ćwiczenie na biceps z hantlami. Można wykonywać naprzemiennie.'),
            ('Uginanie młotkowe', 'biceps', 'Ćwiczenie na biceps i ramię. Hantle trzymaj neutralnie jak młotek.'),
            ('Uginanie na modlitewniku', 'biceps', 'Izolowane ćwiczenie na biceps na specjalnej ławce.'),

            # Triceps
            ('Wyciskanie wąskim chwytem', 'triceps', 'Ćwiczenie na triceps ze sztangą. Chwyć sztangę na szerokość barków.'),
            ('Prostowanie ramion na wyciągu', 'triceps', 'Izolowane ćwiczenie na triceps na maszynie.'),
            ('Francuskie wyciskanie', 'triceps', 'Ćwiczenie na triceps. Leż na ławce i opuszczaj sztangę za głowę.'),
            ('Pompki na poręczach', 'triceps', 'Ćwiczenie z masą ciała na triceps i klatkę piersiową.'),

            # Brzuch
            ('Brzuszki', 'brzuch', 'Podstawowe ćwiczenie na mięśnie proste brzucha.'),
            ('Plank', 'brzuch', 'Statyczne ćwiczenie na core. Utrzymuj pozycję deski przez określony czas.'),
            ('Unoszenie nóg w zwisie', 'brzuch', 'Ćwiczenie na dolne partie brzucha. Zwis na drążku i unoś nogi.'),
            ('Russian twist', 'brzuch', 'Ćwiczenie na mięśnie skośne brzucha z rotacją tułowia.'),
        ]

        licznik = 0
        for nazwa, kategoria, opis in cwiczenia:
            cwiczenie, created = Cwiczenie.objects.get_or_create(
                nazwa=nazwa,
                dodane_przez=None,
                defaults={
                    'kategoria': kategoria,
                    'opis': opis,
                    'czy_publiczne': True,
                }
            )
            if created:
                licznik += 1

        self.stdout.write(
            self.style.SUCCESS(f'Dodano {licznik} nowych ćwiczeń do bazy danych!')
        )

        dodane_plany = 0
        for nazwa, poziom, opis, pozycje in GOTOWE_PLANY:
            plan, utworzony = PlanTreningowy.objects.get_or_create(
                nazwa=nazwa,
                uzytkownik=None,
                defaults={'poziom': poziom, 'opis': opis},
            )
            if not utworzony:
                continue
            for nazwa_cwiczenia, serie, powtorzenia, notatka in pozycje:
                cwiczenie = Cwiczenie.objects.filter(
                    nazwa=nazwa_cwiczenia, dodane_przez__isnull=True).first()
                if cwiczenie is None:
                    raise CommandError(f'Brak ćwiczenia "{nazwa_cwiczenia}" w bazie.')
                CwiczeniePlanu.objects.create(
                    plan=plan, cwiczenie=cwiczenie, serie=serie,
                    powtorzenia=powtorzenia, ciezar=0, notatki=notatka)
            dodane_plany += 1

        self.stdout.write(
            self.style.SUCCESS(f'Dodano {dodane_plany} nowych gotowych planów!')
        )