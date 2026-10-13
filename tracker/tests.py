import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from django.utils import timezone

from .analiza import (
    ostatnie_serie, podsumowanie_sesji, progres_cwiczenia, rekordy_uzytkownika,
    rekordy_wpisow, sredni_czas_treningu, szacowane_1rm,
)
from .models import formatuj_minuty
from .forms import CwiczeniePlanuForm, NowyWpisForm, WpisForm
from .models import (
    Cwiczenie, CwiczeniePlanu, PlanTreningowy, SeriaWpisu, SesjaTreningowa, WpisDziennika,
)
from .views import oblicz_1rm


def utworz_wpis(sesja, cwiczenie, serie=((5, 50),), notatki=''):
    wpis = WpisDziennika.objects.create(sesja=sesja, cwiczenie=cwiczenie, notatki=notatki)
    for powtorzenia, ciezar in serie:
        SeriaWpisu.objects.create(wpis=wpis, powtorzenia=powtorzenia, ciezar=ciezar)
    return wpis


class BazowyTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ania = User.objects.create_user('ania', password='haslo12345')
        cls.bartek = User.objects.create_user('bartek', password='haslo12345')
        cls.publiczne = Cwiczenie.objects.create(nazwa='Przysiad', kategoria='nogi', czy_publiczne=True)
        cls.prywatne_ani = Cwiczenie.objects.create(
            nazwa='Ruch Ani', kategoria='inne', czy_publiczne=False, dodane_przez=cls.ania)
        cls.prywatne_bartka = Cwiczenie.objects.create(
            nazwa='Ruch Bartka', kategoria='inne', czy_publiczne=False, dodane_przez=cls.bartek)

    def setUp(self):
        self.client.force_login(self.ania)


class DostepDoCwiczenTest(BazowyTest):
    def test_lista_pokazuje_publiczne_i_wlasne_prywatne(self):
        odpowiedz = self.client.get(reverse('lista_cwiczen'))
        nazwy = {c.nazwa for c in odpowiedz.context['cwiczenia']}
        self.assertIn('Przysiad', nazwy)
        self.assertIn('Ruch Ani', nazwy)
        self.assertNotIn('Ruch Bartka', nazwy)

    def test_formularz_planu_nie_oferuje_cudzych_prywatnych(self):
        formularz = CwiczeniePlanuForm(uzytkownik=self.ania)
        dostepne = set(formularz.fields['cwiczenie'].queryset)
        self.assertEqual(dostepne, {self.publiczne, self.prywatne_ani})

    def test_formularz_wpisu_odrzuca_cudze_prywatne(self):
        formularz = WpisForm(
            {'cwiczenie': self.prywatne_bartka.pk, 'notatki': ''},
            uzytkownik=self.ania,
        )
        self.assertFalse(formularz.is_valid())
        self.assertIn('cwiczenie', formularz.errors)

    def test_edycja_cudzego_cwiczenia_zwraca_404(self):
        odpowiedz = self.client.get(reverse('edytuj_cwiczenie', args=[self.prywatne_bartka.pk]))
        self.assertEqual(odpowiedz.status_code, 404)


class DostepDoDanychTest(BazowyTest):
    def setUp(self):
        super().setUp()
        self.plan_bartka = PlanTreningowy.objects.create(nazwa='Plan B', uzytkownik=self.bartek)
        self.cwiczenie_planu_bartka = CwiczeniePlanu.objects.create(
            plan=self.plan_bartka, cwiczenie=self.publiczne)
        self.sesja_bartka = SesjaTreningowa.objects.create(uzytkownik=self.bartek, data=date.today())
        self.wpis_bartka = utworz_wpis(self.sesja_bartka, self.publiczne, serie=((5, 100),) * 3)

    def test_cudze_obiekty_zwracaja_404(self):
        adresy = [
            reverse('szczegoly_planu', args=[self.plan_bartka.pk]),
            reverse('edytuj_plan', args=[self.plan_bartka.pk]),
            reverse('usun_plan', args=[self.plan_bartka.pk]),
            reverse('rozpocznij_trening', args=[self.plan_bartka.pk]),
            reverse('dodaj_cwiczenie_do_planu', args=[self.plan_bartka.pk]),
            reverse('edytuj_cwiczenie_planu', args=[self.cwiczenie_planu_bartka.pk]),
            reverse('usun_cwiczenie_planu', args=[self.cwiczenie_planu_bartka.pk]),
            reverse('szczegoly_sesji', args=[self.sesja_bartka.pk]),
            reverse('edytuj_sesje', args=[self.sesja_bartka.pk]),
            reverse('usun_sesje', args=[self.sesja_bartka.pk]),
            reverse('edytuj_wpis', args=[self.wpis_bartka.pk]),
            reverse('usun_wpis', args=[self.wpis_bartka.pk]),
        ]
        for adres in adresy:
            with self.subTest(adres=adres):
                self.assertEqual(self.client.get(adres).status_code, 404)

    def test_nie_mozna_usunac_cudzego_planu_przez_post(self):
        self.client.post(reverse('usun_plan', args=[self.plan_bartka.pk]))
        self.assertTrue(PlanTreningowy.objects.filter(pk=self.plan_bartka.pk).exists())

    def test_cudze_plany_nie_pojawiaja_sie_na_liscie(self):
        odpowiedz = self.client.get(reverse('lista_planow'))
        self.assertEqual(list(odpowiedz.context['moje_plany']), [])

    def test_widoki_wymagaja_logowania(self):
        self.client.logout()
        odpowiedz = self.client.get(reverse('dziennik'))
        self.assertEqual(odpowiedz.status_code, 302)
        self.assertIn(reverse('logowanie'), odpowiedz.url)


class RozpocznijTreningTest(BazowyTest):
    def test_kopiuje_cwiczenia_planu_do_wpisow(self):
        plan = PlanTreningowy.objects.create(nazwa='Push', uzytkownik=self.ania)
        CwiczeniePlanu.objects.create(plan=plan, cwiczenie=self.publiczne, serie=4, powtorzenia=6, ciezar=80)
        CwiczeniePlanu.objects.create(plan=plan, cwiczenie=self.prywatne_ani, serie=2, powtorzenia=12, ciezar=10)
        odpowiedz = self.client.post(reverse('rozpocznij_trening', args=[plan.pk]))
        sesja = SesjaTreningowa.objects.get(uzytkownik=self.ania)
        self.assertRedirects(odpowiedz, reverse('szczegoly_sesji', args=[sesja.pk]))
        self.assertEqual(sesja.wpisy.count(), 2)
        wpis = sesja.wpisy.get(cwiczenie=self.publiczne)
        serie = [(s.powtorzenia, s.ciezar) for s in wpis.serie.all()]
        self.assertEqual(serie, [(6, Decimal('80'))] * 4)

    def test_get_nie_tworzy_sesji(self):
        plan = PlanTreningowy.objects.create(nazwa='Push', uzytkownik=self.ania)
        self.client.get(reverse('rozpocznij_trening', args=[plan.pk]))
        self.assertEqual(SesjaTreningowa.objects.count(), 0)


