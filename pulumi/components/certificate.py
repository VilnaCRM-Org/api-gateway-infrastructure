import pulumi
import pulumi_aws as aws

class Certificate:
    def __init__(self, subdomain, hosted_zone_id):
        self.certificate = aws.acm.Certificate("api-cert",
            domain_name=subdomain,
            validation_method="DNS",
            tags={
                "Environment": "Production",
            })

        # Wait for the domain validation options to be available
        self.validation_options = self.certificate.domain_validation_options.apply(
            lambda options: options[0]
        )

        self.validation_record = aws.route53.Record("cert-validation",
            zone_id=hosted_zone_id,
            name=self.validation_options.resource_record_name,
            type=self.validation_options.resource_record_type,
            records=[self.validation_options.resource_record_value],
            ttl=300)

        self.certificate_validation = aws.acm.CertificateValidation("certValidation",
            certificate_arn=self.certificate.arn,
            validation_record_fqdns=[self.validation_record.fqdn])

        self.certificate_arn = self.certificate_validation.certificate_arn
