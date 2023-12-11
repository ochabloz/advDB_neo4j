FROM ubuntu:22.04

RUN apt-get update -y && \
    apt-get install -y python3-pip python3 python3-wheel jq 7zip wget

COPY ./ /app/

WORKDIR /app
RUN pip3 install pip --upgrade
RUN pip3 install -r requirements.txt

CMD ["./run.sh"]




