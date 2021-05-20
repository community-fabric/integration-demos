from typing import List, Dict, Optional
import os

from httpx import Client as httpxClient

class IPFClient (httpxClient):
    def __init__ (self, *vargs, token : Optional[str] = None, snapshot_id = '$last', **kwargs):
        '''
        Initialise an IPFClient object.
        
        Sets properties:
        * base_url = IP Fabric instance provided in 'base_url' parameter, or the 'IPF_URL' environment variable
        * headers = Required headers for the IP Fabric API calls - embeds the API token from the 'token' parameter or 'IPF_TOKEN' environment variable
        * snapshot_id = IP Fabric snapshot ID to use by default for database actions - defaults to '$last'
        '''
        try:
            env_url = os.environ['IPF_URL']
        except KeyError:
            env_url = ''

        try:
            assert kwargs.setdefault('base_url',env_url)
        except AssertionError:
            raise RuntimeError(
                f'base_url not provided or IPF_URL not set'
            )
            
        kwargs['base_url']+='/api/v1'

        if not token:
            try:
                token = os.environ['IPF_TOKEN']
            except KeyError:
                raise RuntimeError(
                    f'token not provided or IPF_TOKEN not set'
                )

        super().__init__(*vargs, verify=False, **kwargs)
        self.headers['X-API-Token'] = token
        self.snapshot_id = snapshot_id


    def snapshot_list(self):
        '''
        Method to fetch a list of snapshots from the IPF instance opened in the API client.

        Takes no additional parameters.
        Returns a list of dictionaries in the form:
        [
            {
                'index': index in the IPF snapshot table,
                'id': snapshot id,
                'name': descriptive snapshot name,
                'count': number of devices discovered in snapshot,
                'state': unloaded or loaded
            }
        ]
        '''
        res=self.get('/snapshots')
        res.raise_for_status()

        snap_list=[]
        count=0
        for snapshot_deet in res.json():
            snap={'index':count,'id':snapshot_deet['id'],'name':snapshot_deet['name'],'count':snapshot_deet['totalDevCount'],'state':snapshot_deet['state']}
            count=count+1
            snap_list.append(snap)

        return snap_list
        

    def fetch_table(self, url, columns: List[str], filters: Optional[Dict] = None, pagination: Optional[Dict] = None, snapshot_id: Optional[str] = None):
        '''
        Method to fetch data from IP Fabric tables. D

        Takes parameters to select:
        * url - [mandatory] a string containing the API endpoint for the table to be queried
        * columns - [mandatory] a list of strings describing which data is required as output
        * filters - [optional] dictionary describing the table filters to be applied to the records (taken from IP Fabric table description)
        * pagination - [optional] start and length of the "page" of data required
        * snapshot_id - [optional] IP Fabric snapshot identifier to override the default defined at object initialisation

        Returns JSON describing a dictionary containing the records required.
        '''
        
        payload = dict(columns=columns,snapshot=snapshot_id or self.snapshot_id)
        if filters:
            payload['filters']=filters

        if pagination:
            payload['pagination']=pagination

        res=self.post(url,json=payload)
        res.raise_for_status()
        body=res.json()
        return body['data'] 
        
class IPFDevice():
    def __init__ (self, name: str):
        ipf=IPFClient()
        device=ipf.fetch_table('tables/inventory/devices',columns=['hostname','siteName','vendor','platform','loginIp'],filters={'hostname':['like',name]})
        self.hostname = device[0]['hostname']
        self.site = device[0]['siteName']
        self.vendor = device[0]['vendor']
        self.ipaddr = device[0]['loginIp']
        self.snmpv2 = 'public'


