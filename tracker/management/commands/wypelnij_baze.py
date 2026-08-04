from django.core.management.base import BaseCommand
from tracker.models import Cwiczenie


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