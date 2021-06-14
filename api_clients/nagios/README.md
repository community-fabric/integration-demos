# nagios_api_client.py
This module contains an API Client for NAGIOS XI up to and including v20.3. It defines two classes:

## class NAGIOSClient(base_url,token)
(Not really for general use) Subclass of the httpx client.

Example use: n = NAGIOSClient(base_url='http://XXXX',token='XXXX')

* base_url = [optional] base URL for NAGIOS server - if none is provided will default to content of 'NAGIOS_URL' environment variable
* token = [optional] credentials for the NAGIOS API calls - if none is provided will default to content of 'NAGIOS_TOKEN' environment variable

## class NAGIOSSensor(name,ipaddr)

Example initialisation: s = NAGIOSSensor(name='XXX',ipaddr='XXX')

Creates a NAGIOS host using the parameters provided and start pinging to ensure reachability.

Takes parameters:
* name - [mandatory] a string containing the hostname for the sensor
* ipaddr - [mandatory] a string containing the IP address of the sensor

### delete() method

Example use: s.delete()

Deletes the host sensor from the NAGIOS server