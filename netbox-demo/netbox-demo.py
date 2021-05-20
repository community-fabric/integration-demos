from flask import Flask, request, Response, render_template
import concurrent.futures
#import logging
import queue
#import random
import threading
import time
import json
import requests
import pynetbox
from rich import print
from webexteamssdk import WebexTeamsAPI

app=Flask(__name__)

#Global variables
pipeline = queue.Queue(maxsize=10)

sNowServer='dev85455.service-now.com'
sNowUser='admin'
sNowPass='Ipfabricdem0!'
nbApiToken='af76ac335611fed9a0c0efcb8d3d2034cd05629b'
nbServer='10.0.9.73'
ipfApiToken='c920033ffd96e7dbd631478870e3a9d8'
ipfServer='demo6.ipf.ipfabric.io'
ipfBaseUrl='/api/v1/'
ipfHeaders={'X-API-Token':ipfApiToken,'Content-Type':'application/json'}
nbHeaders={'Authorization':'Token '+nbApiToken, 'Content-Type':'application/json'}
sNowHeaders={'Connection':'keep-alive','Content-Type':'application/json','Accept':'application/json'}
webhookServer='10.0.9.2' #'127.0.0.1'
firstTime=True

@app.route('/')
@app.route('/index')
def index():
    return 'Some random nonsense just to prove that the web server is working'

'''
@app.route('/added')
def added():
    return render_template('added.html')

@app.route('/removed')
def removed():
    return render_template('removed.html')
'''

@app.route('/webhook',methods=['POST'])
def webhook():
    #Take message from the /webhook URL and place it on the queue
    pipeline.put(request.json)
    return Response(status=200)

@app.route('/addform')
def addform():
    return render_template('add-form.j2')

@app.route('/decomform')
def decomform():
    return render_template('decom-form.j2')

@app.route('/nbadd',methods=['POST'])
def nbadd():
    l=[]
    addedDevs=[]
    addedDevStr=''

    f=request.form
    for key in f.keys():
        for value in f.getlist(key):
            if key[0:3]!='Togg':
                l.append ((key,value))
    
    for key in l:
        if key[1]=='yes':
            addedDevs.append(key[0])
            addedDevStr=addedDevStr+','+key[0]

    addedRegEx=addedDevStr[1:].replace(',','|')

    #Fetch last loaded snapshot info from IP Fabric
    snapEndpoint='https://'+ipfServer+ipfBaseUrl+'snapshots'
    snapRequest=requests.get(snapEndpoint,headers=ipfHeaders,verify=False)
    snaps=json.loads(snapRequest.text)
    lastLoaded=False
    for snap in snaps:
        if snap['state']=='loaded':
            if not lastLoaded:
                lastSnap=(snap['id'],snap['name'],time.strftime("%d-%m-%Y %H:%M:%S",time.localtime(snap['tsEnd']/1000)))
                lastLoaded=True
                break

    ipfDevs=fetchIpfInventory(ipfServer,ipfApiToken,ipfBaseUrl,lastSnap[0],ipfFilter='{"hostname": ["reg","'+addedRegEx+'"]}')
    ipfInts=fetchIpfInterfaces(ipfServer,ipfApiToken,ipfBaseUrl,lastSnap[0],ipfFilter='{"hostname": ["reg","'+addedRegEx+'"]}')

    #Update Netbox with added sites, vendors, platforms, devices and interfaces
    nbApi=pynetbox.api('https://'+nbServer,token=nbApiToken)
    nbApi.http_session.verify=False
    snapTag=createNetBoxSnapshotTag (nbApi, lastSnap[0], lastSnap[1], lastSnap[2])
    devListToNetBox(nbApi,ipfDevs,ipfInts,snapTag)

    #update SNow with devices
    devListToSNow(sNowServer,sNowUser,sNowPass,ipfDevs)

    notes=''
    for dev in addedDevs:
        notes=notes+dev+'    '
    webexTeamsRoom=WebexTeamsAPI()
    myWebexRoom='Y2lzY29zcGFyazovL3VzL1JPT00vNmUwYTQ2MzAtNTAzNC0xMWVhLTk2OTgtODMwZmVjZGNhOGM4'
    response=webexTeamsRoom.messages.create(roomId=myWebexRoom,text=time.ctime()+' - IP Fabric discovery - Devices added to Netbox\n\n'+notes)
    if response.id != None:
        print("[green]WxT  - Submitted new device message to Webex Teams room[/green]")

    f=open("templates/add-list.html","w")
    f.write('<h2>EMPTY</h2>')
    f.close()

    return Response(response="<h1>Successfully added "+addedDevStr[1:]+"</h1>",status=200)

