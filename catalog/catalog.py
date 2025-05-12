import cherrypy
import json
import time

# Functions

# - Devices

def add_device(catalog, dict_body, params, last_update):
    """
    Add a device to the devices list and to the requested greenhouse's or zone's devices.

    Parameters:
        catalog (dict): catalog.
        dict_body (dict): device to add.
        params (dict): parameters of the request (containing the ID of the greenhouse or zone in which to add the device).
        last_update (str): formatted timestamp of the update.

    Returns:
        str: success message.
    """
    
    if any(d['deviceID'] == dict_body['deviceID'] for d in catalog["devicesList"]):
        raise cherrypy.HTTPError(400, 'DEVICE ALREADY REGISTERED')
    
    if 'greenhouseID' in params:
        # Add the device ID in the greenhouse's devices list
        greenhouseID = int(params['greenhouseID'])
        greenhouse = next((gh for gh in catalog["greenhousesList"] if gh["greenhouseID"] == greenhouseID), None)
        device = {"deviceID": dict_body["deviceID"]}
        greenhouse["devices"].append(device)

    elif 'zoneID' in params:
        # Add the device ID in the zone's devices list
        zoneID = int(params['zoneID'])
        zone = next((zn for zn in catalog["zonesList"] if zn["zoneID"] == zoneID), None)
        device = {"deviceID": dict_body["deviceID"]}
        zone["devices"].append(device)

    else:
        raise cherrypy.HTTPError(400, "Missing 'greenhouseID' or 'zoneID' parameter")
    
    # Add the device info in the catalog
    dict_body['lastUpdate'] = last_update
    catalog["devicesList"].append(dict_body)
    return f"Device with ID {dict_body['deviceID']} has been added"

def update_device(catalog, dict_body, last_update):
    """
    Update a device.

    Parameters:
        catalog (dict): catalog.
        dict_body (dict): updated device.
        last_update (str): formatted timestamp of the update.

    Returns:
        str: success message.
    """
    
    deviceID = dict_body['deviceID']
    device = next((d for d in catalog["devicesList"] if d["deviceID"] == deviceID), None)

    if not device:
        raise cherrypy.HTTPError(404, f'Device with ID {deviceID} not found')

    dict_body['lastUpdate'] = last_update
    catalog["devicesList"] = [
        dict_body if d["deviceID"] == deviceID else d 
        for d in catalog["devicesList"]
    ]

    return f"Device with ID {deviceID} updated successfully"

def remove_device(catalog, resource_id):
    """
    Remove a device from the devices list and from its greenhouse's or zone's devices.

    Parameters:
        catalog (dict): catalog.
        resource_id (int): ID of the device to remove.

    Returns:
        str: success message.
    """

    device = next((d for d in catalog["devicesList"] if d["deviceID"] == resource_id), None)
    if not device:
        raise cherrypy.HTTPError(404, f"Device with ID {resource_id} not found")

    # Remove device from devicesList
    catalog["devicesList"] = [d for d in catalog["devicesList"] if d["deviceID"] != resource_id]

    # Remove device ID from any greenhouse's and zone's devices list
    resource = {"deviceID": resource_id}
    for gh in catalog["greenhousesList"]:   
        if "devices" in gh and resource in gh["devices"]:
            gh["devices"].remove(resource)
    for zn in catalog["zonesList"]:   
        if "devices" in zn and resource in zn["devices"]:
            zn["devices"].remove(resource)

    return f"Device with ID {resource_id} has been removed"

# - Services

def add_service(catalog, dict_body, last_update):
    """
    Add a services to the services list.

    Parameters:
        catalog (dict): catalog.
        dict_body (dict): device to add.
        last_update (str): formatted timestamp of the update.

    Returns:
        str: success message.
    """

    if any(s['serviceID'] == dict_body['serviceID'] for s in catalog["servicesList"]):
        raise cherrypy.HTTPError(400, 'SERVICE ALREADY REGISTERED')
    
    dict_body['lastUpdate'] = last_update
    catalog["servicesList"].append(dict_body)
    return f"Service with ID {dict_body['serviceID']} has been added"

