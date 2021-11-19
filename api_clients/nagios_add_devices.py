"""
Script to show simple use of ipf_api_client and nagios_api_client
"""
from ipfabric import IPFClient
from nagios.nagios_api_client import NAGIOSHost


def main():
    #creation of the IPFClient
    ipf = IPFClient()
    # collect all devices from IP Fabric using the filter
    filters = {"siteName": ["like", "45"]}
    devices = ipf.inventory.devices.all(filters=filters)
    # now we create in Nagios each device
    for device in devices:
        print(f" -- Adding device '{device['hostname']}' in site '{device['siteName']}'")
        NAGIOSHost(name=device["hostname"], ipaddr=device["loginIp"], site=device["siteName"])
    print(f"Job completed! {len(devices)} devices were added to hostgroup '{devices[0]['siteName']}'")


if __name__ == "__main__":
    main()
