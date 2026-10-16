from django.contrib.auth.models import User
from django.db import models


class WiadomoscCzatu(models.Model):
    ROLE = [
        ('user', 'Użytkownik'),
        ('assistant', 'Asystent'),
    ]

    uzytkownik = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='wiadomosci_czatu')
    rola = models.CharField(max_length=10, choices=ROLE)
    tresc = models.TextField()
    utworzono = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.uzytkownik.username} ({self.rola}): {self.tresc[:40]}"

    class Meta:
        verbose_name = 'Wiadomość czatu'
        verbose_name_plural = 'Wiadomości czatu'
        ordering = ['pk']
