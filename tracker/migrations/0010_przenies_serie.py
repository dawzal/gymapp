from django.db import migrations


def wpisy_na_serie(apps, schema_editor):
    WpisDziennika = apps.get_model('tracker', 'WpisDziennika')
    SeriaWpisu = apps.get_model('tracker', 'SeriaWpisu')
    nowe = []
    for wpis in WpisDziennika.objects.all():
        for _ in range(wpis.serie):
            nowe.append(SeriaWpisu(wpis=wpis, powtorzenia=wpis.powtorzenia, ciezar=wpis.ciezar))
    SeriaWpisu.objects.bulk_create(nowe)


def serie_na_wpisy(apps, schema_editor):
    WpisDziennika = apps.get_model('tracker', 'WpisDziennika')
    for wpis in WpisDziennika.objects.all():
        serie = list(wpis.serie_wpisu.all())
        if serie:
            wpis.serie = len(serie)
            wpis.powtorzenia = serie[0].powtorzenia
            wpis.ciezar = serie[0].ciezar
            wpis.save(update_fields=['serie', 'powtorzenia', 'ciezar'])


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0009_seria_i_kolejnosc'),
    ]

    operations = [
        migrations.RunPython(wpisy_na_serie, serie_na_wpisy),
    ]
