FROM python:3.10.12
COPY . /app/autobot
WORKDIR /app
#COPY ./pip.conf /etc/pip.conf
RUN pip install -r autobot/requirements.txt
EXPOSE 8080
RUN chmod -R 777 .
ENTRYPOINT python3 -m uvicorn autobot.main:app --host 0.0.0.0 --port 8888 --workers 3