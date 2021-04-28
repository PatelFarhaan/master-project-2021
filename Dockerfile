FROM ubuntu:latest

EXPOSE 5000

WORKDIR /apis

COPY apis.py /apis

COPY updated_data.csv /apis

COPY requirements.sh /apis

RUN apt-get update && apt-get upgrade -y

RUN apt-get install python3-pip -y

RUN bash requirements.sh

ENTRYPOINT ["python3"]

CMD ["apis.py"]