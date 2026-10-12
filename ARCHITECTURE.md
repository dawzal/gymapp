# GymApp — architektura i audyt kodu

Stan na: 2026-10-12, branch `main`, commit `cce2307`.
Audyt tylko do odczytu (poza utworzeniem tego pliku nic nie zmieniono). Uruchomiono wyłącznie
`manage.py check`, `check --deploy` i `makemigrations --check --dry-run` (brak zmian w migracjach).

## 1. Zakres analizy

| Obszar | Status |
|---|---|
| `config/` (settings, urls, wsgi/asgi) | przeanalizowane |
| `accounts/` (views, urls, szablony, models/admin/tests – puste) | przeanalizowane |
| `tracker/models.py`, `views.py`, `forms.py`, `urls.py`, `admin.py` | przeanalizowane |
| `tracker/management/commands/wypelnij_baze.py` | przeanalizowane |
| Migracje `tracker/0001–0005` | przejrzane pobieżnie (typy operacji, spójność ze stanem modeli) |
| Szablony: `base`, `dashboard`, `lista_cwiczen`, `lista_planow`, `szczegoly_planu`, `szczegoly_sesji`, `statystyki`, `kalkulator_1rm`, `usun_plan`, `dodaj_cwiczenie_do_planu` | przeczytane w całości |
| Pozostałe szablony tracker (`edytuj_*`, `dodaj_*`, `usun_*`, `dziennik`, `rozpocznij_trening`) i accounts | tylko wymiary/nazwy, wzorzec identyczny jak wyżej — **nie czytane linia po linii** |
| `db.sqlite3` | celowo nieotwierany (zakaz zmian w bazie) |
| JavaScript / CSS własne | brak; jedyny JS to inline Chart.js w `statystyki.html` |
| serializers, services, signals, middleware własne, zadania async, integracje zewn. | **nie istnieją** w projekcie |

## 2. Stos

- Django (settings wygenerowane przez 6.0.6), SQLite, szablony Django + Bootstrap 5.3.0 z CDN, Chart.js z CDN (bez przypiętej wersji).
- Brak `requirements.txt`/`pyproject.toml`. W środowisku są też zainstalowane `djangorestframework` i `simplejwt`, ale projekt ich **nie używa** (nie ma ich w `INSTALLED_APPS`).
- UI i nazewnictwo w języku polskim (modele, widoki, URL-e, komunikaty).

## 3. Struktura

```
config/            settings, root urls (admin/, accounts, tracker – oba pod '')
accounts/          rejestracja / logowanie / wylogowanie (wbudowane formularze auth)
tracker/           cała logika domenowa
  models.py        5 modeli
  views.py         ~25 widoków funkcyjnych, wszystkie @login_required
  forms.py         5 ModelForm
  management/commands/wypelnij_baze.py   seed 31 ćwiczeń
templates/base.html                      layout + nav + messages
tracker/templates/tracker/*.html         23 szablony
```

## 4. Model danych

```
User ─┬─< PlanTreningowy ─< CwiczeniePlanu >─ Cwiczenie >─(dodane_przez, SET_NULL)─ User
      └─< SesjaTreningowa ─< WpisDziennika >─ Cwiczenie
```

- `Cwiczenie`: nazwa, kategoria (choices), opis, `dodane_przez` (SET_NULL), `czy_publiczne`.
- `PlanTreningowy`: nazwa, opis, `uzytkownik` (CASCADE), `czy_publiczny`.
- `CwiczeniePlanu`: plan (related_name `cwiczenia`), cwiczenie (CASCADE), serie, powtorzenia, ciezar, notatki.
- `SesjaTreningowa`: uzytkownik, data, nazwa, notatki; ordering `-data`.
- `WpisDziennika`: sesja (related_name `wpisy`), cwiczenie (CASCADE), serie, powtorzenia, ciezar, notatki.
- Plan i sesja **nie są powiązane** — rozpoczęcie treningu kopiuje wartości z planu do wpisów, bez śladu źródła.

## 5. Przepływ danych i reguły biznesowe

