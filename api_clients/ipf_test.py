"""
Script to show sample use of ipf_api_client
"""
from ipf.ipf_api_client import IPFClient
from ipf.ipf_device import IPFDevice

# this requires the variables IPF_URL and IPF_TOKEN to exists in the environment
ipf = IPFClient()

# Otherwise you can use:
# ipf=IPFClient(base_url="https://ipfabric.server", token="123qwe45ert67tyui")

print(ipf.snapshots)
print(ipf.inventory.devices.all(columns=['hostname', 'siteName', 'vendor']))
print(ipf.fetch_all('/tables/inventory/devices', columns=['hostname', 'siteName', 'vendor'])[0:5])

d = IPFDevice('L66EXR1')
print(d.ipaddr)
