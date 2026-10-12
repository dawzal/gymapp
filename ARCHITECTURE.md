# GymApp - architektura

Dokument opisuje aktualną strukturę aplikacji, przepływ danych i reguły biznesowe,
a na końcu listę znanych ograniczeń.

## 1. Stos

- Python, Django 6.0, baza SQLite
- szablony Django, Bootstrap 5.3.0 i Chart.js 4.4.0 ładowane z CDN
- brak własnego JavaScriptu poza wykresem w `statystyki.html`
- brak REST API, zadań asynchronicznych i integracji zewnętrznych

## 2. Struktura

```
config/            ustawienia (zmienne środowiskowe), główny routing
accounts/          rejestracja, logowanie (LoginView), wylogowanie (POST)
tracker/           logika domenowa
  models.py        5 modeli
  forms.py         5 formularzy ModelForm + ograniczanie listy ćwiczeń
  views.py         widoki funkcyjne, wszystkie z @login_required
  tests.py         testy autoryzacji, logiki i renderowania
  management/commands/wypelnij_baze.py   domyślna baza ćwiczeń
templates/
  base.html                 układ strony, nawigacja, komunikaty
  formularz.html            wspólny szablon wszystkich formularzy add/edit (opcjonalny przycisk "dodaj kolejne")
  pola_formularza.html      renderowanie pól wraz z błędami
  potwierdz_usuniecie.html  wspólny szablon potwierdzenia usunięcia
tracker/templates/tracker/  szablony list, szczegółów, statystyk, kalkulatora
```

## 3. Model danych

```
User ─┬─< PlanTreningowy ─< CwiczeniePlanu >─ Cwiczenie >─(dodane_przez, SET_NULL)─ User
      └─< SesjaTreningowa ─< WpisDziennika >─ Cwiczenie
```

- `Cwiczenie`: nazwa, kategoria, opis, autor, `czy_publiczne`. Metoda `dostepne_dla(user)`
  zwraca ćwiczenia publiczne oraz własne użytkownika.
- `PlanTreningowy`: nazwa, opis, poziom, właściciel (CASCADE). Plan bez właściciela
  (`uzytkownik = NULL`) to gotowy plan systemowy: widoczny dla wszystkich, niedostępny do edycji
  przez użytkowników. Metoda `kopiuj_dla(user)` tworzy edytowalną kopię na koncie użytkownika.
- `CwiczeniePlanu`: ćwiczenie w planie (serie, powtórzenia, ciężar, notatki).
- `SesjaTreningowa`: data, nazwa, notatki, właściciel; sortowana malejąco po dacie.
- `WpisDziennika`: wykonane ćwiczenie w sesji (serie, powtórzenia, ciężar, notatki).
- Serie, powtórzenia i ciężar mają walidatory minimalnych wartości (>= 1, >= 1, >= 0).

## 4. Przepływ danych

1. Użytkownik rejestruje się i loguje (`accounts`), po czym trafia na `dashboard`.
2. Wybiera ćwiczenia z bazy (publiczne i własne) lub dodaje własne. Początkujący mogą wziąć
   gotowy plan ze strony "Gotowe plany" (POST tworzy kopię, oryginał pozostaje bez zmian).
3. Tworzy plan i dodaje do niego ćwiczenia.
4. "Rozpocznij trening" (przycisk POST na dashboardzie, liście planów i w szczegółach planu, bez strony pośredniej) w jednej transakcji tworzy sesję z dzisiejszą datą
   i kopiuje ćwiczenia planu do wpisów dziennika. Wpisy są niezależne od planu.
5. "Trening bez planu" tworzy pustą sesję (domyślnie z dzisiejszą datą); wpisy dodaje się w widoku szczegółów sesji.
6. `statystyki` agreguje dane zalogowanego użytkownika; `kalkulator_1rm` nie zapisuje danych.

## 5. Bezpieczeństwo i autoryzacja

- Każdy widok jest chroniony `@login_required`.
- Obiekty pobierane są z filtrem właściciela (`get_object_or_404` z `uzytkownik=request.user`
  lub przez relację), więc cudze obiekty zwracają 404.
- Formularze planu i dziennika ograniczają listę ćwiczeń do dostępnych dla użytkownika,
  także walidacją po stronie serwera.
- Usuwanie i wylogowanie wyłącznie metodą POST z tokenem CSRF.
- Logowanie przez `LoginView` obsługuje parametr `next` i odrzuca obce adresy.
- `SECRET_KEY`, `DEBUG` i `ALLOWED_HOSTS` pochodzą ze zmiennych środowiskowych;
  przy `DJANGO_DEBUG=0` bez klucza aplikacja nie startuje.
- Dane do JavaScriptu przekazywane są przez `json_script`.

## 6. Testy

`python manage.py test` uruchamia 44 testy: uprawnienia (cudze obiekty -> 404),
widoczność ćwiczeń, start treningu, kalkulator 1RM, statystyki, walidację,
logowanie i wylogowanie, renderowanie wszystkich stron oraz tworzenie, edycję i usuwanie.

## 7. Znane ograniczenia

- Brak paginacji list (dziennik, ćwiczenia).
- Seria jest agregatem (serie x powtórzenia @ ciężar), bez zapisu pojedynczych serii.
- Sesja nie przechowuje powiązania z planem, z którego powstała.
- Usunięcie ćwiczenia (np. w panelu admina) kasuje powiązane wpisy dziennika (`CASCADE`).
- Zasoby Bootstrap i Chart.js pochodzą z CDN bez sum kontrolnych SRI.
- Brak limitu prób logowania i weryfikacji adresu e-mail.
- Brak konfiguracji plików statycznych pod wdrożenie produkcyjne (`STATIC_ROOT`).
