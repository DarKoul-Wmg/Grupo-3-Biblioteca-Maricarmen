from django.shortcuts import render
from django.http import HttpResponse
from django.views.static import serve
from django.template.loader import get_template
from django.template.exceptions import TemplateDoesNotExist
from django.core.exceptions import PermissionDenied
import os


from dal import autocomplete
from django.db.models import Q
from django.http import JsonResponse
from .models import Llibre

def index(response):
    try:
        tpl = get_template("index.html")
        return render(response,"index.html")
    except TemplateDoesNotExist:
        return HttpResponse("Backend OK. Posa en marxa el frontend seguint el README.")
    
def protected_serve(request, path, document_root=None, show_indexes=False):
    full_path = os.path.join(document_root, path)

    # If the path is a directory, deny access
    if os.path.isdir(full_path):
        raise PermissionDenied()
        #return HttpResponseForbidden("Accés denegat.")

    # Otherwise serve the file normally
    return serve(request, path, document_root=document_root, show_indexes=show_indexes)


# Autocompletar per a la cerca de llibres
class AutorAutocomplete(autocomplete.Select2ListView):
    def get_list(self):
        if not self.q:
            return []
        return list(
            Llibre.objects.values_list('autor', flat=True)
            .filter(autor__icontains=self.q)
            .distinct()
        )

class EditorialAutocomplete(autocomplete.Select2ListView):
    def get_list(self):
        if not self.q:
            return []
        return list(
            Llibre.objects.values_list('editorial', flat=True)
            .filter(editorial__icontains=self.q)
            .distinct()
        )