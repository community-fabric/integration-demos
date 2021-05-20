from typing import List, Dict, Optional
import os

from httpx import Client

class PRTGClient (Client):
    def __init__ (self, *vargs, username : Optional[str] = None, password : Optional[str] = None, **kwargs):
        '''
        Initialise a PRTGClient object.
        
        Sets properties:
        * base_url = IP Fabric instance provided in 'base_url' parameter, or the 'PRTG_URL' environment variable
        * credentials = Required credentials for the PRTG API calls - embeds the username from the 'username' parameter
            or 'PRTG_USER' environment variable and the password from the 'password' parameter or 'PRTG_PASS' variable
        '''

        try:
            assert kwargs.setdefault('base_url',os.environ['PRTG_URL'])
        except (AssertionError, KeyError):
            raise RuntimeError(
                f'base_url not provided or PRTG_URL not set'
            )
        kwargs['base_url']+='/api'

        if not username:
            try:
                username = os.environ['PRTG_USER']
            except KeyError:
                raise RuntimeError(
                    f'username not provided or PRTG_USER not set'
                )
        if not password:
            try:
                password = os.environ['PRTG_PASS']
            except KeyError:
                raise RuntimeError(
                    f'password not provided or PRTG_PASS not set'
                )

        super().__init__(*vargs, verify=False, **kwargs)
        self.credentials='&username='+username+'&password='+password


class PRTGSensor():
    def __init__ (self, name: str, ipaddr: str, snmpv2: Optional[str], templateid: Optional[int] = 7205, groupid: Optional[int] = 7204):
        '''
        Initialise a PRTGSensor object.
        
        Takes parameters:
        * name - [mandatory] a string containing the hostname for the sensor
        * ipaddr - [mandatory] a string containing the IP address of the sensor
        * snmpv2 - [optional] a string containing the SNMPv2 community string for the sensor
        * templateid - [mandatory] sensor to duplicate 
        * groupid - [mandatory] ID for group where sensor should be created

        Sets properties:
        * id = created object ID
        '''
        prtg=PRTGClient()
        endpoint='duplicateobject.htm?name='+name+'&host='+ipaddr+'&id='+str(templateid)+'&targetid='+str(groupid)+'&show=nohtmlencode'+prtg.credentials
        res=prtg.post(endpoint)
        res.raise_for_status()
        prtg.close()
        self.id=(res.url.full_path.split('id%3D')[1]).split('&')[0]
        self.status='paused'

    def pause(self):
        '''
        Sets status of sensor as "paused"
        '''
        prtg=PRTGClient()
        endpoint='pause.htm?id='+str(self.id)+'&action=0'+prtg.credentials
        res=prtg.post(endpoint)
        res.raise_for_status()
        prtg.close()
        self.status='paused'

    def resume(self):
        '''
        Sets status of sensor to "resumed"
        '''
        prtg=PRTGClient()
        endpoint='pause.htm?id='+str(self.id)+'&action=1'+prtg.credentials
        res=prtg.post(endpoint)
        res.raise_for_status()
        prtg.close()
        self.status='resumed'

    def delete(self):
        '''
        Deletes sensor object from PRTG
        '''
        prtg=PRTGClient()
        endpoint='deleteobject.htm?id='+str(self.id)+'&approve=1'+prtg.credentials
        res=prtg.post(endpoint)
        res.raise_for_status()
        prtg.close()
        self.status='deleted'