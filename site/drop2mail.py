import os
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
import mimetypes

from dropbox import client
from dropbox import session as db_session
from flask import Flask, url_for, session, redirect, request
from flask import render_template
import boto

import settings

app = Flask(__name__)

def _get_dropbox_session():
    return db_session.DropboxSession(settings.APP_KEY, settings.APP_SECRET, settings.ACCESS_TYPE)

@app.route('/send/', methods=['POST'])
def send():
    target_email = request.form['target_email']
    file_paths = request.form.getlist('files')
    
    if 'db_access_token' not in session:
        return redirect(url_for('start'))
    sess = _get_dropbox_session()
    access_key, access_secret = session['db_access_token']
    sess.set_token(access_key, access_secret)
    c = client.DropboxClient(sess)
            
    conn = boto.connect_ses(aws_access_key_id=settings.AWS_KEY, aws_secret_access_key=settings.AWS_SECRET_KEY)
    msg = MIMEMultipart()
    msg['Subject'] = "[drop2mail] Dropbox Files"
    msg['From'] = settings.SENDER_ADDRESS
    msg['To'] = target_email
    msg.preamble = 'Dropbox files attached'
    
    m = MIMEText("Dropbox files attached")
    msg.attach(m)
    
    files = {}
    for path in file_paths:
        f, metadata = c.get_file_and_metadata(path)
        ctype, encoding = mimetypes.guess_type(path)
        if ctype is None:
            ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        m = MIMEBase(maintype, subtype)
        m.set_payload(f.read())
        encoders.encode_base64(m)
        m.add_header('Content-Disposition', 'attachment', filename=os.path.split(path)[1])
        msg.attach(m)
    
    # print msg.as_string()
    conn.send_raw_email(msg.as_string(), settings.SENDER_ADDRESS)
    return redirect(request.form.get('current_url', url_for('browse_default')))

@app.route('/browse/')
def browse_default():
    return browse('')    
    
@app.route('/browse/<path:path>')
def browse(path):
    if 'db_access_token' not in session:
        return redirect(url_for('start'))
    sess = _get_dropbox_session()
    access_key, access_secret = session['db_access_token']
    sess.set_token(access_key, access_secret)
    c = client.DropboxClient(sess)
    folder_metadata = c.metadata(path)
    root_path = path if not path else '/'+path
    contents = []
    for item in folder_metadata['contents']:
        item['relative_path'] = item['path'].replace(root_path + '/', '')
        contents.append(item)
    contents.sort(lambda x, y: cmp(y['is_dir'], x['is_dir']))
    root_elements = root_path.split('/')
    if len(root_elements) > 1 and root_elements[-1] == '':
        root_elements = root_elements[:-1]
    path_elements = [(element, url_for('browse', path='/'.join(root_elements[:i+1])[1:])) for i, element in enumerate(root_elements)]
    return render_template('browse.html', contents=contents, root_path=path_elements, 
                            send_url=url_for('send'), current_url=request.url)   
    
@app.route('/start')
def start():
    if 'db_access_token' in session:
        return redirect(url_for('browse', path=''))
    sess = _get_dropbox_session()
    request_token = sess.obtain_request_token()
    session['request_token'] = (request_token.key, request_token.secret)
    url = sess.build_authorize_url(request_token, "http://localhost:5000" + url_for('db_callback'))
    return redirect(url)

@app.route('/start/db_callback')
def db_callback():
    sess = _get_dropbox_session()
    request_token_key, request_token_secret = session['request_token']
    request_token = db_session.OAuthToken(request_token_key, request_token_secret)
    access_token = sess.obtain_access_token(request_token)
    session['db_access_token'] = (access_token.key, access_token.secret)
    return redirect(url_for('browse', path=''))

@app.route('/')
def index():
    return render_template('index.html', start_url=url_for('start'))
    
if __name__=='__main__':
    # TODO: Put this into settings
    app.debug = settings.APP_DEBUG
    app.secret_key = settings.APP_SECRET_KEY
    app.run()
