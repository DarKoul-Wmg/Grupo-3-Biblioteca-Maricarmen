from django.contrib.auth import authenticate
from ninja import NinjaAPI, Schema, File, Form, Query
from ninja.files import UploadedFile
from ninja.errors import HttpError
from ninja.responses import Response
from ninja.security import HttpBasicAuth, HttpBearer
from django.http import HttpRequest
from django.db.models import Q

from .models import *
from typing import List, Optional, Union, Dict, Any
import re  # For email validation
import io  # For handling in-memory file operations
import csv  # For CSV file handling
import secrets
from math import ceil

api = NinjaAPI()


# Autenticació bàsica
class BasicAuth(HttpBasicAuth):
    def authenticate(self, request, username, password):
        try:
            # Busca al usuario por email
            user = Usuari.objects.get(email=username)
            # Verifica la contraseña
            if user.check_password(password):
                # Genera un token simple
                token = secrets.token_hex(16)
                user.auth_token = token
                user.save()
                return token
            return user
        except Usuari.DoesNotExist:
            return None
        except Exception as e:
            raise HttpError(500, "Ha ocurrido un error al autenticar el usuario.")


# Autenticació per Token Bearer
class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            user = Usuari.objects.get(auth_token=token)
            return user
        except Usuari.DoesNotExist:
            return None



class UsuariOut(Schema):
    id: int
    first_name: str
    last_name: str
    email: str
    telefon: Optional[str]
    centre: Optional[str]  
    groups: List[str]  
    imatge: Optional[str]  
    
# Endpoint per obtenir informació de l'usuari
@api.get("/user-info", auth=AuthBearer())
def get_user_info(request):
    user = request.auth  # Usuario autenticado por el token

    # Obtener los grupos (roles) del usuario
    groups = list(user.groups.values_list("name", flat=True))

    # Obtener el nombre del centro (si existe)
    centre = user.centre.nom if user.centre else None

    # Construir la URL de la imagen del usuario (si existe)
    imatge_url = (
        request.build_absolute_uri(user.imatge.url) if user.imatge else None
    )

    # Serializar los datos del usuario
    user_data = UsuariOut(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        telefon=user.telefon,
        centre=centre,
        groups=groups,
        imatge=imatge_url,
    )

    return {
        "user-details": user_data.dict(),  # Convertir a dict para incluir en la respuesta
    }

@api.get("/usuaris/{info}")
def buscar_usuaris(request, info: str):
    info = info.strip()

    usuaris = Usuari.objects.filter(
        Q(first_name__icontains=info) |
        Q(last_name__icontains=info) |
        Q(email__icontains=info) |
        Q(telefon__icontains=info) |
        Q(username__icontains=info)
    )

    return [
        {
            "id": u.id,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "username": u.username,
            "email": u.email,
            "telefon": u.telefon,
            "centre": u.centre.nom if u.centre else None,
            "cicle": u.cicle.nom if u.cicle else None,
        }
        for u in usuaris
    ]

# Endpoint per obtenir un token
@api.get("/token", auth=BasicAuth())
@api.get("/token/", auth=BasicAuth())
def obtenir_token(request):
    return {"token": request.auth}

class CatalegOut(Schema):
    id: int
    titol: str
    autor: Optional[str]

class LlibreOut(CatalegOut):
    editorial: Optional[str]
    ISBN: Optional[str]

class ExemplarOut(Schema):
    id: int
    registre: str
    exclos_prestec: bool
    baixa: bool
    cataleg: Union[LlibreOut,CatalegOut]
    tipus: str

class CentreOut(Schema):
    nom: str
    
class ExemplarInLlibreOut(Schema):
    id: int
    registre: Optional[str]
    exclos_prestec: bool
    baixa: bool
    centre: Optional[CentreOut]

class LlibreDetailOut(CatalegOut):
    editorial: Optional[str]
    ISBN: Optional[str]
    colleccio: Optional[str]
    lloc: Optional[str]
    pais: Optional[str]  # Or use PaisOut if you want full info
    llengua: Optional[str]
    numero: Optional[int]
    volums: Optional[int]
    pagines: Optional[int]
    info_url: Optional[str]
    preview_url: Optional[str]
    thumbnail_url: Optional[str]
    exemplars: List[ExemplarInLlibreOut] = []

