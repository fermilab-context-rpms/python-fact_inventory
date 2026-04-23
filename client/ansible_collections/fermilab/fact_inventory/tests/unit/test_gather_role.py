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

    # fact_inventory_gather_package_manager
    assert options["fact_inventory_gather_package_manager"]["default"] == "auto"
    assert options["fact_inventory_gather_package_manager"]["type"] == "str"
    assert defaults["fact_inventory_gather_package_manager"] == "auto"

    # fact_inventory_gather_local_facts_dir
    assert (
        options["fact_inventory_gather_local_facts_dir"]["default"]
        == "/etc/ansible/facts.d"
    )
    assert options["fact_inventory_gather_local_facts_dir"]["type"] == "path"
    assert defaults["fact_inventory_gather_local_facts_dir"] == "/etc/ansible/facts.d"

    # fact_inventory_gather_facts_become
    assert options["fact_inventory_gather_facts_become"]["default"] is True
    assert options["fact_inventory_gather_facts_become"]["type"] == "bool"
    assert defaults["fact_inventory_gather_facts_become"] is True

    # fact_inventory_gather_facts_subset
    assert options["fact_inventory_gather_facts_subset"]["type"] == "list"
    assert defaults["fact_inventory_gather_facts_subset"] == ["all", "!facter", "!ohai"]


def test_api_parameters() -> None:
    """Validate API endpoint parameters match specs."""
    specs_file = get_role_path() / "meta" / "argument_specs.yml"
    defaults_file = get_role_path() / "defaults" / "main.yml"

    specs = load_yaml_file(specs_file)
    defaults = load_yaml_file(defaults_file)

    options = specs["argument_specs"]["main"]["options"]

    # fact_inventory_gather_api_server
    assert (
        options["fact_inventory_gather_api_server"]["default"]
        == "http://127.0.0.1:8000"
    )
    assert options["fact_inventory_gather_api_server"]["type"] == "str"
    assert defaults["fact_inventory_gather_api_server"] == "http://127.0.0.1:8000"

    # fact_inventory_gather_api_base_path
    assert (
        options["fact_inventory_gather_api_base_path"]["default"] == "/fact_inventory"
    )
    assert options["fact_inventory_gather_api_base_path"]["type"] == "str"
    assert defaults["fact_inventory_gather_api_base_path"] == "/fact_inventory"

    # fact_inventory_gather_api_endpoint
    assert options["fact_inventory_gather_api_endpoint"]["default"] == "/api/v1/facts"
    assert options["fact_inventory_gather_api_endpoint"]["type"] == "str"
    assert defaults["fact_inventory_gather_api_endpoint"] == "/api/v1/facts"

    # fact_inventory_gather_api_validate_certs
    assert options["fact_inventory_gather_api_validate_certs"]["default"] is True
    assert options["fact_inventory_gather_api_validate_certs"]["type"] == "bool"
    assert defaults["fact_inventory_gather_api_validate_certs"] is True

    # fact_inventory_gather_api_ca_path
    assert options["fact_inventory_gather_api_ca_path"]["type"] == "path"
    assert defaults["fact_inventory_gather_api_ca_path"] is None

    # fact_inventory_gather_api_expected_status_codes
    assert options["fact_inventory_gather_api_expected_status_codes"]["type"] == "list"
    assert (
        options["fact_inventory_gather_api_expected_status_codes"]["elements"] == "int"
    )
    assert defaults["fact_inventory_gather_api_expected_status_codes"] == [201]

    # fact_inventory_gather_api_url is a role output, not an input
    assert "fact_inventory_gather_api_url" not in options
    assert "fact_inventory_gather_api_url" not in defaults


def test_api_url_is_composed_by_role() -> None:
    """Verify collect_facts.yml registers the composed API URL."""
    tasks_file = get_role_path() / "tasks" / "collect_facts.yml"
    tasks = yaml.safe_load(tasks_file.read_text(encoding="utf-8"))
    assert tasks is not None

    set_facts = [t for t in tasks if "ansible.builtin.set_fact" in t]
    assert set_facts, "collect_facts.yml must register the API URL via set_fact"

    url_task = next(
        t
        for t in set_facts
        if "fact_inventory_gather_api_url" in t["ansible.builtin.set_fact"]
    )
    composition = url_task["ansible.builtin.set_fact"]["fact_inventory_gather_api_url"]
    for component in (
        "fact_inventory_gather_api_server",
        "fact_inventory_gather_api_base_path",
        "fact_inventory_gather_api_endpoint",
    ):
        assert component in composition


