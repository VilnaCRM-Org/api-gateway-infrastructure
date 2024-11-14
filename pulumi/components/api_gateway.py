import pulumi
import pulumi_aws as aws

class APIGateway:
    def __init__(self, name, vpc_link, vpc_endpoint, subdomain, certificate_arn):
        # Create an API Gateway HTTP API
        self.api = aws.apigatewayv2.Api(f"{name}-httpApi",
            name=f"{name}-http-api",
            protocol_type="HTTP",
            tags={
                "Name": f"{name}-http-api",
            })

        # Create an API integration with the VPC Link and VPC Endpoint
        self.integration = aws.apigatewayv2.Integration(f"{name}-apiIntegration",
            api_id=self.api.id,
            integration_type="HTTP_PROXY",
            connection_type="VPC_LINK",
            connection_id=vpc_link.id,
            integration_uri=vpc_endpoint.dns_entries.apply(
                lambda entries: "http://" + entries[0]['dns_name']
            ),
            payload_format_version="1.0",)

        # Create a default route that forwards all requests to the integration
        self.route = aws.apigatewayv2.Route(f"{name}-defaultRoute",
            api_id=self.api.id,
            route_key="ANY /{proxy+}",
            target=self.integration.id.apply(lambda id: f"integrations/{id}"),)

        # Deploy the API (creates a $default stage)
        self.stage = aws.apigatewayv2.Stage(f"{name}-apiStage",
            api_id=self.api.id,
            name="$default",
            auto_deploy=True,
            tags={
                "Name": f"{name}-api-stage",
            })

        # Create a custom domain name for API Gateway
        self.api_domain_name = aws.apigatewayv2.DomainName(f"{name}-apiDomainName",
            domain_name=subdomain,
            domain_name_configuration=aws.apigatewayv2.DomainNameDomainNameConfigurationArgs(
                certificate_arn=certificate_arn,
                endpoint_type="REGIONAL",
                security_policy="TLS_1_2",
            ),
            tags={
                "Name": f"{name}-api-domain-name",
            })

        # Map the custom domain name to the API stage
        self.api_mapping = aws.apigatewayv2.ApiMapping(f"{name}-apiMapping",
            api_id=self.api.id,
            domain_name=self.api_domain_name.id,
            stage=self.stage.id,
            api_mapping_key="",)
