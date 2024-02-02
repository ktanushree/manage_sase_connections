#!/usr/bin/env python

"""
Script to manage Prisma SASE Connections (Easy Onboarding)
Author: tkamath@paloaltonetworks.com
Version: 1.0.0b3
"""
import prisma_sase
import argparse
import os
import time
import yaml
import sys
import datetime

##############################################################################
# Service Account Details -
# Create a Service Account at the Master tenant level
# Grant All Apps & MSP Super Privileges
##############################################################################
try:
    from prismasase_settings import PRISMASASE_CLIENT_ID, PRISMASASE_CLIENT_SECRET, PRISMASASE_TSG_ID

except ImportError:
    PRISMASASE_CLIENT_ID = None
    PRISMASASE_CLIENT_SECRET = None
    PRISMASASE_TSG_ID = None

##############################################################################
##############################################################################
# Global dicts & variables
##############################################################################
LIST = "list_palocations"
DELETE = "delete_saseconn"
CONFIG = "config_saseconn"
BIND = "bind_zone"
ACTION = [LIST, DELETE, CONFIG, BIND]

site_id_name = {}
site_name_id = {}
spokesitenames = []
zone_id_name = {}
zone_name_id = {}
wannw_id_name = {}
wannw_name_id = {}
siteid_swinamelist = {}
siteid_swiidlist = {}
siteid_swiidname = {}
siteid_swinameid = {}
siteid_activeswiidlist = []
swis_inactive = []

siteid_elemidlist = {}
elemid_servicelinkidlist = {}
elem_id_name = {}
servicelink_id_name = {}

rnqosprofile_id_name = {}
rnqosprofile_name_id = {}
palocations_displayname_value = {}
palocations_value_displayname = {}
palocations_value_data = {}
palocations_value_aggregion = {}
palocations_aggregion_valuelist = {}

palocations_bwalloc = []
palocations_aggregion = []
palocation_value_spnnamelist = {}
palocation_value_bw = {}


