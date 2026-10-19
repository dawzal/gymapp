import json
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
from django.contrib.auth.models import User
from google.genai import errors, types
from django.test import TestCase, override_settings
from django.urls import reverse

from tracker.models import Cwiczenie, SeriaWpisu, SesjaTreningowa, WpisDziennika

from . import klient
from .klient import BladCzatu
from .kontekst import zbuduj_kontekst
from .models import WiadomoscCzatu


def odpowiedz_api(tekst='Odpowiedź', powod=types.FinishReason.STOP, blokada=None):
    return SimpleNamespace(
        text=tekst,
        candidates=[SimpleNamespace(finish_reason=powod)],
        prompt_feedback=SimpleNamespace(block_reason=blokada),
    )


@override_settings(GEMINI_API_KEY='klucz-testowy', CZAT_DZIENNY_LIMIT=30)
class CzatBazowyTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ania = User.objects.create_user('ania', password='haslo12345')
        cls.bartek = User.objects.create_user('bartek', password='haslo12345')

    def setUp(self):
        self.client.force_login(self.ania)
        self.adres = reverse('czat_wyslij')

    def wyslij(self, tresc='Jak robić przysiad?', **dodatkowe):
        dane = {'tresc': tresc, **dodatkowe}
        return self.client.post(self.adres, data=json.dumps(dane), content_type='application/json')


class StronaCzatuTest(CzatBazowyTest):
    def test_wymaga_logowania(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('czat')).status_code, 302)
        self.assertEqual(self.client.post(self.adres).status_code, 302)

    def test_strona_sie_renderuje(self):
        odpowiedz = self.client.get(reverse('czat'))
        self.assertEqual(odpowiedz.status_code, 200)
        self.assertContains(odpowiedz, 'Asystent treningowy')
        self.assertContains(odpowiedz, 'id="formularz-czatu"')
        self.assertEqual(odpowiedz.context['pozostalo'], 30)

    @override_settings(GEMINI_API_KEY='')
    def test_bez_klucza_pokazuje_komunikat_i_blokuje_formularz(self):
        odpowiedz = self.client.get(reverse('czat'))
        self.assertContains(odpowiedz, 'GEMINI_API_KEY')
        self.assertFalse(odpowiedz.context['skonfigurowany'])

    def test_pokazuje_tylko_wlasna_historie(self):
        WiadomoscCzatu.objects.create(uzytkownik=self.ania, rola='user', tresc='Moje pytanie')
        WiadomoscCzatu.objects.create(uzytkownik=self.bartek, rola='user', tresc='Cudze pytanie')
        odpowiedz = self.client.get(reverse('czat'))
        self.assertContains(odpowiedz, 'Moje pytanie')
        self.assertNotContains(odpowiedz, 'Cudze pytanie')

    def test_tresc_wiadomosci_jest_escapowana(self):
        WiadomoscCzatu.objects.create(
            uzytkownik=self.ania, rola='assistant', tresc='<script>alert(1)</script>')
        odpowiedz = self.client.get(reverse('czat'))
        self.assertNotContains(odpowiedz, '<script>alert(1)</script>')
        self.assertContains(odpowiedz, '&lt;script&gt;alert(1)&lt;/script&gt;')


