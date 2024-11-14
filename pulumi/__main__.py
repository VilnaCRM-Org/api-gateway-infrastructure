import pulumi
import pulumi_aws as aws
import os
from dotenv import dotenv_values

config = {
    **dotenv_values(".env"),
    **dotenv_values(".env.local"),
    **os.environ,
}

# Configuration variables
domain_name = "vilnacrm.com"
subdomain = "api." + domain_name
region = "us-east-1"  # Change as needed
vpc_cidr = "10.0.0.0/16"

# Replace with the actual endpoint service name provided by Account B
endpoint_service_name = "com.amazonaws.vpce.us-east-1.vpce-svc-xxxxxxxxxxxxxxxxx"

# Fetch the existing Route53 hosted zone
hosted_zone = aws.route53.get_zone(name=domain_name)

# Request an ACM certificate for the subdomain
certificate = aws.acm.Certificate("api-cert",
    domain_name=subdomain,
    validation_method="DNS",
    tags={
        "Environment": "Production",
    })

# Create a DNS validation record
validation_options = certificate.domain_validation_options

validation_record = aws.route53.Record("cert-validation",
    zone_id=hosted_zone.zone_id,
    name=validation_options[0].resource_record_name,
    type=validation_options[0].resource_record_type,
    records=[validation_options[0].resource_record_value],
    ttl=300)

# Wait for certificate validation
certificate_validation = aws.acm.CertificateValidation("certValidation",
    certificate_arn=certificate.arn,
    validation_record_fqdns=[validation_record.fqdn])

# Create a VPC for API Gateway's VPC Link
vpc = aws.ec2.Vpc("api-vpc",
    cidr_block=vpc_cidr,
    enable_dns_support=True,
    enable_dns_hostnames=True,
    tags={
        "Name": "api-vpc",
    })

# Create two public subnets
subnet1 = aws.ec2.Subnet("subnet1",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    availability_zone=region + "a",
    tags={
        "Name": "subnet1",
    })

subnet2 = aws.ec2.Subnet("subnet2",
    vpc_id=vpc.id,
    cidr_block="10.0.2.0/24",
    availability_zone=region + "b",
    tags={
        "Name": "subnet2",
    })

# Create a security group for the VPC Endpoint
vpc_endpoint_sg = aws.ec2.SecurityGroup("vpc-endpoint-sg",
    description="Allow traffic for VPC Endpoint",
    vpc_id=vpc.id,
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            protocol="-1",
            from_port=0,
            to_port=0,
            cidr_blocks=[vpc_cidr],
        ),
    ],
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            protocol="-1",
            from_port=0,
            to_port=0,
            cidr_blocks=["0.0.0.0/0"],
        ),
    ],
    tags={
        "Name": "vpc-endpoint-sg",
    })

# Create an Interface VPC Endpoint that connects to the endpoint service in Account B
vpc_endpoint = aws.ec2.VpcEndpoint("interfaceVpcEndpoint",
    vpc_id=vpc.id,
    service_name=endpoint_service_name,
    vpc_endpoint_type="Interface",
    security_group_ids=[vpc_endpoint_sg.id],
    subnet_ids=[subnet1.id, subnet2.id],
    private_dns_enabled=False,  # Set to False if the endpoint service does not support private DNS
    tags={
        "Name": "interface-vpc-endpoint",
    })

# Create an API Gateway VPC Link
vpc_link = aws.apigatewayv2.VpcLink("apiVpcLink",
    name="api-vpc-link",
    subnet_ids=[subnet1.id, subnet2.id],
    security_group_ids=[vpc_endpoint_sg.id],
    tags={
        "Name": "api-vpc-link",
    })

# Create an API Gateway HTTP API
api = aws.apigatewayv2.Api("httpApi",
    name="my-http-api",
    protocol_type="HTTP",
    tags={
        "Name": "my-http-api",
    })

# Create an API integration with the VPC Link and VPC Endpoint
integration = aws.apigatewayv2.Integration("apiIntegration",
    api_id=api.id,
    integration_type="HTTP_PROXY",
    connection_type="VPC_LINK",
    connection_id=vpc_link.id,
    integration_uri=vpc_endpoint.dns_entries.apply(
        lambda entries: "http://" + entries[0]['dns_name']
    ),
    payload_format_version="1.0",
    tags={
        "Name": "api-integration",
    })

# Create a default route that forwards all requests to the integration
route = aws.apigatewayv2.Route("defaultRoute",
    api_id=api.id,
    route_key="ANY /{proxy+}",
    target=integration.id.apply(lambda id: f"integrations/{id}"),
    tags={
        "Name": "default-route",
    })

# Deploy the API (creates a $default stage)
deployment = aws.apigatewayv2.Stage("apiStage",
    api_id=api.id,
    name="$default",
    auto_deploy=True,
    tags={
        "Name": "api-stage",
    })

# Create a custom domain name for API Gateway
api_domain_name = aws.apigatewayv2.DomainName("apiDomainName",
    domain_name=subdomain,
    domain_name_configuration=aws.apigatewayv2.DomainNameDomainNameConfigurationArgs(
        certificate_arn=certificate_validation.certificate_arn,
        endpoint_type="REGIONAL",
        security_policy="TLS_1_2",
    ),
    tags={
        "Name": "api-domain-name",
    })

# Map the custom domain name to the API stage
api_mapping = aws.apigatewayv2.ApiMapping("apiMapping",
    api_id=api.id,
    domain_name=api_domain_name.id,
    stage=deployment.id,
    api_mapping_key="",  # Empty string maps to the root of the domain
    tags={
        "Name": "api-mapping",
    })

# Create a Route53 Alias record pointing the subdomain to the API Gateway domain
alias_record = aws.route53.Record("apiAliasRecord",
    zone_id=hosted_zone.zone_id,
    name=subdomain,
    type="A",
    aliases=[aws.route53.RecordAliasArgs(
        name=api_domain_name.domain_name_configuration.target_domain_name,
        zone_id=api_domain_name.domain_name_configuration.hosted_zone_id,
        evaluate_target_health=False,
    )],
    tags={
        "Name": "api-alias-record",
    })

# Export the API endpoint URL
pulumi.export("apiEndpoint", api_domain_name.domain_name)
