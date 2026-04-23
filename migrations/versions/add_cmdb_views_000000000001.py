"""Add comprehensive CMDB views for fact_inventory JSONB data.

Revision ID: 000000000001
Revises: 000000000000

PostgreSQL-only. Creates decomposed views for convenient access to host,
network, hardware, and OS data from fact_inventory JSONB columns:

Network views:
  1. cmdb_host_interfaces: All interfaces with basic metadata
  2. cmdb_host_interface_ipv4_addresses: IPv4 addresses per interface
  3. cmdb_host_interface_ipv6_addresses: IPv6 addresses per interface

Hardware views:
  4. cmdb_host_hardware: CPU, architecture, chassis, and hardware identification metadata
  5. cmdb_host_storage_devices: Storage device metadata with partition info

OS view:
  6. cmdb_host_os_info: Operating system metadata (kernel, distribution, machine_id)

All extracted columns are documented with JSON path references in docstrings.
"""

# ruff: noqa: E501

from alembic import op

__all__ = [
    "downgrade",
    "upgrade",
]

# Revision identifiers, used by Alembic.
revision = "000000000001"
down_revision = "000000000000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all CMDB views."""
    if op.get_context().dialect.name == "postgresql":
        # Network interface views
        _create_cmdb_host_interfaces()
        _create_cmdb_host_interface_ipv4_addresses()
        _create_cmdb_host_interface_ipv6_addresses()
        # Hardware and storage views
        _create_cmdb_host_hardware()
        _create_cmdb_host_storage_devices()
        # OS info view
        _create_cmdb_host_os_info()


def downgrade() -> None:
    """Drop all CMDB views"""
    op.execute("DROP VIEW IF EXISTS cmdb_host_os_info")
    op.execute("DROP VIEW IF EXISTS cmdb_host_storage_devices")
    op.execute("DROP VIEW IF EXISTS cmdb_host_hardware")
    op.execute("DROP VIEW IF EXISTS cmdb_host_interface_ipv6_addresses")
    op.execute("DROP VIEW IF EXISTS cmdb_host_interface_ipv4_addresses")
    op.execute("DROP VIEW IF EXISTS cmdb_host_interfaces")


# --- Network Interface Views ------------------------------------------------


def _create_cmdb_host_interfaces() -> None:
    """Create cmdb_host_interfaces view.

    Extracts all non-loopback interfaces from system_facts JSONB.
    One row per interface per client_address.

    Filtering:
      - Only extracts actual network interfaces (those with 'device' field)
      - Excludes metadata objects like default_ipv4, python, selinux, etc.
      - Excludes loopback interface (lo)

    JSON paths:
      - fqdn: system_facts.fqdn
      - device_type: system_facts.{interface_name}.type
      - mac_address: system_facts.{interface_name}.macaddress
      - is_active: system_facts.{interface_name}.active
      - mtu: system_facts.{interface_name}.mtu
    """
    sql = """
    CREATE VIEW cmdb_host_interfaces AS
    SELECT fi.id AS inventory_id
         , fi.client_address
         , (fi.system_facts ->> 'fqdn') AS fqdn
         , fi.updated_at AS last_updated_at
         , iface_key AS interface_name
         , (iface_data ->> 'type') AS device_type
         , NULLIF((iface_data ->> 'macaddress'), '')::macaddr AS mac_address
         , (iface_data ->> 'active')::boolean AS is_active
         , (iface_data ->> 'mtu')::integer AS mtu
      FROM fact_inventory AS fi
     CROSS JOIN LATERAL jsonb_each(fi.system_facts)
           AS ifaces(iface_key, iface_data)
     WHERE iface_data ? 'device'
       AND iface_key IS DISTINCT FROM 'lo'
    """
    op.execute(sql)


