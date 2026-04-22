# api/migrations/0002_preload_basic_data.py

from __future__ import annotations

from datetime import date
from typing import Any, Optional, TypedDict

from django.contrib.auth.hashers import make_password
from django.db import migrations, models, transaction
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


# ------------------------------------------------------
# Typed seed structures
# ------------------------------------------------------

class PetSeedData(TypedDict):
    name: str
    sex: str
    species: str
    breed: str
    birth_date: date
    photo_url: str | None
    body_description: str
    size_label: str
    last_weight: float


# ------------------------------------------------------
# Seed constants
# ------------------------------------------------------

CENTER_1_DATA = {
    "id": 1,
    "name": "Clínica Veterinaria San Rafael",
    "country_code": "CL",
    "clinic_code": "SR",
    "email": "contacto@sanrafael.cl",
    "address": "Av. Principal 1234, Santiago",
    "phone": "+56912345678",
}

CENTER_2_DATA = {
    "id": 2,
    "name": "Centro Veterinario Demo",
    "country_code": "CL",
    "clinic_code": "DEMO",
    "email": "demo@vetcenter.cl",
    "address": "Av. Secundaria 567, Santiago",
    "phone": "+56911111111",
}

COMMON_SETTINGS = {
    "city": "Santiago",
    "country": "Chile",
    "default_consultation_duration": 30,
    "allow_emergency_attention": True,
    "require_microchip_for_surgery": True,
    "require_microchip_for_hospitalization": False,
    "require_microchip_for_consultation": False,
    "auto_generate_history_code": True,
    "primary_color": "#3b82f6",
    "secondary_color": "#10b981",
    "send_vaccine_reminders": True,
    "send_followup_reminders": True,
}

GLOBAL_SPECIES_BREEDS = {
    "Canino": [
        "Labrador Retriever",
        "Golden Retriever",
        "Pastor Alemán",
        "Bulldog Francés",
        "Poodle",
        "Beagle",
        "Rottweiler",
        "Yorkshire Terrier",
        "Boxer",
        "Dachshund",
    ],
    "Felino": [
        "Siamés",
        "Persa",
        "Maine Coon",
        "Bengalí",
        "Ragdoll",
        "British Shorthair",
        "Sphynx",
        "Scottish Fold",
        "Abisinio",
        "Azul Ruso",
    ],
    "Ave": [
        "Cacatúa",
        "Periquito",
        "Canario",
        "Guacamayo",
        "Agapornis",
    ],
    "Conejo": [
        "Holland Lop",
        "Mini Rex",
        "Lionhead",
        "Dutch Rabbit",
        "Flemish Giant",
    ],
    "Reptil": [
        "Bearded Dragon",
        "Leopard Gecko",
        "Ball Python",
        "Corn Snake",
        "Green Iguana",
    ],
    "Roedor": [
        "Syrian Hamster",
        "Dwarf Hamster",
        "Guinea Pig",
        "Chinchilla",
        "Gerbil",
    ],
    "Hurón": [
        "Standard Ferret",
        "Albino Ferret",
        "Sable Ferret",
        "Black Sable Ferret",
        "Champagne Ferret",
    ],
    "Caballo": [
        "Arabian",
        "Thoroughbred",
        "Quarter Horse",
        "Appaloosa",
        "Friesian",
    ],
    "Bovino": [
        "Holstein",
        "Angus",
        "Hereford",
        "Brahman",
        "Simmental",
    ],
    "Caprino": [
        "Boer",
        "Nubian",
        "Alpine",
        "Saanen",
        "LaMancha",
    ],
}

FOCUSED_SPECIES_NAMES = [
    "Canino",
    "Felino",
    "Ave",
]