@app.route('/nbremove',methods=['POST'])
def nbremove():
    l=[]
    removedDevs=[]

    f=request.form
    for key in f.keys():
        for value in f.getlist(key):
            if key[0:3]!='Togg':
                l.append ((key,value))
    
    for key in l:
        if key[1]=='yes':
            removedDevs.append(key[0])

    #Update Netbox with status inactive
    nbApi=pynetbox.api('https://'+nbServer,token=nbApiToken)
    nbApi.http_session.verify=False

    notes=''
    print("[yellow]NETBOX - decommissioning sites [/yellow] ",end="")
    for dev in removedDevs:
        nbDevice=nbApi.dcim.devices.get(name=dev)
        nbDevice.update({'status':'decommissioning'})
        notes=notes+dev+'    '
        print("[yellow].[/yellow]",end="")
    print("[yellow]DONE[/yellow]")

    webexTeamsRoom=WebexTeamsAPI()
    myWebexRoom='Y2lzY29zcGFyazovL3VzL1JPT00vNmUwYTQ2MzAtNTAzNC0xMWVhLTk2OTgtODMwZmVjZGNhOGM4'
    response=webexTeamsRoom.messages.create(roomId=myWebexRoom,text=time.ctime()+' - Devices decommissioned in Netbox\n\n'+notes)
    if response.id != None:
        print("[green]WxT  - Submitted decommissioning message to Webex Teams room[/green]")

    f=open("templates/decom-list.html","w")
    f.write('<label><h2>EMPTY</h2></label>')
    f.close()
    
    return Response(response="<h1>Successfully decommissioned</h1>",status=200)

'''
@app.route('/doadd')
def doadd():
    #Grab list of removed devices
    f=open("templates/added-list.html","r")
    addedDevStr=f.read().replace('</li><li>',',')
    f.close()

    for x in ("<li>","</li>","<ul>","</ul>"):
        addedDevStr=addedDevStr.replace(x,'')
    addedDevs=addedDevStr.split(',')
 
    addedRegEx=addedDevStr.replace(',','|')

    #Fetch last loaded snapshot info from IP Fabric
    snapEndpoint='https://'+ipfServer+ipfBaseUrl+'snapshots'
    snapRequest=requests.get(snapEndpoint,headers=ipfHeaders,verify=False)
    snaps=json.loads(snapRequest.text)
    lastLoaded=False
    for snap in snaps:
        if snap['state']=='loaded':
            if not lastLoaded:
                lastSnap=(snap['id'],snap['name'],time.strftime("%d-%m-%Y %H:%M:%S",time.localtime(snap['tsEnd']/1000)))
                lastLoaded=True
                break

    ipfDevs=fetchIpfInventory(ipfServer,ipfApiToken,ipfBaseUrl,lastSnap[0],ipfFilter='{"hostname": ["reg","'+addedRegEx+'"]}')
    ipfInts=fetchIpfInterfaces(ipfServer,ipfApiToken,ipfBaseUrl,lastSnap[0],ipfFilter='{"hostname": ["reg","'+addedRegEx+'"]}')

    #Update Netbox with added sites, vendors, platforms, devices and interfaces
    nbApi=pynetbox.api('https://'+nbServer,token=nbApiToken)
    nbApi.http_session.verify=False
    snapTag=createNetBoxSnapshotTag (nbApi, lastSnap[0], lastSnap[1], lastSnap[2])
    devListToNetBox(nbApi,ipfDevs,ipfInts,snapTag)

    notes=''
    for dev in addedDevs:
        notes=notes+dev+'    '
    webexTeamsRoom=WebexTeamsAPI()
    myWebexRoom='Y2lzY29zcGFyazovL3VzL1JPT00vNmUwYTQ2MzAtNTAzNC0xMWVhLTk2OTgtODMwZmVjZGNhOGM4'
    response=webexTeamsRoom.messages.create(roomId=myWebexRoom,text=time.ctime()+' - IP Fabric discovery - Devices added to Netbox\n\n'+notes)
    if response.id != None:
        print("[green]WxT  - Submitted new device message to Webex Teams room[/green]")

    f=open("templates/added-list.html","w")
    f.write('<label><H2>EMPTY</H2></label>')
    f.close()

    return Response(response="<h1>Successfully added</h1>",status=200)


@app.route('/doremove')
def doremove():
    #Grab list of removed devices
    f=open("templates/removed-list.html","r")
    removedDevStr=f.read().replace('</li><li>',',')
    f.close()

    for x in ("<li>","</li>","<ul>","</ul>"):
        removedDevStr=removedDevStr.replace(x,'')
    removedDevs=removedDevStr.split(',')

    #Update Netbox with status inactive
    nbApi=pynetbox.api('https://'+nbServer,token=nbApiToken)
    nbApi.http_session.verify=False

    notes=''
    print("[yellow]NETBOX - decommissioning sites [/yellow] ",end="")
    for dev in removedDevs:
        nbDevice=nbApi.dcim.devices.get(name=dev)
        nbDevice.update({'status':'decommissioning'})
        notes=notes+dev+'    '
        print("[yellow].[/yellow]",end="")
    print("[yellow]DONE[/yellow]")

    webexTeamsRoom=WebexTeamsAPI()
    myWebexRoom='Y2lzY29zcGFyazovL3VzL1JPT00vNmUwYTQ2MzAtNTAzNC0xMWVhLTk2OTgtODMwZmVjZGNhOGM4'
    response=webexTeamsRoom.messages.create(roomId=myWebexRoom,text=time.ctime()+' - Devices decommissioned in Netbox\n\n'+notes)
    if response.id != None:
        print("[green]WxT  - Submitted decommissioning message to Webex Teams room[/green]")

    f=open("templates/removed-list.html","w")
    f.write('<label><h2>EMPTY</h2></label>')
    f.close()

    return Response(response="<h1>Successfully decommissioned</h1>",status=200)
'''

