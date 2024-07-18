import os
from flask_appbuilder.security.manager import AUTH_OAUTH
from airflow import configuration as conf

basedir = os.path.abspath(os.path.dirname(__file__))

WTF_CSRF_ENABLED = True

AUTH_TYPE = AUTH_OAUTH
AUTH_USER_REGISTRATION = True
AUTH_ROLES_MAPPING = {
    "<Okta Group Name>": ["User"],
    "<Okta Group Name>": ["Admin"],
    "<Okta Group Name>": ["Viewer"],
    "<Okta Group Name>": ["Op"]
}

AUTH_USER_REGISTRATION_ROLE = "User"
AUTH_ROLES_SYNC_AT_LOGIN = True

client_id = os.environ['AIRFLOW_WEB_CLIENT_ID']
client_secret = os.environ['AIRFLOW_WEB_CLIENT_SECRET']

OAUTH_PROVIDERS = [
    {'name': 'okta', 'icon': 'fa-circle-o',
        'token_key': 'access_token',
        'remote_app': {
            'client_id': client_id,
            'client_secret': client_secret,
            'api_base_url': 'https://<account>.okta.com/oauth2/v1/',
            'client_kwargs': {
                'scope': 'openid profile email groups'
            },
            'access_token_url': 'https://<account>.okta.com/oauth2/v1/token',
            'authorize_url': 'https://<account>.okta.com/oauth2/v1/authorize',
    }
    }
]