class LlibreIn(Schema):
    titol: str
    editorial: str


@api.get("/llibres", response=List[LlibreOut])
@api.get("/llibres/", response=List[LlibreOut])
#@api.get("/llibres/", response=List[LlibreOut], auth=AuthBearer())
def get_llibres(request):
    qs = Llibre.objects.all()
    return qs

@api.get("/llibres/search", response=Dict[str, Any])
def search_llibres(request, text: str, page: int = Query(1)):
    text_lower = text.lower()

    # busca titulo y autor (sin duplicados)
    llibres = Llibre.objects.filter(titol__icontains=text) | Llibre.objects.filter(autor__icontains=text)
    llibres = llibres.distinct()

    # Ordena por coincidencia exacta primero, luego por posicion de la coincidencia
    def relevance_key(llibre):
        titol = llibre.titol.lower()
        autor = llibre.autor.lower()

        if titol == text_lower or autor == text_lower:
            return (0, 0)

        titol_index = titol.find(text_lower)
        autor_index = autor.find(text_lower)

        titol_score = titol_index if titol_index != -1 else 999
        autor_score = autor_index if autor_index != -1 else 999

        return (1, min(titol_score, autor_score))

    llibres_sorted = sorted(llibres, key=relevance_key)

    # Pagination logic
    items_per_page = 10
    total_items = len(llibres_sorted)
    total_pages = ceil(total_items / items_per_page)

    if page < 1:
        page = 1
        
    if page > total_pages:
        page = total_pages

    start = (page - 1) * items_per_page
    end = start + items_per_page
    llibres_paginated = llibres_sorted[start:end]

    return {
        "current_page": page,
        "total_pages": total_pages,
        "results": [LlibreOut.from_orm(llibre) for llibre in llibres_paginated]
    }
    
@api.get("/catalegs/search", response=Dict[str, Any])
def search_catalegs(request, text: str, page: int = Query(1)):
    text_lower = text.lower()
    query = Q(titol__icontains=text) | Q(autor__icontains=text)

    all_results = []
    for model in [Llibre, Revista, CD, DVD, BR, Dispositiu]:
        results = list(model.objects.filter(query).distinct())
        all_results.extend(results)

    def relevance_key(obj):
        titol = obj.titol.lower()
        autor = obj.autor.lower() if hasattr(obj, "autor") and obj.autor else ""
        if titol == text_lower or autor == text_lower:
            return (0, 0)

        titol_index = titol.find(text_lower)
        autor_index = autor.find(text_lower)

        titol_score = titol_index if titol_index != -1 else 999
        autor_score = autor_index if autor_index != -1 else 999

        return (1, min(titol_score, autor_score))

    sorted_results = sorted(all_results, key=relevance_key)

    items_per_page = 10
    total_items = len(sorted_results)
    total_pages = ceil(total_items / items_per_page)

    page = max(1, min(page, total_pages))
    start = (page - 1) * items_per_page
    end = start + items_per_page
    paginated = sorted_results[start:end]

    def serialize(obj):
        base_data = {
            "id": obj.id,
            "titol": obj.titol,
            "autor": getattr(obj, "autor", None),
            "type": obj.__class__.__name__,
        }

        if isinstance(obj, Llibre):
            schema_data = LlibreOut.from_orm(obj).dict()
        else:
            schema_data = CatalegOut.from_orm(obj).dict()

        return {
            **base_data,
            **schema_data
        }

    return {
        "current_page": page,
        "total_pages": total_pages,
        "results": [serialize(o) for o in paginated]
    }

