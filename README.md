# GymApp

Aplikacja webowa w Django do planowania treningów siłowych, prowadzenia dziennika treningowego i analizy postępów. Zawiera też asystenta treningowego opartego na Google Gemini API (darmowy poziom).

## Funkcje

- rejestracja, logowanie i wylogowanie użytkowników,
- baza ćwiczeń (domyślne publiczne oraz własne, publiczne lub prywatne),
- plany treningowe z ćwiczeniami (serie, powtórzenia, ciężar, notatki wyświetlane jako dymek),
- gotowe plany dla początkujących i średniozaawansowanych (dodawane jako własna, edytowalna kopia),
- zmiana kolejności ćwiczeń w planie przeciąganiem myszą lub palcem,
- rozpoczęcie treningu z planu: automatyczne utworzenie sesji z wpisami i seriami (ciężar podpowiadany z poprzedniego treningu),
- dziennik treningów, w którym każda seria ma własną liczbę powtórzeń i ciężar oraz status wykonana/zaplanowana,
- licznik czasu treningu i minutnik przerw między seriami,
- oznaczanie rekordów (najlepsza seria wg szacowanego 1RM) i podgląd poprzedniego treningu na karcie ćwiczenia,
- statystyki: najczęstsze ćwiczenia, wykres aktywności z ostatnich 10 dni treningowych, wykres progresu wybranego ćwiczenia, tabela rekordów, średni czas treningu,
- kalkulator maksymalnego ciężaru (1RM, wzór Brzyckiego) z tabelą procentową,
- asystent treningowy (czat) z dziennym limitem wiadomości i opcjonalnym przekazaniem danych z dziennika.

Każdy użytkownik ma dostęp wyłącznie do własnych planów, dziennika i historii czatu.

## Wymagania

- Python 3.12 lub nowszy
- Django 6.0 oraz pakiety `google-genai` i `python-dotenv` (patrz `requirements.txt`)

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
Komenda `wypelnij_baze` dodaje domyślne ćwiczenia oraz gotowe plany (można ją uruchamiać wielokrotnie).

## Testy

```
python manage.py test
```

Testy używają osobnej, tymczasowej bazy danych i nie zmieniają `db.sqlite3`.

## Konfiguracja

Ustawienia są pobierane ze zmiennych środowiskowych lub z pliku `.env` w głównym folderze projektu (wzór: `.env.example`). Plik `.env` nie trafia do repozytorium.

| Zmienna | Domyślnie | Opis |
|---|---|---|
| `DJANGO_DEBUG` | `1` | `0` wyłącza tryb debugowania |
| `DJANGO_SECRET_KEY` | klucz deweloperski | wymagany, gdy `DJANGO_DEBUG=0` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | lista hostów oddzielona przecinkami |
| `GEMINI_API_KEY` | brak | darmowy klucz z Google AI Studio; bez niego czat jest wyłączony |
| `CZAT_MODEL` | `gemini-flash-latest` | model używany przez asystenta |
| `CZAT_DZIENNY_LIMIT` | `30` | maksymalna liczba wiadomości użytkownika na dobę |

## Struktura projektu

```
config/    ustawienia i główny routing
accounts/  rejestracja, logowanie, wylogowanie
tracker/   modele, widoki, formularze, analiza danych, szablony i testy
           (static/tracker – skrypty JS: wykresy, kolejność ćwiczeń, serie i minutnik)
czat/      asystent treningowy: klient API, budowa kontekstu, widoki i historia
           (static/czat – skrypt JS czatu)
templates/ szablon bazowy oraz wspólne szablony formularzy i potwierdzeń
```
