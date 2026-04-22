# preload_data.py

from django.db import migrations, transaction
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from datetime import date, timedelta
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.db import migrations
from django.db.migrations.state import StateApps
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

from api.shared.choices.choices import Choices_ConsultationStatus, Choices_DiseaseEventType, Choices_ProblemEventType

from typing import TYPE_CHECKING, Optional, Set, Type, cast
from django.db import migrations, models

if TYPE_CHECKING:
    from api.models import Pet_Problem_Case

#################################
# PARTE 01
#################################

def load_initial_data(
    apps: StateApps,
    schema_editor: BaseDatabaseSchemaEditor,
) -> None:
    
    def _model_field_names(Model: Type[models.Model]) -> Set[str]:
        return {f.name for f in Model._meta.get_fields() if hasattr(f, "attname")}

    # def _pick_valid_choice_value(
    #     field: models.Field[Any, Any],
    #     preferred_values: Iterable[str],
    # ) -> Optional[str]:

    #     allowed = {c[0] for c in (field.choices or [])}

    #     for v in preferred_values:
    #         if v in allowed:
    #             return v

    #     return next(iter(allowed), None)

    def create_consultation_safe(
        *,
        Consultation: Type[models.Model],
        pet: models.Model,
        veterinarian: models.Model,
        consultation_type: Optional[models.Model],
        veterinary_center: models.Model,
        weight: Optional[float],
        price: Optional[float],
        now: datetime,
        created_by: Optional[models.Model] = None,
    ) -> models.Model:
        field_names = _model_field_names(Consultation)

        payload = {}

        # comunes (los tuyos ya existen)
        if "pet" in field_names:
            payload["pet"] = pet

        # if "vet" in field_names:
        #     payload["vet"] = veterinarian
        # elif "veterinarian" in field_names:
        #     payload["veterinarian"] = veterinarian

        if "consultation_type" in field_names:
            payload["consultation_type"] = consultation_type

        if "veterinary_center" in field_names:
            payload["veterinary_center"] = veterinary_center

        if "weight" in field_names:
            payload["weight"] = weight

        if "price" in field_names:
            payload["price"] = price

        # timestamps típicos
        if "consulted_at" in field_names:
            payload["consulted_at"] = now

        # auditoría típica
        if created_by is not None:
            if "created_by" in field_names:
                payload["created_by"] = created_by
            elif "created_by_personnel" in field_names:
                payload["created_by_personnel"] = created_by

        # status (si existe)
        if "status" in field_names:

            status_field = Consultation._meta.get_field("status")

            if isinstance(status_field, models.Field):

                has_default = (
                    status_field.has_default()
                    or status_field.default is not None
                )

                if not has_default:
                    payload["status"] = Choices_ConsultationStatus.COMPLETED
                    
        payload["vet"] = veterinarian

        consultation, _ = Consultation.objects.get_or_create(
            pet=pet,
            veterinary_center=veterinary_center,
            consulted_at=payload.get("consulted_at"),
            vet=veterinarian,
            defaults=payload,
        )

        return consultation

    Veterinary_Center = apps.get_model("api", "Veterinary_Center")
    Vet_Center_Personnel = apps.get_model("api", "Vet_Center_Personnel")
    Personnel_Login_Session = apps.get_model("api", "Personnel_Login_Session")

    Contact = apps.get_model("api", "Contact")
    Species = apps.get_model("api", "Species")
    Breed = apps.get_model("api", "Breed")
    Pet = apps.get_model("api", "Pet")
    Consultation = apps.get_model("api", "Consultation")
    ConsultationType = apps.get_model("api", "Consultation_Type")
    Critical_Case = apps.get_model("api", "Critical_Case")
    Clinical_Focus_For_SOAP_Template = apps.get_model(
        "api",
        "Clinical_Focus_For_SOAP_Template",
    )

    now = timezone.now()

    with transaction.atomic():
        
