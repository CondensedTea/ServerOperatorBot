from flask import Flask, request
from ServerOperator import load_json, data_file
import os
import telegram

app = Flask(__name__)
bot = telegram.Bot(token=os.environ["TOKEN_SO"])
hcloud_network = "192.168.89."


@app.route('/get_name')
def get_name():
    name_resolve = {}
    data = load_json(data_file)
    for telegram_id in data:
        name_resolve['{}{}'.format(hcloud_network, data[telegram_id]["server_ip"])] = data[telegram_id]["name"]
    return name_resolve[str(request.remote_addr)]


@app.route('/user/<name>')
def is_ready(name):
    id_resolve = {}
    data = load_json(data_file)
    for telegram_id in data:
        id_resolve[data[telegram_id]["name"]] = telegram_id

    bot.send_message(chat_id=id_resolve[name], text="Удаленный рабочий стол готов к работе")
    return '', 202

if __name__ == '__main__':
    app.run(host='0.0.0.0')