def _create_cmdb_host_interface_ipv4_addresses() -> None:
    """Create cmdb_host_interface_ipv4_addresses view.

    Extracts IPv4 addresses from interfaces. Handles both:
      - Structured objects: {"address": "10.0.0.1", "prefix": 24, ...}
      - Array of strings: ["10.0.0.1", "10.0.0.0/24", ...]

    One row per address per interface per client_address.
    Derives all metadata (netmask, prefix, network, broadcast) from inet cast.

    Filtering: Excludes 127.0.0.0/8 addresses (loopback already filtered at
    interface level). Preserves NULL addresses for auditing downstream filtering.

    JSON paths:
      - ipv4 data: system_facts.{interface_name}.ipv4
    """
    sql = """
    CREATE VIEW cmdb_host_interface_ipv4_addresses AS
    SELECT ci.inventory_id
         , ci.client_address
         , ci.fqdn
         , ci.last_updated_at
         , ci.interface_name
         , ci.device_type
         , ci.mac_address
         , ci.is_active
         , CASE
             WHEN addr_str IS NOT NULL
             THEN host(addr_str::inet)::inet
             ELSE NULL
           END AS ipv4_address
         , CASE
             WHEN addr_str IS NOT NULL
             THEN netmask(addr_str::inet)::inet
             ELSE NULL
           END AS ipv4_netmask
         , CASE
             WHEN addr_str IS NOT NULL
             THEN masklen(addr_str::inet)::smallint
             ELSE NULL
           END AS ipv4_prefix
         , CASE
             WHEN addr_str IS NOT NULL
             THEN network(addr_str::inet)::inet
             ELSE NULL
           END AS ipv4_network
         , CASE
             WHEN addr_str IS NOT NULL
             THEN broadcast(addr_str::inet)::inet
             ELSE NULL
           END AS ipv4_broadcast
      FROM cmdb_host_interfaces AS ci
     CROSS JOIN LATERAL (
           SELECT fi.system_facts -> ci.interface_name -> 'ipv4' AS ipv4_data
             FROM fact_inventory AS fi
            WHERE fi.id = ci.inventory_id
           ) AS ipv4_obj
      LEFT JOIN LATERAL (
        -- Handle structured object: {"address": "...", ...}
        SELECT (ipv4_obj.ipv4_data ->> 'address')::text AS addr_str
         WHERE jsonb_typeof(ipv4_obj.ipv4_data) = 'object'
        UNION ALL
        -- Handle array of strings: ["10.0.0.1", "10.0.0.0/24", ...]
        SELECT jsonb_array_elements(ipv4_obj.ipv4_data)::text
         WHERE jsonb_typeof(ipv4_obj.ipv4_data) = 'array'
    ) AS addr ON TRUE
    WHERE addr_str IS NULL
       OR NOT (addr_str::inet << inet '127.0.0.0/8')
    """
    op.execute(sql)


def _create_cmdb_host_interface_ipv6_addresses() -> None:
    """Create cmdb_host_interface_ipv6_addresses view.

    Extracts IPv6 addresses from interfaces. Handles both:
      - Array of objects: [{"address": "::1", "prefix": 128, ...}, ...]
      - Array of strings: ["::1", "fe80::1", ...]

    One row per address per interface per client_address.
    Derives prefix and network from inet cast (scope only from objects).

    Filtering: Excludes ::1 address (loopback interface already filtered at
    interface level). Preserves NULL addresses for auditing downstream filtering.

    JSON paths:
      - ipv6 data: system_facts.{interface_name}.ipv6
    """
    sql = """
    CREATE VIEW cmdb_host_interface_ipv6_addresses AS
    SELECT ci.inventory_id
         , ci.client_address
         , ci.fqdn
         , ci.last_updated_at
         , ci.interface_name
         , ci.device_type
         , ci.mac_address
         , ci.is_active
         , CASE
             WHEN addr_str IS NOT NULL
             THEN host(addr_str::inet)::inet
             ELSE NULL
           END AS ipv6_address
         , CASE
             WHEN addr_str IS NOT NULL
             THEN masklen(addr_str::inet)::smallint
             ELSE NULL
           END AS ipv6_prefix
         , scope AS ipv6_scope
       FROM cmdb_host_interfaces AS ci
      CROSS JOIN LATERAL (
            SELECT fi.system_facts -> ci.interface_name -> 'ipv6' AS ipv6_array
              FROM fact_inventory AS fi
             WHERE fi.id = ci.inventory_id
       ) AS ipv6_arr
       LEFT JOIN LATERAL (
         -- Handle array of objects: [{"address": "...", "scope": "..."}, ...]
         SELECT (elem ->> 'address')::text AS addr_str
              , (elem ->> 'scope')::text AS scope
           FROM jsonb_array_elements(ipv6_arr.ipv6_array) AS elem
          WHERE jsonb_typeof(elem) = 'object'
         UNION ALL
         -- Handle array of strings: ["::1", "fe80::1", ...]
         SELECT elem::text AS addr_str
              , NULL::text AS scope
           FROM jsonb_array_elements(ipv6_arr.ipv6_array) AS elem
          WHERE jsonb_typeof(elem) = 'string'
       ) AS addr ON TRUE
      WHERE addr_str IS NULL
         OR addr_str::inet IS DISTINCT FROM inet '::1'
    """
    op.execute(sql)


