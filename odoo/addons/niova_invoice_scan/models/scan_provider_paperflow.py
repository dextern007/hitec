# -*- coding: utf-8 -*-
#################################################################################
# Author      : Niova Group ApS (<https://niova.dk/>)
# Copyright(c): 2018-Present Niova Group ApS
# License URL : https://invoice-scan.com/license/
# All Rights Reserved.
#################################################################################
from odoo.addons.niova_invoice_scan.models.invoice_scan_manager import InvoiceScanManager
import json
import logging

_logger = logging.getLogger(__name__)
INVOICE_SCAN_API_BASE_URL = 'https://api.bilagscan.dk'


class ScanProviderPaperflow(object):

    def __init__(self, client_secret):
        self._client_secret = client_secret
        self._scan_service = None

    @property
    def scan_service(self):
        if self._scan_service is None:
            self._scan_service = InvoiceScanManager().get_scan_service(self._client_secret)
        return self._scan_service

    def upload_voucher(self, voucher_data):
        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json',
                   'Authorization': self._get_token()}
        uri = '/v1/organizations/%s/vouchers' % self._get_organization()
        parms = json.dumps({"voucher_data": voucher_data})
        status, content, request_time = self._request(uri, parms, headers, 'POST', response_format='bytes')
        return json.loads(content.decode('utf-8')).get('data') if status else False

    def get_vouchers(self, search):
        headers = {'Accept': 'application/json',
                   'Authorization': self._get_token()}

        uri = '/v1/organizations/%s/vouchers' % self._get_organization()
        status, content, _ = self._request(uri, search, headers, 'GET')

        if status:
            return content
        return {}

    def get_conditional_vouchers(self, offset=0, search_strings={}, count=10, seen='not_seen'):
        search = {}

        if seen == 'not_seen':
            search['seen'] = False
        elif seen == 'seen':
            search['seen'] = True
            
        if offset:
            search['offset'] = offset
        if count:
            search['count'] = count 
        
        # Apply search string
        for search_key, search_value in search_strings.items():
            search[search_key] = search_value 
        return self.get_vouchers(search)

    def get_voucher(self, voucher_id):
        headers = {'Accept': 'application/json',
                   'Authorization': self._get_token()}

        uri = '/v1/vouchers/%s' % (voucher_id)
        status, content, _ = self._request(uri, {}, headers, 'GET')
        if status:
            return content['data']
        return False

    def get_voucher_text(self, voucher_id):
        headers = {'Accept': 'application/json',
                   'Authorization': self._get_token()}

        uri = '/v1/vouchers/%s/text' % (voucher_id)
        status, content, _ = self._request(uri, {}, headers, 'GET')
        if status:
            return content['data']['text']
        return False

    def get_voucher_pdf(self, voucher_id):
        headers = {'Accept': 'application/json',
                   'Authorization': self._get_token()}

        uri = '/v1/vouchers/%s/pdf' % (voucher_id)
        status, content, _ = self._request(uri, {}, headers, 'GET', response_format='bytes')
        
        if status:
            return content
        return False

    def set_vouchers_as_seen(self, voucher_ids):
        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json',
                   'Authorization': self._get_token()}

        uri = '/v1/organizations/%s/vouchers/seen' % self._get_organization()
        parms = json.dumps({"vouchers": voucher_ids})
        status, content, request_time = self._request(uri, parms, headers, 'POST', response_format='bytes')
        return (status, content or False, request_time)

    def set_fields(self, fields):
        headers = {'Accept': 'application/json',
                   'Authorization': self._get_token()}

        uri = '/v1/organizations/%s/fields' % self._get_organization()
        status, content, request_time = self._request(uri, fields, headers, 'PUT', response_format='bytes')
        return (status, content or False, request_time) 

    def set_debitors(self, debitors):
        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json',
                   'Authorization': self._get_token()}
        
        parms = json.dumps({"debitors": debitors})
        uri = '/v1/organizations/%s/creditorCatalog' % self._get_organization()
        status, content, request_time = self._request(uri, parms, headers, 'PUT', response_format='bytes')
        return (status, content or False, request_time)

    def _get_organization(self):
        return self.scan_service.get_organization()
    
    def _get_token(self):
        return self.scan_service.get_access_token()
    
    def _request(self, uri, params={}, headers={}, request_type='GET', response_format='json'):
        status, response, request_time = self.scan_service.request(INVOICE_SCAN_API_BASE_URL + uri, params, headers, request_type)
        
        if response_format == 'bytes' or request_type in ('POST', 'PATCH', 'PUT'):
            content = response.content
        else:
            content = response.json()
            
        return status, content, request_time
    