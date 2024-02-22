import pynetbox, logging
from extras.default_configs import *

NETBOX_URL = "https://3.144.220.159"
NETBOX_TOKEN = "b186b056aae496bb4b2f1b8240964dad6f941265"

def configure_bgp(host, netbox) -> str:
    config: str = ""
    bgp = netbox.plugins.bgp

    config += configure_prefix_lists(host, bgp)
    config += configure_communities(host, bgp)
    config += configure_route_policies(host, bgp)
    return config

def configure_prefix_lists(host, bgp) -> str:
    config: str = ""

    ## Get Prefix Lists used in the device
    prefix_lists = []
    for bgp_session in bgp.session.filter(device=host.name):
        routing_policies = bgp_session.import_policies + bgp_session.export_policies
        for routing_policy in routing_policies:
            rules = bgp.routing_policy_rule.filter(routing_policy_id=routing_policy.id)
            for rule in rules:
                for prefix_list in rule.match_ip_address:
                    prefix_lists.append(prefix_list)

    ## Configure Prefix Lists without Duplicates
    for prefix_list in set(prefix_lists):
        for rule in bgp.prefix_list_rule.filter(prefix_list_id=prefix_list.id):
            if rule.prefix:
                prefix = rule.prefix.prefix.split("/")
            elif rule.prefix_custom:
                prefix = rule.prefix_custom.split("/")

            config += f"ip ip-prefix { prefix_list.name } index { rule.index } { rule.action } { prefix[0] } { prefix[1] }"

            if rule.ge:
                config += " greater-equal " + str(rule.ge)
            if rule.le:
                config += " less-equal " + str(rule.le)

            config += "\n"

    return config + "\n"

def configure_route_policies(host, bgp) -> str:
    output: str = ""

    for bgp_session in bgp.session.filter(device=host.name):
        routing_policies = bgp_session.import_policies + bgp_session.export_policies
        for routing_policy in routing_policies:
            rules = bgp.routing_policy_rule.filter(routing_policy_id=routing_policy.id)
            for rule in rules:
                output += f"route-policy {routing_policy.name} {rule.action} node {rule.index}\n"

                if rule.description:
                    output += f"    description {rule.description}\n"

                ## Match Clauses ------
                for prefix_list in rule.match_ip_address:
                    output += f"    if-match ip-prefix {prefix_list.name}\n"

                for community in rule.match_community:
                    community_filter = bgp.community.get(id=community.id).description
                    output += f"    if-match community-filter {community_filter}\n"
                
                if rule.match_custom:
                    for match_clause in rule.match_custom:
                        if match_clause[0] == 'as-path-filter':
                            output += f"    if-match as-path-filter {match_clause[1]}\n"

                        elif match_clause[0] == 'acl':
                            output += f"    if-match acl {match_clause[1]}\n"
                        
                        else:
                            raise Exception(f"Custom Match Clause not supported: {match_clause[0]}")

                ## Apply Clauses -------
                if rule.set_actions:
                    for action in rule.set_actions:
                        if action[0] == 'community':
                            output += "    apply community "
                            for community in action[1]:
                                output += f"{community} "
                            output += "\n"
                        
                        elif action[0] == 'as-path prepend':
                            output += "    apply as-path "
                            for asn in action[1]:
                                output += f"{asn} "
                            output += "additive\n"

                        elif action[0] == 'next-hop':
                            output += f"    apply ip-address next-hop {action[1]}\n"
                
                        else:
                            raise Exception(f"Custom Apply Clause not supported: {action[0]}")
                    # ------ TODO: CUSTOM APPLIES > ? ------ #
                
                if rule.custom_fields["local_preference"]:
                    output += f'    apply local-preference {rule.custom_fields["local_preference"]}\n'

            output += "\n"  
    return output

def configure_communities(host, bgp) -> str:
    output: str = ""

    for bgp_session in bgp.session.filter(device=host.name):
        routing_policies = bgp_session.import_policies + bgp_session.export_policies
        for routing_policy in routing_policies:
            rules = bgp.routing_policy_rule.filter(routing_policy_id=routing_policy.id)
            for rule in rules:
                for community in rule.match_community:
                    community_filter = bgp.community.get(id=community.id)
                    output += f"ip community-filter basic {community_filter.description} index 10 permit {community_filter.value}\n"

    output += "\n"
    return output

def main():
    logger = logging.getLogger("logger")
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    netbox = pynetbox.api(
        url=NETBOX_URL,
        token=NETBOX_TOKEN
    )
    netbox.http_session.verify = False

    for host in netbox.dcim.devices.all():
        output_config = ""

        if host.primary_ip and host.platform:
            if host.platform.name == "Huawei VRP":
                print(f"Generating configuration script for {host.name}...\n\n")
                # output_config += HUAWEI_INITIAL_DEFAULT_CONFIG

                output_config += configure_bgp(host, netbox)
        else:
            raise Exception(f"Device {host.name} has no Primary IP and no Platform")
            
    print(output_config)

if __name__ == "__main__":
    main()