from ipfabric import IPFClient


class IPFDevice(IPFClient):
    def __init__(self, hostname: str, *vargs, **kwargs):
        """
        Initialise an IPFDevice object.
        Sets properties:
        * hostname = hostname of the device we are looking for in IP Fabric.
        """
        super().__init__(*vargs, **kwargs)

        device = self.inventory.devices.all(
            columns=["hostname", "siteName", "vendor", "platform", "loginIp"],
            filters={"hostname": ["like", hostname]},
        )
        if device:
            self.hostname = device[0]["hostname"]
            self.site = device[0]["siteName"]
            self.vendor = device[0]["vendor"]
            self.platform = device[0]["platform"]
            self.ipaddr = device[0]["loginIp"]
            self.snmpv2 = self.getSNMP(self.hostname)
            self.bestsnmpv2 = self.getBestSNMPComm(self.snmpv2)
            self.status = f"INFO - device '{self.hostname}' found"
        else:
            self.status = f"WARNING - device '{hostname}' not found"
        self.close()

    def getSNMP(self, name: str):
        """
        return a list of SNMP community configured for a specific device
        """
        snmp_list = self.query(
            "/tables/management/snmp/communities",
            columns=["hostname", "name", "authorization", "acl"],
            filters={"hostname": ["eq", name]},
        )
        return snmp_list

    def getBestSNMPComm(self, snmp_list):
        """
        return "the best" snmp community from a list of dictionnaries
        """
        # Select "the best" SNMP community from the list
        chosenComm = {"community": "", "auth": "", "acl": True}
        # Loop through all communities
        for comm in snmp_list:
            # And select the best match
            if chosenComm["community"] == "":
                replaceComm = comm["name"] != ""
            elif chosenComm["auth"] == "read-write" and chosenComm["acl"]:
                replaceComm = comm["authorization"] == "read-only" or not comm["acl"]
            elif chosenComm["auth"] == "read-write" and not chosenComm["acl"]:
                replaceComm = comm["authorization"] == "read-only"
            elif chosenComm["auth"] == "read-only" and chosenComm["acl"]:
                replaceComm = not comm["acl"]
            else:
                replaceComm = False

            if replaceComm:
                chosenComm["community"] = comm["name"]
                chosenComm["auth"] = comm["authorization"]
                if comm["acl"]:
                    chosenComm["acl"] = len(comm["acl"]) > 0
                else:
                    chosenComm["acl"] = False

        return chosenComm["community"]
