import cherrypy
import json
import time

def addDevice(catalog, devicesInfo):
    catalog["devices"].append(devicesInfo)

def updateDevice(catalog, DeviceID, devicesInfo):
    for i in range(len(catalog["devices"])):
        device = catalog["devices"][i]
        if device['deviceID'] == DeviceID:
            catalog["devices"][i] = devicesInfo

def removeDevices(catalog, DeviceID):
    for i in range(len(catalog["devices"])):
        device = catalog["devices"][i]
        if device['deviceID'] == int(DeviceID):
            catalog["devices"].pop(i)

def addService(catalog, ServiceInfo):
    catalog["services"].append(ServiceInfo)

def updateService(catalog, ServiceID, ServiceInfo):
    for i in range(len(catalog["services"])):
        service = catalog["services"][i]
        if service['serviceID'] == ServiceID:
            catalog["services"][i] = ServiceInfo

def removeService(catalog, ServiceID):
    for i in range(len(catalog["services"])):
        service = catalog["services"][i]
        if service['serviceID'] == int(ServiceID):
            catalog["services"].pop(i)

def addGreenHouse(catalog, greenhouseID):
    catalog["greenhousesList"].append(greenhouseID)

def updateGreenHouse(catalog, greenhouseID, GreenHouseInfo):
    for i in range(len(catalog["greenhousesList"])):
        greenhouse = catalog["greenhousesList"][i]
        if greenhouse['greenhouseID'] == greenhouseID:
            catalog["greenhousesList"][i] = GreenHouseInfo

def removeGreenHouse(catalog, greenhouseID):
    for i in range(len(catalog["greenhousesList"])):
        greenhouse = catalog["greenhousesList"][i]
        if greenhouse['greenhouseID'] == greenhouseID:
            catalog["greenhousesList"].pop(i)


class CatalogREST(object):
    exposed = True

    def __init__(self, catalog_address):
        self.catalog_address = catalog_address
        catalog_address = "C:/Users/parni/Desktop/MSc_PoliTo/Programming_For_IoT/FinalProject/catalog.json"
    
    def GET(self, *uri, **params):
        catalog=json.load(open(self.catalog_address,"r"))
        if len(uri)==0:   # An error will be raised in case there is no uri 
           raise cherrypy.HTTPError(status=400, message='UNABLE TO MANAGE THIS URL')
        elif uri[0]=='all':
            output = catalog
        elif uri[0]=='devices':
            output = {"devices":catalog["devices"]}
        elif uri[0]=='services':
            output = {"services":catalog["services"]}
        elif uri[0] == 'greenhousesList':
            if len(uri) == 2:  # specific GreenHouse by greenhouseID
                greenhouseID = int(uri[1])
                greenhouse = next((gh for gh in catalog["greenhousesList"] if gh["greenhouseID"] == greenhouseID), None)
                if greenhouse:
                    output = greenhouse
                # else:
                    # raise cherrypy.HTTPError(status=404, message=f"Greenhouse with ID {greenhouseID} not found.")
            else:  
                output = {"greenhousesList": catalog["greenhousesList"]}
        
        elif uri[0] == 'zones':
            if len(uri) == 3 and uri[1] == 'greenhouse':
                # Get zones of a specific greenhouse
                greenhouseID = int(uri[2])
                zones = [zone for zone in catalog["zonesList"] if zone.get("greenhouseID") == greenhouseID]
                if zones:
                    output = {"zones": zones}
                else:
                    raise cherrypy.HTTPError(404, f"No zones found for Greenhouse ID {greenhouseID}.")

            elif len(uri) == 2:
                # get specific zone by zoneID
                zoneID = int(uri[1])
                zone = next((z for z in catalog["zonesList"] if z["zoneID"] == zoneID), None)
                if zone:
                    output = zone
                else:
                    raise cherrypy.HTTPError(404, f"Zone with ID {zoneID} not found.")

            else:
                # Get all zones
                output = {"zones": catalog["zonesList"]}

        return json.dumps(output)
    '''
    def POST(self, *uri, **params):
        catalog=json.load(open(self.catalog_address,"r"))
        body = cherrypy.request.body.read()
        json_body = json.loads(body.decode('utf-8'))
        if uri[0]=='devices':
            if not any(d['ID'] == json_body['ID'] for d in catalog["devices"]):
                lastUpdate = time.time()
                json_body['lastUpdate'] = lastUpdate
                addDevice(catalog, json_body)
                output = f"Device with ID {json_body['ID']} has been added"
                print(output)
            else:
                raise cherrypy.HTTPError(status=400, message='DEVICE ALREADY REGISTERED')
        elif uri[0]=='services':
            if not any(d['ID'] == json_body['ID'] for d in catalog["services"]):
                lastUpdate = time.time()
                json_body['lastUpdate'] = lastUpdate
                addService(catalog, json_body)
                output = f"Service with ID {json_body['ID']} has been added"
                print(output)
            else:
                raise cherrypy.HTTPError(status=400, message='SERVICE ALREADY REGISTERED')
        json.dump(catalog,open(self.catalog_address,"w"),indent=4)
        print(catalog)
        return output
    '''
    def POST(self, *uri, **params):
        catalog = json.load(open(self.catalog_address, "r"))
        body = cherrypy.request.body.read()
        json_body = json.loads(body.decode('utf-8'))
        lastUpdate = time.time()

        if uri[0] == 'devices':
            if any(d['deviceID'] == json_body['deviceID'] for d in catalog["devices"]):
                raise cherrypy.HTTPError(400, 'DEVICE ALREADY REGISTERED')
            json_body['lastUpdate'] = lastUpdate
            catalog["devices"].append(json_body)
            output = f"Device with ID {json_body['deviceID']} has been added"

        elif uri[0] == 'services':
            if any(s['serviceID'] == json_body['serviceID'] for s in catalog["services"]):
                raise cherrypy.HTTPError(400, 'SERVICE ALREADY REGISTERED')
            json_body['lastUpdate'] = lastUpdate
            catalog["services"].append(json_body)
            output = f"Service with ID {json_body['serviceID']} has been added"

        elif uri[0] == 'greenhousesList':
            if any(gh['greenhouseID'] == json_body['greenhouseID'] for gh in catalog["greenhousesList"]):
                raise cherrypy.HTTPError(400, 'GREENHOUSE ALREADY REGISTERED')
            json_body['lastUpdate'] = lastUpdate
            json_body["zones"] = []  # Initialize empty zones list
            catalog["greenhousesList"].append(json_body)
            output = f"Greenhouse with ID {json_body['greenhouseID']} has been added"

        elif uri[0] == 'zones':
            greenhouseID = json_body['greenhouseID']
            zone_temp_range = json_body['TemperatureRange']  # e.g., [min, max]

            greenhouse = next((gh for gh in catalog["greenhousesList"] if gh["zoneID"] == greenhouseID), None)
            if not greenhouse:
                raise cherrypy.HTTPError(404, f'Greenhouse ID {greenhouseID} not found')