class Kalkulator1RMTest(BazowyTest):
    def test_wzor_brzyckiego(self):
        self.assertEqual(oblicz_1rm(100, 1), 100.0)
        self.assertEqual(oblicz_1rm(100, 10), round(100 * 36 / 27, 2))

    def test_poprawne_dane_daja_wynik_i_tabele(self):
        odpowiedz = self.client.post(reverse('kalkulator_1rm'), {'ciezar': '100', 'powtorzenia': '10'})
        self.assertEqual(odpowiedz.context['wynik'], oblicz_1rm(100, 10))
        self.assertEqual(len(odpowiedz.context['tabela']), 5)
        self.assertEqual(odpowiedz.context['tabela'][0]['procent'], 95)

    def test_niepoprawne_dane_nie_daja_wyniku(self):
        for ciezar, powt in [('abc', '5'), ('inf', '5'), ('nan', '5'), ('-5', '5'), ('100', '0'), ('100', '37')]:
            with self.subTest(ciezar=ciezar, powt=powt):
                odpowiedz = self.client.post(reverse('kalkulator_1rm'), {'ciezar': ciezar, 'powtorzenia': powt})
                self.assertIsNone(odpowiedz.context['wynik'])


class StatystykiTest(BazowyTest):
    def test_liczy_rozne_cwiczenia_i_ostatnie_dni(self):
        dzis = date.today()
        drugie = Cwiczenie.objects.create(nazwa='Wiosla', kategoria='plecy')
        for i in range(12):
            sesja = SesjaTreningowa.objects.create(uzytkownik=self.ania, data=dzis - timedelta(days=i))
            utworz_wpis(sesja, self.publiczne if i % 2 else drugie, serie=((5, 50),) * 3)
        odpowiedz = self.client.get(reverse('statystyki'))
        self.assertEqual(odpowiedz.context['liczba_roznych_cwiczen'], 2)
        etykiety = odpowiedz.context['etykiety_wykresu']
        self.assertEqual(len(etykiety), 10)
        self.assertEqual(etykiety[-1], dzis.isoformat())
        self.assertEqual(etykiety, sorted(etykiety))

    def test_nie_wlicza_danych_innych_uzytkownikow(self):
        sesja = SesjaTreningowa.objects.create(uzytkownik=self.bartek, data=date.today())
        utworz_wpis(sesja, self.publiczne, serie=((5, 50),) * 3)
        odpowiedz = self.client.get(reverse('statystyki'))
        self.assertEqual(odpowiedz.context['liczba_wpisow'], 0)
        self.assertEqual(odpowiedz.context['liczba_sesji'], 0)


class DodawanieCwiczeniaDoSesjiTest(BazowyTest):
    def setUp(self):
        super().setUp()
        self.sesja = SesjaTreningowa.objects.create(uzytkownik=self.ania, data=date.today())
        self.adres = reverse('szczegoly_sesji', args=[self.sesja.pk])

    def test_wystarczy_wybrac_cwiczenie(self):
        odpowiedz = self.client.post(self.adres, {'cwiczenie': self.publiczne.pk})
        wpis = self.sesja.wpisy.get()
        self.assertRedirects(odpowiedz, f'{self.adres}#wpis-{wpis.pk}')
        self.assertEqual(wpis.cwiczenie, self.publiczne)
        self.assertEqual(wpis.serie.count(), 0)

    def test_formularz_ma_tylko_pole_cwiczenia(self):
        odpowiedz = self.client.get(self.adres)
        self.assertEqual(list(odpowiedz.context['formularz'].fields), ['cwiczenie'])

    def test_wymaga_wyboru_cwiczenia(self):
        odpowiedz = self.client.post(self.adres, {})
        self.assertEqual(odpowiedz.status_code, 200)
        self.assertEqual(self.sesja.wpisy.count(), 0)

    def test_odrzuca_cudze_prywatne_cwiczenie(self):
        self.client.post(self.adres, {'cwiczenie': self.prywatne_bartka.pk})
        self.assertEqual(self.sesja.wpisy.count(), 0)

    def test_karta_pokazuje_przycisk_dodawania_serii(self):
        self.client.post(self.adres, {'cwiczenie': self.publiczne.pk})
        odpowiedz = self.client.get(self.adres)
        self.assertContains(odpowiedz, 'data-dodaj-serie=')
        self.assertContains(odpowiedz, 'Nie ma jeszcze serii')


class SeriePoSeriiTest(BazowyTest):
    def setUp(self):
        super().setUp()
        self.sesja = SesjaTreningowa.objects.create(uzytkownik=self.ania, data=date.today())
        self.wpis = utworz_wpis(self.sesja, self.publiczne, serie=((8, 60), (8, 60), (8, 60)))
        self.prefiks = f'serie{self.wpis.pk}'

    def dane_formularza(self, serie, usun=(), nowe=()):
        pozycje = list(self.wpis.serie.all())
        dane = {
            f'{self.prefiks}-TOTAL_FORMS': len(pozycje) + len(nowe),
            f'{self.prefiks}-INITIAL_FORMS': len(pozycje),
            f'{self.prefiks}-MIN_NUM_FORMS': 0,
            f'{self.prefiks}-MAX_NUM_FORMS': 1000,
        }
        for i, seria in enumerate(pozycje):
            powt, ciezar = serie[i]
            dane[f'{self.prefiks}-{i}-id'] = seria.pk
            dane[f'{self.prefiks}-{i}-wpis'] = self.wpis.pk
            dane[f'{self.prefiks}-{i}-powtorzenia'] = powt
            dane[f'{self.prefiks}-{i}-ciezar'] = ciezar
            dane[f'{self.prefiks}-{i}-wykonana'] = 'on'
            if i in usun:
                dane[f'{self.prefiks}-{i}-DELETE'] = 'on'
        for j, (powt, ciezar) in enumerate(nowe, start=len(pozycje)):
            dane[f'{self.prefiks}-{j}-wpis'] = self.wpis.pk
            dane[f'{self.prefiks}-{j}-powtorzenia'] = powt
            dane[f'{self.prefiks}-{j}-ciezar'] = ciezar
            dane[f'{self.prefiks}-{j}-wykonana'] = 'on'
        return dane

    def wyslij(self, dane):
        return self.client.post(reverse('zapisz_serie', args=[self.wpis.pk]), dane)

    def test_kazda_seria_moze_miec_inna_liczbe_powtorzen(self):
        odpowiedz = self.wyslij(self.dane_formularza([(8, '60'), (7, '60'), (5, '60')]))
        self.assertRedirects(
            odpowiedz, reverse('szczegoly_sesji', args=[self.sesja.pk]) + f'#wpis-{self.wpis.pk}')
        powtorzenia = [s.powtorzenia for s in self.wpis.serie.all()]
        self.assertEqual(powtorzenia, [8, 7, 5])

    def test_mozna_dodac_serie(self):
        self.wyslij(self.dane_formularza([(8, '60')] * 3, nowe=[(4, '65')]))
        self.assertEqual(self.wpis.serie.count(), 4)
        self.assertEqual(self.wpis.serie.last().ciezar, Decimal('65'))

    def test_mozna_usunac_serie(self):
        self.wyslij(self.dane_formularza([(8, '60')] * 3, usun=[1]))
        self.assertEqual(self.wpis.serie.count(), 2)

    def test_bledne_dane_nie_zapisuja_i_pokazuja_blad(self):
        odpowiedz = self.wyslij(self.dane_formularza([(0, '60'), (8, '-5'), (8, '60')]))
        self.assertEqual(odpowiedz.status_code, 200)
        self.assertContains(odpowiedz, 'text-danger')
        self.assertEqual([s.powtorzenia for s in self.wpis.serie.all()], [8, 8, 8])

    def test_nie_mozna_zapisac_serii_cudzego_wpisu(self):
        sesja_b = SesjaTreningowa.objects.create(uzytkownik=self.bartek, data=date.today())
        wpis_b = utworz_wpis(sesja_b, self.publiczne)
        odpowiedz = self.client.post(reverse('zapisz_serie', args=[wpis_b.pk]), {})
        self.assertEqual(odpowiedz.status_code, 404)

    def test_get_na_zapisie_serii_przekierowuje(self):
        odpowiedz = self.client.get(reverse('zapisz_serie', args=[self.wpis.pk]))
        self.assertRedirects(odpowiedz, reverse('szczegoly_sesji', args=[self.sesja.pk]))


