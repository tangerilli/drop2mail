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

def deploy_scripts():
    local("find site -name '*.pyc' -delete")
    run("mkdir -p drop2mail")
    put("site/*", "drop2mail/")
    with cd("drop2mail"):
        run("virtualenv --no-site-packages env")
        run("env/bin/pip install -r requirements.txt")

def update():
    with settings(warn_only=True):
        run("killall gunicorn")
    deploy_scripts()
    with cd("drop2mail"):
        run("env/bin/gunicorn -D -b 127.0.0.1:4337 drop2mail:app", pty=False)
