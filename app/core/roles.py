from enum import Enum


class Role(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    RP_ADMIN = "RP_ADMIN"
    DEVELOPER = "DEVELOPER"
    READ_ONLY = "READ_ONLY"
