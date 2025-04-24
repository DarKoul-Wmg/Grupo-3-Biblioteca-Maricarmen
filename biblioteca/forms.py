from dal import autocomplete
from django import forms
from .models import Llibre

class LlibreForm(forms.ModelForm):
    autor = forms.CharField(
        widget=autocomplete.Select2(
            url='autor-autocomplete',
            attrs={
                'data-placeholder': 'Escriu o selecciona un autor...',
                'data-allow-clear': 'true',
                'data-tags': 'true',  # Permite crear nuevos valores
            }
        ),
        required=False,
        label="Autor"
    )
    editorial = forms.CharField(
        widget=autocomplete.Select2(
            url='editorial-autocomplete',
            attrs={
                'data-placeholder': 'Escriu o selecciona una editorial...',
                'data-allow-clear': 'true',
                'data-tags': 'true',
            }
        ),
        required=False,
        label="Editorial"
    )

    class Meta:
        model = Llibre
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si el formulario está vinculado a una instancia, cargamos los valores iniciales
        if self.instance and self.instance.pk:
            # Configurar el valor inicial para el widget de autocompletar
            if self.instance.autor:
                self.fields['autor'].widget.choices = [(self.instance.autor, self.instance.autor)]
                self.fields['autor'].initial = self.instance.autor
            if self.instance.editorial:
                self.fields['editorial'].widget.choices = [(self.instance.editorial, self.instance.editorial)]
                self.fields['editorial'].initial = self.instance.editorial