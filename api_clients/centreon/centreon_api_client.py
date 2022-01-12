"""
2022-01-07 - v1.0
This CENTREON API Client has been created and tested on CENTREON 21.04.3
"""

from typing import Optional
import os
import sys
from httpx import Client
import httpx


class CENTREONClient(Client):
    def __init__(
        self,
        *vargs,
        username: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialises a CENTREONClient object.

        Sets properties:
        * base_url = IP Fabric instance provided in 'base_url' parameter, or the 'CENTREON_URL' environment variable
        * username = Required username for the CENTREON API calls or the 'CENTREON_USERNAME' environment variable
        * password = Required password for the CENTREON API calls or the 'CENTREON_PASSWORD' environment variable
        """
        try:
            env_url = os.environ["CENTREON_URL"]
        except KeyError:
            env_url = ""

        try:
            assert kwargs.setdefault("base_url", env_url)
        except (AssertionError, KeyError):
            raise RuntimeError(f"base_url not provided or CENTREON_URL not set")
        kwargs["base_url"] += "/centreon/api/"

        if not username:
            try:
                username = os.environ["CENTREON_USERNAME"]
            except KeyError:
                raise RuntimeError(
                    f"username not provided or CENTREON_USERNAME not set in env. variable"
                )
        if not password:
            try:
                password = os.environ["CENTREON_PASSWORD"]
            except KeyError:
                raise RuntimeError(
                    f"password not provided or CENTREON_PASSWORD not set in env. variable"
                )

        if username is None or password is None:
            sys.exit()

        super().__init__(*vargs, verify=False, **kwargs)

        # Update the headers with the Token, using username and password
        self.refreshCentreonToken(username=username, password=password)

        # Generic URL for Command Line API
        self.clapi_url = (
            str(self.base_url) + "index.php?action=action&object=centreon_clapi"
        )

    def refreshCentreonToken(self, username: str, password: str):
        """
        Refreshes the API Token for the specified user

        :param username: str: username for Centreon, it needs to have API access
        :param password: str: password for that user

        :return: Nothing, function will update the headers with the new token
        """
        self.centreon_token = self.getCentreonToken(
            username=username, password=password
        )
        self.headers = {
            "Content-Type": "application/json",
            "centreon-auth-token": self.centreon_token,
        }

    def getCentreonToken(self, username: str, password: str):
        """
        Gets the API Token for the specified user

        :param username: str: username for Centreon, it needs to have API access
        :param password: str: password for that user

        :return: Result: Returns the token as a string if successful
        """
        centreon_url = str(self.base_url) + "index.php?action=authenticate"
        centreon_payl = {
            "username": username,
            "password": password,
        }
        # not using self.post() due to an issue when the token had expired
        try:
            centreon_req = httpx.post(centreon_url, data=centreon_payl, headers=None)
            centreon_req.raise_for_status()
        except httpx.ConnectTimeout as exc:
            print(
                f"##ERROR## Type of error: {type(exc)} Check that URL '{self.base_url}' is reachable"
            )
            sys.exit(f"##ERROR## While requesting the token, message: {exc.args}")

        return centreon_req.json()["authToken"]

    def get_hosts_list(self):
        """
        Gets the list of hosts

        :return: Result: Returns the list of hosts
        """
        payload_hosts_list = {
            "action": "show",
            "object": "host",
        }
        try:
            hosts_list = self.post(self.clapi_url, json=payload_hosts_list)
            hosts_list = hosts_list.json()["result"]
        except KeyError as exc:
            print(f"##ERROR## Type of error: {type(exc)}")
            sys.exit(f"##ERROR## While getting the list of hosts, message: {exc.args}")
        return hosts_list

    def create_host(
        self,
        hostname: str,
        alias: str,
        ip_address: str,
        hostgroup: str,
        template: str,
        poller_name: str,
        snmp_community: Optional[str] = None,
        snmp_version: Optional[str] = None,
    ):
        """
        Creates a new host. If the host already exists, it will call the method
        to update the details with the provided information.

        :param hostname: str: name of the device
        :param alias: str: alternative name for the device
        :param ip_address: str: IP address of the device
        :param hostgroup: str: group in which to add the device
                               in IP Fabric, this would be the siteName
        :param template: str: template used to create the host
        :param poller_name: str: poller on which the host will be added
        :param snmp_community: str: Optional - SNMP community configured on the device
        :param snmp_version: str: Optional - needed if snmp community is provided

        :return: Nothing
        """

        ## Verify the hostgroup exists
        if not self.verify_hostgroup(hostgroup):
            self.create_hostgroup(hostgroup, hostgroup)

        payload_create_host = {
            "action": "add",
            "object": "host",
            "values": ";".join(
                [hostname, alias, ip_address, template, poller_name, hostgroup]
            ),
        }
        try:
            request_create_host = self.post(self.clapi_url, json=payload_create_host)
            # If information about snmp has been added, we will add details to the device
            if snmp_community and snmp_version:
                setparam_snmp_community_values = (
                    hostname + ";snmp_community;" + snmp_community
                )
                setparam_snmp_version_values = (
                    hostname + ";snmp_version;" + snmp_version
                )
                self.general_cmd("setparam", "host", setparam_snmp_community_values)
                self.general_cmd("setparam", "host", setparam_snmp_version_values)
        except KeyError as exc:
            print(f"##ERROR## Type of error: {type(exc)}")
            sys.exit(
                f"##ERROR## While getting creating the host '{hostname}', message: {exc.args}"
            )
        if request_create_host.is_error:
            # In case of error 409 saying the device already exists, we will update the device
            if (
                request_create_host.status_code == 409
                and "Object already exists" in request_create_host.text
            ):
                print(
                    f"##INFO## The device '{hostname}'' already exists. Updating with latest information..."
                )
                self.update_host(
                    hostname, alias, ip_address, snmp_community, snmp_version
                )
            else:
                print(
                    f"##ERR## the device '{hostname}' could not be created. Status code: {request_create_host.status_code}"
                )
                print(f"##ERR## Message: '{request_create_host.text}'")
        else:
            print(f"##INFO## the device '{hostname}' has been created!")

    def update_host(
        self,
        hostname: str,
        alias: str,
        ip_address: str,
        snmp_community: Optional[str] = None,
        snmp_version: Optional[str] = None,
    ):
        """
        Updates an existing host.

        :param hostname: str: name of the device
        :param alias: str: alternative name for the device
        :param ip_address: str: IP address of the device
        :param snmp_community: str: Optional - SNMP community configured on the device
        :param snmp_version: str: Optional - needed if snmp community is provided

        :return: Nothing
        """

        try:
            # Update alias
            request_update_host = self.general_cmd(
                "setparam", "host", hostname + ";alias;" + alias
            )
            # update ip address
            request_update_host = self.general_cmd(
                "setparam", "host", hostname + ";address;" + ip_address
            )
            if snmp_community and snmp_version:
                request_update_host = self.general_cmd(
                    "setparam", "host", hostname + ";snmp_community;" + snmp_community
                )
                request_update_host = self.general_cmd(
                    "setparam", "host", hostname + ";snmp_version;" + snmp_version
                )
            elif snmp_community or snmp_version:
                print(
                    "##WARNING## SNMP information incomplete, please provide snmp_community AND snmp_version. Host Alias and IP Address will be updated"
                )

        except KeyError as exc:
            print(f"##ERROR## Type of error: {type(exc)}")
            sys.exit(
                f"##ERROR## While updating the host '{hostname}', message: {exc.args}"
            )
        if request_update_host.is_error:
            print(
                f"##ERR## the device '{hostname}' could not be updated. Status code: {request_update_host.status_code}"
            )
            print(f"##ERR## Message: '{request_update_host.text}'")
        else:
            print(f"##INFO## the device '{hostname}' has been updated!")

    def delete_host(self, hostname: str):
        """
        Deletes the host provided

        :param hostname: str: name of the device to delete

        :return: Nothing
        """

        payload_delete_host = {"action": "del", "object": "host", "values": hostname}
        try:
            request_delete_host = self.post(self.clapi_url, json=payload_delete_host)
        except KeyError as exc:
            print(f"##ERROR## Type of error: {type(exc)}")
            sys.exit(
                f"##ERROR## While deleting the host '{hostname}', message: {exc.args}"
            )
        if request_delete_host.is_error:
            print(
                f"##ERR## the device '{hostname}' could not be deleted. Status code: {request_delete_host.status_code}"
            )
            print(f"##ERR## Message: '{request_delete_host.text}'")
        else:
            print(f"##INFO## the device '{hostname}' has been deleted!")

    def get_hostgroups_list(self):
        """
        Gets the list of hostgroups

        :return: Result: Returns the list of hostgroups
        """

        payload_hostgroups_list = {
            "action": "show",
            "object": "hg",
        }
        try:
            hostgroups_list = self.post(self.clapi_url, json=payload_hostgroups_list)
            hostgroups_list = hostgroups_list.json()["result"]
        except KeyError as exc:
            print(f"##ERROR## Type of error: {type(exc)}")
            sys.exit(
                f"##ERROR## While getting the list of hostgroups, message: {exc.args}"
            )
        return hostgroups_list

    def verify_hostgroup(self, name: str):
        """
        Boolean Function checking if the name provided is a name of an existing hostgroup

        :param name: str: name of the hostgroup we searching for in Centreon

        :return: Result: True or False
        """
        hostgroups_list = self.get_hostgroups_list()
        for hostgroup in hostgroups_list:
            if hostgroup["name"] == name:
                return True
        return False

    def create_hostgroup(self, name: str, alias: Optional[str] = ""):
        """
        Creates hostgroup based on the name provided

        :param name: str: name of the hostgroup to create

        :return: Nothing
        """

        payload_create_hostgroup = {
            "action": "add",
            "object": "hg",
            "values": ";".join([name, alias]),
        }
        try:
            request_create_hostgroup = self.post(
                self.clapi_url, json=payload_create_hostgroup
            )
        except KeyError as exc:
            print(f"##ERROR## Type of error: {type(exc)}")
            sys.exit(
                f"##ERROR## While creating the hostgroup '{name}', message: {exc.args}"
            )
        if request_create_hostgroup.is_error:
            print(
                f"##ERR## the hostgroup '{name}' could not be created. Status code: {request_create_hostgroup.status_code}"
            )
            print(f"##ERR## Message: '{request_create_hostgroup.text}'")
        else:
            print(f"##INFO## the hostgroup '{name}' has been created!")

    def get_services_list(self):
        """
        Gets the list of services

        :return: Result: Returns the list of services
        """
        payload_services_list = {
            "action": "show",
            "object": "service",
        }
        try:
            services_list = self.post(self.clapi_url, json=payload_services_list)
            services_list = services_list.json()["result"]
        except KeyError as exc:
            print(f"##ERROR## Type of error: {type(exc)}")
            sys.exit(
                f"##ERROR## While getting the list of services, message: {exc.args}"
            )
        return services_list

    def verify_service(self, description: str):
        """
        Checks if a service exists, and if it does, it returns the first host using this service

        :param description: str:

        :return: empty string if the service doesn't exist, or the name of a host using this service
        """
        services_list = self.get_services_list()
        for service in services_list:
            if service["description"] == description:
                return service["host name"]
        return ""

    def add_host_to_service(
        self, host: str, service_name: str, service_template: Optional[str] = ""
    ):
        """
        Add a host to a service in Centron. If the service doesn't exist it will be created with the
        template provided.

        :param host: str: Name of the host to add to a service
        :param service_name: str: name of the service
        :param service_template: str: Optional - if the service doesn't exist,
                                      it will be created using this template

        :return: Nothing
        """
        ## Verify the service exists
        service_host = self.verify_service(service_name)
        if service_host != "":
            self.general_cmd(
                "addhost", "service", ";".join([service_host, service_name, host])
            )
            print(f"##INFO## '{host}' is now assigned to the service '{service_name}'")
        elif service_template != "":
            self.general_cmd(
                "add", "service", ";".join([host, service_name, service_template])
            )
            print(
                f"##INFO## Service '{service_name}' has been created, using template '{service_template}'"
            )
        else:
            print(
                f"##WARNING## Service '{service_name}' can't be created as no template was provided"
            )

    def general_cmd(self, action, object, values: Optional[str] = ""):
        """
        General function to interact with Centreon API

        :param action: str: the action to perform
        :param object: str: the object on which the action will be performed
        :param values: str: Optional - values required for the action/object
                            value1;value2;value3

        :return: the json output of this request
        """
        if values == "":
            payload_general_cmd = {
                "action": action,
                "object": object,
            }
        else:
            payload_general_cmd = {
                "action": action,
                "object": object,
                "values": values,
            }
        try:
            request_general_cmd = self.post(self.clapi_url, json=payload_general_cmd)
        except KeyError as exc:
            print(f"##ERROR## Type of error: {type(exc)}")
            sys.exit(
                f"##ERROR## While trying '{action}' for the object '{object}', message: {exc.args}"
            )
        return request_general_cmd

    def get_pollers_list(self):
        """
        Gets the list of pollers

        :return: the list of pollers
        """
        try:
            pollers_list = self.general_cmd("show", "instance")
            pollers_list = pollers_list.json()["result"]
        except KeyError as exc:
            print(f"##ERROR## Type of error: {type(exc)}")
            sys.exit(f"##ERROR## While getting the list of hosts, message: {exc.args}")
        return pollers_list

    def apply_config(self):
        """
        Applies configuration to Centreon. After changing configuration in Centreon, this action needs
        to be performed for the changes to be taken into account.

        :return: Nothing
        """
        # Get the name of the first Poller
        general_poller_name = self.get_pollers_list()[0]["name"]
        # Apply new config
        self.general_cmd("applycfg", "", general_poller_name)
        # Restart Poller with the new config
        self.general_cmd("pollerrestart", "", "1")
        print(f"##INFO## New configuration has been applied to {general_poller_name}")
