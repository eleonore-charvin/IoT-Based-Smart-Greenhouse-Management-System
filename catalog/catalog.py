import cherrypy
import json
import time

class CatalogREST(object):
    exposed = True

    def __init__(self, catalog_address):
        """
        Initialize Catalog.
        
        Parameters:
            catalog_address (str): Path of the catalog.json file.
        """
        self.catalog_address = catalog_address
        self.catalog = json.load(open(self.catalog_address, "r"))
        self.inactive_threshold = 80 # devices and services who have not updated their registration for 80 s are consider inactive
    
    # - Users

    def get_users(self, params):
        """
        Return the list of all users or a list containing the requested user, depending on the params.

        Parameters:
            params (dict): parameters of the request (containing the ID of the requested user or nothing).

        Returns:
            dict: dictionnary containing the user(s) requested.
        """

        # Return the requested user
        if 'userID' in params:
            userID = int(params['userID'])
            user = next((u for u in self.catalog["usersList"] if u["userID"] == userID), None)
            if user:
                return {"usersList": [user]}
            else:
                raise cherrypy.HTTPError(404, f"User with ID {userID} not found.")
        
        # Return all users
        else:
            return {"usersList": self.catalog["usersList"]}

    # - Devices

    def add_device(self, dict_body, params, last_update):
        """
        Add a device to the devices list and to the requested greenhouse's or zone's devices.

        Parameters:
            dict_body (dict): device to add.
            params (dict): parameters of the request (containing the ID of the greenhouse or zone in which to add the device).
            last_update (str): formatted timestamp of the update.

        Returns:
            str: success message.
        """
        
        if any(d['deviceID'] == dict_body['deviceID'] for d in self.catalog["devicesList"]):
            raise cherrypy.HTTPError(400, 'DEVICE ALREADY REGISTERED')
        
        if 'greenhouseID' in params:
            # Add the device ID in the greenhouse's devices list
            greenhouseID = int(params['greenhouseID'])
            greenhouse = next((gh for gh in self.catalog["greenhousesList"] if gh["greenhouseID"] == greenhouseID), None)
            device = {"deviceID": dict_body["deviceID"]}
            greenhouse["devices"].append(device)

        elif 'zoneID' in params:
            # Add the device ID in the zone's devices list
            zoneID = int(params['zoneID'])
            zone = next((zn for zn in self.catalog["zonesList"] if zn["zoneID"] == zoneID), None)
            device = {"deviceID": dict_body["deviceID"]}
            zone["devices"].append(device)

        else:
            raise cherrypy.HTTPError(400, "Missing 'greenhouseID' or 'zoneID' parameter")
        
        # Add the device info in the catalog
        dict_body['lastUpdate'] = last_update
        self.catalog["devicesList"].append(dict_body)
        return f"Device with ID {dict_body['deviceID']} has been added"

    def update_device(self, dict_body, last_update):
        """
        Update a device.

        Parameters:
            dict_body (dict): updated device.
            last_update (str): formatted timestamp of the update.

        Returns:
            str: success message.
        """
        
        deviceID = dict_body['deviceID']
        device = next((d for d in self.catalog["devicesList"] if d["deviceID"] == deviceID), None)

        if not device:
            raise cherrypy.HTTPError(404, f'Device with ID {deviceID} not found')

        dict_body['lastUpdate'] = last_update
        self.catalog["devicesList"] = [
            dict_body if d["deviceID"] == deviceID else d 
            for d in self.catalog["devicesList"]
        ]

        return f"Device with ID {deviceID} updated successfully"

    def remove_device(self, resource_id):
        """
        Remove a device from the devices list and from its greenhouse's or zone's devices.

        Parameters:
            resource_id (int): ID of the device to remove.

        Returns:
            str: success message.
        """

        device = next((d for d in self.catalog["devicesList"] if d["deviceID"] == resource_id), None)
        if not device:
            raise cherrypy.HTTPError(404, f"Device with ID {resource_id} not found")

        # Remove device from devicesList
        self.catalog["devicesList"] = [d for d in self.catalog["devicesList"] if d["deviceID"] != resource_id]

        # Remove device ID from any greenhouse's and zone's devices list
        resource = {"deviceID": resource_id}
        for gh in self.catalog["greenhousesList"]:   
            if "devices" in gh and resource in gh["devices"]:
                gh["devices"].remove(resource)
        for zn in self.catalog["zonesList"]:   
            if "devices" in zn and resource in zn["devices"]:
                zn["devices"].remove(resource)

        return f"Device with ID {resource_id} has been removed"

    def clean_devices(self):
        """
        Remove inactive devices from the services list.
        """

        current_time = time.time()
        devices_removed = []
        for device in self.catalog["devicesList"]:
            last_update = device["lastUpdate"]
            if (current_time - last_update) < self.inactive_threshold:
                deviceID = device["deviceID"]
                self.remove_device(deviceID)
                devices_removed.append(deviceID)
        print(f"Devices with ID {devices_removed} have been removed because they were inactive")

    # - Services

    def add_service(self, dict_body, last_update):
        """
        Add a services to the services list.

        Parameters:
            dict_body (dict): device to add.
            last_update (str): formatted timestamp of the update.

        Returns:
            str: success message.
        """

        if any(s['serviceID'] == dict_body['serviceID'] for s in self.catalog["servicesList"]):
            raise cherrypy.HTTPError(400, 'SERVICE ALREADY REGISTERED')
        
        dict_body['lastUpdate'] = last_update
        self.catalog["servicesList"].append(dict_body)
        return f"Service with ID {dict_body['serviceID']} has been added"

    def update_service(self, dict_body, last_update):
        """
        Update a service.

        Parameters:
            dict_body (dict): updated service.
            last_update (str): formatted timestamp of the update.

        Returns:
            str: success message.
        """

        serviceID = dict_body['serviceID']
        service = next((s for s in self.catalog["servicesList"] if s["serviceID"] == serviceID), None)

        if not service:
            raise cherrypy.HTTPError(404, f'Service with ID {serviceID} not found')

        dict_body['lastUpdate'] = last_update
        self.catalog["servicesList"] = [
            dict_body if s["serviceID"] == serviceID else s 
            for s in self.catalog["servicesList"]
        ]

        return f"Service with ID {serviceID} updated successfully"

    def remove_service(self, resource_id):
        """
        Remove a service from the services list.

        Parameters:
            resource_id (int): ID of the service to remove.

        Returns:
            str: success message.
        """

        self.catalog["servicesList"] = [s for s in self.catalog["servicesList"] if s["ID"] != resource_id]
        return f"Service with ID {resource_id} has been removed"

    def clean_services(self):
        """
        Remove inactive services from the services list.
        """

        current_time = time.time()
        services_removed = []
        for service in self.catalog["servicesList"]:
            last_update = service["lastUpdate"]
            if (current_time - last_update) < self.inactive_threshold:
                serviceID = service["serviceID"]
                self.remove_service(serviceID)
                services_removed.append(serviceID)
        print(f"Services with ID {services_removed} have been removed because they were inactive")

    # - Greenhouses

    def add_greenhouse(self, dict_body, params, last_update):
        """
        Add a greenhouse to the greenhouses list and to the requested user's greenhouses.

        Parameters:
            dict_body (dict): greenhouse to add.
            params (dict): parameters of the request (containing the ID of the user in which to add the greenhouse).
            last_update (str): formatted timestamp of the update.

        Returns:
            str: success message.
        """

        greenhouseID = dict_body['greenhouseID']
        if any(gh['greenhouseID'] == greenhouseID for gh in self.catalog["greenhousesList"]):
            raise cherrypy.HTTPError(400, 'GREENHOUSE ALREADY REGISTERED')
        
        if 'userID' not in params:
            raise cherrypy.HTTPError(400, "Missing 'userID' parameter")

        # Add the greenhouse info in the catalog
        dict_body['lastUpdate'] = last_update
        dict_body["zones"] = []  # Initialize empty zones list
        self.catalog["greenhousesList"].append(dict_body)

        # Add the greenhouse id in the user greenhouses list
        userID = int(params['userID'])
        user = next((u for u in self.catalog["usersList"] if u["userID"] == userID), None)
        greenhouse = {"greenhouseID": greenhouseID}
        user["greenhouses"].append(greenhouse)
        return f"Greenhouse with ID {dict_body['greenhouseID']} has been added"

    def update_greenhouse(self, dict_body, last_update):
        """
        Update a greenhouse.

        Parameters:
            dict_body (dict): updated greenhouse.
            last_update (str): formatted timestamp of the update.

        Returns:
            str: success message.
        """

        greenhouseID = dict_body['greenhouseID']
        greenhouse = next((gh for gh in self.catalog["greenhousesList"] if gh["greenhouseID"] == greenhouseID), None)

        if not greenhouse:
            raise cherrypy.HTTPError(404, f'Greenhouse with ID {greenhouseID} not found')

        dict_body['lastUpdate'] = last_update
        self.catalog["greenhousesList"] = [
            dict_body if gh["greenhouseID"] == greenhouseID else gh 
            for gh in self.catalog["greenhousesList"]
        ]

        return f"Greenhouse with ID {greenhouseID} updated successfully"

    def remove_greenhouse(self, resource_id):
        """
        Remove a greenhouse from the greenhouses list and from its user's greenhouses.
        All zones of the greenhouse and all devices in the greenhouse and its zones will be deleted as well.

        Parameters:
            resource_id (int): ID of the greenhouse to remove.

        Returns:
            str: success message.
        """

        greenhouse = next((gh for gh in self.catalog["greenhousesList"] if gh["greenhouseID"] == resource_id), None)
        if not greenhouse:
            raise cherrypy.HTTPError(404, f"Greenhouse with ID {resource_id} not found")
        
        # Remove the devices in the greenhouse
        devices = greenhouse.get("devices", [])
        for device in devices:
            self.remove_device(device["deviceID"])

        # Remove the zones in the greenhouse (and their devices)
        zones = greenhouse.get("zones", [])
        for zone in zones:
            self.remove_zone(zone["zoneID"])

        # Remove greenhouse from greenhousesList
        self.catalog["greenhousesList"] = [gh for gh in self.catalog["greenhousesList"] if gh["greenhouseID"] != resource_id]
        
        # Remove greenhouse ID from any user's greenhouses list
        resource = {"greenhouseID": resource_id}
        for u in self.catalog["usersList"]:
            if "greenhouses" in u and resource in u["greenhouses"]:
                u["greenhouses"].remove(resource)

        return f"Greenhouse with ID {resource_id} has been removed"

    def get_greenhouse(self, params):
        """
        Return the list of all greenhouses, or of greenhouses of a user, or a list containing the requested greenhouse, depending on the params.

        Parameters:
            params (dict): parameters of the request (containing the ID of the requested greenhouse, or of the user, or nothing).

        Returns:
            dict: dictionnary containing the greenhouse(s) requested.
        """

        # Return the requested greenhouse
        if 'greenhouseID' in params:
            greenhouseID = int(params['greenhouseID'])
            greenhouse = next((gh for gh in self.catalog["greenhousesList"] if gh["greenhouseID"] == greenhouseID), None)
            if greenhouse:
                return {"greenhousesList": [greenhouse]}
            else:
                raise cherrypy.HTTPError(404, f"Greenhouse with ID {greenhouseID} not found.")
        
        # Return the greenhouses of the user
        elif 'userID' in params:
            userID = int(params['userID'])
            greenhouses = self.get_greenhouses_of_user(userID)
            if greenhouses:
                return {"greenhousesList": greenhouses}
            else:
                raise cherrypy.HTTPError(404, f"No greenhouses found for user with ID {userID}.")
        
        # Return all greenhouses
        else:
            return {"greenhousesList": self.catalog["greenhousesList"]}

    def get_greenhouses_of_user(self, userID):
        """
        Return the list of greenhouses of the requested user.

        Parameters:
            userID (int): ID of the requested user.

        Returns:
            list: list of the greenhouse of the requested user.
        """

        # Get the list of greenhouse IDs from the user
        user = next((u for u in self.catalog["usersList"] if u["userID"] == userID), None)
        if not user:
            return []

        greenhouse_ids_dict = user.get("greenhouses", [])
        greenhouse_ids = [greenhouse["greenhouseID"] for greenhouse in greenhouse_ids_dict]
        return [greenhouse for greenhouse in self.catalog["greenhousesList"] if greenhouse["greenhouseID"] in greenhouse_ids]

    # - Zones

    def add_zone(self, dict_body, params, last_update):
        """
        Add a zone to the zones list and to the requested greenhouse's zones.
        Before adding the zone, a check is done on its temperature range so that it overlaps with the ones of the other zones of the greenhouse.
        A check is also done on the moisture threshold to verify it has an allowed value.

        Parameters:
            dict_body (dict): zone to add.
            params (dict): parameters of the request (containing the ID of the greenhouse in which to add the zone).
            last_update (str): formatted timestamp of the update.

        Returns:
            str: success message.
        """

        if any(zn['zoneID'] == dict_body['zoneID'] for zn in self.catalog["zonesList"]):
            raise cherrypy.HTTPError(400, 'ZONE ALREADY REGISTERED')
        
        if 'greenhouseID' not in params:
            raise cherrypy.HTTPError(400, "Missing 'greenhouseID' parameter")

        greenhouseID = int(params['greenhouseID'])
        greenhouse = next((gh for gh in self.catalog["greenhousesList"] if gh["greenhouseID"] == greenhouseID), None)
        if not greenhouse:
            raise cherrypy.HTTPError(404, f'Greenhouse ID {greenhouseID} not found')

        # Check that the zone's temperature range overlaps with the ones of the other zones in the greenhouse
        zone_temp_range = dict_body['temperatureRange']
        existing_zones = self.get_zones_of_greenhouse(greenhouseID)
        if existing_zones:
            overlap = self.check_range_overlap(existing_zones, zone_temp_range)
        else:
            overlap = True

        # Check that the moisture threshold is present and is a float between 0 and 100
        valid_threshold = self.check_moisture_threshold(dict_body)

        if not overlap:
            raise cherrypy.HTTPError(400, f'Temperature range of new zone does NOT overlap with existing zones: {zone_temp_range}')

        # If both tests are passed, add the zone to the zones list
        elif valid_threshold:
            dict_body['lastUpdate'] = last_update
            self.catalog["zonesList"].append(dict_body)

            # Add the zone id in the greenhouse zones list
            zone = {"zoneID": dict_body["zoneID"]}
            greenhouse["zones"].append(zone)
            return f"Zone with ID {dict_body['zoneID']} added to Greenhouse {greenhouseID}"

    def update_zone(self, dict_body, params, last_update):
        """
        Update a zone.
        Before adding the zone, a check is done on its temperature range so that it overlaps with the ones of the other zones of the greenhouse.
        A check is also done on the moisture threshold to verify it has an allowed value.

        Parameters:
            dict_body (dict): updated zone.
            last_update (str): formatted timestamp of the update.

        Returns:
            str: success message.
        """

        if 'greenhouseID' not in params:
            raise cherrypy.HTTPError(400, "Missing 'greenhouseID' parameter")

        greenhouseID = int(params['greenhouseID'])
        zone = next((z for z in self.catalog["zonesList"] if z["zoneID"] == dict_body["zoneID"]), None)
        if not zone:
            raise cherrypy.HTTPError(404, 'ZONE NOT FOUND')

        # Check that the temperature range overlaps with the ones of the other zones of the greenhouse
        new_range = dict_body["temperatureRange"]
        existing_zones = self.get_zones_of_greenhouse(greenhouseID)
        if existing_zones:
            overlap = self.check_range_overlap(existing_zones, new_range)
        else:
            overlap = True
        
        # Check that the moisture threshold is present and is a float between 0 and 100
        valid_threshold = self.check_moisture_threshold(dict_body)

        if not overlap:
            raise cherrypy.HTTPError(400, f'Temperature range of new zone does NOT overlap with existing zones: {new_range}')

        # If both tests are passed, update zone
        elif valid_threshold:
            dict_body['lastUpdate'] = last_update
            self.catalog["zonesList"] = [
                dict_body if z["zoneID"] == dict_body["zoneID"] else z 
                for z in self.catalog["zonesList"]
            ]
            return f"Zone with ID {dict_body['zoneID']} updated successfully"

    def update_moisture_threshold(self, dict_body, last_update):
        """
        Update the moisture threshold of the requested zone.
        Before adding the zone, a check is done on the moisture threshold to verify it has an allowed value.

        Parameters:
            dict_body (dict): dictionnary containing the zone ID and the amount to add to the moisture threshold.
            last_update (str): formatted timestamp of the update.

        Returns:
            str: success message.
        """

        zoneID = dict_body["zoneID"]
        threshold_delta = dict_body["thresholdDelta"]

        # Get the current zone data
        zone = next((z for z in self.catalog["zonesList"] if z["zoneID"] == zoneID), None)
        if not zone:
            raise cherrypy.HTTPError(404, 'ZONE NOT FOUND')

        # Compute the new moisture threshold
        old_threshold = zone["moistureThreshold"]
        new_threshold = old_threshold + threshold_delta
        threshold_dioct = {"moistureThreshold": new_threshold}

        # Check that the moisture threshold is present and is a float between 0 and 100
        valid_threshold = self.check_moisture_threshold(threshold_dioct)

        # If both tests are passed, update zone
        if valid_threshold:
            zone['lastUpdate'] = last_update
            zone["moistureThreshold"] = new_threshold
            return f"Moisture theshold of zone {dict_body['zoneID']} updated successfully"

    def remove_zone(self, resource_id):
        """
        Remove a zone from the zones list and from its greenhouse's zones.
        All devices in the zones will be deleted as well.

        Parameters:
            resource_id (int): ID of the zone to remove.

        Returns:
            str: success message.
        """

        zone = next((z for z in self.catalog["zonesList"] if z["zoneID"] == resource_id), None)
        if not zone:
            raise cherrypy.HTTPError(404, f"Zone with ID {resource_id} not found")
        
        # Remove the devices in the zones
        devices = zone.get("devices", [])
        for device in devices:
            self.remove_device(device["deviceID"])

        # Remove the zone from the zones list
        self.catalog["zonesList"] = [z for z in self.catalog["zonesList"] if z["zoneID"] != resource_id]

        # Remove zone ID from any greenhouse's zones
        for gh in self.catalog["greenhousesList"]:
            resource = {"zoneID": resource_id}
            if "zones" in gh and resource in gh["zones"]:
                gh["zones"].remove(resource)

        return f"Zone with ID {resource_id} has been deleted and removed from its greenhouse"

    def get_zonesID(self, params):
        """
        Return the list of zones ID in the requested greenhouse.

        Parameters:
            params (dict): parameters of the request (containing the ID of the requested greenhouse).

        Returns:
            dict: dictionnary containing the zones ID requested.
        """

        if 'greenhouseID' not in params:
            raise cherrypy.HTTPError(400, "Missing 'greenhouseID' parameter")

        greenhouseID = int(params['greenhouseID'])
        greenhouse = next((gh for gh in self.catalog["greenhousesList"] if gh["greenhouseID"] == greenhouseID), None)
        if not greenhouse:
            raise cherrypy.HTTPError(404, f"Greenhouse with ID {greenhouseID} not found")

        return {"zones": greenhouse.get("zones", [])}

    def get_zones(self, params):
        """
        Return the list of all zones or a list containing the zones in the requested greenhouse or a list containing the requested zone, depending on the params.

        Parameters:
            params (dict): parameters of the request (containing the ID of the requested zone or greenhouse or nothing).

        Returns:
            dict: dictionnary containing the zone(s) requested.
        """

        if 'zoneID' in params:
            # Return one zone by ID
            zoneID = int(params['zoneID'])
            zone = next((z for z in self.catalog["zonesList"] if z["zoneID"] == zoneID), None)
            if not zone:
                raise cherrypy.HTTPError(404, f"Zone with ID {zoneID} not found")
            return {"zonesList": [zone]}

        elif 'greenhouseID' in params:
            # Return all zones belonging to a greenhouse
            greenhouseID = int(params['greenhouseID'])
            zones = self.get_zones_of_greenhouse(greenhouseID)
            return {"zonesList": zones}

        else:
            # Return all zones
            return {"zonesList": self.catalog["zonesList"]}

    def get_zones_of_greenhouse(self, greenhouseID):
        """
        Return the list of zones in the requested greenhouse.

        Parameters:
            greenhouseID (int): ID of the requested greenhouse.

        Returns:
            list: list of the zones of the requested greenhouse.
        """

        # Get the list of zone IDs from the greenhouse
        greenhouse = next((gh for gh in self.catalog["greenhousesList"] if gh["greenhouseID"] == greenhouseID), None)
        if not greenhouse:
            return []

        zone_ids_dict = greenhouse.get("zones", [])
        zone_ids = [zone["zoneID"] for zone in zone_ids_dict]
        return [zone for zone in self.catalog["zonesList"] if zone["zoneID"] in zone_ids]

    def check_range_overlap(self, existing_zones, zone_temp_range):
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

    def check_moisture_threshold(self, dict_body):
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

    def add_user(self, dict_body, last_update):
        """
        Add a device to the devices list and in the requested greenhouse's or zone's devices.

        Parameters:
            dict_body (dict): device to add.
            params (dict): parameters of the request (containing the ID of the greenhouse or zone in which to add the device).
            last_update (str): formatted timestamp of the update.

        Returns:
            str: success message.
        """

        if any(user['userID'] == dict_body['userID'] for user in self.catalog["usersList"]):
            raise cherrypy.HTTPError(400, 'USER ALREADY REGISTERED')
        dict_body['lastUpdate'] = last_update
        self.catalog["usersList"].append(dict_body)
        return f"User with ID {dict_body['userID']} has been added"

    def update_user(self, dict_body, last_update):
        """
        Update a device.

        Parameters:
            dict_body (dict): updated device.
            last_update (str): formatted timestamp of the update.

        Returns:
            str: success message.
        """

        user = next((u for u in self.catalog["usersList"] if u["userID"] == dict_body["userID"]), None)
        if not user:
            raise cherrypy.HTTPError(404, 'USER NOT FOUND')

        dict_body['lastUpdate'] = last_update
        self.catalog["usersList"] = [
            dict_body if u["userID"] == dict_body["userID"] else u 
            for u in self.catalog["usersList"]
        ]
        return f"User with ID {dict_body['userID']} updated successfully"

    def remove_user(self, resource_id):
        """
        Remove a device from the devices list and from its greenhouse's or zone's devices.
        All greenhouses of the user, all these greenhouses' zones and all devices in the greenhouses and their zones will be deleted as well.

        Parameters:
            resource_id (int): ID of the device to remove.

        Returns:
            str: success message.
        """

        user = next((u for u in self.catalog["usersList"] if u["userID"] == resource_id), None)
        if not user:
            raise cherrypy.HTTPError(404, f"User with ID {resource_id} not found")
        
        # Remove the greenhouses of the user (and their zones and devices)
        greenhouses = user.get("greenhouses", [])
        for greenhouse in greenhouses:
            self.remove_greenhouse(greenhouse["greenhouseID"])

        # Remove greenhouse from greenhousesList
        self.catalog["usersList"] = [u for u in self.catalog["usersList"] if u["userID"] != resource_id]
        
        return f"User with ID {resource_id} has been removed"

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

        if len(uri) == 0:
            raise cherrypy.HTTPError(400, 'UNABLE TO MANAGE THIS URL')

        if uri[0] == 'all':
            output = self.catalog

        elif uri[0] == 'devices':
            output = {"devicesList": self.catalog["devicesList"]}

        elif uri[0] == 'services':
            output = {"servicesList": self.catalog["servicesList"]}

        elif uri[0] == 'greenhouses':
            output = self.get_greenhouse(params)
            
        elif uri[0] == 'zonesID':
            output = self.get_zonesID(params)

        elif uri[0] == 'zones':
            output = self.get_zones(params)

        elif uri[0] == 'users':
            output = self.get_users(params)
            
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

        body = cherrypy.request.body.read()
        dict_body = json.loads(body.decode('utf-8'))
        last_update = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        if uri[0] == 'devices':
            output = self.add_device(dict_body, params, last_update)
            
        elif uri[0] == 'services':
            output = self.add_service(dict_body, last_update)

        elif uri[0] == 'greenhouses':
            output = self.add_greenhouse(dict_body, params, last_update)
            
        elif uri[0] == 'zones':
            output = self.add_zone(dict_body, params, last_update)
            
        elif uri[0] == 'users':
            output = self.add_user(dict_body, last_update)
            
        else:
            raise cherrypy.HTTPError(400, 'INVALID ENDPOINT')
        
        # Update the catalog's lastUpdate field
        self.catalog["lastUpdate"] = last_update

        # Save updated catalog
        json.dump(self.catalog, open(self.catalog_address, "w"), indent=4)

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

        body = cherrypy.request.body.read()
        dict_body = json.loads(body.decode('utf-8'))
        last_update = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        if uri[0] == 'devices':
            output = self.update_device(dict_body, last_update)
            
        elif uri[0] == 'services':
            output = self.update_service(dict_body, last_update)
            
        elif uri[0] == 'greenhouses':
            output = self.update_greenhouse(dict_body, last_update)
            
        elif uri[0] == 'zones':
            output = self.update_zone(dict_body, params, last_update)
        
        elif uri[0] == 'threshold':
            output = self.update_moisture_threshold(dict_body, last_update)

        elif uri[0] == 'users':
            output = self.update_user(dict_body, last_update)
            
        else:
            raise cherrypy.HTTPError(400, 'INVALID ENDPOINT')

        # Update the catalog's lastUpdate field
        self.catalog["lastUpdate"] = last_update

        # Save updated catalog
        json.dump(self.catalog, open(self.catalog_address, "w"), indent=4)
        
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

        if len(uri) < 2:
            raise cherrypy.HTTPError(400, 'Missing resource ID in DELETE request')

        resource_type = uri[0]
        resource_id = int(uri[1])

        if resource_type == 'devices':
            output = self.remove_device(resource_id)
            
        elif resource_type == 'services':
            output = self.remove_service(resource_id)
            
        elif resource_type == 'greenhouses':
            output = self.remove_greenhouse(resource_id)
            
        elif resource_type == 'zones':
            output = self.remove_zone(resource_id)
            
        elif resource_type == 'users':
            output = self.remove_user(resource_id)
            
        else:
            raise cherrypy.HTTPError(400, 'Invalid resource type for DELETE')

        # Update the catalog's lastUpdate field
        self.catalog["lastUpdate"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        # Save updated catalog
        with open(self.catalog_address, "w") as f:
            json.dump(self.catalog, f, indent=4)

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

    # Keep script running
    while True:
        time.sleep(80)
        
        # Remove the services and devices that have been inactive for too long
        catalogClient.clean_services()
        catalogClient.clean_devices()