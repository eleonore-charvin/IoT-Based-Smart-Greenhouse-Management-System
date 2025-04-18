import cherrypy
import json
import time

def addDevice(catalog, devicesInfo):
    catalog["devicesList"].append(devicesInfo)

def updateDevice(catalog, DeviceID, devicesInfo):
    for i in range(len(catalog["devicesList"])):
        device = catalog["devicesList"][i]
        if device['deviceID'] == DeviceID:
            catalog["devicesList"][i] = devicesInfo

def removeDevices(catalog, DeviceID):
    for i in range(len(catalog["devicesList"])):
        device = catalog["devicesList"][i]
        if device['deviceID'] == int(DeviceID):
            catalog["devicesList"].pop(i)

def addService(catalog, ServiceInfo):
    catalog["servicesList"].append(ServiceInfo)

def updateService(catalog, ServiceID, ServiceInfo):
    for i in range(len(catalog["servicesList"])):
        service = catalog["servicesList"][i]
        if service['serviceID'] == ServiceID:
            catalog["servicesList"][i] = ServiceInfo

def removeService(catalog, ServiceID):
    for i in range(len(catalog["servicesList"])):
        service = catalog["servicesList"][i]
        if service['serviceID'] == int(ServiceID):
            catalog["servicesList"].pop(i)

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
    greenhouse = next((gh for gh in catalog["greenhousesList"] if gh["greenhouseID"] == greenhouseID), None)
    if not greenhouse:
        return []

    zone_ids = greenhouse.get("zones", [])
    return [zone for zone in catalog["zonesList"] if zone["zoneID"] in zone_ids]

def check_range_overlap(existing_zones, zone_temp_range):
    """
    Check that zone_temp_range overlaps with all existing_zones
    """
    for existing_zone in existing_zones:
        existing_range = existing_zone["temperatureRange"]
        overlap = not (zone_temp_range["max"] < existing_range["min"] or zone_temp_range["min"] > existing_range["max"])
        return overlap

