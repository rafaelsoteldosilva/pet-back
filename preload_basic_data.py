# api/migrations/0002_preload_basic_data.py

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, TypedDict

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
    last_weight: int | float | str | Decimal
    
class StaffSeedData(TypedDict):
    email: str
    first_name: str
    last_name: str
    document_id: str
    country_code: str
    cell_phone: str
    password: str
    center_key: str
    role: str
    work_email: str
    work_phone: str
    job_title: str
    professional_license_number: str | None
    is_default_last_attending_vet: bool


# ------------------------------------------------------
# Pet contact role constants
# ------------------------------------------------------

ROLE_OWNER_GUARDIAN = "OWNER_GUARDIAN"
ROLE_CAREGIVER = "CAREGIVER"
ROLE_BILLING_RESPONSIBLE = "BILLING_RESPONSIBLE"
ROLE_REFERRING_VET = "REFERRING_VET"

ROLE_RESPONSIBLE_INSTITUTION = "RESPONSIBLE_INSTITUTION"
ROLE_REFERRING_INSTITUTION = "REFERRING_INSTITUTION"
ROLE_BREEDER = "BREEDER"
ROLE_SHELTER_OR_FOUNDATION = "SHELTER_OR_FOUNDATION"

CENTER_CONTACT_TYPE_PERSON = "PERSON"
CENTER_CONTACT_TYPE_INSTITUTION = "INSTITUTION"


NO_PET_CONTACT_PERMISSIONS = {
    "is_primary_contact": False,
    "is_emergency_contact": False,
    "can_authorize_treatment": False,
    "can_receive_medical_updates": False,
    "can_receive_billing": False,
    "can_pickup_pet": False,
}


PET_CONTACT_DEFAULT_PERMISSIONS_BY_ROLE = {
    ROLE_OWNER_GUARDIAN: {
        "is_primary_contact": False,
        "is_emergency_contact": False,
        "can_authorize_treatment": True,
        "can_receive_medical_updates": True,
        "can_receive_billing": True,
        "can_pickup_pet": True,
    },
    ROLE_CAREGIVER: {
        "is_primary_contact": False,
        "is_emergency_contact": False,
        "can_authorize_treatment": False,
        "can_receive_medical_updates": True,
        "can_receive_billing": False,
        "can_pickup_pet": True,
    },
    ROLE_BILLING_RESPONSIBLE: {
        "is_primary_contact": False,
        "is_emergency_contact": False,
        "can_authorize_treatment": False,
        "can_receive_medical_updates": False,
        "can_receive_billing": True,
        "can_pickup_pet": False,
    },
    ROLE_REFERRING_VET: {
        "is_primary_contact": False,
        "is_emergency_contact": False,
        "can_authorize_treatment": False,
        "can_receive_medical_updates": True,
        "can_receive_billing": False,
        "can_pickup_pet": False,
    },
    ROLE_RESPONSIBLE_INSTITUTION: {
        "is_primary_contact": False,
        "is_emergency_contact": False,
        "can_authorize_treatment": True,
        "can_receive_medical_updates": True,
        "can_receive_billing": True,
        "can_pickup_pet": False,
    },
    ROLE_REFERRING_INSTITUTION: {
        "is_primary_contact": False,
        "is_emergency_contact": False,
        "can_authorize_treatment": False,
        "can_receive_medical_updates": True,
        "can_receive_billing": False,
        "can_pickup_pet": False,
    },
    ROLE_BREEDER: {
        "is_primary_contact": False,
        "is_emergency_contact": False,
        "can_authorize_treatment": False,
        "can_receive_medical_updates": True,
        "can_receive_billing": False,
        "can_pickup_pet": False,
    },
    ROLE_SHELTER_OR_FOUNDATION: {
        "is_primary_contact": False,
        "is_emergency_contact": False,
        "can_authorize_treatment": False,
        "can_receive_medical_updates": True,
        "can_receive_billing": False,
        "can_pickup_pet": False,
    },
}


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


