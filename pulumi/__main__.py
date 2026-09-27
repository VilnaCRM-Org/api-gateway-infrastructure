"""Existing gateway stack plus the TEST user-service TLS prerequisite.

The public route follows after the service's authenticated ALB descriptor.
"""

import pulumi
from pulumi_aws import s3

from poc_gateway import provision_test_certificate

# Preserve the existing main-stack resource and export on updates.
bucket = s3.BucketV2("my-bucket")
pulumi.export("bucket_name", bucket.id)

provision_test_certificate()
