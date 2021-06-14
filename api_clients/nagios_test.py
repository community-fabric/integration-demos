"""
Script to show sample use of ipf_api_client and nagios_api_client
"""

from ipf.ipf_api_client import IPFDevice, IPFClient
from nagios.nagios_api_client import NAGIOSSensor, NAGIOSClient
from rich import print  # Optional

"""
export IPF_URL = ""
export IPF_TOKEN = ""
d=IPFDevice('L66EXR1')
d.hostname
d.ipaddr

export NAGIOS_URL=""
export NAGIOS_TOKEN=""
s=NAGIOSSensor(name=d.hostname,ipaddr=d.ipaddr)
s.delete()
"""