#################################
# PARTE 02
#################################

        # ======================================================
        # 1) VETERINARY CENTER
        # ======================================================

        # ======================================================
        # 1) VETERINARY CENTERS
        # ======================================================

        # Crear center 1 si no existe
        center = Veterinary_Center.objects.filter(pk=1).first()

        if center is None:
            center = Veterinary_Center.objects.create(
                id=1,
                name="Clínica Veterinaria San Rafael",
                country_code="CL",
                email="contacto@sanrafael.cl",
                address="Av. Principal 1234, Santiago",
                phone="+56912345678",
            )
        else:
            # opcional: asegurar que tenga los valores correctos
            center.name = "Clínica Veterinaria San Rafael"
            center.country_code = "CL"
            center.email = "contacto@sanrafael.cl"
            center.address = "Av. Principal 1234, Santiago"
            center.phone = "+56912345678"
            center.save(update_fields=[
                "name",
                "country_code",
                "email",
                "address",
                "phone",
            ])

        # Crear center 2 si no existe (pero NO usarlo)
        if not Veterinary_Center.objects.filter(pk=2).exists():
            Veterinary_Center.objects.create(
                id=2,
                name="Centro Veterinario Demo",
                country_code="CL",
                email="demo@vetcenter.cl",
                address="Av. Secundaria 567, Santiago",
                phone="+56911111111",
            )

        # Garantía absoluta
        assert center.pk == 1, f"ERROR: preload_data está usando Veterinary_Center ID={center.pk}, debe ser 1"

        # ======================================================
        # 2) PERSONNEL
        # ======================================================
        pwd = make_password("Chile.17")

        super_user, _ = Vet_Center_Personnel.objects.get_or_create(
            first_name="Rafael",
            last_name="Soteldo",
            role="super",
            cell_phone="+56975703826",
            national_dni="26144985-4",
            email="rafael.soteldo@gmail.com",
            country_code="CL",
            password_hash=pwd,
            veterinary_center=center,
        )

        vet_user, _ = Vet_Center_Personnel.objects.get_or_create(
            first_name="Elsy",
            last_name="Noguera",
            role="vet",
            cell_phone="+5697573386349",
            national_dni="26445363-1",
            email="elsy.noguera@gmail.com",
            country_code="CL",
            password_hash=pwd,
            veterinary_center=center,
        )

        for p in [super_user, vet_user]:
            Personnel_Login_Session.objects.get_or_create(
                personnel=p,
                login_at=now - timedelta(hours=1),
            )

        # ======================================================
        # 3) CONTACTS
        # ======================================================
        contacts = [
            Contact.objects.get_or_create(
                first_name="Catalina",
                last_name="Lao",
                contact_type="person",
                country_code="CL",
                national_dni="36409597-K",
                email="catalina.lao@gmail.com",
                veterinary_center=center,
            )[0],
            Contact.objects.get_or_create(
                institution="Patitas Felices",
                country_code="CL",
                contact_type="institution",
                national_dni="34318629-0",
                email="patitas.feleles@gmail.com",
                veterinary_center=center,
            )[0],
        ]
        
        person_contacts = []
        institution_contacts = []

        for c in contacts:
            if c.institution:
                institution_contacts.append(c)
            else:
                person_contacts.append(c)

        # ======================================================
        # 4) SPECIES & BREEDS
        # ======================================================
        species_breeds = {
            "Canino": ["Labrador Retriever", "Beagle", "Golden Retriever", "Pastor Alemán", "Bulldog Francés"],
            "Felino": ["Siamés", "Persa", "Maine Coon", "Bengalí", "Azul Ruso"],
            "Ave": ["Periquito", "Cacatúa", "Canario"],
        }

        species_objs = {}
        breed_objs = {}

        for sname, breeds in species_breeds.items():
            s, _ = Species.objects.get_or_create(name=sname, veterinary_center=center)
            species_objs[sname] = s
            breed_objs[sname] = [
                Breed.objects.get_or_create(name=b, species=s)[0]
                for b in breeds
            ]


        # ======================================================
        # 5) PETS (NOMBRES Y PHOTO_URL INTACTOS)
        # ======================================================
        pets_data = [
            ("Rocky", "m", "Canino", "Labrador Retriever", date(2020, 3, 15),
             "https://images.pexels.com/photos/2253275/pexels-photo-2253275.jpeg?auto=compress&cs=tinysrgb&w=800",
             "Labrador Retriever dorado, muy activo y juguetón.", "mediano", 30.5),

            ("Bella", "f", "Felino", "Siamés", date(2021, 6, 5),
             "https://images.pexels.com/photos/45201/kitty-cat-kitten-pet-45201.jpeg?auto=compress&cs=tinysrgb&w=800",
             "Gata siamés de pelaje corto, muy curiosa y afectuosa.", "mediano", 4.2),

            ("Luna", "f", "Felino", "Maine Coon", date(2022, 2, 20),
             "https://images.pexels.com/photos/20787/pexels-photo.jpg?auto=compress&cs=tinysrgb&w=800",
             "Gata Maine Coon de pelo largo, tranquila pero juguetona.", "mediano", 5.8),

            ("Max", "m", "Canino", "Golden Retriever", date(2023, 1, 25),
             "https://images.pexels.com/photos/1108099/pexels-photo-1108099.jpeg?auto=compress&cs=tinysrgb&w=800",
             "Golden Retriever joven, muy sociable y activo.", "mediano", 28.3),

            ("Coco", "f", "Ave", "Cacatúa", date(2019, 8, 10),
             None,
             "Cacatúa blanca de cresta amarilla, muy vocal.", "mediano", 0.45),

            ("Charlie", "m", "Canino", "Bulldog Francés", date(2022, 7, 18),
             None,
             "Bulldog francés atigrado, muy cariñoso.", "mediano", 12.0),

            ("Milo", "m", "Felino", "Azul Ruso", date(2020, 11, 12),
             None,
             "Gato Azul Ruso reservado pero afectuoso.", "mediano", 4.0),

            ("Nina", "f", "Canino", "Pastor Alemán", date(2021, 4, 7),
             "https://images.pexels.com/photos/4587996/pexels-photo-4587996.jpeg?auto=compress&cs=tinysrgb&w=800",
             "Pastor alemán hembra, muy obediente.", "mediano", 32.0),

            ("Simba", "m", "Felino", "Bengalí", date(2018, 9, 28),
             "https://images.pexels.com/photos/730896/pexels-photo-730896.jpeg?auto=compress&cs=tinysrgb&w=800",
             "Gato bengalí moteado, muy activo.", "mediano", 5.0),

            ("Toby", "m", "Canino", "Beagle", date(2024, 2, 1),
             "https://images.pexels.com/photos/4587995/pexels-photo-4587995.jpeg?auto=compress&cs=tinysrgb&w=800",
             "Beagle joven e inquieto.", "mediano", 10.2),
        ]

        pets = []

        for idx, (name, sex, species_name, breed_name, dob, photo, body_desc, size, last_weight) in enumerate(pets_data):

            species = species_objs[species_name]
            breed = next(b for b in breed_objs[species_name] if b.name == breed_name)

            history_code = f"P{idx+1:05d}"

            pet, _ = Pet.objects.get_or_create(
                history_code=history_code,
                veterinary_center=center,
                defaults={
                    "name": name,
                    "birth_date": dob,
                    "sex": sex,
                    "species": species,
                    "breed": breed,
                    "last_attending_vet": vet_user,
                    "photo_url": photo,
                    "body_description": body_desc,
                    "size": size,
                    "last_weight": last_weight,
                },
            )

            owner = None

            if person_contacts:
                owner = person_contacts[idx % len(person_contacts)]

                if owner and not pet.owner.filter(id=owner.id).exists():
                    pet.owner.add(owner)

            if institution_contacts and idx % 2 == 0:
                inst = institution_contacts[0]

                if not pet.brought_by.filter(id=inst.id).exists():
                    pet.brought_by.add(inst)

            elif owner:
                if not pet.brought_by.filter(id=owner.id).exists():
                    pet.brought_by.add(owner)

            pets.append(pet)

