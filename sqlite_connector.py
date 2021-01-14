import sqlite3
import logging


class Database:
    def __init__(self, telegram_id=0, server_ip=0):
        if telegram_id:
            sql_query = """select u.name, s.server_ip, s.server_id, u.status, s.creation_date, s.snapshot_id, u.id, i.token, u.status
            from Users as u left join Servers as s on u.id = s.user_id left join Invites as i on u.id = i.user_id where u.id = ?"""
            (self.name,
             self.server_ip,
             self.server_id,
             self.user_status,
             self.creation_date,
             self.snapshot_id,
             self.id,
             self.token,
             self.is_admin) = db_query(sql_query, (telegram_id,))
            self.computername = "cloud-pc-{}".format(self.name)
        else:
            self.server_ip = server_ip

    def server_update(self):
        db_query("update Servers set server_ip = ?, server_id = ?, creation_date = ?, snapshot_id = ? where user_id = ?",
                 (self.server_ip, self.server_id, self.creation_date, self.snapshot_id, self.id)
                 )

    def server_delete(self):
        db_query("delete from Servers where user_id = ?", (self.id,))

    def invite_create(self, invite):
        db_query("insert into Invites (token, user_id) values (?, ?)", (invite, self.id))

    def user_create(self, name):
        db_query("insert into Users (id, name) values (?, ?)", (self.id, name))

    def get_name(self):
        return db_query("select name from Users where id = (select user_id from Servers where server_ip = ?)", (self.server_ip,))

    def ready_up(self):
        return db_query("select user_id from Servers where server_ip = ?", (self.server_ip,))

    def server_create(self):
        db_query("insert into Servers (server_ip, server_id, creation_date, user_id) values (?, ?, ?, ?)",
                 (self.server_ip, self.server_id, self.creation_date, self.id)
                 )

    @staticmethod
    def list_users():
        return db_query("select id, name from Users", many=True)


def config(filename, lowest_ip):
    global _database_name, _lowest_ip
    _database_name = filename
    _lowest_ip = lowest_ip


def db_query(query, data=(), many=False):
    try:
        conn = sqlite3.connect(_database_name)
        c = conn.cursor()
        c.execute(query, data)
        conn.commit()
        if many:
            return c.fetchall()
        else:
            return c.fetchone()
    except sqlite3.Error as err:
        logging.error("SQL query failed with error: {}".format(err))
        raise sqlite3.Error


def get_user_ids():
    """
    Generates list with telegram IDs of all users in bot database.
    :return: list of user IDs
    """
    user_list = []
    admin_list = []
    for (user, admin) in db_query("select id, status from Users", many=True):
        if admin:
            admin_list.append(user)
        user_list.append(user)
    return user_list, admin_list


def get_ip_address():
    """
    Function to distribute ip address from lowest free to 255. It checks database for taken ips and gives next ip.
    Have to make this one as hcloud api doesnt allow to create servers with predetermined ips, need to guess it.
    :return: full ip as u-string
    """
    ip_list = db_query("select server_ip from Servers", many=True)
    for ip in range(_lowest_ip + 1, 255):
        if (u'192.168.89.{}'.format(ip),) not in ip_list:
            return u'192.168.89.{}'.format(ip)
