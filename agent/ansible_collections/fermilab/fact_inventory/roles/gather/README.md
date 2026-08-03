# fermilab.fact_inventory.gather

Collects Ansible system facts, package facts, and local facts, then POSTs
them to the fact_inventory API. Optionally writes a local audit copy of the
payload and API response (best-effort, non-fatal).

## Why a role, not a module

This is orchestration (setup -> package_facts -> uri -> copy -> fail), not
management of a single idempotent resource, so it is built from stock
`ansible.builtin` modules rather than a custom Python module:

- Idempotency, check_mode, and retries are already handled correctly by
  `setup`, `package_facts`, `uri`, `copy`, and `file`.
  A custom module would re-implement this in Python for no benefit.
- `become` stays scoped per-task (only where root is actually needed),
  matching least-privilege intent.
  A monolithic module would need to replicate that internally.
- Anyone who knows `ansible.builtin` can read and modify this role. A
  custom module requires knowing `argument_spec`, `module_utils`, and
  `ansible-test` module conventions - a higher bar to hand off over a
  multi-decade lifespan / staff turnover.

## Task layout

`tasks/main.yml` only orchestrates; each phase lives in its own file so a
reader can jump straight to the concern they need without scanning one
large task list:

| File                      | Responsibility                                                         |
| ------------------------- | ---------------------------------------------------------------------- |
| `collect_facts.yml`       | `setup` + `package_facts`                                              |
| `build_payload.yml`       | Assemble the API payload via `set_fact`                                |
| `submit_facts.yml`        | POST to the fact_inventory API                                         |
| `write_audit_log.yml`     | Optional local audit copy (only run if `fact_inventory_audit_enabled`) |
| `validate_submission.yml` | Fail the play if and only if the API call failed                       |

`import_tasks` (static) is used rather than `include_tasks` (dynamic) since
none of these files are conditionally selected by name - static import
resolves fully at playbook-parse time, which is easier to reason about and
slightly cheaper across a large host count.

## Requirements

- ansible-core >= 2.10 (for collection-qualified role names)
- Python 3 on the target
- Network reachability from the target to the fact_inventory API
- Root privileges (e.g. `-K`, or a configured become method) for full
  fact detail; see `fact_inventory_facts_become` / `fact_inventory_audit_become`
  below if you want to run parts of this without privilege escalation

## Usage

    - hosts: all
      gather_facts: false
      roles:
        - fermilab.fact_inventory.gather

Or with `include_role` / `import_role` and per-call overrides:

    - hosts: all
      tasks:
        - name: Submit facts to a specific API server
          ansible.builtin.include_role:
            name: fermilab.fact_inventory.gather
          vars:
            fact_inventory_api_server: "https://inventory.example.com"
            fact_inventory_audit_enabled: true

Equivalent CLI patterns:

    # Gather facts locally with privilege escalation
    ansible-playbook -K -i 'localhost,' -c local site.yml

    # Target a specific API server
    ansible-playbook -K -e 'fact_inventory_api_server=https://fqdn' site.yml

    # Load overrides from a file
    ansible-playbook -K -e '@override_vars.yml' site.yml

    # Collect only specific fact subsets
    ansible-playbook -K -i 'localhost,' -c local \
      -e 'fact_inventory_facts_subset=["network","hardware"]' site.yml

    # Enable the audit file and use a custom API endpoint
    ansible-playbook -K -i 'localhost,' -c local \
      -e 'fact_inventory_api_server=https://inventory.example.com' \
      -e 'fact_inventory_audit_enabled=true' site.yml

## Variables

All variables are role defaults (lowest precedence, safely overridable
from group*vars/host_vars/-e) and use the `fact_inventory*` prefix - the
collection's domain, not just this one role - so a future sibling role in
this collection can share the same names without collision.

Deliberately flat rather than nested dicts: Ansible's default
`hash_behaviour` is `replace`, so a host_vars override of one key in a
nested dict silently drops its sibling keys. Flat names avoid that.

| Variable                                    | Default                                | Purpose                                  |
| ------------------------------------------- | -------------------------------------- | ---------------------------------------- |
| `fact_inventory_package_manager`            | `auto`                                 | `package_facts` manager                  |
| `fact_inventory_local_facts_dir`            | `/etc/ansible/facts.d`                 | Local facts (`ansible_local`) source dir |
| `fact_inventory_facts_become`               | `true`                                 | Privilege escalation for `setup`         |
| `fact_inventory_facts_subset`               | `["all", "!facter", "!ohai"]`          | `setup` gather_subset                    |
| `fact_inventory_api_server`                 | `http://127.0.0.1:8000`                | fact_inventory API host                  |
| `fact_inventory_api_base_path`              | `/fact_inventory`                      | API base path                            |
| `fact_inventory_api_endpoint`               | `/api/v1/facts`                        | API resource path                        |
| `fact_inventory_api_url`                    | computed from the three vars above     | Full submission URL                      |
| `fact_inventory_audit_enabled`              | `false`                                | Write a local audit copy                 |
| `fact_inventory_audit_become`               | `true`                                 | Privilege escalation for audit file ops  |
| `fact_inventory_audit_path`                 | `/var/log/fact-inventory/payload.json` | Audit file path                          |
| `fact_inventory_audit_owner/group/mode`     | `root` / `root` / `"0600"`             | Audit file ownership/perms               |
| `fact_inventory_audit_create_parent_dir`    | `true`                                 | Create audit file's parent dir           |
| `fact_inventory_audit_dir_owner/group/mode` | `root` / `root` / `"0755"`             | Audit dir ownership/perms                |

## Facts set by this role (not inputs)

- `fact_inventory_api_payload` - the payload sent to the API
- `fact_inventory_api_result` - the registered `uri` result

These are visible to later tasks in the same play (e.g. for custom
notifications) but are not meant to be set by the caller.

## Exit behavior

- Fails (non-zero) if the API submission does not return HTTP 201.
- Audit logging failures are captured with `failed_when: false` and never
  affect the role's exit status.

## Reviewing submitted results

- Local audit copy (if `fact_inventory_audit_enabled: true`): the path in
  `fact_inventory_audit_path`.
- Otherwise: query the fact_inventory API directly.
