import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

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


class WalidacjaSeriiTest(BazowyTest):
    def test_nowy_wpis_odrzuca_zerowa_liczbe_serii_i_ujemny_ciezar(self):
        formularz = NowyWpisForm(
            {'cwiczenie': self.publiczne.pk, 'liczba_serii': 0, 'powtorzenia': 5, 'ciezar': '-1'},
            uzytkownik=self.ania,
        )
        self.assertFalse(formularz.is_valid())
        self.assertIn('liczba_serii', formularz.errors)
        self.assertIn('ciezar', formularz.errors)

    def test_nowy_wpis_tworzy_podana_liczbe_serii(self):
        sesja = SesjaTreningowa.objects.create(uzytkownik=self.ania, data=date.today())
        self.client.post(reverse('szczegoly_sesji', args=[sesja.pk]), {
            'cwiczenie': self.publiczne.pk, 'liczba_serii': 4, 'powtorzenia': 8,
            'ciezar': '45', 'notatki': 'x',
        })
        wpis = sesja.wpisy.get()
        self.assertEqual(wpis.serie.count(), 4)
        self.assertEqual(wpis.notatki, 'x')


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
            if i in usun:
                dane[f'{self.prefiks}-{i}-DELETE'] = 'on'
        for j, (powt, ciezar) in enumerate(nowe, start=len(pozycje)):
            dane[f'{self.prefiks}-{j}-wpis'] = self.wpis.pk
            dane[f'{self.prefiks}-{j}-powtorzenia'] = powt
            dane[f'{self.prefiks}-{j}-ciezar'] = ciezar
        return dane

    def wyslij(self, dane):
        return self.client.post(reverse('zapisz_serie', args=[self.wpis.pk]), dane)

    def test_kazda_seria_moze_miec_inna_liczbe_powtorzen(self):
        odpowiedz = self.wyslij(self.dane_formularza([(8, '60'), (7, '60'), (5, '60')]))
        self.assertRedirects(odpowiedz, reverse('szczegoly_sesji', args=[self.sesja.pk]))
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