class KolejnoscCwiczenTest(BazowyTest):
    def setUp(self):
        super().setUp()
        self.plan = PlanTreningowy.objects.create(nazwa='Plan', uzytkownik=self.ania)
        self.a = CwiczeniePlanu.objects.create(plan=self.plan, cwiczenie=self.publiczne)
        self.b = CwiczeniePlanu.objects.create(plan=self.plan, cwiczenie=self.prywatne_ani)
        self.c = CwiczeniePlanu.objects.create(plan=self.plan, cwiczenie=self.publiczne)
        self.adres = reverse('zmien_kolejnosc', args=[self.plan.pk])

    def wyslij(self, tresc):
        return self.client.post(
            self.adres, data=json.dumps(tresc), content_type='application/json')

    def test_nowe_cwiczenia_trafiaja_na_koniec(self):
        self.assertEqual(list(self.plan.cwiczenia.all()), [self.a, self.b, self.c])

    def test_zmiana_kolejnosci(self):
        odpowiedz = self.wyslij({'kolejnosc': [self.c.pk, self.a.pk, self.b.pk]})
        self.assertEqual(odpowiedz.status_code, 200)
        self.assertEqual(list(self.plan.cwiczenia.all()), [self.c, self.a, self.b])

    def test_kolejnosc_przenosi_sie_na_trening(self):
        self.wyslij({'kolejnosc': [self.c.pk, self.b.pk, self.a.pk]})
        self.client.post(reverse('rozpocznij_trening', args=[self.plan.pk]))
        sesja = SesjaTreningowa.objects.get(uzytkownik=self.ania)
        self.assertEqual(
            [w.cwiczenie_id for w in sesja.wpisy.all()],
            [self.c.cwiczenie_id, self.b.cwiczenie_id, self.a.cwiczenie_id])

    def test_odrzuca_niepelna_lub_obca_liste(self):
        for tresc in ({'kolejnosc': [self.a.pk]}, {'kolejnosc': [self.a.pk, self.b.pk, 9999]},
                      {'inne': 1}, {'kolejnosc': 'abc'}):
            with self.subTest(tresc=tresc):
                self.assertEqual(self.wyslij(tresc).status_code, 400)
        self.assertEqual(list(self.plan.cwiczenia.all()), [self.a, self.b, self.c])

    def test_cudzy_plan_zwraca_404(self):
        self.client.force_login(self.bartek)
        odpowiedz = self.wyslij({'kolejnosc': [self.c.pk, self.a.pk, self.b.pk]})
        self.assertEqual(odpowiedz.status_code, 404)

    def test_get_jest_niedozwolony(self):
        self.assertEqual(self.client.get(self.adres).status_code, 405)

    def test_kopia_gotowego_planu_zachowuje_kolejnosc(self):
        szablon = PlanTreningowy.objects.create(nazwa='Gotowy', uzytkownik=None)
        pierwsze = CwiczeniePlanu.objects.create(plan=szablon, cwiczenie=self.publiczne)
        drugie = CwiczeniePlanu.objects.create(plan=szablon, cwiczenie=self.prywatne_ani)
        pierwsze.kolejnosc, drugie.kolejnosc = 1, 0
        CwiczeniePlanu.objects.bulk_update([pierwsze, drugie], ['kolejnosc'])
        kopia = szablon.kopiuj_dla(self.ania)
        self.assertEqual(
            [c.cwiczenie_id for c in kopia.cwiczenia.all()],
            [self.prywatne_ani.pk, self.publiczne.pk])


