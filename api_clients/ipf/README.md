# ipf_api_client.py
This module contains an API Client for IP Fabric. It defines a class of object, subclass of the httpx client with some additional properties.

Example use: ipf = IPFClient(base_url='https://demoXX.ipfabric.io', token='XXXXXXXXXXXXX')

* base_url = IP Fabric instance provided in 'base_url' parameter, or the 'IPF_URL' environment variable
* headers = Required headers for the IP Fabric API calls - embeds the API token from the 'token' parameter or 'IPF_TOKEN' environment variable
* snapshot_id = IP Fabric snapshot ID to use by default for database actions - defaults to '$last'

Methods are defined as follows:

## snapshot_list ()
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

## fetch_tables (url, columns, filters, pagination, snapshot_id)
Method to fetch data from IP Fabric tables. D

Takes parameters to select:
* url - [mandatory] a string containing the API endpoint for the table to be queried
* columns - [mandatory] a list of strings describing which data is required as output
* filters - [optional] dictionary describing the table filters to be applied to the records (taken from IP Fabric table description)
* pagination - [optional] start and length of the "page" of data required
* snapshot_id - [optional] IP Fabric snapshot identifier to override the default defined at object initialisation

Returns JSON describing a dictionary containing the records required.