1. Rejestracja/logowanie (`accounts`) → `dashboard`.
2. Użytkownik tworzy własne ćwiczenia (`dodaj_cwiczenie`) lub korzysta z publicznych (seed).
3. Tworzy plan → dodaje do niego ćwiczenia (serie × powtórzenia @ ciężar).
4. „Rozpocznij trening” (POST) tworzy `SesjaTreningowa` z dzisiejszą datą i kopiuje każde `CwiczeniePlanu` do `WpisDziennika`.
5. Sesję można też założyć ręcznie (`dodaj_sesje`) i dodawać wpisy w `szczegoly_sesji`.
6. `statystyki` agreguje wpisy i sesje użytkownika; `kalkulator_1rm` liczy wzór Brzyckiego (bez zapisu do bazy).

Autoryzacja: każdy widok obiektowy filtruje po właścicielu w `get_object_or_404` (`uzytkownik=request.user`,
`plan__uzytkownik`, `sesja__uzytkownik`, `dodane_przez`). To jest poprawne i spójne — **nie znaleziono IDOR** w widokach. Usuwanie wyłącznie przez POST z CSRF.

## 6. Znalezione problemy

### Błędy (funkcjonalne)

| # | Gdzie | Opis |
|---|---|---|
| B1 | `views.py:166` i `:312` | `rozpocznij_trening` zdefiniowany **dwa razy**; pierwszy (bez kopiowania ćwiczeń) jest martwym kodem, nadpisanym przez drugi. |
| B2 | `lista_planow.html`, `dashboard.html` | `plan.dni.count` — related_name `dni` nie istnieje po migracji 0005 (usunięto `DzienPlanuTreningowego`). Django po cichu zwraca pusty string; „Dni treningowe” nic nie pokazuje. `usun_plan.html` też mówi o „dniach”. |
| B3 | `lista_cwiczen` | Filtruje `czy_publiczne=True` — **własne ćwiczenia prywatne użytkownika są niewidoczne i nieedytowalne** z listy. |
| B4 | `CwiczeniePlanuForm`, `WpisForm` | Pole `cwiczenie` ma pełny queryset `Cwiczenie` — w selekcie widać też **prywatne ćwiczenia innych użytkowników** (wyciek nazw; można je też przypisać do własnego planu przez POST). |
| B5 | `lista_planow.html` | Plany publiczne innych są wyświetlane bez linku; `szczegoly_planu` wymaga bycia właścicielem — „publiczny” plan jest w praktyce nieprzeglądalny ani nie do skopiowania. |
| B6 | `statystyki` | „Różnych ćwiczeń” = `len` listy top-5 (maks. 5). Wykres: `order_by('data')[:10]` daje 10 **najstarszych** dni, nie najnowszych. Grupowanie po `data` scala sesje z tego samego dnia. |
| B7 | `kalkulator_1rm.html` | Wiersz „95%” pokazuje pełne 1RM zamiast 95%. `float('inf')` przechodzi walidację. `widthratio` zaokrągla do całych kg. |
| B8 | `base.html` | Wszystkie komunikaty mają klasę `alert-success`, także `messages.error` z kalkulatora (błąd na zielono). |
| B9 | `rozpocznij_trening` | Sesja + wpisy tworzone bez `transaction.atomic`; pętla `create()` zamiast `bulk_create`. Brak ochrony przed wielokrotnym kliknięciem (duplikaty sesji). |

### Bezpieczeństwo

| # | Gdzie | Opis |
|---|---|---|
| S1 | `settings.py` | Zahardkodowany `SECRET_KEY`, `DEBUG=True`, `ALLOWED_HOSTS=[]`. `check --deploy` zgłasza 7 ostrzeżeń (HSTS, SSL redirect, secure cookies itd.). Wymaga konfiguracji z env przed jakimkolwiek wdrożeniem. |
| S2 | `.gitignore` | Plik zapisany w **UTF-16** — git go nie parsuje, więc ignorowanie nie działa. Efekt: `db.sqlite3` (z hasłami/hashami użytkowników i sesjami) oraz 27 plików `.pyc` **są śledzone w repozytorium**. |
| S3 | `accounts/views.py:29` | Wylogowanie przez GET (CSRF-logout). Django 5+ wymaga POST dla `LogoutView`. |
| S4 | `accounts/views.py` | Własne widoki logowania ignorują parametr `next` (nie ma open-redirect, ale `@login_required` gubi docelowy URL). Brak limitu prób logowania. Rejestracja bez weryfikacji e-mail/ograniczeń. |
| S5 | `base.html`, `statystyki.html` | Bootstrap/Chart.js z CDN bez SRI; Chart.js bez wersji (`/npm/chart.js`). W JS wstawiane `'{{ sesja.data }}'` zamiast `json_script`/`isoformat`. |
| S6 | modele/formularze | Brak walidatorów serwerowych: `ciezar` może być ujemny, `serie`/`powtorzenia` = 0 (`min`/`max` tylko w HTML; `WpisForm` w ogóle bez `max`). |

