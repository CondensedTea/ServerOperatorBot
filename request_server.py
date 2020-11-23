from flask import Flask, request
from server_operator import load_json, data_file
import os
import telegram
import logging


app = Flask(__name__)
bot = telegram.Bot(token=os.environ["TOKEN_SO"])
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


@app.route('/get_name')
def get_name():
    logging.info("🧪 get_name was called from {}".format(request.remote_addr))
    name_resolve = {}
    data = load_json(data_file)
    for telegram_id in data:
        name_resolve['192.168.89.{}'.format(data[telegram_id]["server_ip"])] = data[telegram_id]["name"]
    return name_resolve[str(request.remote_addr)]


@app.route('/user/<name>')
def is_ready(name):
    logging.info("🧪 {}'s server is up and running".format(name))
    id_resolve = {}
    data = load_json(data_file)
    for telegram_id in data:
        id_resolve[data[telegram_id]["name"]] = telegram_id

    bot.send_message(chat_id=id_resolve[name], text="Удаленное рабочее место готово к работе")
    return '', 202

if __name__ == '__main__':
    app.run(host='0.0.0.0')
