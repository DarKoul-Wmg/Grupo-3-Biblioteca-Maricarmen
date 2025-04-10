from django.contrib.auth import authenticate
from ninja import NinjaAPI, Schema, File, Form
from ninja.files import UploadedFile
from ninja.errors import HttpError
from ninja.responses import Response
from ninja.security import HttpBasicAuth, HttpBearer
from django.http import HttpRequest
from .models import *
from typing import List, Optional, Union, Literal
import re  # For email validation
import io  # For handling in-memory file operations
import csv  # For CSV file handling

import secrets

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
        except Usuari.DoesNotExist:
            return None

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

@api.get("/llibres/search", response=List[LlibreOut])
def search_llibres(request, text: str):
    llibres = Llibre.objects.filter(titol__icontains=text) | Llibre.objects.filter(autor__icontains=text)
    llibres = llibres.distinct()
    return llibres

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


@api.post("/import-users/")
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
    imported_error_count = 0
    errors = []
    warnings = []

    for index, row in enumerate(reader, start=1):
        error = False
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
            error = True
        else:
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
                print(f"Centre '{centre_val}' no trobat (línia {index})")
                error = True

            try:
                cicle_obj = Cicle.objects.get(nom=grup_val)
            except Cicle.DoesNotExist:
                print(f"Cicle '{grup_val}' no trobat (línia {index})")
                error = True

            if not error:
                username = email
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
                    warnings.append(index)
                    continue
        
        if error:
            errors.append(index)
            imported_error_count += 1
            continue
            
        imported_count += 1
        
    print(errors)
    summary = {
        "ok": f"Se han importat {imported_count} entrades correctament",
        "error": f"Han fallat {imported_error_count} registres, revisa las lineas {', '.join(map(str, errors))}",
        "warning": f"Les entrades {', '.join(map(str, warnings))} ja existeixen a la base de dades"
    }

    return summary