class WlasneStronyTest(BazowyTest):
    def setUp(self):
        super().setUp()
        self.plan = PlanTreningowy.objects.create(nazwa='Moj plan', uzytkownik=self.ania)
        self.cwiczenie_planu = CwiczeniePlanu.objects.create(plan=self.plan, cwiczenie=self.publiczne)
        self.sesja = SesjaTreningowa.objects.create(uzytkownik=self.ania, data=date(2025, 3, 7))
        self.wpis = utworz_wpis(self.sesja, self.publiczne, serie=((8, 60), (7, 60), (5, 60)))

    def test_wszystkie_strony_renderuja_sie(self):
        adresy = [
            reverse('dashboard'), reverse('lista_cwiczen'), reverse('dodaj_cwiczenie'),
            reverse('edytuj_cwiczenie', args=[self.prywatne_ani.pk]),
            reverse('lista_planow'), reverse('dodaj_plan'),
            reverse('szczegoly_planu', args=[self.plan.pk]),
            reverse('edytuj_plan', args=[self.plan.pk]),
            reverse('usun_plan', args=[self.plan.pk]),
            reverse('dodaj_cwiczenie_do_planu', args=[self.plan.pk]),
            reverse('edytuj_cwiczenie_planu', args=[self.cwiczenie_planu.pk]),
            reverse('usun_cwiczenie_planu', args=[self.cwiczenie_planu.pk]),
            reverse('kalkulator_1rm'), reverse('dziennik'), reverse('dodaj_sesje'),
            reverse('szczegoly_sesji', args=[self.sesja.pk]),
            reverse('edytuj_sesje', args=[self.sesja.pk]),
            reverse('usun_sesje', args=[self.sesja.pk]),
            reverse('edytuj_wpis', args=[self.wpis.pk]),
            reverse('usun_wpis', args=[self.wpis.pk]),
            reverse('statystyki'),
        ]
        for adres in adresy:
            with self.subTest(adres=adres):
                self.assertEqual(self.client.get(adres).status_code, 200)

    def test_formularz_edycji_sesji_ma_date_w_formacie_iso(self):
        odpowiedz = self.client.get(reverse('edytuj_sesje', args=[self.sesja.pk]))
        self.assertContains(odpowiedz, 'value="2025-03-07"')

    def test_blad_walidacji_jest_widoczny(self):
        odpowiedz = self.client.post(reverse('dodaj_cwiczenie_do_planu', args=[self.plan.pk]), {
            'cwiczenie': self.publiczne.pk, 'serie': 0, 'powtorzenia': 5, 'ciezar': '10',
        })
        self.assertEqual(odpowiedz.status_code, 200)
        self.assertContains(odpowiedz, 'text-danger')
        self.assertEqual(self.plan.cwiczenia.count(), 1)

    def test_tworzenie_planu_i_cwiczenia(self):
        self.client.post(reverse('dodaj_plan'), {'nazwa': 'Nowy plan', 'opis': ''})
        plan = PlanTreningowy.objects.get(nazwa='Nowy plan')
        self.assertEqual(plan.uzytkownik, self.ania)
        self.client.post(reverse('dodaj_cwiczenie_do_planu', args=[plan.pk]), {
            'cwiczenie': self.publiczne.pk, 'serie': 4, 'powtorzenia': 8, 'ciezar': '40', 'notatki': '',
        })
        self.assertEqual(plan.cwiczenia.count(), 1)

    def test_edycja_wpisu_zmienia_cwiczenie_i_notatke(self):
        self.client.post(reverse('edytuj_wpis', args=[self.wpis.pk]), {
            'cwiczenie': self.prywatne_ani.pk, 'notatki': 'Nowa',
        })
        self.wpis.refresh_from_db()
        self.assertEqual(self.wpis.cwiczenie, self.prywatne_ani)
        self.assertEqual(self.wpis.notatki, 'Nowa')
        self.assertEqual(self.wpis.serie.count(), 3)

    def test_usuniecie_dziala_tylko_przez_post(self):
        self.client.get(reverse('usun_sesje', args=[self.sesja.pk]))
        self.assertTrue(SesjaTreningowa.objects.filter(pk=self.sesja.pk).exists())
        odpowiedz = self.client.post(reverse('usun_sesje', args=[self.sesja.pk]))
        self.assertRedirects(odpowiedz, reverse('dziennik'))
        self.assertFalse(SesjaTreningowa.objects.filter(pk=self.sesja.pk).exists())
        self.assertFalse(WpisDziennika.objects.filter(pk=self.wpis.pk).exists())


class NowyPrzeplywTest(BazowyTest):
    def setUp(self):
        super().setUp()
        self.plan = PlanTreningowy.objects.create(nazwa='Push', uzytkownik=self.ania)

    def test_get_na_starcie_treningu_przekierowuje_do_planu(self):
        odpowiedz = self.client.get(reverse('rozpocznij_trening', args=[self.plan.pk]))
        self.assertRedirects(odpowiedz, reverse('szczegoly_planu', args=[self.plan.pk]))
        self.assertEqual(SesjaTreningowa.objects.count(), 0)

    def test_pusty_plan_nie_tworzy_sesji(self):
        odpowiedz = self.client.post(reverse('rozpocznij_trening', args=[self.plan.pk]))
        self.assertRedirects(odpowiedz, reverse('szczegoly_planu', args=[self.plan.pk]))
        self.assertEqual(SesjaTreningowa.objects.count(), 0)

    def test_dodaj_i_dodaj_kolejne_wraca_do_formularza(self):
        adres = reverse('dodaj_cwiczenie_do_planu', args=[self.plan.pk])
        odpowiedz = self.client.post(adres, {
            'cwiczenie': self.publiczne.pk, 'serie': 3, 'powtorzenia': 10, 'ciezar': '20',
            'notatki': '', 'dodaj_kolejne': '1',
        })
        self.assertRedirects(odpowiedz, adres)
        self.assertEqual(self.plan.cwiczenia.count(), 1)

    def test_zwykle_dodanie_wraca_do_planu(self):
        odpowiedz = self.client.post(reverse('dodaj_cwiczenie_do_planu', args=[self.plan.pk]), {
            'cwiczenie': self.publiczne.pk, 'serie': 3, 'powtorzenia': 10, 'ciezar': '20', 'notatki': '',
        })
        self.assertRedirects(odpowiedz, reverse('szczegoly_planu', args=[self.plan.pk]))

    def test_lista_cwiczen_jest_pogrupowana_wg_kategorii(self):
        odpowiedz = self.client.get(reverse('dodaj_cwiczenie_do_planu', args=[self.plan.pk]))
        self.assertContains(odpowiedz, '<optgroup label="Nogi">')
        self.assertContains(odpowiedz, '<optgroup label="Inne">')

    def test_trening_bez_planu_ma_domyslna_date(self):
        odpowiedz = self.client.get(reverse('dodaj_sesje'))
        from django.utils import timezone
        self.assertContains(odpowiedz, f'value="{timezone.localdate().isoformat()}"')

    def test_dashboard_pokazuje_ostatni_trening_i_tydzien(self):
        SesjaTreningowa.objects.create(uzytkownik=self.ania, data=date.today(), nazwa='Wczorajszy')
        odpowiedz = self.client.get(reverse('dashboard'))
        self.assertEqual(odpowiedz.context['ostatnia_sesja'].nazwa, 'Wczorajszy')
        self.assertEqual(odpowiedz.context['sesje_w_tygodniu'], 1)


