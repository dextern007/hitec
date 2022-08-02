# -*- coding: utf-8 -*-
#################################################################################
# Author      : Niova Group ApS (<https://niova.dk/>)
# Copyright(c): 2018-Present Niova Group ApS
# License URL : https://invoice-scan.com/license/
# All Rights Reserved.
#################################################################################
import sys
import requests
from odoo.http import request
from datetime import datetime, timedelta
import werkzeug
import logging

_logger = logging.getLogger(__name__)

TIMEOUT = 20
INVOICE_SCAN_CLIENT_ID = '5a6c194c-f790-483b-9cb8-33c30318fb14'
INVOICE_SCAN_BASE_URL = 'https://api.invoice-scan.com/'
INVOICE_SCAN_AUTH_ENDPOINT = 'oauth/authorize'
INVOICE_SCAN_TOKEN_ENDPOINT = 'oauth/token'

ODOO_REDIRECT_URI = 'invoice_scan/authentication'


class InvoiceScanService(object):

    def __init__(self, client_secret):
        self._client_secret = client_secret
    
    expires_in = None
    access_token = str()
    refresh_token = str()
    token_type = str()
    organization = str()
    
    def redirect_to_invoicescan(self):
        authorize_uri = self._get_authorize_uri('')
        return {
            'type': 'ir.actions.act_url',
            'url': authorize_uri,
            'target': 'new'
        }
        
    def get_access_token(self):
        if not self._get_refresh_token() and not self.get_organization():
            self._issue_access_token()
        elif not self._get_access_token() or self._get_expires_datetime() < (datetime.now() + timedelta(minutes=1)):
            self._refresh_access_token()
        return self._get_access_token()
        
    def _issue_access_token(self):
        uri, headers, data = self._get_token_request('invoice_scan', '')
        try:
            _, reponse, _ = self.request(uri, params=data, headers=headers, request_type='POST')
            content = reponse.json()
        except:
            error_msg = "Something went wrong issue access token. Maybe the Authorization setup is invalid."
            raise Exception(error_msg)
        
        self._set_access_token(content.get('access_token', ''), content.get('token_type', ''))
        self._set_expires_datetime(int(content.get('expires_in', 0)))
        self._set_refresh_token(content.get('refresh_token', ''))
        self._set_organization(content.get('organization_id', ''))
    
    def _refresh_access_token(self):
        uri, headers, data = self._get_token_request('refresh_token', '')
        try:
            _, reponse, _ = self.request(uri, params=data, headers=headers, request_type='POST')
            content = reponse.json()
        except:
            self.reset_tokens()
            error_msg = "Something went wrong issue access token. Maybe the Authorization setup is invalid."
            raise Exception(error_msg)
        
        self._set_access_token(content.get('access_token', ''), content.get('token_type', ''))
        self._set_refresh_token(content.get('refresh_token', ''))
        self._set_expires_datetime(int(content.get('expires_in', 0)))
            
    def request(self, uri, params={}, headers={}, request_type='GET'):
        _logger.debug("Uri: %s - Type : %s - Headers: %s - Params : %s !", (uri, type, headers, params))

        request_time = datetime.now()
        try:
            if request_type.upper() in ('GET', 'DELETE'):
                response = requests.request(request_type.lower(), uri, params=params, headers=headers, timeout=TIMEOUT)
            elif request_type.upper() in ('POST', 'PATCH', 'PUT'):
                response = requests.request(request_type.lower(), uri, data=params, headers=headers, timeout=TIMEOUT)
            else:
                raise Exception(('Method not supported [%s] not in [GET, POST, PUT, PATCH or DELETE]!') % (request_type))
            response.raise_for_status()
        except requests.HTTPError as error:
            error_message = 'Bad Invoice Scan request : {error_content}'.format(error_content=error.response.content)
            _logger.exception(error_message)
            raise Exception((error_message))
        except:
            error_message  = 'Something went wrong with the request to Invoice Scan request. Error message: {error}'.format(error=sys.exc_info()[1]) 
            _logger.exception(error_message)
            raise Exception((error_message))

        return (self._get_status(response), response, self._get_request_time(response, request_time))
    
    def _get_token_request(self, grant, scope):
        uri = INVOICE_SCAN_BASE_URL + INVOICE_SCAN_TOKEN_ENDPOINT
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        data = {
            'scope': scope,
            'client_id': INVOICE_SCAN_CLIENT_ID,
            'client_secret': self.client_secret,
            'grant_type': grant,
        }
        
        if grant == 'refresh_token':
            data.update({'refresh_token': self._get_refresh_token()})
        elif grant == 'invoice-scan':
            data.update({'redirect_uri': request.httprequest.url_root + ODOO_REDIRECT_URI})
            data.update({'code': 'next level of issue token'})
        return uri, headers, data
    
    def _get_authorize_uri(self, scope):
        return INVOICE_SCAN_BASE_URL
        uri = INVOICE_SCAN_BASE_URL + INVOICE_SCAN_AUTH_ENDPOINT + '?{parms}'
        data = {
            'scope': scope,
            'redirect_uri': request.httprequest.url_root + ODOO_REDIRECT_URI,
            'client_id': INVOICE_SCAN_CLIENT_ID,
            'response_type': 'code',
        }
        return uri.format(parms=werkzeug.url_encode(data))

    def _get_status(self, response): 
        response.raise_for_status()
        if int(response.status_code) in (204, 404):
            return False
        return True  
    
    def _get_request_time(self, response, request_time): 
        try:
            request_time = datetime.strptime(response.headers.get('date'), "%a, %d %b %Y %H:%M:%S %Z")
        except:
            pass
        return request_time
    
    def _set_access_token(self, token, token_type='Bearer'):
        self.token_type = token_type
        self.access_token = token
        
    def _get_access_token(self):
        if not self.access_token:
            return False
        return self.token_type + ' ' + self.access_token
            
    def _set_refresh_token(self, token):
        self.refresh_token = token

    def _get_refresh_token(self):
        return self.refresh_token
    
    def _set_organization(self, organization):
        self.organization = organization
        
    def get_organization(self):
        return self.organization
    
    @property
    def client_secret(self):
        return self._client_secret
    
    def _set_expires_datetime(self, expires_in=0):
        self.expires_in = datetime.now() + timedelta(seconds=expires_in)
    
    def _get_expires_datetime(self):
        if not self.expires_in:
            return datetime.now()
        return self.expires_in

    def reset_tokens(self):
        self._set_refresh_token('')
        self._set_access_token('')
        self._set_organization('')
        self._set_expires_datetime()
        self.env.cr.commit()