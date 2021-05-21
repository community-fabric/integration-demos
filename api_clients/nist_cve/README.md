# nistcve_api_client.py
This module contains an API Client for cvedetails.com - the NIST vulnerability database. It defines two classes:

## class NistCVEClient()

(Not really for general use) Subclass of the httpx client.

Example use: n = NistCVEClient(base_url='http://XXXX')

* base_url (optional) = Base URL for CVE service - if none is provided will default to "http://services.nvd.nist.gov/rest/json/cves/1.0"

## class NistCVECheck()

Example initialisation: c = NistCVECheck(vendor='XXX',family='XXX',version='XXX')

Takes parameters:
* vendor - (mandatory) a string containing the vendor for the device to be checked
* family - (mandatory) a string containing the family of the device to be checked
* version - (mandatory) a string containing the software version of the device to be checked
        
Returns an object with the properties:
* checked = parameter string in NIST URL
* json = NIST response in JSON format
* list = list of CVE IDs
* num = number of CVEs