class WysylanieWiadomosciTest(CzatBazowyTest):
    @patch('czat.views.zapytaj_model', return_value='Plecy proste, kolana na zewnątrz.')
    def test_zapisuje_pytanie_i_odpowiedz(self, atrapa):
        odpowiedz = self.wyslij('Jak robić przysiad?')
        self.assertEqual(odpowiedz.status_code, 200)
        self.assertEqual(odpowiedz.json()['odpowiedz'], 'Plecy proste, kolana na zewnątrz.')
        self.assertEqual(odpowiedz.json()['pozostalo'], 29)
        wiadomosci = list(WiadomoscCzatu.objects.filter(uzytkownik=self.ania))
        self.assertEqual([w.rola for w in wiadomosci], ['user', 'assistant'])
        self.assertEqual(wiadomosci[0].tresc, 'Jak robić przysiad?')

    @patch('czat.views.zapytaj_model', return_value='ok')
    def test_do_modelu_trafia_historia_tylko_tego_uzytkownika(self, atrapa):
        WiadomoscCzatu.objects.create(uzytkownik=self.ania, rola='user', tresc='Pytanie 1')
        WiadomoscCzatu.objects.create(uzytkownik=self.ania, rola='assistant', tresc='Odp 1')
        WiadomoscCzatu.objects.create(uzytkownik=self.bartek, rola='user', tresc='Cudze')
        self.wyslij('Pytanie 2')
        historia, kontekst = atrapa.call_args.args
        self.assertEqual(historia, [
            {'role': 'user', 'content': 'Pytanie 1'},
            {'role': 'assistant', 'content': 'Odp 1'},
            {'role': 'user', 'content': 'Pytanie 2'},
        ])
        self.assertEqual(kontekst, '')

    @override_settings(CZAT_HISTORIA=2)
    @patch('czat.views.zapytaj_model', return_value='ok')
    def test_historia_jest_przycinana_i_zaczyna_od_pytania(self, atrapa):
        for i in range(3):
            WiadomoscCzatu.objects.create(uzytkownik=self.ania, rola='user', tresc=f'P{i}')
            WiadomoscCzatu.objects.create(uzytkownik=self.ania, rola='assistant', tresc=f'O{i}')
        self.wyslij('Nowe')
        historia = atrapa.call_args.args[0]
        self.assertEqual(historia[0]['role'], 'user')
        self.assertEqual(historia[-1], {'role': 'user', 'content': 'Nowe'})
        self.assertLessEqual(len(historia), 3)

    def test_odrzuca_niepoprawne_dane(self):
        for tresc in ('', '   ', 'x' * 1001):
            with self.subTest(dlugosc=len(tresc)):
                self.assertEqual(self.wyslij(tresc).status_code, 400)
        for cialo in ('to nie json', '[]', '{"brak": 1}', '{"tresc": 5}', '{"tresc": ["a"]}'):
            with self.subTest(cialo=cialo):
                odpowiedz = self.client.post(
                    self.adres, data=cialo, content_type='application/json')
                self.assertEqual(odpowiedz.status_code, 400)
        self.assertEqual(WiadomoscCzatu.objects.count(), 0)

    def test_get_jest_niedozwolony(self):
        self.assertEqual(self.client.get(self.adres).status_code, 405)

    @patch('czat.views.zapytaj_model', return_value='ok')
    @override_settings(CZAT_DZIENNY_LIMIT=2)
    def test_dzienny_limit(self, atrapa):
        self.assertEqual(self.wyslij('a').status_code, 200)
        self.assertEqual(self.wyslij('b').status_code, 200)
        odpowiedz = self.wyslij('c')
        self.assertEqual(odpowiedz.status_code, 429)
        self.assertEqual(atrapa.call_count, 2)

    @patch('czat.views.zapytaj_model', return_value='ok')
    @override_settings(CZAT_DZIENNY_LIMIT=1)
    def test_limit_jest_osobny_dla_kazdego_uzytkownika(self, atrapa):
        self.wyslij('a')
        self.client.force_login(self.bartek)
        self.assertEqual(self.wyslij('b').status_code, 200)

    @patch('czat.views.zapytaj_model')
    @override_settings(GEMINI_API_KEY='')
    def test_bez_klucza_zwraca_503_i_nie_wola_api(self, atrapa):
        self.assertEqual(self.wyslij().status_code, 503)
        atrapa.assert_not_called()

    @patch('czat.views.zapytaj_model', side_effect=BladCzatu('Przeciążenie', 429))
    def test_blad_api_nic_nie_zapisuje(self, atrapa):
        odpowiedz = self.wyslij()
        self.assertEqual(odpowiedz.status_code, 429)
        self.assertEqual(odpowiedz.json()['blad'], 'Przeciążenie')
        self.assertEqual(WiadomoscCzatu.objects.count(), 0)

    @patch('czat.views.zapytaj_model', return_value='ok')
    def test_dane_treningowe_tylko_za_zgoda(self, atrapa):
        Cwiczenie.objects.create(nazwa='Przysiad', kategoria='nogi')
        self.wyslij('a')
        self.assertEqual(atrapa.call_args.args[1], '')
        self.wyslij('b', uzyj_danych=True)
        self.assertIn('Dane z dziennika', atrapa.call_args.args[1])

    @patch('czat.views.zapytaj_model', return_value='ok')
    def test_wyczyszczenie_usuwa_tylko_wlasne_wiadomosci(self, atrapa):
        self.wyslij('a')
        WiadomoscCzatu.objects.create(uzytkownik=self.bartek, rola='user', tresc='Cudze')
        odpowiedz = self.client.post(reverse('czat_wyczysc'))
        self.assertRedirects(odpowiedz, reverse('czat'))
        self.assertEqual(WiadomoscCzatu.objects.filter(uzytkownik=self.ania).count(), 0)
        self.assertEqual(WiadomoscCzatu.objects.filter(uzytkownik=self.bartek).count(), 1)

    def test_wyczyszczenie_wymaga_post(self):
        self.assertEqual(self.client.get(reverse('czat_wyczysc')).status_code, 405)


