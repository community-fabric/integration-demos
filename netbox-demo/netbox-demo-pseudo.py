
Webhook received

Add to queue


Main Loop

Check queue
If entry in queue, run update routine


Initialise

Connect to IPF
Check latest snapshot
Connect to NetBox
Open NetBox inventory
If there is any inventory:
    Update routine
else:
    Pull IPF inventory
    Write to Netbox
    Tag with IPF Snapshot id


Updates (parameters = latest IPF snapshot, NetBox snapshot)

#Fetch inventory changes and create report & web page
Connect to IPF
Diff inventory from IPF and NetBox snapshots
Create "report" list - temporary file and HTML
Push URL for report to Webex Teams

#Automatic update of Netbox interface data
Load interface data from NetBox snapshot
Load interface data from latest IPF snapshot
Diff them (for devices in Netbox only)
Write changes back to NetBox
Push list of changes to Webex Teams - URL for change log?


Process inventory updates (from web page)

Loop through temporary file of additions
If confirmed:
    Write to NetBox
    Log
else:
    Log

Loop through temporary file of removals
If confirmed:
    Write to NetBox
    Log
else:
    Log

Write log to WxT