def fetchIpfInventory(ipfServer,ipfApiToken,ipfBaseUrl,ipfSnapshotId,ipfFilter='{}'):
#Retrieve a list of devices in JSON format from IP Fabric and return it.

    ipfHeaders={'X-API-Token':ipfApiToken,'Content-Type':'application/json'}
    devIPFEndpoint='https://'+ipfServer+ipfBaseUrl+'tables/inventory/devices'
    devIPFReqData='{"columns": ["hostname","vendor","siteName","devType","snHw","loginIp","loginType","platform"],"filters":'+ipfFilter+',"snapshot":"'+ipfSnapshotId+'"}'
    devIPFRequest=requests.post(devIPFEndpoint,devIPFReqData,headers=ipfHeaders,verify=False)
    devDetails=json.loads(devIPFRequest.text)
    print("[green]IPF - fetched devices from latest snapshot - filter="+ipfFilter)
    return devDetails


def fetchIpfInterfaces(ipfServer,ipfApiToken,ipfBaseUrl,ipfSnapshotId,ipfFilter='{}'):
#Retrieve a list of interfaces in JSON format from IP Fabric and return it.

    ipfHeaders={'X-API-Token':ipfApiToken,'Content-Type':'application/json'}
    intIPFEndpoint='https://'+ipfServer+ipfBaseUrl+'tables/inventory/interfaces'
    intIPFFilter='{"columns": ["hostname","intName","dscr","l1","l2","reason"],"filters":'+ipfFilter+',"snapshot":"'+ipfSnapshotId+'"}'
    intIPFRequest=requests.post(intIPFEndpoint,intIPFFilter,headers=ipfHeaders,verify=False)
    intDetails=json.loads(intIPFRequest.text)
    print("[green]IPF - fetched interface details from latest snapshot - filter="+ipfFilter)
    return intDetails


def intListToNetBox(nbApi,ipfDevs,ipfSnapshotTag):
#Take a list of devices sourced from IP Fabric and upload it to NetBox, creating Vendor, Platform, Site and Device Type records as we go.
#Tag with the IPF Snapshot ID
    allOK=False

    try:
        allOK=(nbApi.status())!={}
    except:
        nbApi=pynetbox.api('https://'+nbServer,token=nbApiToken)
        nbApi.http_session.verify=False
        allOK=(nbApi.status())!={}

    if allOK:
        try:
            allVendors = set([])
            allDevTypes = set([])
            allPlatforms = set([])
            allSites = set([])

            for dev in ipfDevs['data']:
                allVendors.add(dev['vendor'])
                allDevTypes.add(dev['devType'])
                allPlatforms.add((dev['vendor'],dev['platform']))
                allSites.add(dev['siteName'])

            nbSiteList=ipfSitesToNetBox(allSites,nbApi,ipfSnapshotTag)
            nbManufacturers=ipfVendorsToNetBox(allVendors,nbApi)
            nbDeviceRoles=ipfDevTypesToNetBox(allDevTypes,nbApi)
            nbDeviceTypes=ipfPlatformsToNetBox(allPlatforms,nbApi,nbManufacturers)
            nbAllDevices=ipfInventoryToNetBox(ipfDevs,nbApi,nbDeviceTypes,nbDeviceRoles,nbSiteList,ipfSnapshotTag)
        except:
            print("[red]NetBox write process failed[/red]")

    return allOK

