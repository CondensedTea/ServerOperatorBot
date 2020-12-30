from telegram.ext import Updater, CommandHandler, Filters
import os
import random
import string
import logging
import json
import re
from text import Text
import systemd.daemon
from hcloud import Client
from hcloud.images.domain import Image
from hcloud.servers.domain import Server
from hcloud.server_types.domain import ServerType
from hcloud.locations.domain import Location
from hcloud.ssh_keys.domain import SSHKey
from hcloud.networks.domain import Network

import subprocess
import shlex

# Config
admins_list = [458654293]
data_file = "data.json"
invites_file = "invites.json"
text_file = "text.py"
log_file = "bot.log"
default_image = 28353196
admin_password = os.environ["ROBOT"]
t = Text

logging.basicConfig(filename=log_file, filemode="a", format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

client = Client(token=os.environ["TOKEN_HCLOUD"], poll_interval=30)
admin_filter = Filters.user()
user_filter = Filters.user()


class User:
    def __init__(self, telegram_id):
        self.data = load_json(data_file)
        self.id = int(telegram_id)
        self.name = self.data[str(telegram_id)]["name"]
        self.server_ip = self.data[str(telegram_id)]["server_ip"]
        self.server_id = self.data[str(telegram_id)]["server_id"]
        self.snapshot_id = self.data[str(telegram_id)]["snapshot_id"]


def start(update, context):
    """
    Starting command for bot. With /start link, allows to register in database with token.
    :param update: bot's updater
    :param context: context of the bot
    :return: nothing
    """
    u = User(update.message.from_user.id)
    invites = load_json(invites_file)
    join_token = extract_join_token(context.args)
    name = re.search(r'--(.*)', join_token)
    if join_token in invites.keys():
        if f'{u.id}' not in u.data.keys():
            if invites[str(join_token)] == "":
                u.data[u.id] = {"name": name, "server_ip": "", "server_id": "", "snapshot_id": ""}
                user_filter.add_user_ids(u.id)
                invites[str(join_token)] = u.id
                flush_json(data_file, u.data)
                flush_json(invites_file, invites)
                context.bot.send_message(chat_id=u.id, text=Text.welcome)
                logging.info(f'✅  {name}({u.id}) was successfully registered')
            else:
                context.bot.send_message(chat_id=u.id, text=Text.broken_link)
                logging.info(f'⚠️  {name}({u.id}) tried to use taken link')
        else:
            context.bot.send_message(chat_id=u.id, text=Text.user_in_base)
            logging.info(f'🤔  {name}({u.id}) tried to register again')
    else:
        logging.info(f'❌  {name}({u.id}) tried to register without real link')


def gen_link(update, context):
    """
    Bot command for creating invitation for user. Can be called only from admin in admin_list
    :param update:
    :param context:
    :return:
    """
    if len(context.args) == 1:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Для создания приглашения необходимо указать имя, /gen_link <имя>")
    else:
        u = User(update.effective_chat.id)
        invites = load_json(invites_file)
        current_join_token = gen_join_token(context.args[0])
        invites[str(current_join_token)] = ""
        flush_json(invites_file, invites)
        context.bot.send_message(chat_id=u.id, text=f'https://t.me/ServerOperatorBot?start={current_join_token}')
        logging.info(f'🔗 Invite link was made by ({u.id}) for {context.args[0]}')


def list_users(update, context):
    """
    List of users in database, only for admins in admin_list
    :param update:
    :param context:
    :return:
    """
    u = User(update.message.from_user.id)
    user_table = "Список пользователей: \n"
    for user in u.data:
        user_table += ("{} -- {} \n".format(u.data[str(user)]["name"], user))
    context.bot.send_message(chat_id=u.id, text=user_table)


def open_server(update, context):
    """
    Bot command for creation server from default snapshot or snapshot of previous session. Can be called from admin for other user.
    :param update:
    :param context:
    :return:
    """
    if len(context.args) == 0:
        u = User(update.effective_chat.id)
    else:
        u = User(context.args[0])
    if u.snapshot_id == "":
        image = default_image
    else:
        image = u.snapshot_id
    try:
        if u.server_ip == "":
            ip = get_ip_address(u.data)
            create_response = client.servers.create(
                name='cloud-pc-{}'.format(u.name),
                server_type=ServerType(name="cpx31"),
                image=Image(id=image),
                ssh_keys=[SSHKey(id=1884416)],
                networks=[Network(id=135205)],
                location=Location(id=2)
            )
            delete_snapshot_responce = client.images.delete(image=Image(id=int(u.snapshot_id)))
            delete_snapshot_responce.action.wait_until_finished(max_retries=80)
            u.server_ip = ip
            u.server_id = create_response.server.id
            u.snapshot_id = ""
            samba_tool("add", u.name, ip)
            flush_json(data_file, u.data)
            context.bot.send_message(chat_id=u.id, text=t.creation_complete)
            logging.info(f'⬆️ {u.name}({u.id}) created server on {u.server_ip}')
        else:
            context.bot.send_message(chat_id=u.id, text=t.user_have_server)
            logging.info(f'⚠️ {u.name}({u.id}) tried to create second server')
    except Exception as err:
        context.bot.send_message(chat_id=u.id, text=t.open_server_error)
        logging.error(f'❌ {u.name}({u.id}) could not create server, {err}')


def close_server(update, context):
    """
    Bot command for saving roaming profile data, taking snapshot of server and deleting server.
    :param update:
    :param context:
    :return:
    """
    if len(context.args) == 0:
        u = User(update.message.from_user.id)
    else:
        u = User(context.args[0])
    try:
        if u.server_id is not "":
            logging.warning("Starting to close server({})".format(u.server_id))
            msg = context.bot.send_message(chat_id=u.id, text=t.deletion_started)

            response_shutdown = client.servers.shutdown(server=Server(id=int(u.server_id)))
            response_shutdown.wait_until_finished(max_retries=80)
            logging.warning("Server({}) shutdown complete".format(u.server_id))

            response_create_snapshot = client.servers.create_image(server=Server(id=int(u.server_id)), description="cloud-pc-{}".format(u.name))
            response_create_snapshot.action.wait_until_finished(max_retries=80)
            logging.warning("Image from server({}) creation complete".format(u.server_id))

            client.servers.delete(server=Server(id=int(u.server_id)))
            logging.warning("Server({}) deletion complete".format(u.server_id))
        else:
            context.bot.send_message(chat_id=u.id, text=t.no_server)
            logging.info(f'⚠️ {u.name}({u.id}) tried to call /close without server')

        u.server_ip = ""
        u.server_id = ""
        u.snapshot_id = response_create_snapshot.image.id
        flush_json(data_file, u.data)
        context.bot.edit_message_text(chat_id=u.id, message_id=msg.message_id, text=t.deletion_complete)
        logging.info(f'⬇️ {u.name}({u.id}) deleted server on {u.server_ip}')
    except Exception as err:
        context.bot.send_message(chat_id=update.effective_chat.id, text=t.deletion_error)
        logging.error(f'❌ {u.name}({u.id}) could not delete server on {u.server_ip}, {err}')


def clear(context):
    """
    Bot command for clearing users server and samba computer instance. Takes as argument name of user
    :param context:
    :return:
    """
    u = User(context.args[0])
    try:
        response_shutdown = client.servers.shutdown(server=Server(id=int(u.server_id)))
        response_shutdown.wait_until_finished(max_retries=80)
        logging.warning("Server({}) shutdown complete".format(u.server_id))

        client.servers.delete(server=Server(id=int(u.server_id)))
        logging.warning("Server({}) deletion complete".format(u.server_id))

        client.images.delete(image=Image(id=int(u.snapshot_id)))
        logging.warning("Snapshot deleted")

        samba_tool("delete", u.name, u.server_ip)
        samba_tool("computer delete", u.name)
        logging.warning(u.server_id+' samba-clear complete')

        u.server_ip = ""
        u.server_id = ""
        u.snapshot_id = ""
        flush_json(data_file, u.data)

        context.bot.send_message(chat_id=u.id, text=t.clear_complete)
    except Exception as err:
        context.bot.send_message(chat_id=u.id, text=t.clear_error+u.name)
        logging.error(f'❌ Could not clear user {u.name}, {err}')


def samba_tool(command, name, ip=""):
    """
    Function for interacting with samba-tool CLI, either samba-tool dns or samba-tool computer add
    :param command: option for samba-tool to call
    :param name: name of cloud-pc
    :param ip: ip of cloud-pc
    :return: False or nothing
    """
    if command == "computer delete":
        command_line = f'/usr/local/samba/bin/samba-tool computer delete cloud-pc-{name}'
    else:
        command_line = f'/usr/local/samba/bin/samba-tool dns {command} wikijs-samba.hq.rtdprk.ru hq.rtdprk.ru cloud-pc-{name} A 192.168.89.{ip} -U robot --password {admin_password}'

    command_line_args = shlex.split(command_line)
    logging.warning('Subprocess: ' + command_line_args[0])

    try:
        command_line_process = subprocess.Popen(command_line_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,)
        out, err = command_line_process.communicate()
        logging.warning("samba-tool: {} \n Out: {}, Err: {}".format(str(command), str(out), str(err)))
    except (OSError, CalledProcessError) as exception:
        logging.warning('Exception occurred: ' + str(exception))
        logging.warning('Subprocess failed')
        return False
    else:
        logging.warning('Subprocess finished')


def gen_join_token(user):
    """
    Generates random string of letters and numbers with length 24 and username in the end
    :param user: username
    :return: random string plus username
    """
    letters = string.ascii_letters+string.digits
    result_str = ''.join(random.choice(letters) for i in range(24))+"--"+user
    return result_str


def extract_join_token(args):
    """
    Returns first item of list with length 1, else returns None
    :param args: list of arguments
    :return: first item in list or None
    """
    return args[0] if len(args) == 1 else None


def get_ip_address(data):
    """
    Function to distribute ip address from x to 255. It checks json for taken ips and gives next ip.
    Have to make this one as hcloud api doesnt allow to create servers with predetermined, need to guess it.
    :param data: dict from json
    :return: last octet for ip address
    """
    ip_pool = []
    for token in data:
        if data[str(token)]["server_ip"] != "":
            ip_pool.append(int(data[token]["server_ip"]))
    for ip in range(8, 255):
        if ip not in ip_pool:
            return str(ip)


def load_json(json_file):
    """
    Loads json file into dict
    :param json_file: json file
    :return: dict with data
    """
    with open(json_file, "r") as file:
        return json.load(file)


def flush_json(json_file, data):
    """
    Flushes (overrides) dict with data into json file
    :param json_file: json file
    :param data: dict with data
    :return: nothing
    """
    with open(json_file, "w") as file:
        json.dump(data, file, indent=4)


def get_user_ids(file):
    """
    Generates list with telegram IDs of all users in bot database.
    :param file: json file to load
    :return: list of user IDs
    """
    user_list = []
    data = load_json(file)
    for user in data.keys():
        user_list.append(int(user))
    return user_list


def main():
    """
    Main function called upon start. Creates user_filter (accessible for all users in bot database),
    admin_filter (accessible for users IDs from var admin_list).
    Next it starts updater for bot and creates commands.
    At last it calls READY for systemd and ready to recieve commands from users
    :return:
    """
    user_filter.add_user_ids(get_user_ids(data_file))
    admin_filter.add_user_ids(admins_list)

    updater = Updater(token=os.environ["TOKEN_SO"], use_context=True)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("gen_link", gen_link, admin_filter))
    dp.add_handler(CommandHandler("list_users", list_users, admin_filter))
    dp.add_handler(CommandHandler("clear", clear, admin_filter, run_async=True))
    dp.add_handler(CommandHandler("open", open_server, user_filter, run_async=True))
    dp.add_handler(CommandHandler("close", close_server, user_filter, run_async=True))

    systemd.daemon.notify('READY=1')

    updater.start_polling()

if __name__ == '__main__':
    main()
