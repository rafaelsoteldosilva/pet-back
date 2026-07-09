# api/domains/pet/errors.py

from __future__ import annotations

from collections.abc import Iterable


class PetRuleViolationError(Exception):
    """
    Base exception for pet domain rule violations.
    """


# ======================================================
# Species / breed errors
# ======================================================


class PetSpeciesNotAllowedForCenterError(PetRuleViolationError):
    """
    Raised when the selected species is not enabled for the veterinary center.
    """

    def __init__(self, species_id: int, veterinary_center_id: int):
        self.species_id = int(species_id)
        self.veterinary_center_id = int(veterinary_center_id)

        super().__init__(
            f"Species {self.species_id} is not allowed for veterinary center "
            f"{self.veterinary_center_id}."
        )


class PetBreedDoesNotBelongToSpeciesError(PetRuleViolationError):
    """
    Raised when the selected breed does not belong to the selected species.
    """

    def __init__(self, breed_id: int, species_id: int):
        self.breed_id = int(breed_id)
        self.species_id = int(species_id)

        super().__init__(
            f"Breed {self.breed_id} does not belong to species {self.species_id}."
        )


# ======================================================
# Pet deletion errors
# ======================================================


class PetCannotBeDeletedBecauseClinicalRecordsExistError(PetRuleViolationError):
    """
    Raised when a pet cannot be deleted because it already has clinical records.
    """

    def __init__(
        self,
        *,
        clinical_record_sources: Iterable[str],
    ) -> None:
        normalized_sources = sorted(
            {
                str(source).strip()
                for source in clinical_record_sources
                if str(source).strip()
            }
        )

        self.clinical_record_sources = normalized_sources

        if normalized_sources:
            message = (
                "No se puede eliminar el paciente porque tiene información "
                "clínica asociada: "
                + ", ".join(normalized_sources)
                + "."
            )
        else:
            message = (
                "No se puede eliminar el paciente porque tiene información "
                "clínica asociada."
            )

        super().__init__(message)


# ======================================================
# Pedigree errors
# ======================================================


class PetPedigreeRegistryRequiresPedigreeError(PetRuleViolationError):
    pass


# ======================================================
# Microchip errors
# ======================================================


class PetMicrochipCodeRequiresMicrochipCodeError(PetRuleViolationError):
    pass


class PetMicrochipCode15DigitsNotApplicableError(PetRuleViolationError):
    pass


class PetMicrochipDateBeforeBirthDateError(PetRuleViolationError):
    pass


# ======================================================
# Pet_Contact_Link errors
# ======================================================


class PetContactLinkCenterContactDifferentCenterError(PetRuleViolationError):
    """
    Raised when an Center_Contact record belongs to a different veterinary
    center than the pet being linked.
    """

    def __init__(self):
        super().__init__(
            "El contacto debe pertenecer al mismo centro veterinario que la mascota."
        )


class PetContactLinkInvalidRoleForPersonError(PetRuleViolationError):
    """
    Raised when a person Center_Contact receives an institution-only role
    through a Pet_Contact_Link.
    """

    def __init__(self):
        super().__init__(
            "Para un contacto de tipo persona, selecciona un rol válido para personas."
        )


class PetContactLinkInvalidRoleForInstitutionError(PetRuleViolationError):
    """
    Raised when an institution Center_Contact receives a person-only role
    through a Pet_Contact_Link.
    """

    def __init__(self):
        super().__init__(
            "Para un contacto de tipo institución, selecciona un rol válido para instituciones."
        )


class PetContactLinkCenterContactInvalidTypeError(PetRuleViolationError):
    """
    Raised when the Center_Contact type is not recognized by the domain.
    """

    def __init__(self):
        super().__init__("Tipo de contacto inválido.")
        
class PetCannotBeDeletedByDifferentUserError(PetRuleViolationError):
    """
    Raised when a user tries to delete a pet created by another user.
    """

    def __init__(self):
        super().__init__(
            "Solo el usuario que creó el paciente puede eliminarlo."
        )


class PetContactLinkBillingResponsibleRequiresBillingPermissionError(
    PetRuleViolationError
):
    """
    Raised when a billing responsible Pet_Contact_Link cannot receive billing
    information.
    """

    def __init__(self):
        super().__init__(
            "El responsable de pago debe poder recibir información de facturación."
        )


__all__ = [
    "PetRuleViolationError",
    "PetSpeciesNotAllowedForCenterError",
    "PetBreedDoesNotBelongToSpeciesError",
    "PetCannotBeDeletedBecauseClinicalRecordsExistError",
    "PetCannotBeDeletedByDifferentUserError",
    "PetPedigreeRegistryRequiresPedigreeError",
    "PetMicrochipCodeRequiresMicrochipCodeError",
    "PetMicrochipCode15DigitsNotApplicableError",
    "PetMicrochipDateBeforeBirthDateError",
    "PetContactLinkCenterContactDifferentCenterError",
    "PetContactLinkInvalidRoleForPersonError",
    "PetContactLinkInvalidRoleForInstitutionError",
    "PetContactLinkCenterContactInvalidTypeError",
    "PetContactLinkBillingResponsibleRequiresBillingPermissionError",
]