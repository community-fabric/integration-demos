from httpx import Client, ReadTimeout


class NistCVEClient(Client):
    def __init__(self, *vargs, **kwargs):
        """
        Initialise a NistCVEClient object.
        
        Sets properties:
        * base_url = Standard NIST URL or URL provided in 'base_url' parameter
        """
        kwargs.setdefault('base_url', 'https://services.nvd.nist.gov/rest/json/cves/1.0')
        kwargs.setdefault('timeout', 30)
        super().__init__(*vargs, verify=False, **kwargs)


class NistCVECheck:
    def __init__(self, vendor: str, family: str, version: str):
        """
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
        """
        params = {
            'cpeMatchString': 'cpe:2.3:*:',
            'startIndex': 0,
            'resultsPerPage': 50
        }
        nist = NistCVEClient(timeout=15)

        # format check URL depending on vendor-specific info
        if vendor == 'juniper':
            params['cpeMatchString'] += vendor + ":" + family + ":" + version[:version.rfind('R') + 2].replace('R', ':r')
        elif vendor == 'paloalto':
            params['cpeMatchString'] += 'palo_alto' + ":" + family + ":" + version
        elif vendor == 'cisco':
            params['cpeMatchString'] += 'cisco:' + family + ':' + (version.replace('(', '.')).replace(')', '.')
        elif vendor == 'fortinet' and family == 'fortigate':
            params['cpeMatchString'] += 'fortinet:fortios:' + version.replace(',', '.')
        else:
            v = str(version).split(',')[0]
            params['cpeMatchString'] += str(vendor) + ":" + str(family) + ":" + v

        try:
            res = nist.get('', params=params)
            res.raise_for_status()
            nist.close()
            self.json = res.json()
            self.num = self.json['totalResults']
            self.cves = [i['cve']['CVE_data_meta']['ID'] for i in self.json['result']['CVE_Items']]

        except ReadTimeout:
            self.json = {'status': 'timeout'}
            self.num = 0
            self.cves = ['Timeout']
