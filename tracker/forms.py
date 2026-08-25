from django import forms
from .models import Cwiczenie, PlanTreningowy, CwiczeniePlanu, SesjaTreningowa, WpisDziennika


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
        fields = ['nazwa', 'opis', 'czy_publiczny']
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
            'czy_publiczny': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'nazwa': 'Nazwa planu',
            'opis': 'Opis (opcjonalnie)',
            'czy_publiczny': 'Widoczny dla innych użytkowników',
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


class SesjaForm(forms.ModelForm):
    class Meta:
        model = SesjaTreningowa
        fields = ['data', 'nazwa', 'notatki']
        widgets = {
            'data': forms.DateInput(attrs={
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
        fields = ['cwiczenie', 'serie', 'powtorzenia', 'ciezar', 'notatki']
        widgets = {
            'cwiczenie': forms.Select(attrs={'class': 'form-select'}),
            'serie': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'powtorzenia': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'ciezar': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.5'}),
            'notatki': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'cwiczenie': 'Ćwiczenie',
            'serie': 'Serie',
            'powtorzenia': 'Powtórzenia',
            'ciezar': 'Ciężar (kg)',
            'notatki': 'Notatki',
        }