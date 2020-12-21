from flask import Flask, request
from server_operator import load_json, data_file
import systemd.daemon
import os
import telegram.ext
import logging

app = Flask(__name__)
bot = telegram.Bot(token=os.environ["TOKEN_SO"])
hcloud_network = "192.168.89."
log = logging.getLogger('werkzeug')
log.setLevel(logging.INFO)


@app.route('/get_name')
def get_name():
    name_resolve = {}
    data = load_json(data_file)
    for telegram_id in data:
        name_resolve['{}{}'.format(hcloud_network, data[telegram_id]["server_ip"])] = data[telegram_id]["name"]
    return name_resolve[str(request.remote_addr)]
    logging.info("/get_name was called from {}".format(request.remote_addr))


@app.route('/user/<name>')
def is_ready(name):
    id_resolve = {}
    data = load_json(data_file)
    for telegram_id in data:
        id_resolve[data[telegram_id]["name"]] = telegram_id
    bot.sendMessage(chat_id=id_resolve[name.lower()], text="Удаленный рабочий стол готов к работе")
    logging.info("ReadyUp was called from {} by {}".format(request.remote_addr, name))
    return '', 202

if __name__ == '__main__':
    systemd.daemon.notify('READY=1')
    app.run(host='0.0.0.0')
