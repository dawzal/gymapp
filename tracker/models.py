from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
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

    @classmethod
    def dostepne_dla(cls, uzytkownik):
        return cls.objects.filter(Q(czy_publiczne=True) | Q(dodane_przez=uzytkownik))

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

    def __str__(self):
        return self.nazwa

    class Meta:
        verbose_name = 'Plan treningowy'
        verbose_name_plural = 'Plany treningowe'


class CwiczeniePlanu(models.Model):
    plan = models.ForeignKey(PlanTreningowy, on_delete=models.CASCADE, related_name='cwiczenia')
    cwiczenie = models.ForeignKey(Cwiczenie, on_delete=models.CASCADE)
    serie = models.PositiveIntegerField(default=3, validators=[MinValueValidator(1)])
    powtorzenia = models.PositiveIntegerField(default=10, validators=[MinValueValidator(1)])
    ciezar = models.DecimalField(max_digits=6, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    notatki = models.TextField(blank=True)

    def __str__(self):
        return f"{self.cwiczenie.nazwa} - {self.serie}x{self.powtorzenia}"

    class Meta:
        verbose_name = 'Ćwiczenie planu'
        verbose_name_plural = 'Ćwiczenia planu'


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
    serie = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    powtorzenia = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    ciezar = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(0)])
    notatki = models.TextField(blank=True)

    def __str__(self):
        return f"{self.cwiczenie.nazwa} - {self.serie}x{self.powtorzenia} @ {self.ciezar}kg"

    class Meta:
        verbose_name = 'Wpis dziennika'
        verbose_name_plural = 'Wpisy dziennika'