def update_service(catalog, dict_body, last_update):
    """
    Update a service.

    Parameters:
        catalog (dict): catalog.
        dict_body (dict): updated service.
        last_update (str): formatted timestamp of the update.

    Returns:
        str: success message.
    """

    serviceID = dict_body['serviceID']
    service = next((s for s in catalog["servicesList"] if s["serviceID"] == serviceID), None)

    if not service:
        raise cherrypy.HTTPError(404, f'Service with ID {serviceID} not found')

    dict_body['lastUpdate'] = last_update
    catalog["servicesList"] = [
        dict_body if s["serviceID"] == serviceID else s 
        for s in catalog["servicesList"]
    ]

    return f"Service with ID {serviceID} updated successfully"

def remove_service(catalog, resource_id):
    """
    Remove a service from the services list.

    Parameters:
        catalog (dict): catalog.
        resource_id (int): ID of the service to remove.

    Returns:
        str: success message.
    """

    catalog["servicesList"] = [s for s in catalog["servicesList"] if s["ID"] != resource_id]
    return f"Service with ID {resource_id} has been removed"

# - Greenhouses

def add_greenhouse(catalog, dict_body, params, last_update):
    """
    Add a greenhouse to the greenhouses list and to the requested user's greenhouses.

    Parameters:
        catalog (dict): catalog.
        dict_body (dict): greenhouse to add.
        params (dict): parameters of the request (containing the ID of the user in which to add the greenhouse).
        last_update (str): formatted timestamp of the update.

    Returns:
        str: success message.
    """

    greenhouseID = dict_body['greenhouseID']
    if any(gh['greenhouseID'] == greenhouseID for gh in catalog["greenhousesList"]):
        raise cherrypy.HTTPError(400, 'GREENHOUSE ALREADY REGISTERED')
    
    if 'userID' not in params:
        raise cherrypy.HTTPError(400, "Missing 'userID' parameter")

    # Add the greenhouse info in the catalog
    dict_body['lastUpdate'] = last_update
    dict_body["zones"] = []  # Initialize empty zones list
    catalog["greenhousesList"].append(dict_body)

    # Add the greenhouse id in the user greenhouses list
    userID = int(params['userID'])
    user = next((u for u in catalog["usersList"] if u["userID"] == userID), None)
    greenhouse = {"greenhouseID": greenhouseID}
    user["greenhouses"].append(greenhouse)
    return f"Greenhouse with ID {dict_body['greenhouseID']} has been added"

def update_greenhouse(catalog, dict_body, last_update):
    """
    Update a greenhouse.

    Parameters:
        catalog (dict): catalog.
        dict_body (dict): updated greenhouse.
        last_update (str): formatted timestamp of the update.

    Returns:
        str: success message.
    """

    greenhouseID = dict_body['greenhouseID']
    greenhouse = next((gh for gh in catalog["greenhousesList"] if gh["greenhouseID"] == greenhouseID), None)

    if not greenhouse:
        raise cherrypy.HTTPError(404, f'Greenhouse with ID {greenhouseID} not found')

    dict_body['lastUpdate'] = last_update
    catalog["greenhousesList"] = [
        dict_body if gh["greenhouseID"] == greenhouseID else gh 
        for gh in catalog["greenhousesList"]
    ]

    return f"Greenhouse with ID {greenhouseID} updated successfully"

