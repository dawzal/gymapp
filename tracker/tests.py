from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .forms import CwiczeniePlanuForm, WpisForm
from .models import Cwiczenie, CwiczeniePlanu, PlanTreningowy, SesjaTreningowa, WpisDziennika
from .views import oblicz_1rm


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
            {'cwiczenie': self.prywatne_bartka.pk, 'serie': 3, 'powtorzenia': 8, 'ciezar': '50'},
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
        self.wpis_bartka = WpisDziennika.objects.create(
            sesja=self.sesja_bartka, cwiczenie=self.publiczne, serie=3, powtorzenia=5, ciezar=100)

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
        self.assertEqual((wpis.serie, wpis.powtorzenia, wpis.ciezar), (4, 6, Decimal('80')))

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
            WpisDziennika.objects.create(
                sesja=sesja, cwiczenie=self.publiczne if i % 2 else drugie,
                serie=3, powtorzenia=5, ciezar=50)
        odpowiedz = self.client.get(reverse('statystyki'))
        self.assertEqual(odpowiedz.context['liczba_roznych_cwiczen'], 2)
        etykiety = odpowiedz.context['etykiety_wykresu']
        self.assertEqual(len(etykiety), 10)
        self.assertEqual(etykiety[-1], dzis.isoformat())
        self.assertEqual(etykiety, sorted(etykiety))

    def test_nie_wlicza_danych_innych_uzytkownikow(self):
        sesja = SesjaTreningowa.objects.create(uzytkownik=self.bartek, data=date.today())
        WpisDziennika.objects.create(
            sesja=sesja, cwiczenie=self.publiczne, serie=3, powtorzenia=5, ciezar=50)
        odpowiedz = self.client.get(reverse('statystyki'))
        self.assertEqual(odpowiedz.context['liczba_wpisow'], 0)
        self.assertEqual(odpowiedz.context['liczba_sesji'], 0)


class WalidacjaWpisuTest(BazowyTest):
    def test_odrzuca_zerowe_serie_i_ujemny_ciezar(self):
        formularz = WpisForm(
            {'cwiczenie': self.publiczne.pk, 'serie': 0, 'powtorzenia': 5, 'ciezar': '-1'},
            uzytkownik=self.ania,
        )
        self.assertFalse(formularz.is_valid())
        self.assertIn('serie', formularz.errors)
        self.assertIn('ciezar', formularz.errors)


class WlasneStronyTest(BazowyTest):
    def setUp(self):
        super().setUp()
        self.plan = PlanTreningowy.objects.create(nazwa='Moj plan', uzytkownik=self.ania)
        self.cwiczenie_planu = CwiczeniePlanu.objects.create(plan=self.plan, cwiczenie=self.publiczne)
        self.sesja = SesjaTreningowa.objects.create(uzytkownik=self.ania, data=date(2025, 3, 7))
        self.wpis = WpisDziennika.objects.create(
            sesja=self.sesja, cwiczenie=self.publiczne, serie=3, powtorzenia=5, ciezar=60)

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

    def test_edycja_wpisu(self):
        self.client.post(reverse('edytuj_wpis', args=[self.wpis.pk]), {
            'cwiczenie': self.publiczne.pk, 'serie': 5, 'powtorzenia': 3, 'ciezar': '70', 'notatki': '',
        })
        self.wpis.refresh_from_db()
        self.assertEqual((self.wpis.serie, self.wpis.powtorzenia), (5, 3))

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
