from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .operator import Operator, ROLE_ADMIN, ROLE_OPERATOR

DEFAULT_OPERATOR_NAME = "Yönetici"
DEFAULT_PIN = "0000"


class OperatorManager:

    def __init__(self, path: Path | str = "configuration/operators.json"):

        self.path = Path(path)

        self._ensure_default()

    # -------------------------------------------------
    # İlk Kurulum
    # -------------------------------------------------

    def _ensure_default(self):

        if self.path.exists():
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)

        self._save([
            Operator(
                name=DEFAULT_OPERATOR_NAME,
                pin_hash=self._hash(DEFAULT_PIN),
                role=ROLE_ADMIN,
                approved=True
            )
        ])

    # -------------------------------------------------

    def _hash(self, pin: str) -> str:

        return hashlib.sha256(pin.encode("utf-8")).hexdigest()

    # -------------------------------------------------

    def _load(self) -> list[Operator]:

        if not self.path.exists():
            return []

        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)

        operators = []

        for o in data.get("operators", []):

            default_role = (
                ROLE_ADMIN if o["name"] == DEFAULT_OPERATOR_NAME
                else ROLE_OPERATOR
            )

            operators.append(
                Operator(
                    name=o["name"],
                    pin_hash=o["pin_hash"],
                    role=o.get("role", default_role),
                    # Eski kayıtlarda onay alanı yoktu; bu özellikten
                    # önce eklenmiş operatörler geriye dönük olarak
                    # onaylı sayılır, aksi halde mevcut kullanıcılar
                    # aniden erişimini kaybederdi.
                    approved=o.get("approved", True)
                )
            )

        return operators

    # -------------------------------------------------

    def _save(self, operators: list[Operator]):

        data = {
            "operators": [
                {
                    "name": o.name,
                    "pin_hash": o.pin_hash,
                    "role": o.role,
                    "approved": o.approved
                }
                for o in operators
            ]
        }

        with open(self.path, "w", encoding="utf-8") as f:

            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

    # -------------------------------------------------
    # Sorgular
    # -------------------------------------------------

    def list_operators(self) -> list[str]:

        return [o.name for o in self._load()]

    # -------------------------------------------------

    def list_operator_details(self) -> list[Operator]:

        return self._load()

    # -------------------------------------------------

    def verify(self, name: str, pin: str) -> bool:

        pin_hash = self._hash(pin)

        for operator in self._load():

            if operator.name == name and operator.pin_hash == pin_hash:
                return True

        return False

    # -------------------------------------------------

    def is_approved(self, name: str) -> bool:

        for operator in self._load():

            if operator.name == name:
                return operator.approved

        return False

    # -------------------------------------------------

    def is_admin(self, name: str) -> bool:

        for operator in self._load():

            if operator.name == name:
                return operator.role == ROLE_ADMIN

        return False

    # -------------------------------------------------
    # Operatör Yönetimi
    # -------------------------------------------------

    def create_operator(self, name: str, pin: str):

        name = name.strip()

        if not name:
            raise ValueError("Operatör adı boş olamaz.")

        operators = self._load()

        if any(o.name == name for o in operators):
            raise ValueError(f"'{name}' zaten kayıtlı.")

        operators.append(
            Operator(
                name=name,
                pin_hash=self._hash(pin),
                role=ROLE_OPERATOR,
                # Yeni eklenen operatörler yönetici onaylayana kadar
                # giriş yapamaz.
                approved=False
            )
        )

        self._save(operators)

    # -------------------------------------------------

    def approve_operator(self, name: str):

        operators = self._load()

        for operator in operators:

            if operator.name == name:

                operator.approved = True

                self._save(operators)

                return

        raise ValueError(f"'{name}' bulunamadı.")

    # -------------------------------------------------

    def delete_operator(self, name: str):

        operators = self._load()

        target = next((o for o in operators if o.name == name), None)

        if target is None:
            return

        remaining_admins = [
            o for o in operators
            if o.role == ROLE_ADMIN and o.name != name
        ]

        if target.role == ROLE_ADMIN and not remaining_admins:
            raise ValueError("Son yönetici silinemez.")

        operators = [o for o in operators if o.name != name]

        self._save(operators)

    # -------------------------------------------------

    def change_pin(self, name: str, new_pin: str):

        operators = self._load()

        for operator in operators:

            if operator.name == name:

                operator.pin_hash = self._hash(new_pin)

                self._save(operators)

                return

        raise ValueError(f"'{name}' bulunamadı.")