PETS_DATA: list[PetSeedData] = [
    {
        "name": "Rocky",
        "sex": "m",
        "species": "Canino",
        "breed": "Labrador Retriever",
        "birth_date": date(2020, 3, 15),
        "photo_url": "https://images.pexels.com/photos/2253275/pexels-photo-2253275.jpeg",
        "body_description": "Labrador Retriever dorado.",
        "size_label": "mediano",
        "last_weight": 30.5,
    },
    {
        "name": "Bella",
        "sex": "f",
        "species": "Felino",
        "breed": "Siamés",
        "birth_date": date(2021, 6, 5),
        "photo_url": "https://images.pexels.com/photos/45201/kitty-cat-kitten-pet-45201.jpeg",
        "body_description": "Gata siamés.",
        "size_label": "mediano",
        "last_weight": 4.2,
    },
    {
        "name": "Luna",
        "sex": "f",
        "species": "Felino",
        "breed": "Maine Coon",
        "birth_date": date(2022, 2, 20),
        "photo_url": "https://images.pexels.com/photos/20787/pexels-photo.jpg",
        "body_description": "Maine Coon.",
        "size_label": "mediano",
        "last_weight": 5.8,
    },
    {
        "name": "Max",
        "sex": "m",
        "species": "Canino",
        "breed": "Golden Retriever",
        "birth_date": date(2023, 1, 25),
        "photo_url": "https://images.pexels.com/photos/1108099/pexels-photo-1108099.jpeg",
        "body_description": "Golden Retriever.",
        "size_label": "mediano",
        "last_weight": 28.3,
    },
    {
        "name": "Coco",
        "sex": "f",
        "species": "Ave",
        "breed": "Cacatúa",
        "birth_date": date(2019, 8, 10),
        "photo_url": None,
        "body_description": "Cacatúa.",
        "size_label": "mediano",
        "last_weight": 0.45,
    },
    {
        "name": "Charlie",
        "sex": "m",
        "species": "Canino",
        "breed": "Bulldog Francés",
        "birth_date": date(2022, 7, 18),
        "photo_url": None,
        "body_description": "Bulldog francés.",
        "size_label": "mediano",
        "last_weight": 12.0,
    },
    {
        "name": "Milo",
        "sex": "m",
        "species": "Felino",
        "breed": "Azul Ruso",
        "birth_date": date(2020, 11, 12),
        "photo_url": None,
        "body_description": "Azul Ruso.",
        "size_label": "mediano",
        "last_weight": 4.0,
    },
    {
        "name": "Nina",
        "sex": "f",
        "species": "Canino",
        "breed": "Pastor Alemán",
        "birth_date": date(2021, 4, 7),
        "photo_url": "https://images.pexels.com/photos/4587996/pexels-photo-4587996.jpeg",
        "body_description": "Pastor alemán.",
        "size_label": "mediano",
        "last_weight": 32.0,
    },
    {
        "name": "Simba",
        "sex": "m",
        "species": "Felino",
        "breed": "Bengalí",
        "birth_date": date(2018, 9, 28),
        "photo_url": "https://images.pexels.com/photos/730896/pexels-photo-730896.jpeg",
        "body_description": "Bengalí.",
        "size_label": "mediano",
        "last_weight": 5.0,
    },
    {
        "name": "Toby",
        "sex": "m",
        "species": "Canino",
        "breed": "Beagle",
        "birth_date": date(2024, 2, 1),
        "photo_url": "https://images.pexels.com/photos/4587995/pexels-photo-4587995.jpeg",
        "body_description": "Beagle.",
        "size_label": "mediano",
        "last_weight": 10.2,
    },
]

SEEDED_PET_NAMES = [pet["name"] for pet in PETS_DATA]
SEEDED_SPECIES_NAMES = list(GLOBAL_SPECIES_BREEDS.keys())
SEEDED_CONTACT_EMAILS = [
    "catalina.lao@gmail.com",
    "nelly.silva@gmail.com",
    "patitas.feleles@gmail.com",
]


# ------------------------------------------------------
# Helpers
# ------------------------------------------------------