#################################
# PARTE 03
#################################

        # ======================================================
        # 6) CONSULTATION TYPES (BEFORE DISEASES)
        # ======================================================

        consultation_types_data = [
            # code, label, color, flags
            {
                "code": "consultation",
                "label": "Consulta",
                "color": "#2563eb",
                "base_price": 20000
            },
            {
                "code": "preventive",
                "label": "Consulta Preventiva",
                "color": "#22c55e",  # verde
                "is_preventive": True,
                "base_price": 25000,
            },
            {
                "code": "vaccine",
                "label": "Vacunación",
                "color": "#15803d",  # verde oscuro
                "is_preventive": True,
                "base_price": 15000,
            },
            {
                "code": "followup",
                "label": "Control / Seguimiento",
                "color": "#38bdf8",  # celeste
                "requires_follow_up": True,
                "base_price": 18000,
            },
            {
                "code": "emergency",
                "label": "Emergencia",
                "color": "#dc2626",  # rojo
                "is_emergency": True,
                "base_price": 50000,
            },
            {
                "code": "preop",
                "label": "Consulta Prequirúrgica",
                "color": "#f97316",  # naranja
                "base_price": 22000,
            },
            {
                "code": "postop",
                "label": "Control Postquirúrgico",
                "color": "#facc15",  # amarillo
                "requires_follow_up": True,
                "base_price": 20000,
            },
            {
                "code": "pediatric",
                "label": "Consulta Pediátrica",
                "color": "#8b5cf6",  # violeta
                "age_focus": "pediatric",
                "base_price": 25000,
            },
            {
                "code": "geriatric",
                "label": "Consulta Geriátrica",
                "color": "#92400e",  # marrón
                "age_focus": "senior",
                "base_price": 28000,
            },
        ]

        consultation_types = {}

        for data in consultation_types_data:
            ct, _ = ConsultationType.objects.get_or_create(
                veterinary_center=center,
                code=data["code"],
                defaults=data,
            )

            consultation_types[ct.code] = ct


        # AHORA sí
        general_type = consultation_types["consultation"]

        consultations = {}

        default_weights = {
            "Canino": 12.5,
            "Felino": 4.3,
            "Ave": 0.45,
        }
        
        for idx, pet in enumerate(pets):
            if idx % 2 == 0:
                cons = create_consultation_safe(
                    Consultation=Consultation,
                    pet=pet,
                    veterinarian=vet_user,
                    consultation_type=general_type,
                    veterinary_center=center,
                    weight=default_weights.get(pet.species.name, 5.0),
                    price=general_type.base_price,
                    now=now,
                    created_by=vet_user,
                )
                consultations[pet.id] = cons
    
