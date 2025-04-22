from dal import autocomplete
from django import forms
from .models import Llibre

class LlibreForm(forms.ModelForm):
    autor = forms.CharField(
        widget=autocomplete.ListSelect2(
            url='autor-autocomplete'
        ),
        required=False,
        label="Autor"
    )
    editorial = forms.CharField(
        widget=autocomplete.ListSelect2(
            url='editorial-autocomplete'
        ),
        required=False,
        label="Editorial"
    )

    class Meta:
        model = Llibre
        fields = '__all__'