@api.get("/llibres/{llibre_id}", response=LlibreDetailOut)
def get_llibre_by_id(request, llibre_id: int):
    try:
        llibre = Llibre.objects.get(id=llibre_id)
        exemplars = list(Exemplar.objects.select_related("centre").filter(cataleg=llibre))

        # Preparar un diccionario con los datos necesarios para el esquema
        data = {
            "id": llibre.id,
            "titol": llibre.titol,
            "autor": llibre.autor,
            "editorial": llibre.editorial,
            "ISBN": llibre.ISBN,
            "colleccio": llibre.colleccio,
            "lloc": llibre.lloc,
            "pais": str(llibre.pais) if llibre.pais else None,
            "llengua": str(llibre.llengua) if llibre.llengua else None,
            "numero": llibre.numero,
            "volums": llibre.volums,
            "pagines": llibre.pagines,
            "info_url": llibre.info_url,
            "preview_url": llibre.preview_url,
            "thumbnail_url": llibre.thumbnail_url,
            "exemplars": [
                ExemplarInLlibreOut(
                    id=ex.id,
                    registre=ex.registre,
                    exclos_prestec=ex.exclos_prestec,
                    baixa=ex.baixa,
                    centre=CentreOut(nom=ex.centre.nom) if ex.centre else None,
                )
                for ex in exemplars
            ]
        }

        return data
    except Llibre.DoesNotExist:
        raise HttpError(404, "Llibre not found")
    
@api.get("/catalog/{model_type}/{item_id}", response=Dict)
def get_catalog_item(request, model_type: str, item_id: int):
    # Define a dictionary of model types for quick lookup
    model_map = {
        'Llibre': Llibre,
        'Revista': Revista,
        'CD': CD,
        'DVD': DVD,
        'BR': BR,
        'Dispositiu': Dispositiu,
    }

    # Check if the model_type is valid
    if model_type not in model_map:
        raise HttpError(400, "Invalid model type")

    # Get the model class based on the model_type
    model_class = model_map[model_type]

    try:
        # Retrieve the item by ID from the corresponding model
        item = model_class.objects.get(id=item_id)

        # Retrieve Exemplars associated with this item
        exemplars = list(Exemplar.objects.select_related("centre").filter(cataleg=item))

        # Prepare the response data
        data = {
            "id": item.id,
            "titol": item.titol,
            "autor": item.autor,
            "resum": item.resum,
            "model_type": model_type,  # Adding model type in the response
        }

        # Add model-specific fields to the response
        if isinstance(item, Llibre):
            data["ISBN"] = item.ISBN
            data["editorial"] = item.editorial
            data["colleccio"] = item.colleccio
            data["lloc"] = item.lloc
            data["pais"] = str(item.pais) if item.pais else None
            data["llengua"] = str(item.llengua) if item.llengua else None
            data["numero"] = item.numero
            data["volums"] = item.volums
            data["pagines"] = item.pagines
            data["info_url"] = item.info_url
            data["preview_url"] = item.preview_url
            data["thumbnail_url"] = item.thumbnail_url

        elif isinstance(item, Revista):
            data["ISSN"] = item.ISSN
            data["editorial"] = item.editorial
            data["lloc"] = item.lloc
            data["pais"] = str(item.pais) if item.pais else None
            data["llengua"] = str(item.llengua) if item.llengua else None
            data["numero"] = item.numero
            data["volums"] = item.volums
            data["pagines"] = item.pagines

        elif isinstance(item, CD):
            data["discografica"] = item.discografica
            data["estil"] = item.estil
            data["duracio"] = item.duracio

        elif isinstance(item, DVD):
            data["productora"] = item.productora
            data["duracio"] = item.duracio

        elif isinstance(item, BR):
            data["productora"] = item.productora
            data["duracio"] = item.duracio

        elif isinstance(item, Dispositiu):
            data["marca"] = item.marca
            data["model"] = item.model

        # Add Exemplars to the response data
        data["exemplars"] = [
            {
                "id": ex.id,
                "registre": ex.registre,
                "exclos_prestec": ex.exclos_prestec,
                "baixa": ex.baixa,
                "centre": {
                    "nom": ex.centre.nom if ex.centre else None
                }
            }
            for ex in exemplars
        ]

        # Return the data directly (assuming the response handler knows how to return it as JSON)
        return data

    except model_class.DoesNotExist:
        raise HttpError(404, f"{model_type} with id {item_id} not found")


@api.post("/llibres/")
def post_llibres(request, payload: LlibreIn):
    llibre = Llibre.objects.create(**payload.dict())
    return {
        "id": llibre.id,
        "titol": llibre.titol
    }

