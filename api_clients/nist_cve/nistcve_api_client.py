from typing import List, Dict, Optional
import os

from httpx import Client

class NistCVEClient (Client):
    def __init__ (self, *vargs, **kwargs):
        '''
        Initialise a NistCVEClient object.
        
        Sets properties:
        * base_url = Standard NIST URL or URL provided in 'base_url' parameter
        '''

        try:
            assert kwargs.setdefault('base_url','http://services.nvd.nist.gov/rest/json/cves/1.0?cpeMatchString=cpe:2.3:*:')
        except (AssertionError, KeyError):
            raise RuntimeError(
                f'base_url not provided'
            )
        
        super().__init__(*vargs, verify=False, **kwargs)



class NistCVECheck():
    def __init__ (self, vendor: str, family: str, version: str):
        '''
        Initialise a NistCVECheck object.
        
        Takes parameters:
        * vendor - [mandatory] a string containing the vendor for the device to be checked
        * family - [mandatory] a string containing the family of the device to be checked
        * version - [mandatory] a string containing the software version of the device to be checked
        
        Sets properties:
        * checked = parameter string in NIST URL
        * json = NIST response in JSON format
        * list = list of CVE IDs
        * num = number of CVEs
        '''
        nist=NistCVEClient()

        #format check URL depending on vendor-specific info
        if vendor=='juniper':
            checkVersion=vendor+":"+family+":"+version[:version.rfind('R')+2].replace('R',':r')
        elif vendor=='paloalto':
            checkVersion='palo_alto'+":"+family+":"+version
        elif vendor=='cisco':
            checkVersion='cisco:'+family+':'+(version.replace('(','.')).replace(')','.')
        elif vendor=='fortinet' and family=='fortigate':
            checkVersion='fortinet:fortios:'+version.replace(',','.')
        else:
            v=str(version).split(',')[0]
            checkVersion=str(vendor)+":"+str(family)+":"+v

        try:
            res=nist.get(str(nist.base_url)+checkVersion)
            res.raise_for_status()
            nist.close()
            self.json=res.json()
            self.num=self.json['totalResults']
            self.list=[]
            for i in self.json['result']['CVE_Items']:
                self.list.append(i['cve']['CVE_data_meta']['ID'])
            
        except ReadTimeout:
            self.json={}
        
        self.checked=checkVersion

    