def test_audit_parameters() -> None:
    """Validate audit file/directory parameters match specs."""
    specs_file = get_role_path() / "meta" / "argument_specs.yml"
    defaults_file = get_role_path() / "defaults" / "main.yml"

    specs = load_yaml_file(specs_file)
    defaults = load_yaml_file(defaults_file)

    options = specs["argument_specs"]["main"]["options"]

    # fact_inventory_gather_audit_enabled
    assert options["fact_inventory_gather_audit_enabled"]["default"] is False
    assert options["fact_inventory_gather_audit_enabled"]["type"] == "bool"
    assert defaults["fact_inventory_gather_audit_enabled"] is False

    # fact_inventory_gather_audit_become
    assert options["fact_inventory_gather_audit_become"]["default"] is True
    assert options["fact_inventory_gather_audit_become"]["type"] == "bool"
    assert defaults["fact_inventory_gather_audit_become"] is True

    # fact_inventory_gather_audit_path
    assert (
        options["fact_inventory_gather_audit_path"]["default"]
        == "/var/log/fact-inventory/payload.json"
    )
    assert options["fact_inventory_gather_audit_path"]["type"] == "path"
    assert (
        defaults["fact_inventory_gather_audit_path"]
        == "/var/log/fact-inventory/payload.json"
    )

    # fact_inventory_gather_audit_owner
    assert options["fact_inventory_gather_audit_owner"]["default"] == "root"
    assert options["fact_inventory_gather_audit_owner"]["type"] == "str"
    assert defaults["fact_inventory_gather_audit_owner"] == "root"

    # fact_inventory_gather_audit_group
    assert options["fact_inventory_gather_audit_group"]["default"] == "root"
    assert options["fact_inventory_gather_audit_group"]["type"] == "str"
    assert defaults["fact_inventory_gather_audit_group"] == "root"

    # fact_inventory_gather_audit_mode
    assert options["fact_inventory_gather_audit_mode"]["default"] == "0600"
    assert options["fact_inventory_gather_audit_mode"]["type"] == "str"
    assert defaults["fact_inventory_gather_audit_mode"] == "0600"

    # fact_inventory_gather_audit_create_parent_dir
    assert options["fact_inventory_gather_audit_create_parent_dir"]["default"] is True
    assert options["fact_inventory_gather_audit_create_parent_dir"]["type"] == "bool"
    assert defaults["fact_inventory_gather_audit_create_parent_dir"] is True

    # fact_inventory_gather_audit_dir_owner
    assert options["fact_inventory_gather_audit_dir_owner"]["default"] == "root"
    assert options["fact_inventory_gather_audit_dir_owner"]["type"] == "str"
    assert defaults["fact_inventory_gather_audit_dir_owner"] == "root"

    # fact_inventory_gather_audit_dir_group
    assert options["fact_inventory_gather_audit_dir_group"]["default"] == "root"
    assert options["fact_inventory_gather_audit_dir_group"]["type"] == "str"
    assert defaults["fact_inventory_gather_audit_dir_group"] == "root"

    # fact_inventory_gather_audit_dir_mode
    assert options["fact_inventory_gather_audit_dir_mode"]["default"] == "0755"
    assert options["fact_inventory_gather_audit_dir_mode"]["type"] == "str"
    assert defaults["fact_inventory_gather_audit_dir_mode"] == "0755"


def test_no_log_parameters() -> None:
    """Validate no_log parameters match specs."""
    specs_file = get_role_path() / "meta" / "argument_specs.yml"
    defaults_file = get_role_path() / "defaults" / "main.yml"

    specs = load_yaml_file(specs_file)
    defaults = load_yaml_file(defaults_file)

    options = specs["argument_specs"]["main"]["options"]

    # fact_inventory_gather_suppress_collection_output
    assert (
        options["fact_inventory_gather_suppress_collection_output"]["default"] is False
    )
    assert options["fact_inventory_gather_suppress_collection_output"]["type"] == "bool"
    assert defaults["fact_inventory_gather_suppress_collection_output"] is False

    # fact_inventory_gather_suppress_audit_output
    assert options["fact_inventory_gather_suppress_audit_output"]["default"] is True
    assert options["fact_inventory_gather_suppress_audit_output"]["type"] == "bool"
    assert defaults["fact_inventory_gather_suppress_audit_output"] is True

    # fact_inventory_gather_suppress_submit_output
    assert options["fact_inventory_gather_suppress_submit_output"]["default"] is False
    assert options["fact_inventory_gather_suppress_submit_output"]["type"] == "bool"
    assert defaults["fact_inventory_gather_suppress_submit_output"] is False