def create_dicts(sase_session, action, sitename):
    global default_qos_profile_id
    default_qos_profile_id = None

    if action in [LIST, CONFIG]:
        #
        # PA Locations
        #
        print("\tPA Locations")
        resp = sase_session.rest_call("https://api.sase.paloaltonetworks.com/sse/config/v1/locations", method="GET")
        if resp.cgx_status:
            itemlist = resp.cgx_content
            for item in itemlist:
                palocations_displayname_value[item["display"]] = item["value"]
                palocations_value_displayname[item["value"]] = item["display"]
                palocations_value_aggregion[item["value"]] = item["aggregate_region"]
                if item["aggregate_region"] in palocations_aggregion_valuelist.keys():
                    value_list = palocations_aggregion_valuelist[item["aggregate_region"]]
                    value_list.append(item["value"])
                    palocations_aggregion_valuelist[item["aggregate_region"]] = value_list
                else:
                    palocations_aggregion_valuelist[item["aggregate_region"]] = [item["value"]]

                palocations_value_data[item["value"]] = item
        else:
            print("ERR: Could not retrieve PA Locations")
            prisma_sase.jd_detailed(resp)

        #
        # BW Allocations
        #
        print("\tBW Allocation")
        resp = sase_session.rest_call("https://api.sase.paloaltonetworks.com/sse/config/v1/bandwidth-allocations",
                                      method="GET")
        if resp.cgx_status:
            itemlist = resp.cgx_content.get("data", None)
            for item in itemlist:
                palocations_aggregion.append(item["name"])
                palocs = palocations_aggregion_valuelist[item["name"]]
                for paloc in palocs:
                    palocations_bwalloc.append(paloc)
                    palocation_value_spnnamelist[paloc] = item["spn_name_list"]
                    palocation_value_bw[paloc] = item["allocated_bandwidth"]
        else:
            print("ERR: Could not retrieve BW Allocation")
            prisma_sase.jd_detailed(resp)

        if len(palocations_bwalloc) == 0:
            print("ERR: BW not allocated to any PA Location. "
                  "Please allocate BW via Workflows -> Prisma Access Setup -> Remote Networks -> Bandwidth Management."
                  "\nExiting..")
            sys.exit()

    if action in [CONFIG, DELETE, BIND]:
        #
        # Sites
        #
        print("\tSites")
        resp = sase_session.get.sites()
        if resp.cgx_status:
            itemlist = resp.cgx_content.get("items", None)
            for item in itemlist:
                site_id_name[item["id"]] = item["name"]
                site_name_id[item["name"]] = item["id"]

                if item["element_cluster_role"] == "SPOKE":
                    spokesitenames.append(item["name"])
        else:
            print("ERR: Could not retrieve Sites")
            prisma_sase.jd_detailed(resp)

        #
        # Validate Site Name Exists
        #
        if sitename not in spokesitenames:
            print("ERR: Invalid Site Name: {}. Please select a valid site name.\nExiting..".format(sitename))
            sys.exit()

        sid = site_name_id[sitename]

        if action in [CONFIG, BIND]:
            #
            # WAN Networks
            #
            print("\tWAN Networks")
            resp = sase_session.get.wannetworks()
            if resp.cgx_status:
                wannetworks = resp.cgx_content.get("items", None)
                for wannw in wannetworks:
                    wannw_id_name[wannw["id"]] = wannw["name"]
                    wannw_name_id[wannw["name"]] = wannw["id"]
            else:
                print("ERR: Could not retrieve Sites")
                prisma_sase.jd_detailed(resp)

            #
            # Active SWI IDs
            #
            print("\tElements Query")
            active_swis = []
            data = {
                "query_params": {
                    "site_id": {"in": [sid]}
                }
            }
            resp = sase_session.post.element_query(data=data)
            if resp.cgx_status:
                elements = resp.cgx_content.get("items", None)

                eids = []
                for elem in elements:
                    eids.append(elem["id"])
                    elem_id_name[elem["id"]] = elem["name"]
                    resp = sase_session.get.interfaces(site_id=sid, element_id=elem["id"])
                    if resp.cgx_status:
                        interfaces = resp.cgx_content.get("items", None)

                        servicelinkids = []
                        for intf in interfaces:
                            if intf["type"] == "service_link" and "AUTO_PA_SDWAN_MANAGED" in intf["tags"]:
                                servicelink_id_name[intf["id"]] = intf["name"]
                                servicelinkids.append(intf["id"])

                            swis = intf.get("site_wan_interface_ids", None)
                            if swis is not None:
                                if len(swis) > 0:
                                    if swis[0] not in active_swis:
                                        active_swis.append(swis[0])

                        elemid_servicelinkidlist[elem["id"]] = servicelinkids

                siteid_elemidlist[sid] = eids

            else:
                print("ERR: Could not retrieve Elements.\nExiting..")
                prisma_sase.jd_detailed(resp)
                sys.exit()

            #
            # WAN Interfaces
            #
            print("\tSite WAN Interfaces")
            resp = sase_session.get.waninterfaces(site_id=sid)
            if resp.cgx_status:
                swis = resp.cgx_content.get("items", None)

                swinames = []
                swiids = []
                swi_id_name = {}
                swi_name_id = {}
                for swi in swis:
                    if swi.get("name", None) is None:
                        swiname = "Circuit to {}".format(wannw_id_name[swi["network_id"]])
                    else:
                        swiname = swi["name"]

                    if swi["id"] not in active_swis:
                        swis_inactive.append(swiname)
                        continue

                    swi_id_name[swi["id"]] = swiname
                    swi_name_id[swiname] = swi["id"]
                    if swi["type"] == "publicwan":
                        swinames.append(swiname)
                        swiids.append(swi["id"])

                siteid_swiidname[sid] = swi_id_name
                siteid_swinameid[sid] = swi_name_id
                siteid_swiidlist[sid] = swiids
                siteid_swinamelist[sid] = swinames

            else:
                print("ERR: Could not retrieve WAN Interfaces")
                prisma_sase.jd_detailed(resp)

            if action in [BIND]:
                #
                # Security Zones
                #
                print("\tSecurity Zones")
                resp = sase_session.get.securityzones()
                if resp.cgx_status:
                    itemlist = resp.cgx_content.get("items", None)
                    for item in itemlist:
                        zone_id_name[item["id"]] = item["name"]
                        zone_name_id[item["name"]] = item["id"]

                else:
                    print("ERR: Could not retrieve Security Zones")
                    prisma_sase.jd_detailed(resp)

            if action in [CONFIG]:
                #
                # RN QoS Profiles
                #
                print("\tRN QoS Profiles")
                resp = sase_session.rest_call(
                    "https://api.sase.paloaltonetworks.com/sse/config/v1/qos-profiles?folder=Remote Networks",
                    method="GET")
                if resp.cgx_status:
                    qosprofiles = resp.cgx_content.get("data", None)
                    for profile in qosprofiles:
                        rnqosprofile_id_name[profile["id"]] = profile["name"]
                        rnqosprofile_name_id[profile["name"]] = profile["id"]
                        if profile["snippet"] == "default":
                            default_qos_profile_id = profile["id"]

                    if default_qos_profile_id is None:
                        print("ERR: No default QoS profile found for RN.\nExiting..")
                        sys.exit()

                else:
                    print("ERR: Could not retrieve QoS Profiles for Remote Networks")
                    prisma_sase.jd_detailed(resp)

    return



