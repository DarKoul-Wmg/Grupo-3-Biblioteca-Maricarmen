import random
import unicodedata
from faker import Faker
from datetime import timedelta
from django.utils.timezone import now
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group  # Importa el modelo Group



from biblioteca.models import (
    Categoria, Pais, Llengua, Cataleg, Llibre, Revista, CD, DVD, BR, Dispositiu,
    Exemplar, Centre, Grup, Usuari, Reserva, Prestec
)

# ========== CONFIG ==========

NUM_LLIBRES = 600
NUM_AUTORS = 100
MAX_EJEMPLARS_PER_LLIBRE = 10
NUM_USUARIS = 100
NUM_CENTRES = 7
NUM_GRUPS = 15

NUM_PAISOS = 5
NUM_CATEGORIES = 20
NUM_RESERVES = 100
NUM_PRESTECS = 150

LLENGUES_DISPONIBLES = ['Català', 'Español', 'English']
# ========== CREADO POR SI ACASO ======= 
NUM_REVISTES = 30
NUM_CDS = 20
NUM_DVDS = 15
NUM_BRS = 10
NUM_DISPOSITIUS = 10


# ========== Faker Multilang ==========
IDIOMES = ['es_ES', 'en_US']
fakers = [Faker(locale) for locale in IDIOMES]

def get_faker():
    return random.choice(fakers)

# ========== FUNCIONES ==========

def crear_centres():
    centres = []
    for i in range(NUM_CENTRES - 1):
        fake = get_faker()
        nom_centre = f"{fake.first_name()} {fake.last_name()}"
        centre = Centre.objects.create(nom=nom_centre)
        centres.append(centre)

    centres.append(Centre.objects.create(nom=f"IES Esteve Terradas"))

    return centres

def crear_llengues_i_paisos():
    llengues = []
    for lang in LLENGUES_DISPONIBLES:
        llengues.append(Llengua.objects.create(nom=lang))

    paisos = []
    for _ in range(NUM_PAISOS):
        paisos.append(Pais.objects.create(nom=get_faker().country()))

    return llengues, paisos

def crear_categories():
    categories = []
    for _ in range(NUM_CATEGORIES):
        categories.append(Categoria.objects.create(nom=get_faker().word()))
    return categories

def crear_grups():
    grups = []
    for i in range(NUM_GRUPS):
        fake = get_faker()
        nom = f"{fake.word().capitalize()} {fake.word().capitalize()}"
        grup = Grup.objects.create(nom=nom)
        grups.append(grup)
    return grups



