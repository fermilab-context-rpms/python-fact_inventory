"""Tests for the gather role public API.

This role collects facts from a target system and submits them to
the fact_inventory API, with an optional local audit copy.

Tests validate the role's public parameters as documented in
meta/argument_specs.yml, ensuring the documented defaults and
types are preserved across versions.

Integration tests are in tests/integration/targets/.
"""

from pathlib import Path

import yaml


def load_yaml_file(path: Path) -> dict:
    """Load and parse a YAML file."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def get_role_path() -> Path:
    """Get the path to the gather role."""
    # This test file is in tests/unit/, role is at roles/gather/
    test_file = Path(__file__)
    collection_root = test_file.parent.parent.parent
    return collection_root / "roles" / "gather"


def test_argument_specs_exist() -> None:
    """Verify argument_specs.yml exists and is valid YAML."""
    specs_file = get_role_path() / "meta" / "argument_specs.yml"
    specs = load_yaml_file(specs_file)
    assert "argument_specs" in specs
    assert "main" in specs["argument_specs"]


def test_defaults_exist() -> None:
    """Verify defaults/main.yml exists and is valid YAML."""
    defaults_file = get_role_path() / "defaults" / "main.yml"
    defaults = load_yaml_file(defaults_file)
    assert defaults is not None


def test_fact_collection_parameters() -> None:
    """Validate fact collection parameters match specs."""
    specs_file = get_role_path() / "meta" / "argument_specs.yml"
    defaults_file = get_role_path() / "defaults" / "main.yml"

    specs = load_yaml_file(specs_file)
    defaults = load_yaml_file(defaults_file)

    options = specs["argument_specs"]["main"]["options"]

    # fact_inventory_package_manager
    assert options["fact_inventory_package_manager"]["default"] == "auto"
    assert options["fact_inventory_package_manager"]["type"] == "str"
    assert defaults["fact_inventory_package_manager"] == "auto"

    # fact_inventory_local_facts_dir
    assert (
        options["fact_inventory_local_facts_dir"]["default"] == "/etc/ansible/facts.d"
    )
    assert options["fact_inventory_local_facts_dir"]["type"] == "path"
    assert defaults["fact_inventory_local_facts_dir"] == "/etc/ansible/facts.d"

    # fact_inventory_facts_become
    assert options["fact_inventory_facts_become"]["default"] is True
    assert options["fact_inventory_facts_become"]["type"] == "bool"
    assert defaults["fact_inventory_facts_become"] is True

    # fact_inventory_facts_subset
    assert options["fact_inventory_facts_subset"]["type"] == "list"
    assert defaults["fact_inventory_facts_subset"] == ["all", "!facter", "!ohai"]


def test_api_parameters() -> None:
    """Validate API endpoint parameters match specs."""
    specs_file = get_role_path() / "meta" / "argument_specs.yml"
    defaults_file = get_role_path() / "defaults" / "main.yml"

    specs = load_yaml_file(specs_file)
    defaults = load_yaml_file(defaults_file)

    options = specs["argument_specs"]["main"]["options"]

    # fact_inventory_api_server
    assert options["fact_inventory_api_server"]["default"] == "http://127.0.0.1:8000"
    assert options["fact_inventory_api_server"]["type"] == "str"
    assert defaults["fact_inventory_api_server"] == "http://127.0.0.1:8000"

    # fact_inventory_api_base_path
    assert options["fact_inventory_api_base_path"]["default"] == "/fact_inventory"
    assert options["fact_inventory_api_base_path"]["type"] == "str"
    assert defaults["fact_inventory_api_base_path"] == "/fact_inventory"

    # fact_inventory_api_endpoint
    assert options["fact_inventory_api_endpoint"]["default"] == "/api/v1/facts"
    assert options["fact_inventory_api_endpoint"]["type"] == "str"
    assert defaults["fact_inventory_api_endpoint"] == "/api/v1/facts"


def test_audit_parameters() -> None:
    """Validate audit file/directory parameters match specs."""
    specs_file = get_role_path() / "meta" / "argument_specs.yml"
    defaults_file = get_role_path() / "defaults" / "main.yml"

    specs = load_yaml_file(specs_file)
    defaults = load_yaml_file(defaults_file)

    options = specs["argument_specs"]["main"]["options"]

    # fact_inventory_audit_enabled
    assert options["fact_inventory_audit_enabled"]["default"] is False
    assert options["fact_inventory_audit_enabled"]["type"] == "bool"
    assert defaults["fact_inventory_audit_enabled"] is False

    # fact_inventory_audit_become
    assert options["fact_inventory_audit_become"]["default"] is True
    assert options["fact_inventory_audit_become"]["type"] == "bool"
    assert defaults["fact_inventory_audit_become"] is True

    # fact_inventory_audit_path
    assert (
        options["fact_inventory_audit_path"]["default"]
        == "/var/log/fact-inventory/payload.json"
    )
    assert options["fact_inventory_audit_path"]["type"] == "path"
    assert (
        defaults["fact_inventory_audit_path"] == "/var/log/fact-inventory/payload.json"
    )

    # fact_inventory_audit_owner
    assert options["fact_inventory_audit_owner"]["default"] == "root"
    assert options["fact_inventory_audit_owner"]["type"] == "str"
    assert defaults["fact_inventory_audit_owner"] == "root"

    # fact_inventory_audit_group
    assert options["fact_inventory_audit_group"]["default"] == "root"
    assert options["fact_inventory_audit_group"]["type"] == "str"
    assert defaults["fact_inventory_audit_group"] == "root"

    # fact_inventory_audit_mode
    assert options["fact_inventory_audit_mode"]["default"] == "0600"
    assert options["fact_inventory_audit_mode"]["type"] == "str"
    assert defaults["fact_inventory_audit_mode"] == "0600"

    # fact_inventory_audit_create_parent_dir
    assert options["fact_inventory_audit_create_parent_dir"]["default"] is True
    assert options["fact_inventory_audit_create_parent_dir"]["type"] == "bool"
    assert defaults["fact_inventory_audit_create_parent_dir"] is True

    # fact_inventory_audit_dir_owner
    assert options["fact_inventory_audit_dir_owner"]["default"] == "root"
    assert options["fact_inventory_audit_dir_owner"]["type"] == "str"
    assert defaults["fact_inventory_audit_dir_owner"] == "root"

    # fact_inventory_audit_dir_group
    assert options["fact_inventory_audit_dir_group"]["default"] == "root"
    assert options["fact_inventory_audit_dir_group"]["type"] == "str"
    assert defaults["fact_inventory_audit_dir_group"] == "root"

    # fact_inventory_audit_dir_mode
    assert options["fact_inventory_audit_dir_mode"]["default"] == "0755"
    assert options["fact_inventory_audit_dir_mode"]["type"] == "str"
    assert defaults["fact_inventory_audit_dir_mode"] == "0755"
