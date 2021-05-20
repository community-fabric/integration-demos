'''
Script to show sample use of ipf_api_client and prtg_api_client
'''
from ipf.ipf_api_client import IPFDevice,IPFClient
from prtg.prtg_api_client import PRTGSensor
from rich import print #Optional

'''
d=IPFDevice('L45R5')
d.hostname
d.ipaddr
d.snmpv2

s=PRTGSensor(name=d.hostname,ipaddr=d.ipaddr,snmpv2=d.snmpv2)
s.resume()
s.pause()
s.delete()
'''
