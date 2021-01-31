from telegram.ext import Updater, CommandHandler, Filters
import os
import random
import string
import logging
import re
import time
import systemd.daemon
import sqlite_connector
from sqlite_connector import Database, get_user_ids, get_ip_address
from samba_connector import ActiveDirectory
from datetime import datetime
from text import Text
from hcloud import Client
from hcloud.images.domain import Image
from hcloud.servers.domain import Server
from hcloud.server_types.domain import ServerType
from hcloud.locations.domain import Location
from hcloud.ssh_keys.domain import SSHKey
from hcloud.networks.domain import Network

# Config
log_file = os.environ["LOGFILE"]
default_image = 28353196
admin_password = os.environ["ROBOT"]
token_h = os.environ["TOKEN_HCLOUD"]
token_tg = os.environ["TOKEN_SO"]
support_email = "a.b.tyshkevich@rtdprk.ru"
t = Text

logging.basicConfig(filename=log_file, filemode="a", format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
sqlite_connector.config(filename=os.environ["SQLITE_DB"], lowest_ip=7)

client = Client(token=token_h, poll_interval=30)
admin_filter = Filters.user()
user_filter = Filters.user()


def start(update, context):
    """
    Starting command for bot. With join link given, registers in database.
    :param update:
    :param context:
    :return:
    """
    u = Database(update.message.from_user.id)
    join_token = extract_join_token(context.args)
    name = re.search(r'--(.*)', join_token)
    if not u.id:
        if u.token:
            u.id = update.message.from_user.id
            u.user_create(name)
            u.server_create()
            u.invite_create(join_token)
            user_filter.add_user_ids(u.id)
            context.bot.send_message(chat_id=u.id, text=Text.welcome)
            logging.info(f'✅  {name}({u.id}) was successfully registered')
        else:
            context.bot.send_message(chat_id=u.id, text=Text.broken_link)
            logging.warning(f'⚠️  {name}({u.id}) tried to use taken link')
    else:
        context.bot.send_message(chat_id=u.id, text=Text.user_in_base)
        logging.warning(f'🤔  {name}({u.id}) tried to register again')


def gen_link(update, context):
    """
    Creates join link for new user, can be called by admin
    :param update:
    :param context:
    :return:
    """
    u = Database(update.effective_chat.id)
    if len(context.args) == 0:
        context.bot.send_message(chat_id=u.id, text=t.gen_link_howto)
    else:
        current_join_token = gen_join_token(context.args[0])
        u.invite_create(current_join_token)
        context.bot.send_message(chat_id=u.id, text=f'https://t.me/ServerOperatorBot?start={current_join_token}')
        logging.info(f'🔗 Invite link was made by ({u.id}) for {context.args[0]}')


def list_users(update, context):
    """
    Lists users from Users table, can be called by admins
    :param update:
    :param context:
    :return:
    """
    u = Database(update.message.from_user.id)
    user_table = "Список пользователей: \n"
    for user in u.list_users():
        user_table += "{} -- {} \n".format(user[0], user[1])
    logging.info("Listed users by request of {}({})".format(u.name, u.id))
    context.bot.send_message(chat_id=u.id, text=user_table)


def open_server(update, context):
    """
    Bot command for creation server from default snapshot or snapshot of previous session.
    Can be called as admin for other user.
    :param update:
    :param context:
    :return:
    """
    u = Database(update.effective_chat.id)
    ad = ActiveDirectory("robot", admin_password, "192.168.89.4", "hq.rtdprk.ru")
    if len(context.args) == 1 and u.is_admin:
        u = Database(context.args[0])
    if not u.snapshot_id:
        image = default_image
    else:
        image = u.snapshot_id
    try:
        msg = context.bot.send_message(chat_id=u.id, text=t.creation_began)
        if u.server_id is None:
            logging.info("Begging to create server")
            if u.server_ip is None:
                u.server_ip = get_ip_address()
                ad.add_computer(u.computername)
                ad.add_dns_record(u.computername, u.server_ip)
                logging.info("First server in chain, created DNS and AD records")
            create_response = client.servers.create(
                name='cloud-pc-{}'.format(u.name),
                server_type=ServerType(name="cpx31"),
                image=Image(id=image),
                ssh_keys=[SSHKey(id=1884416)],
                networks=[Network(id=135205)],
                location=Location(id=2)
            )
            logging.info("Created server on hcloud")
            create_response.action.wait_until_finished(max_retries=80)
            if u.snapshot_id is not None:
                client.images.delete(image=Image(id=u.snapshot_id))
                time.sleep(30)  # hcloud api client.images.delete() returns Bool instead of Action, cant use response.wait_until_finished()
                u.snapshot_id = None
                logging.info("Cleared old snapshot")
            u.server_id = create_response.server.id
            u.creation_date = int(datetime.now().timestamp())  # TODO: finish creation date usage
            u.server_update()
            logging.info("Transaction to database complete")
            context.bot.edit_message_text(chat_id=u.id, message_id=msg.message_id, text=t.creation_complete)
            logging.info(f'⬆️ {u.name}({u.id}) created server on {u.server_ip}')
        else:
            context.bot.send_message(chat_id=u.id, text=t.user_have_server)
            logging.info(f'⚠️ {u.name}({u.id}) tried to create second server')
    except Exception as err:
        context.bot.send_message(chat_id=u.id, text=t.open_server_error.format(support_email))
        logging.error(f'❌ {u.name}({u.id}) could not create server, {err}')


def close_server(update, context):
    """
    Bot command that saves roaming profile data, takes snapshot of server and deletes server.
    :param update:
    :param context:
    :return:
    """
    u = Database(update.message.from_user.id)
    ad = ActiveDirectory("robot", admin_password, "192.168.89.4", "hq.rtdprk.ru")
    if len(context.args) == 1 and u.is_admin:
        u = Database(context.args[0])
    try:
        if u.server_id:
            logging.warning("Starting to close server({})".format(u.server_id))
            msg = context.bot.send_message(chat_id=u.id, text=t.deletion_started)

            response_shutdown = client.servers.shutdown(server=Server(id=u.server_id))
            response_shutdown.wait_until_finished(max_retries=80)
            logging.warning("Server({}) shutdown complete".format(u.server_id))

            response_create_snapshot = client.servers.create_image(server=Server(id=u.server_id), description="cloud-pc-{}".format(u.name))
            response_create_snapshot.action.wait_until_finished(max_retries=80)
            logging.warning("Image from server({}) creation complete".format(u.server_id))

            client.servers.delete(server=Server(id=u.server_id))
            logging.warning("Server({}) deletion complete".format(u.server_id))
        else:
            context.bot.send_message(chat_id=u.id, text=t.no_server)
            logging.info(f'⚠️ {u.name}({u.id}) tried to call /close without server')
            return

        u.server_id = None
        u.snapshot_id = response_create_snapshot.image.id
        u.server_update()
        ad.remove_dns_record(u.computername, u.server_ip)
        context.bot.edit_message_text(chat_id=u.id, message_id=msg.message_id, text=t.deletion_complete)
        logging.info(f'⬇️ {u.name}({u.id}) deleted server')
    except Exception as err:
        context.bot.send_message(chat_id=update.effective_chat.id, text=t.deletion_error.format(support_email))
        logging.error(f'❌ {u.name}({u.id}) could not delete server on {u.server_ip}, {err}')


def clear(update, context):
    """
    Bot command for clearing users server and samba computer instance. Takes as argument telegram id of user.
    :param update:
    :param context: Telegram id of user
    :return:
    """
    u = Database(context.args[0])
    ad = ActiveDirectory("robot", admin_password, "192.168.89.4", "hq.rtdprk.ru")
    try:
        response_shutdown = client.servers.shutdown(server=Server(id=u.server_id))
        response_shutdown.wait_until_finished(max_retries=80)
        logging.warning("Server({}) shutdown complete".format(u.server_id))

        client.servers.delete(server=Server(id=u.server_id))
        logging.warning("Server({}) deletion complete".format(u.server_id))

        client.images.delete(image=Image(id=u.snapshot_id))
        logging.warning("Snapshot deleted")

        ad.remove_dns_record(u.computername, u.server_ip)
        ad.remove_computer(u.computername)
        logging.warning(u.server_id + ' samba-clear complete')

        u.server_delete()
        context.bot.send_message(chat_id=u.id, text=t.clear_complete)
    except Exception as err:
        context.bot.send_message(chat_id=u.id, text=t.clear_error + u.name)
        logging.error(f'❌ Could not clear user {u.name}, {err}')


def gen_join_token(user):
    """
    Generates auth token for user with length of 24 and username
    :param user: username
    :return: auth token
    """
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for i in range(24)) + "--" + user


def extract_join_token(args):
    """
    Extracts auth token from list
    :param args: list of arguments
    :return: first item in list or None
    """
    return args[0] if len(args) == 1 else None


def main():
    """
    Main function called upon start. Creates user_filter (accessible for all users in bot database),
    admin_filter (accessible for users IDs from var admin_list).
    Next it starts updater for bot and creates commands.
    At last it calls READY for systemd and ready to receive commands from users
    :return:
    """
    (user_list, admins_list) = get_user_ids()
    user_filter.add_user_ids(user_list)
    admin_filter.add_user_ids(admins_list)

    updater = Updater(token=token_tg, use_context=True)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("gen_link", gen_link, admin_filter))
    dp.add_handler(CommandHandler("list_users", list_users))
    dp.add_handler(CommandHandler("clear", clear, admin_filter, run_async=True))
    dp.add_handler(CommandHandler("open", open_server, user_filter, run_async=True))
    dp.add_handler(CommandHandler("close", close_server, user_filter, run_async=True))

    systemd.daemon.notify("READY=1")

    updater.start_polling()

if __name__ == '__main__':
    main()
