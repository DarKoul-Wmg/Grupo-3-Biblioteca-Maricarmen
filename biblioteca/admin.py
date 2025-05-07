from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import escape, mark_safe
from datetime import datetime
from django.core.exceptions import ValidationError
from django import forms


from .models import *
from .forms import LlibreForm

def generate_unique_exemplar_code_for_catalegItem(cataleg):
    year = datetime.now().year
    prefix = f"EX-{year}"

    # Get highest existing number for this catalog item
    latest_exemplar = (
        Exemplar.objects
        .filter(cataleg=cataleg, registre__startswith=prefix)
        .order_by("-registre")
        .first()
    )

    if latest_exemplar and latest_exemplar.registre:
        try:
            last_number = int(latest_exemplar.registre.split("-")[-1])
        except (IndexError, ValueError):
            last_number = 0
    else:
        last_number = 0

    new_number = last_number + 1
    return f"{prefix}-{str(new_number).zfill(6)}"

class CategoriaAdmin(admin.ModelAdmin):
	list_display = ('nom','parent')
	ordering = ('parent','nom')


class UsuariAdmin(UserAdmin):
    fieldsets = list(UserAdmin.fieldsets)  # Convertimos a lista para poder modificar los campos del admin panel (django)

    # telefon en grup existent
    fieldsets[1] = (
        fieldsets[1][0],
        {'fields': fieldsets[1][1]['fields'] + ('telefon',)}
    )

    fieldsets += (
        ("Dades acadèmiques", {
            'fields': ('centre', 'grup', 'imatge'),
        }),
    )

class MarkNewInstancesAsChangedModelForm(forms.ModelForm):
    def has_changed(self):
        """Returns True for new instances, calls super() for ones that exist in db.
        Prevents forms with defaults being recognized as empty/unchanged."""
        return not self.instance.pk or super().has_changed()

class ExemplarsInline(admin.TabularInline):
    model = Exemplar
    extra = 0  # Set to 0 to prevent any pre-filled extra forms
    form = MarkNewInstancesAsChangedModelForm
    fields = ('registre', 'exclos_prestec', 'baixa', 'centre')  # Removed 'pk' field

    def get_readonly_fields(self, request, obj=None):
        # Always make 'registre' readonly for everyone
        readonly = list(super().get_readonly_fields(request, obj))
        readonly.append('registre')  # Ensure 'registre' is readonly
        if not request.user.is_superuser:
            readonly.append('centre')  # Make 'centre' readonly for non-superusers
        return readonly

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(centre=request.user.centre)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)

        class CustomFormset(formset):
            def save_new(self, form, commit=True):
                instance = super().save_new(form, commit=False)

                # Auto-generate registre if not set
                instance.registre = generate_unique_exemplar_code_for_catalegItem(instance.cataleg)
                
                if not request.user.is_superuser:
                    if not request.user.centre:
                        raise ValidationError("L'usuari no té cap centre assignat.")
                    instance.centre = request.user.centre

                if commit:
                    instance.save()
                return instance

            def save_m2m(self):
                # Overriding save_m2m to handle many-to-many relationships if needed
                for form in self.forms:
                    if form.has_changed():
                        form.save_m2m()
                
                # Call to save the instances
                for form in self.forms:
                    if form.has_changed():
                        form.save()

        return CustomFormset

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if not request.user.is_superuser and 'centre' in fields:
            fields.remove('centre')  # Remove 'centre' field for non-superusers
        return fields

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Automatically populate the 'centre' field for non-superuser users.
        """
        if db_field.name == 'centre' and not request.user.is_superuser:
            kwargs['initial'] = request.user.centre
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class LlibreAdmin(admin.ModelAdmin):
	form = LlibreForm
	filter_horizontal = ('tags',)
	inlines = [ExemplarsInline,]
	search_fields = ('titol','autor','CDU','signatura','ISBN','editorial','colleccio')
	list_display = ('titol','autor','editorial','num_exemplars')
	readonly_fields = ('thumb',)
	def num_exemplars(self,obj):
		return obj.exemplar_set.count()
	def thumb(self,obj):
		return mark_safe("<img src='{}' />".format(escape(obj.thumbnail_url)))
	thumb.allow_tags = True

admin.site.register(Usuari,UsuariAdmin)
admin.site.register(Categoria,CategoriaAdmin)
admin.site.register(Pais)
admin.site.register(Llengua)
admin.site.register(Llibre,LlibreAdmin)
admin.site.register(Imatge)

class RevistaAdmin(admin.ModelAdmin):
	inlines = [ExemplarsInline]
admin.site.register(Revista,RevistaAdmin)

class CDAdmin(admin.ModelAdmin):
    inlines = [ExemplarsInline]
admin.site.register(CD, CDAdmin)

class BRAdmin(admin.ModelAdmin):
    inlines = [ExemplarsInline]
admin.site.register(BR, BRAdmin)

class DVDAdmin(admin.ModelAdmin):
    inlines = [ExemplarsInline]
admin.site.register(DVD, DVDAdmin)

class DispositiuAdmin(admin.ModelAdmin):
    inlines = [ExemplarsInline]
admin.site.register(Dispositiu, DispositiuAdmin)

class PrestecAdmin(admin.ModelAdmin):
    fields = ('exemplar','usuari','data_prestec','data_retorn','anotacions')
    list_display = ('exemplar','usuari','data_prestec','data_retorn')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(exemplar__centre=request.user.centre)

admin.site.register(Centre)
admin.site.register(Grup)
admin.site.register(Reserva)
admin.site.register(Prestec,PrestecAdmin)
admin.site.register(Peticio)