def remove_greenhouse(catalog, resource_id):
    """
    Remove a greenhouse from the greenhouses list and from its user's greenhouses.
    All zones of the greenhouse and all devices in the greenhouses and its zones will be deleted as well.

    Parameters:
        catalog (dict): catalog.
        resource_id (int): ID of the greenhouse to remove.

    Returns:
        str: success message.
    """

    greenhouse = next((gh for gh in catalog["greenhousesList"] if gh["greenhouseID"] == resource_id), None)
    if not greenhouse:
        raise cherrypy.HTTPError(404, f"Greenhouse with ID {resource_id} not found")
    
    # Remove the devices in the greenhouse
    devices = greenhouse.get("devices", [])
    for device in devices:
        remove_device(catalog, device["deviceID"])

    # Remove the zones in the greenhouse (and their devices)
    zones = greenhouse.get("zones", [])
    for zone in zones:
        remove_zone(catalog, zone["zoneID"])

    # Remove greenhouse from greenhousesList
    catalog["greenhousesList"] = [gh for gh in catalog["greenhousesList"] if gh["greenhouseID"] != resource_id]
    
    # Remove greenhouse ID from any user's greenhouses list
    resource = {"greenhouseID": resource_id}
    for u in catalog["usersList"]:
        if "greenhouses" in u and resource in u["greenhouses"]:
            u["greenhouses"].remove(resource)

    return f"Greenhouse with ID {resource_id} has been removed"

def get_greenhouse(catalog, params):
    """
    Return the list of all greenhouses or a list containing the requested greenhouse, depending on the params.

    Parameters:
        catalog (dict): catalog.
        params (dict): parameters of the request (containing the ID of the requested greenhouse or nothing).

    Returns:
        dict: dictionnary containing the greenhouse(s) requested.
    """

    # Return the requested greenhouse
    if 'greenhouseID' in params:
        greenhouseID = int(params['greenhouseID'])
        greenhouse = next((gh for gh in catalog["greenhousesList"] if gh["greenhouseID"] == greenhouseID), None)
        if greenhouse:
            return {"greenhousesList": [greenhouse]}
        else:
            raise cherrypy.HTTPError(404, f"Greenhouse with ID {greenhouseID} not found.")
    
    # Return all greenhouses
    else:
        return {"greenhousesList": catalog["greenhousesList"]}

# - Zones

def add_zone(catalog, dict_body, params, last_update):
    """
    Add a zone to the zones list and to the requested greenhouse's zones.
    Before adding the zone, a check is done on its temperature range so that it overlaps with the ones of the other zones of the greenhouse.
    A check is also done on the moisture threshold to verify it has an allowed value.

    Parameters:
        catalog (dict): catalog.
        dict_body (dict): zone to add.
        params (dict): parameters of the request (containing the ID of the greenhouse in which to add the zone).
        last_update (str): formatted timestamp of the update.

    Returns:
        str: success message.
    """

    if any(zn['zoneID'] == dict_body['zoneID'] for zn in catalog["zonesList"]):
        raise cherrypy.HTTPError(400, 'ZONE ALREADY REGISTERED')
    
    if 'greenhouseID' not in params:
        raise cherrypy.HTTPError(400, "Missing 'greenhouseID' parameter")

    greenhouseID = int(params['greenhouseID'])
    greenhouse = next((gh for gh in catalog["greenhousesList"] if gh["zoneID"] == greenhouseID), None)
    if not greenhouse:
        raise cherrypy.HTTPError(404, f'Greenhouse ID {greenhouseID} not found')

    # Check that the zone's temperature range overlaps with the ones of the other zones in the greenhouse
    zone_temp_range = dict_body['temperatureRange']
    existing_zones = get_zones_of_greenhouse(catalog, greenhouseID)
    overlap = check_range_overlap(existing_zones, zone_temp_range)

    # Check that the moisture threshold is present and is a float between 0 and 100
    valid_threshold = check_moisture_threshold(dict_body)

    if not overlap:
        raise cherrypy.HTTPError(400, f'Temperature range of new zone does NOT overlap with existing zones: {new_range}')

    # If both tests are passed, add the zone to the zones list
    elif valid_threshold:
        dict_body['lastUpdate'] = last_update
        catalog["zonesList"].append(dict_body)

        # Add the zone id in the greenhouse zones list
        zone = {"zoneID": dict_body["zoneID"]}
        greenhouse["zones"].append(zone)
        return f"Zone with ID {dict_body['zoneID']} added to Greenhouse {greenhouseID}"

