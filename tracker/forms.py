from django import forms
from .models import Cwiczenie

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