def get_attr(obj: Any, attr_name: str, default: Any = None) -> Any:
    return getattr(obj, attr_name, default)


def model_has_field(model: type[models.Model], field_name: str) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def choice_value(
    model: type[models.Model],
    field_name: str,
    label_or_value: Optional[str],
) -> Optional[str]:
    if not label_or_value:
        return None

    field = model._meta.get_field(field_name)
    choices = list(getattr(field, "choices", []) or [])

    for value, _label in choices:
        if label_or_value == value:
            return value

    needle = str(label_or_value).strip().lower()

    for value, label in choices:
        if str(label).strip().lower() == needle:
            return value
        if str(value).strip().lower() == needle:
            return value

    return None


def set_allowed_species_if_present(
    *,
    settings_obj: Any,
    global_species: list[Any],
    center_species: list[Any],
) -> None:
    if not model_has_field(type(settings_obj), "allowed_species"):
        return

    field = settings_obj._meta.get_field("allowed_species")
    remote_field = get_attr(field, "remote_field")
    remote_model = get_attr(remote_field, "model")
    remote_model_name = get_attr(remote_model, "__name__", "")

    allowed_species_manager = get_attr(settings_obj, "allowed_species")

    if remote_model_name == "Global_Species":
        allowed_species_manager.set(global_species)
        return

    if remote_model_name == "Species_In_Center":
        allowed_species_manager.set(center_species)
        return


def clear_allowed_species_if_present(settings_obj: Any) -> None:
    if not model_has_field(type(settings_obj), "allowed_species"):
        return

    get_attr(settings_obj, "allowed_species").clear()


def get_models(apps: StateApps) -> dict[str, Any]:
    return {
        "Veterinary_Center": apps.get_model("api", "Veterinary_Center"),
        "Veterinary_Center_Settings": apps.get_model("api", "Veterinary_Center_Settings"),
        "Vet_Center_Personnel": apps.get_model("api", "Vet_Center_Personnel"),
        "Contact": apps.get_model("api", "Contact"),
        "Global_Species": apps.get_model("api", "Global_Species"),
        "Global_Breed": apps.get_model("api", "Global_Breed"),
        "Species_In_Center": apps.get_model("api", "Species_In_Center"),
        "Breed_In_Center": apps.get_model("api", "Breed_In_Center"),
        "Pet": apps.get_model("api", "Pet"),
        "Pet_Contact": apps.get_model("api", "Pet_Contact"),
    }


# ------------------------------------------------------
# Seed steps
# ------------------------------------------------------

def seed_centers(loaded_models: dict[str, Any]) -> dict[str, Any]:
    Veterinary_Center = loaded_models["Veterinary_Center"]

    center_1, _ = Veterinary_Center.objects.update_or_create(
        id=CENTER_1_DATA["id"],
        defaults={
            "name": CENTER_1_DATA["name"],
            "country_code": CENTER_1_DATA["country_code"],
            "clinic_code": CENTER_1_DATA["clinic_code"],
            "email": CENTER_1_DATA["email"],
            "address": CENTER_1_DATA["address"],
            "phone": CENTER_1_DATA["phone"],
        },
    )

    center_2, _ = Veterinary_Center.objects.update_or_create(
        id=CENTER_2_DATA["id"],
        defaults={
            "name": CENTER_2_DATA["name"],
            "country_code": CENTER_2_DATA["country_code"],
            "clinic_code": CENTER_2_DATA["clinic_code"],
            "email": CENTER_2_DATA["email"],
            "address": CENTER_2_DATA["address"],
            "phone": CENTER_2_DATA["phone"],
        },
    )

    return {
        "center_1": center_1,
        "center_2": center_2,
    }