def update_zone(catalog, dict_body, params, last_update):
    """
    Update a zone.
    Before adding the zone, a check is done on its temperature range so that it overlaps with the ones of the other zones of the greenhouse.
    A check is also done on the moisture threshold to verify it has an allowed value.

    Parameters:
        catalog (dict): catalog.
        dict_body (dict): updated zone.
        last_update (str): formatted timestamp of the update.

    Returns:
        str: success message.
    """

    if 'greenhouseID' not in params:
        raise cherrypy.HTTPError(400, "Missing 'greenhouseID' parameter")

    greenhouseID = int(params['greenhouseID'])
    zone = next((z for z in catalog["zonesList"] if z["zoneID"] == dict_body["zoneID"]), None)
    if not zone:
        raise cherrypy.HTTPError(404, 'ZONE NOT FOUND')

    # Check that the temperature range overlaps with the ones of the other zones of the greenhouse
    new_range = dict_body["temperatureRange"]
    existing_zones = get_zones_of_greenhouse(catalog, greenhouseID)
    overlap = check_range_overlap(existing_zones, new_range)

    # Check that the moisture threshold is present and is a float between 0 and 100
    valid_threshold = check_moisture_threshold(dict_body)

    if not overlap:
        raise cherrypy.HTTPError(400, f'Temperature range of new zone does NOT overlap with existing zones: {new_range}')

    # If both tests are passed, update zone
    elif valid_threshold:
        dict_body['lastUpdate'] = last_update
        catalog["zonesList"] = [
            dict_body if z["zoneID"] == dict_body["zoneID"] else z 
            for z in catalog["zonesList"]
        ]
        return f"Zone with ID {dict_body['zoneID']} updated successfully"

def update_moisture_threshold(catalog, dict_body, last_update):
    """
    Update the moisture threshold of the requested zone.
    Before adding the zone, a check is done on the moisture threshold to verify it has an allowed value.

    Parameters:
        catalog (dict): catalog.
        dict_body (dict): dictionnary containing the zone ID and the amount to add to the moisture threshold.
        last_update (str): formatted timestamp of the update.

    Returns:
        str: success message.
    """

    zoneID = dict_body["zoneID"]
    threshold_delta = dict_body["thresholdDelta"]

    # Get the current zone data
    zone = next((z for z in catalog["zonesList"] if z["zoneID"] == zoneID), None)
    if not zone:
        raise cherrypy.HTTPError(404, 'ZONE NOT FOUND')

    # Compute the new moisture threshold
    old_threshold = zone["moistureThreshold"]
    new_threshold = old_threshold + threshold_delta
    threshold_dioct = {"moistureThreshold": new_threshold}

    # Check that the moisture threshold is present and is a float between 0 and 100
    valid_threshold = check_moisture_threshold(threshold_dioct)

    # If both tests are passed, update zone
    if valid_threshold:
        zone['lastUpdate'] = last_update
        zone["moistureThreshold"] = new_threshold
        return f"Moisture theshold of zone {dict_body['zoneID']} updated successfully"

def remove_zone(catalog, resource_id):
    """
    Remove a zone from the zones list and from its greenhouse's zones.
    All devices in the zones will be deleted as well.

    Parameters:
        catalog (dict): catalog.
        resource_id (int): ID of the zone to remove.

    Returns:
        str: success message.
    """

    zone = next((z for z in catalog["zonesList"] if z["zoneID"] == resource_id), None)
    if not zone:
        raise cherrypy.HTTPError(404, f"Zone with ID {resource_id} not found")
    
    # Remove the devices in the zones
    devices = zone.get("devices", [])
    for device in devices:
        remove_device(catalog, device["deviceID"])

    # Remove the zone from the zones list
    catalog["zonesList"] = [z for z in catalog["zonesList"] if z["zoneID"] != resource_id]

    # Remove zone ID from any greenhouse's zones
    for gh in catalog["greenhousesList"]:
        resource = {"zoneID": resource_id}
        if "zones" in gh and resource in gh["zones"]:
            gh["zones"].remove(resource)

    return f"Zone with ID {resource_id} has been deleted and removed from its greenhouse"