def test_facts_filter_defaults() -> None:
    """Validate facts filter parameter matches specs and defaults."""
    specs_file = get_role_path() / "meta" / "argument_specs.yml"
    defaults_file = get_role_path() / "defaults" / "main.yml"

    specs = load_yaml_file(specs_file)
    defaults = load_yaml_file(defaults_file)

    options = specs["argument_specs"]["main"]["options"]

    assert options["fact_inventory_gather_facts_filter"]["type"] == "list"
    assert options["fact_inventory_gather_facts_filter"]["elements"] == "str"
    assert defaults["fact_inventory_gather_facts_filter"] == [
        "^env$",
        "^loadavg$",
        "^memfree_mb$",
        "^swapfree_mb$",
        "^default_ipv4$",
        "^default_ipv6$",
    ]


def test_url_normalization_strips_redundant_slashes() -> None:
    """Verify collect_facts.yml normalizes the API URL components."""
    tasks_file = get_role_path() / "tasks" / "collect_facts.yml"
    tasks = yaml.safe_load(tasks_file.read_text(encoding="utf-8"))

    url_task = next(
        t
        for t in tasks
        if "ansible.builtin.set_fact" in t
        and "fact_inventory_gather_api_url" in t["ansible.builtin.set_fact"]
    )
    composition = url_task["ansible.builtin.set_fact"]["fact_inventory_gather_api_url"]

    assert "regex_replace" in composition
    assert "fact_inventory_gather_api_server" in composition
    assert "fact_inventory_gather_api_base_path" in composition
    assert "fact_inventory_gather_api_endpoint" in composition
    assert (
        "reject('equalto', '')" in composition or 'reject("equalto", "")' in composition
    )
    assert "join('/')" in composition


def test_facts_filter_excludes_configured_keys() -> None:
    """Verify build_payload.yml filters ansible_facts with regex search."""
    tasks_file = get_role_path() / "tasks" / "build_payload.yml"
    tasks = yaml.safe_load(tasks_file.read_text(encoding="utf-8"))

    payload_task = next(
        t
        for t in tasks
        if "ansible.builtin.set_fact" in t
        and "fact_inventory_gather_api_payload" in t["ansible.builtin.set_fact"]
    )
    system_facts = payload_task["ansible.builtin.set_fact"][
        "fact_inventory_gather_api_payload"
    ]["system_facts"]

    assert "dict2items" in system_facts
    assert "rejectattr" in system_facts
    assert "fact_inventory_gather_facts_filter" in system_facts
    assert "'search'" in system_facts or "search" in system_facts
    assert "items2dict" in system_facts


def test_tasks_that_handle_payload_have_no_log() -> None:
    """Tasks that handle facts or API results must support no_log."""
    for task_file in ("collect_facts.yml", "build_payload.yml", "submit_facts.yml"):
        tasks = yaml.safe_load(
            (get_role_path() / "tasks" / task_file).read_text(encoding="utf-8")
        )
        for task in tasks:
            if "ansible.builtin.set_fact" in task or "ansible.builtin.uri" in task:
                assert "no_log" in task, f"{task_file} task should set no_log"


def test_submit_facts_uses_failed_when_false() -> None:
    """Submit task uses failed_when: false to allow validation in a later task."""
    tasks_file = get_role_path() / "tasks" / "submit_facts.yml"
    tasks = yaml.safe_load(tasks_file.read_text(encoding="utf-8"))

    uri_task = next(t for t in tasks if "ansible.builtin.uri" in t)
    assert "failed_when" in uri_task
    assert uri_task["failed_when"] is False
    assert "ignore_errors" not in uri_task


def test_submit_facts_passes_tls_options() -> None:
    """Submit task passes validate_certs and ca_path to uri."""
    tasks_file = get_role_path() / "tasks" / "submit_facts.yml"
    tasks = yaml.safe_load(tasks_file.read_text(encoding="utf-8"))

    uri_task = next(t for t in tasks if "ansible.builtin.uri" in t)
    uri_args = uri_task["ansible.builtin.uri"]
    assert "validate_certs" in uri_args
    assert "ca_path" in uri_args


def test_submit_facts_uses_expected_status_codes() -> None:
    """Submit task uses the configurable expected status code list."""
    tasks_file = get_role_path() / "tasks" / "submit_facts.yml"
    tasks = yaml.safe_load(tasks_file.read_text(encoding="utf-8"))

    uri_task = next(t for t in tasks if "ansible.builtin.uri" in t)
    uri_args = uri_task["ansible.builtin.uri"]
    assert "status_code" in uri_args
    assert "fact_inventory_gather_api_expected_status_codes" in str(
        uri_args["status_code"]
    )


def test_validate_submission_checks_expected_status_codes() -> None:
    """Validation task fails when the response status is not in the expected list."""
    tasks_file = get_role_path() / "tasks" / "validate_submission.yml"
    tasks = yaml.safe_load(tasks_file.read_text(encoding="utf-8"))

    fail_task = next(t for t in tasks if "ansible.builtin.fail" in t)
    condition = str(fail_task["when"])
    assert "status" in condition
    assert "fact_inventory_gather_api_expected_status_codes" in condition
