import random
import unicodedata
from faker import Faker
from datetime import timedelta
from django.utils.timezone import now
from django.core.management.base import BaseCommand


from biblioteca.models import (
    Categoria, Pais, Llengua, Cataleg, Llibre, Revista, CD, DVD, BR, Dispositiu,
    Exemplar, Centre, Cicle, Usuari, Reserva, Prestec
)

# ========== CONFIG ==========

NUM_LIBROS = 500
NUM_AUTORES = 75
MAX_EJEMPLARES_POR_LIBRO = 10
NUM_USUARIS = 50
NUM_CENTRES = 3
NUM_CICLES = 9

NUM_PAISOS = 5
NUM_CATEGORIES = 10
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
    for i in range(NUM_CENTRES):
        fake = get_faker()
        nom_centre = f"IES {fake.first_name()} {fake.last_name()}"
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

def crear_cicles():
    cicles = []
    for i in range(NUM_CICLES):
        fake = get_faker()
        nom = f"{fake.word().capitalize()} {fake.word().capitalize()}"
        cicle = Cicle.objects.create(nom=nom)
        cicles.append(cicle)
    return cicles



# Elimina los acentos de un texto
def quitar_acentos(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def crear_usuaris(centres, cicles):
    usuaris = []
    for _ in range(NUM_USUARIS):
        fake = get_faker()
        centre = random.choice(centres)
        cicle = random.choice(cicles)

        # primeras dos iniciales + apellido
        nom_propi = fake.first_name()
        cognom = fake.last_name()
        username_base = f"{nom_propi[0].lower()}{nom_propi[1].lower()}{cognom.lower()}"
        username = quitar_acentos(username_base)

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
            cicle=cicle,  
            telefon=fake.random_number(digits=9)
        )
        usuaris.append(user)
    return usuaris

def crear_autors(num_autors):
    return [get_faker().name() for _ in range(num_autors)]

def crear_llibres(autors, llengues, paisos, categories):
    llibres = []
    llibres_per_autor = [[] for _ in autors]

    titols_generats = set()

    for i in range(NUM_LIBROS):
        fake = get_faker()

        # Evitar títulos duplicados
        titol = fake.sentence(nb_words=4)
        while titol in titols_generats:
            titol = fake.sentence(nb_words=4)
        titols_generats.add(titol)

        titol_original = fake.sentence(nb_words=5)

        autor_idx = i % len(autors)
        autor = autors[autor_idx]

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
            pagines=random.randint(100, 500),
            resum=fake.paragraph(),
            anotacions=fake.sentence(),
            ISBN=fake.isbn13(),
            data_edicio=fake.date_between(start_date='-10y', end_date='today'),
        )
        llibre.tags.set(random.sample(categories, k=random.randint(1, 3)))
        llibres.append(llibre)
        llibres_per_autor[autor_idx].append(llibre)
    return llibres

def crear_exemplars(llibres, centres):
    exemplars = []
    for llibre in llibres:
        for _ in range(random.randint(1, MAX_EJEMPLARES_POR_LIBRO)):
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
        data_prestec = now() - timedelta(days=random.randint(0, 30))
        Prestec.objects.create(
            usuari=user,
            exemplar=exemplar,
            data_prestec=data_prestec,
            data_retorn=(data_prestec + timedelta(days=random.randint(1, 15))) if random.random() < 0.7 else None,
            anotacions=get_faker().sentence()
        )

def crear_altres_catalegs(llengues, paisos, categories):
    fake = get_faker()
    for _ in range(NUM_REVISTES):
        Revista.objects.create(
            titol=fake.sentence(),
            autor=fake.name(),
            llengua=random.choice(llengues),
            pais=random.choice(paisos),
            ISSN=fake.isbn13(),
            editorial=fake.company(),
            data_edicio=fake.date_this_century(),
        )
    for _ in range(NUM_CDS):
        CD.objects.create(
            titol=fake.sentence(),
            autor=fake.name(),
            discografica=fake.company(),
            estil=fake.word(),
            duracio=fake.time(),
        )
    for _ in range(NUM_DVDS):
        DVD.objects.create(
            titol=fake.sentence(),
            autor=fake.name(),
            productora=fake.company(),
            duracio=fake.time(),
        )
    for _ in range(NUM_BRS):
        BR.objects.create(
            titol=fake.sentence(),
            autor=fake.name(),
            productora=fake.company(),
            duracio=fake.time(),
        )
    for _ in range(NUM_DISPOSITIUS):
        Dispositiu.objects.create(
            titol=fake.word(),
            autor=None,
            marca=fake.company(),
            model=fake.word()
        )

# ========== COMANDO DE DJANGO ==========

class Command(BaseCommand):
    help = 'Crea datos de prueba para la base de datos'

    def handle(self, *args, **kwargs):
        print("Creando datos de prueba...")
        Reserva.objects.all().delete()
        Prestec.objects.all().delete()
        Exemplar.objects.all().delete()
        Cataleg.objects.all().delete()
        Cicle.objects.all().delete()
        Centre.objects.all().delete()
        Usuari.objects.exclude(is_superuser=True).delete()
        print("Datos anteriores borrados con exito")

        centres = crear_centres()
        print("Centros generados")
        llengues, paisos = crear_llengues_i_paisos()
        print("Lenguas y paises generados")

        categories = crear_categories()
        print("Categorias generadas")

        cicles = crear_cicles()
        print("Ciclos generados")

        usuaris = crear_usuaris(centres, cicles)
        print("Usuarios comunes generados")

        autors = crear_autors(NUM_AUTORES)
        print("Autores")

        llibres = crear_llibres(autors, llengues, paisos, categories)
        print("Libros generados")

        exemplars = crear_exemplars(llibres, centres)
        print("Ejemplares generados")

        crear_reserves_i_presteus(usuaris, exemplars)
        print("Reservas y prestamos generados")

        crear_altres_catalegs(llengues, paisos, categories)
        print("Otros catalogos generados")


        self.stdout.write(self.style.SUCCESS("✅ Datos creados correctamente."))
