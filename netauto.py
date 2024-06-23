import pynetbox, logging
from pynetbox.core.response import RecordSet, Record
from pynetbox.core.app import App

NETBOX_URL: str = "https://netbox.iribarrem.com"
NETBOX_TOKEN: str = "b186b056aae496bb4b2f1b8240964dad6f941265"
#NETBOX_TOKEN: str = "e6c1791b139de6e247a1a75a865f605949a18cb6"

class Netbox():
    def __init__(self, url, token) -> None:
        self.netbox = pynetbox.api(
            url=url,
            token=token,
            threading=True,
        )
        self.netbox.http_session.verify = False

        self.devices: list[Record] = list(self.netbox.dcim.devices.all())
        
        self.bgp: App = self.netbox.plugins.bgp
        self.bgp_sessions: list[Record] = list(self.bgp.session.all())
        self.rp_rules: list[Record] = list(self.bgp.routing_policy_rule.all())
        self.cl_rules: list[Record] = list(self.bgp.community_list_rule.all())
        self.pl_rules: list[Record] = list(self.bgp.prefix_list_rule.all())

class DeviceConfig():
    def __init__(self, device: Record) -> None:
        self.hostname: str = device.name

        self.basic_config: list[str] = self.__generate_basic_config()
        self.community_lists: list[str] = []
        self.prefix_lists: list[str] = []

    def add_community_list_rule(self, cl_rule: Record) -> None:
        self.community_lists.append(f"ip community-filter {cl_rule.community_list["name"]} {cl_rule.action} {cl_rule.community["value"]}")

    def add_pl_rule(self, pl_rule: Record) -> None:
        command: str = f"ip ip-prefix {pl_rule.prefix_list["name"]} index {pl_rule.index} {pl_rule.action} "

        if pl_rule.prefix is not None:
            prefix, netmask = pl_rule.prefix["prefix"].split("/")
        elif pl_rule.prefix_custom is not None:
            prefix, netmask = pl_rule.prefix_custom.split("/")
        command += f"{prefix} {netmask} "

        if pl_rule.ge is not None:
            command += f"ge {pl_rule.ge} "
        if pl_rule.le is not None:
            command += f"le {pl_rule.le}"

        self.prefix_lists.append(command)

    def __generate_basic_config(self) -> list[str]:
        basic_config: list[str] = []

        basic_config.append(f"hostname {self.hostname}")

        return basic_config
    
    def get_config(self) -> str:
        commands: list[str] = []

        commands.extend(set(self.basic_config))
        commands.extend(set(self.community_lists))
        commands.extend(set(self.prefix_lists))

        output: str = "\n".join(commands)

        return output

def main() -> None:
    netbox = Netbox(NETBOX_URL, NETBOX_TOKEN)

    for device in netbox.devices:
        device_config = DeviceConfig(device)
        device_bgp_sessions: list[Record] = [bgp_session for bgp_session in netbox.bgp_sessions if bgp_session.device["id"] == device.id]

        device_rp_rules: list[Record] = []
        for session in device_bgp_sessions:
            routing_policies: list[int] = [rp["id"] for rp in session.import_policies]
            routing_policies.extend([rp["id"] for rp in session.export_policies])
            device_rp_rules.extend([rp_rule for rp_rule in netbox.rp_rules 
                                             if rp_rule.routing_policy["id"] in routing_policies])
            
        for rp_rule in device_rp_rules:
            prefix_lists: list[int] = [pl["id"] for pl in rp_rule.match_ip_address]
            pl_rules: list[Record] = [pl_rule for pl_rule in netbox.pl_rules if pl_rule.prefix_list["id"] in prefix_lists]

            for pl_rule in pl_rules:
                device_config.add_pl_rule(pl_rule)
        
        for rp_rule in device_rp_rules:
            community_lists: list[int] = [cl["id"] for cl in rp_rule.match_community]
            cl_rules: list[Record] = [cl_rule for cl_rule in netbox.cl_rules if cl_rule.community_list["id"] in community_lists]

            for cl_rule in cl_rules:
                device_config.add_community_list_rule(cl_rule)
        
        print(f"{device.name} config:\n")
        print(device_config.get_config())
        
if __name__ == "__main__":
    main()