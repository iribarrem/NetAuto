import pynetbox, logging
from pynetbox.core.response import RecordSet, Record
from pynetbox.core.app import App

NETBOX_URL: str = "https://netbox.iribarrem.com"
NETBOX_TOKEN: str = "b186b056aae496bb4b2f1b8240964dad6f941265"

class Netbox():
    def __init__(self, url, token) -> None:
        self.netbox = pynetbox.api(
            url=url,
            token=token,
            threading=True
        )

        self.devices: list[Record] = list(self.netbox.dcim.devices.all())
        
        self.bgp: App = self.netbox.plugins.bgp
        self.bgp_sessions: list[Record] = list(self.bgp.session.all())
        self.rp_rules: list[Record] = list(self.bgp.routing_policy_rule.all())
        self.cl_rules: list[Record] = list(self.bgp.community_list_rule.all())
        self.pl_rules: list[Record] = list(self.bgp.prefix_list_rule.all())

def main() -> None:
    netbox = Netbox(NETBOX_URL, NETBOX_TOKEN)

    for device in netbox.devices:
        print(f"{device.name} configs:")
        device_bgp_sessions: list[Record] = [bgp_session for bgp_session in netbox.bgp_sessions if bgp_session.device["id"] == device.id]

        device_rp_rules: list[Record] = []
        for session in device_bgp_sessions:
            routing_policies: list[int] = [rp["id"] for rp in session.import_policies]
            routing_policies.extend([rp["id"] for rp in session.export_policies])
            device_rp_rules.extend([rp_rule for rp_rule in netbox.rp_rules 
                                             if rp_rule.routing_policy["id"] in routing_policies])
            
        device_pl_rules: list[Record] = []
        for rp_rule in device_rp_rules:
            prefix_lists: list[int] = [pl["id"] for pl in rp_rule.match_ip_address]
            device_pl_rules.extend([pl_rule for pl_rule in netbox.pl_rules
                                    if pl_rule.prefix_list["id"] in prefix_lists])
        
        device_cl_rules: list[Record] = []
        for rp_rule in device_rp_rules:
            community_lists: list[int] = [cl["id"] for cl in rp_rule.match_community]
            device_cl_rules.extend([cl_rule for cl_rule in netbox.cl_rules
                                    if cl_rule.community_list["id"] in community_lists])
        
        
if __name__ == "__main__":
    main()