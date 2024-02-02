# manage_sase_connections
Script to manage Prisma SD-WAN Easy Onboarding (SASE Connections).

This script can be used to manage SASE Connections created by Prisma SD-WAN Easy Onboarding. 
The script provides the following functionality:
1. Retrieve PA Locations that have BW Allocated (Action: **list_palocations**)
2. Create SASE Connections on a Site for all or listed public circuits (Action: **config_saseconn**)
3. Delete SASE Connections on a Site (Action: **delete_saseconn**)
4. Bind Security Zone to SASE tunnels (Action: **bind_zone**)

### Authentication:
Please create a Service Account via _Settings -> Identity and Access_ portal and save the client ID, client secret and TSG ID in the **prismasase_settings.py** file.

```
PRISMASASE_CLIENT_ID="paste client ID"
PRISMASASE_CLIENT_SECRET="paste client secret"
PRISMASASE_TSG_ID="paste TSG ID"
```

### Requirements
* Active Prisma SD-WAN Account
* Python >=3.7
* Python modules:
    * Prisma SASE Python SDK >= 6.3.1b1 - <https://github.com/PaloAltoNetworks/prisma-sase-sdk-python>

### License
MIT

### Installation:
 - **Github:** Download files to a local directory, manually run the scripts

### Usage:
#### List PA Locations 
List PA Locations that have bandwidth allocated
```
./manage_sase_connection.py -A list_palocations
```

Here's a sample response:
```angular2html
Here are the PA Locations with allocated BW:
canada-central-toronto
	Canada Central [canada-central]: 500 Mbps
us-southwest
	US Southwest [us-west-201]: 500 Mbps
	US West [us-west-1]: 500 Mbps
asia-south
	Bangladesh [bangladesh]: 100 Mbps
	India South [india-south]: 100 Mbps
	India West [ap-south-1]: 100 Mbps
	Pakistan South [pakistan-south]: 100 Mbps
	Pakistan West [pakistan-west]: 100 Mbps
asia-southeast
	Cambodia [cambodia]: 100 Mbps
	Malaysia [malaysia]: 100 Mbps
	Myanmar [myanmar]: 100 Mbps
	Pakistan West (II) [pakistan-west-2]: 100 Mbps
	Philippines [philippines]: 100 Mbps
	Singapore [ap-southeast-1]: 100 Mbps
	Sri Lanka [srilanka]: 100 Mbps
	Thailand [thailand]: 100 Mbps
	Vietnam [vietnam]: 100 Mbps
us-east-miami
	US-Southeast (Miami)** [us-east-1-miami]: 50 Mbps
```
Note: The Prisma Access Location for creating the SASE connection needs to be extracted from the above response.
For eg: to create tunnels to the **US Southwest** location, provide the value **us-west-201**


#### Create SASE Connection
Create SASE tunnels on all public circuits at a Site
```
./manage_sase_connection.py -S <SiteName> -CN ALL -A config_saseconn -PL <pa_location>
```
Create SASE tunnel on a few circuits at a site
```
/manage_sase_connection.py -S <SiteName> -CN "<CircuitName1>,<CircuitName2>" -A config_saseconn -PL <pa_location>
```

#### Delete SASE Connection
Delete tunnels created to Prisma Access at a site
```
./manage_sase_connection.py -S <SiteName> -A delete_saseconn
```
#### Bind Security Zone
Bind security zone to SASE tunnels
```
./manage_sase_connection.py -S <SiteName> -A bind_zone -Z <ZoneName>
```


### Help Text:
```
(base) Tanushree's Macbook Pro:policy_config tkamath$ ./manage_sase_connection.py -h
usage: manage_sase_connection.py [-h] [--action ACTION] [--sitename SITENAME] [--palocation PALOCATION] [--circuit_names CIRCUIT_NAMES]

Prisma SD-WAN UTD Lab Setup.

optional arguments:
  -h, --help            show this help message and exit

Config:
  Details for the tenant you wish to operate

  --action ACTION, -A ACTION
                        Action. Allowed Actions: list_palocations, delete_saseconn, config_saseconn
  --sitename SITENAME, -S SITENAME
                        Site Name
  --palocation PALOCATION, -PL PALOCATION
                        PA Location
  --circuit_names CIRCUIT_NAMES, -CN CIRCUIT_NAMES
                        Comma separated circuit list (Site WAN Interface Names). For all public circuits, use keyword: ALL
(base) Tanushree's Macbook Pro:policy_config tkamath$
```

### Version
| Version | Build | Changes |
| ------- | ----- | ------- |
| **1.0.0** | **b2** | Added support to bind security zones to SASE tunnels |
|           | **b1** | Initial Release |
