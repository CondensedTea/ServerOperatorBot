from telegram.ext import Updater, CommandHandler, Filters
import os
import random
import string
import logging
import json
import re
from text import Text
from hcloud import Client
from hcloud.images.domain import Image
from hcloud.servers.domain import Server
from hcloud.server_types.domain import ServerType
from hcloud.locations.domain import Location
from hcloud.networks.domain import Network

# Config
admins_list = [458654293]
data_file = "data.json"
invites_file = "invites.json"
text_file = "text.py"
log_file = "bot.log"
admin_password = os.environ["ROBOT"]

logging.basicConfig(filename=log_file, filemode="a", format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger("apscheduler.scheduler")
logger.setLevel(logging.WARNING)

client = Client(token=os.environ["TOKEN_HCLOUD"])
admin_filter = Filters.user()
user_filter = Filters.user()


def start(update, context):
    data = load_json(data_file)
    invites = load_json(invites_file)
    join_token = extract_join_token(context.args)
    user_id = update.message.from_user.id
    name = re.search(r'--(.*)')
    if join_token in invites.keys():
        if f'{user_id}' not in data.keys():
            if invites[str(join_token)] == "":
                data[str(user_id)] = {"name": name, "server_ip": "", "server_id": ""}
                user_filter.add_user_ids(user_id)
                invites[str(join_token)] = user_id
                flush_json(data_file, data)
                flush_json(invites_file, invites)
                context.bot.send_message(chat_id=update.effective_chat.id, text=Text.welcome)
                logging.info(f'✅ {name}({user_id}) was successfully registered')
            else:
                context.bot.send_message(chat_id=update.effective_chat.id, text=Text.broken_link)
                logging.warning(f'⚠️ {name}({user_id}) tried to use taken link')
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text=Text.user_in_base)
            logging.warning(f'🤔 {name}({user_id}) tried to register again')
    else:
        logging.warning(f'❌ {name}({user_id}) tried to register without real link')


def gen_link(update, context):
    user_id = update.message.from_user.id
    name = get_name(update)
    invites = load_json(invites_file)
    current_join_token = gen_join_token(context.args[0])
    invites[str(current_join_token)] = ""
    flush_json(invites_file, invites)
    context.bot.send_message(chat_id=update.effective_chat.id, text=f'https://t.me/ServerOperatorBot?start={current_join_token}')
    logging.info(f'🔗 Invite link was made by {name}({user_id}) for {context.args[0]}')


def open_server(update, context):
    data = load_json(data_file)
    if len(context.args) == 0:
        user_id = update.message.from_user.id
    elif update.message.from_user.id in admins_list:
        for tg_id in data:
            if data[str(tg_id)]["name"] == context.args[0]:
                user_id = tg_id
    else:
        return
    name = data[str(user_id)]["name"]
    try:
        t = Text(name)
        if data[str(user_id)]["server_ip"] == "":
            ip = get_ip_address(data)
            create_response = client.servers.create(
                name='cloud-pc-{}'.format(data[str(user_id)]["name"]),
                server_type=ServerType(name="cpx31"),
                image=Image(id=25660860),
                networks=[Network(id=135205)],
                location=Location(id=2)
            )
            data[str(user_id)]["server_ip"] = ip
            data[str(user_id)]["server_id"] = create_response.server.id
            os.system(f'/usr/local/samba/bin/samba-tool dns add wikijs-samba.hq.rtdprk.ru hq.rtdprk.ru cloud-pc-{name} A 192.168.89.{ip} -U robot --password {admin_password}')
            flush_json(data_file, data)
            context.bot.send_message(chat_id=update.effective_chat.id, text=t.creation_complete())
            logging.info(f'⬆️ {name}({user_id}) created server Cloud-PC-{name}')
        else:
            ip = data[str(user_id)]["server_ip"]
            context.bot.send_message(chat_id=update.effective_chat.id, text=t.user_have_server())
            logging.warning(f'⚠️ {name}({user_id}) tried create second server')
            return
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text=t.open_server_error)
        logging.error(f'❌ {name}({user_id}) could not create server')


def close_server(update, context):
    data = load_json(data_file)
    if len(context.args) == 0:
        user_id = update.message.from_user.id
    elif update.message.from_user.id in admins_list:
        for tg_id in data:
            if data[str(tg_id)]["name"] == context.args[0]:
                user_id = tg_id
    else:
        return
    name = data[str(user_id)]["name"]
    ip = data[str(user_id)]["server_ip"]
    t = Text(name)
    server_id = data[str(user_id)]["server_id"]
    try:
        client.servers.delete(server=Server(id=int(server_id)))
        os.system(f'/usr/local/samba/bin/samba-tool dns delete wikijs-samba.hq.rtdprk.ru hq.rtdprk.ru cloud-pc-{name} A 192.168.89.{ip} -U robot --password {os.environ["robot"]}')
        os.system(f'/usr/local/samba/bin/samba-tool computer delete cloud-pc-{name}')
        data[str(user_id)]["server_ip"] = ""
        data[str(user_id)]["server_id"] = ""
        flush_json(data_file, data)
        context.bot.send_message(chat_id=update.effective_chat.id, text=t.deletion_complete())
        logging.info(f'⬇️ {name}({user_id}) deleted server {ip}')
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text=t.deletion_error())
        logging.error(f'❌ {name}({user_id}) could not delete server {ip}')


def gen_join_token(user="unknown"):
    letters = string.ascii_letters+string.digits
    result_str = ''.join(random.choice(letters) for i in range(24))+"--"+user
    return result_str


def extract_join_token(args):
    return args[0] if len(args) == 1 else None


def get_ip_address(data):
    ip_pool = []
    for token in data:
        if data[str(token)]["server_ip"] != "":
            ip_pool.append(int(data[token]["server_ip"]))
    for ip in range(4, 255):
        if ip not in ip_pool:
            return ip


def load_json(json_file):
    with open(json_file, "r") as file:
        return json.load(file)


def flush_json(json_file, data):
    with open(json_file, "w") as file:
        json.dump(data, file, indent=4)


def get_name(update):
    return f'{update.message.chat.first_name}{"" if update.message.chat.last_name is None else " "+update.message.chat.last_name}'


def get_user_ids(file):
    user_list = []
    data = load_json(file)
    for user in data.keys():
        user_list.append(int(user))
    return user_list


def main():
    user_filter.add_user_ids(get_user_ids(data_file))
    admin_filter.add_user_ids(admins_list)

    updater = Updater(token=os.environ["TOKEN_SO"], use_context=True)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("gen_link", gen_link, admin_filter))
    dp.add_handler(CommandHandler("open", open_server, user_filter))
    dp.add_handler(CommandHandler("close", close_server, user_filter))

    updater.start_polling()

if __name__ == '__main__':
    main()
