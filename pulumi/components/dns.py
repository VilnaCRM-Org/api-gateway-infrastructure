import pulumi
import pulumi_aws as aws

class DNS:
    def __init__(self, subdomain, hosted_zone_id, api_domain_name):
        # Create a Route53 Alias record pointing the subdomain to the API Gateway domain
        self.alias_record = aws.route53.Record("apiAliasRecord",
            zone_id=hosted_zone_id,
            name=subdomain,
            type="A",
            aliases=[aws.route53.RecordAliasArgs(
                name=api_domain_name.domain_name_configuration.target_domain_name,
                zone_id=api_domain_name.domain_name_configuration.hosted_zone_id,
                evaluate_target_health=False,
            )]
        )
