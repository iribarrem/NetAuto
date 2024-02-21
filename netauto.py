import pynetbox, logging
from extras.default_configs import *

NETBOX_URL = "https://3.144.220.159"
NETBOX_TOKEN = "b186b056aae496bb4b2f1b8240964dad6f941265"

def configure_bgp(host, netbox) -> str:
    config: str = ""
    bgp = netbox.plugins.bgp

    config += configure_prefix_lists(host, bgp)

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
    return config

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
                # output_config += HUAWEI_INITIAL_DEFAULT_CONFIG

                output_config += configure_bgp(host, netbox)
        else:
            raise Exception(f"Device {host.name} has no Primary IP and no Platform")
            
    print(output_config)

if __name__ == "__main__":
    main()