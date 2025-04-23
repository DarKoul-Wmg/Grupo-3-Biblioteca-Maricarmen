from dal import autocomplete
from django import forms
from .models import Llibre

class LlibreForm(forms.ModelForm):
    autor = forms.CharField(
        widget=autocomplete.Select2(
            url='autor-autocomplete'
        ),
        required=False,
        label="Autor"
    )
    editorial = forms.CharField(
        widget=autocomplete.Select2(
            url='editorial-autocomplete'
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