class GotowePlanyTest(BazowyTest):
    def setUp(self):
        super().setUp()
        self.szablon = PlanTreningowy.objects.create(
            nazwa='Gotowy', opis='Opis', uzytkownik=None, poziom='poczatkujacy')
        CwiczeniePlanu.objects.create(
            plan=self.szablon, cwiczenie=self.publiczne, serie=3, powtorzenia=8,
            ciezar=0, notatki='Wskazowka')

    def test_lista_gotowych_planow(self):
        odpowiedz = self.client.get(reverse('gotowe_plany'))
        self.assertEqual(odpowiedz.status_code, 200)
        self.assertContains(odpowiedz, 'Gotowy')
        self.assertContains(odpowiedz, 'Wskazowka')

    def test_uzycie_tworzy_kopie_a_szablon_zostaje(self):
        odpowiedz = self.client.post(reverse('uzyj_gotowego_planu', args=[self.szablon.pk]))
        kopia = PlanTreningowy.objects.get(uzytkownik=self.ania)
        self.assertRedirects(odpowiedz, reverse('szczegoly_planu', args=[kopia.pk]))
        self.assertNotEqual(kopia.pk, self.szablon.pk)
        wpis = kopia.cwiczenia.get()
        self.assertEqual((wpis.serie, wpis.powtorzenia, wpis.notatki), (3, 8, 'Wskazowka'))

    def test_edycja_kopii_nie_zmienia_szablonu(self):
        self.client.post(reverse('uzyj_gotowego_planu', args=[self.szablon.pk]))
        kopia = PlanTreningowy.objects.get(uzytkownik=self.ania)
        self.client.post(reverse('edytuj_plan', args=[kopia.pk]), {'nazwa': 'Moj wariant', 'opis': ''})
        self.client.post(reverse('usun_plan', args=[kopia.pk]))
        self.szablon.refresh_from_db()
        self.assertEqual(self.szablon.nazwa, 'Gotowy')
        self.assertEqual(self.szablon.cwiczenia.count(), 1)

    def test_szablonu_nie_mozna_edytowac_ani_usunac_bezposrednio(self):
        for nazwa in ('edytuj_plan', 'usun_plan', 'szczegoly_planu'):
            with self.subTest(widok=nazwa):
                self.assertEqual(
                    self.client.get(reverse(nazwa, args=[self.szablon.pk])).status_code, 404)
        self.client.post(reverse('usun_plan', args=[self.szablon.pk]))
        self.assertTrue(PlanTreningowy.objects.filter(pk=self.szablon.pk).exists())

    def test_get_na_uzyciu_nie_tworzy_kopii(self):
        self.client.get(reverse('uzyj_gotowego_planu', args=[self.szablon.pk]))
        self.assertEqual(PlanTreningowy.objects.filter(uzytkownik=self.ania).count(), 0)

    def test_szablony_nie_sa_na_liscie_moich_planow(self):
        odpowiedz = self.client.get(reverse('lista_planow'))
        self.assertEqual(list(odpowiedz.context['moje_plany']), [])

    def test_start_treningu_kopiuje_notatki(self):
        self.client.post(reverse('uzyj_gotowego_planu', args=[self.szablon.pk]))
        kopia = PlanTreningowy.objects.get(uzytkownik=self.ania)
        self.client.post(reverse('rozpocznij_trening', args=[kopia.pk]))
        wpis = WpisDziennika.objects.get(sesja__uzytkownik=self.ania)
        self.assertEqual(wpis.notatki, 'Wskazowka')

    def test_notatka_jest_widoczna_jako_dymek_w_planie(self):
        self.client.post(reverse('uzyj_gotowego_planu', args=[self.szablon.pk]))
        kopia = PlanTreningowy.objects.get(uzytkownik=self.ania)
        odpowiedz = self.client.get(reverse('szczegoly_planu', args=[kopia.pk]))
        self.assertContains(odpowiedz, 'data-bs-toggle="tooltip" title="Wskazowka"')


class PrzyciskUsuwaniaSeriiTest(BazowyTest):
    def test_kazda_zapisana_seria_ma_przycisk_usuwania(self):
        sesja = SesjaTreningowa.objects.create(uzytkownik=self.ania, data=date.today())
        utworz_wpis(sesja, self.publiczne, serie=((8, 60), (7, 60), (5, 60)))
        odpowiedz = self.client.get(reverse('szczegoly_sesji', args=[sesja.pk]))
        self.assertContains(
            odpowiedz,
            '<button type="button" class="btn btn-sm btn-outline-danger" data-przelacz-usuniecie>',
            count=3,
        )


class HistoriaTestBase(BazowyTest):
    def sesja_z(self, data, serie, cwiczenie=None, uzytkownik=None):
        sesja = SesjaTreningowa.objects.create(uzytkownik=uzytkownik or self.ania, data=data)
        utworz_wpis(sesja, cwiczenie or self.publiczne, serie=serie)
        return sesja


class AnalizaTest(HistoriaTestBase):
    def test_szacowane_1rm(self):
        self.assertEqual(szacowane_1rm(100, 1), 100.0)
        self.assertIsNone(szacowane_1rm(100, 37))
        self.assertIsNone(szacowane_1rm(100, 0))

    def test_ostatnie_serie_bierze_najnowsza_wczesniejsza_sesje(self):
        self.sesja_z(date(2025, 1, 1), ((10, 40),))
        self.sesja_z(date(2025, 1, 8), ((8, 50), (7, 50)))
        biezaca = self.sesja_z(date(2025, 1, 15), ((5, 60),))
        self.sesja_z(date(2025, 1, 22), ((3, 70),))
        wynik = ostatnie_serie(biezaca, [self.publiczne.pk])[self.publiczne.pk]
        self.assertEqual(wynik['data'], date(2025, 1, 8))
        self.assertEqual([(s.powtorzenia, s.ciezar) for s in wynik['serie']],
                         [(8, Decimal('50')), (7, Decimal('50'))])

    def test_ostatnie_serie_pomija_cudze_dane(self):
        self.sesja_z(date(2025, 1, 1), ((8, 50),), uzytkownik=self.bartek)
        biezaca = self.sesja_z(date(2025, 1, 8), ((5, 60),))
        self.assertEqual(ostatnie_serie(biezaca, [self.publiczne.pk]), {})

    def test_rekord_gdy_wynik_jest_lepszy_niz_dotychczasowy(self):
        self.sesja_z(date(2025, 1, 1), ((8, 50),))
        biezaca = self.sesja_z(date(2025, 1, 8), ((8, 55),))
        wpisy = list(biezaca.wpisy.prefetch_related('serie'))
        rekordy = rekordy_wpisow(biezaca, wpisy)
        self.assertIn(wpisy[0].pk, rekordy)
        self.assertGreater(rekordy[wpisy[0].pk]['obecny'], rekordy[wpisy[0].pk]['poprzedni'])

    def test_brak_rekordu_przy_pierwszym_podejsciu_i_przy_remisie(self):
        pierwsza = self.sesja_z(date(2025, 1, 1), ((8, 50),))
        wpisy = list(pierwsza.wpisy.prefetch_related('serie'))
        self.assertEqual(rekordy_wpisow(pierwsza, wpisy), {})
        druga = self.sesja_z(date(2025, 1, 8), ((8, 50),))
        wpisy = list(druga.wpisy.prefetch_related('serie'))
        self.assertEqual(rekordy_wpisow(druga, wpisy), {})

    def test_progres_grupuje_po_dniach(self):
        self.sesja_z(date(2025, 1, 1), ((8, 50), (6, 55)))
        self.sesja_z(date(2025, 1, 8), ((5, 60),))
        punkty = progres_cwiczenia(self.ania, self.publiczne.pk)
        self.assertEqual([p['data'] for p in punkty], [date(2025, 1, 1), date(2025, 1, 8)])
        self.assertEqual(punkty[0]['ciezar'], 55.0)
        self.assertEqual(punkty[0]['powt_ciezar'], 6)
        self.assertEqual((punkty[0]['powt_rm'], punkty[0]['ciezar_rm']), (6, 55.0))
        self.assertEqual(punkty[0]['powt_wykres'], 6)

    def test_rekordy_uzytkownika_zwracaja_najlepsza_serie(self):
        self.sesja_z(date(2025, 1, 1), ((8, 50), (3, 70)))
        self.sesja_z(date(2025, 1, 8), ((10, 40),))
        rekordy = rekordy_uzytkownika(self.ania)
        self.assertEqual(len(rekordy), 1)
        self.assertEqual((rekordy[0]['powtorzenia'], rekordy[0]['ciezar']), (3, Decimal('70')))

    def test_podsumowanie_sesji(self):
        sesja = self.sesja_z(date(2025, 1, 1), ((10, 20), (5, 40)))
        sesja.rozpoczeto = timezone.now()
        sesja.zakonczono = sesja.rozpoczeto + timedelta(minutes=47)
        podsumowanie = podsumowanie_sesji(sesja)
        self.assertEqual(podsumowanie['cwiczenia'], 1)
        self.assertEqual(podsumowanie['serie'], 2)
        self.assertEqual(podsumowanie['powtorzenia'], 15)
        self.assertEqual(podsumowanie['objetosc'], Decimal('400'))
        self.assertEqual(sesja.czas_trwania_minuty, 47)
        self.assertEqual(sesja.czas_trwania_tekst, '47 min')