@api.get("/exemplars", response=List[ExemplarOut])
@api.get("/exemplars/", response=List[ExemplarOut])
def get_exemplars(request):
    # carreguem objectes amb els proxy models relacionats exactes
    exemplars = Exemplar.objects.select_related(
        "cataleg__llibre",
        "cataleg__revista",
        "cataleg__cd",
        "cataleg__dvd",
        "cataleg__br",
        "cataleg__dispositiu",
    ).all()
    result = []

    for exemplar in exemplars:
        cataleg_instance = exemplar.cataleg

        # Determinar el tipus de l'objecte Cataleg
        if hasattr(cataleg_instance, "llibre"):
            cataleg_schema = LlibreOut.from_orm(cataleg_instance.llibre)
            tipus = "llibre"
        #elif hasattr(cataleg_instance, "dispositiu"):
        #    cataleg_schema = LlibreOut.from_orm(cataleg_instance.dispositiu)
        # TODO: afegir altres esquemes
        else:
            cataleg_schema = CatalegOut.from_orm(cataleg_instance)
            tipus = "indefinit"

        # Afegir l'Exemplar amb el Cataleg serialitzat
        result.append(
            ExemplarOut(
                id=exemplar.id,
                registre=exemplar.registre,
                exclos_prestec=exemplar.exclos_prestec,
                baixa=exemplar.baixa,
                cataleg=cataleg_schema,
                tipus=tipus,
            )
        )

    return result

@api.post("/prestecs/")
def crear_prestec(request):
    data = request.json
    usuari_id = data.get("usuari_id")
    exemplar_id = data.get("exemplar_id")
    anotacions = data.get("anotacions", "")

    if not usuari_id or not exemplar_id:
        raise HttpError(400, "Falten dades obligatòries")

    try:
        usuari = Usuari.objects.get(id=usuari_id)
        exemplar = Exemplar.objects.get(id=exemplar_id)
    except Usuari.DoesNotExist:
        raise HttpError(404, "Usuari no trobat")
    except Exemplar.DoesNotExist:
        raise HttpError(404, "Exemplar no trobat")

    prestec = Prestec.objects.create(
        usuari=usuari,
        exemplar=exemplar,
        anotacions=anotacions,
        data_prestec=date.today()
    )

    return {
        "id": prestec.id,
        "usuari": f"{usuari.first_name} {usuari.last_name}",
        "exemplar": str(exemplar),
        "data_prestec": prestec.data_prestec,
        "anotacions": prestec.anotacions,
    }

class UsuariUpdateOut(Schema):
    username: str
    email: str
    telefon: Optional[str]
    imatge: Optional[str]
    
class ProfileUpdatePayload(Schema):
    email: str 
    telefon: str = None # Ensure names match frontend 'name' attributes


def is_valid_email(email: str) -> bool:
    """Validate email format."""
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email) is not None

@api.post("/update-profile/", auth=AuthBearer())
def update_profile(request: HttpRequest,                  # Access request for auth user
    payload: ProfileUpdatePayload = Form(...), # Use Form(...) to get form fields
    avatar: Optional[UploadedFile] = File(None) # Use File(...) to get the uploaded file, make it optional
):
    user = request.auth  # Get authenticated user from token

    if not user:
        return api.create_response(request, {"details": "User not authenticated."}, status=401)

    errors = {}
    updated = False # Flag to check if any changes were made

    if payload.email:
        if not is_valid_email(payload.email):
            errors["email"] = "Email no té un format válid."
        elif payload.email != user.email:
            user.email = payload.email
            updated = True

    if payload.telefon:
        if len(payload.telefon) != 9 or not payload.telefon.isdigit():
            errors["telefon"] = "El teléfon ha de tenir 9 dígits."
        elif payload.telefon != user.telefon:
            user.telefon = payload.telefon
            updated = True

    if avatar:
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp']
        if avatar.content_type not in allowed_types:
            errors["avatar"] = "Format de imatge invàlid. Només poden ser JPG, JPEG, PNG i WEBP."
        else:
            user.imatge = avatar
            updated = True

    if errors:
        return api.create_response(request, {"formErrors": errors}, status=400)

    if updated:
        try:
            user.save()
            return api.create_response(request, {"type": "success_modify", "userData": UsuariUpdateOut.from_orm(user)}, status=200)
        except Exception as e:
            print(e)
            return api.create_response(request, {"details": f"Error al intentar actualitzar el perfil. Torna a intentar-ho més tard"}, status=500)

    return api.create_response(request, {"type": "no_change", "detail": "No changes made."}, status=200)