def ipfSitesToNetBox(allSites,nbApi,ipfSnapshotTag):
#Push list of sites from IP Fabric into NetBox. Return the list with IDs.
    nbSites={}
    allOK=False
    try:
        allOK=(nbApi.status())!={}
    except:
        nbApi=pynetbox.api('https://'+nbServer,token=nbApiToken)
        nbApi.http_session.verify=False
        allOK=(nbApi.status())!={}

    if allOK:
        print("[green]NETBOX - pushing sites [/green]",end="")
        #Loop through sites, create in NetBox if required, fetch IDs
        for site in allSites:
            if not(nbApi.dcim.sites.get(name=site)):
                siteAttributes={'name':site,'slug':site.lower(),'status': 'active','tags':[{'id':ipfSnapshotTag}]}
                createdSite=dict(nbApi.dcim.sites.create(siteAttributes))
                nbSites.update([(site,createdSite['id'])])
                print("[green].[/green]",end="")
            else:
                retrievedSite=dict(nbApi.dcim.sites.get(name=site))
                nbSites.update([(site,retrievedSite['id'])])
                print("[yellow].[/yellow]",end="")
        print("[green]DONE[/green]")

    return nbSites


def ipfVendorsToNetBox(allVendors,nbApi):
#Take a list of IP Fabric vendors and create Netbox Manufacturers.  Return the list created with IDs.
    nbManufacturers={}
    allOK=False
    try:
        allOK=(nbApi.status())!={}
    except:
        nbApi=pynetbox.api('https://'+nbServer,token=nbApiToken)
        nbApi.http_session.verify=False
        allOK=(nbApi.status())!={}

    if allOK:
        print("[green]NETBOX - creating manufacturers[/green]",end="")
        #Loop through vendors, create in NetBox if required, fetch IDs
        for vendor in allVendors:
            if not(nbApi.dcim.manufacturers.get(name=vendor)):
                manAttributes={'name':vendor,'slug':vendor.lower()}
                createdVendor=dict(nbApi.dcim.manufacturers.create(manAttributes))
                nbManufacturers.update([(vendor,createdVendor['id'])])
                print("[green].[/green]",end="")
            else:
                retrievedVendor=dict(nbApi.dcim.manufacturers.get(name=vendor))
                nbManufacturers.update([(vendor,retrievedVendor['id'])])
                print("[yellow].[/yellow]",end="")
        print("[green]DONE[/green]")

    return nbManufacturers


def ipfDevTypesToNetBox(allDevTypes,nbApi):
#Take a list of IP Fabric device types and create NetBox Device Roles. Return the list created with IDs.
    nbDeviceRoles={}
    allOK=False
    try:
        allOK=(nbApi.status())!={}
    except:
        nbApi=pynetbox.api('https://'+nbServer,token=nbApiToken)
        nbApi.http_session.verify=False
        allOK=(nbApi.status())!={}

    if allOK:    
        print("[green]NETBOX - creating device roles[/green]",end="")
        #Loop through device types, create in NetBox if required, fetch IDs
        for devType in allDevTypes:
            if not(nbApi.dcim.device_roles.get(name=devType)):
                roleAttributes={'name':devType,'slug':devType.lower(),'vm_role':False}
                createdRole=dict(nbApi.dcim.device_roles.create(roleAttributes))
                nbDeviceRoles.update([(devType,createdRole['id'])])
                print("[green].[/green]",end="")
            else:
                retrievedRole=dict(nbApi.dcim.device_roles.get(name=devType))
                nbDeviceRoles.update([(devType,retrievedRole['id'])])
                print("[yellow].[/yellow]",end="")
        print("[green]DONE[/green]")

    return nbDeviceRoles


def ipfPlatformsToNetBox(allPlatforms,nbApi,nbManufacturers):
#Take a list of vendor and platform pairs and create NetBox DeviceTypes using previously created manufacturer tags.  Return the list created.
    nbDeviceTypes={}
    allOK=False

    try:
        allOK=(nbApi.status())!={}
    except:
        nbApi=pynetbox.api('https://'+nbServer,token=nbApiToken)
        nbApi.http_session.verify=False
        allOK=(nbApi.status())!={}

    if allOK:
        print("[green]NETBOX - creating device types[/green]",end="")
        #Loop through device types, create in NetBox if required, fetch IDs
        for platform in allPlatforms:
            if not(nbApi.dcim.device_types.get(model=platform[1])):
                badChars=' /&'
                newSlug=platform[1].lower()
                for c in badChars:
                    newSlug=newSlug.replace(c,'-')
                devTypeAttributes={'manufacturer':nbManufacturers[platform[0]],'model':platform[1],'slug':newSlug}
                createdType=dict(nbApi.dcim.device_types.create(devTypeAttributes))
                nbDeviceTypes.update([(platform[1],createdType['id'])])
                print("[green].[/green]",end="")
            else:
                retrievedType=dict(nbApi.dcim.device_types.get(model=platform[1]))
                nbDeviceTypes.update([(platform[1],retrievedType['id'])])
                print("[yellow].[/yellow]",end="")
        print("[green]DONE[/green]")

    return nbDeviceTypes


