from flask import Flask, request
from ServerOperator import load_json, data_file
import os
import telegram
import logging

# Config
log_file = "flask.log"

app = Flask(__name__)
bot = telegram.Bot(token=os.environ["TOKEN_SO"])
logging.basicConfig(filename=log_file, filemode="a", format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)


@app.route('/get_name')
def get_name():
    logging.info("get_name was called from {}".format(request.remote_addr))
    name_resolve = {}
    data = load_json(data_file)
    for telegram_id in data:
        name_resolve['192.168.89.{}'.format(data[telegram_id]["server_ip"])] = data[telegram_id]["name"]
    return name_resolve[str(request.remote_addr)]


@app.route('/user/<name>')
def is_ready(name):
    logging.info("{} is up and running".format(name))
    id_resolve = {}
    data = load_json(data_file)
    for telegram_id in data:
        id_resolve[data[telegram_id]["name"]] = telegram_id

    bot.send_message(chat_id=id_resolve[name], text="Удаленный рабочий стол готов к работе")
    return '', 202

if __name__ == '__main__':
    app.run(host='0.0.0.0')