#################################
# PARTE 04
#################################
    
        # ======================================================
        # 7) DISEASE GROUPS
        # ======================================================
        Disease_Group = apps.get_model("api", "Disease_Group")
        Disease_Catalog = apps.get_model("api", "Disease_Catalog")
        Pet_Disease_Case = apps.get_model("api", "Pet_Disease_Case")
        Pet_Disease_Event = apps.get_model("api", "Pet_Disease_Event")

        cat_infectious, _  = Disease_Group.objects.get_or_create(
            name="Infecciosas",
            code="INF",
            color="#dc2626",
            veterinary_center=center,
        )

        cat_derma, _ = Disease_Group.objects.get_or_create(
            name="Dermatológicas",
            code="DERM",
            color="#f97316",
            veterinary_center=center,
        )

        cat_dental, _ = Disease_Group.objects.get_or_create(
            name="Dentales",
            code="DENT",
            color="#0ea5e9",
            veterinary_center=center,
        )

        cat_metabolic, _ = Disease_Group.objects.get_or_create(
            name="Metabólicas",
            code="METAB",
            color="#a855f7",
            veterinary_center=center,
        )

        cat_msk, _ = Disease_Group.objects.get_or_create(
            name="Músculo-Esqueléticas",
            code="MSK",
            color="#22c55e",
            veterinary_center=center,
        )

        # ======================================================
        # 8) DISEASE CATALOG
        # ======================================================
        d_oti_canina, _ = Disease_Catalog.objects.get_or_create(
            name="Otitis Externa",
            species=species_objs["Canino"],
            veterinary_center=center,
            disease_group=cat_derma,
            diagnostic_code="OTI-CAN-001",
            contagious=False,
            can_be_chronic=False,
        )

        d_derma_canina, _ = Disease_Catalog.objects.get_or_create(
            name="Dermatitis Alérgica",
            species=species_objs["Canino"],
            veterinary_center=center,
            disease_group=cat_derma,
            diagnostic_code="DERM-CAN-002",
            contagious=False,
            can_be_chronic=False,
        )

        d_periodontal, _ = Disease_Catalog.objects.get_or_create(
            name="Enfermedad Periodontal",
            species=species_objs["Canino"],
            veterinary_center=center,
            disease_group=cat_dental,
            diagnostic_code="DENT-CAN-003",
            contagious=False,
            can_be_chronic=True,
        )


        d_osteo, _ = Disease_Catalog.objects.get_or_create(
            name="Osteoartritis",
            species=species_objs["Canino"],
            veterinary_center=center,
            disease_group=cat_msk,
            diagnostic_code="MSK-CAN-005",
            contagious=False,
            can_be_chronic=True,
        )

        d_ckd, _ = Disease_Catalog.objects.get_or_create(
            name="Enfermedad Renal Crónica",
            species=species_objs["Felino"],
            veterinary_center=center,
            disease_group=cat_metabolic,
            diagnostic_code="MET-FEL-001",
            can_be_chronic=True,
        )

        d_gingivitis, _ = Disease_Catalog.objects.get_or_create(
            name="Gingivitis Felina",
            species=species_objs["Felino"],
            veterinary_center=center,
            disease_group=cat_dental,
            diagnostic_code="DENT-FEL-002",
            can_be_chronic=False,
        )

        d_resp_complex, _ = Disease_Catalog.objects.get_or_create(
            name="Complejo Respiratorio Felino",
            species=species_objs["Felino"],
            veterinary_center=center,
            disease_group=cat_infectious,
            diagnostic_code="INF-FEL-003",
            contagious=True,
        )

        d_psitacosis, _ = Disease_Catalog.objects.get_or_create(
            name="Psitacosis",
            species=species_objs["Ave"],
            veterinary_center=center,
            disease_group=cat_infectious,
            diagnostic_code="INF-AVE-001",
            contagious=True,
            zoonotic=True,
            can_be_chronic=False,
        )


#################################
# PARTE 05
#################################

        # ======================================================
        # 9) PET DISEASE CASES + INITIAL EVENTS
        # ======================================================
        def create_pet_disease_case(
            *,
            pet: models.Model,
            disease: models.Model,
            severity: str,
            notes: Optional[str],
        ) -> models.Model:
            case, created = Pet_Disease_Case.objects.get_or_create(
                pet=pet,
                disease_catalog=disease,
                veterinary_center=center,
                defaults={
                    "diagnosis_date": now.date(),
                    "initial_consultation": consultations.get(pet.pk),
                },
            )

            if created:
                consultation = consultations.get(pet.pk)
                Pet_Disease_Event.objects.get_or_create(
                    pet_disease_case=case,
                    event_type=Choices_DiseaseEventType.DIAGNOSIS,
                    veterinary_center=center,
                    defaults={
                        "consultation": consultation,
                        "severity": severity,
                        "notes": notes,
                        "event_date": now,
                    },
                )

            return case



        # ------------------------------------------------------
        # ASSIGN DISEASES TO PETS
        # ------------------------------------------------------
        create_pet_disease_case(
            pet=pets[0], 
            disease=d_oti_canina, 
            severity="mild", 
            notes="Oído ligeramente inflamado."
        )

        create_pet_disease_case(
            pet=pets[0], 
            disease=d_derma_canina, 
            severity="moderate", 
            notes=""
        )

        create_pet_disease_case(
            pet=pets[1], 
            disease=d_gingivitis, 
            severity="mild", 
            notes=""
        )

        # Crear el caso primero
        case = create_pet_disease_case(
            pet=pets[2],
            disease=d_ckd,
            severity="moderate",
            notes="Enfermedad renal crónica en evaluación inicial.",
        )

        # Crear el evento que declara el caso como crónico
        Pet_Disease_Event.objects.get_or_create(
            pet_disease_case=case,
            event_type=Choices_DiseaseEventType.CHRONIC_DECLARATION,
            veterinary_center=center,
            defaults={
                "consultation": consultations.get(getattr(case, "pet_id")),
                "severity": "moderate",
                "notes": "Caso declarado crónico basado en evolución clínica.",
                "event_date": now,
            },
        )

        create_pet_disease_case(
            pet=pets[3], 
            disease=d_osteo, 
            severity="mild", 
            notes="Molestia leve en cadera."
        )
       
        critical_disease_case = create_pet_disease_case(
            pet=pets[4],  # Ave con psitacosis (buen candidato)
            disease=d_psitacosis,
            severity="moderate",
            notes="Riesgo zoonótico. Requiere aislamiento."
        )

        create_pet_disease_case(
            pet=pets[5], 
            disease=d_periodontal, 
            severity="moderate", 
            notes=""
        )

        create_pet_disease_case(
            pet=pets[6], 
            disease=d_resp_complex, 
            severity="mild", 
            notes=""
        )

        create_pet_disease_case(
            pet=pets[7], 
            disease=d_derma_canina, 
            severity="mild", 
            notes=""
        )
        
        # ======================================================
        # 9.1) CRITICAL CASE FROM DISEASE
        # ======================================================

        Critical_Case.objects.get_or_create(
            veterinary_center=center,
            pet=getattr(critical_disease_case, "pet"),
            disease_case=critical_disease_case,
            reason="Psitacosis activa con riesgo zoonótico.",
            created_by=vet_user,
        )


