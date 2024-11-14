import os
from dotenv import dotenv_values

class Config:
    def __init__(self):
        self.config = {
            **dotenv_values(".env"),
            **dotenv_values(".env.local"),
            **os.environ,
        }

    @property
    def domain_name(self):
        return self.config.get('DOMAIN_NAME')

    @property
    def subdomain(self):
        return self.config.get('SUBDOMAIN')

    @property
    def full_subdomain(self):
        return f"{self.subdomain}.{self.domain_name}"

    @property
    def region(self):
        return self.config.get('REGION', 'us-east-1')

    @property
    def vpc_cidr(self):
        return self.config.get('VPC_CIDR', '10.0.0.0/16')

    @property
    def endpoint_service_name(self):
        return self.config.get('ENDPOINT_SERVICE_NAME')
