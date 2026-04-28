import enum


class UserRole(str, enum.Enum):
    USER = "USER"
    VOLUNTEER = "VOLUNTEER"
    ADMIN = "ADMIN"


class PetSpecies(str, enum.Enum):
    DOG = "DOG"
    CAT = "CAT"
    OTHER = "OTHER"


class NotificationCategory(str, enum.Enum):
    VOLUNTEER = "VOLUNTEER"
    MATCH = "MATCH"
    REVIEW = "REVIEW"
    NEWS = "NEWS"
    POLICY = "POLICY"
    SYSTEM = "SYSTEM"


class MatchStatus(str, enum.Enum):
    WAITING = "WAITING"
    MATCHING = "MATCHING"
    PROGRESS = "PROGRESS"
    DONE = "DONE"


class ApplicationStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class VolunteerRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class StoreCategory(str, enum.Enum):
    CAFE = "CAFE"
    RESTAURANT = "RESTAURANT"
    PARK = "PARK"


class StoreStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
