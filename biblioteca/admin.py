from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import escape, mark_safe


from .models import *
from .forms import LlibreForm

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

class ExemplarsInline(admin.TabularInline):
	model = Exemplar
	extra = 1
	readonly_fields = ('pk',)
	fields = ('pk','registre','exclos_prestec','baixa','centre',)
 
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
				if not request.user.is_superuser:
					instance.centre = request.user.centre
				instance.exclos_prestec = False  # valor per defecte
				if commit:
					instance.save()
				return instance

		return CustomFormset

	def get_fields(self, request, obj=None):
		fields = list(super().get_fields(request, obj))
		if not request.user.is_superuser and 'centre' in fields:
			fields.remove('centre')
		return fields

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
admin.site.register(Revista)
admin.site.register(Dispositiu)
admin.site.register(Imatge)

class PrestecAdmin(admin.ModelAdmin):
    fields = ('exemplar','usuari','data_prestec','data_retorn','anotacions')
    list_display = ('exemplar','usuari','data_prestec','data_retorn')

admin.site.register(Centre)
admin.site.register(Grup)
admin.site.register(Reserva)
admin.site.register(Prestec,PrestecAdmin)
admin.site.register(Peticio)
