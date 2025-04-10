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

def get_zones_of_greenhouse(catalog, greenhouseID):
    # Get the list of zone IDs from the greenhouse
    greenhouse = next((gh for gh in catalog["GreenHouses"] if gh["ID"] == greenhouseID), None)
    if not greenhouse:
        return []

    zone_ids = greenhouse.get("Zones", [])
    return [zone for zone in catalog["ZonesList"] if zone["ZoneID"] in zone_ids]


class CatalogREST(object):
    exposed = True

    def __init__(self, catalog_address):
        self.catalog_address = catalog_address
        catalog_address = "C:/Users/parni/Desktop/MSc_PoliTo/Programming_For_IoT/FinalProject/catalog.json"
    
    def GET(self, *uri, **params):
        catalog = json.load(open(self.catalog_address, "r"))

        if len(uri) == 0:
            raise cherrypy.HTTPError(400, 'UNABLE TO MANAGE THIS URL')

        if uri[0] == 'all':
            output = catalog

        elif uri[0] == 'devices':
            output = {"devices": catalog["devices"]}

        elif uri[0] == 'services':
            output = {"services": catalog["services"]}

        elif uri[0] == 'greenhouses':
            if len(uri) == 2:
                greenhouseID = int(uri[1])
                greenhouse = next((gh for gh in catalog["GreenHouses"] if gh["ID"] == greenhouseID), None)
                if greenhouse:
                    output = greenhouse
                else:
                    raise cherrypy.HTTPError(404, f"Greenhouse with ID {greenhouseID} not found.")
            else:
                output = {"GreenHouses": catalog["GreenHouses"]}

        elif uri[0] == 'zonesID':
            if 'greenhouseID' not in params:
                raise cherrypy.HTTPError(400, "Missing 'greenhouseID' parameter")

            greenhouseID = int(params['greenhouseID'])
            greenhouse = next((gh for gh in catalog["GreenHouses"] if gh["ID"] == greenhouseID), None)
            if not greenhouse:
                raise cherrypy.HTTPError(404, f"Greenhouse with ID {greenhouseID} not found")

            output = {"zoneIDs": greenhouse.get("Zones", [])}

        elif uri[0] == 'zones':
            if 'zoneID' in params:
                # Return one zone by ID
                zoneID = int(params['zoneID'])
                zone = next((z for z in catalog["ZonesList"] if z["ZoneID"] == zoneID), None)
                if not zone:
                    raise cherrypy.HTTPError(404, f"Zone with ID {zoneID} not found")
                output = zone

            elif 'greenhouseID' in params:
                # Return all zones belonging to a greenhouse
                greenhouseID = int(params['greenhouseID'])
                greenhouse = next((gh for gh in catalog["GreenHouses"] if gh["ID"] == greenhouseID), None)
                if not greenhouse:
                    raise cherrypy.HTTPError(404, f"Greenhouse with ID {greenhouseID} not found")

                zone_ids = greenhouse.get("Zones", [])
                zones = [z for z in catalog["ZonesList"] if z["ZoneID"] in zone_ids]
                output = {"zones": zones}

            else:
                # Return all zones
                output = {"Zones": catalog["ZonesList"]}

        else:
            raise cherrypy.HTTPError(400, 'INVALID ENDPOINT')

        return json.dumps(output)

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

            existing_zones = get_zones_of_greenhouse(catalog, greenhouseID)
            for existing_zone in existing_zones:
                existing_range = existing_zone["TemperatureRange"]
                overlap = not ( zone_temp_range["max"] < existing_range["min"] or zone_temp_range["min"] > existing_range["max"])
                    # i could not find the true reference to call "zone temperature range" in our json file or elsewhere so zone_temp_range is just a place holder for correct name
                if not overlap:
                         raise cherrypy.HTTPError(400, f'Temperature range of new zone does NOT overlap with existing zone ID {existing_zone["ZoneID"]}')


            
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
        catalog["lastUpdate"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        json.dump(catalog, open(self.catalog_address, "w"), indent=4)

        print(output)
        return json.dumps({"message": output})
    
    def PUT(self, *uri, **params):
        catalog = json.load(open(self.catalog_address, "r"))
        body = cherrypy.request.body.read()
        json_body = json.loads(body.decode('utf-8'))
        last_update = time.time()

        if uri[0] == 'greenhouses':
            # Get greenhouseID from params, not URI or body
            if 'greenhouseID' not in params:
                raise cherrypy.HTTPError(400, 'greenhouseID parameter missing')

            greenhouseID = int(params['greenhouseID'])
            greenhouse = next((gh for gh in catalog["GreenHouses"] if gh["ID"] == greenhouseID), None)

            if not greenhouse:
                raise cherrypy.HTTPError(404, f'Greenhouse with ID {greenhouseID} not found')

            # Update existing greenhouse with provided data, preserving ID and Zones
            updated_greenhouse = {
                "ID": greenhouseID,
                "Name": json_body.get("Name", greenhouse["Name"]),
                "Location": json_body.get("Location", greenhouse["Location"]),
                "Zones": greenhouse.get("Zones", []),
                "last_update": last_update
            }

            catalog["GreenHouses"] = [
                updated_greenhouse if gh["ID"] == greenhouseID else gh 
                for gh in catalog["GreenHouses"]
            ]

            output = f"Greenhouse with ID {greenhouseID} updated successfully"

        elif uri[0] == 'zones':
            zone = next((z for z in catalog["ZonesList"] if z["ZoneID"] == json_body["ZoneID"]), None)
            if not zone:
                raise cherrypy.HTTPError(404, 'ZONE NOT FOUND')

            new_range = json_body["TemperatureRange"]
            greenhouseID = json_body["GreenHouseID"]

            existing_zones = get_zones_of_greenhouse(catalog, greenhouseID)
            for existing_zone in existing_zones:
                if existing_zone["ZoneID"] != json_body["ZoneID"]:

                    existing_range = existing_zone["TemperatureRange"]
                    overlap = not ( zone_temp_range["max"] < existing_range["min"] or zone_temp_range["min"] > existing_range["max"])
                    # i could not find the true reference to call "zone temperature range" in our json file or elsewhere so zone_temp_range is just a place holder for correct name
                    if not overlap:
                            raise cherrypy.HTTPError(400, f'Temperature range of new zone does NOT overlap with existing zone ID {existing_zone["ZoneID"]}')

                    raise cherrypy.HTTPError(400, f'Temperature range overlaps with zone ID {existing_zone["ZoneID"]}')

            json_body['last_update'] = last_update
            catalog["ZonesList"] = [
                json_body if z["ZoneID"] == json_body["ZoneID"] else z 
                for z in catalog["ZonesList"]
            ]
            output = f"Zone with ID {json_body['ZoneID']} updated successfully"

        elif uri[0] == 'users':
            user = next((u for u in catalog["UsersList"] if u["UserID"] == json_body["UserID"]), None)
            if not user:
                raise cherrypy.HTTPError(404, 'USER NOT FOUND')

            json_body['last_update'] = last_update
            catalog["UsersList"] = [
                json_body if u["UserID"] == json_body["UserID"] else u 
                for u in catalog["UsersList"]
            ]
            output = f"User with ID {json_body['UserID']} updated successfully"

        else:
            raise cherrypy.HTTPError(400, 'INVALID ENDPOINT')

        json.dump(catalog, open(self.catalog_address, "w"), indent=4)
        print(output)
        return json.dumps({"message": output})


    def DELETE(self, *uri):
        catalog = json.load(open(self.catalog_address, "r"))

        if len(uri) < 2:
            raise cherrypy.HTTPError(400, 'Missing resource ID in DELETE request')

        resource_type = uri[0]
        resource_id = int(uri[1])

        if resource_type == 'devices':
            catalog["devices"] = [d for d in catalog["devices"] if d["ID"] != resource_id]
            output = f"Device with ID {resource_id} has been removed"

        elif resource_type == 'services':
            catalog["services"] = [s for s in catalog["services"] if s["ID"] != resource_id]
            output = f"Service with ID {resource_id} has been removed"

        elif resource_type == 'greenhouses':
            greenhouse_exists = any(gh["ID"] == resource_id for gh in catalog["GreenHouses"])
            if not greenhouse_exists:
                raise cherrypy.HTTPError(404, f"Greenhouse with ID {resource_id} not found")
            catalog["GreenHouses"] = [gh for gh in catalog["GreenHouses"] if gh["ID"] != resource_id]
            output = f"Greenhouse with ID {resource_id} has been removed"

        elif resource_type == 'zones':
            zone = next((z for z in catalog["ZonesList"] if z["ZoneID"] == resource_id), None)
            if not zone:
                raise cherrypy.HTTPError(404, f"Zone with ID {resource_id} not found")

            # Remove zone from ZonesList
            catalog["ZonesList"] = [z for z in catalog["ZonesList"] if z["ZoneID"] != resource_id]

            # Remove zone ID from any greenhouse's Zones list
            for gh in catalog["GreenHouses"]:
                if "Zones" in gh and resource_id in gh["Zones"]:
                    gh["Zones"].remove(resource_id)

            output = f"Zone with ID {resource_id} has been deleted and removed from its greenhouse"

        elif resource_type == 'users':
            user_exists = any(u["UserID"] == resource_id for u in catalog["UsersList"])
            if not user_exists:
                raise cherrypy.HTTPError(404, f"User with ID {resource_id} not found")
            catalog["UsersList"] = [u for u in catalog["UsersList"] if u["UserID"] != resource_id]
            output = f"User with ID {resource_id} has been removed"

        else:
            raise cherrypy.HTTPError(400, 'Invalid resource type for DELETE')

        # ✅ Update the catalog's lastUpdate field
        catalog["lastUpdate"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        # Save updated catalog
        with open(self.catalog_address, "w") as f:
            json.dump(catalog, f, indent=4)

        print(output)
        return json.dumps({"message": output})



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