#################################
# PARTE 06
#################################

        # ======================================================
        # 10) PROBLEM GROUPS
        # ======================================================
        Problem_Group = apps.get_model("api", "Problem_Group")
        Problem_Catalog = apps.get_model("api", "Problem_Catalog")
        Pet_Problem_Case: Type[models.Model] = apps.get_model("api", "Pet_Problem_Case")
        Pet_Problem_Event: Type[models.Model] = apps.get_model("api", "Pet_Problem_Event")

        prob_trauma, _ = Problem_Group.objects.get_or_create(
            name="Trauma",
            code="TRAUMA",
            color="#ef4444",
            description="",
            veterinary_center=center,
        )

        prob_general, _ = Problem_Group.objects.get_or_create(
            name="Síntomas Generales",
            code="SYMPT",
            color="#6366f1",
            description="",
            veterinary_center=center,
        )

        prob_skin, _ = Problem_Group.objects.get_or_create(
            name="Problemas Dermatológicos",
            code="DERM-PROB",
            color="#0ea5e9",
            description="",
            veterinary_center=center,
        )

        prob_msk, _ = Problem_Group.objects.get_or_create(
            name="Músculo-Esquelético",
            code="MSK",
            color="#22c55e",
            description="",
            veterinary_center=center,
        )

        prob_resp, _ = Problem_Group.objects.get_or_create(
            name="Respiratorio",
            code="RESP",
            color="#f59e0b",
            description="",
            veterinary_center=center,
        )

        # ======================================================
        # 11) PROBLEM CATALOG
        # ======================================================
        p_herida, _ = Problem_Catalog.objects.get_or_create(
            name="Herida Traumática",
            veterinary_center=center,
            problem_group=prob_trauma,
            defaults={
                "is_emergency": False,
                "is_chronic_prone": False,
            },
        )
        p_herida.species.add(species_objs["Canino"])

        p_cojera, _ = Problem_Catalog.objects.get_or_create(
            name="Cojera",
            veterinary_center=center,
            problem_group=prob_msk,
            defaults={
                "is_emergency": False,
                "is_chronic_prone": True,
            },
        )
        p_cojera.species.add(species_objs["Canino"])

        p_vomitos, _ = Problem_Catalog.objects.get_or_create(
            name="Vómitos",
            veterinary_center=center,
            problem_group=prob_general,
            defaults={
                "is_emergency": True,
                "is_chronic_prone": False,
            },
        )
        p_vomitos.species.add(species_objs["Canino"])

        p_estornudos, _ = Problem_Catalog.objects.get_or_create(
            name="Estornudos Frecuentes",
            veterinary_center=center,
            problem_group=prob_resp,
            defaults={
                "is_emergency": False,
                "is_chronic_prone": False,
            },
        )
        p_estornudos.species.add(species_objs["Felino"])

        p_alopecia, _ = Problem_Catalog.objects.get_or_create(
            name="Alopecia",
            veterinary_center=center,
            problem_group=prob_skin,
            defaults={
                "is_emergency": False,
                "is_chronic_prone": True,
            },
        )
        p_alopecia.species.add(species_objs["Felino"])

        p_plumas_rotas, _ = Problem_Catalog.objects.get_or_create(
            name="Plumas Quebradizas",
            veterinary_center=center,
            problem_group=prob_skin,
            defaults={
                "is_emergency": False,
                "is_chronic_prone": False,
            },
        )
        p_plumas_rotas.species.add(species_objs["Ave"])

        p_dificultad_respirar, _ = Problem_Catalog.objects.get_or_create(
            name="Dificultad Respiratoria",
            veterinary_center=center,
            problem_group=prob_resp,
            defaults={
                "is_emergency": True,
                "is_chronic_prone": False,
            },
        )
        p_dificultad_respirar.species.add(species_objs["Ave"])

