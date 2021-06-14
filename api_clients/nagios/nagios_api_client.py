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


class NAGIOSSensor:
    def __init__(self, name: str, ipaddr: str):
        """
        Initialise a NAGIOSSensor object.

        Takes parameters:
        * name - [mandatory] a string containing the hostname for the sensor
        * ipaddr - [mandatory] a string containing the IP address of the sensor

        Sets properties:
        * id = created object ID
        """
        nagios = NAGIOSClient()
        endpoint = "config/host?pretty=1" + nagios.credentials
        payload = {
            "host_name": name,
            "address": ipaddr,
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
