from __future__ import with_statement
from fabric.api import *
from fabric.contrib.console import confirm
from fabric.contrib.files import append, upload_template

import sys
import time
import os
    
def live():
    env.hosts = ['servername']
    env.user = 'username'

def prereqs():
    sudo("apt-get install python-virtualenv nginx")

def setup_nginx():
    put("drop2mail.nginx", "/tmp")
    sudo("mv /tmp/drop2mail.nginx /etc/nginx/sites-available/drop2mail")
    sudo("ln -sf /etc/nginx/sites-available/drop2mail /etc/nginx/sites-enabled/drop2mail")
    sudo("/etc/init.d/nginx restart")

def deploy_scripts():
    prereqs()
    local("find site -name '*.pyc' -delete")
    run("mkdir -p sites/drop2mail")
    put("site/*", "sites/drop2mail/")
    with cd("sites/drop2mail"):
        run("virtualenv --no-site-packages env")
        run("env/bin/pip install -r requirements.txt")

def update():
    with settings(warn_only=True):
        run("kill `ps ax | grep gunicorn | grep drop2mail | awk '{ print $1 }'`")
    deploy_scripts()
    with cd("sites/drop2mail"):
        run("env/bin/gunicorn -D -b 127.0.0.1:4337 drop2mail:app", pty=False)