SEEDED_PET_NAMES = [
    pet["name"]
    for pet in PETS_DATA
]
SEEDED_CENTER_CONTACT_EMAILS = [
    "catalina.lao@gmail.com",
    "nelly.silva@gmail.com",
    "patitas.felices@gmail.com",
]

SEEDED_STAFF_EMAILS = [
    "nombre.apellido@gmail.com",
    "juan.perez@gmail.com",
]


STAFF_SEED_DATA: list[StaffSeedData] = [
    {
        "email": "nombre.apellido@gmail.com",
        "first_name": "Elsy",
        "last_name": "Noguera",
        "document_id": "26445363-1",
        "country_code": "CL",
        "cell_phone": "+5697573386349",
        "password": "Password.26",
        "center_key": "center_1",
        "role": "VETERINARIAN",
        "work_email": "nombre.apellido@gmail.com",
        "work_phone": "+5697573386349",
        "job_title": "Médica veterinaria",
        "professional_license_number": None,
        "is_default_last_attending_vet": True,
    },
    {
        "email": "juan.perez@gmail.com",
        "first_name": "Juan",
        "last_name": "Pérez",
        "document_id": "11111111-1",
        "country_code": "CL",
        "cell_phone": "+56922222222",
        "password": "Password.26",
        "center_key": "center_1",
        "role": "VETERINARIAN",
        "work_email": "juan.perez@gmail.com",
        "work_phone": "+56922222222",
        "job_title": "Médico veterinario",
        "professional_license_number": None,
        "is_default_last_attending_vet": False,
    },
]

# ------------------------------------------------------
# Helpers
# ------------------------------------------------------


def get_attr(
    obj: Any,
    attr_name: str,
    default: Any = None,
) -> Any:
    return getattr(obj, attr_name, default)


def model_has_field(
    model: type[models.Model],
    field_name: str,
) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def existing_model_defaults(
    model: type[models.Model],
    defaults: dict[str, Any],
) -> dict[str, Any]:
    return {
        field_name: value
        for field_name, value in defaults.items()
        if model_has_field(model, field_name)
    }


def choice_value(
    model: type[models.Model],
    field_name: str,
    label_or_value: str | None,
) -> str | None:
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
        "Veterinary_Center_Settings": apps.get_model(
            "api",
            "Veterinary_Center_Settings",
        ),
        "Center_Staff_Member": apps.get_model("api", "Center_Staff_Member"),
        "Center_Contact": apps.get_model("api", "Center_Contact"),
        "Global_Species": apps.get_model("api", "Global_Species"),
        "Global_Breed": apps.get_model("api", "Global_Breed"),
        "Species_In_Center": apps.get_model("api", "Species_In_Center"),
        "Breed_In_Center": apps.get_model("api", "Breed_In_Center"),
        "Pet": apps.get_model("api", "Pet"),
        "Pet_Contact_Link": apps.get_model("api", "Pet_Contact_Link"),
    }


def get_pet_contact_default_permissions_for_seed(role: str) -> dict[str, bool]:
    return dict(
        PET_CONTACT_DEFAULT_PERMISSIONS_BY_ROLE.get(
            role,
            NO_PET_CONTACT_PERMISSIONS,
        )
    )


def upsert_pet_contact_link_for_seed(
    *,
    Pet_Contact_Link: Any,
    pet: Any,
    center_contact: Any,
    role: str,
    specific_relationship: str = "",
    notes: str = "",
    permission_overrides: dict[str, bool] | None = None,
) -> Any:
    defaults: dict[str, Any] = get_pet_contact_default_permissions_for_seed(role)

    if permission_overrides:
        defaults.update(permission_overrides)

    if role == ROLE_BILLING_RESPONSIBLE:
        defaults["can_receive_billing"] = True

    defaults.update(
        {
            "specific_relationship": specific_relationship,
            "notes": notes,
            "is_active": True,
        }
    )

    pet_contact_link, _ = Pet_Contact_Link.objects.update_or_create(
        pet=pet,
        center_contact=center_contact,
        role=role,
        defaults=existing_model_defaults(
            Pet_Contact_Link,
            defaults,
        ),
    )

    return pet_contact_link