def get_zonesID(catalog, params):
    """
    Return the list of zones ID in the requested greenhouse.

    Parameters:
        catalog (dict): catalog.
        params (dict): parameters of the request (containing the ID of the requested greenhouse).

    Returns:
        dict: dictionnary containing the zones ID requested.
    """

    if 'greenhouseID' not in params:
        raise cherrypy.HTTPError(400, "Missing 'greenhouseID' parameter")

    greenhouseID = int(params['greenhouseID'])
    greenhouse = next((gh for gh in catalog["greenhousesList"] if gh["greenhouseID"] == greenhouseID), None)
    if not greenhouse:
        raise cherrypy.HTTPError(404, f"Greenhouse with ID {greenhouseID} not found")

    return {"zones": greenhouse.get("zones", [])}

def get_zones(catalog, params):
    """
    Return the list of all zones or a list containing the zones in the requested greenhouse or a list containing the requested zone, depending on the params.

    Parameters:
        catalog (dict): catalog.
        params (dict): parameters of the request (containing the ID of the requested zone or greenhouse or nothing).

    Returns:
        dict: dictionnary containing the zone(s) requested.
    """

    if 'zoneID' in params:
        # Return one zone by ID
        zoneID = int(params['zoneID'])
        zone = next((z for z in catalog["zonesList"] if z["zoneID"] == zoneID), None)
        if not zone:
            raise cherrypy.HTTPError(404, f"Zone with ID {zoneID} not found")
        return {"zonesList": [zone]}

    elif 'greenhouseID' in params:
        # Return all zones belonging to a greenhouse
        greenhouseID = int(params['greenhouseID'])
        zones = get_zones_of_greenhouse(catalog, greenhouseID)
        return {"zonesList": zones}

    else:
        # Return all zones
        return {"zonesList": catalog["zonesList"]}

def get_zones_of_greenhouse(catalog, greenhouseID):
    """
    Return the list of zones in the requested greenhouse.

    Parameters:
        catalog (dict): catalog.
        greenhouseID (int): ID of the requested greenhouse.

    Returns:
        list: list of the zones of the requested greenhouse.
    """

    # Get the list of zone IDs from the greenhouse
    greenhouse = next((gh for gh in catalog["greenhousesList"] if gh["greenhouseID"] == greenhouseID), None)
    if not greenhouse:
        return []

    zone_ids_dict = greenhouse.get("zones", [])
    zone_ids = [zone["zoneID"] for zone in zone_ids_dict]
    return [zone for zone in catalog["zonesList"] if zone["zoneID"] in zone_ids]

def check_range_overlap(existing_zones, zone_temp_range):
    """
    Check that the provided range overlaps with all existing ranges.

    Parameters:
        zone_temp_range (dict): dictionnary containing the minimum and maximum temperature allowed for the zone.
        existing_zones (list): list of dictionnaries containing the minimum and maximum temperature for the other zones of the greenhouse.

    Returns:
        boolean: true if the ranges overlap, false otherwise.
    """

    for existing_zone in existing_zones:
        existing_range = existing_zone["temperatureRange"]
        overlap = not (zone_temp_range["max"] < existing_range["min"] or zone_temp_range["min"] > existing_range["max"])
        return overlap

def check_moisture_threshold(dict_body):
    """
    Check that the moisture threshold is present in the zone and has a valid value.

    Parameters:
        dict_body (dict): zone for which to check the moisture threshold.

    Returns:
        boolean: true if the moisture threshold is valid, false otherwise.
    """

    valid_threshold = False
    if "moistureThreshold" in dict_body.keys():
        try:
            # validate it is within 0–100
            new_mt = float(dict_body["moistureThreshold"])
            valid_threshold = (0 <= new_mt <= 100)
            if not valid_threshold:
                raise cherrypy.HTTPError(400, f"Zone {dict_body['zoneID']}: moistureThreshold must be between 0 and 100")
        except ValueError:
            raise cherrypy.HTTPError(400, f"Zone {dict_body['zoneID']}: moistureThreshold must be a float")
    else:
        raise cherrypy.HTTPError(400, f"Zone {dict_body['zoneID']}: moistureThreshold must be provided")
    return valid_threshold

