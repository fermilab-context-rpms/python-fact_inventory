# Client

The Ansible client collection `fermilab.fact_inventory` collects system facts
from hosts and submits them to the fact_inventory API.

**This is not a standalone Python package.** It is an Ansible collection located
in the `client/` directory and must be used with Ansible.

## Location

The client collection is in `client/ansible_collections/fermilab/fact_inventory/`.

## Documentation

Please read the documentation in the client directory:

- Collection README: `client/ansible_collections/fermilab/fact_inventory/README.md`

For production deployment of the API service that receives these facts, see the
main docs in this `docs/` directory.

Example rpm at https://github.com/fermilab-context-rpms/fermilab-conf_fact-inventory