def seed_settings(
    loaded_models: dict[str, Any],
    centers: dict[str, Any],
) -> dict[str, Any]:
    Veterinary_Center_Settings = loaded_models["Veterinary_Center_Settings"]

    center_1 = centers["center_1"]
    center_2 = centers["center_2"]

    settings_1, _ = Veterinary_Center_Settings.objects.update_or_create(
        veterinary_center=center_1,
        defaults={
            "name": CENTER_1_DATA["name"],
            "phone": CENTER_1_DATA["phone"],
            "email": CENTER_1_DATA["email"],
            "address": CENTER_1_DATA["address"],
            "pet_history_code_prefix": CENTER_1_DATA["clinic_code"],
            **COMMON_SETTINGS,
        },
    )

    settings_2, _ = Veterinary_Center_Settings.objects.update_or_create(
        veterinary_center=center_2,
        defaults={
            "name": CENTER_2_DATA["name"],
            "phone": CENTER_2_DATA["phone"],
            "email": CENTER_2_DATA["email"],
            "address": CENTER_2_DATA["address"],
            "pet_history_code_prefix": CENTER_2_DATA["clinic_code"],
            **COMMON_SETTINGS,
        },
    )

    return {
        "settings_1": settings_1,
        "settings_2": settings_2,
    }


def seed_personnel(
    loaded_models: dict[str, Any],
    centers: dict[str, Any],
) -> dict[str, Any]:
    Vet_Center_Personnel = loaded_models["Vet_Center_Personnel"]

    pwd = make_password("Chile.17")

    vet_user, _ = Vet_Center_Personnel.objects.update_or_create(
        email="elsy.noguera@gmail.com",
        veterinary_center=centers["center_1"],
        defaults={
            "first_name": "Elsy",
            "last_name": "Noguera",
            "role": "vet",
            "cell_phone": "+5697573386349",
            "national_dni": "26445363-1",
            "country_code": "CL",
            "password_hash": pwd,
        },
    )

    return {
        "vet_user": vet_user,
    }


def seed_contacts(
    loaded_models: dict[str, Any],
    centers: dict[str, Any],
) -> dict[str, Any]:
    Contact = loaded_models["Contact"]
    center_1 = centers["center_1"]

    catalina, _ = Contact.objects.update_or_create(
        email="catalina.lao@gmail.com",
        veterinary_center=center_1,
        defaults={
            "first_name": "Catalina",
            "last_name": "Lao",
            "contact_type": "person",
            "country_code": "CL",
            "national_dni": "36409597-K",
        },
    )

    nelly, _ = Contact.objects.update_or_create(
        email="nelly.silva@gmail.com",
        veterinary_center=center_1,
        defaults={
            "first_name": "Nelly",
            "last_name": "Silva",
            "contact_type": "person",
            "country_code": "CL",
            "national_dni": "23281282-6",
            "cell_phone": "975703827",
            "address": "Santiago de Chile",
        },
    )

    institution, _ = Contact.objects.update_or_create(
        email="patitas.feleles@gmail.com",
        veterinary_center=center_1,
        defaults={
            "institution": "Patitas Felices",
            "contact_type": "institution",
            "country_code": "CL",
            "national_dni": "34318629-0",
        },
    )

    return {
        "catalina": catalina,
        "nelly": nelly,
        "institution": institution,
    }


def seed_global_species_and_breeds(
    loaded_models: dict[str, Any],
) -> dict[str, Any]:
    Global_Species = loaded_models["Global_Species"]
    Global_Breed = loaded_models["Global_Breed"]

    global_species_objs: dict[str, Any] = {}
    global_breed_objs: dict[tuple[str, str], Any] = {}

    for species_name, breed_names in GLOBAL_SPECIES_BREEDS.items():
        global_species_obj, _ = Global_Species.objects.update_or_create(
            name=species_name,
        )
        global_species_objs[species_name] = global_species_obj

        for breed_name in breed_names:
            global_breed_obj, _ = Global_Breed.objects.update_or_create(
                species=global_species_obj,
                name=breed_name,
            )
            global_breed_objs[(species_name, breed_name)] = global_breed_obj

    return {
        "global_species_objs": global_species_objs,
        "global_breed_objs": global_breed_objs,
    }