#################################
# PARTE 07
#################################

        # ======================================================
        # 12) PET PROBLEM CASES + INITIAL EVENTS
        # ======================================================
        def create_pet_problem_case(
            *,
            pet: models.Model,
            problem: models.Model,
            event_type: str,
            notes: Optional[str],
            consultation: Optional[models.Model],
            updated_by: Optional[models.Model],
            event_date: datetime,

            # 👇 CAPTURA PARA PYLANCE (CLAVE)
            PetProblemCaseModel: Type[models.Model] = Pet_Problem_Case,
            PetProblemEventModel: Type[models.Model] = Pet_Problem_Event,

        ) -> models.Model:

            case, created = PetProblemCaseModel.objects.get_or_create(
                pet=pet,
                problem_catalog=problem,
                veterinary_center=center,
                defaults={
                    "first_noted_date": event_date.date(),
                },
            )

            if created:

                PetProblemEventModel.objects.get_or_create(
                    pet_problem_case=case,
                    event_type=event_type,
                    veterinary_center=center,
                    defaults={
                        "consultation": consultation,
                        "notes": notes,
                        "updated_by": updated_by,
                        "event_date": event_date,
                    },
                )

            return case

        # ------------------------------------------------------
        # ASSIGN PROBLEMS TO PETS
        # ------------------------------------------------------

        create_pet_problem_case(
            pet=pets[0],
            problem=p_cojera,
            event_type=Choices_ProblemEventType.DIAGNOSIS,
            notes="Cojera leve posterior, sin dolor aparente.",
            consultation=consultations.get(pets[0].id),
            updated_by=vet_user,
            event_date=now,
        )

        create_pet_problem_case(
            pet=pets[1],
            problem=p_estornudos,
            event_type=Choices_ProblemEventType.DIAGNOSIS,
            notes="Estornudos persistentes 48h.",
            consultation=consultations.get(pets[1].id),
            updated_by=vet_user,
            event_date=now,
        )

        create_pet_problem_case(
            pet=pets[2],
            problem=p_alopecia,
            event_type=Choices_ProblemEventType.DIAGNOSIS,
            notes="Pérdida de pelo en zona lumbar.",
            consultation=consultations.get(pets[2].id),
            updated_by=vet_user,
            event_date=now,
        )

        create_pet_problem_case(
            pet=pets[3],
            problem=p_herida,
            event_type=Choices_ProblemEventType.DIAGNOSIS,
            notes="Rasguño superficial en zona torácica.",
            consultation=consultations.get(pets[3].id),
            updated_by=vet_user,
            event_date=now,
        )
       
        create_pet_problem_case(
            pet=pets[4],  # mismo u otro pet, tú decides
            problem=p_dificultad_respirar,
            event_type=Choices_ProblemEventType.DIAGNOSIS,
            notes="Respiración forzada. Compromiso respiratorio.",
            consultation=consultations.get(pets[4].id),
            updated_by=vet_user,
            event_date=now,
        )

        create_pet_problem_case(
            pet=pets[5],
            problem=p_vomitos,
            event_type=Choices_ProblemEventType.DIAGNOSIS,
            notes="Vómitos esporádicos, monitoreo recomendado.",
            consultation=consultations.get(pets[5].id),
            updated_by=vet_user,
            event_date=now,
        )

        critical_problem_case = create_pet_problem_case(
            pet=pets[6],
            problem=p_dificultad_respirar,
            event_type=Choices_ProblemEventType.DIAGNOSIS,
            notes="Compatible con complejo respiratorio felino.",
            consultation=consultations.get(pets[6].id),
            updated_by=vet_user,
            event_date=now,
        )

        create_pet_problem_case(
            pet=pets[7],
            problem=p_cojera,
            event_type=Choices_ProblemEventType.DIAGNOSIS,
            notes="Cojera en extremidad posterior derecha.",
            consultation=consultations.get(pets[7].id),
            updated_by=vet_user,
            event_date=now,
        )
        
        # ======================================================
        # 12.1) CRITICAL CASE FROM PROBLEM
        # ======================================================

        Critical_Case.objects.get_or_create(
            veterinary_center=center,
            pet=cast("Pet_Problem_Case", critical_problem_case).pet,
            problem_case=critical_problem_case,
            reason="Cuadro respiratorio agudo con compromiso clínico.",
            resolved_at=now,
            created_by=vet_user,
        )

#################################
# PARTE 08
#################################

        # ======================================================
        # 13) PROCEDURES & VACCINES
        # ======================================================
        Procedure_Type = apps.get_model("api", "Procedure_Type")
        Vaccine_Type = apps.get_model("api", "Vaccine_Type")
        Clinical_Event = apps.get_model("api", "Clinical_Event")
        Follow_Up_Category = apps.get_model("api", "Follow_Up_Category")
        Follow_Up = apps.get_model("api", "Follow_Up")

        # proc_consulta, _ = Procedure_Type.objects.get_or_create(
        #     name="Consulta General",
        #     category="Consulta",
        #     code="GENERAL_CONSULTATION",
        #     veterinary_center=center,
        #     defaults={
        #         "requires_followup": False,
        #     },
        # )

        # proc_radio, _ = Procedure_Type.objects.get_or_create(
        #     name="Radiografía",
        #     category="Diagnóstico",
        #     code="READIOGRAPHY",
        #     veterinary_center=center,
        #     defaults={
        #         "requires_followup": False,
        #     },
        # )

        proc_desparasitacion, _ = Procedure_Type.objects.get_or_create(
            name="Desparasitación",
            category="Prevención",
            veterinary_center=center,
            code="DEWORMING",
            defaults={
                "requires_followup": True,
                "followup_interval_months": 3,
            },
        )

        vac_canina, _ = Vaccine_Type.objects.get_or_create(
            name="Antirrábica",
            species=species_objs["Canino"],
            veterinary_center=center,
            code="RABIES_VACCINE",
            defaults={
                "requires_booster": True,
                "booster_interval_months": 12,
            },
        )

        vac_felina, _ = Vaccine_Type.objects.get_or_create(
            name="Triple Felina",
            species=species_objs["Felino"],
            veterinary_center=center,
            code="FVRCP_VACCINE",
            defaults={
                "requires_booster": True,
                "booster_interval_months": 12,
            },
        )

        # ======================================================
        # 14) FOLLOW_UP CATEGORIES
        # ======================================================
        default_categories = [
            ("reminder", "Recordatorio"),
            ("follow_up", "Seguimiento"),
            ("results", "Entrega de Resultados"),
            ("owner_question", "Consulta del Propietario"),
            ("appointment_change", "Cambio de Cita"),
            ("prescription_refill", "Reposición de Receta"),
            ("payment", "Consulta de Pago"),
            ("emergency", "Emergencia"),
            ("internal_note", "Nota Interna"),
        ]

        for code, label in default_categories:
            Follow_Up_Category.objects.get_or_create(
                code=code,
                label=label,
                description="",
                veterinary_center=center,
            )

        reminder_category = Follow_Up_Category.objects.get(
            code="reminder",
            veterinary_center=center,
        )

        followup_category = Follow_Up_Category.objects.get(
            code="follow_up",
            veterinary_center=center,
        )

