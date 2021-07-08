"""
Script to show sample use of ipf_api_client
"""
from ipf.ipf_api_client import IPFClient, IPFDevice
from rich import print  # Optional

# this requires the variables IPF_URL and IPF_TOKEN to exists in the environment
ipf = IPFClient()

# Otherwise you can use:
# ipf=IPFClient(base_url="https://ipfabric.server", token="123qwe45ert67tyui")

# print(ipf.snapshot_list())
# print(ipf.fetch_table('/tables/inventory/devices',columns=['hostname','siteName','vendor']))

# d=IPFDevice('L66EXR1')
# d.ipaddr
