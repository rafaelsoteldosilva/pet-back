# api/shared/choices/choices.py

from __future__ import annotations

from django.db import models


class Choices_Diagnostic_Coding_System(models.TextChoices):
    VENOM = "VeNom", "Códigos VeNom"
    INTERNAL = "Internal", "Códigos Internos"


class Choices_Center_Contact_Type(models.TextChoices):
    PERSON = "PERSON", "Persona"
    INSTITUTION = "INSTITUTION", "Institución"

    @classmethod
    def values_set(cls) -> set[str]:
        return {
            item.value
            for item in cls
        }


class Choices_Pet_Contact_Link_Role(models.TextChoices):
    OWNER_GUARDIAN = (
        "OWNER_GUARDIAN",
        "Propietario / Tutor",
    )

    CAREGIVER = (
        "CAREGIVER",
        "Cuidador",
    )

    BILLING_RESPONSIBLE = (
        "BILLING_RESPONSIBLE",
        "Responsable de pago",
    )

    REFERRING_VET = (
        "REFERRING_VET",
        "Veterinario remitente",
    )

    RESPONSIBLE_INSTITUTION = (
        "RESPONSIBLE_INSTITUTION",
        "Institución responsable",
    )

    REFERRING_INSTITUTION = (
        "REFERRING_INSTITUTION",
        "Institución remitente",
    )

    BREEDER = (
        "BREEDER",
        "Criador / Criadero",
    )

    SHELTER_OR_FOUNDATION = (
        "SHELTER_OR_FOUNDATION",
        "Refugio o fundación",
    )

    @classmethod
    def normalize_role(cls, role: str | None) -> str | None:
        if role is None:
            return None

        clean_role = str(role).strip().upper()

        return clean_role or None

    @classmethod
    def values_set(cls) -> set[str]:
        return {
            role.value
            for role in cls
        }

    @classmethod
    def person_role_values(cls) -> set[str]:
        return {
            cls.OWNER_GUARDIAN.value,
            cls.CAREGIVER.value,
            cls.BILLING_RESPONSIBLE.value,
            cls.REFERRING_VET.value,
            cls.BREEDER.value,
        }

    @classmethod
    def institution_role_values(cls) -> set[str]:
        return {
            cls.RESPONSIBLE_INSTITUTION.value,
            cls.BILLING_RESPONSIBLE.value,
            cls.REFERRING_INSTITUTION.value,
            cls.BREEDER.value,
            cls.SHELTER_OR_FOUNDATION.value,
        }

    @classmethod
    def is_person_role(cls, role: str | None) -> bool:
        return cls.normalize_role(role) in cls.person_role_values()

    @classmethod
    def is_institution_role(cls, role: str | None) -> bool:
        return cls.normalize_role(role) in cls.institution_role_values()


class Choices_Pet_Contact_Link_Permission(models.TextChoices):
    AUTHORIZE_TREATMENT = (
        "AUTHORIZE_TREATMENT",
        "Puede autorizar tratamientos",
    )

    RECEIVE_MEDICAL_UPDATES = (
        "RECEIVE_MEDICAL_UPDATES",
        "Puede recibir información médica",
    )

    RECEIVE_BILLING = (
        "RECEIVE_BILLING",
        "Puede recibir información de pago",
    )

    PICKUP_PET = (
        "PICKUP_PET",
        "Puede retirar al paciente",
    )

    @classmethod
    def values_set(cls) -> set[str]:
        return {
            permission.value
            for permission in cls
        }


class Choices_Contact_Relationship_for_appointments(models.TextChoices):
    FAMILY = "family", "Family"
    FRIEND = "friend", "Friend"
    NEIGHBOR = "neighbor", "Neighbor"
    CARETAKER = "caretaker", "Caretaker"
    EMPLOYEE = "employee", "Employee"
    OTHER = "other", "Other"


class Choices_Pet_Status(models.TextChoices):
    ACTIVE = "ACTIVE", "Activo"
    INACTIVE = "INACTIVE", "Inactivo"
    DECEASED = "DECEASED", "Fallecido"
    ARCHIVED = "ARCHIVED", "Archivado"


class Choices_Pet_Clinical_Record_Status(models.TextChoices):
    DRAFT = "draft", "Borrador"
    CLINICAL = "clinical", "Clínico"
    ARCHIVED = "archived", "Archivado"


class Choices_Appointment_Status(models.TextChoices):
    SCHEDULED = "scheduled", "Scheduled"
    CONFIRMED = "confirmed", "Confirmed"
    CANCELLED = "cancelled", "Cancelled"
    NO_SHOW = "no_show", "No show"


class Choices_Consultation_Type(models.TextChoices):
    GENERAL = "general", "General"
    CLINICAL = "clinical", "Clinical"
    FOLLOW_UP = "follow_up", "Follow-up"
    EMERGENCY = "emergency", "Emergency"
    VACCINE = "vaccine", "Vaccine"
    WELLNESS = "wellness", "Wellness"
    PROCEDURE = "procedure", "Procedure"
    DIAGNOSTIC = "diagnostic", "Diagnostic"
    HOSPITALIZATION = "hospitalization", "Hospitalization"
    ADMINISTRATIVE = "administrative", "Administrative"
    OTHER = "other", "Other"


