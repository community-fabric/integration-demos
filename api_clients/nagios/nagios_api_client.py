"""
This NAGIOS API Client has been created and tested on NAGIOS XI 5.8.3 and 5.8.4
"""

from typing import List, Dict, Optional
import os

from httpx import Client


class NAGIOSClient(Client):
    def __init__(self, *vargs, token: Optional[str] = None, **kwargs):
        """
        Initialise a NAGIOSClient object.

        Sets properties:
        * base_url = IP Fabric instance provided in 'base_url' parameter, or the 'NAGIOS_URL' environment variable
        * token = Required credentials for the NAGIOS API calls or the 'NAGIOS_TOKEN' environment variable
        """
        try:
            env_url = os.environ["NAGIOS_URL"]
        except KeyError:
            env_url = ""

        try:
            assert kwargs.setdefault("base_url", env_url)
        except (AssertionError, KeyError):
            raise RuntimeError(f"base_url not provided or NAGIOS_URL not set")
        kwargs["base_url"] += "/nagiosxi/api/v1/"

        if not token:
            try:
                token = os.environ["NAGIOS_TOKEN"]
            except KeyError:
                raise RuntimeError(f"token not provided or NAGIOS_USER not set")

        super().__init__(*vargs, verify=False, **kwargs)
        self.credentials = "&apikey=" + token

    def hostgroup_list(self):
        """
        Method to fetch a list of hostgroups from Nagios.

        Takes no additional parameters.
        Returns a list of dictionaries in the form:
        [
            {
                "index": [not native] index in NAGIOS XI
                "instance_id": id in NAGIOS XI,
                "config_type": type of configuration,
                "hostgroup_object_id": Object ID of the hostgroup,
                "alias": alias of the hostgroup,
                "object_id": id of the object,
                "hostgroup_name": name of the hostgroup,
                "is_active": True is the hostgroup is active,
            }
        ]
        """
        endpoint = "objects/hostgroup?pretty=1" + self.credentials
        res = self.get(endpoint)
        res.raise_for_status()

        hostg_list = []
        count = 0
        for hostg_deet in res.json()["hostgroup"]:
            hostgroup = {
                "index": count,
                "instance_id": hostg_deet["instance_id"],
                "config_type": hostg_deet["config_type"],
                "hostgroup_object_id": hostg_deet["hostgroup_object_id"],
                "alias": hostg_deet["alias"],
                "object_id": hostg_deet["object_id"],
                "hostgroup_name": hostg_deet["hostgroup_name"],
                "is_active": hostg_deet["is_active"],
            }
            count = count + 1
            hostg_list.append(hostgroup)
        return hostg_list

    def create_hostgroup(self, site: str):
        """
        Create hostgroup in Nagios
        """
        endpoint = "config/hostgroup?pretty=1" + self.credentials
        try:
            alias = site.split(" ", 1)[0]
        except:
            alias = site
        payload = {
            "hostgroup_name": site,
            "alias": alias,
            "is_active": 1,
            "applyconfig": "1",
        }
        res = self.post(endpoint, data=payload)
        res.raise_for_status()


class NAGIOSSensor:
    def __init__(self, name: str, ipaddr: str, site: Optional[str] = ""):
        """
        Initialise a NAGIOSSensor object.

        Takes parameters:
        * name - [mandatory] a string containing the hostname for the sensor
        * ipaddr - [mandatory] a string containing the IP address of the sensor
        * site - [optional] site string, if not in Nagios, it will be created

        Sets properties:
        * id = created object ID
        """
        nagios = NAGIOSClient()
        endpoint = "config/host?pretty=1" + nagios.credentials

        # check if a hostgroup exists with this site name if not, we will create it
        createSite = False
        if site != "":
            for item in nagios.hostgroup_list():
                if site in item["hostgroup_name"]:
                    createSite = False
                    break
                else:
                    createSite = True

        if createSite:
            nagios.create_hostgroup(site)

        payload = {
            "host_name": name,
            "address": ipaddr,
            "hostgroups": site,
            "check_command": "check_ping\!3000,80%\!5000,100%",
            "max_check_attempts": 2,
            "check_period": "24x7",
            "contacts": "nagiosadmin",
            "notification_interval": 5,
            "notification_period": "24x7",
            "applyconfig": "1",
        }
        res = nagios.post(endpoint, data=payload)
        res.raise_for_status()
        nagios.close()
        self.name = name
        self.status = f"created: {res.json()}"

    def delete(self):
        """
        Deletes sensor object from NAGIOS
        """
        nagios = NAGIOSClient()
        endpoint = (
            "config/host/"
            + str(self.name)
            + "?pretty=1&applyconfig=1"
            + nagios.credentials
        )
        res = nagios.delete(endpoint)
        res.raise_for_status()
        nagios.close()
        self.status = f"deleted: {res.json()}"