#################################
# PARTE 09
#################################

        # ======================================================
        # 15) CLINICAL EVENTS
        # ======================================================
        clinical_events = []

        for pet in pets:
            consultation = consultations.get(pet.id)
            if not consultation:
                continue
            # ev1, _ = Clinical_Event.objects.get_or_create(
            #     veterinary_center=center,
            #     pet=pet,
            #     consultation=consultation,
            #     procedure_type=proc_consulta,
            #     occurred_at=consultation.consulted_at or now,
            #     defaults={
            #         "vet": vet_user,
            #         "notes": "Consulta clínica general.",
            #         "is_applied": True,
            #         "applied_at": consultation.consulted_at or now,
            #         "is_closed": True,
            #         "closed_at": consultation.consulted_at or now,
            #     },
            # )

            # ev2, _ = Clinical_Event.objects.get_or_create(
            #     veterinary_center=center,
            #     pet=pet,
            #     consultation=consultation,
            #     procedure_type=proc_radio,
            #     occurred_at=consultation.consulted_at or now,
            #     defaults={
            #         "vet": vet_user,
            #         "notes": "Radiografía de control.",
            #         "is_applied": True,
            #         "applied_at": consultation.consulted_at or now,
            #         "is_closed": True,
            #         "closed_at": consultation.consulted_at or now,
            #     },
            # )

            base_date = consultation.consulted_at or now

            next_due_date = None

            if proc_desparasitacion.followup_interval_months:
                next_due_date = base_date + relativedelta(
                    months=proc_desparasitacion.followup_interval_months
                )
            elif proc_desparasitacion.followup_interval_weeks:
                next_due_date = base_date + relativedelta(
                    weeks=proc_desparasitacion.followup_interval_weeks
                )
            ev3, _ = Clinical_Event.objects.get_or_create(
                veterinary_center=center,
                pet=pet,
                consultation=consultation,
                procedure_type=proc_desparasitacion,
                occurred_at=base_date,
                defaults={
                    "vet": vet_user,
                    "notes": "Desparasitación preventiva.",
                    "is_applied": True,
                    "applied_at": base_date,
                    "next_due_date": next_due_date,
                },
            )

            clinical_events.append(ev3)

            if pet.species.name == "Canino":
                vaccine = vac_canina
            elif pet.species.name == "Felino":
                vaccine = vac_felina
            else:
                vaccine = None

            if vaccine:
                ev4, created = Clinical_Event.objects.get_or_create(
                    veterinary_center=center,
                    pet=pet,
                    consultation=consultation,
                    vaccine_type=vaccine,
                    occurred_at=consultation.consulted_at or now,
                    defaults={
                        "vet": vet_user,
                        "notes": "Vacunación anual.",
                    },
                )
                if created:
                    ev4.is_applied = True
                    ev4.applied_at = ev4.occurred_at

                    base_date = consultation.consulted_at or now

                    if vaccine.booster_interval_months:
                        ev4.next_due_date = base_date + relativedelta(
                            months=vaccine.booster_interval_months
                        )
                    elif vaccine.booster_interval_weeks:
                        ev4.next_due_date = base_date + relativedelta(
                            weeks=vaccine.booster_interval_weeks
                        )

                    ev4.save(update_fields=[
                        "is_applied",
                        "applied_at",
                        "next_due_date",
                    ])

                clinical_events.append(ev4)

        # ======================================================
        # 16) AUTOMATIC FOLLOW_UPS FROM CLINICAL EVENTS
        # ======================================================

        from api.shared.choices.choices import Choices_SOAPContextTypes

        SOAP_Template = apps.get_model("api", "SOAP_Template")
        Consultation_Template = apps.get_model("api", "Consultation_Template")
        Procedure_Template = apps.get_model("api", "Procedure_Template")

