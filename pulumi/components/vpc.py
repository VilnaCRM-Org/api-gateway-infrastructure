import pulumi
import pulumi_aws as aws

class VPC:
    def __init__(self, name, cidr_block, region):
        self.vpc = aws.ec2.Vpc(f"{name}-vpc",
            cidr_block=cidr_block,
            enable_dns_support=True,
            enable_dns_hostnames=True,
            tags={
                "Name": f"{name}-vpc",
            })

        self.subnet1 = aws.ec2.Subnet(f"{name}-subnet1",
            vpc_id=self.vpc.id,
            cidr_block="10.0.1.0/24",
            availability_zone=f"{region}a",
            tags={
                "Name": f"{name}-subnet1",
            })

        self.subnet2 = aws.ec2.Subnet(f"{name}-subnet2",
            vpc_id=self.vpc.id,
            cidr_block="10.0.2.0/24",
            availability_zone=f"{region}b",
            tags={
                "Name": f"{name}-subnet2",
            })

        self.security_group = aws.ec2.SecurityGroup(f"{name}-vpc-endpoint-sg",
            description="Allow traffic for VPC Endpoint",
            vpc_id=self.vpc.id,
            ingress=[
                aws.ec2.SecurityGroupIngressArgs(
                    protocol="-1",
                    from_port=0,
                    to_port=0,
                    cidr_blocks=[cidr_block],
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
                "Name": f"{name}-vpc-endpoint-sg",
            })