class Choices_Consultation_Status(models.TextChoices):
    IN_PROGRESS = "in_progress", "En curso"
    COMPLETED = "completed", "Finalizada"
    CANCELLED = "cancelada", "Cancelada"


class Choices_Procedure_Status(models.TextChoices):
    PENDING = "pending", "Pendiente"
    DONE = "done", "Realizado"


class Choices_Sex(models.TextChoices):
    MALE = "m", "Macho"
    FEMALE = "f", "Hembra"
    UNDETERMINED = "u", "Indeterminado"


class Choices_Size(models.TextChoices):
    SMALL = "small", "Pequeño"
    MEDIUM = "medium", "Mediano"
    LARGE = "large", "Grande"
    XLARGE = "xlarge", "Gigante"


class Choices_Role(models.TextChoices):
    CENTER_ADMIN = "CENTER_ADMIN", "Administrador"
    VETERINARIAN = "VETERINARIAN", "Médico veterinario"
    ASSISTANT = "ASSISTANT", "Asistente"
    RECEPTIONIST = "RECEPTIONIST", "Recepción"
    VIEWER = "VIEWER", "Solo lectura"


class Choices_Severity_Level(models.TextChoices):
    MILD = "mild", "Leve"
    MODERATE = "moderate", "Moderada"
    SEVERE = "severe", "Severa"


class Choices_Disease_Event_Type(models.TextChoices):
    DIAGNOSIS = "DIAGNOSIS", "Diagnóstico"
    FOLLOW_UP = "FOLLOW_UP", "Seguimiento"
    PROGRESSION = "PROGRESSION", "Progresión"
    IMPROVEMENT = "IMPROVEMENT", "Mejoría"
    RELAPSE = "RELAPSE", "Recaída"
    CHRONIC_DECLARATION = "CHRONIC", "Declaración de cronicidad"
    REMISSION = "REMISSION", "Remisión"
    RESOLUTION = "RESOLUTION", "Resolución"
    REOPEN = "REOPEN", "Reapertura"
    CORRECTION = "CORRECTION", "Corrección administrativa"


class Choices_Disease_Case_Status(models.TextChoices):
    ACTIVE = "active", "Activo"
    RESOLVED = "resolved", "Resuelto"


class Choices_Problem_Case_Status(models.TextChoices): 
	ACTIVE = "active", "Activo" 
	INACTIVE = "inactive", "Inactivo" 
	RESOLVED = "resolved", "Resuelto"


class Choices_Problem_Event_Type(models.TextChoices):
    DIAGNOSIS = "DIAGNOSIS", "Diagnóstico inicial"
    UPDATE = "UPDATE", "Actualización clínica"
    FOLLOW_UP = "FOLLOW_UP", "Seguimiento"
    RESOLUTION = "RESOLUTION", "Resolución"
    REOPEN = "REOPEN", "Reapertura"
    CORRECTION = "CORRECTION", "Corrección administrativa"


class Choices_SOAP_Context_Types(models.TextChoices):
    INITIAL = "initial", "Primera consulta"
    FOLLOW_UP = "follow_up", "Control / Seguimiento"
    EMERGENCY = "emergency", "Emergencia"
    HOSPITALIZATION = "hospitalization", "Hospitalización"
    POSTOP = "postop", "Postoperatorio"
    PREVENTIVE = "preventive", "Preventivo / Vacunación"


class Choices_Age_Focus_Types(models.TextChoices):
    PEDIATRIC = "pediatric", "Pediátrica"
    ADULT = "adult", "Adulto"
    SENIOR = "geriatrica", "Geriátrica"


class Choices_Activity_Direction_Types(models.TextChoices):
    OUTBOUND = "outbound", "Saliente"
    INBOUND = "inbound", "Entrante"
    BOTH = "both", "Ambos"


class Choices_Critical_Case_Status(models.TextChoices):
    ACTIVE = "ACTIVE", "Activo"
    RESOLVED = "RESOLVED", "Resuelto"


class Choices_Hospitalization_Status_Choices(models.TextChoices):
    STATUS_ACTIVE = "Active", "Activo"
    STATUS_DISCHARGED = "Discharged", "Alta médica"
    STATUS_DECEASED = "Deceased", "Fallecido"


class Choices_Resource_Types(models.TextChoices):
    KENNEL = "Kennel", "Kennel"
    CAGE = "Cage", "Jaula"
    ICU = "ICU", "Terapia Intensiva"
    OXYGEN = "Oxygen", "Oxígeno"
    ISOLATION = "Isolation", "Aislamiento"


