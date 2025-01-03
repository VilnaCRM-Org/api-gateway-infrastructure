import pulumi
import pulumi_aws as aws

from config.config import Config
from components.certificate import Certificate
from components.vpc import VPC
from components.api_gateway import APIGateway
from components.dns import DNS

config = Config()

subdomain = config.full_subdomain
domain_name = config.domain_name
region = config.region
vpc_cidr = config.vpc_cidr
endpoint_service_name = config.endpoint_service_name

# Fetch the existing Route53 hosted zone
hosted_zone = aws.route53.get_zone(name=domain_name)

# Request an ACM certificate for the subdomain
certificate = Certificate(subdomain, hosted_zone.zone_id)

# Create a VPC for API Gateway's VPC Link
vpc = VPC(name="api", cidr_block=vpc_cidr, region=region)

# Create an Interface VPC Endpoint that connects to the endpoint service in Account B
vpc_endpoint = aws.ec2.VpcEndpoint("interfaceVpcEndpoint",
    vpc_id=vpc.vpc.id,
    service_name=endpoint_service_name,
    vpc_endpoint_type="Interface",
    security_group_ids=[vpc.security_group.id],
    subnet_ids=[vpc.subnet1.id, vpc.subnet2.id],
    private_dns_enabled=False,  # Set to False if the endpoint service does not support private DNS
    tags={
        "Name": "interface-vpc-endpoint",
    })

# Create an API Gateway VPC Link
vpc_link = aws.apigatewayv2.VpcLink("apiVpcLink",
    name="api-vpc-link",
    subnet_ids=[vpc.subnet1.id, vpc.subnet2.id],
    security_group_ids=[vpc.security_group.id],
    tags={
        "Name": "api-vpc-link",
    })

# Set up API Gateway
api_gateway = APIGateway(
    name="api",
    vpc_link=vpc_link,
    vpc_endpoint=vpc_endpoint,
    subdomain=subdomain,
    certificate_arn=certificate.certificate_arn
)

# Set up DNS records
dns = DNS(
    subdomain=subdomain,
    hosted_zone_id=hosted_zone.zone_id,
    api_domain_name=api_gateway.api_domain_name
)

# Export the API endpoint URL
pulumi.export("apiEndpoint", api_gateway.api_domain_name.domain_name)

# TODO: remove all manual steps that we need to perform in cli for make plan and make up (automate aws configure, secret password)