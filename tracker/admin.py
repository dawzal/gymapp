from django.contrib import admin
from .models import Cwiczenie, PlanTreningowy, DzienPlanTreningowego, CwiczenieDnia, SesjaTreningowa, WpisDziennika

admin.site.register(Cwiczenie)
admin.site.register(PlanTreningowy)
admin.site.register(DzienPlanTreningowego)
admin.site.register(CwiczenieDnia)
admin.site.register(SesjaTreningowa)
admin.site.register(WpisDziennika)