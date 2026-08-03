# fermilab.fact_inventory

Ansible collection for the fact_inventory system: collects host facts and
submits them to a central fact_inventory API.

## Contents

- `roles/gather` - collects Ansible system/package/local facts and POSTs
  them to the fact_inventory API. See `roles/gather/README.md` for
  variables, usage, and design rationale.

## Install

Local/offline use (no Galaxy/Automation Hub required):

    mkdir -p ~/.ansible/collections/ansible_collections/fermilab
    cp -r fact_inventory ~/.ansible/collections/ansible_collections/fermilab/

Or build and install as a normal collection artifact:

    ansible-galaxy collection build
    ansible-galaxy collection install fermilab-fact_inventory-0.1.0.tar.gz

## Usage

    - hosts: all
      gather_facts: false
      roles:
        - fermilab.fact_inventory.gather

See `roles/gather/README.md` for override variables.

## Testing

    ansible-test sanity
    ansible-test integration gather_role

(Run from the collection root, i.e. this directory, with ansible-core
installed. Integration tests use a local mock HTTP server on 127.0.0.1 -
no real fact_inventory server or network access required. The test target
is named `gather_role`, not `gather`, because ansible-test resolves
`roles: [gather]` against the collection's actual role first when a target
shares the role's exact name - keep test targets and role names distinct.)

## License

This collection is primarily licensed and distributed as a whole under the AGPL v3.0 or later.

See LICENSE for the full text.