def list_palocations():
    print("Here are the PA Locations with allocated BW:")
    for aggregion in palocations_aggregion:
        print("{}".format(aggregion))

        palocations = palocations_aggregion_valuelist[aggregion]
        for item in palocations:
            print("\t{} [{}]: {} Mbps".format(palocations_value_displayname[item], item, palocation_value_bw[item]))

    return


def config_saseconnection(sase_session, sitename, circuit_names_list, palocation):
    spnname = palocation_value_spnnamelist[palocation]
    siteid = site_name_id[sitename]
    swiids = []

    if "ALL" in circuit_names_list:
        swiids = siteid_swiidlist[siteid]

    else:
        swi_name_id = siteid_swinameid[siteid]
        for item in circuit_names_list:
            swiids.append(swi_name_id[item])

    updated_sitename = sitename.replace(" ","")
    rng_name = "{}_{}".format(updated_sitename, spnname[0])
    ipsec_tunnels = []

    swi_id_name = siteid_swiidname[siteid]
    tunnel_count = 1
    for item in swiids:
        swiname = swi_id_name[item]
        updated_swiname = swiname.replace(" ","")
        display_palocation = palocations_value_displayname[palocation]
        updated_display_palocation = display_palocation.replace(" ","")
        name = "{}_{}_{}_tunnel_{}".format(updated_sitename,updated_swiname,updated_display_palocation,tunnel_count)
        tunnelconf = {
            "name": name,
            "wan_interface_id": item
        }
        ipsec_tunnels.append(tunnelconf)
        tunnel_count +=1

    data = {
        "enabled_wan_interface_ids": swiids,
        "ipsec_tunnel_configs": {
            "anti_replay": False,
            "copy_tos": False,
            "enable_gre_encapsulation": False,
            "tunnel_monitoring": True
        },
        "is_active": True,
        "prismaaccess_edge_location": [palocation],
        "prismaaccess_qos_cir_mbps": 1,
        "prismaaccess_qos_profile_id": default_qos_profile_id,
        "remote_network_groups": [
            {
                "ipsec_tunnels": ipsec_tunnels,
                "name": rng_name,
                "spn_name": [spnname[0]]
            }
        ],
        "routing_configs": {
            "advertise_default_route": False,
            "bgp_secret": None,
            "export_routes": False,
            "summarize_mobile_routes_before_advertise": False
        }
    }

    resp = sase_session.post.prismasase_connections(site_id=siteid, data=data)
    if resp.cgx_status:
        print("INFO: SASE Connection request sent to Prisma SASE Controller.\nConnection Details:")
        print("\tSite Name: {}".format(sitename))
        print("\tPA Location: {} [{}]. Allocated BW: {} Mbps".format(palocation, spnname[0], palocation_value_bw[palocation]))
    else:
        print("ERR: Could not establish SASE Connection")
        prisma_sase.jd_detailed(resp)

    return

