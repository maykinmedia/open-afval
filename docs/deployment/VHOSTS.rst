Apache + mod-wsgi configuration
===============================

An example Apache2 vhost configuration follows::

    WSGIDaemonProcess openafval-<target> threads=5 maximum-requests=1000 user=<user> group=staff
    WSGIRestrictStdout Off

    <VirtualHost *:80>
        ServerName my.domain.name

        ErrorLog "/srv/sites/openafval/log/apache2/error.log"
        CustomLog "/srv/sites/openafval/log/apache2/access.log" common

        WSGIProcessGroup openafval-<target>

        Alias /media "/srv/sites/openafval/media/"
        Alias /static "/srv/sites/openafval/static/"

        WSGIScriptAlias / "/srv/sites/openafval/src/openafval/wsgi/wsgi_<target>.py"
    </VirtualHost>


Nginx + uwsgi + supervisor configuration
========================================

Supervisor/uwsgi:
-----------------

.. code::

    [program:uwsgi-openafval-<target>]
    user = <user>
    command = /srv/sites/openafval/env/bin/uwsgi --socket 127.0.0.1:8001 --wsgi-file /srv/sites/openafval/src/openafval/wsgi/wsgi_<target>.py
    home = /srv/sites/openafval/env
    master = true
    processes = 8
    harakiri = 600
    autostart = true
    autorestart = true
    stderr_logfile = /srv/sites/openafval/log/uwsgi_err.log
    stdout_logfile = /srv/sites/openafval/log/uwsgi_out.log
    stopsignal = QUIT

Nginx
-----

.. code::

    upstream django_openafval_<target> {
      ip_hash;
      server 127.0.0.1:8001;
    }

    server {
      listen :80;
      server_name  my.domain.name;

      access_log /srv/sites/openafval/log/nginx-access.log;
      error_log /srv/sites/openafval/log/nginx-error.log;

      location /500.html {
        root /srv/sites/openafval/src/openafval/templates/;
      }
      error_page 500 502 503 504 /500.html;

      location /static/ {
        alias /srv/sites/openafval/static/;
        expires 30d;
      }

      location /media/ {
        alias /srv/sites/openafval/media/;
        expires 30d;
      }

      location / {
        uwsgi_pass django_openafval_<target>;
      }
    }
