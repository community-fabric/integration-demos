'''
Script to show sample use of ipf_api_client
'''
from ipf_api_client import IPFClient, IPFDevice
from rich import print #Optional

ipf=IPFClient()
#print(ipf.snapshot_list())
#print(ipf.fetch_table('/tables/inventory/devices',columns=['hostname','siteName','vendor']))