def delete_saseconnection(sase_session, sitename):
    siteid = site_name_id[sitename]
    resp = sase_session.get.prismasase_connections(site_id=siteid)
    if resp.cgx_status:
        saseconnections = resp.cgx_content.get("items", None)
        if len(saseconnections) == 0:
            print("WARN: No SASE Connections found at Site {}".format(sitename))
            return

        for saseconnection in saseconnections:
            remote_network_groups = saseconnection.get("remote_network_groups", None)
            updated_rns = []
            for rn in remote_network_groups:
                rn["ipsec_tunnels"] = []
                updated_rns.append(rn)

            saseconnection["remote_network_groups"] = updated_rns
            saseconnection["enabled_wan_interface_ids"] = []
            resp = sase_session.put.prismasase_connections(site_id=siteid,
                                                  prismasase_connection_id=saseconnection["id"],
                                                  data=saseconnection)
            if resp.cgx_status:
                print("INFO: Circuits unbound from SASE Connection.")
                print("INFO: SASE Connection cleanup request sent to Prisma SASE Controller.")

                # resp = sase_session.delete.prismasase_connections(site_id=siteid,
                #                                          prismasase_connection_id=saseconnection["id"])
                # if resp.cgx_status:
                #     print("INFO: SASE Connection at Site {} deleted".format(sitename))
                # else:
                #     print("ERR: Could not delete SASE Connection")
                #     prisma_sase.jd_detailed(resp)

            else:
                print("ERR: Could not edit SASE Connection")
                prisma_sase.jd_detailed(resp)
    else:
        print("ERR: Could not retrieve SASE Connections")
        prisma_sase.jd_detailed(resp)


def bind_zones(sase_session, sitename, zone):

    siteid = site_name_id[sitename]
    zid = zone_name_id[zone]
    elemids = siteid_elemidlist[siteid]

    for elemid in elemids:
        servicelinks = elemid_servicelinkidlist[elemid]
        if len(servicelinks) == 0:
            print("ERR: No SASE tunnels found on {}:{}".format(sitename, elem_id_name[elemid]))

        else:
            data = {
                "zone_id":zid,
                "lannetwork_ids":[],
                "interface_ids":servicelinks,
                "wanoverlay_ids":[],
                "waninterface_ids":[]
            }

            resp = sase_session.post.elementsecurityzones(site_id=siteid, element_id=elemid, data=data)
            if resp.cgx_status:
                print("INFO: Zone {} bound to {}:{} on:".format(zone, sitename, elem_id_name[elemid]))
                for slid in servicelinks:
                    print("\t{}".format(servicelink_id_name[slid]))
            else:
                print("ERR: Could not bind Zone {} to {}:{}".format(zone, sitename, elem_id_name[elemid]))
                prisma_sase.jd_detailed(resp)

    return

def parse_circuit_name(circuit_names):
    if "," in circuit_names:
        tmp = circuit_names.split(",")

        return tmp
    else:
        return [circuit_names]


