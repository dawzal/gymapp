from django.db import models
from django.contrib.auth.models import User

class Cwiczenie(models.Model):
    KATEGORIE = [
        ('klatka', 'Klatka piersiowa'),
        ('plecy', 'Plecy'),
        ('nogi', 'Nogi'),
        ('barki', 'Barki'),
        ('biceps', 'Biceps'),
        ('triceps', 'Triceps'),
        ('brzuch', 'Brzuch'),
        ('inne', 'Inne'),
    ]

    nazwa = models.CharField(max_length=100)
    kategoria = models.CharField(max_length=20, choices=KATEGORIE)
    opis = models.TextField(blank=True)
    dodane_przez = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    czy_publiczne = models.BooleanField(default=True)

    def __str__(self):
        return self.nazwa
    
    class Meta:
        verbose_name = 'Ćwiczenie'
        verbose_name_plural = 'Ćwiczenia'

class PlanTreningowy(models.Model):
    nazwa = models.CharField(max_length=100)
    opis = models.TextField(blank=True)
    uzytkownik = models.ForeignKey(User, on_delete=models.CASCADE)
    data_utworzenia = models.DateTimeField(auto_now_add=True)
    czy_publiczny = models.BooleanField(default=False)

    def __str__(self):
        return self.nazwa

    class Meta:
        verbose_name = 'Plan treningowy'
        verbose_name_plural = 'Plany treningowe'


class DzienPlanTreningowego(models.Model):
    DNI = [
        ('poniedzialek', 'Poniedziałek'),
        ('wtorek', 'Wtorek'),
        ('sroda', 'Środa'),
        ('czwartek', 'Czwartek'),
        ('piatek', 'Piątek'),
        ('sobota', 'Sobota'),
        ('niedziela', 'Niedziela'),
    ]

    plan = models.ForeignKey(PlanTreningowy, on_delete=models.CASCADE, related_name='dni')
    dzien = models.CharField(max_length=20, choices=DNI)
    kolejnosc = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.plan.nazwa} - {self.get_dzien_display()}"

    class Meta:
        verbose_name = 'Dzień planu'
        verbose_name_plural = 'Dni planu'
        ordering = ['kolejnosc']


class CwiczenieDnia(models.Model):
    dzien = models.ForeignKey(DzienPlanTreningowego, on_delete=models.CASCADE, related_name='cwiczenia')
    cwiczenie = models.ForeignKey(Cwiczenie, on_delete=models.CASCADE)
    serie = models.PositiveIntegerField(default=3)
    powtorzenia = models.PositiveIntegerField(default=10)
    czas_odpoczynku = models.PositiveIntegerField(default=60, help_text='Czas odpoczynku w sekundach')

    def __str__(self):
        return f"{self.cwiczenie.nazwa} - {self.serie}x{self.powtorzenia}"

    class Meta:
        verbose_name = 'Ćwiczenie dnia'
        verbose_name_plural = 'Ćwiczenia dnia'

class SesjaTreningowa(models.Model):
    uzytkownik = models.ForeignKey(User, on_delete=models.CASCADE)
    data = models.DateField()
    nazwa = models.CharField(max_length=100, blank=True)
    notatki = models.TextField(blank=True)

    def __str__(self):
        return f"{self.uzytkownik.username} - {self.data}"

    class Meta:
        verbose_name = 'Sesja treningowa'
        verbose_name_plural = 'Sesje treningowe'
        ordering = ['-data']


class WpisDziennika(models.Model):
    sesja = models.ForeignKey(SesjaTreningowa, on_delete=models.CASCADE, related_name='wpisy')
    cwiczenie = models.ForeignKey(Cwiczenie, on_delete=models.CASCADE)
    serie = models.PositiveIntegerField()
    powtorzenia = models.PositiveIntegerField()
    ciezar = models.DecimalField(max_digits=6, decimal_places=2)
    notatki = models.TextField(blank=True)

    def __str__(self):
        return f"{self.cwiczenie.nazwa} - {self.serie}x{self.powtorzenia} @ {self.ciezar}kg"

    class Meta:
        verbose_name = 'Wpis dziennika'
        verbose_name_plural = 'Wpisy dziennika'