'''
            # Check temperature range overlaps
            for existing_zone in catalog["zonesList"]:
                if existing_zone["greenhouseID"] == greenhouseID:
                    existing_range = existing_zone["TemperatureRange"]
                    overlap = not (zone_temp_range[1] < existing_range[0] or zone_temp_range[0] > existing_range[1])
                    if overlap:
                        raise cherrypy.HTTPError(400, f'Temperature range overlaps with existing zone ID {existing_zone["zoneID"]}')
'''
            # If no overlaps, add zone
            json_body['lastUpdate'] = lastUpdate
            catalog["zonesList"].append(json_body)
            greenhouse["zones"].append(json_body["zoneID"])
            output = f"Zone with ID {json_body['zoneID']} added to Greenhouse {greenhouseID}"

        elif uri[0] == 'users':
            if any(user['UserID'] == json_body['UserID'] for user in catalog["UsersList"]):
                raise cherrypy.HTTPError(400, 'USER ALREADY REGISTERED')
            json_body['lastUpdate'] = lastUpdate
            catalog["UsersList"].append(json_body)
            output = f"User with ID {json_body['UserID']} has been added"

        else:
            raise cherrypy.HTTPError(400, 'INVALID ENDPOINT')
        catalog["lastUpdate"] = time.time()
        json.dump(catalog, open(self.catalog_address, "w"), indent=4)
        print(output)
        return json.dumps({"message": output})
    
    def PUT(self, *uri, **params):
        catalog = json.load(open(self.catalog_address, "r"))
        body = cherrypy.request.body.read()
        json_body = json.loads(body.decode('utf-8'))
        lastUpdate = time.time()

        if uri[0] == 'devices':
            device = next((d for d in catalog["devices"] if d["deviceID"] == json_body["deviceID"]), None)
            if not device:
                raise cherrypy.HTTPError(404, 'DEVICE NOT FOUND')
            json_body['lastUpdate'] = lastUpdate
            catalog["devices"] = [json_body if d["deviceID"] == json_body["deviceID"] else d for d in catalog["devices"]]
            output = f"Device with ID {json_body['deviceID']} has been updated"

        elif uri[0] == 'services':
            service = next((s for s in catalog["services"] if s["serviceID"] == json_body["serviceID"]), None)
            if not service:
                raise cherrypy.HTTPError(404, 'SERVICE NOT FOUND')
            json_body['lastUpdate'] = lastUpdate
            catalog["services"] = [json_body if s["serviceID"] == json_body["serviceID"] else s for s in catalog["services"]]
            output = f"Service with ID {json_body['serviceID']} has been updated"

        elif uri[0] == 'greenhousesList':
            greenhouse = next((gh for gh in catalog["greenhousesList"] if gh["greenhouseID"] == json_body["greenhouseID"]), None)
            if not greenhouse:
                raise cherrypy.HTTPError(404, 'GREENHOUSE NOT FOUND')
            json_body['lastUpdate'] = lastUpdate
            # Keep existing zones unless explicitly updated
            # json_body["zones"] = greenhouse.get("zones", [])
            catalog["greenhousesList"] = [json_body if gh["greenhouseID"] == json_body["greenhouseID"] else gh for gh in catalog["greenhousesList"]]
            output = f"Greenhouse with ID {json_body['greenhouseID']} has been updated"

        elif uri[0] == 'zones':
            zone = next((z for z in catalog["zonesList"] if z["zoneID"] == json_body["zoneID"]), None)
            if not zone:
                raise cherrypy.HTTPError(404, 'ZONE NOT FOUND')

            # Check for temperature range overlaps before updating
            greenhouseID = json_body["greenhouseID"]
            new_range = json_body["TemperatureRange"]

            for existing_zone in catalog["zonesList"]:
                if existing_zone["greenhouseID"] == greenhouseID and existing_zone["zoneID"] != json_body["zoneID"]:
                    existing_range = existing_zone["TemperatureRange"]
                    overlap = not (new_range[1] < existing_range[0] or new_range[0] > existing_range[1])
                    if overlap:
                        raise cherrypy.HTTPError(400, f'Temperature range overlaps with zone ID {existing_zone["zoneID"]}')

            json_body['lastUpdate'] = lastUpdate
            catalog["zonesList"] = [json_body if z["zoneID"] == json_body["zoneID"] else z for z in catalog["zonesList"]]
            output = f"Zone with ID {json_body['zoneID']} has been updated"

        elif uri[0] == 'users':
            user = next((u for u in catalog["UsersList"] if u["UserID"] == json_body["UserID"]), None)
            if not user:
                raise cherrypy.HTTPError(404, 'USER NOT FOUND')
            json_body['lastUpdate'] = lastUpdate
            catalog["UsersList"] = [json_body if u["UserID"] == json_body["UserID"] else u for u in catalog["UsersList"]]
            output = f"User with ID {json_body['UserID']} has been updated"

        else:
            raise cherrypy.HTTPError(400, 'INVALID ENDPOINT')

        json.dump(catalog, open(self.catalog_address, "w"), indent=4)
        print(output)
        return json.dumps({"message": output})

    '''
    def PUT(self, *uri, **params):
        catalog=json.load(open(self.catalog_address,"r"))
        body = cherrypy.request.body.read()
        json_body = json.loads(body.decode('utf-8'))
        if uri[0]=='devices':
            if not any(d['ID'] == json_body['ID'] for d in catalog["devices"]):
                raise cherrypy.HTTPError(status=400, message='DEVICE NOT FOUND')
            else:
                lastUpdate = time.time()
                json_body['lastUpdate'] = lastUpdate
                updateDevice(catalog, json_body['ID'], json_body)
        elif uri[0]=='services':
            if not any(d['ID'] == json_body['ID'] for d in catalog["services"]):
                raise cherrypy.HTTPError(status=400, message='SERVICE NOT FOUND')
            else:
                lastUpdate = time.time()
                json_body['lastUpdate'] = lastUpdate
                updateService(catalog, json_body['ID'], json_body)
        print(catalog)
        json.dump(catalog,open(self.catalog_address,"w"),indent=4)
        return json_body
    '''
        
    def DELETE(self, *uri):
        catalog=json.load(open(self.catalog_address,"r"))
        if uri[0]=='devices':
            removeDevices(catalog,uri[1])
            output = f"Device with ID {uri[1]} has been removed"
            print(output)
        elif uri[0]=='services':
            catalog = removeService(catalog,uri[1])
            output = f"Service with ID {uri[0]} has been removed"
            print(output)
        json.dump(catalog,open(self.catalog_address,"w"),indent=4)
        # add another elif to remove the greenhouse and zones and also zoneID from the greenhouse itself




if __name__ == '__main__':
    catalogClient = CatalogREST("catalog.json")
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True
        }
    }
    cherrypy.config.update({'server.socket_host': '0.0.0.0', 'server.socket_port': 8080})
    #cherrypy.config.update({'server.socket_port': 8080})
    cherrypy.tree.mount(catalogClient, '/', conf)
    cherrypy.engine.start()
    cherrypy.engine.block()
    cherrypy.engine.exit()