# - Users

def add_user(catalog, dict_body, last_update):
    """
    Add a device to the devices list and in the requested greenhouse's or zone's devices.

    Parameters:
        catalog (dict): catalog.
        dict_body (dict): device to add.
        params (dict): parameters of the request (containing the ID of the greenhouse or zone in which to add the device).
        last_update (str): formatted timestamp of the update.

    Returns:
        str: success message.
    """

    if any(user['userID'] == dict_body['userID'] for user in catalog["usersList"]):
        raise cherrypy.HTTPError(400, 'USER ALREADY REGISTERED')
    dict_body['lastUpdate'] = last_update
    catalog["usersList"].append(dict_body)
    return f"User with ID {dict_body['userID']} has been added"

def update_user(catalog, dict_body, last_update):
    """
    Update a device.

    Parameters:
        catalog (dict): catalog.
        dict_body (dict): updated device.
        last_update (str): formatted timestamp of the update.

    Returns:
        str: success message.
    """

    user = next((u for u in catalog["usersList"] if u["userID"] == dict_body["userID"]), None)
    if not user:
        raise cherrypy.HTTPError(404, 'USER NOT FOUND')

    dict_body['lastUpdate'] = last_update
    catalog["usersList"] = [
        dict_body if u["userID"] == dict_body["userID"] else u 
        for u in catalog["usersList"]
    ]
    return f"User with ID {dict_body['userID']} updated successfully"

def remove_user(catalog, resource_id):
    """
    Remove a device from the devices list and from its greenhouse's or zone's devices.

    Parameters:
        catalog (dict): catalog.
        resource_id (int): ID of the device to remove.

    Returns:
        str: success message.
    """

    user_exists = any(u["userID"] == resource_id for u in catalog["usersList"])
    if not user_exists:
        raise cherrypy.HTTPError(404, f"User with ID {resource_id} not found")
    catalog["usersList"] = [u for u in catalog["usersList"] if u["userID"] != resource_id]
    return f"User with ID {resource_id} has been removed"

