"""Validate migration 005 SQL structure — OIDC + RBAC."""

from __future__ import annotations

from pathlib import Path

MIGRATION = Path(__file__).parent.parent.parent / "migrations" / "005_oidc_and_rbac.sql"


def test_migration_file_exists():
    assert MIGRATION.exists()


def test_creates_users_table():
    sql = MIGRATION.read_text()
    assert "CREATE TABLE IF NOT EXISTS users" in sql


def test_users_table_has_required_columns():
    sql = MIGRATION.read_text()
    for col in ["oidc_sub", "email", "display_name", "role", "org_id"]:
        assert col in sql, f"Missing column: {col}"


def test_adds_tenant_id_columns():
    sql = MIGRATION.read_text()
    assert "ADD COLUMN tenant_id" in sql


def test_adds_user_id_columns():
    sql = MIGRATION.read_text()
    assert "ADD COLUMN user_id" in sql


def test_adds_role_to_api_keys():
    sql = MIGRATION.read_text()
    assert "ADD COLUMN role TEXT DEFAULT 'admin'" in sql


def test_is_idempotent():
    sql = MIGRATION.read_text()
    assert "IF NOT EXISTS" in sql
    assert "IF NOT EXISTS (SELECT 1 FROM information_schema" in sql


def test_has_rollback_sql():
    sql = MIGRATION.read_text()
    assert "ROLLBACK SQL" in sql
    assert "DROP TABLE IF EXISTS users" in sql
    assert "DROP COLUMN IF EXISTS tenant_id" in sql
    assert "DROP COLUMN IF EXISTS user_id" in sql
    assert "DROP COLUMN IF EXISTS role" in sql


def test_is_additive_only():
    """Migration must not contain DROP or DELETE outside rollback comments."""
    sql = MIGRATION.read_text()
    # Split on the rollback comment
    parts = sql.split("ROLLBACK SQL")
    active_sql = parts[0]
    assert "DROP " not in active_sql
    assert "DELETE " not in active_sql
