# api/shared/choices/choices.py

from django.db import models
   
class Choices_DiagnosticCodingSystem(models.TextChoices):
    VENOM = "VeNom", "Códigos VeNom"
    INTERNAL = "Internal", "Códigos Internos"
    
class Choices_PetContactRole(models.TextChoices):
    OWNER = "OWNER", "Dueño"
    RESPONSIBLE = "RESPONSIBLE", "Responsable"
    AUTHORIZED = "AUTHORIZED", "Autorizado"
    EMERGENCY = "EMERGENCY", "Contacto de emergencia"
    BREEDER = "BREEDER", "Criador"
   
class Choices_ContactType(models.TextChoices):
    PERSON = "person", "Persona"
    INSTITUTION = "institution", "Institución"
    
class Choices_ContactRelationship(models.TextChoices):
    FAMILY = "family", "Family"
    FRIEND = "friend", "Friend"
    NEIGHBOR = "neighbor", "Neighbor"
    CARETAKER = "caretaker", "Caretaker"
    EMPLOYEE = "employee", "Employee"
    OTHER = "other", "Other"

class Choices_PetStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"
    DECEASED = "DECEASED", "Deceased"
    
class Choices_PetClinicalRecordStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    CLINICAL = "clinical", "Clinical"
    
class Choices_AppointmentStatus(models.TextChoices):
    SCHEDULED = "scheduled", "Scheduled"
    CONFIRMED = "confirmed", "Confirmed"
    CANCELLED = "cancelled", "Cancelled"
    NO_SHOW = "no_show", "No show"

class Choices_ConsultationType(models.TextChoices):
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
        
class Choices_ConsultationStatus(models.TextChoices):
    IN_PROGRESS = "in_progress", "En curso"
    COMPLETED = "completed", "Finalizada"
    CANCELLED = "cancelled", "Cancelada"
    
class Choices_ProcedureStatus(models.TextChoices):
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
    SUPER = "super", "Super User"
    ADMIN = "administrator", "Administrador"
    VET = "vet", "Veterinario"
    ASSISTANT = "assistant", "Asistente Veterinario"
    
class Choices_SeverityLevel(models.TextChoices):
    MILD = "mild", "Leve"
    MODERATE = "moderate", "Moderada"
    SEVERE = "severe", "Severa"
    
class Choices_DiseaseEventType(models.TextChoices):
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

class Choices_DiseaseCaseStatus(models.TextChoices):
    ACTIVE = "active", "Activo"
    RESOLVED = "resolved", "Resuelto"
class Choices_ProblemCaseStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactivo"
    
class Choices_ProblemEventType(models.TextChoices):
    DIAGNOSIS = "DIAGNOSIS", "Diagnóstico inicial"
    UPDATE = "UPDATE", "Actualización clínica"
    FOLLOW_UP = "FOLLOW_UP", "Seguimiento"
    RESOLUTION = "RESOLUTION", "Resolución"
    REOPEN = "REOPEN", "Reapertura"
    CORRECTION = "CORRECTION", "Corrección administrativa"
    
class Choices_SOAPContextTypes(models.TextChoices):
    INITIAL = "initial", "Primera consulta"
    FOLLOW_UP = "follow_up", "Control / Seguimiento"
    EMERGENCY = "emergency", "Emergencia"
    HOSPITALIZATION = "hospitalization", "Hospitalización"
    POSTOP = "postop", "Postoperatorio"
    PREVENTIVE = "preventive", "Preventivo / Vacunación"
    
class Choices_AgeFocusTypes(models.TextChoices):
    PEDIATRIC = "pediatric", "Pediatrica"
    ADULT = "adult", "Adulto"
    SENIOR = "geriatrica", "Geriátrica"
    
class Choices_ActivityDirectionTypes(models.TextChoices):
    OUTBOUND = "outbound", "Saliente"
    INBOUND = "inbound", "Entrante"
    BOTH = "both", "Ambos"
