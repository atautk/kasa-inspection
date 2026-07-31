from dataclasses import dataclass


@dataclass(slots=True)
class Operator:

    name: str
    pin_hash: str