class Campaign_Type(models.TextChoices):
    VACCINATION = "vaccination", "Vaccination"
    MICROCHIP = "microchip", "Microchip"
    DEWORMING = "deworming", "Deworming"
    DENTAL = "dental", "Dental Health"
    SENIOR = "senior", "Senior Wellness"
    LAB_SCREENING = "lab_screening", "Lab Screening"
    GENERAL_WELLNESS = "general_wellness", "General Wellness"
    OTHER = "other", "Other"


class Choices_Pet_Search_Types(models.TextChoices):
    BROUGHT_BY = "brought_by", "Responsable"
    OWNER_GUARDIAN = "owner_guardian", "Propietario / Tutor"
    NAME = "name", "Nombre"
    MICROCHIP = "microchip", "Microchip"


class Choices_Campaign_Actions(models.TextChoices):
    VACCINE = "vaccine", "Vacuna"
    PROCEDURE = "procedure", "Procedimiento"
    CONSULTATION = "consultation", "Consulta"


class Choices_Campaign_Statuses(models.TextChoices):
    PENDING = "pending", "Pendiente"
    CONTACTED = "contacted", "Contactado"
    SCHEDULED = "scheduled", "Agendado"
    COMPLETED = "completed", "Completado"
    DECLINED = "declined", "Rechazado"
    EXCLUDED = "excluded", "Excluido"


class Choices_Procedure_Category(models.TextChoices):
    # Preventive medicine
    PREVENTIVE = "preventive", "Preventivo"
    VACCINATION = "vaccination", "Vacunación"
    DEWORMING = "deworming", "Desparasitación"

    # Diagnostic procedures
    DIAGNOSTIC = "diagnostic", "Diagnóstico"
    LABORATORY = "laboratory", "Laboratorio"
    IMAGING = "imaging", "Imagenología"

    # Therapeutic procedures
    TREATMENT = "treatment", "Tratamiento"
    SURGERY = "surgery", "Cirugía"
    HOSPITALIZATION = "hospitalization", "Hospitalización"

    # Reproductive medicine
    REPRODUCTIVE = "reproductive", "Reproductivo"
    STERILIZATION = "sterilization", "Esterilización"

    # Administrative / clinical management
    ADMINISTRATIVE = "administrative", "Administrativo"

    # Other / flexible
    OTHER = "other", "Otro"


class Choices_Activity_Type(models.TextChoices):
    # Comunicación directa con el cliente
    CALL = "call", "Llamada telefónica"
    WHATSAPP = "whatsapp", "Mensaje WhatsApp"
    SMS = "sms", "Mensaje SMS"
    EMAIL = "email", "Correo electrónico"

    # Actividad clínica
    FOLLOW_UP = "follow_up", "Seguimiento clínico"
    CONSULTATION_NOTE = "consultation_note", "Nota de consulta"
    CLINICAL_OBSERVATION = "clinical_observation", "Observación clínica"
    MEDICATION_COMMUNICATION = (
        "medication_communication",
        "Comunicación sobre medicación",
    )
    LAB_RESULT_COMMUNICATION = (
        "lab_result_communication",
        "Comunicación de resultado de laboratorio",
    )

    # Actividad administrativa
    APPOINTMENT_COMMUNICATION = (
        "appointment_communication",
        "Comunicación sobre cita",
    )
    BILLING_COMMUNICATION = (
        "billing_communication",
        "Comunicación administrativa",
    )
    CLIENT_COMMUNICATION = (
        "client_communication",
        "Comunicación general con cliente",
    )

    # Actividad automática del sistema
    SYSTEM_REMINDER = "system_reminder", "Recordatorio automático"
    SYSTEM_NOTIFICATION = "system_notification", "Notificación automática"
    SYSTEM_ALERT = "system_alert", "Alerta del sistema"

    # Interno
    INTERNAL_NOTE = "internal_note", "Nota interna"
    OTHER = "other", "Otro"


__all__ = [
    "Campaign_Type",
    "Choices_Activity_Direction_Types",
    "Choices_Activity_Type",
    "Choices_Age_Focus_Types",
    "Choices_Appointment_Status",
    "Choices_Campaign_Actions",
    "Choices_Campaign_Statuses",
    "Choices_Consultation_Status",
    "Choices_Consultation_Type",
    "Choices_Contact_Relationship_for_appointments",
    "Choices_Critical_Case_Status",
    "Choices_Diagnostic_Coding_System",
    "Choices_Disease_Case_Status",
    "Choices_Disease_Event_Type",
    "Choices_Hospitalization_Status_Choices",
    "Choices_Center_Contact_Type",
    "Choices_Pet_Clinical_Record_Status",
    "Choices_Pet_Contact_Link_Permission",
    "Choices_Pet_Contact_Link_Role",
    "Choices_Pet_Search_Types",
    "Choices_Pet_Status",
    "Choices_Problem_Case_Status",
    "Choices_Problem_Event_Type",
    "Choices_Procedure_Category",
    "Choices_Procedure_Status",
    "Choices_Resource_Types",
    "Choices_Role",
    "Choices_SOAP_Context_Types",
    "Choices_Severity_Level",
    "Choices_Sex",
    "Choices_Size",
]