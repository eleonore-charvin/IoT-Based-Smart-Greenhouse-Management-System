import cherrypy
import json
import time

def addDevice(catalog, devicesInfo):
    catalog["devices"].append(devicesInfo)

def updateDevice(catalog, DeviceID, devicesInfo):
    for i in range(len(catalog["devices"])):
        device = catalog["devices"][i]
        if device['ID'] == DeviceID:
            catalog["devices"][i] = devicesInfo

def removeDevices(catalog, DeviceID):
    for i in range(len(catalog["devices"])):
        device = catalog["devices"][i]
        if device['ID'] == int(DeviceID):
            catalog["devices"].pop(i)

def addService(catalog, ServiceInfo):
    catalog["services"].append(ServiceInfo)

def updateService(catalog, ServiceID, ServiceInfo):
    for i in range(len(catalog["services"])):
        service = catalog["services"][i]
        if service['ID'] == ServiceID:
            catalog["services"][i] = ServiceInfo

def removeService(catalog, ServiceID):
    for i in range(len(catalog["services"])):
        service = catalog["services"][i]
        if service['ID'] == int(ServiceID):
            catalog["services"].pop(i)

def addGreenHouse(catalog, GreenHouseID):
    catalog["GreenHouses"].append(GreenHouseID)

def updateGreenHouse(catalog, GreenHouseID, GreenHouseInfo):
    for i in range(len(catalog["GreenHouses"])):
        greenhouse = catalog["GreenHouses"][i]
        if greenhouse['ID'] == GreenHouseID:
            catalog["GreenHouses"][i] = GreenHouseInfo

