from telegram.ext import Updater, CommandHandler
import os
import random
import string
import logging
import json
from hcloud import Client
from hcloud.images.domain import Image
from hcloud.servers.domain import Server
from hcloud.server_types.domain import ServerType
from hcloud.locations.domain import Location
from hcloud.networks.domain import Network


logging.basicConfig(filename="ServerOperator.log", filemode="a", format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
client = Client(token=os.environ["TOKEN_HCLOUD"])

admins_list = [458654293]


def start(update, context):
    with open("data.json", "r") as data_file:
        data = json.load(data_file)
    with open("invites.json", "r") as invites_file:
        invites = json.load(invites_file)
    join_token = extract_join_token(context.args)
    user_id = update.message.from_user["id"]
    name = f'{update.message.chat.first_name}{"" if update.message.chat.last_name is None else " "+update.message.chat.last_name}'
    if join_token:
        if f'{user_id}' not in data.keys():
            if join_token in invites.keys():
                data[f'{user_id}'] = {"name": name, "server_ip": "", "server_id": ""}
                invites[f'{join_token}'] = user_id
                with open("data.json", "w") as data_file:
                    json.dump(data, data_file, indent=4)
                with open("invites.json", "w") as invites_file:
                    json.dump(invites, invites_file, indent=4)
                context.bot.send_message(chat_id=update.effective_chat.id, text="Добро пожаловать, вы были успешно зарегистрированны в системе")
            else:
                context.bot.send_message(chat_id=update.effective_chat.id, text="Эта ссылка больше не работает, обратитесь к администратору за новой ссылкой для регистрации")
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Вы уже зарегестрированы в базе")


def gen_link(update, context):
    if update.message.from_user["id"] in admins_list:
        with open("invites.json", "r") as file:
            invites = json.load(file)
        current_join_token = gen_join_token()
        invites[f'{current_join_token}'] = ""
        with open("invites.json", "w") as file:
            json.dump(invites, file, indent=4)
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'https://t.me/ServerOperatorBot?start={current_join_token}')


def test(update, context):
    client.servers.delete(
        server=Server(name=str(context.args[0]))
    )


def open_server(update, context):
    user_id = update.message.from_user["id"]
    with open("data.json", "r") as file:
        data = json.load(file)
    try:
        if data[f'{user_id}']["server_ip"] == "":
            ip = get_ip_address(data, user_id)
            create_response = client.servers.create(
                name=f'Cloud-PC-{ip}',
                server_type=ServerType(name="cpx31"),
                image=Image(id=25093007),
                networks=[Network(id=135205)],
                location=Location(id=2)
            )
            data[f'{user_id}']["server_ip"] = ip
            data[f'{user_id}']["server_id"] = create_response.server.id
            with open("data.json", "w") as file:
                json.dump(data, file, indent=4)
            # context.bot.send_message(chat_id=update.effective_chat.id, text=f'Server id is {create_response.server.id}')
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'Вы успешно создали сервер Cloud-PC-{ip}.hq.rtdprk.ru, он будет доступен через 15 минут')
            # logging.INFO()
        else:
            ip = data[f'{user_id}']["server_ip"]
            context.bot.send_message(chat_id=update.effective_chat.id, text=f'Вы уже открыли сервер Cloud-PC-{ip}, что бы открыть новый сервер, необходимо закрыть старый командой /close')
            return
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Сейчас невозможно создать сервер, обратитесь в поддержку helpdesk@rtdprk.ru")


def close_server(update, context):
    user_id = update.message.from_user["id"]
    with open("data.json", "r") as file:
        data = json.load(file)
    ip = data[f'{user_id}']["server_ip"]
    server_id = data[f'{user_id}']["server_id"]
    try:
        client.servers.delete(
            server=Server(id=int(server_id))
        )
        # os.system(f'samba-tool computer delete "Cloud-PC-{ip}"')
        data[f'{user_id}']["server_id"] = ""
        data[f'{user_id}']["server_id"] = ""
        with open("data.json", "w") as file:
            json.dump(data, file, indent=4)
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'Вы успешно закрыли сервер Cloud-PC-{ip}')
    except:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f'Не удалось закрыть сервер Cloud-PC-{ip}')


def gen_join_token():
    letters = string.ascii_letters+string.digits
    result_str = ''.join(random.choice(letters) for i in range(24))
    return result_str


def extract_join_token(wordlist):
    return wordlist[0] if len(wordlist) == 1 else None


def get_ip_address(data, user_id):
    ip_pool = []
    for token in data:
        if data[f'{token}']["server_ip"] != "":
            ip_pool.append(int(data[token]["server_ip"]))
    for ip in range(3, 255):
        if ip not in ip_pool:
            return ip


def main():
    updater = Updater(token=os.environ["TOKEN_SO"], use_context=True)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("gen_link", gen_link))
    dp.add_handler(CommandHandler("open", open_server))
    dp.add_handler(CommandHandler("test", test))
    dp.add_handler(CommandHandler("close", close_server))

    updater.start_polling()

if __name__ == '__main__':
    main()