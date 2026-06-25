# api/domains/pet/errors.py

from __future__ import annotations


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