def go():
    #############################################################################
    # Begin Script
    ############################################################################
    parser = argparse.ArgumentParser(description="{0}.".format("Prisma SD-WAN UTD Lab Setup"))
    config_group = parser.add_argument_group('Config', 'Details for the tenant you wish to operate')
    config_group.add_argument("--action", "-A", help="Action. Allowed Actions: list_palocations, delete_saseconn, config_saseconn, bind_zone", default=None)
    config_group.add_argument("--sitename", "-S", help="Site Name", default=None)
    config_group.add_argument("--palocation", "-PL", help="PA Location", default=None)
    config_group.add_argument("--circuit_names", "-CN", help="Comma separated circuit list (Site WAN Interface Names). For all public circuits, use keyword: ALL", default="ALL")
    config_group.add_argument("--zone", "-Z", help="Security Zone to bind to SASE circuits", default=None)
    #config_group.add_argument("--circuit_ids", "-CI", help="Comma separated circuit list (Site WAN Interface IDs). For all public circuits, use keyword: ALL", default="ALL")

    #############################################################################
    # Parse Arguments
    #############################################################################
    args = vars(parser.parse_args())
    action = args.get("action", None)
    if action not in ACTION:
        print("ERR: Invalid Action! Please choose from: list_palocations, delete_saseconn, config_saseconn, bind_zone\nExiting..")
        sys.exit()

    sitename = None
    circuit_names = "ALL"
    palocation = None
    zone = None
    if action in [DELETE, CONFIG, BIND]:
        sitename = args.get("sitename", None)
        if sitename is None:
            print("ERR: Site name not provided.\nExiting..")
            sys.exit()

        circuit_names = args.get("circuit_names", None)
        if circuit_names in [None, "ALL"]:
            circuit_names = "ALL"

        zone = args.get("zone", None)
        if zone is None:
            if action in [BIND]:
                print("ERR: Zone not provided.\nExiting..")
                sys.exit()

        palocation = args.get("palocation", None)
        if palocation is None:
            if action in [CONFIG]:
                print("ERR: PA Location not provided.\nExiting..")
                sys.exit()

    ##############################################################################
    # Login
    ##############################################################################
    sase_session = prisma_sase.API()
    sase_session.interactive.login_secret(client_id=PRISMASASE_CLIENT_ID,
                                          client_secret=PRISMASASE_CLIENT_SECRET,
                                          tsg_id=PRISMASASE_TSG_ID)
    sase_session.remove_header("X-PANW-Region")
    if sase_session.tenant_id is None:
        print("ERR: Service Account login failure. Please check client credentials")
        sys.exit()

    ##############################################################################
    # Create Translation Dicts
    ##############################################################################
    print("INFO: Building Translation Dicts..")
    create_dicts(sase_session=sase_session, action=action, sitename=sitename)

    ##############################################################################
    # Validate Input Data
    ##############################################################################
    circuit_names_list = []
    if action in [CONFIG]:
        sid = site_name_id[sitename]
        swinames = siteid_swinamelist[sid]
        if circuit_names not in ["ALL"]:
            circuit_names_list = parse_circuit_name(circuit_names)

            for item in circuit_names_list:
                if item not in swinames:
                    if item in swis_inactive:
                        print("ERR: Circuit {} not bound to any interface at Site {}. "
                              "Please select from the following:".format(item, sitename))
                    else:
                        print("ERR: Invalid circuit name: {}\nNo such circuit configured at Site {}. "
                              "Please select from the following:".format(item, sitename))

                    for swi in swinames:
                        print("\t{}".format(swi))
                    print("Exiting..")
                    sys.exit()
        else:
            circuit_names_list = ["ALL"]

        if palocation not in palocations_value_displayname.keys():
            print("ERR: Invalid PA Location! Please select from the following:")
            for paloc in palocations_bwalloc:
                print("\t{}".format(paloc))

            print("Exiting..")
            sys.exit()

        else:
            if palocation not in palocations_bwalloc:
                print("ERR: No BW allocated to PA Location: {}".format(palocation))
                print("Please select a PA Location from the following:")
                for paloc in palocations_bwalloc:
                    print("\t{}".format(paloc))

                print("Exiting..")
                sys.exit()

    elif action in [BIND]:
        if zone not in zone_name_id.keys():
            print("ERR: Invalid Zone: {}. Please select from the following: ".format(zone))
            for item in zone_name_id.keys():
                print("\t{}".format(item))

            print("Exiting..")
            sys.exit()
    ##############################################################################
    # Perform task
    ##############################################################################

    if action == LIST:
        list_palocations()

    elif action == CONFIG:
        config_saseconnection(sase_session=sase_session, sitename=sitename, circuit_names_list=circuit_names_list, palocation=palocation)

    elif action == DELETE:
        delete_saseconnection(sase_session=sase_session, sitename=sitename)

    elif action == BIND:
        bind_zones(sase_session=sase_session, sitename=sitename, zone=zone)

    sys.exit()


if __name__ == "__main__":
    go()
