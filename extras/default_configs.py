HUAWEI_INITIAL_DEFAULT_CONFIG = """"
as-notation plain
"""

HUAWEI_FINAL_DEFAULT_CONFIG = """"
undo telnet server enable
undo telnet ipv6 server enable
lldp enable

stelnet server enable
ssh authorization-type default aaa
ssh ipv6 server-source all-interface

snetconf server enable

user-interface vty 0 4
    authentication-mode aaa
    protocol inbound ssh
#
"""