def ipfInventoryToNetBox(ipfDevices,nbApi,nbDeviceTypes, nbDeviceRoles, nbSiteList, ipfSnapshotTag):
#Function to take an IP Fabric inventory and push it into the NetBox object in nbApi.
#Use nbDeviceTypes, nbDeviceRoles, nbSiteList and ipfSnapshotTag to provide linked data
#Return the list of NetBox devices and IDs

    nbInventory={}
    allOK=False

    try:
        allOK=(nbApi.status())!={}
    except:
        nbApi=pynetbox.api('https://'+nbServer,token=nbApiToken)
        nbApi.http_session.verify=False
        allOK=(nbApi.status())!={}

    if allOK:
        print("[green]NETBOX - fetching all devices for comparison[/green]")
        #Get existing NetBox devices
        nbExisting=nbApi.dcim.devices.all()
        for dev in nbExisting:
            devDict=dict(dev)
            nbInventory.update([(devDict['name'],devDict['id'])])

        print("[green]NETBOX - creating new devices[/green]",end="")
        #Loop through devices and create in Netbox if not already existing
        for dev in ipfDevices['data']:
            nbDevExists=False
            try:
                nbDevExists=(nbInventory[dev['hostname']]!=None)
            except KeyError:
                devAttributes={'name':dev['hostname'],'device_type':nbDeviceTypes[dev['platform']],'device_role':nbDeviceRoles[dev['devType']],'serial':dev['snHw'],'site':nbSiteList[dev['siteName']],'status':'active','primary_ip':dev['loginIp'],'tags':[ipfSnapshotTag]}
                createdDev=dict(nbApi.dcim.devices.create(devAttributes))
                nbInventory.update([(dev['hostname'],createdDev['id'])])
                print("[green].[/green]",end="")
            if nbDevExists:
                print("[yellow].[/yellow]",end="")
        print("[green]DONE[/green]")

    return nbInventory


def ipfInterfacesToNetBox(ipfInts,nbApi,nbAllDevices,ipfSnapshotTag):
#Take list of IPF interfaces and create interface records in NetBox using IDs from NetBox device list
    nbInterfaces={}
    allOK=False

    try:
        allOK=(nbApi.status())!={}
    except:
        nbApi=pynetbox.api('https://'+nbServer,token=nbApiToken)
        nbApi.http_session.verify=False
        allOK=(nbApi.status())!={}

    if allOK:
        print("[green]NETBOX - fetching interfaces for comparison (may take a while)[/green]")
        #Fetch existing Netbox interfaces
        nbExisting=nbApi.dcim.interfaces.all()
        for intf in nbExisting:
            intfDict=dict(intf)
            nbInterfaces.update([(intfDict['device']['name']+'::'+intfDict['name'],intfDict['id'])])

        print("[green]NETBOX - creating new interfaces[/green]",end="")
        #Loop through devices and create in Netbox if not already existing
        for intf in ipfInts['data']:
            nbIntfExists=False
            try:
            #if not(nbApi.dcim.interfaces.filter(device=nbAllDevices[intf['hostname']],name=intf['intName'])):
                nbIntfExists=(nbInterfaces[intf['hostname']+'::'+intf['intName']]!=None)
            except KeyError:
                if intf['l1']=='down' and intf['l2']=="down" and intf['reason']=='admin':
                    intfEnabled=False
                else:
                    intfEnabled=True

                if intf['dscr']==None:
                    intDesc='<empty>'
                else:
                    intDesc=intf['dscr']
                
                intfAttributes={'device':nbAllDevices[intf['hostname']],'name':intf['intName'],'label':intDesc,'enabled':intfEnabled,'type':'1000base-t','tags':[ipfSnapshotTag]}
                createdIntf=dict(nbApi.dcim.interfaces.create(intfAttributes))
                print("[green].[/green]",end="")
            if nbIntfExists:
                print("[yellow].[/yellow]",end="")
        print("[green]DONE[/green]")

    return allOK #nbInterfaces


