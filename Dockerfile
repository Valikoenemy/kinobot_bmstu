FROM python:3.14-alpine

RUN rm -rf /opt/venv
RUN python -m venv /opt/venv
RUN source /opt/venv/bin/activate

COPY ./requirements.txt ./
COPY ./*.py ./
COPY ./handlers/*.py ./handlers/
COPY ./images ./
COPY ./kinocredentials_new.json ./
COPY ./.env ./

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "./main.py"]