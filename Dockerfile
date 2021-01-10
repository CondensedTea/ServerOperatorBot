FROM ubuntu:20.10

RUN apt update && \
    apt install -y python3-samba pip && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ServerOperator/requirements.txt
WORKDIR ServerOperator/
RUN pip install -r requirements.txt

COPY . ServerOperator/

CMD python3 server_operator.py && python3 request_server.py

EXPOSE 5000