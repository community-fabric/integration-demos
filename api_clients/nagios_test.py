"""
Script to show sample use of ipf_api_client and nagios_api_client
"""

"""
export IPF_URL=""
export IPF_TOKEN=""
d=IPFDevice('L66EXR1')
d.hostname
d.ipaddr

export NAGIOS_URL=""
export NAGIOS_TOKEN=""
n=NAGIOSClient()
n.host_list()
n.hostgroup_list()
n.create_hostgroup("site")
s=NAGIOSHost(name=d.hostname,ipaddr=d.ipaddr,site=d.site)
s.delete()
"""
