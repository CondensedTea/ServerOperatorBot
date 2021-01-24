## Server Operator Bot

This bot operates self-hosted VDI based on Hetzner Cloud API and integrates with Samba Active Directory.

It is based on `hcloud-python` and `python-telegram-bot` libs and needs `python3-samba`, `python-systemd` packages, all data is stored in SQLite database.

Requires environment variables:

| Variable  | Value |
| ------------- | ------------- |
| TOKEN_HCLOUD  | hcloud API token  |
| TOKEN_SO  | telegram API token  |
| ROBOT  | password for Samba AD OU admin  |
| LOGFILE  | path to log file  |
| SQLITE_DB  | path to database file |
| TOKEN_SO  | telegram API token  |

Tested on Debian 10/11