def seed_center_species_and_breeds(
    loaded_models: dict[str, Any],
    centers: dict[str, Any],
    settings: dict[str, Any],
    globals_data: dict[str, Any],
) -> dict[str, Any]:
    Species_In_Center = loaded_models["Species_In_Center"]
    Breed_In_Center = loaded_models["Breed_In_Center"]

    center_1 = centers["center_1"]
    settings_1 = settings["settings_1"]

    global_species_objs = globals_data["global_species_objs"]
    global_breed_objs = globals_data["global_breed_objs"]

    center_species_objs: dict[str, Any] = {}
    center_breed_objs: dict[tuple[str, str], Any] = {}

    for species_name in FOCUSED_SPECIES_NAMES:
        global_species_obj = global_species_objs[species_name]

        center_species_obj, _ = Species_In_Center.objects.update_or_create(
            veterinary_center=center_1,
            global_species=global_species_obj,
            defaults={
                "is_active": True,
            },
        )
        center_species_objs[species_name] = center_species_obj

        for breed_name in GLOBAL_SPECIES_BREEDS[species_name]:
            global_breed_obj = global_breed_objs[(species_name, breed_name)]

            center_breed_obj, _ = Breed_In_Center.objects.update_or_create(
                species_in_center=center_species_obj,
                global_breed=global_breed_obj,
                defaults={
                    "is_active": True,
                },
            )
            center_breed_objs[(species_name, breed_name)] = center_breed_obj

    set_allowed_species_if_present(
        settings_obj=settings_1,
        global_species=[
            global_species_objs[species_name]
            for species_name in FOCUSED_SPECIES_NAMES
        ],
        center_species=[
            center_species_objs[species_name]
            for species_name in FOCUSED_SPECIES_NAMES
        ],
    )

    return {
        "center_species_objs": center_species_objs,
        "center_breed_objs": center_breed_objs,
    }


def seed_pets(
    loaded_models: dict[str, Any],
    centers: dict[str, Any],
    personnel: dict[str, Any],
    contacts: dict[str, Any],
    center_catalog_data: dict[str, Any],
) -> None:
    Pet = loaded_models["Pet"]
    Pet_Contact = loaded_models["Pet_Contact"]

    center_1 = centers["center_1"]
    vet_user = personnel["vet_user"]

    catalina = contacts["catalina"]
    nelly = contacts["nelly"]
    institution = contacts["institution"]

    center_species_objs = center_catalog_data["center_species_objs"]
    center_breed_objs = center_catalog_data["center_breed_objs"]

    clinic_code = get_attr(center_1, "clinic_code")

    for index, pet_data in enumerate(PETS_DATA, start=1):
        species_name = pet_data["species"]
        breed_name = pet_data["breed"]

        species_obj = center_species_objs[species_name]
        breed_obj = center_breed_objs[(species_name, breed_name)]

        size_value = choice_value(Pet, "size", pet_data["size_label"])
        history_code = f"{clinic_code}-{index:04d}"

        pet, _ = Pet.objects.update_or_create(
            veterinary_center=center_1,
            history_code=history_code,
            defaults={
                "name": pet_data["name"],
                "sex": pet_data["sex"],
                "species": species_obj,
                "breed": breed_obj,
                "birth_date": pet_data["birth_date"],
                "photo_url": pet_data["photo_url"],
                "body_description": pet_data["body_description"],
                "size": size_value,
                "last_weight": pet_data["last_weight"],
                "last_attending_vet": vet_user,
                "sterilized": False,
                "has_microchip": False,
                "microchip_code": None,
            },
        )

        Pet_Contact.objects.get_or_create(
            pet=pet,
            contact=catalina,
            role="OWNER",
            defaults={"is_primary_contact": True},
        )

        if pet_data["name"] == "Bella":
            Pet_Contact.objects.get_or_create(
                pet=pet,
                contact=nelly,
                role="OWNER",
                defaults={"is_primary_contact": False},
            )

        responsible_contact = (
            institution
            if pet_data["name"] in ["Rocky", "Max", "Coco", "Milo", "Simba"]
            else catalina
        )

        Pet_Contact.objects.get_or_create(
            pet=pet,
            contact=responsible_contact,
            role="RESPONSIBLE",
            defaults={"is_primary_contact": True},
        )