def normalize_seed_decimal(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


# ------------------------------------------------------
# Seed steps
# ------------------------------------------------------


def seed_centers(loaded_models: dict[str, Any]) -> dict[str, Any]:
    Veterinary_Center = loaded_models["Veterinary_Center"]

    center_1, _ = Veterinary_Center.objects.update_or_create(
        id=CENTER_1_DATA["id"],
        defaults=existing_model_defaults(
            Veterinary_Center,
            {
                "name": CENTER_1_DATA["name"],
                "country_code": CENTER_1_DATA["country_code"],
                "clinic_code": CENTER_1_DATA["clinic_code"],
                "email": CENTER_1_DATA["email"],
                "address": CENTER_1_DATA["address"],
                "phone": CENTER_1_DATA["phone"],
            },
        ),
    )

    center_2, _ = Veterinary_Center.objects.update_or_create(
        id=CENTER_2_DATA["id"],
        defaults=existing_model_defaults(
            Veterinary_Center,
            {
                "name": CENTER_2_DATA["name"],
                "country_code": CENTER_2_DATA["country_code"],
                "clinic_code": CENTER_2_DATA["clinic_code"],
                "email": CENTER_2_DATA["email"],
                "address": CENTER_2_DATA["address"],
                "phone": CENTER_2_DATA["phone"],
            },
        ),
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
        defaults=existing_model_defaults(
            Veterinary_Center_Settings,
            {
                "name": CENTER_1_DATA["name"],
                "phone": CENTER_1_DATA["phone"],
                "email": CENTER_1_DATA["email"],
                "address": CENTER_1_DATA["address"],
                "pet_history_code_prefix": CENTER_1_DATA["clinic_code"],
                **COMMON_SETTINGS,
            },
        ),
    )

    settings_2, _ = Veterinary_Center_Settings.objects.update_or_create(
        veterinary_center=center_2,
        defaults=existing_model_defaults(
            Veterinary_Center_Settings,
            {
                "name": CENTER_2_DATA["name"],
                "phone": CENTER_2_DATA["phone"],
                "email": CENTER_2_DATA["email"],
                "address": CENTER_2_DATA["address"],
                "pet_history_code_prefix": CENTER_2_DATA["clinic_code"],
                **COMMON_SETTINGS,
            },
        ),
    )

    return {
        "settings_1": settings_1,
        "settings_2": settings_2,
    }


def build_user_lookup(
    *,
    User: Any,
    email: str,
) -> dict[str, Any]:
    if model_has_field(User, "username"):
        return {
            "username": email,
        }

    if model_has_field(User, "email"):
        return {
            "email": email,
        }

    raise RuntimeError(
        "Cannot seed staff user because the user model has neither "
        "'username' nor 'email'."
    )


def seed_personnel(
    loaded_models: dict[str, Any],
    centers: dict[str, Any],
) -> dict[str, Any]:
    Center_Staff_Member = loaded_models["Center_Staff_Member"]

    User = Center_Staff_Member._meta.get_field("user").remote_field.model

    seeded_members: dict[str, Any] = {}

    for staff_data in STAFF_SEED_DATA:
        email = staff_data["email"]
        center_key = staff_data["center_key"]

        if model_has_field(User, "username"):
            user_lookup = {
                "username": email,
            }
        elif model_has_field(User, "email"):
            user_lookup = {
                "email": email,
            }
        else:
            raise RuntimeError(
                "Cannot seed staff user because the user model has neither "
                "'username' nor 'email'."
            )

        user_defaults = existing_model_defaults(
            User,
            {
                "email": email,
                "first_name": staff_data["first_name"],
                "last_name": staff_data["last_name"],
                "document_id": staff_data["document_id"],
                "country_code": staff_data["country_code"],
                "cell_phone": staff_data["cell_phone"],
                "password": make_password(staff_data["password"]),
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
            },
        )

        user, _ = User.objects.update_or_create(
            **user_lookup,
            defaults=user_defaults,
        )

        staff_member, _ = Center_Staff_Member.objects.update_or_create(
            user=user,
            veterinary_center=centers[center_key],
            defaults=existing_model_defaults(
                Center_Staff_Member,
                {
                    "role": staff_data["role"],
                    "work_email": staff_data["work_email"],
                    "work_phone": staff_data["work_phone"],
                    "job_title": staff_data["job_title"],
                    "professional_license_number": staff_data[
                        "professional_license_number"
                    ],
                    "is_active": True,
                },
            ),
        )

        seeded_members[email] = staff_member

        if staff_data["is_default_last_attending_vet"]:
            seeded_members["vet_staff_member"] = staff_member

    if "vet_staff_member" not in seeded_members:
        raise RuntimeError(
            "At least one seeded staff member must be marked as "
            "is_default_last_attending_vet=True."
        )

    return seeded_members

def seed_center_contacts(
    loaded_models: dict[str, Any],
    centers: dict[str, Any],
) -> dict[str, Any]:
    Center_Contact = loaded_models["Center_Contact"]
    center_1 = centers["center_1"]

    catalina, _ = Center_Contact.objects.update_or_create(
        email="catalina.lao@gmail.com",
        veterinary_center=center_1,
        defaults=existing_model_defaults(
            Center_Contact,
            {
                "center_contact_type": CENTER_CONTACT_TYPE_PERSON,
                "first_name": "Catalina",
                "last_name": "Lao",
                "country": "CL",
                "document_id": "36409597-K",
                "primary_phone": "975703828",
                "secondary_phone": "",
                "tertiary_phone": "",
                "address": "Santiago de Chile",
                "is_active": True,
            },
        ),
    )

    nelly, _ = Center_Contact.objects.update_or_create(
        email="nelly.silva@gmail.com",
        veterinary_center=center_1,
        defaults=existing_model_defaults(
            Center_Contact,
            {
                "center_contact_type": CENTER_CONTACT_TYPE_PERSON,
                "first_name": "Nelly",
                "last_name": "Silva",
                "country": "CL",
                "document_id": "23281282-6",
                "primary_phone": "975703827",
                "secondary_phone": "",
                "tertiary_phone": "",
                "address": "Santiago de Chile",
                "is_active": True,
            },
        ),
    )
    
    institution, _ = Center_Contact.objects.update_or_create(
        email="patitas.felices@gmail.com",
        veterinary_center=center_1,
        defaults=existing_model_defaults(
            Center_Contact,
            {
                "center_contact_type": CENTER_CONTACT_TYPE_INSTITUTION,
                "institution_name": "Patitas Felices",
                "country": "CL",
                "document_id": "34318629-0",
                "primary_phone": "9757038279",
                "secondary_phone": "",
                "tertiary_phone": "",
                "address": "Santiago de Chile",
                "is_active": True,
            },
        ),
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
            defaults=existing_model_defaults(
                Species_In_Center,
                {
                    "is_active": True,
                },
            ),
        )
        center_species_objs[species_name] = center_species_obj

        for breed_name in GLOBAL_SPECIES_BREEDS[species_name]:
            global_breed_obj = global_breed_objs[(species_name, breed_name)]

            center_breed_obj, _ = Breed_In_Center.objects.update_or_create(
                species_in_center=center_species_obj,
                global_breed=global_breed_obj,
                defaults=existing_model_defaults(
                    Breed_In_Center,
                    {
                        "is_active": True,
                    },
                ),
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
    center_contacts: dict[str, Any],
    center_catalog_data: dict[str, Any],
) -> None:
    Pet = loaded_models["Pet"]
    Pet_Contact_Link = loaded_models["Pet_Contact_Link"]

    center_1 = centers["center_1"]
    vet_staff_member = personnel["vet_staff_member"]

    catalina = center_contacts["catalina"]
    nelly = center_contacts["nelly"]
    institution = center_contacts["institution"]

    center_species_objs = center_catalog_data["center_species_objs"]
    center_breed_objs = center_catalog_data["center_breed_objs"]

    clinic_code = get_attr(center_1, "clinic_code")

    pets_with_institution_responsible = {
        "Rocky",
        "Max",
        "Coco",
        "Milo",
        "Simba",
    }

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
            defaults=existing_model_defaults(
                Pet,
                {
                    "name": pet_data["name"],
                    "sex": pet_data["sex"],
                    "species": species_obj,
                    "breed": breed_obj,
                    "birth_date": pet_data["birth_date"],
                    "photo_url": pet_data["photo_url"],
                    "body_description": pet_data["body_description"],
                    "size": size_value,
                    "last_weight": normalize_seed_decimal(
                        pet_data["last_weight"],
                    ),
                    "last_attending_vet": vet_staff_member,
                    "sterilized": False,
                    "has_pedigree": False,
                    "has_visual_identification": False,
                    "has_microchip": False,
                    "microchip_code": None,
                },
            ),
        )

        upsert_pet_contact_link_for_seed(
            Pet_Contact_Link=Pet_Contact_Link,
            pet=pet,
            center_contact=catalina,
            role=ROLE_OWNER_GUARDIAN,
            specific_relationship="Propietaria / tutora",
            permission_overrides={
                "is_primary_contact": True,
            },
        )

        if pet_data["name"] == "Bella":
            upsert_pet_contact_link_for_seed(
                Pet_Contact_Link=Pet_Contact_Link,
                pet=pet,
                center_contact=nelly,
                role=ROLE_CAREGIVER,
                specific_relationship="Cuidadora",
            )

        if pet_data["name"] in pets_with_institution_responsible:
            upsert_pet_contact_link_for_seed(
                Pet_Contact_Link=Pet_Contact_Link,
                pet=pet,
                center_contact=institution,
                role=ROLE_RESPONSIBLE_INSTITUTION,
                specific_relationship="Institución responsable",
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
        center_contacts = seed_center_contacts(
            loaded_models,
            centers,
        )
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
            center_contacts,
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

    Veterinary_Center_Settings = loaded_models["Veterinary_Center_Settings"]
    Center_Staff_Member = loaded_models["Center_Staff_Member"]
    User = Center_Staff_Member._meta.get_field("user").remote_field.model
    Center_Contact = loaded_models["Center_Contact"]
    Pet = loaded_models["Pet"]
    Pet_Contact_Link = loaded_models["Pet_Contact_Link"]

    with transaction.atomic():
        if model_has_field(Veterinary_Center_Settings, "allowed_species"):
            for settings_obj in Veterinary_Center_Settings.objects.filter(
                veterinary_center__id__in=[
                    CENTER_1_DATA["id"],
                    CENTER_2_DATA["id"],
                ],
            ):
                clear_allowed_species_if_present(settings_obj)

        Pet_Contact_Link.objects.filter(
            pet__name__in=SEEDED_PET_NAMES,
            pet__veterinary_center__id=CENTER_1_DATA["id"],
        ).delete()

        Pet.objects.filter(
            name__in=SEEDED_PET_NAMES,
            veterinary_center__id=CENTER_1_DATA["id"],
        ).delete()

        Center_Contact.objects.filter(
            email__in=SEEDED_CENTER_CONTACT_EMAILS,
            veterinary_center__id=CENTER_1_DATA["id"],
        ).delete()

        Center_Staff_Member.objects.filter(
            work_email__in=SEEDED_STAFF_EMAILS,
            veterinary_center__id=CENTER_1_DATA["id"],
        ).delete()

        if model_has_field(User, "email"):
            User.objects.filter(
                email__in=SEEDED_STAFF_EMAILS,
            ).delete()
        elif model_has_field(User, "username"):
            User.objects.filter(
                username__in=SEEDED_STAFF_EMAILS,
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