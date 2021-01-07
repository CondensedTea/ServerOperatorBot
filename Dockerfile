FROM ubuntu:20.10

RUN apt update && \
    apt install -y python3-samba \
                   pip && \
    rm -rf /var/lib/apt/lists/*

WORKDIR ServerOperator/

COPY server_operator.py request_server.py sqlite_connector.py samba_connector.py ServerOperator/

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

EXPOSE 5000