class KontekstTest(CzatBazowyTest):
    def test_zawiera_wykonane_serie_i_rekordy_ale_nie_zaplanowane(self):
        cwiczenie = Cwiczenie.objects.create(nazwa='Wyciskanie', kategoria='klatka')
        sesja = SesjaTreningowa.objects.create(uzytkownik=self.ania, data=date(2025, 3, 7))
        wpis = WpisDziennika.objects.create(sesja=sesja, cwiczenie=cwiczenie)
        SeriaWpisu.objects.create(wpis=wpis, powtorzenia=8, ciezar=60, wykonana=True)
        SeriaWpisu.objects.create(wpis=wpis, powtorzenia=5, ciezar=200, wykonana=False)
        kontekst = zbuduj_kontekst(self.ania)
        self.assertIn('Trening 07.03.2025: Wyciskanie: 8 x 60 kg', kontekst)
        self.assertNotIn('200', kontekst)
        self.assertIn('Rekordy', kontekst)
        self.assertIn('szacowane 1RM', kontekst)

    def test_nie_zawiera_danych_innych_uzytkownikow(self):
        cwiczenie = Cwiczenie.objects.create(nazwa='Tajne', kategoria='inne')
        sesja = SesjaTreningowa.objects.create(uzytkownik=self.bartek, data=date(2025, 3, 7))
        wpis = WpisDziennika.objects.create(sesja=sesja, cwiczenie=cwiczenie)
        SeriaWpisu.objects.create(wpis=wpis, powtorzenia=8, ciezar=60)
        kontekst = zbuduj_kontekst(self.ania)
        self.assertNotIn('Tajne', kontekst)
        self.assertIn('nie ma jeszcze zapisanych', kontekst)

    def test_ma_ograniczona_dlugosc(self):
        cwiczenie = Cwiczenie.objects.create(nazwa='N' * 90, kategoria='inne')
        for dzien in range(1, 6):
            sesja = SesjaTreningowa.objects.create(uzytkownik=self.ania, data=date(2025, 1, dzien))
            wpis = WpisDziennika.objects.create(sesja=sesja, cwiczenie=cwiczenie)
            for _ in range(60):
                SeriaWpisu.objects.create(wpis=wpis, powtorzenia=10, ciezar=100)
        self.assertLessEqual(len(zbuduj_kontekst(self.ania)), 3000)


def blad_api(klasa, kod, komunikat='blad'):
    return klasa(kod, {'error': {'code': kod, 'message': komunikat, 'status': 'BLAD'}})


def atrapa_klienta(wynik=None, wyjatek=None):
    atrapa = MagicMock()
    generuj = atrapa.models.generate_content
    if wyjatek is not None:
        generuj.side_effect = wyjatek
    else:
        generuj.return_value = wynik
    return atrapa


@override_settings(
    GEMINI_API_KEY='klucz-testowy', CZAT_MODEL='gemini-test', CZAT_MODEL_ZAPASOWY='gemini-zapas')
