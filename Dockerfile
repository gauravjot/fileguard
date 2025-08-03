# pull official base image
FROM python:3.13-slim-bookworm

# install packages
RUN apt-get update && apt install -y python3-dev supervisor gcc curl lsof nano netcat-openbsd
RUN pip install uwsgi

# set work directory
RUN mkdir -p /opt/fileguard
WORKDIR /opt/fileguard

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# copy files
COPY . /opt/fileguard

# install python packages
RUN pip install -r requirements.txt

# setup django server
RUN python manage.py collectstatic --noinput

# Supervisor and uWSGI setup
WORKDIR /var/log/supervisor
RUN cp /opt/fileguard/docker/supervisor.conf /etc/supervisor/conf.d
EXPOSE 8000
RUN service supervisor stop

# Starting service
WORKDIR /opt/fileguard
RUN chmod +x ./docker/start.sh
CMD ["./docker/start.sh"]