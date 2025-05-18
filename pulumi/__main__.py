import pulumi
import pulumi_aws as aws

# -----------------------------------------------------------
# 1. Configuration
# -----------------------------------------------------------
config = pulumi.Config("vilnacrm")
region = config.require("region")
app_runner_url = config.require("app_runner_url")

# -----------------------------------------------------------
# 2. Create an HTTP API Gateway
# -----------------------------------------------------------
api = aws.apigatewayv2.Api(
    "httpApi",
    protocol_type="HTTP"
)

# -----------------------------------------------------------
# 3. Set Up Greedy Proxy Integration for /user/*
# -----------------------------------------------------------
# The {proxy} placeholder will be replaced with whatever path segment(s)
# matched by the route's {proxy+} variable.
integration = aws.apigatewayv2.Integration(
    "userProxyIntegration",
    api_id=api.id,
    integration_type="HTTP_PROXY",
    integration_method="ANY",
    # Embed {proxy} directly in the URI so API Gateway forwards the full path.
    integration_uri=f"{app_runner_url}/user/{{proxy}}"
)

# -----------------------------------------------------------
# 4. Catch-All Route for /user/{proxy+}
# -----------------------------------------------------------
# ANY method, greedy path match under /user.
route = aws.apigatewayv2.Route(
    "userProxyRoute",
    api_id=api.id,
    route_key="ANY /user/{proxy+}",
    target=pulumi.Output.concat("integrations/", integration.id)
)

# -----------------------------------------------------------
# 5. Deploy on the Default Stage
# -----------------------------------------------------------
# AWS requires a non-empty name; using the reserved `$default` yields
# an invoke URL without a stage-name suffix.
stage = aws.apigatewayv2.Stage(
    "apiStage",
    api_id=api.id,
    name="$default",
    auto_deploy=True,
    opts=pulumi.ResourceOptions(depends_on=[route])
)

# -----------------------------------------------------------
# 6. Export the API Endpoint
# -----------------------------------------------------------
# Clients will call this without any extra /<stage> segment.
pulumi.export("apiEndpoint", stage.invoke_url)