def devListToSNow(sNowServer,sNowUser,sNowPass,ipfDevs,ipfSnapshotTag=''):
#Take a list of devices sourced from IP Fabric and upload it to sNow, matching Vendor and Site records as we go.
#Tag with the IPF Snapshot ID
    
    allOK=True

    if allOK:
        try:
            vendDict={}
            locDict={}
            locId=''
            print("[green]SNow - writing inventory ",end="")
            
            for dev in ipfDevs['data']:
                #Fetch SNow vendor and site lists if we don't already have them
                if (vendDict=={}):
                    vendEndpoint='https://'+ sNowServer + '/api/now/v1/table/core_company'
                    vendRequest=requests.get(vendEndpoint,auth=(sNowUser,sNowPass),headers=sNowHeaders)
                    vendDict=json.loads(vendRequest.text)

                if (locDict=={}):
                    locEndpoint='https://'+ sNowServer + '/api/now/v1/table/cmn_location'
                    locRequest=requests.get(locEndpoint,auth=(sNowUser,sNowPass),headers=sNowHeaders)
                    locDict=json.loads(locRequest.text)
  
                #loop through vendor list till we find a match
                testVendor=dev['vendor']
                for vendor in vendDict['result']:
                    if vendor['name'] == testVendor.capitalize():
                        vendId=vendor['sys_id']
                        break

                #loop through location list till we find a match
                testSite=dev['siteName']
                for loc in locDict['result']:
                    if loc['name'] == testSite.capitalize():
                        locId=loc['sys_id']
                        break

                #Create new ServiceNow inventory item
                deviceData={"attributes": {"sys_class_name": "cmdb_ci_netgear","discovery_source":"ServiceNow","manufacturer": vendId,"serial_number": dev['snHw'],"name": dev['hostname'],"ip_address": dev['loginIp']}}
                if locId !='':
                    deviceData['location']=locId
                deviceEndpoint='https://'+ sNowServer + '/api/now/v1/cmdb/instance/cmdb_ci_netgear'
                deviceRequest=requests.post(deviceEndpoint,auth=(sNowUser,sNowPass),headers=sNowHeaders,data=json.dumps(deviceData))
                print("[green].[/green]",end="")
            print("[green]DONE[/green]")    
        except:
            print("[red]ServiceNow write process failed[/red]")
            allOK=False

    return allOK
                        

def devListToNetBox(nbApi,ipfDevs,ipfInts,ipfSnapshotTag):
#Take a list of devices sourced from IP Fabric and upload it to NetBox, creating Vendor, Platform, Site and Device Type records as we go.
#Tag with the IPF Snapshot ID
    allOK=False

    try:
        allOK=(nbApi.status())!={}
    except:
        nbApi=pynetbox.api('https://'+nbServer,token=nbApiToken)
        nbApi.http_session.verify=False
        allOK=(nbApi.status())!={}

    if allOK:
        try:
            allVendors = set([])
            allDevTypes = set([])
            allPlatforms = set([])
            allSites = set([])

            for dev in ipfDevs['data']:
                allVendors.add(dev['vendor'])
                allDevTypes.add(dev['devType'])
                allPlatforms.add((dev['vendor'],dev['platform']))
                allSites.add(dev['siteName'])

            nbSiteList=ipfSitesToNetBox(allSites,nbApi,ipfSnapshotTag)
            nbManufacturers=ipfVendorsToNetBox(allVendors,nbApi)
            nbDeviceRoles=ipfDevTypesToNetBox(allDevTypes,nbApi)
            nbDeviceTypes=ipfPlatformsToNetBox(allPlatforms,nbApi,nbManufacturers)
            nbAllDevices=ipfInventoryToNetBox(ipfDevs,nbApi,nbDeviceTypes,nbDeviceRoles,nbSiteList,ipfSnapshotTag)
            nbAllInterfaces=ipfInterfacesToNetBox(ipfInts,nbApi,nbAllDevices,ipfSnapshotTag)
        except:
            print("[red]NetBox write process failed[/red]")

    return allOK


def fetchIpfSnapDiff(ipfServer,ipfBaseUrl,ipfApiToken,beforeSnapId,afterSnapId):
#Function to determine additions and removals to/from beforeSnapId

    diffEndpoint='https://'+ipfServer+ipfBaseUrl+'tables/management/changes/devices'
    diffFilter='{"columns": ["hostname","loginIp","sn"],"filters": {"and": [{"or": [{"status": ["eq","added"]}]}],"after": ["eq","'+afterSnapId+'"],"before": ["eq","'+beforeSnapId+'"]}}'
    addedDevs={"data":[],"_meta":{"limit":None,"start":0,"count":1,"size":0}}

    #Pause until IPF returns actual differences
    while len(addedDevs['data'])!=addedDevs['_meta']['count']:
        #if not, wait one second and try again!
        time.sleep(1)
        diffRequest=requests.post(diffEndpoint,diffFilter,headers=ipfHeaders,verify=False)
        addedDevs=json.loads(diffRequest.text)

    diffFilter='{"columns": ["hostname","loginIp","sn"],"filters": {"and": [{"or": [{"status": ["eq","removed"]}]}],"after": ["eq","'+afterSnapId+'"],"before": ["eq","'+beforeSnapId+'"]}}'
    removedDevs={"data":[],"_meta":{"limit":None,"start":0,"count":1,"size":0}}

    #Pause until IPF returns actual differences
    while len(removedDevs['data'])!=removedDevs['_meta']['count']:
        #if not, wait one second and try again!
        time.sleep(1)
        diffRequest=requests.post(diffEndpoint,diffFilter,headers=ipfHeaders,verify=False)
        removedDevs=json.loads(diffRequest.text)

    return addedDevs,removedDevs