class OstatnioWSesjiTest(HistoriaTestBase):
    def test_strona_sesji_pokazuje_ostatnie_serie_i_rekord(self):
        self.sesja_z(date(2025, 1, 1), ((8, 50), (7, 50)))
        biezaca = self.sesja_z(date(2025, 1, 8), ((8, 60),))
        odpowiedz = self.client.get(reverse('szczegoly_sesji', args=[biezaca.pk]))
        self.assertContains(odpowiedz, 'Ostatnio (01.01.2025)')
        self.assertContains(odpowiedz, '8 x 50 kg, 7 x 50 kg')
        self.assertContains(odpowiedz, 'Nowy rekord')
        self.assertEqual(odpowiedz.context['liczba_rekordow'], 1)

    def test_start_treningu_przejmuje_ostatni_ciezar_gdy_plan_ma_zero(self):
        self.sesja_z(date(2025, 1, 1), ((8, 50), (6, 55)))
        plan = PlanTreningowy.objects.create(nazwa='P', uzytkownik=self.ania)
        CwiczeniePlanu.objects.create(
            plan=plan, cwiczenie=self.publiczne, serie=2, powtorzenia=8, ciezar=0)
        self.client.post(reverse('rozpocznij_trening', args=[plan.pk]))
        sesja = SesjaTreningowa.objects.filter(uzytkownik=self.ania).order_by('-pk').first()
        self.assertEqual({s.ciezar for s in sesja.wpisy.get().serie.all()}, {Decimal('55')})
        self.assertIsNotNone(sesja.rozpoczeto)

    def test_start_treningu_zachowuje_ciezar_z_planu(self):
        self.sesja_z(date(2025, 1, 1), ((8, 50),))
        plan = PlanTreningowy.objects.create(nazwa='P', uzytkownik=self.ania)
        CwiczeniePlanu.objects.create(
            plan=plan, cwiczenie=self.publiczne, serie=1, powtorzenia=8, ciezar=70)
        self.client.post(reverse('rozpocznij_trening', args=[plan.pk]))
        sesja = SesjaTreningowa.objects.filter(uzytkownik=self.ania).order_by('-pk').first()
        self.assertEqual(sesja.wpisy.get().serie.get().ciezar, Decimal('70'))


