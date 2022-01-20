"""
2022-01-10 - v1.0
Script to show sample use of ipfabric python's module and centreon_api_client
"""

# from api.ipf_api_client import IPFDevice, IPFClient
from ipfabric import IPFClient
from centreon.centreon_api_client import CENTREONClient
from rich import print  # Optional


# Variables for Centreon
SERVICE_INTF_TRAFFIC = "snmp-intf-traffic"
SERVICE_INTF_TRAFFIC_TEMPLATE = "Net-Cisco-Standard-Traffic-Global-SNMP-custom"
HOST_TEMPLATE_CISCO = "Net-Cisco-Standard-SNMP-custom"
HOST_TEMPLATE_DEFAULT = "Network-Devices-Default"

c = CENTREONClient(
    base_url="https://server.centreon",
    username="user_api_access",
    password="secret_password",
)
ipf = IPFClient(
    base_url="https://server.ipfabric",
    token="ipfabric_api_token",
)

# Collect all devices from IP Fabric
devices_to_add = ipf.inventory.devices.all()
# devices_to_add = ipf.inventory.devices.all(filters={"siteName": ["like", "38"]}) # example of using a filter to only get some devices

add_device = True

if add_device:
    for dev in devices_to_add:
        snmp_payload = {
            "columns": ["hostname", "name"],
            "filters": {"hostname": ["like", dev["hostname"]]},
            "snapshot": ipf.snapshot_id,
        }
        # Identify the first snmp community listed in IP Fabric, if found
        try:
            first_snmp = ipf.post(
                url="/tables/management/snmp/communities", json=snmp_payload
            ).json()["data"][0]["name"]
        except IndexError:
            first_snmp = ""
        # let's create the host
        c.create_host(
            dev["hostname"],  # Host
            "",  # Alias
            dev["loginIp"],  # IP Address
            dev["siteName"],  # Hostgroup
            HOST_TEMPLATE_CISCO if dev["vendor"] == "cisco" else HOST_TEMPLATE_DEFAULT,  # different template for Cisco or other
            "Central",  # Poller
            first_snmp if first_snmp != "" else "",  # [Optional] SNMP community
            "2c" if first_snmp != "" else "",  # [Optional] SNMP version
        )

        # Adding the service to monitor interfaces, if the device is a Cisco device and a SNMP community exists
        if dev["vendor"] == "cisco" and first_snmp != "":
            c.add_host_to_service(
                dev["hostname"], SERVICE_INTF_TRAFFIC, SERVICE_INTF_TRAFFIC_TEMPLATE
            )

print("\n##INFO## Applying new configuration")
c.apply_config()
c.close()