class CatalogREST(object):
    exposed = True

    def __init__(self, catalog_address):
        """
        Initialize Catalog.
        
        Parameters:
            catalog_address (str): Path of the catalog.json file.
        """
        self.catalog_address = catalog_address
    
    def GET(self, *uri, **params):
        """
        GET method with different urls:
            'all': returns the full catalog.
            'devices': returns the list of all devices.
            'services': returns the list of all services.
            'greenhouses': returns the list of all greenhouses or a list containing the requested greenhouse, depending on the params.
            'zonesID': returns the list of zones ID in the requested greenhouse.
            'zones': returns the list of all zones, of zones in the requested greenhouse or a list containing the requested zone, depending on the params.
            'users': returns the list of all users.

        Parameters:
            uri (list): uri of the request.
            params (dict): params of the request.

        Returns:
            json: json containing the response.
    """

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
            output = get_greenhouse(catalog, params)
            
        elif uri[0] == 'zonesID':
            output = get_zonesID(catalog, params)

        elif uri[0] == 'zones':
            output = get_zones(catalog, params)

        elif uri[0] == 'users':
            output = {"usersList": catalog["usersList"]}
            
        else:
            raise cherrypy.HTTPError(400, 'INVALID ENDPOINT')

        return json.dumps(output)

    def POST(self, *uri, **params):
        """
        POST method with different urls:
            'devices': add a device in the list of devices and to the requested greenhouse's or zone's devices.
            'services': add a service the list of services.
            'greenhouses': add a greenhouse in the list of greenhouses and to the requested user's greenhouses.
            'zones': add a zone the list of zones and to the requested greenhouse's zones.
            'users': add a user to the list of users.

        Parameters:
            uri (list): uri of the request.
            params (dict): params of the request.

        Returns:
            json: json containing the success message.
        """

        catalog = json.load(open(self.catalog_address, "r"))
        body = cherrypy.request.body.read()
        dict_body = json.loads(body.decode('utf-8'))
        last_update = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        if uri[0] == 'devices':
            output = add_device(catalog, dict_body, params, last_update)
            
        elif uri[0] == 'services':
            output = add_service(catalog, dict_body, last_update)

        elif uri[0] == 'greenhouses':
            output = add_greenhouse(catalog, dict_body, params, last_update)
            
        elif uri[0] == 'zones':
            output = add_zone(catalog, dict_body, params, last_update)
            
        elif uri[0] == 'users':
            output = add_user(catalog, dict_body, last_update)
            
        else:
            raise cherrypy.HTTPError(400, 'INVALID ENDPOINT')
        
        # Update the catalog's lastUpdate field
        catalog["lastUpdate"] = last_update

        # Save updated catalog
        json.dump(catalog, open(self.catalog_address, "w"), indent=4)

        print(output)
        return json.dumps({"message": output})
    
    def PUT(self, *uri, **params):
        """
        PUT method with different urls:
            'devices': update the requested device.
            'services': update the requested service.
            'greenhouses': update the requested greenhouse.
            'zones': update the requested zone.
            'threshold': update the moisture threshold of the requested zone.
            'users': update the requested user.

        Parameters:
            uri (list): uri of the request.
            params (dict): params of the request.

        Returns:
            json: json containing the success message.
        """

        catalog = json.load(open(self.catalog_address, "r"))
        body = cherrypy.request.body.read()
        dict_body = json.loads(body.decode('utf-8'))
        last_update = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        if uri[0] == 'devices':
            output = update_device(catalog, dict_body, last_update)
            
        elif uri[0] == 'services':
            output = update_service(catalog, dict_body, last_update)
            
        elif uri[0] == 'greenhouses':
            output = update_greenhouse(catalog, dict_body, last_update)
            
        elif uri[0] == 'zones':
            output = update_zone(catalog, dict_body, params, last_update)
        
        elif uri[0] == 'threshold':
            output = update_moisture_threshold(catalog, dict_body, last_update)

        elif uri[0] == 'users':
            output = update_user(catalog, dict_body, last_update)
            
        else:
            raise cherrypy.HTTPError(400, 'INVALID ENDPOINT')

        # Update the catalog's lastUpdate field
        catalog["lastUpdate"] = last_update

        # Save updated catalog
        json.dump(catalog, open(self.catalog_address, "w"), indent=4)
        
        print(output)
        return json.dumps({"message": output})

    def DELETE(self, *uri):
        """
        DELETE method with different urls:
            'devices': delete the requested device from the devices list and from its greenhouse's or zone's devices.
            'services': delete the requested service from the services list.
            'greenhouses': delete the requested greenhouse from the greenhouses list and from its user's greenhouses.
            'zones': delete the requested zone from the zones list and from its greenhouse's zones.
            'users': delete the requested user from the users list.

        Parameters:
            uri (list): uri of the request.
            params (dict): params of the request.

        Returns:
            json: json containing the success message.
        """

        catalog = json.load(open(self.catalog_address, "r"))

        if len(uri) < 2:
            raise cherrypy.HTTPError(400, 'Missing resource ID in DELETE request')

        resource_type = uri[0]
        resource_id = int(uri[1])

        if resource_type == 'devices':
            output = remove_device(catalog, resource_id)
            
        elif resource_type == 'services':
            output = remove_service(catalog, resource_id)
            
        elif resource_type == 'greenhouses':
            output = remove_greenhouse(catalog, resource_id)
            
        elif resource_type == 'zones':
            output = remove_zone(catalog, resource_id)
            
        elif resource_type == 'users':
            output = remove_user(catalog, resource_id)
            
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
    cherrypy.tree.mount(catalogClient, '/', conf)
    cherrypy.engine.start()
    cherrypy.engine.block()
    cherrypy.engine.exit()