# Elimina los acentos de un texto
def quitar_acentos(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def crear_usuaris(centres, grups):
    #obtiene el grupo del admin panel para asingar a todos los usuarios por defecto al grupo Usuaris
    grup_usuaris, created = Group.objects.get_or_create(name="Usuari")
    if created:
        print("Grup 'Usuari' s'ha creat")
    else:
        print("Grup 'Usuaris' ja existeix.")

    usuaris = []
    for _ in range(NUM_USUARIS):
        fake = get_faker()
        centre = random.choice(centres)
        grup = random.choice(grups)

        # primeras dos iniciales + apellido
        nom_propi = fake.first_name()
        cognom = fake.last_name()
        username_base = f"{nom_propi[0].lower()}{nom_propi[1].lower()}{cognom.lower()}"
        username = quitar_acentos(username_base)

        # Asegura que el username es único
        contador = 1
        while Usuari.objects.filter(username=username).exists():
            username = f"{username_base}{contador}"
            contador += 1

        # email: primeraletranombre + apellido + XXXX + @ieti.com
        random_digits = ''.join(random.choices('0123456789', k=4))
        email_base = f"{nom_propi[0].lower()}{cognom.lower()}{random_digits}"
        email = f"{quitar_acentos(email_base)}@ieti.com"

        user = Usuari.objects.create_user(
            username=username,
            password='12345678',
            email=email,
            first_name=nom_propi,
            last_name=cognom,
            centre=centre,
            grup=grup,  
            telefon=fake.random_number(digits=9)
        )

        #asignar al usuario al grupo correspondiente:
        user.groups.add(grup_usuaris)

        usuaris.append(user)
    return usuaris

def crear_autors(num_autors):
    return [get_faker().name() for _ in range(num_autors)]

def crear_llibres(autors, llengues, paisos, categories):
    llibres = []
    llibres_per_autor = [[] for _ in autors]

    titols_generats = set()

    for i in range(NUM_LLIBRES):
        fake = get_faker()

        # Evitar títulos duplicados
        titol = fake.text(max_nb_chars=40).strip('.')
        while titol in titols_generats:
            titol = fake.text(max_nb_chars=40).strip('.')
        titols_generats.add(titol)

        titol_original = fake.text(max_nb_chars=40).strip('.')

        autor_idx = i % len(autors)
        autor = autors[autor_idx]

        cdu = f"{random.randint(10, 999)}.{random.randint(1, 99)}"  # Ejemplo de formato CDU

        llibre = Llibre.objects.create(
            titol=titol,
            titol_original=titol_original,
            autor=autor,
            editorial=fake.company(),
            lloc=fake.city(),
            pais=random.choice(paisos),
            llengua=random.choice(llengues),
            numero=random.randint(1, 10),
            volums=random.randint(1, 3),
            pagines=random.randint(40, 500),
            resum=fake.paragraph(),
            anotacions=fake.sentence(),
            ISBN=fake.isbn13().replace("-", ""),
            data_edicio=fake.date_between(start_date='-10y', end_date='today'),
            CDU=cdu,
            colleccio=fake.word().capitalize(),  # Añadir colleccio
            mides=f"{random.randint(10, 30)}x{random.randint(10, 30)} cm",  # Añadir mides
            signatura=f"SIGN-{random.randint(1000, 9999)}",  # Añadir signatura
        )
        llibre.tags.set(random.sample(categories, k=random.randint(1, 3)))
        llibres.append(llibre)
        llibres_per_autor[autor_idx].append(llibre)
    return llibres

def crear_exemplars(llibres, centres):
    exemplars = []
    for llibre in llibres:
        for _ in range(random.randint(1, MAX_EJEMPLARS_PER_LLIBRE)):
            exemplar = Exemplar.objects.create(
                cataleg=llibre,
                registre=f"{get_faker().ean(length=13)}",
                centre=random.choice(centres),
                exclos_prestec=random.choice([True, False]),
                baixa=False,
            )
            exemplars.append(exemplar)
    return exemplars

def crear_reserves_i_presteus(usuaris, exemplars):
    for _ in range(NUM_RESERVES):
        user = random.choice(usuaris)
        exemplar = random.choice(exemplars)
        Reserva.objects.create(
            usuari=user,
            exemplar=exemplar
        )

    for _ in range(NUM_PRESTECS):
        user = random.choice(usuaris)
        exemplar = random.choice(exemplars)

        # Seleccionar una fecha de préstamo entre hoy y 30 días antes
        data_prestec = now() - timedelta(days=random.randint(0, 30))

        # La fecha de retorno será exactamente 7 días después de la fecha de préstamo
        data_retorn = data_prestec + timedelta(days=7)
        # print(f"Data préstec: {data_prestec}, Data retorn: {data_retorn}")  # Depuración

        # Crear el préstamo
        Prestec.objects.create(
            usuari=user,
            exemplar=exemplar,
            data_prestec=data_prestec,
            data_retorn=data_retorn,
            anotacions=get_faker().sentence()
        )

def crear_altres_catalegs(llengues, paisos, categories, centres):
    fake = get_faker()
    revistes, cds, dvds, brs, dispositius = [], [], [], [], []

    for _ in range(NUM_REVISTES):
        revista = Revista.objects.create(
            titol=fake.text(max_nb_chars=40).strip('.'),
            titol_original=fake.text(max_nb_chars=40).strip('.'),
            autor=fake.name(),
            llengua=random.choice(llengues),
            pais=random.choice(paisos),
            ISSN=fake.isbn13().replace("-", ""),
            editorial=fake.company(),
            lloc=fake.city(),
            numero=random.randint(1, 100),
            volums=random.randint(1, 10),
            pagines=random.randint(20, 200),
            data_edicio=fake.date_this_century(),
            resum=fake.paragraph(),
            anotacions=fake.sentence(),
            CDU=f"{random.randint(10, 999)}.{random.randint(1, 99)}",
            signatura=f"SIGN-{random.randint(1000, 9999)}",
            mides=f"{random.randint(10, 30)}x{random.randint(10, 30)} cm",
        )
        revista.tags.set(random.sample(categories, k=random.randint(1, 3)))
        revistes.append(revista)

    for _ in range(NUM_CDS):
        cd = CD.objects.create(
            titol=fake.text(max_nb_chars=40).strip('.'),
            titol_original=fake.text(max_nb_chars=40).strip('.'),
            autor=fake.name(),
            discografica=fake.company(),
            estil=fake.word(),
            duracio=fake.time(),
            resum=fake.paragraph(),
            anotacions=fake.sentence(),
            CDU=f"{random.randint(10, 999)}.{random.randint(1, 99)}",
            signatura=f"SIGN-{random.randint(1000, 9999)}",
            mides=f"{random.randint(10, 30)}x{random.randint(10, 30)} cm",
        )
        cds.append(cd)

    for _ in range(NUM_DVDS):
        dvd = DVD.objects.create(
            titol=fake.text(max_nb_chars=40).strip('.'),
            titol_original=fake.text(max_nb_chars=40).strip('.'),
            autor=fake.name(),
            productora=fake.company(),
            duracio=fake.time(),
            resum=fake.paragraph(),
            anotacions=fake.sentence(),
            CDU=f"{random.randint(10, 999)}.{random.randint(1, 99)}",
            signatura=f"SIGN-{random.randint(1000, 9999)}",
            mides=f"{random.randint(10, 30)}x{random.randint(10, 30)} cm",
        )
        dvds.append(dvd)

    for _ in range(NUM_BRS):
        br = BR.objects.create(
            titol=fake.text(max_nb_chars=40).strip('.'),
            titol_original=fake.text(max_nb_chars=40).strip('.'),
            autor=fake.name(),
            productora=fake.company(),
            duracio=fake.time(),
            resum=fake.paragraph(),
            anotacions=fake.sentence(),
            CDU=f"{random.randint(10, 999)}.{random.randint(1, 99)}",
            signatura=f"SIGN-{random.randint(1000, 9999)}",
            mides=f"{random.randint(10, 30)}x{random.randint(10, 30)} cm",
        )
        brs.append(br)

    for _ in range(NUM_DISPOSITIUS):
        dispositiu = Dispositiu.objects.create(
            titol=fake.word(),
            titol_original=fake.word(),
            autor=None,
            marca=fake.company(),
            model=fake.word(),
            resum=fake.paragraph(),
            anotacions=fake.sentence(),
            CDU=f"{random.randint(10, 999)}.{random.randint(1, 99)}",
            mides=f"{random.randint(10, 30)}x{random.randint(10, 30)} cm",
        )
        dispositius.append(dispositiu)

    crear_exemplars_catalegs(revistes + cds + dvds + brs + dispositius, centres)

def crear_exemplars_catalegs(catalegs, centres):
    for cataleg in catalegs:
        for _ in range(random.randint(1, MAX_EJEMPLARS_PER_LLIBRE)):
            Exemplar.objects.create(
                cataleg=cataleg,
                registre=f"{get_faker().ean(length=13)}",
                centre=random.choice(centres),
                exclos_prestec=random.choice([True, False]),
                baixa=False,
            )

# ========== COMANDO DE DJANGO ==========

class Command(BaseCommand):
    help = 'Genera dades de prova per a la biblioteca'

    def handle(self, *args, **kwargs):
        print("Crea dades de prova...")
        Reserva.objects.all().delete()
        Prestec.objects.all().delete()
        Exemplar.objects.all().delete()
        Cataleg.objects.all().delete()
        Grup.objects.all().delete()
        Centre.objects.all().delete()
        Usuari.objects.exclude(is_superuser=True).delete()
        print("Dades anteriors esborrades")

        centres = crear_centres()
        print("Centres generats")
        llengues, paisos = crear_llengues_i_paisos()
        print("Llengües i països generats")

        categories = crear_categories()
        print("Categories generades")

        grups = crear_grups()
        print("Grups generats")

        usuaris = crear_usuaris(centres, grups)
        print("Usuaris generats")

        autors = crear_autors(NUM_AUTORS)
        print("Autors generats")

        llibres = crear_llibres(autors, llengues, paisos, categories)
        print("Llibres generats")

        exemplars = crear_exemplars(llibres, centres)
        print("Exemplars generats")

        crear_reserves_i_presteus(usuaris, exemplars)
        print("Reserves i presteus generats")

        crear_altres_catalegs(llengues, paisos, categories, centres)
        print("Altres catàlegs generats")


        self.stdout.write(self.style.SUCCESS("✅ Dades creades correctament."))
