"""TEST user-service API Gateway certificate prerequisite.

The public route follows after the service's authenticated ALB descriptor.
"""

from poc_gateway import provision_test_certificate

provision_test_certificate()