#################################
# PARTE 10
#################################

        # --------------------------------------------------
        # CLINICAL FOCUSES
        # --------------------------------------------------

        general_clinical_focus, _ = Clinical_Focus_For_SOAP_Template.objects.get_or_create(
            code="general",
            label="General",
            veterinary_center=center,
            description=(
                "Evaluación clínica general del paciente. "
                "Incluye revisión global de signos vitales, estado corporal, "
                "conducta, apetito y motivo de consulta no focalizado."
            ),
        )

        gastrointestinal_clinical_focus, _ = Clinical_Focus_For_SOAP_Template.objects.get_or_create(
            code="gastrointestinal",
            label="Gastrointestinal",
            veterinary_center=center,
            description=(
                "Enfoque clínico digestivo. Incluye vómitos, diarrea, anorexia, "
                "dolor abdominal, distensión, deshidratación y alteraciones del tránsito intestinal."
            ),
        )

        other_clinical_focus, _ = Clinical_Focus_For_SOAP_Template.objects.get_or_create(
            code="other",
            label="Otro / No específico",
            veterinary_center=center,
            description=(
                "Enfoque clínico no específico o misceláneo. "
                "Se utiliza cuando el cuadro no encaja claramente en un sistema "
                "orgánico definido o requiere evaluación adicional."
            ),
        )

        # --------------------------------------------------
        # SOAP TEMPLATES
        # --------------------------------------------------

        soap_general, _ = SOAP_Template.objects.get_or_create(
            veterinary_center=center,
            name="SOAP - Consulta General",
            context=Choices_SOAPContextTypes.INITIAL,
            clinical_focus=general_clinical_focus,
            subjective="Tutor refiere motivo de consulta general.",
            objective="Paciente alerta, constantes vitales dentro de rangos normales.",
            assessment="Paciente clínicamente estable.",
            plan="Indicaciones generales y seguimiento según evolución.",
            is_default=True,
        )

        soap_general.species.set([
            species_objs["Canino"],
            species_objs["Felino"],
        ])

        soap_emergency_digestive, _ = SOAP_Template.objects.get_or_create(
            veterinary_center=center,
            name="SOAP - Emergencia Digestiva",
            context=Choices_SOAPContextTypes.EMERGENCY,
            clinical_focus=gastrointestinal_clinical_focus,
            subjective="Tutor refiere vómitos y/o diarrea de inicio agudo.",
            objective="Deshidratación leve, dolor abdominal a la palpación.",
            assessment="Gastroenteritis aguda. DDx: pancreatitis.",
            plan="Fluidoterapia, antiemético, ayuno controlado y reevaluación.",
        )

        soap_emergency_digestive.species.set([
            species_objs["Canino"],
            species_objs["Felino"],
        ])

        soap_followup, _ = SOAP_Template.objects.get_or_create(
            veterinary_center=center,
            name="SOAP - Control / Seguimiento",
            context=Choices_SOAPContextTypes.FOLLOW_UP,
            clinical_focus=other_clinical_focus,
            subjective="Tutor refiere evolución desde la última consulta.",
            objective="Mejoría clínica respecto a control previo.",
            assessment="Evolución favorable.",
            plan="Mantener tratamiento y programar nuevo control.",
        )

        soap_followup.species.set([
            species_objs["Canino"],
            species_objs["Felino"],
        ])

        soap_vaccine, _ = SOAP_Template.objects.get_or_create(
            veterinary_center=center,
            name="SOAP - Vacunación",
            context=Choices_SOAPContextTypes.PREVENTIVE,
            clinical_focus=other_clinical_focus,
            subjective="Paciente acude para vacunación programada.",
            objective="Paciente clínicamente sano al examen previo.",
            assessment="Paciente apto para vacunación.",
            plan="Aplicar vacuna correspondiente e indicar cuidados post vacunación.",
        )

        soap_vaccine.species.set([
            species_objs["Canino"],
            species_objs["Felino"],
        ])

#################################
# PARTE 11
#################################

        # --------------------------------------------------
        # DEFAULT TEMPLATES
        # --------------------------------------------------

        Consultation_Template.objects.get_or_create(
            veterinary_center=center,
            name="Consulta General",
            consultation_type=general_type,
            defaults={
                "default_price": general_type.base_price,
                "default_duration_minutes": 30,
                "default_soap_template": soap_general,
            },
        )

        Procedure_Template.objects.get_or_create(
            veterinary_center=center,
            name="Desparasitación",
            procedure_type=proc_desparasitacion,
            defaults={
                "default_notes": "Aplicación de antiparasitario externo/interno.",
            },
        )

        # --------------------------------------------------
        # FOLLOWUPS LOOP
        # --------------------------------------------------

        for ce in clinical_events:

            contact = ce.pet.owner.first() or ce.pet.brought_by.first()

            if not ce.next_due_date:
                continue

            if ce.procedure_type and ce.procedure_type.requires_followup:

                Follow_Up.objects.get_or_create(
                    veterinary_center=center,
                    pet=ce.pet,
                    clinical_event=ce,
                    follow_up_category=followup_category,
                    due_date=ce.next_due_date,
                    defaults={
                        "contact": contact,
                        "notes": f"Seguimiento de {ce.procedure_type.name}.",
                    },
                )

            elif ce.vaccine_type and ce.vaccine_type.requires_booster:

                Follow_Up.objects.get_or_create(
                    veterinary_center=center,
                    pet=ce.pet,
                    clinical_event=ce,
                    follow_up_category=reminder_category,
                    due_date=ce.next_due_date,
                    defaults={
                        "contact": contact,
                        "notes": f"Recordatorio de refuerzo: {ce.vaccine_type.name}.",
                    },
                )
                
#################################
# PARTE 12
#################################

def unload_data(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """
    Reverse migration hook.
    Elimina únicamente datos creados por preload_data si es necesario.
    """
    Critical_Case = apps.get_model("api", "Critical_Case")
    SOAP_Template = apps.get_model("api", "SOAP_Template")
    Clinical_Focus_For_SOAP_Template = apps.get_model("api", "Clinical_Focus_For_SOAP_Template")
    Species = apps.get_model("api", "Species")
    Medication = apps.get_model("api", "Medication")
    Procedure_Type = apps.get_model("api", "Procedure_Type")

    # Ejemplo: borrar solo registros creados por preload (usa identifiers únicos)

    Critical_Case.objects.filter(
        reason="Cuadro respiratorio agudo con compromiso clínico."
    ).delete()

    SOAP_Template.objects.filter(
        name__in=[
            "SOAP - Consulta General",
            "SOAP - Emergencia Digestiva",
        ]
    ).delete()

    Clinical_Focus_For_SOAP_Template.objects.filter(
        code__in=[
            "general",
            "emergency",
            "gastrointestinal",
        ]
    ).delete()

    Procedure_Type.objects.filter(
        code__in=[
            "CONSULT_GENERAL",
            "EMERGENCY_VISIT",
        ]
    ).delete()

    Medication.objects.filter(
        code__in=[
            "AMOXICILLIN",
            "MELOXICAM",
        ]
    ).delete()

    Species.objects.filter(
        name__in=[
            "Canino",
            "Felino",
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(load_initial_data, reverse_code=unload_data),
    ]

