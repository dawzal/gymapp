from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Max, Q
from django.contrib.auth.models import User


def formatuj_minuty(minuty):
    if minuty is None:
        return ''
    if minuty < 60:
        return f'{minuty} min'
    return f'{minuty // 60} h {minuty % 60:02d} min'


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
    POZIOMY = [
        ('poczatkujacy', 'Początkujący'),
        ('sredni', 'Średniozaawansowany'),
    ]

    nazwa = models.CharField(max_length=100)
    opis = models.TextField(blank=True)
    uzytkownik = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    poziom = models.CharField(max_length=20, choices=POZIOMY, blank=True)
    data_utworzenia = models.DateTimeField(auto_now_add=True)

    @property
    def czy_gotowy(self):
        return self.uzytkownik_id is None

    def kopiuj_dla(self, uzytkownik):
        kopia = PlanTreningowy.objects.create(
            nazwa=self.nazwa, opis=self.opis, uzytkownik=uzytkownik)
        CwiczeniePlanu.objects.bulk_create([
            CwiczeniePlanu(
                plan=kopia, cwiczenie=c.cwiczenie, serie=c.serie,
                powtorzenia=c.powtorzenia, ciezar=c.ciezar, notatki=c.notatki,
                kolejnosc=pozycja)
            for pozycja, c in enumerate(self.cwiczenia.select_related('cwiczenie'))
        ])
        return kopia

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
    kolejnosc = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if self._state.adding and self.kolejnosc == 0:
            najwieksza = CwiczeniePlanu.objects.filter(plan=self.plan).aggregate(
                najwieksza=Max('kolejnosc'))['najwieksza']
            self.kolejnosc = 0 if najwieksza is None else najwieksza + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cwiczenie.nazwa} - {self.serie}x{self.powtorzenia}"

    class Meta:
        verbose_name = 'Ćwiczenie planu'
        verbose_name_plural = 'Ćwiczenia planu'
        ordering = ['kolejnosc', 'pk']


class SesjaTreningowa(models.Model):
    uzytkownik = models.ForeignKey(User, on_delete=models.CASCADE)
    data = models.DateField()
    nazwa = models.CharField(max_length=100, blank=True)
    notatki = models.TextField(blank=True)
    rozpoczeto = models.DateTimeField(null=True, blank=True)
    zakonczono = models.DateTimeField(null=True, blank=True)

    @property
    def czas_trwania_minuty(self):
        if self.rozpoczeto and self.zakonczono:
            sekundy = (self.zakonczono - self.rozpoczeto).total_seconds()
            return max(1, round(sekundy / 60))
        return None

    @property
    def czas_trwania_tekst(self):
        return formatuj_minuty(self.czas_trwania_minuty)

    @property
    def trwa(self):
        return self.rozpoczeto is not None and self.zakonczono is None

    def __str__(self):
        return f"{self.uzytkownik.username} - {self.data}"

    class Meta:
        verbose_name = 'Sesja treningowa'
        verbose_name_plural = 'Sesje treningowe'
        ordering = ['-data']


class WpisDziennika(models.Model):
    sesja = models.ForeignKey(SesjaTreningowa, on_delete=models.CASCADE, related_name='wpisy')
    cwiczenie = models.ForeignKey(Cwiczenie, on_delete=models.CASCADE)
    notatki = models.TextField(blank=True)

    def __str__(self):
        return f"{self.cwiczenie.nazwa} ({self.sesja.data})"

    class Meta:
        verbose_name = 'Wpis dziennika'
        verbose_name_plural = 'Wpisy dziennika'
        ordering = ['pk']


class SeriaWpisu(models.Model):
    wpis = models.ForeignKey(WpisDziennika, on_delete=models.CASCADE, related_name='serie')
    powtorzenia = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    ciezar = models.DecimalField(
        max_digits=6, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    wykonana = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.powtorzenia} x {self.ciezar} kg"

    class Meta:
        verbose_name = 'Seria'
        verbose_name_plural = 'Serie'
        ordering = ['pk']
