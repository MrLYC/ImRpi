#!/usr/bin/env python
# encoding: utf-8

import argparse
from multiprocessing.pool import ThreadPool
from urlparse import urljoin
import socket

import requests


class DomainNotFound(Exception):
    pass


class RecordNotFound(Exception):
    pass


class DnspodApiResult(object):
    def __init__(self, apply_result):
        self._apply_result = apply_result
        self._lazy_result = NotImplemented
        
    def __getattr__(self, name):
        if self._lazy_result is NotImplemented:
            response = self._apply_result.get()
            self._lazy_result = response.json()
        return self._lazy_result[name]


class DnspodApi(object):
    DnspodApiUrl = "https://dnsapi.cn/"
    Pool = ThreadPool()
    
    def __init__(self, email, password):
        self._context = {
            "login_email": email,
            "login_password": password,
            "format": "json",
            "lang": "cn"
        }

    def call_method_async(self, method_name, **kwargs):
        kwargs.update(self._context)
        return DnspodApiResult(self.Pool.apply_async(requests.post, (
            urljoin(self.DnspodApiUrl, method_name),
            kwargs,
        )))

    def list_domains(self, keyword="", **kwargs):
        return self.call_method_async("domain.list", keyword=keyword, **kwargs)
    
    def list_records(self, domain_id, keyword="", **kwargs):
        return self.call_method_async(
            "record.list", domain_id=domain_id, keyword=keyword,
            **kwargs
        )
        
    def update_record(self, domain, record, **params):
        domain_list = self.list_domains(domain)
        try:
            domain_info = domain_list.domains[0]
        except IndexError:
            raise DomainNotFound(domain)
            
        record_list = self.list_records(domain_info["id"], record)
        try:
            record_info = record_list.records[0]
        except IndexError:
            raise RecordNotFound(record)
            
        params.setdefault("domain_id", domain_info["id"])
        params.setdefault("record_id", record_info["id"])
        params.setdefault("sub_domain", record_info["name"])
        params.setdefault("record_type", record_info["type"])
        params.setdefault("record_line", record_info["line"])
        params.setdefault("mx", record_info["mx"])
        params.setdefault("ttl", record_info["ttl"])
        params.setdefault("status", record_info["status"])
        
        return self.call_method_async(
            "record.modify", **params
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("email", help="email for dnspod")
    parser.add_argument("password", help="password for dnspod")
    parser.add_argument("subdomain", help="subdomain for raspberry pi")
    parser.add_argument(
        "--ip", default=socket.gethostbyname(socket.gethostname()),
        help="ip for raspberry pi"
    )
    args = parser.parse_args()
    
    dnspod = DnspodApi(args.email, args.password)
    record, domain = args.subdomain.split(".", 1)
    result = dnspod.update_record(
        domain, record, value=args.ip,
    )
    print result.status["message"]