from dataclasses import dataclass

ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"


@dataclass(slots=True)
class Operator:

    name: str
    pin_hash: str
    role: str = ROLE_OPERATOR
    approved: bool = True
