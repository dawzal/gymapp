from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class KontaTest(TestCase):
    def test_rejestracja_tworzy_konto_i_loguje(self):
        odpowiedz = self.client.post(reverse('rejestracja'), {
            'username': 'nowy',
            'password1': 'Silne-haslo-123',
            'password2': 'Silne-haslo-123',
        })
        self.assertRedirects(odpowiedz, reverse('dashboard'))
        self.assertTrue(User.objects.filter(username='nowy').exists())

    def test_logowanie_poprawnym_haslem(self):
        User.objects.create_user('ania', password='haslo12345')
        odpowiedz = self.client.post(reverse('logowanie'), {'username': 'ania', 'password': 'haslo12345'})
        self.assertRedirects(odpowiedz, reverse('dashboard'))

    def test_logowanie_blednym_haslem_nie_loguje(self):
        User.objects.create_user('ania', password='haslo12345')
        self.client.post(reverse('logowanie'), {'username': 'ania', 'password': 'zle'})
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_wylogowanie_wymaga_post(self):
        User.objects.create_user('ania', password='haslo12345')
        self.client.login(username='ania', password='haslo12345')
        self.assertEqual(self.client.get(reverse('wylogowanie')).status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)
        self.client.post(reverse('wylogowanie'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logowanie_przekierowuje_na_adres_next(self):
        User.objects.create_user('ania', password='haslo12345')
        odpowiedz = self.client.post(
            reverse('logowanie') + '?next=' + reverse('dziennik'),
            {'username': 'ania', 'password': 'haslo12345', 'next': reverse('dziennik')},
        )
        self.assertRedirects(odpowiedz, reverse('dziennik'))

    def test_logowanie_ignoruje_obcy_adres_next(self):
        User.objects.create_user('ania', password='haslo12345')
        odpowiedz = self.client.post(
            reverse('logowanie'),
            {'username': 'ania', 'password': 'haslo12345', 'next': 'https://obca-strona.example/'},
        )
        self.assertRedirects(odpowiedz, reverse('dashboard'))

    def test_zalogowany_nie_widzi_strony_logowania(self):
        User.objects.create_user('ania', password='haslo12345')
        self.client.login(username='ania', password='haslo12345')
        odpowiedz = self.client.get(reverse('logowanie'))
        self.assertRedirects(odpowiedz, reverse('dashboard'))
