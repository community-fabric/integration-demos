# prtg_api_client.py
This module contains an API Client for PRTG up to and including v20.3. It defines two classes:

## class PRTGClient(base_url,username,password)

(Not really for general use) Subclass of the httpx client.

Example use: p = PRTGClient(base_url='http://XXXX',username='XXXX',password='XXXX')

* base_url - [optional] base URL for PRTG server - if none is provided will default to content of 'PRTG_URL' environment variable
* username - [optional] admin username for PRTG - defaults to content of 'PRTG_USER' environment variable
* password - [optional] admin password for PRTG - default is 'PRTG_PASS' enviromnent variable

## class PRTGSensor(name,ipaddr,snmpv3,templateid,groupid)

Example initialisation: s = PRTGSensor(name='XXX',ipaddr='XXX',snmpv2='XXX',templateid='XXX',groupid='XXX')

Creates a PRTG sensor using the parameters provided and puts it in "pause" state.

Takes parameters:
* name - [mandatory] a string containing the hostname for the sensor
* ipaddr - [mandatory] a string containing the IP address of the sensor
* snmpv2 - [optional] a string containing the SNMPv2 community string for the sensor
* templateid - [mandatory] sensor to duplicate 
* groupid - [mandatory] ID for group where sensor should be created

Sets properties:
* id = created object ID

### pause() method

Example use: s.pause()

Sets status of sensor as "paused"

### resume() method

Example use: s.resume()

Sets status of sensor as "resumed" and commences auto-discovery tasks

### delete() method

Example use: s.delete()

Deletes the sensor from the PRTG server