from django.contrib import admin
from .models import (
    Cwiczenie, CwiczeniePlanu, PlanTreningowy, SeriaWpisu, SesjaTreningowa, WpisDziennika,
)

admin.site.register(Cwiczenie)
admin.site.register(PlanTreningowy)
admin.site.register(CwiczeniePlanu)
admin.site.register(SesjaTreningowa)
admin.site.register(WpisDziennika)
admin.site.register(SeriaWpisu)
