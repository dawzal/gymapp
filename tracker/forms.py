from django import forms
from django.forms import inlineformset_factory

from .models import (
    Cwiczenie, CwiczeniePlanu, PlanTreningowy, SeriaWpisu, SesjaTreningowa, WpisDziennika,
)


def ogranicz_cwiczenia(formularz, uzytkownik):
    if uzytkownik is None:
        return
    dostepne = Cwiczenie.dostepne_dla(uzytkownik)
    instancja = getattr(formularz, 'instance', None)
    if instancja is not None and instancja.pk and instancja.cwiczenie_id:
        dostepne = dostepne | Cwiczenie.objects.filter(pk=instancja.cwiczenie_id)
    dostepne = dostepne.distinct()
    formularz.fields['cwiczenie'].queryset = dostepne
    formularz.fields['cwiczenie'].choices = pogrupowane_wybory(dostepne)


def pogrupowane_wybory(cwiczenia):
    grupy = {klucz: [] for klucz, _ in Cwiczenie.KATEGORIE}
    for cwiczenie in cwiczenia.order_by('nazwa'):
        grupy.setdefault(cwiczenie.kategoria, []).append((cwiczenie.pk, cwiczenie.nazwa))
    nazwy = dict(Cwiczenie.KATEGORIE)
    wybory = [('', '---------')]
    for klucz, pozycje in grupy.items():
        if pozycje:
            wybory.append((nazwy.get(klucz, klucz), pozycje))
    return wybory


class CwiczenieForm(forms.ModelForm):
    class Meta:
        model = Cwiczenie
        fields = ['nazwa', 'kategoria', 'opis', 'czy_publiczne']
        widgets = {
            'nazwa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'np. Wyciskanie sztangi'
            }),
            'kategoria': forms.Select(attrs={
                'class': 'form-select'
            }),
            'opis': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Opisz technikę wykonania...'
            }),
            'czy_publiczne': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'nazwa': 'Nazwa ćwiczenia',
            'kategoria': 'Kategoria',
            'opis': 'Opis (opcjonalnie)',
            'czy_publiczne': 'Widoczne dla wszystkich',
        }


class PlanTreningowyForm(forms.ModelForm):
    class Meta:
        model = PlanTreningowy
        fields = ['nazwa', 'opis']
        widgets = {
            'nazwa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'np. Plan Push/Pull/Legs'
            }),
            'opis': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Opisz swój plan treningowy...'
            }),
        }
        labels = {
            'nazwa': 'Nazwa planu',
            'opis': 'Opis (opcjonalnie)',
        }


class CwiczeniePlanuForm(forms.ModelForm):
    class Meta:
        model = CwiczeniePlanu
        fields = ['cwiczenie', 'serie', 'powtorzenia', 'ciezar', 'notatki']
        widgets = {
            'cwiczenie': forms.Select(attrs={'class': 'form-select'}),
            'serie': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20}),
            'powtorzenia': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 100}),
            'ciezar': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.5'}),
            'notatki': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'cwiczenie': 'Ćwiczenie',
            'serie': 'Liczba serii',
            'powtorzenia': 'Liczba powtórzeń',
            'ciezar': 'Ciężar (kg)',
            'notatki': 'Notatki (opcjonalnie)',
        }

    def __init__(self, *args, uzytkownik=None, **kwargs):
        super().__init__(*args, **kwargs)
        ogranicz_cwiczenia(self, uzytkownik)


class SesjaForm(forms.ModelForm):
    class Meta:
        model = SesjaTreningowa
        fields = ['data', 'nazwa', 'notatki']
        widgets = {
            'data': forms.DateInput(format='%Y-%m-%d', attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'nazwa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'np. Trening Push'
            }),
            'notatki': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Jak się czułeś? Co poszło dobrze?'
            }),
        }
        labels = {
            'data': 'Data treningu',
            'nazwa': 'Nazwa sesji (opcjonalnie)',
            'notatki': 'Notatki (opcjonalnie)',
        }


class WpisForm(forms.ModelForm):
    class Meta:
        model = WpisDziennika
        fields = ['cwiczenie', 'notatki']
        widgets = {
            'cwiczenie': forms.Select(attrs={'class': 'form-select'}),
            'notatki': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'cwiczenie': 'Ćwiczenie',
            'notatki': 'Notatki',
        }

    def __init__(self, *args, uzytkownik=None, **kwargs):
        super().__init__(*args, **kwargs)
        ogranicz_cwiczenia(self, uzytkownik)


class NowyWpisForm(forms.Form):
    cwiczenie = forms.ModelChoiceField(
        queryset=Cwiczenie.objects.none(),
        label='Ćwiczenie',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    liczba_serii = forms.IntegerField(
        label='Liczba serii', min_value=1, max_value=20, initial=3,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 20}),
    )
    powtorzenia = forms.IntegerField(
        label='Powtórzenia w serii', min_value=1, max_value=100, initial=10,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 100}),
    )
    ciezar = forms.DecimalField(
        label='Ciężar (kg)', min_value=0, max_digits=6, decimal_places=2, initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.5'}),
    )
    notatki = forms.CharField(
        label='Notatki', required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    )

    def __init__(self, *args, uzytkownik=None, **kwargs):
        super().__init__(*args, **kwargs)
        ogranicz_cwiczenia(self, uzytkownik)

    def zapisz(self, sesja):
        dane = self.cleaned_data
        wpis = WpisDziennika.objects.create(
            sesja=sesja, cwiczenie=dane['cwiczenie'], notatki=dane['notatki'])
        SeriaWpisu.objects.bulk_create([
            SeriaWpisu(wpis=wpis, powtorzenia=dane['powtorzenia'], ciezar=dane['ciezar'])
            for _ in range(dane['liczba_serii'])
        ])
        return wpis


class SeriaForm(forms.ModelForm):
    class Meta:
        model = SeriaWpisu
        fields = ['powtorzenia', 'ciezar']
        widgets = {
            'powtorzenia': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm', 'min': 1, 'max': 100}),
            'ciezar': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm', 'min': 0, 'step': '0.5'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['powtorzenia'].widget.attrs['min'] = 1


SeriaFormSet = inlineformset_factory(
    WpisDziennika, SeriaWpisu, form=SeriaForm, extra=0, can_delete=True)