def createNetBoxSnapshotTag (nbApi, snapId, snapName, snapTime):
#Create a tag in NetBox and return its ID for the IPF snapshot
    AllOK=False
    snapTag=-1
    
    try:
        allOK=(nbApi.status())!={}
    except:
        nbApi=pynetbox.api('https://'+nbServer,token=nbApiToken)
        nbApi.http_session.verify=False
        allOK=(nbApi.status())!={}

    if allOK:
        if not(nbApi.extras.tags.get(name='IPF-'+snapId)): 
            tagAttributes={'name':'IPF-'+snapId,'slug':snapId.lower(),'color':'03a9f4','description':'Discovered by IP Fabric -- Snapshot ID: '+snapId+' -- Snapshot Name: '+snapName+' -- Snapshot completed: '+snapTime}
            snapTag=dict(nbApi.extras.tags.create(tagAttributes))['id']
        else:
            snapTag=dict(nbApi.extras.tags.get(name='IPF-'+snapId))['id']

    return snapTag

def consumer(queue, event):
    #Pull message from queue and act on it

    while not event.is_set() or not queue.empty():
        #Lift the message off the queue
        message = queue.get()

        if message['type'] == 'snapshot':
            #If the message relates to snapshots, process it
            print('[blue]WEBHOOK > IPF SNAPSHOT '+message['status'].upper()+'[/blue]')
            
            if (message['status']=='completed') or (message['status']=='loaded'):
                #Fetch last and previous snapshots info from IP Fabric
                snapEndpoint='https://'+ipfServer+ipfBaseUrl+'snapshots'
                snapRequest=requests.get(snapEndpoint,headers=ipfHeaders,verify=False)
                snaps=json.loads(snapRequest.text)
                lastLoaded=False
                prevLoaded=False

                for snap in snaps:
                    if snap['state']=='loaded':
                        if not lastLoaded:
                            lastSnap=(snap['id'],snap['name'],time.strftime("%d-%m-%Y %H:%M:%S",time.localtime(snap['tsEnd']/1000)))
                            lastLoaded=True
                            print("[green]IPF - SNAPSHOT - Found lastLoaded ("+lastSnap[0]+","+lastSnap[1]+")[/green]")
                        elif not prevLoaded:
                            prevSnap=(snap['id'],snap['name'],time.strftime("%d-%m-%Y %H:%M:%S",time.localtime(snap['tsEnd']/1000)))
                            prevLoaded=True
                            print("[green]IPF - SNAPSHOT - Found prevLoaded ("+prevSnap[0]+","+prevSnap[1]+")[/green]")

                addedDevs, removedDevs = fetchIpfSnapDiff(ipfServer,ipfBaseUrl,ipfApiToken,prevSnap[0],lastSnap[0])

                al=open('templates/add-list.html','w')
                
                print("[blue]Added devices:[/blue]")
                al.write('<label><input id="toggle" type="checkbox" onclick="toggleAll()" name="Toggle all" checked /><i>Toggle all '+str(len(addedDevs['data']))+' devices</i></label><hr class="rounded"></hr>')
                for dev in addedDevs['data']:
                    print("  [blue]"+dev['hostname']+"[/blue]",end="")
                    al.write('<label><input id="dev" type="checkbox" onclick="toggleOne()" value="yes" name="'+dev['hostname']+'" checked />'+dev['hostname']+'</label>')
                print()
                al.close()

                rl=open("templates/decom-list.html","w")

                print("[red]Removed devices:[/red]")
                rl.write('<label><input id="toggle" type="checkbox" onclick="toggleAll()" name="Toggle all" checked /><i>Toggle all '+str(len(removedDevs['data']))+' devices</i></label><hr class="rounded"></hr>')
                for dev in removedDevs['data']:
                    print("  [red]"+dev['hostname']+"[/red]",end="")
                    rl.write('<label><input id="dev" type="checkbox" onclick="toggleOne()" value="yes" name="'+dev['hostname']+'" checked />'+dev['hostname']+'</label>')
                print()
                rl.close()

                webexTeamsRoom=WebexTeamsAPI()
                myWebexRoom='Y2lzY29zcGFyazovL3VzL1JPT00vNmUwYTQ2MzAtNTAzNC0xMWVhLTk2OTgtODMwZmVjZGNhOGM4'
                response=webexTeamsRoom.messages.create(roomId=myWebexRoom,text=time.ctime()+' - IPF Snapshot completed\n\nFor devices added, see http://'+webhookServer+':5000/addform\n\nFor devices to be decommissioned, see http://'+webhookServer+':5000/decomform\n\n\n')
                if response.id != None:
                    print("[green]WxT  - Submitted added/removed device messages to Webex Teams room[/green]")

                oldInts=fetchIpfInterfaces(ipfServer,ipfApiToken,ipfBaseUrl,prevSnap[0])
                oldIntList=[]
                for intf in oldInts['data']:
                    if intf['dscr']==None:
                        intDesc='<empty>'
                    else:
                        intDesc=intf['dscr']
                    oldIntList.append((intf['hostname']+'::'+intf['intName'],intDesc))

                newInts=fetchIpfInterfaces(ipfServer,ipfApiToken,ipfBaseUrl,lastSnap[0])
                newIntDict={}
                for intf in newInts['data']:
                    if intf['dscr']==None:
                        intDesc='<empty>'
                    else:
                        intDesc=intf['dscr']
                    newIntDict.update([(intf['hostname']+'::'+intf['intName'],intDesc)])
                
                updateList=[]
                for oldIntf in oldIntList:
                    try:
                        intfKey=oldIntf[0]
                        noMatch=False
                        newIntfDesc=newIntDict[intfKey]
                        if newIntfDesc != oldIntf[1]:
                            updateList.append((intfKey,newIntfDesc))
                    except:
                        noMatch=True

                #Update Netbox with status inactive
                nbApi=pynetbox.api('https://'+nbServer,token=nbApiToken)
                nbApi.http_session.verify=False
                snapTag=createNetBoxSnapshotTag (nbApi, lastSnap[0], lastSnap[1], lastSnap[2])

                notes=''
                print("[green]NETBOX - interface descriptions updating[/green]",end="")
                for intf in updateList:
                    #nbDevice=nbApi.dcim.devices.get(name=dev)
                    #nbDevice.update({'status':'decommissioning'})
                    notes=notes+intf[0]+'    '
                    nbIntfExists=False
                    try:
                        dev=intf[0].split('::')[0]
                        intfName=intf[0].split('::')[1]
                        nbInterface=nbApi.dcim.interfaces.filter(device=dev,name=intfName)[0]
                        noMatch=False
                        nbInterface.update({'label':intf[1],'tags':[snapTag]})
                        print("[green].[/green]",end="")
                    except:
                        noMatch=True
                print("[green]DONE[/green]")

                webexTeamsRoom=WebexTeamsAPI()
                myWebexRoom='Y2lzY29zcGFyazovL3VzL1JPT00vNmUwYTQ2MzAtNTAzNC0xMWVhLTk2OTgtODMwZmVjZGNhOGM4'
                response=webexTeamsRoom.messages.create(roomId=myWebexRoom,text=time.ctime()+' - IPF Snapshot completed\n\nInterface descriptions changed for:\n\n'+notes)
                if response.id != None:
                    print("[green]WxT  - Submitted interface description message to Webex Teams room[/green]")
                print("[blue]WEBHOOK ACTIONS COMPLETED[/blue]")

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

    if firstTime:
        #Open NetBox API session
        nb=pynetbox.api('https://'+nbServer,token=nbApiToken)
        nb.http_session.verify=False

        #Fetch IP Fabric snapshot details
        snapEndpoint='https://'+ipfServer+ipfBaseUrl+'snapshots'
        snapRequest=requests.get(snapEndpoint,headers=ipfHeaders,verify=False)
        snaps=json.loads(snapRequest.text)
        lastLoaded=False
        prevLoaded=False

        for snap in snaps:
            if snap['state']=='loaded':
                if not lastLoaded:
                    lastSnap=(snap['id'],snap['name'],time.strftime("%d-%m-%Y %H:%M:%S",time.localtime(snap['tsEnd']/1000)))
                    lastLoaded=True
                    print("[green]IPF - SNAPSHOT - Found lastLoaded ("+lastSnap[0]+","+lastSnap[1]+")[/green]")
                elif not prevLoaded:
                    prevSnap=(snap['id'],snap['name'],time.strftime("%d-%m-%Y %H:%M:%S",time.localtime(snap['tsEnd']/1000)))
                    prevLoaded=True
                    print("[green]IPF - SNAPSHOT - Found prevLoaded ("+prevSnap[0]+","+prevSnap[1]+")[/green]")

        #Ensure all devices and interfaces loaded from current snapshot 
        snapTag=createNetBoxSnapshotTag(nb,lastSnap[0],lastSnap[1],lastSnap[2])
        devDeets=fetchIpfInventory(ipfServer,ipfApiToken,ipfBaseUrl,lastSnap[0])
        intDeets=fetchIpfInterfaces(ipfServer,ipfApiToken,ipfBaseUrl,lastSnap[0])
        #devListToNetBox(nb,devDeets,intDeets,snapTag)
        #devListToSNow(sNowServer,sNowUser,sNowPass,devDeets)
        firstTime=False

    event = threading.Event()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(consumer, pipeline, event)
        #app.run(debug=True,host='0.0.0.0')
        app.run(debug=False,host='0.0.0.0')
        time.sleep(30)
        logging.info("Main: about to set event")
        event.set()
