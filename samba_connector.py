import sys
sys.path.insert(0, "/usr/local/samba/lib/python3.7/site-packages")

from samba.auth import system_session
from samba.credentials import Credentials
from samba.param import LoadParm
from samba.samdb import SamDB
from samba.netcmd.dns import dns_connect, dns_type_flag
from samba.dcerpc import dnsp, dnsserver
from samba.dnsserver import ARecord


class ActiveDirectory:
    def __init__(self, user, password, server, domain):
        self.ldap_server = "ldap://{}".format(server)
        self.dns_server = server
        self.domain = domain
        self.lp = LoadParm()
        self.creds = Credentials()
        self.creds.guess(self.lp)
        self.creds.set_username(user)
        self.creds.set_password(password)
        self.samdb = SamDB(url=self.ldap_server, session_info=system_session(), credentials=self.creds, lp=self.lp)

    def add_computer(self, computername):
        self.samdb.newcomputer(computername=computername, computerou='OU=CloudDesktops,DC=hq,DC=rtdprk,DC=ru')

    def remove_computer(self, computername):
        fulldn = "CN={},".format(computername)+"OU=CloudDesktops,DC=hq,DC=rtdprk,DC=ru"
        self.samdb.erase_users_computers(dn=fulldn)

    def add_dns_record(self, name, ip):
        dns_conn = dns_connect(self.dns_server, self.lp, self.creds)
        add_rec_buf = dnsserver.DNS_RPC_RECORD_BUF()
        add_rec_buf.rec = ARecord(ip)
        dns_conn.DnssrvUpdateRecord2(dnsserver.DNS_CLIENT_VERSION_LONGHORN, 0, self.dns_server, self.domain, name, add_rec_buf, None)

    def remove_dns_record(self, name, ip):
        dns_conn = dns_connect(self.dns_server, self.lp, self.creds)
        del_rec_buf = dnsserver.DNS_RPC_RECORD_BUF()
        del_rec_buf.rec = ARecord(ip)
        dns_conn.DnssrvUpdateRecord2(dnsserver.DNS_CLIENT_VERSION_LONGHORN,0, self.dns_server, self.domain, name, None, del_rec_buf)
