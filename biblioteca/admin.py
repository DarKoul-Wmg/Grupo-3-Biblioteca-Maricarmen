from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import escape, mark_safe
from django.core.exceptions import ValidationError
from django import forms
from django.db.models import Max
from datetime import datetime

from .models import *
from .forms import LlibreForm

def generate_unique_exemplar_code():
    # Get the current year
    current_year = datetime.now().year
    
    # Find the highest number for the current year in the Exemplar model
    last_number = Exemplar.objects.filter(registre__startswith=f"EX-{current_year}-").aggregate(Max('registre'))
    
    # Extract the last used number (if any)
    last_number = last_number.get('registre__max')
    if last_number:
        # Extract the numeric part of the last code (NNNNNN)
        last_num = int(last_number.split('-')[-1])
    else:
        last_num = 0  # If no exemplar exists for the current year, start at 0
    
    # Increment to create a new unique number
    new_number = last_num + 1
    
    # Format the new code: EX-YYYY-NNNNNN
    new_code = f"EX-{current_year}-{new_number:06d}"
    
    return new_code

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
                if not instance.registre:
                    instance.registre = generate_unique_exemplar_code()

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
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "exemplar" and not request.user.is_superuser:
            kwargs["queryset"] = Exemplar.objects.filter(centre=request.user.centre)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(Centre)
admin.site.register(Grup)
admin.site.register(Reserva)
admin.site.register(Prestec,PrestecAdmin)
admin.site.register(Peticio)

class ExemplarAdmin(admin.ModelAdmin):
    list_display = ('registre', 'cataleg_nom','cataleg_tipus', 'centre', 'exclos_prestec', 'baixa')
    search_fields = ('registre', 'cataleg__titol')
    list_filter = ('centre', 'exclos_prestec', 'baixa')
    ordering = ('cataleg__titol',)
    fields = ('registre', 'cataleg', 'centre', 'exclos_prestec', 'baixa')
    
    def get_readonly_fields(self, request, obj=None):
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

    def cataleg_nom(self, obj):
        return obj.cataleg.titol
    cataleg_nom.admin_order_field = 'cataleg__titol'
    cataleg_nom.short_description = 'Títol Catàleg'

    def cataleg_tipus(self, obj):
        # Devuelve el tipo real del catálogo (Llibre, Revista, CD, etc.)
        for tipus in ['llibre', 'revista', 'cd', 'dvd', 'br', 'dispositiu']:
            if hasattr(obj.cataleg, tipus):
                return tipus.capitalize()
        return "Catàleg"
    cataleg_tipus.short_description = 'Tipus'

    def save_model(self, request, obj, form, change):
        """
        Override the save_model method to auto-generate the 'registre' field
        when a new Exemplar is created.
        """
        if not obj.registre:  # Only generate 'registre' if it's not set already
            obj.registre = generate_unique_exemplar_code()
        
        # Ensure the 'centre' is set correctly for non-superusers
        if not request.user.is_superuser and not obj.centre:
            if not request.user.centre:
                raise ValidationError("L'usuari no té cap centre assignat.")
            obj.centre = request.user.centre

        # Save the object
        super().save_model(request, obj, form, change)


admin.site.register(Exemplar, ExemplarAdmin)
