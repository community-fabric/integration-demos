# api_clients directory
This directory contains API clients for use in IP Fabric integrations.  Subfolders are:

## centreon subdirectory

For centreon_api_client.py, a Centreon API client subclass of httpx. Test script is centreon_test.py
It takes the inventory from IP Fabric, and create the host in Centreon if not present, or update them if they are.

## nagios subdirectory

For nagios_api_client.py, a NAGIOS XI API client subclass of httpx. Test script is nagios_test.py

## nist_cve subdirectory

For nistcve_api_client.py, a NIST cvedetails.com API client subclass of httpx. Test script is vuln_ipf.py

## prtg subdirectory

For prtg_api_client.py, a PRTG API client subclass of httpx. Test script is prtg_test.py


