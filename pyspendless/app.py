# Per avviare correttamente:
# python -m pyspendless.app

from flask import Flask, render_template, redirect, url_for, session, request, flash
from .conf import load_env
import os
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)
load_env()
app.secret_key = os.getenv('SECRET_KEY', 'changeme')

# OAuth setup
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@app.route("/login")
def login():
    return render_template("ps-login.html")

@app.route("/auth/login")
def auth_login():
    redirect_uri = os.getenv('OAUTH_REDIRECT_URI', url_for('auth_callback', _external=True))
    return google.authorize_redirect(redirect_uri)

@app.route("/auth/callback")
def auth_callback():
    token = google.authorize_access_token()
    resp = google.get('https://openidconnect.googleapis.com/v1/userinfo')
    user_info = resp.json()
    user_email = user_info.get('email')
    # Whitelist check (mock, replace with DB check)
    whitelist = os.getenv('WHITELIST_EMAILS', '').split(',')
    if user_email not in whitelist:
        flash('Email non autorizzata', 'danger')
        return redirect(url_for('login'))
    session['user_email'] = user_email
    return redirect(url_for('home'))

@app.route("/home")
def home():
    user_email = session.get('user_email')
    return render_template("ps-home.html", user_email=user_email)

if __name__ == "__main__":
    app.run(debug=True)
