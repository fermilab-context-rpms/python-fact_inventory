# Client

The Ansible client collection `fermilab.fact_inventory` collects system facts
from hosts and submits them to the fact_inventory API.

**This is not a standalone Python package.** It is an Ansible collection located
in the `agent/` directory and must be used with Ansible.

## Location

The client role is in `agent/ansible_collections/fermilab/fact_inventory/`.

## Documentation

Please read the documentation in the agent directory:

- Collection README: `agent/ansible_collections/fermilab/fact_inventory/README.md`
- Role README: `agent/ansible_collections/fermilab/fact_inventory/roles/gather/README.md`

For production deployment of the API service that receives these facts, see the
main docs in this `docs/` directory.
