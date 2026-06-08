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