# ------------------------------------------------------
# Forward migration
# ------------------------------------------------------

def load_initial_data(
    apps: StateApps,
    schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    del schema_editor

    loaded_models = get_models(apps)

    with transaction.atomic():
        centers = seed_centers(loaded_models)
        settings = seed_settings(loaded_models, centers)
        personnel = seed_personnel(loaded_models, centers)
        contacts = seed_contacts(loaded_models, centers)
        globals_data = seed_global_species_and_breeds(loaded_models)
        center_catalog_data = seed_center_species_and_breeds(
            loaded_models,
            centers,
            settings,
            globals_data,
        )
        seed_pets(
            loaded_models,
            centers,
            personnel,
            contacts,
            center_catalog_data,
        )


# ------------------------------------------------------
# Reverse migration
# ------------------------------------------------------

def unload_data(
    apps: StateApps,
    schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    del schema_editor

    loaded_models = get_models(apps)

    Veterinary_Center = loaded_models["Veterinary_Center"]
    Veterinary_Center_Settings = loaded_models["Veterinary_Center_Settings"]
    Vet_Center_Personnel = loaded_models["Vet_Center_Personnel"]
    Contact = loaded_models["Contact"]
    Global_Species = loaded_models["Global_Species"]
    Global_Breed = loaded_models["Global_Breed"]
    Species_In_Center = loaded_models["Species_In_Center"]
    Breed_In_Center = loaded_models["Breed_In_Center"]
    Pet = loaded_models["Pet"]
    Pet_Contact = loaded_models["Pet_Contact"]

    with transaction.atomic():
        if model_has_field(Veterinary_Center_Settings, "allowed_species"):
            for settings_obj in Veterinary_Center_Settings.objects.filter(
                veterinary_center__id__in=[CENTER_1_DATA["id"], CENTER_2_DATA["id"]],
            ):
                clear_allowed_species_if_present(settings_obj)

        Pet_Contact.objects.filter(
            pet__name__in=SEEDED_PET_NAMES,
        ).delete()

        Pet.objects.filter(
            name__in=SEEDED_PET_NAMES,
            veterinary_center__id=CENTER_1_DATA["id"],
        ).delete()

        Breed_In_Center.objects.filter(
            species__veterinary_center__id=CENTER_1_DATA["id"],
            species__global_species__name__in=FOCUSED_SPECIES_NAMES,
        ).delete()

        Species_In_Center.objects.filter(
            veterinary_center__id=CENTER_1_DATA["id"],
            global_species__name__in=FOCUSED_SPECIES_NAMES,
        ).delete()

        Global_Breed.objects.filter(
            species__name__in=SEEDED_SPECIES_NAMES,
        ).delete()

        Global_Species.objects.filter(
            name__in=SEEDED_SPECIES_NAMES,
        ).delete()

        Contact.objects.filter(
            email__in=SEEDED_CONTACT_EMAILS,
        ).delete()

        Vet_Center_Personnel.objects.filter(
            email="elsy.noguera@gmail.com",
        ).delete()

        Veterinary_Center.objects.filter(
            id__in=[CENTER_1_DATA["id"], CENTER_2_DATA["id"]],
        ).delete()


# ------------------------------------------------------
# Migration
# ------------------------------------------------------

class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(load_initial_data, reverse_code=unload_data),
    ]