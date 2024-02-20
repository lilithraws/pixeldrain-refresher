FROM python:3-bookworm

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY main.py ./

CMD [ "python", "./main.py"]