class Choices_CriticalCaseStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Activo"
    RESOLVED = "RESOLVED", "Resuelto"
class Choices_HospitalizationStatusChoices(models.TextChoices):
    STATUS_ACTIVE = "Active", "Activo"
    STATUS_DISCHARGED = "Discharged", "Dado de Baja"
    STATUS_DECEASED = "Deceased", "Fallecido"
    
class Choices_ResourceTypes(models.TextChoices):
    KENNEL = "Kennel", "Kennel"
    CAGE= "Cage", "Jaula"
    ICU = "ICU", "Terapia Intensiva"
    OXYGEN = "Oxygen", "Oxígeno"
    ISOLATION = "Isolation", "Aislamiento"

# class CampaignType(models.TextChoices):
#     VACCINATION = "vaccination", "Vaccination"
#     MICROCHIP = "microchip", "Microchip"
#     DEWORMING = "deworming", "Deworming"
#     DENTAL = "dental", "Dental Health"
#     SENIOR = "senior", "Senior Wellness"
#     LAB_SCREENING = "lab_screening", "Lab Screening"
#     GENERAL_WELLNESS = "general_wellness", "General Wellness"
#     OTHER = "other", "Other"
       
class Choices_PetSearchTypes(models.TextChoices):
    BROUGHT_BY = "brought_by", "Responsable"
    OWNER= "owner", "Dueño"
    NAME = "name", "Nombre"
    MICROCHIP = "microchip", "Microchip"
   
class Choices_CampaignActions(models.TextChoices):
    VACCINE = "vaccine", "Vacuna"
    PROCEDURE = "procedure", "Procedimiento"
    CONSULTATION = "consultation", "Consulta"

class Choices_CampaignStatuses(models.TextChoices):
    PENDING = "pending", "Pendiente"
    CONTACTED = "contacted", "Contactado"
    SCHEDULED = "scheduled", "Agendado"
    COMPLETED = "completed", "Completado"
    DECLINED = "declined", "Rechazado"
    EXCLUDED = "excluded", "Excluido"
    
    # STATUS_CHOICES = [
    #     ("pending", "Pendiente"),
    #     ("contacted", "Contactado"),
    #     ("scheduled", "Agendado"),
    #     ("completed", "Completado"),
    #     ("declined", "Rechazado"),
    #     ("excluded", "Excluido"),
    # ]
    
class Choices_ProcedureCategory(models.TextChoices):

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
       
class Choices_ActivityType(models.TextChoices):
    # Comunicación directa con el cliente
    CALL = "call", "Llamada telefónica"
    WHATSAPP = "whatsapp", "Mensaje WhatsApp"
    SMS = "sms", "Mensaje SMS"
    EMAIL = "email", "Correo electrónico"
    # Actividad clínica
    FOLLOW_UP = "follow_up", "Seguimiento clínico"
    CONSULTATION_NOTE = "consultation_note", "Nota de consulta"
    CLINICAL_OBSERVATION = "clinical_observation", "Observación clínica"
    MEDICATION_COMMUNICATION = "medication_communication", "Comunicación sobre medicación"
    LAB_RESULT_COMMUNICATION = "lab_result_communication", "Comunicación de resultado de laboratorio"
    # Actividad administrativa
    APPOINTMENT_COMMUNICATION = "appointment_communication", "Comunicación sobre cita"
    BILLING_COMMUNICATION = "billing_communication", "Comunicación administrativa"
    CLIENT_COMMUNICATION = "client_communication", "Comunicación general con cliente"
    # Actividad automática del sistema
    SYSTEM_REMINDER = "system_reminder", "Recordatorio automático"
    SYSTEM_NOTIFICATION = "system_notification", "Notificación automática"
    SYSTEM_ALERT = "system_alert", "Alerta del sistema"
    # Interno
    INTERNAL_NOTE = "internal_note", "Nota interna"
    OTHER = "other", "Otro"