from ipfabric import IPFClient
from nist_cve.nistcve_api_client import NistCVECheck


def fetch_cve(dev):
    # if not, fetch up to the first 50 CVEs from NIST
    print(
        'CVEs not fetched before - requesting ' + str((dev['vendor'], dev['family'], dev['version'])) + ' ...')
    try:
        res = NistCVECheck(dev['vendor'], dev['family'], dev['version'])
        return res.cves
    except:
        return ['Error']


def print_cve(f, dev, cves):
    f.write("'" + dev['hostname'] + "','" + dev['vendor'] + "','")
    if dev['family']:
        f.write(dev['family'] + "','")
    else:
        f.write("','")
    f.write(dev['version'] + "','" + str({len(cves)}))
    for c in cves:
        f.write("','" + c)
    f.write("\n")


def main(screen=True, file='cve.csv'):
    print("Fetching IP Fabric inventory")
    ipf = IPFClient()
    devs = ipf.inventory.devices.all(columns=['hostname', 'vendor', 'family', 'version'],
                                     filters={"siteName": ["like", "L35"]})
    fetched_cves = dict()

    if file:
        f = open(file, "w")
        f.write("'hostname','vendor','family','version','number','CVE list'\n")

    for dev in devs:
        combo = (dev['vendor'], dev['family'], dev['version'])
        if combo not in fetched_cves:
            fetched_cves[combo] = fetch_cve(dev)

        # output the result
        if screen:
            print(dev['hostname'], dev['vendor'], dev['family'], dev['version'])
            print(f'    No of CVEs: {len(fetched_cves[combo])}')
            for c in fetched_cves[combo]:
                print('        ', c)

        if file:
            print_cve(f, dev, fetched_cves[combo])

    if file:
        f.close()


if __name__ == "__main__":
    main()
