from flask import Flask, request
import sqlite_connector
from sqlite_connector import Database
import os
import systemd.daemon
import telegram.ext
import logging

app = Flask(__name__)
bot = telegram.Bot(token=os.environ["TOKEN_SO"])
log_file = os.environ["LOG_FILE"]
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)

logging.basicConfig(filename=log_file, filemode="a", format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
sqlite_connector.config(filename=os.environ["SQLITE_DB"], lowest_ip=7)

@app.route('/get_name')
def get_name():
    u = Database(server_ip=request.remote_addr)
    if not u:
        logging.warning("Received call for /get_name from unknown ip, {}".format(request.remote_addr))
    else:
        logging.info("/get_name was successfully called from {}".format(request.remote_addr))
        (name,) = u.get_name()
        return name


@app.route('/user/<name>')
def ready_up(name):
    u = Database(server_ip=request.remote_addr)
    if not u:
        logging.warning("Received call for /ready_up from unknown ip -- {}".format(request.remote_addr))
    else:
        bot.sendMessage(chat_id=u.ready_up(), text="Удаленный рабочий стол готов к работе")
        logging.info("/ready_up was successfully called from {}".format(request.remote_addr))
        return '', 202

if __name__ == '__main__':
    systemd.daemon.notify("READY=1")
    app.run(host='0.0.0.0')
