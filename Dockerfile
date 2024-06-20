FROM python:3.12-alpine
RUN mkdir /code
WORKDIR /code
RUN pip install --upgrade pip
COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt


CMD alembic upgrade head && python /code/main.py