class ZakonczenieTreninguTest(BazowyTest):
    def setUp(self):
        super().setUp()
        self.sesja = SesjaTreningowa.objects.create(
            uzytkownik=self.ania, data=date.today(), rozpoczeto=timezone.now())

    def test_zakonczenie_i_wznowienie(self):
        self.client.post(reverse('zakoncz_sesje', args=[self.sesja.pk]))
        self.sesja.refresh_from_db()
        self.assertIsNotNone(self.sesja.zakonczono)
        odpowiedz = self.client.get(reverse('szczegoly_sesji', args=[self.sesja.pk]))
        self.assertContains(odpowiedz, 'Zakończony o')
        self.client.post(reverse('wznow_sesje', args=[self.sesja.pk]))
        self.sesja.refresh_from_db()
        self.assertIsNone(self.sesja.zakonczono)

    def test_get_jest_niedozwolony(self):
        self.assertEqual(self.client.get(reverse('zakoncz_sesje', args=[self.sesja.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse('wznow_sesje', args=[self.sesja.pk])).status_code, 405)

    def test_cudza_sesja_zwraca_404(self):
        self.client.force_login(self.bartek)
        self.assertEqual(
            self.client.post(reverse('zakoncz_sesje', args=[self.sesja.pk])).status_code, 404)

    def test_trening_bez_planu_zapamietuje_start_tylko_dla_dzisiejszej_daty(self):
        self.client.post(reverse('dodaj_sesje'), {'data': date.today().isoformat(), 'nazwa': 'Dzis', 'notatki': ''})
        self.client.post(reverse('dodaj_sesje'), {'data': '2020-01-01', 'nazwa': 'Dawno', 'notatki': ''})
        self.assertIsNotNone(SesjaTreningowa.objects.get(nazwa='Dzis').rozpoczeto)
        self.assertIsNone(SesjaTreningowa.objects.get(nazwa='Dawno').rozpoczeto)


class StatystykiProgresTest(HistoriaTestBase):
    def test_domyslnie_wybiera_najczesciej_cwiczone(self):
        rzadkie = Cwiczenie.objects.create(nazwa='Rzadkie', kategoria='inne')
        self.sesja_z(date(2025, 1, 1), ((8, 50),))
        self.sesja_z(date(2025, 1, 8), ((8, 55),))
        self.sesja_z(date(2025, 1, 9), ((8, 20),), cwiczenie=rzadkie)
        odpowiedz = self.client.get(reverse('statystyki'))
        self.assertEqual(odpowiedz.context['wybrane_cwiczenie'], self.publiczne)
        self.assertEqual([p['ciezar'] for p in odpowiedz.context['progres']], [50.0, 55.0])

    def test_wybor_cwiczenia_z_adresu(self):
        rzadkie = Cwiczenie.objects.create(nazwa='Rzadkie', kategoria='inne')
        self.sesja_z(date(2025, 1, 1), ((8, 50),))
        self.sesja_z(date(2025, 1, 9), ((8, 20),), cwiczenie=rzadkie)
        odpowiedz = self.client.get(reverse('statystyki'), {'cwiczenie': rzadkie.pk})
        self.assertEqual(odpowiedz.context['wybrane_cwiczenie'], rzadkie)

    def test_nieznane_lub_niepoprawne_cwiczenie_wraca_do_domyslnego(self):
        self.sesja_z(date(2025, 1, 1), ((8, 50),))
        for wartosc in ('abc', '99999', str(self.prywatne_bartka.pk)):
            with self.subTest(wartosc=wartosc):
                odpowiedz = self.client.get(reverse('statystyki'), {'cwiczenie': wartosc})
                self.assertEqual(odpowiedz.status_code, 200)
                self.assertEqual(odpowiedz.context['wybrane_cwiczenie'], self.publiczne)

    def test_brak_danych_nie_psuje_strony(self):
        odpowiedz = self.client.get(reverse('statystyki'))
        self.assertEqual(odpowiedz.status_code, 200)
        self.assertIsNone(odpowiedz.context['wybrane_cwiczenie'])
        self.assertEqual(odpowiedz.context['rekordy'], [])


class CzasTreninguTest(BazowyTest):
    def sesja(self, minuty=None, trwa=False, uzytkownik=None):
        teraz = timezone.now()
        sesja = SesjaTreningowa.objects.create(
            uzytkownik=uzytkownik or self.ania, data=date.today(),
            rozpoczeto=teraz - timedelta(minutes=minuty or 0) if (minuty or trwa) else None,
        )
        if minuty is not None and not trwa:
            sesja.zakonczono = teraz
            sesja.save()
        return sesja

    def test_formatowanie_minut(self):
        self.assertEqual(formatuj_minuty(None), '')
        self.assertEqual(formatuj_minuty(5), '5 min')
        self.assertEqual(formatuj_minuty(60), '1 h 00 min')
        self.assertEqual(formatuj_minuty(135), '2 h 15 min')

    def test_czas_trwania_zakonczonej_sesji(self):
        sesja = self.sesja(minuty=72)
        self.assertEqual(sesja.czas_trwania_minuty, 72)
        self.assertEqual(sesja.czas_trwania_tekst, '1 h 12 min')
        self.assertFalse(sesja.trwa)

    def test_sesja_w_trakcie_nie_ma_jeszcze_czasu(self):
        sesja = self.sesja(trwa=True)
        self.assertIsNone(sesja.czas_trwania_minuty)
        self.assertTrue(sesja.trwa)

    def test_sesja_bez_znacznika_startu_nie_ma_czasu(self):
        sesja = SesjaTreningowa.objects.create(uzytkownik=self.ania, data=date(2020, 1, 1))
        self.assertIsNone(sesja.czas_trwania_minuty)
        self.assertFalse(sesja.trwa)

    def test_strona_sesji_w_trakcie_ma_licznik_na_zywo(self):
        sesja = self.sesja(trwa=True)
        odpowiedz = self.client.get(reverse('szczegoly_sesji', args=[sesja.pk]))
        self.assertContains(odpowiedz, 'id="czas-trwania"')
        self.assertContains(odpowiedz, 'data-start="')

    def test_strona_zakonczonej_sesji_pokazuje_czas_bez_licznika(self):
        sesja = self.sesja(minuty=45)
        odpowiedz = self.client.get(reverse('szczegoly_sesji', args=[sesja.pk]))
        self.assertContains(odpowiedz, '45 min')
        self.assertNotContains(odpowiedz, 'id="czas-trwania"')

    def test_dziennik_pokazuje_czas_treningu(self):
        self.sesja(minuty=50)
        odpowiedz = self.client.get(reverse('dziennik'))
        self.assertContains(odpowiedz, 'Czas treningu: 50 min')

    def test_sredni_czas_liczy_tylko_zakonczone_sesje_uzytkownika(self):
        self.sesja(minuty=40)
        self.sesja(minuty=60)
        self.sesja(trwa=True)
        self.sesja(minuty=500, uzytkownik=self.bartek)
        self.assertEqual(sredni_czas_treningu(self.ania), 50)
        odpowiedz = self.client.get(reverse('statystyki'))
        self.assertEqual(odpowiedz.context['sredni_czas'], '50 min')

    def test_brak_zakonczonych_sesji_daje_pusty_sredni_czas(self):
        self.assertIsNone(sredni_czas_treningu(self.ania))
        odpowiedz = self.client.get(reverse('statystyki'))
        self.assertEqual(odpowiedz.context['sredni_czas'], '')


class WykresProgresuTest(HistoriaTestBase):
    def test_okres_ogranicza_dane(self):
        dzis = date.today()
        self.sesja_z(dzis - timedelta(days=200), ((8, 50),))
        self.sesja_z(dzis - timedelta(days=40), ((8, 55),))
        self.sesja_z(dzis - timedelta(days=5), ((8, 60),))
        wszystkie = self.client.get(reverse('statystyki'))
        self.assertEqual(len(wszystkie.context['progres']), 3)
        for dni, oczekiwane in ((30, 1), (90, 2), (180, 2), (365, 3)):
            with self.subTest(dni=dni):
                odpowiedz = self.client.get(reverse('statystyki'), {'dni': dni})
                self.assertEqual(len(odpowiedz.context['progres']), oczekiwane)
                self.assertEqual(odpowiedz.context['wybrany_zakres'], dni)

    def test_niepoprawny_okres_oznacza_caly_okres(self):
        self.sesja_z(date(2020, 1, 1), ((8, 50),))
        for wartosc in ('abc', '7', '-5'):
            with self.subTest(wartosc=wartosc):
                odpowiedz = self.client.get(reverse('statystyki'), {'dni': wartosc})
                self.assertEqual(odpowiedz.context['wybrany_zakres'], 0)
                self.assertEqual(len(odpowiedz.context['progres']), 1)

    def test_punkt_zawiera_serie_bazowa_dla_1rm(self):
        self.sesja_z(date(2025, 3, 1), ((12, 40), (5, 60), (3, 70)))
        punkt = self.client.get(reverse('statystyki')).context['progres'][0]
        self.assertEqual((punkt['powt_ciezar'], punkt['ciezar']), (3, 70.0))
        self.assertEqual((punkt['powt_rm'], punkt['ciezar_rm']), (3, 70.0))
        self.assertEqual(punkt['data'], '01.03.2025')

    def test_cwiczenie_bez_ciezaru_pokazuje_powtorzenia(self):
        sesja = SesjaTreningowa.objects.create(uzytkownik=self.ania, data=date(2025, 3, 1))
        utworz_wpis(sesja, self.publiczne, serie=((15, 0), (12, 0)))
        punkt = self.client.get(reverse('statystyki')).context['progres'][0]
        self.assertIsNone(punkt['rm'])
        self.assertEqual(punkt['powt_wykres'], 15)

    def test_tabela_i_wykres_sa_na_stronie(self):
        self.sesja_z(date(2025, 3, 1), ((8, 50),))
        odpowiedz = self.client.get(reverse('statystyki'))
        self.assertContains(odpowiedz, 'id="wykresProgresu"')
        self.assertNotContains(odpowiedz, 'wykresPowtorzen')
        self.assertContains(odpowiedz, 'id="tabela-progresu"')
        self.assertContains(odpowiedz, 'id="progres-dane"')

    def test_pusty_okres_pokazuje_komunikat(self):
        self.sesja_z(date(2020, 1, 1), ((8, 50),))
        odpowiedz = self.client.get(reverse('statystyki'), {'dni': 30})
        self.assertContains(odpowiedz, 'Brak danych dla tego ćwiczenia w wybranym okresie.')


class WykonaneISerieZaplanowaneTest(HistoriaTestBase):
    def zaplanowana(self, sesja, powtorzenia, ciezar, cwiczenie=None):
        wpis = WpisDziennika.objects.create(sesja=sesja, cwiczenie=cwiczenie or self.publiczne)
        SeriaWpisu.objects.create(
            wpis=wpis, powtorzenia=powtorzenia, ciezar=ciezar, wykonana=False)
        return wpis

    def test_domyslnie_seria_jest_wykonana(self):
        sesja = SesjaTreningowa.objects.create(uzytkownik=self.ania, data=date.today())
        wpis = utworz_wpis(sesja, self.publiczne)
        self.assertTrue(wpis.serie.get().wykonana)

    def test_zaplanowana_seria_nie_jest_rekordem(self):
        self.sesja_z(date(2025, 1, 1), ((1, 120),))
        biezaca = SesjaTreningowa.objects.create(uzytkownik=self.ania, data=date(2025, 1, 8))
        self.zaplanowana(biezaca, 8, 120)
        wpisy = list(biezaca.wpisy.prefetch_related('serie'))
        self.assertEqual(rekordy_wpisow(biezaca, wpisy), {})

    def test_wykonana_seria_o_tym_samym_ciezarze_jest_rekordem(self):
        self.sesja_z(date(2025, 1, 1), ((1, 120),))
        biezaca = SesjaTreningowa.objects.create(uzytkownik=self.ania, data=date(2025, 1, 8))
        wpis = self.zaplanowana(biezaca, 8, 120)
        wpis.serie.update(wykonana=True)
        wpisy = list(biezaca.wpisy.prefetch_related('serie'))
        rekordy = rekordy_wpisow(biezaca, wpisy)
        self.assertAlmostEqual(rekordy[wpis.pk]['obecny'], 149.0, places=0)
        self.assertEqual(rekordy[wpis.pk]['poprzedni'], 120.0)

    def test_zaplanowane_serie_nie_wchodza_do_historii_i_statystyk(self):
        stara = SesjaTreningowa.objects.create(uzytkownik=self.ania, data=date(2025, 1, 1))
        self.zaplanowana(stara, 8, 200)
        biezaca = SesjaTreningowa.objects.create(uzytkownik=self.ania, data=date(2025, 1, 8))
        self.assertEqual(ostatnie_serie(biezaca, [self.publiczne.pk]), {})
        self.assertEqual(progres_cwiczenia(self.ania, self.publiczne.pk), [])
        self.assertEqual(rekordy_uzytkownika(self.ania), [])

    def test_podsumowanie_liczy_tylko_wykonane(self):
        sesja = SesjaTreningowa.objects.create(uzytkownik=self.ania, data=date.today())
        wpis = utworz_wpis(sesja, self.publiczne, serie=((10, 20),))
        SeriaWpisu.objects.create(wpis=wpis, powtorzenia=10, ciezar=100, wykonana=False)
        podsumowanie = podsumowanie_sesji(sesja)
        self.assertEqual(podsumowanie['serie'], 1)
        self.assertEqual(podsumowanie['serie_razem'], 2)
        self.assertEqual(podsumowanie['objetosc'], Decimal('200'))

    def test_start_treningu_tworzy_serie_zaplanowane(self):
        plan = PlanTreningowy.objects.create(nazwa='P', uzytkownik=self.ania)
        CwiczeniePlanu.objects.create(
            plan=plan, cwiczenie=self.publiczne, serie=3, powtorzenia=8, ciezar=50)
        self.client.post(reverse('rozpocznij_trening', args=[plan.pk]))
        sesja = SesjaTreningowa.objects.get(uzytkownik=self.ania)
        self.assertEqual(sesja.wpisy.get().serie.filter(wykonana=False).count(), 3)
        odpowiedz = self.client.get(reverse('szczegoly_sesji', args=[sesja.pk]))
        self.assertEqual(odpowiedz.context['liczba_rekordow'], 0)
        self.assertEqual(odpowiedz.context['podsumowanie']['serie'], 0)
        self.assertEqual(odpowiedz.context['podsumowanie']['serie_razem'], 3)

    def test_scenariusz_rekord_pojawia_sie_dopiero_po_oznaczeniu_serii(self):
        self.sesja_z(date(2025, 1, 1), ((1, 120),))
        plan = PlanTreningowy.objects.create(nazwa='P', uzytkownik=self.ania)
        CwiczeniePlanu.objects.create(
            plan=plan, cwiczenie=self.publiczne, serie=1, powtorzenia=8, ciezar=0)
        self.client.post(reverse('rozpocznij_trening', args=[plan.pk]))
        sesja = SesjaTreningowa.objects.order_by('-pk').first()
        wpis = sesja.wpisy.get()
        seria = wpis.serie.get()
        self.assertEqual((seria.powtorzenia, seria.ciezar, seria.wykonana), (8, Decimal('120'), False))
        adres = reverse('szczegoly_sesji', args=[sesja.pk])
        self.assertNotContains(self.client.get(adres), 'Nowy rekord')

        prefiks = f'serie{wpis.pk}'
        self.client.post(reverse('zapisz_serie', args=[wpis.pk]), {
            f'{prefiks}-TOTAL_FORMS': 1, f'{prefiks}-INITIAL_FORMS': 1,
            f'{prefiks}-MIN_NUM_FORMS': 0, f'{prefiks}-MAX_NUM_FORMS': 1000,
            f'{prefiks}-0-id': seria.pk, f'{prefiks}-0-wpis': wpis.pk,
            f'{prefiks}-0-powtorzenia': 8, f'{prefiks}-0-ciezar': '120',
            f'{prefiks}-0-wykonana': 'on',
        })
        odpowiedz = self.client.get(adres)
        self.assertContains(odpowiedz, 'Nowy rekord')
        self.assertEqual(odpowiedz.context['liczba_rekordow'], 1)

    def test_karta_pokazuje_dotychczasowy_rekord(self):
        self.sesja_z(date(2025, 1, 1), ((1, 120),))
        biezaca = SesjaTreningowa.objects.create(uzytkownik=self.ania, data=date(2025, 1, 8))
        WpisDziennika.objects.create(sesja=biezaca, cwiczenie=self.publiczne)
        odpowiedz = self.client.get(reverse('szczegoly_sesji', args=[biezaca.pk]))
        self.assertContains(odpowiedz, 'Twój rekord:')
        self.assertContains(odpowiedz, '1 x 120 kg')
        self.assertContains(odpowiedz, 'data-jak-ostatnio=')

    def test_karta_bez_historii_informuje_o_braku_wynikow(self):
        biezaca = SesjaTreningowa.objects.create(uzytkownik=self.ania, data=date(2025, 1, 8))
        WpisDziennika.objects.create(sesja=biezaca, cwiczenie=self.publiczne)
        odpowiedz = self.client.get(reverse('szczegoly_sesji', args=[biezaca.pk]))
        self.assertContains(odpowiedz, 'Brak wcześniejszych wyników')