@api.post("/importUsersFromCsv/")
def import_users(request, file: UploadedFile = File(...)):
    # Verifiquem que hi hagi un fitxer i que sigui CSV
    if not file:
        return Response({"error": "No s'ha proporcionat cap fitxer."}, status=400)
    if not file.name.endswith('.csv'):
        return Response({"error": "El fitxer ha de ser en format CSV."}, status=400)

    try:
        data_set = file.read().decode("UTF-8")
    except Exception as e:
        return Response({"error": f"Error en llegir el fitxer: {str(e)}"}, status=400)

    io_string = io.StringIO(data_set)
    reader = csv.DictReader(io_string)

    # Validem que les columnes siguin correctes
    required_fields = {"nom", "cognom1", "cognom2", "email", "telefon", "centre", "grup"}
    if not required_fields.issubset(set(reader.fieldnames or [])):
        return Response({
            "error": f"El fitxer CSV ha de contenir les següents columnes: {', '.join(required_fields)}"
        }, status=400)

    imported_count = 0
    resultsMessage = []
    resultsStatus = []

    for index, row in enumerate(reader, start=1):
        # Agafem les dades crues
        nom_raw = row.get("nom")
        cognom1_raw = row.get("cognom1")
        cognom2_raw = row.get("cognom2")
        email_raw = row.get("email")
        telefon_raw = row.get("telefon")
        centre_val_raw = row.get("centre")
        grup_val_raw = row.get("grup")

        # Comprovem que cap sigui None o buit
        if not all([nom_raw, cognom1_raw, cognom2_raw, email_raw, telefon_raw, centre_val_raw, grup_val_raw]):
            resultsMessage.append(
                f"Fila {index}: Tots els camps són obligatoris (nom, cognom1, cognom2, email, telefon, centre, grup)."
            )
            resultsStatus.append("error")
            continue

        # Netegem els valors
        nom = nom_raw.strip()
        cognom1 = cognom1_raw.strip()
        cognom2 = cognom2_raw.strip()
        email = email_raw.strip()
        telefon = telefon_raw.strip()
        centre_val = centre_val_raw.strip()
        grup_val = grup_val_raw.strip()

        last_name = f"{cognom1} {cognom2}"

        try:
            centre_obj = Centre.objects.get(nom=centre_val)
        except Centre.DoesNotExist:
            resultsMessage.append(f"Fila {index}: Centre amb ID '{centre_val}' no trobat.")
            resultsStatus.append("error")
            continue

        try:
            cicle_obj = Cicle.objects.get(nom=grup_val)
        except Cicle.DoesNotExist:
            resultsMessage.append(f"Fila {index}: Cicle (grup) amb ID '{grup_val}' no trobat.")
            resultsStatus.append("error")
            continue

        username = email.split('@')[0]

        user, created = Usuari.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "first_name": nom,
                "last_name": last_name,
                "telefon": telefon,
                "centre": centre_obj,
                "cicle": cicle_obj,
            }
        )

        if not created:
            resultsMessage.append(f"Fila {index}: L'usuari amb l'email '{email}' ja existeix.")
            resultsStatus.append("warning")
            continue
        else:
            resultsMessage.append(f"Fila {index}: Usuari '{username}' creat correctament.")
            resultsStatus.append("success")
        imported_count += 1
        
    error_count = resultsStatus.count("error")
    warning_count = resultsStatus.count("warning")
    summary = {
        "imported": imported_count,
        "errorCount": error_count,
        "warningCount": warning_count,
        "resultsMessage": resultsMessage,
        "resultsStatus": resultsStatus,
        "message": "success"
    }

    return summary