### Architektura / jakość

- **Brak testów** — `tracker/tests.py` i `accounts/tests.py` to puste szablony.
- Duplikacja: 8 par szablonów `dodaj_*`/`edytuj_*` o niemal identycznej treści, 4 szablony potwierdzeń usuwania, powtarzane widgety Bootstrap w `forms.py` (kandydaci na mixin / `{% include %}` / wspólny `form_page.html`). W `views.py` powtarza się wzorzec GET/POST/save/redirect 10×.
- N+1: `szczegoly_planu` (`c.cwiczenie.nazwa`), `szczegoly_sesji` (`wpis.cwiczenie`), `lista_cwiczen` (`dodane_przez`), `lista_planow` (`plan.dni.count`) — brak `select_related`. Brak paginacji list.
- `from datetime import date` wewnątrz widoku; `date.today()` zamiast `timezone.localdate()` (przy `USE_TZ=True`, TZ=UTC data „dziś” bywa przesunięta dla użytkownika w PL).
- `LANGUAGE_CODE='en-us'`, `TIME_ZONE='UTC'` dla aplikacji polskiej (daty, komunikaty admina po angielsku).
- Modele: `Cwiczenie.nazwa` nie jest unikalna, a seed robi `get_or_create(nazwa=...)` — może „połączyć się” z ćwiczeniem użytkownika. `on_delete=CASCADE` z `Cwiczenie` na `WpisDziennika` i `CwiczeniePlanu`: skasowanie ćwiczenia (np. w adminie) kasuje historię treningów (rozważyć `PROTECT`). Brak numeracji serii — seria jest agregatem (serie × powt. @ ciężar), co ogranicza analitykę (progres, tonaż).
- Edycja współdzielonego (publicznego) ćwiczenia przez autora zmienia historię innych użytkowników.
- `admin.py` — gołe `register`, brak `list_display`/filtrów. `accounts` nie ma modeli (brak profilu).
- Brak `requirements.txt`, README, konfiguracji statycznych (`STATIC_ROOT`), logowania.
- Stan migracji spójny z modelami (`makemigrations --check` → brak zmian); `manage.py check` bez błędów.

## 7. Plan dalszej pracy (propozycja, w kolejności)

1. **Higiena repo** (S2): poprawić `.gitignore` (UTF-8), `git rm --cached` dla `db.sqlite3` i `*.pyc`; dodać `requirements.txt`. Rozważyć rotację haseł/sesji, jeśli repo było publiczne.
2. **Błędy funkcjonalne**: B1 (usunąć duplikat), B2, B3, B4, B8, B7 — małe, bezpieczne poprawki; dopisać testy regresyjne.
3. **Testy**: najpierw uprawnienia (dostęp do cudzych obiektów → 404), `rozpocznij_trening`, kalkulator, statystyki.
4. **Ustawienia**: SECRET_KEY/DEBUG/ALLOWED_HOSTS z env, `LANGUAGE_CODE='pl'`, `TIME_ZONE='Europe/Warsaw'`, flagi bezpieczeństwa.
5. **Walidacja i modele**: walidatory `ciezar`/`serie`/`powtorzenia`; decyzja o `PROTECT`, powiązaniu `Sesja → Plan`.
6. **Refaktor**: wspólne szablony formularzy, `select_related`, paginacja, `transaction.atomic`, wylogowanie przez POST.
7. **Funkcje**: przeglądanie/kopiowanie planów publicznych (B5), poprawne statystyki (B6).

## 8. Do potwierdzenia z właścicielem

- Czy plany publiczne mają być tylko do podglądu, czy kopiowalne?
- Czy prywatne ćwiczenia mają być widoczne wyłącznie dla autora (zakładam: tak)?
- Czy repo było kiedykolwiek publiczne (wpływa na pilność S2)?
