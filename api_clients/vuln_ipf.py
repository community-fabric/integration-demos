from ipf.ipf_api_client import IPFClient
from nist_cve.nistcve_api_client import NistCVECheck


def main():
    print("Fetching IP Fabric inventory")
    ipf = IPFClient()
    devs = ipf.inventory.devices.all(columns=['hostname', 'vendor', 'family', 'version'],
                                     filters={"siteName": ["like", "L35"]})
    fetched_cves = dict()
    screen = True
    file = 'cve.csv'

    if file:
        f = open(file, "w")
        f.write("'hostname','vendor','family','version','number','CVE list'\n")

    for dev in devs:
        try:  # check to see if CVE list been pulled for combination of vendor, platform, version beforec

            cves = fetched_cves[(dev['vendor'], dev['family'], dev['version'])]
        except KeyError:  # if not, fetch up to the first 20 CVEs from NIST
            print(
                'CVEs not fetched before - requesting ' + str((dev['vendor'], dev['family'], dev['version'])) + ' ...')

            try:
                res = NistCVECheck(dev['vendor'], dev['family'], dev['version'])
                fetched_cves.update({(dev['vendor'], dev['family'], dev['version']): res.list})
                cves = res.list
            except:
                res = None
                cves = list()

        # output the result

        if screen:
            print(dev['hostname'], dev['vendor'], dev['family'], dev['version'])
            print(f'    No of CVEs: {len(cves)}')
            for c in res.list:
                print('        ', c)

        if file:
            f.write("'" + dev['hostname'] + "','" + dev['vendor'] + "','")
            if dev['family']:
                f.write(dev['family'] + "','")
            else:
                f.write("','")
            f.write(dev['version'] + "','" + str({len(cves)}))
            for c in res.list:
                f.write("','" + c)
            f.write("\n")

    if file:
        f.close()


if __name__ == "__main__":
    main()