def removeGreenHouse(catalog, GreenHouseID):
    for i in range(len(catalog["GreenHouses"])):
        greenhouse = catalog["GreenHouses"][i]
        if greenhouse['ID'] == GreenHouseID:
            catalog["GreenHouses"].pop(i)


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
        elif uri[0] == 'greenhouses':
            if len(uri) == 2:  # specific GreenHouse by ID
                greenhouseID = int(uri[1])
                greenhouse = next((gh for gh in catalog["GreenHouses"] if gh["ID"] == greenhouseID), None)
                if greenhouse:
                    output = greenhouse
                # else:
                    # raise cherrypy.HTTPError(status=404, message=f"Greenhouse with ID {greenhouseID} not found.")
            else:  
                output = {"GreenHouses": catalog["GreenHouses"]}
        
        elif uri[0] == 'zones':
            if len(uri) == 3 and uri[1] == 'greenhouse':
                # get zones of a specific greenhouse
                greenhouseID = int(uri[2])
                zones = [zone for zone in catalog["ZonesList"] if zone.get("GreenHouseID") == greenhouseID]
                if zones:
                    output = {"Zones": zones}
                else:
                    raise cherrypy.HTTPError(404, f"No zones found for Greenhouse ID {greenhouseID}.")

            elif len(uri) == 2:
                # get specific zone by ZoneID
                zoneID = int(uri[1])
                zone = next((z for z in catalog["ZonesList"] if z["ZoneID"] == zoneID), None)
                if zone:
                    output = zone
                else:
                    raise cherrypy.HTTPError(404, f"Zone with ID {zoneID} not found.")

            else:
                # Get all zones
                output = {"Zones": catalog["ZonesList"]}

        return json.dumps(output)
    '''
    def POST(self, *uri, **params):
        catalog=json.load(open(self.catalog_address,"r"))
        body = cherrypy.request.body.read()
        json_body = json.loads(body.decode('utf-8'))
        if uri[0]=='devices':
            if not any(d['ID'] == json_body['ID'] for d in catalog["devices"]):
                last_update = time.time()
                json_body['last_update'] = last_update
                addDevice(catalog, json_body)
                output = f"Device with ID {json_body['ID']} has been added"
                print(output)
            else:
                raise cherrypy.HTTPError(status=400, message='DEVICE ALREADY REGISTERED')
        elif uri[0]=='services':
            if not any(d['ID'] == json_body['ID'] for d in catalog["services"]):
                last_update = time.time()
                json_body['last_update'] = last_update
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
        last_update = time.time()

        if uri[0] == 'devices':
            if any(d['ID'] == json_body['ID'] for d in catalog["devices"]):
                raise cherrypy.HTTPError(400, 'DEVICE ALREADY REGISTERED')
            json_body['last_update'] = last_update
            catalog["devices"].append(json_body)
            output = f"Device with ID {json_body['ID']} has been added"

        elif uri[0] == 'services':
            if any(s['ID'] == json_body['ID'] for s in catalog["services"]):
                raise cherrypy.HTTPError(400, 'SERVICE ALREADY REGISTERED')
            json_body['last_update'] = last_update
            catalog["services"].append(json_body)
            output = f"Service with ID {json_body['ID']} has been added"

        elif uri[0] == 'greenhouses':
            if any(gh['ID'] == json_body['ID'] for gh in catalog["GreenHouses"]):
                raise cherrypy.HTTPError(400, 'GREENHOUSE ALREADY REGISTERED')
            json_body['last_update'] = last_update
            json_body["Zones"] = []  # Initialize empty Zones list
            catalog["GreenHouses"].append(json_body)
            output = f"Greenhouse with ID {json_body['ID']} has been added"

        elif uri[0] == 'zones':
            greenhouseID = json_body['GreenHouseID']
            zone_temp_range = json_body['TemperatureRange']  # e.g., [min, max]

            greenhouse = next((gh for gh in catalog["GreenHouses"] if gh["ID"] == greenhouseID), None)
            if not greenhouse:
                raise cherrypy.HTTPError(404, f'Greenhouse ID {greenhouseID} not found')

            # Check temperature range overlaps
            for existing_zone in catalog["ZonesList"]:
                if existing_zone["GreenHouseID"] == greenhouseID:
                    existing_range = existing_zone["TemperatureRange"]
                    overlap = not (zone_temp_range[1] < existing_range[0] or zone_temp_range[0] > existing_range[1])
                    if overlap:
                        raise cherrypy.HTTPError(400, f'Temperature range overlaps with existing zone ID {existing_zone["ZoneID"]}')

            # If no overlaps, add zone
            json_body['last_update'] = last_update
            catalog["ZonesList"].append(json_body)
            greenhouse["Zones"].append(json_body["ZoneID"])
            output = f"Zone with ID {json_body['ZoneID']} added to Greenhouse {greenhouseID}"

        elif uri[0] == 'users':
            if any(user['UserID'] == json_body['UserID'] for user in catalog["UsersList"]):
                raise cherrypy.HTTPError(400, 'USER ALREADY REGISTERED')
            json_body['last_update'] = last_update
            catalog["UsersList"].append(json_body)
            output = f"User with ID {json_body['UserID']} has been added"

        else:
            raise cherrypy.HTTPError(400, 'INVALID ENDPOINT')

        json.dump(catalog, open(self.catalog_address, "w"), indent=4)
        print(output)
        return json.dumps({"message": output})
    
    def PUT(self, *uri, **params):
        catalog = json.load(open(self.catalog_address, "r"))
        body = cherrypy.request.body.read()
        json_body = json.loads(body.decode('utf-8'))
        last_update = time.time()

        if uri[0] == 'devices':
            device = next((d for d in catalog["devices"] if d["ID"] == json_body["ID"]), None)
            if not device:
                raise cherrypy.HTTPError(404, 'DEVICE NOT FOUND')
            json_body['last_update'] = last_update
            catalog["devices"] = [json_body if d["ID"] == json_body["ID"] else d for d in catalog["devices"]]
            output = f"Device with ID {json_body['ID']} has been updated"

        elif uri[0] == 'services':
            service = next((s for s in catalog["services"] if s["ID"] == json_body["ID"]), None)
            if not service:
                raise cherrypy.HTTPError(404, 'SERVICE NOT FOUND')
            json_body['last_update'] = last_update
            catalog["services"] = [json_body if s["ID"] == json_body["ID"] else s for s in catalog["services"]]
            output = f"Service with ID {json_body['ID']} has been updated"

        elif uri[0] == 'greenhouses':
            greenhouse = next((gh for gh in catalog["GreenHouses"] if gh["ID"] == json_body["ID"]), None)
            if not greenhouse:
                raise cherrypy.HTTPError(404, 'GREENHOUSE NOT FOUND')
            json_body['last_update'] = last_update
            # Keep existing zones unless explicitly updated
            json_body["Zones"] = greenhouse.get("Zones", [])
            catalog["GreenHouses"] = [json_body if gh["ID"] == json_body["ID"] else gh for gh in catalog["GreenHouses"]]
            output = f"Greenhouse with ID {json_body['ID']} has been updated"

        elif uri[0] == 'zones':
            zone = next((z for z in catalog["ZonesList"] if z["ZoneID"] == json_body["ZoneID"]), None)
            if not zone:
                raise cherrypy.HTTPError(404, 'ZONE NOT FOUND')

            # Check for temperature range overlaps before updating
            greenhouseID = json_body["GreenHouseID"]
            new_range = json_body["TemperatureRange"]

            for existing_zone in catalog["ZonesList"]:
                if existing_zone["GreenHouseID"] == greenhouseID and existing_zone["ZoneID"] != json_body["ZoneID"]:
                    existing_range = existing_zone["TemperatureRange"]
                    overlap = not (new_range[1] < existing_range[0] or new_range[0] > existing_range[1])
                    if overlap:
                        raise cherrypy.HTTPError(400, f'Temperature range overlaps with zone ID {existing_zone["ZoneID"]}')

            json_body['last_update'] = last_update
            catalog["ZonesList"] = [json_body if z["ZoneID"] == json_body["ZoneID"] else z for z in catalog["ZonesList"]]
            output = f"Zone with ID {json_body['ZoneID']} has been updated"

        elif uri[0] == 'users':
            user = next((u for u in catalog["UsersList"] if u["UserID"] == json_body["UserID"]), None)
            if not user:
                raise cherrypy.HTTPError(404, 'USER NOT FOUND')
            json_body['last_update'] = last_update
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
                last_update = time.time()
                json_body['last_update'] = last_update
                updateDevice(catalog, json_body['ID'], json_body)
        elif uri[0]=='services':
            if not any(d['ID'] == json_body['ID'] for d in catalog["services"]):
                raise cherrypy.HTTPError(status=400, message='SERVICE NOT FOUND')
            else:
                last_update = time.time()
                json_body['last_update'] = last_update
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
