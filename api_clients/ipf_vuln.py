from ipf.ipf_api_client import IPFDevice,IPFClient
from nist_cve.nistcve_api_client import NistCVECheck
import httpx
import json


def main():
    print("Fetching IP Fabric inventory")
    ipf=IPFClient()
    devs=ipf.fetch_table(url='tables/inventory/devices',columns=['hostname','vendor','family','version'],filters={"siteName":["like","L1"]})
    fetchedCVEs={}
    outputToScreen=True
    outputToFile='cve.csv'

    if outputToFile:
        f=open(outputToFile,"w")
        f.write ("'hostname','vendor','family','version','number','CVE list'\n")

    for dev in devs:
        try: #check to see if CVE list been pulled for combination of vendor, platform, version beforec

            CVEList=fetchedCVEs[(dev['vendor'],dev['family'],dev['version'])]
        except KeyError: #if not, fetch up to the first 20 CVEs from NIST
            print('CVEs not fetched before - requesting '+str((dev['vendor'],dev['family'],dev['version']))+' ...')

            try:
                res=NistCVECheck(dev['vendor'],dev['family'],dev['version'])
                fetchedCVEs.update({(dev['vendor'],dev['family'],dev['version']):res.list})
                CVEList=res.list
            except:
                res=None
                CVEList=[]

        #output the result
        noOfCVEs=len(CVEList)

        if outputToScreen:
            print (dev['hostname'],dev['vendor'],dev['family'],dev['version'])
            print ('    No of CVEs: ',noOfCVEs)
            for c in res.list:
                print ('        ',c)

        if outputToFile:
            f.write ("'"+dev['hostname']+"','"+dev['vendor']+"','")
            if dev['family']:
                f.write(dev['family']+"','")
            else:
                f.write("','")
            f.write(dev['version']+"','"+str(noOfCVEs))
            for c in res.list:
                f.write("','"+c)
            f.write ("\n")

    if outputToFile:
        f.close()

if __name__ == "__main__":
    main()