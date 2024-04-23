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

        self.devices: RecordSet = self.netbox.dcim.devices.all()
        
        self.bgp: App = self.netbox.plugins.bgp
        self.bgp_sessions: list[Record] = list(self.bgp.session.all())
        self.rp_rules: list[Record] = list(self.bgp.routing_policy_rule.all())
        self.community_list_rules: list[Record] = list(self.bgp.community_list_rule.all())
        self.prefix_list_rules: list[Record] = list(self.bgp.prefix_list_rule.all())
    
def main() -> None:
    netbox = Netbox(NETBOX_URL, NETBOX_TOKEN)

    for device in netbox.devices:
        device_bgp_sessions: list[Record] = [bgp_session for bgp_session in netbox.bgp_sessions if bgp_session.device["id"] == device.id]

        device_rp_rules: list[Record] = []
        for session in device_bgp_sessions:
            routing_policies: list[int] = [rp["id"] for rp in session.import_policies]
            routing_policies.extend([rp["id"] for rp in session.export_policies])

            device_rp_rules.extend([rp_rule for rp_rule in netbox.rp_rules 
                                             if rp_rule.routing_policy["id"] in routing_policies])
            
        
if __name__ == "__main__":
    main()