class KlientApiTest(TestCase):
    historia = [
        {'role': 'user', 'content': 'Cześć'},
        {'role': 'assistant', 'content': 'Hej!'},
        {'role': 'user', 'content': 'Jak robić martwy ciąg?'},
    ]

    def test_przekazuje_model_historie_i_prompt_systemowy(self):
        atrapa = atrapa_klienta(odpowiedz_api('Hej'))
        with patch('czat.klient._klient', return_value=atrapa):
            tekst = klient.zapytaj_model(self.historia)
        self.assertEqual(tekst, 'Hej')
        parametry = atrapa.models.generate_content.call_args.kwargs
        self.assertEqual(parametry['model'], 'gemini-test')
        self.assertEqual(
            [(tresc.role, tresc.parts[0].text) for tresc in parametry['contents']],
            [('user', 'Cześć'), ('model', 'Hej!'), ('user', 'Jak robić martwy ciąg?')])
        self.assertEqual(parametry['config'].system_instruction, klient.PROMPT_SYSTEMOWY)
        self.assertEqual(parametry['config'].max_output_tokens, klient.MAKS_TOKENOW)

    def test_kontekst_treningowy_trafia_do_instrukcji_systemowej(self):
        atrapa = atrapa_klienta(odpowiedz_api())
        with patch('czat.klient._klient', return_value=atrapa):
            klient.zapytaj_model(self.historia, 'Kontekst treningowy')
        instrukcja = atrapa.models.generate_content.call_args.kwargs['config'].system_instruction
        self.assertTrue(instrukcja.startswith(klient.PROMPT_SYSTEMOWY))
        self.assertTrue(instrukcja.endswith('Kontekst treningowy'))

    def test_odmowa_modelu_daje_czytelny_blad(self):
        for odpowiedz in (
            odpowiedz_api('', powod=types.FinishReason.SAFETY),
            odpowiedz_api('', blokada='SAFETY'),
        ):
            with self.subTest(odpowiedz=odpowiedz):
                with patch('czat.klient._klient', return_value=atrapa_klienta(odpowiedz)):
                    with self.assertRaises(BladCzatu) as kontekst:
                        klient.zapytaj_model(self.historia)
                self.assertEqual(kontekst.exception.status, 422)

    def test_pusta_odpowiedz_daje_blad(self):
        pusta = SimpleNamespace(
            text=None, candidates=None, prompt_feedback=SimpleNamespace(block_reason=None))
        with patch('czat.klient._klient', return_value=atrapa_klienta(pusta)):
            with self.assertRaises(BladCzatu) as kontekst:
                klient.zapytaj_model(self.historia)
        self.assertEqual(kontekst.exception.status, 502)

    def test_mapowanie_bledow_api(self):
        przypadki = [
            (blad_api(errors.ClientError, 401), 503),
            (blad_api(errors.ClientError, 403), 503),
            (blad_api(errors.ClientError, 400, 'API key not valid'), 503),
            (blad_api(errors.ClientError, 404), 503),
            (blad_api(errors.ClientError, 429), 429),
            (blad_api(errors.ClientError, 400, 'Niepoprawne zapytanie'), 502),
            (blad_api(errors.ServerError, 500), 502),
            (blad_api(errors.ServerError, 503), 502),
            (httpx.ConnectError('brak sieci'), 502),
            (httpx.ReadTimeout('timeout'), 502),
        ]
        for wyjatek, oczekiwany in przypadki:
            with self.subTest(wyjatek=repr(wyjatek)):
                with patch('czat.klient._klient', return_value=atrapa_klienta(wyjatek=wyjatek)):
                    with self.assertRaises(BladCzatu) as kontekst:
                        klient.zapytaj_model(self.historia)
                self.assertEqual(kontekst.exception.status, oczekiwany)

    def test_przeciazony_model_przelacza_na_zapasowy(self):
        atrapa = MagicMock()
        atrapa.models.generate_content.side_effect = [
            blad_api(errors.ServerError, 503), odpowiedz_api('Z zapasowego')]
        with patch('czat.klient._klient', return_value=atrapa):
            self.assertEqual(klient.zapytaj_model(self.historia), 'Z zapasowego')
        modele = [w.kwargs['model'] for w in atrapa.models.generate_content.call_args_list]
        self.assertEqual(modele, ['gemini-test', 'gemini-zapas'])

    def test_oba_modele_przeciazone_daje_blad_502(self):
        atrapa = atrapa_klienta(wyjatek=blad_api(errors.ServerError, 503))
        with patch('czat.klient._klient', return_value=atrapa):
            with self.assertRaises(BladCzatu) as kontekst:
                klient.zapytaj_model(self.historia)
        self.assertEqual(kontekst.exception.status, 502)
        self.assertEqual(atrapa.models.generate_content.call_count, 2)

    def test_klucz_nie_trafia_do_komunikatow_o_bledach(self):
        wyjatek = blad_api(errors.ClientError, 400, 'API key not valid: klucz-testowy')
        with patch('czat.klient._klient', return_value=atrapa_klienta(wyjatek=wyjatek)):
            with self.assertRaises(BladCzatu) as kontekst:
                klient.zapytaj_model(self.historia)
        self.assertNotIn('klucz-testowy', kontekst.exception.komunikat)

    def test_klient_ma_ustawiony_klucz_i_limit_czasu(self):
        with patch('czat.klient.genai.Client') as atrapa:
            klient._klient()
        parametry = atrapa.call_args.kwargs
        self.assertEqual(parametry['api_key'], 'klucz-testowy')
        self.assertEqual(parametry['http_options'].timeout, klient.TIMEOUT_MS)

    @override_settings(GEMINI_API_KEY='')
    def test_skonfigurowany_zalezy_od_klucza(self):
        self.assertFalse(klient.czat_skonfigurowany())
        with override_settings(GEMINI_API_KEY='x'):
            self.assertTrue(klient.czat_skonfigurowany())