# --- Hardware Views --------------------------------------------------------


def _create_cmdb_host_hardware() -> None:
    """Create cmdb_host_hardware view.

    Extracts CPU, architecture, chassis, and hardware identification metadata per host.
    One row per client_address (host).

    CPU information:
      - Manufacturer: extracted from processor array (index 1)
      - Model name: extracted from processor array (index 2)
      - Socket count: physical socket count (typically 1)
      - Core count: physical cores per socket
      - Thread count: logical vCPUs

    Hardware information:
      - Product model: e.g., "NUC10i7FNH"
      - Board model: e.g., "NUC10i7FNB"
      - Product UUID/serial: hardware identification
      - Chassis form factor: e.g., "Mini PC", "Desktop", "Laptop", "Server"
      - System architecture: e.g., "x86_64", "aarch64"
      - Memory info (RAM in bytes)

    JSON paths:
      - board_name: system_facts.board_name
      - product_name: system_facts.product_name
      - product_uuid: system_facts.product_uuid
      - product_serial: system_facts.product_serial
      - form_factor: system_facts.form_factor
      - machine: system_facts.machine
      - processor: system_facts.processor
      - processor_count: system_facts.processor_count
      - processor_cores: system_facts.processor_cores
      - processor_vcpus: system_facts.processor_vcpus
    """
    sql = """
    CREATE VIEW cmdb_host_hardware AS
    SELECT fi.id AS inventory_id
         , fi.client_address
         , fi.updated_at AS last_updated_at
         , (fi.system_facts ->> 'board_name') AS board_model
         , (fi.system_facts ->> 'product_name') AS product_name
         , (fi.system_facts ->> 'product_uuid') AS product_uuid
         , (fi.system_facts ->> 'product_serial') AS product_serial
         , (fi.system_facts ->> 'form_factor') AS chassis_form_factor
         , (fi.system_facts ->> 'machine') AS system_arch
         , (fi.system_facts -> 'processor' ->> 1) AS cpu_manufacturer
         , (fi.system_facts -> 'processor' ->> 2) AS cpu_model_name
         , (fi.system_facts ->> 'processor_count')::integer AS cpu_socket_count
         , (fi.system_facts ->> 'processor_cores')::integer AS cpu_core_count
         , (fi.system_facts ->> 'processor_vcpus')::integer AS cpu_thread_count
         , ((fi.system_facts ->> 'memtotal_mb')::bigint * 1048576) AS ram_bytes
       FROM fact_inventory AS fi
    """
    op.execute(sql)


