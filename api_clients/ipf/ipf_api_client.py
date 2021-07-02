from typing import List, Dict, Optional
import os
from httpx import Client as httpxClient


class IPFClient(httpxClient):
    def __init__(
        self, *vargs, token: Optional[str] = None, snapshot_id="$last", **kwargs
    ):
        """
        Initialise an IPFClient object.

        Sets properties:
        * base_url = IP Fabric instance provided in 'base_url' parameter, or the 'IPF_URL' environment variable
        * headers = Required headers for the IP Fabric API calls - embeds the API token from the 'token' parameter or 'IPF_TOKEN' environment variable
        * snapshot_id = IP Fabric snapshot ID to use by default for database actions - defaults to '$last'
        """
        try:
            env_url = os.environ["IPF_URL"]
        except KeyError:
            env_url = ""

        try:
            assert kwargs.setdefault("base_url", env_url)
        except AssertionError:
            raise RuntimeError(f"base_url not provided or IPF_URL not set")

        kwargs["base_url"] += "/api/v1"

        if not token:
            try:
                token = os.environ["IPF_TOKEN"]
            except KeyError:
                raise RuntimeError(f"token not provided or IPF_TOKEN not set")

        super().__init__(*vargs, verify=False, **kwargs)
        self.headers["X-API-Token"] = token
        self.snapshot_id = snapshot_id

    def snapshot_list(self):
        """
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
        """
        res = self.get("/snapshots")
        res.raise_for_status()

        snap_list = []
        count = 0
        for snapshot_deet in res.json():
            snap = {
                "index": count,
                "id": snapshot_deet["id"],
                "name": snapshot_deet["name"],
                "count": snapshot_deet["totalDevCount"],
                "state": snapshot_deet["state"],
            }
            count = count + 1
            snap_list.append(snap)

        return snap_list

    def site_list(
        self,
        filters: Optional[Dict] = None,
        pagination: Optional[Dict] = None,
        snapshot_id: Optional[str] = None,
    ):
        """
        Method to fetch the list of sites from the IPF instance opened in the API client, or the one entered

        Takes parameters to select:
        * filters - [optional] dictionary describing the table filters to be applied to the records (taken from IP Fabric table description)
        * pagination - [optional] start and length of the "page" of data required
        * snapshot_id - [optional] IP Fabric snapshot identifier to override the default defined at object initialisation

        Returns a list of dictionaries in the form:
        [
            {
                'siteName': descriptive site name,
                'id': site id,
                'siteKey': site Key,
                'devicesCount': number of devices in this site,
            }
        ]
        """
        sites = self.fetch_table(
            "tables/inventory/sites",
            columns=["siteName", "id", "siteKey", "devicesCount"],
            filters=filters,
            pagination=pagination,
            snapshot_id=snapshot_id,
        )
        return sites

    def device_list(
        self,
        filters: Optional[Dict] = None,
        pagination: Optional[Dict] = None,
        snapshot_id: Optional[str] = None,
    ):
        """
        Method to fetch the list of devices from the IPF instance opened in the API client, or the one entered

        Takes parameters to select:
        * filters - [optional] dictionary describing the table filters to be applied to the records (taken from IP Fabric table description)
        * pagination - [optional] start and length of the "page" of data required
        * snapshot_id - [optional] IP Fabric snapshot identifier to override the default defined at object initialisation

        Returns a list of dictionaries in the form:
        [
            {
                'hostname': device hostname,
                'siteName': name of the site where the device belongs,
                'vendor': vendor for this device,
                'platform': platform for this device,
                'loginIp': IP used for IP Fabric to login to this device
            }
        ]
        """
        devices = self.fetch_table(
            "tables/inventory/devices",
            columns=["hostname", "siteName", "vendor", "platform", "loginIp"],
            filters=filters,
            pagination=pagination,
            snapshot_id=snapshot_id,
        )
        return devices

    def fetch_table(
        self,
        url,
        columns: List[str],
        filters: Optional[Dict] = None,
        pagination: Optional[Dict] = None,
        snapshot_id: Optional[str] = None,
    ):
        """
        Method to fetch data from IP Fabric tables.

        Takes parameters to select:
        * url - [mandatory] a string containing the API endpoint for the table to be queried
        * columns - [mandatory] a list of strings describing which data is required as output
        * filters - [optional] dictionary describing the table filters to be applied to the records (taken from IP Fabric table description)
        * pagination - [optional] start and length of the "page" of data required
        * snapshot_id - [optional] IP Fabric snapshot identifier to override the default defined at object initialisation

        Returns JSON describing a dictionary containing the records required.
        """

        payload = dict(columns=columns, snapshot=snapshot_id or self.snapshot_id)
        if filters:
            payload["filters"] = filters

        if pagination:
            payload["pagination"] = pagination

        res = self.post(url, json=payload)
        res.raise_for_status()
        body = res.json()
        return body["data"]


class IPFDevice:
    def __init__(self, hostname: str):
        """
        Initialise an IPFDevice object.

        Sets properties:
        * hostname = hostname of the device we are looking for in IP Fabric.
        """
        ipf = IPFClient()

        device = ipf.fetch_table(
            "tables/inventory/devices",
            columns=["hostname", "siteName", "vendor", "platform", "loginIp"],
            filters={"hostname": ["like", hostname]},
        )
        if device != []:
            self.hostname = device[0]["hostname"]
            self.site = device[0]["siteName"]
            self.vendor = device[0]["vendor"]
            self.platform = device[0]["platform"]
            self.ipaddr = device[0]["loginIp"]
            self.snmpv2 = self.getSNMP(ipf, self.hostname)
            self.bestsnmpv2 = self.getBestSNMPComm(self.snmpv2)
            self.status = f"INFO - device '{self.hostname}' found"
        else:
            self.status = f"WARNING - device '{hostname}' not found"
        ipf.close()

    def getSNMP(self, ipf, name: str):
        """
        return a list of SNMP community configured for a specific device
        """
        snmp_list = ipf.fetch_table(
            "/tables/management/snmp/communities",
            ["hostname", "name", "authorization", "acl"],
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
