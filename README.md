# GymApp

Aplikacja webowa w Django do planowania treningów siłowych i prowadzenia dziennika treningowego.

## Funkcje

- rejestracja, logowanie i wylogowanie użytkowników,
- baza ćwiczeń (domyślne publiczne oraz własne, publiczne lub prywatne),
- plany treningowe z ćwiczeniami (serie, powtórzenia, ciężar),
- rozpoczęcie treningu z planu: automatyczne utworzenie sesji z wpisami,
- dziennik treningów (sesje i wpisy, edycja i usuwanie),
- statystyki: najczęstsze ćwiczenia i wykres aktywności z ostatnich 10 dni treningowych,
- kalkulator maksymalnego ciężaru (1RM, wzór Brzyckiego) z tabelą procentową.

Każdy użytkownik ma dostęp wyłącznie do własnych planów i dziennika.

## Wymagania

- Python 3.12 lub nowszy
- Django 6.0 (patrz `requirements.txt`)

## Uruchomienie lokalne

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py wypelnij_baze
python manage.py runserver
```

Aplikacja będzie dostępna pod adresem http://127.0.0.1:8000/.
Komenda `wypelnij_baze` dodaje domyślne ćwiczenia (można ją uruchamiać wielokrotnie).

## Testy

```
python manage.py test
```

Testy używają osobnej, tymczasowej bazy danych i nie zmieniają `db.sqlite3`.

## Konfiguracja

Ustawienia są pobierane ze zmiennych środowiskowych:

| Zmienna | Domyślnie | Opis |
|---|---|---|
| `DJANGO_DEBUG` | `1` | `0` wyłącza tryb debugowania |
| `DJANGO_SECRET_KEY` | klucz deweloperski | wymagany, gdy `DJANGO_DEBUG=0` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | lista hostów oddzielona przecinkami |

## Struktura projektu

```
config/    ustawienia i główny routing
accounts/  rejestracja, logowanie, wylogowanie
tracker/   modele, widoki, formularze, szablony i testy aplikacji
templates/ szablon bazowy oraz wspólne szablony formularzy i potwierdzeń
```

Szczegółowy opis architektury: [ARCHITECTURE.md](ARCHITECTURE.md).
