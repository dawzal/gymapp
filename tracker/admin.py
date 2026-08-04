from django.contrib import admin
from .models import Cwiczenie, PlanTreningowy, DzienPlanTreningowego, CwiczenieDnia, SesjaTreeningowa, WpisDziennika

admin.site.register(Cwiczenie)
admin.site.register(PlanTreningowy)
admin.site.register(DzienPlanTreningowego)
admin.site.register(CwiczenieDnia)
admin.site.register(SesjaTreeningowa)
admin.site.register(WpisDziennika)