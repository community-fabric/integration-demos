import os
import re
from collections import OrderedDict
from typing import Optional, Union
from urllib.parse import urljoin, urlparse
from json import loads
from ipf.ipf_models import Snapshot, Inventory

from httpx import Client as httpxClient


def check_format(func):
    """
    Checks to make sure api/v1/ is not in the URL and converts filters from json str to dict
    """
    def wrapper(self, url, *args, **kwargs):
        if "filters" in kwargs and isinstance(kwargs["filters"], str):
            kwargs["filters"] = loads(kwargs["filters"])
        path = urlparse(url or kwargs["url"]).path
        url = path.split('v1/')[1] if 'v1/' in path else path
        return func(self, url, *args, **kwargs)
    return wrapper


class IPFClient(httpxClient):
    def __init__(
            self,
            base_url: Optional[str] = None,
            token: Optional[str] = None,
            snapshot_id: str = "$last",
            *vargs,
            **kwargs
    ):
        """
        Initializes the IP Fabric Client
        :param base_url: str: IP Fabric instance provided in 'base_url' parameter, or the 'IPF_URL' environment variable
        :param token: str: API token or 'IPF_TOKEN' environment variable
        :param snapshot_id: str: IP Fabric snapshot ID to use by default for database actions - defaults to '$last'
        :param vargs: list: List to pass to httpx
        :param kwargs: dict: Keyword args to pass to httpx
        """
        try:
            base_url = urljoin(base_url or os.environ["IPF_URL"], "api/v1/")
        except KeyError:
            raise RuntimeError(f"IP Fabric base_url not provided or IPF_URL not set")

        try:
            token = token or os.environ["IPF_TOKEN"]
        except KeyError:
            raise RuntimeError(f"IP Fabric token not provided or IPF_TOKEN not set")

        super().__init__(base_url=base_url, *vargs, **kwargs)
        self.headers.update({'Content-Type': 'application/json', 'X-API-Token': token})

        # Request IP Fabric for the OS Version, by doing that we are also ensuring the token is valid
        self.os_version = self.fetch_os_version()
        self.snapshots = self.get_snapshots()
        self.snapshot_id = snapshot_id
        self.inventory = Inventory(self)

    @property
    def snapshot_id(self):
        return self._snapshot_id

    @snapshot_id.setter
    def snapshot_id(self, snapshot_id):
        snapshot_id = "$last" if not snapshot_id else snapshot_id
        if snapshot_id not in self.snapshots:
            # Verify snapshot ID is valid
            raise ValueError(f"##ERROR## EXIT -> Incorrect Snapshot ID: '{snapshot_id}'")
        else:
            self._snapshot_id = self.snapshots[snapshot_id].id

    def fetch_os_version(self):
        """
        Gets IP Fabric version to ensure token is correct
        :return: str: IP Fabric version
        """
        res = self.get(url="os/version")
        if not res.is_error:
            try:
                return res.json()["version"]
            except KeyError as exc:
                raise ConnectionError(f"Error While getting the OS version, no Version available, message: {exc.args}")
        else:
            raise ConnectionRefusedError("Verify URL and Token are correct.")

    def get_snapshots(self):
        """
        Gets all snapshots from IP Fabric and returns a dictionary of {ID: Snapshot_info}
        :return: dict[str, Snapshot]: Dictionary with ID as key and dictionary with info as the value
        """
        res = self.get("/snapshots")
        res.raise_for_status()

        snap_dict = OrderedDict()
        for s in res.json():
            snap = Snapshot(**s)
            snap_dict[snap.id] = snap
            if snap.loaded:
                if "$lastLocked" not in snap_dict and snap.locked:
                    snap_dict["$lastLocked"] = snap
                if "$last" not in snap_dict:
                    snap_dict["$last"] = snap
                    continue
                if "$prev" not in snap_dict:
                    snap_dict["$prev"] = snap
        return snap_dict

    @check_format
    def fetch(
        self,
        url,
        columns: Optional[list[str]] = None,
        filters: Optional[Union[dict, str]] = None,
        limit: Optional[int] = 1000,
        start: Optional[int] = 0,
        snapshot_id: Optional[str] = None,
        reports: Optional[str] = None
    ):
        """
        Gets data from IP Fabric for specified endpoint
        :param url: str: Example tables/vlan/device-summary
        :param columns: list: Optional list of columns to return, None will return all
        :param filters: dict: Optional dictionary of filters
        :param limit: int: Default to 1,000 rows
        :param start: int: Starts at 0
        :param snapshot_id: str: Optional snapshot_id to override default
        :param reports: str: String of frontend URL where the reports are displayed
        :return: list: List of Dictionary objects.
        """

        payload = dict(
            columns=columns or self._get_columns(url),
            snapshot=snapshot_id or self.snapshot_id,
            pagination=dict(
                start=start,
                limit=limit
            )
        )
        if filters:
            payload["filters"] = filters
        if reports:
            payload["report"] = reports

        res = self.post(url, json=payload)
        res.raise_for_status()
        return res.json()["data"]

    @check_format
    def fetch_all(
            self,
            url: str,
            columns: Optional[list[str]] = None,
            filters: Optional[Union[dict, str]] = None,
            snapshot_id: Optional[str] = None,
            reports: Optional[str] = None
    ):
        """
        Gets all data from IP Fabric for specified endpoint
        :param url: str: Example tables/vlan/device-summary
        :param columns: list: Optional list of columns to return, None will return all
        :param filters: dict: Optional dictionary of filters
        :param snapshot_id: str: Optional snapshot_id to override default
        :param reports: str: String of frontend URL where the reports are displayed
        :return: list: List of Dictionary objects.
        """

        payload = dict(columns=columns or self._get_columns(url), snapshot=snapshot_id or self.snapshot_id)
        if filters:
            payload["filters"] = filters
        if reports:
            payload["report"] = reports

        return self._ipf_pager(url, payload)

    @check_format
    def query(self, url: str, payload: Union[str, dict], all: bool = True):
        """
        Submits a query, does no formating on the parameters.  Use for copy/pasting from the webpage.
        :param url: str: Example: https://demo1.ipfabric.io/api/v1/tables/vlan/device-summary
        :param payload: Union[str, dict]: Dictionary to submit in POST or can be JSON string (i.e. read from file).
        :param all: bool: Default use pager to get all results and ignore pagination information in the payload
        :return: list: List of Dictionary objects.
        """
        if isinstance(payload, str):
            payload = loads(payload)
        if all:
            return self._ipf_pager(url, payload)
        else:
            res = self.post(url, json=payload)
            res.raise_for_status()
            return res.json()["data"]

    def _get_columns(self, url: str):
        """
        Submits malformed payload and extracts column names from it
        :param url: str: API url to post
        :return: list: List of column names
        """
        r = self.post(url, json=dict(snapshot=self.snapshot_id, columns=["*"]))
        if r.status_code == 422:
            msg = r.json()["errors"][0]["message"]
            return [x.strip() for x in re.match(r'".*".*\[(.*)\]$', msg).group(1).split(',')]
        else:
            r.raise_for_status()

    def _ipf_pager(
            self,
            url: str,
            payload: dict,
            data: Optional[Union[list, None]] = None,
            limit: int = 10000,
            start: int = 0
    ):
        """
        Loops through and collects all the data from the tables
        :param url: str: Full URL to post to
        :param payload: dict: Data to submit to IP Fabric
        :param data: list: List of data to append subsequent calls
        :param start: int: Where to start for the data
        :return: list: List of dictionaries
        """
        data = data or list()

        payload["pagination"] = dict(
            limit=limit,
            start=start
        )
        r = self.post(url, json=payload)
        r.raise_for_status()
        r = r.json()
        data.extend(r['data'])
        if limit + start < r["_meta"]["count"]:
            self._ipf_pager(url, payload, data, start+limit)
        return data