def _create_cmdb_host_storage_devices() -> None:
    """Create cmdb_host_storage_devices view.

    Extracts physical and virtual storage device metadata.
    One row per device per host. Includes partition metadata as JSONB.

    Device types:
      - Physical: sda, sdb, nvme0n1 (HDD/SSD)
      - Virtual: zram0, loop, dm-* (device mapper)
      - Removable: USB drives, memory cards

    Metadata:
      - Device name: e.g., "sda"
      - Model/Vendor/Serial: hardware identification
      - Size: derived from sectors * sector_size
      - Virtual: 1 = virtual device (zram, loop), 0 = physical
      - Removable: 1 = USB/removable, 0 = fixed
      - Fibre: 1 = Fibre Channel device (detected from device links)
      - WWN: World Wide Name for device identification
      - Partitions: aggregated as JSONB

    Size calculation uses sectors * sectorsize to derive bytes and GB.

    JSON paths:
      - devices: system_facts.devices
      - device metadata: system_facts.devices.{device_name}
      - partitions: system_facts.devices.{device_name}.partitions
    """
    sql = """
    CREATE VIEW cmdb_host_storage_devices AS
    SELECT fi.id AS inventory_id
         , fi.client_address
         , fi.updated_at AS last_updated_at
         , devices.device_name
         , (devices.device_data ->> 'model') AS device_model
         , (devices.device_data ->> 'vendor') AS device_vendor
         , (devices.device_data ->> 'serial') AS device_serial
         , (devices.device_data ->> 'wwn') AS device_wwn
         , CAST(
                 (
                   (devices.device_data ->> 'sectors')::bigint * (devices.device_data ->> 'sectorsize')::integer
                 ) AS bigint
           ) AS device_size_bytes
         , CASE
             WHEN (devices.device_data ->> 'virtual') = '1' THEN true
             ELSE false
           END AS is_virtual
         , CASE
             WHEN (devices.device_data ->> 'removable') = '1' THEN true
             ELSE false
           END AS is_removable
         , CASE
             WHEN (
                 devices.device_data -> 'links' -> 'ids' IS NOT NULL
                 AND (devices.device_data -> 'links' ->> 'ids') ~ 'fc-.*|wwn-0x6'
             ) THEN true
             ELSE false
           END AS is_fibre
         , CASE
             WHEN (devices.device_data ? 'partitions')
                 AND devices.device_data -> 'partitions' != '{}'::jsonb
             THEN devices.device_data -> 'partitions'
             ELSE NULL::jsonb
           END AS partitions
       FROM fact_inventory AS fi
      CROSS JOIN LATERAL jsonb_each(fi.system_facts -> 'devices')
            AS devices(device_name, device_data)
      ORDER BY fi.id
             , fi.client_address
             , devices.device_name
    """
    op.execute(sql)


def _create_cmdb_host_os_info() -> None:
    """Create cmdb_host_os_info view.

    Extracts operating system and machine metadata per host.
    One row per client_address (host).

    Operating System Information:
      - os_name: Distribution name (Fedora, AlmaLinux, RedHat, etc.)
      - os_version: Full version string from distribution_version field

    Host metadata:
      - fqdn: Fully qualified domain name
      - machine_id: systemd machine ID
      - kernel: Kernel version

    JSON paths:
      - fqdn: system_facts.fqdn
      - machine_id: system_facts.machine_id
      - distribution: system_facts.distribution
      - distribution_major_version: system_facts.distribution_major_version
      - distribution_version: system_facts.distribution_version
      - kernel: system_facts.kernel
    """
    sql = """
    CREATE VIEW cmdb_host_os_info AS
    SELECT fi.id AS inventory_id
         , fi.client_address
         , fi.updated_at AS last_updated_at
         , (fi.system_facts ->> 'fqdn') AS fqdn
         , (fi.system_facts ->> 'machine_id') AS machine_id
         , (fi.system_facts ->> 'distribution') AS os_name
         , (fi.system_facts ->> 'distribution_version') AS os_version
         , (fi.system_facts ->> 'kernel') AS kernel
      FROM fact_inventory AS fi
     """
    op.execute(sql)
