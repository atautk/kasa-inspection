import pytest

from modules.configuration.operator_manager import (
    OperatorManager,
    DEFAULT_OPERATOR_NAME,
    DEFAULT_PIN
)
from modules.configuration.operator import ROLE_ADMIN, ROLE_OPERATOR


@pytest.fixture
def manager(tmp_path):

    return OperatorManager(path=tmp_path / "operators.json")


def test_bootstraps_default_admin(manager):

    assert manager.is_admin(DEFAULT_OPERATOR_NAME) is True
    assert manager.is_approved(DEFAULT_OPERATOR_NAME) is True
    assert manager.verify(DEFAULT_OPERATOR_NAME, DEFAULT_PIN) is True
    assert manager.verify(DEFAULT_OPERATOR_NAME, "wrong") is False


def test_new_operator_is_unapproved_and_not_admin(manager):

    manager.create_operator("Ali", "1234")

    assert manager.verify("Ali", "1234") is True
    assert manager.is_approved("Ali") is False
    assert manager.is_admin("Ali") is False


def test_duplicate_name_raises(manager):

    manager.create_operator("Ali", "1234")

    with pytest.raises(ValueError):
        manager.create_operator("Ali", "5678")


def test_approve_operator(manager):

    manager.create_operator("Ali", "1234")

    manager.approve_operator("Ali")

    assert manager.is_approved("Ali") is True


def test_approve_unknown_operator_raises(manager):

    with pytest.raises(ValueError):
        manager.approve_operator("Yok")


def test_delete_operator(manager):

    manager.create_operator("Ali", "1234")

    manager.delete_operator("Ali")

    assert "Ali" not in manager.list_operators()


def test_delete_last_admin_is_blocked(manager):

    with pytest.raises(ValueError):
        manager.delete_operator(DEFAULT_OPERATOR_NAME)

    # hâlâ yerinde olmalı
    assert manager.is_admin(DEFAULT_OPERATOR_NAME) is True


def test_delete_admin_allowed_when_another_admin_exists(manager):

    manager.create_operator("Yedek Yönetici", "1111")

    operators = manager._load()

    for operator in operators:
        if operator.name == "Yedek Yönetici":
            operator.role = ROLE_ADMIN
            operator.approved = True

    manager._save(operators)

    manager.delete_operator(DEFAULT_OPERATOR_NAME)

    assert DEFAULT_OPERATOR_NAME not in manager.list_operators()
    assert manager.is_admin("Yedek Yönetici") is True


def test_change_pin(manager):

    manager.create_operator("Ali", "1234")

    manager.change_pin("Ali", "9999")

    assert manager.verify("Ali", "9999") is True
    assert manager.verify("Ali", "1234") is False


def test_legacy_file_without_role_or_approved_fields(tmp_path):

    import json
    import hashlib

    path = tmp_path / "operators.json"

    legacy_hash = hashlib.sha256(b"9999").hexdigest()

    path.write_text(
        json.dumps({
            "operators": [
                {"name": DEFAULT_OPERATOR_NAME, "pin_hash": hashlib.sha256(
                    DEFAULT_PIN.encode()
                ).hexdigest()},
                {"name": "Eski Operatör", "pin_hash": legacy_hash}
            ]
        }),
        encoding="utf-8"
    )

    manager = OperatorManager(path=path)

    # eski kayıtlar geriye dönük olarak onaylı sayılır
    assert manager.is_approved("Eski Operatör") is True
    assert manager.is_admin("Eski Operatör") is False
    assert manager.is_admin(DEFAULT_OPERATOR_NAME) is True