class CatalogREST(object):
    exposed = True

    def __init__(self, catalog_address):
        self.catalog_address = catalog_address
    
    def GET(self, *uri, **params):
        catalog = json.load(open(self.catalog_address, "r"))

        if len(uri) == 0:
            raise cherrypy.HTTPError(400, 'UNABLE TO MANAGE THIS URL')

        if uri[0] == 'all':
            output = catalog

        elif uri[0] == 'devices':
            output = {"devicesList": catalog["devicesList"]}

        elif uri[0] == 'services':
            output = {"servicesList": catalog["servicesList"]}

        elif uri[0] == 'greenhouses':
            if 'greenhouseID' in params:
                greenhouseID = int(params['greenhouseID'])
                greenhouse = next((gh for gh in catalog["greenhousesList"] if gh["greenhouseID"] == greenhouseID), None)
                if greenhouse:
                    output = {"greenhousesList": greenhouse}
                else:
                    raise cherrypy.HTTPError(404, f"Greenhouse with ID {greenhouseID} not found.")
            else:
                output = {"greenhousesList": catalog["greenhousesList"]}

        elif uri[0] == 'zonesID':
            if 'greenhouseID' not in params:
                raise cherrypy.HTTPError(400, "Missing 'greenhouseID' parameter")

            greenhouseID = int(params['greenhouseID'])
            greenhouse = next((gh for gh in catalog["greenhousesList"] if gh["greenhouseID"] == greenhouseID), None)
            if not greenhouse:
                raise cherrypy.HTTPError(404, f"Greenhouse with ID {greenhouseID} not found")

            output = {"zones": greenhouse.get("zones", [])}

        elif uri[0] == 'zones':
            if 'zoneID' in params:
                # Return one zone by ID
                zoneID = int(params['zoneID'])
                zone = next((z for z in catalog["zonesList"] if z["zoneID"] == zoneID), None)
                if not zone:
                    raise cherrypy.HTTPError(404, f"Zone with ID {zoneID} not found")
                output = {"zonesList": zone}

            elif 'greenhouseID' in params:
                # Return all zones belonging to a greenhouse
                greenhouseID = int(params['greenhouseID'])
                greenhouse = next((gh for gh in catalog["greenhousesList"] if gh["greenhouseID"] == greenhouseID), None)
                if not greenhouse:
                    raise cherrypy.HTTPError(404, f"Greenhouse with ID {greenhouseID} not found")

                zone_ids = greenhouse.get("zones", [])
                zones = [z for z in catalog["zonesList"] if z["zoneID"] in zone_ids]
                output = {"zonesList": zones}

            else:
                # Return all zones
                output = {"zonesList": catalog["zonesList"]}

        else:
            raise cherrypy.HTTPError(400, 'INVALID ENDPOINT')

        return json.dumps(output)

    def POST(self, *uri, **params):
        catalog = json.load(open(self.catalog_address, "r"))
        body = cherrypy.request.body.read()
        json_body = json.loads(body.decode('utf-8'))
        lastUpdate = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        if uri[0] == 'devices':
            if any(d['deviceID'] == json_body['deviceID'] for d in catalog["devicesList"]):
                raise cherrypy.HTTPError(400, 'DEVICE ALREADY REGISTERED')
            json_body['lastUpdate'] = lastUpdate
            catalog["devicesList"].append(json_body)
            output = f"Device with ID {json_body['deviceID']} has been added"

        elif uri[0] == 'services':
            if any(s['serviceID'] == json_body['serviceID'] for s in catalog["servicesList"]):
                raise cherrypy.HTTPError(400, 'SERVICE ALREADY REGISTERED')
            json_body['lastUpdate'] = lastUpdate
            catalog["servicesList"].append(json_body)
            output = f"Service with ID {json_body['serviceID']} has been added"

        elif uri[0] == 'greenhouses':
            if any(gh['greenhouseID'] == json_body['greenhouseID'] for gh in catalog["greenhousesList"]):
                raise cherrypy.HTTPError(400, 'GREENHOUSE ALREADY REGISTERED')
            json_body['lastUpdate'] = lastUpdate
            json_body["zones"] = []  # Initialize empty zones list
            catalog["greenhousesList"].append(json_body)
            output = f"Greenhouse with ID {json_body['greenhouseID']} has been added"

        elif uri[0] == 'zones':
            if 'greenhouseID' not in params:
                raise cherrypy.HTTPError(400, "Missing 'greenhouseID' parameter")

            greenhouseID = int(params['greenhouseID'])
            zone_temp_range = json_body['temperatureRange']  # e.g., [min, max]
            existing_zones = get_zones_of_greenhouse(catalog, greenhouseID)

            greenhouse = next((gh for gh in catalog["greenhousesList"] if gh["zoneID"] == greenhouseID), None)
            if not greenhouse:
                raise cherrypy.HTTPError(404, f'Greenhouse ID {greenhouseID} not found')

            overlap = check_range_overlap(existing_zones, zone_temp_range)
            if not overlap:
                raise cherrypy.HTTPError(400, f'Temperature range of new zone does NOT overlap with existing zone ID {existing_zone["ZoneID"]}')

            # If overlaps, add zone
            json_body['lastUpdate'] = lastUpdate
            catalog["zonesList"].append(json_body)
            greenhouse["zones"].append(json_body["zoneID"])
            output = f"Zone with ID {json_body['zoneID']} added to Greenhouse {greenhouseID}"

        elif uri[0] == 'users':
            if any(user['userID'] == json_body['userID'] for user in catalog["usersList"]):
                raise cherrypy.HTTPError(400, 'USER ALREADY REGISTERED')
            json_body['lastUpdate'] = lastUpdate
            catalog["usersList"].append(json_body)
            output = f"User with ID {json_body['userID']} has been added"

        else:
            raise cherrypy.HTTPError(400, 'INVALID ENDPOINT')
        catalog["lastUpdate"] = lastUpdate
        json.dump(catalog, open(self.catalog_address, "w"), indent=4)

        print(output)
        return json.dumps({"message": output})
    
    def PUT(self, *uri, **params):
        catalog = json.load(open(self.catalog_address, "r"))
        body = cherrypy.request.body.read()
        json_body = json.loads(body.decode('utf-8'))
        last_update = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        if uri[0] == 'greenhouses':
            # Get greenhouseID from body
            greenhouseID = json_body['greenhouseID']
            greenhouse = next((gh for gh in catalog["greenhousesList"] if gh["greenhouseID"] == greenhouseID), None)

            if not greenhouse:
                raise cherrypy.HTTPError(404, f'Greenhouse with ID {greenhouseID} not found')

            catalog["greenhousesList"] = [
                json_body if gh["greenhouseID"] == greenhouseID else gh 
                for gh in catalog["greenhousesList"]
            ]

            output = f"Greenhouse with ID {greenhouseID} updated successfully"

        elif uri[0] == 'zones':
            if 'greenhouseID' not in params:
                raise cherrypy.HTTPError(400, "Missing 'greenhouseID' parameter")

            greenhouseID = int(params['greenhouseID'])
            zone = next((z for z in catalog["zonesList"] if z["zoneID"] == json_body["zoneID"]), None)
            if not zone:
                raise cherrypy.HTTPError(404, 'ZONE NOT FOUND')

            new_range = json_body["temperatureRange"]

            existing_zones = get_zones_of_greenhouse(catalog, greenhouseID)
            overlap = check_range_overlap(existing_zones, new_range)
            if not overlap:
                raise cherrypy.HTTPError(400, f'Temperature range of new zone does NOT overlap with existing zone ID {existing_zone["ZoneID"]}')

            # If overlaps, update zone
            json_body['lastUpdate'] = last_update
            catalog["zonesList"] = [
                json_body if z["zoneID"] == json_body["zoneID"] else z 
                for z in catalog["zonesList"]
            ]
            output = f"Zone with ID {json_body['zoneID']} updated successfully"

        elif uri[0] == 'users':
            user = next((u for u in catalog["usersList"] if u["userID"] == json_body["userID"]), None)
            if not user:
                raise cherrypy.HTTPError(404, 'USER NOT FOUND')

            json_body['lastUpdate'] = last_update
            catalog["usersList"] = [
                json_body if u["userID"] == json_body["userID"] else u 
                for u in catalog["usersList"]
            ]
            output = f"User with ID {json_body['userID']} updated successfully"

        else:
            raise cherrypy.HTTPError(400, 'INVALID ENDPOINT')

        catalog["lastUpdate"] = last_update
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
            catalog["devicesList"] = [d for d in catalog["devicesList"] if d["ID"] != resource_id]
            output = f"Device with ID {resource_id} has been removed"

        elif resource_type == 'services':
            catalog["servicesList"] = [s for s in catalog["servicesList"] if s["ID"] != resource_id]
            output = f"Service with ID {resource_id} has been removed"

        elif resource_type == 'greenhouses':
            greenhouse_exists = any(gh["greenhouseID"] == resource_id for gh in catalog["greenhousesList"])
            if not greenhouse_exists:
                raise cherrypy.HTTPError(404, f"Greenhouse with ID {resource_id} not found")
            catalog["greenhousesList"] = [gh for gh in catalog["greenhousesList"] if gh["greenhouseID"] != resource_id]
            output = f"Greenhouse with ID {resource_id} has been removed"

        elif resource_type == 'zones':
            zone = next((z for z in catalog["zonesList"] if z["zoneID"] == resource_id), None)
            if not zone:
                raise cherrypy.HTTPError(404, f"Zone with ID {resource_id} not found")

            # Remove zone from ZonesList
            catalog["zonesList"] = [z for z in catalog["zonesList"] if z["zoneID"] != resource_id]

            # Remove zone ID from any greenhouse's Zones list
            for gh in catalog["greenhouseID"]:
                if "zones" in gh and resource_id in gh["zones"]:
                    gh["zones"].remove(resource_id)

            output = f"Zone with ID {resource_id} has been deleted and removed from its greenhouse"

        elif resource_type == 'users':
            user_exists = any(u["userID"] == resource_id for u in catalog["usersList"])
            if not user_exists:
                raise cherrypy.HTTPError(404, f"User with ID {resource_id} not found")
            catalog["usersList"] = [u for u in catalog["usersList"] if u["userID"] != resource_id]
            output = f"User with ID {resource_id} has been removed"

        else:
            raise cherrypy.HTTPError(400, 'Invalid resource type for DELETE')

        # Update the catalog's lastUpdate field
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
