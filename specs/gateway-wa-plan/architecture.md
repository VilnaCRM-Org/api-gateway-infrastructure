---
artifact: architecture
workflow: _bmad/bmm/workflows/3-solutioning/bmad-create-architecture (Create mode, non-interactive)
task: gateway-wa-plan
source_baseline: f056c8b32c64e502101ec573191d8f229881bc7a
date: 2026-10-01
revision: 1 (pre-commit audit findings 1-22 folded in before the first commit)
inputDocuments: [research.md, brief.md, prd.md, decisions.md, USI specs/workload-wa-hardening (9d5df4a), USI specs/poc-api-gateway-backend.md]
---

# Architecture: the API gateway Well-Architected track

## 1. Target and engine discovery

| Item | Value |
| --- | --- |
| Repository | `VilnaCRM-Org/api-gateway-infrastructure` (id `887871673`, owner id `114362548`, public) |
| Engine | Pulumi, Python; toolchain moves to uv (PD-2) |
| Stacks | `test` (account `891377212104`), `prod` (account `933245420672`), both `eu-central-1` |
| Backend | `s3://pulumi-api-gateway-infrastructure-{env}-state`, `awskms://alias/pulumi-api-gateway-infrastructure-{env}-secrets?region=eu-central-1` (FR-A03) |
| Provider | `pulumi-aws` 7.23.0 (`integration_target`, `endpoint_access_mode`; research GR-17) |
| Deploy path | PR ChatOps `/pulumi <env> plan|up`, OIDC, saved plans, `@Kravalg`-gated environments (AD-A11) |

## 2. Boundaries and ownership

```
bootstrap-infrastructure (BI; CODEOWNERS @Kravalg; seed operator; installer XP-A1)
  ├─ independent CloudFormation stacks (AD-A1, USI AD-26 layer 6):
  │    ├─ AGI identity stack per env: GitHubCi{Preview,Apply,Drift}-api-gateway-
  │    │    infrastructure-{env}, PulumiStateRepl-… (PD-12), their boundaries and
  │    │    immutable guards, identity policies (G1.2; grants by stack amendments
  │    │    G1.4a, G1.4b, G1.7, G1.8; TEST recovery role G1.9 only under OQ-8 (a))
  │    ├─ AGI backend stack per env: state bucket, replica, Pulumi secrets key (G1.3)
  │    ├─ gateway prerequisites stack per account: API Gateway CloudWatch role,
  │    │    AWS::ApiGateway::Account, WAF-log resource policy (G1.5)
  │    └─ gateway CMK per env (G1.6, OQ-2)
  ├─ seed catalogs: registration of the stack-created principals (G1.1)
  └─ no gateway resource (API, WAF, domain, DNS) is BI's

api-gateway-infrastructure (this repo; no IAM resource, no SSM write)
  ├─ repository controls: main ruleset, CODEOWNERS, environments (G2.2, XP-A3)
  ├─ pipeline: battery, guardrails, ChatOps saved plans, drift + probe (G3.x)
  ├─ certificate + DNS validation per env (G4.1 = PR #34 amended, G4.2)
  ├─ contracts/user-service-backend/{env}.json (pinned USI coordinates, G5.1, G6.1)
  └─ front door per env: VPC link V2, REST API, stage, WAF, custom domain,
       alias records, log groups, topic, alarms (G5.2-G5.5, G6.2)

user-service-infrastructure (USI; external, unchanged by this plan)
  ├─ internal ALB in two app subnets; HTTPS listener on 443 with the gateway
  │    certificate pinned by D-15 (USI XP-10, XP-15)
  ├─ ALB SG: sole ingress TCP 443 from the VPC-link SG
  └─ VPC-link SG (user-service-vpc-link-sg): no ingress, 443 egress to app subnets;
       attached by AGI to its VPC link, never edited by AGI
```

Request path: client → `https://<fqdn>` (Regional custom domain, TLS policy,
`STRICT`) → WAF web ACL on stage `live` → REST API `ANY /{proxy+}` →
`HTTP_PROXY` over VPC link V2 (ENIs in the USI app subnets, VPC-link SG) →
internal ALB HTTPS 443 (certificate name verified against the `uri` host) →
ECS tasks.

## 3. Architecture decisions

- **AD-A1 Gateway CI identities and the six IAM layers (FR-A01, FR-A02,
  FR-A04; OQ-1).**
  The documented catalog route is blocked: `G-GitHubGovernanceApply`
  denies `iam:CreateRole` on `*` and every `iam:*` outside the USI ARNs
  (research GR-12). The plan's default, pending **OQ-1**, is option (a):
  - **Layer 6, principal creation.** A reviewed BI CloudFormation identity
    stack per environment, installed by the XP-A1 installer, creates the
    three CI roles, the replication role (PD-12), their boundaries and
    their guards, as the USI plan creates its new principals (USI AD-26
    layer 6; the #285 precedent: reviewed template and hash, `Retain`, a
    permanent deny-update stack policy, absent-name checks, CREATE
    change-set evidence, a post-create verifier, `@Kravalg`'s approval).
    Each role's guard is a managed policy created and attached **in the
    same stack**, as USI S5.1 does for its ECS roles' `-Guard` policies, so
    no role exists unguarded. Every later grant is a reviewed stack
    amendment (narrow during-update stack policy, UPDATE change-set rows,
    post-update verifier).
  - **Seed registration after creation (G1.1).** The seed catalog then
    registers the installed principals as `existing: true`, with their
    boundaries and guards hash-pinned. In the seed code `existing: false`
    means a new operator executor (BI `pulumi/seed/policy_registry.py`:
    `_verify_role` lines 431-446, `_active_executor_trust` lines 505-514,
    `verify_active_enrollment` lines 570-590), and the registry fixes the
    principal counts (line 355: "Expected 21 existing roles"; README: 24
    principals). G1.1 therefore changes the verifier: the counts, a
    principal kind for independently created service roles, and its
    attachment rule. V-A10 is the BI owner's confirmation that this is
    the right registration shape.
  - **Trust.** The OIDC provider; `aud` `sts.amazonaws.com`; the
    `token.actions.githubusercontent.com:repository_id` (`887871673`) and
    `:repository_owner_id` (`114362548`) claims, as BI pins them for other
    repositories (BI `pulumi/infra/github_identity.py` lines 31-41); the
    `sub` in both the name and the immutable-id format (lines 44-68), for
    exactly one environment per role: `{env}-preview`, `{env}` or
    `{env}-drift`. **No `pull_request` subject** (research GR-11: the
    generic TEST preview trust would add one; USI had it retired in #276).
    The replication role trusts only `s3.amazonaws.com` with
    `aws:SourceAccount`.
  - **No ConfigRead roles** (PD-7): the pipeline reads role ARNs and
    backend names from protected-environment variables.
  - **Layer 3, boundary as a service-family ceiling.** The CI boundary
    allows `sts:GetCallerIdentity`, the state bucket and secrets key, and
    the gateway service families (`apigateway`, `wafv2`, `acm`, `route53`
    on the gateway zones, `logs` on the gateway log groups plus the
    log-delivery and Logs Insights actions, `cloudwatch` alarms and the
    probe metric namespace, `sns` on the gateway topic, `kms` on the
    gateway CMK, and the read-only `elasticloadbalancing` and `ec2`
    describes of AD-A7). Exact resources stay in the identity allows. A
    ceiling sized up front means later grant changes are identity
    amendments only (the USI plan's fallback form, USI `epics-stories.md`
    Epic 5 preamble). The rendered size is checked against 6144
    characters in G1.2.
  - **Layer 4, guards.** Modelled on the USI ones: the Preview and Drift
    guard denies role creation and deletion, permissions-boundary
    changes, secret and parameter reads, the ECR token and STS session
    issuance on Resource `*` (the shape of USI's `ae950d73…`); the Apply
    guard denies role creation and deletion and STS session issuance (the
    shape of `dc27f076…`) and secret and parameter reads (the shape of
    `9f269660…`, with no CI-secret exception, because the gateway has no
    CI secrets, PD-7). They are new statements for new principals; **no
    existing seed statement changes.**
  - **Layer 5, attachment constraint.** The seed's attachment rules
    (`_mutable_attachment_sets`, `verify_active_enrollment`) gain entries
    for the gateway roles only.
  - **Layers 1-2, identity allows and denies.** AD-A7.
  - If the user chooses OQ-1 (b) instead, G1.2 becomes the governance
    catalog PR (the documented PR A) after a guard amendment in G1.1's
    slot that lets the governance stack create the roles; the trust,
    ceiling, guard and deny content of this decision still applies.
- **AD-A2 PR #34: adopt and amend (FR-A14, FR-A24; PD-9).**
  - **Kept:** `assert_test_target`, `only_validation_option`, the stack
    check, the certificate, the validation record with
    `allow_overwrite=False`, `CertificateValidation`, the tests.
  - **Dropped:** the `aws.ssm.Parameter` and the two parameter exports.
    Under D-15 no role reads it, and keeping it would need an
    `ssm:PutParameter` grant for an unused value.
  - **Dropped:** the `my-bucket` preservation. The governed backend is new
    and empty, so the program never owned that bucket there; OQ-5 handles
    any legacy bucket outside it.
  - **Changed:** the account, region, zone and FQDN move from Python
    constants into stack config (FR-A09); both resources get `protect` and
    `retainOnDelete`; the module moves to `pulumi/app/certificate.py`
    behind the `features.certificate` flag (AD-A15); the tests move to
    pytest with 100% branch coverage.
  - **Sequence:** rebased after the pipeline (G3.4), so its first apply is
    a saved plan. The author's commits stay; a maintainer may push the
    amendment commits if the author agrees, otherwise a successor PR
    cherry-picks them with `Co-authored-by` credit.
  - **Why not adopt as is:** it merges an SSM publication D-15 retired and a
    resource kept for a backend this pipeline does not use. **Why not
    supersede:** its fail-closed logic and tests are correct and reviewed.
- **AD-A3 The cross-repository contract (FR-A14, FR-A15, FR-A16, FR-A25;
  OQ-7, OQ-8).** Two pins, one in each direction, both reviewed PRs,
  neither a broad read:
  - **Gateway → USI (D-15):** the gateway owner hands the issued
    certificate ARN to the USI owner (XP-A8); a USI contract PR pins it
    (USI XP-10, XP-15). Nothing is published in SSM.
  - **USI → gateway:** the USI owner hands over the
    `poc-api-gateway-backend/v1` field values (XP-A7); a gateway PR pins
    them in `contracts/user-service-backend/{env}.json` with their source
    (the USI apply run URL and commit, and the sha256 of the canonical
    JSON). A Pulumi `StackReference` would need a read on the USI state
    bucket and its key; it is rejected.
  - **Provenance (OQ-7).** The USI spec's authenticated publication does
    not exist (USI `specs/poc-api-gateway-backend.md` lines 10-15). Under
    the recommended OQ-7 (a), the authority is the gateway's own live
    re-verification below; the strongest binding is the listener's
    certificate, which must be this repository's certificate.
  - **What the gateway uses:** `listener_arn`, the load balancer ARN
    derived from it (`…:listener/app/<name>/<id>/<l>` →
    `…:loadbalancer/app/<name>/<id>`), `subnet_ids`,
    `vpc_link_security_group_id`, `alb_security_group_id`, `vpc_id`,
    `tls_server_name` and `certificate_arn`. `integration_type` and
    `connection_type` are checked equal to `HTTP_PROXY` and `VPC_LINK`.
    `request_parameters` is checked equal to the v1 constant and not used:
    the REST API maps the path itself (AD-A4; K-9; USI-F1).
  - **Live verification on every preview and drift**, by Pulumi data-source
    invokes in the program (so a mismatch fails the plan): the listener
    (HTTPS, 443, that load balancer, that certificate), the load balancer
    (internal, `application`, those subnets, only the ALB group), the ALB
    group (its only ingress is TCP 443 from the VPC-link group), the
    VPC-link group (no ingress), the subnets (in `vpc_id`).
  - **The USI abandon rehearsal (OQ-8).** USI S4.6 step 18 requires no
    foreign ENI in the application subnets, step 19 deletes them with the
    security groups, and step 20 rebuilds them with new ids. A VPC link
    holds ENIs in those subnets and pins their ids (VPC link V2 is
    immutable, GA-2). Under the recommended OQ-8 (c), USI runs step 17
    after step 20, and the gateway's TEST rows run once, against the
    rebuilt workload. Under OQ-8 (a), the conditional rows G1.9, G5.7 and
    G5.8 tear the gateway's TEST VPC-link-dependent resources down before
    step 18 through a reviewed manifest and a TEST-only recovery role
    (FR-A25) and rebuild them after step 20.
  - **Replacement windows (operating residual, not a risk acceptance).**
    If USI replaces its ALB, listener or a group outside the rehearsal,
    gateway previews and drift fail closed until a gateway PR pins the
    new descriptor; a changed subnet or VPC-link group needs a new VPC
    link, which in PROD is a reviewed recovery outside routine apply (no
    PROD delete grant exists). If the gateway replaces its certificate, the
    USI side has the D-15 residual of USI `prd.md` §7 XP-10.
  - **Invariant the USI side keeps** (AS-2): the ALB SG's sole ingress
    from the VPC-link SG; the VPC-link SG with no ingress. The gateway
    never adds a rule to either group.
- **AD-A4 Front-door topology (FR-A17; D-3; V-A1, V-A2, V-A4).**
  - `aws.apigatewayv2.VpcLink` on the two pinned subnets with only the
    pinned VPC-link group.
  - `aws.apigateway.RestApi` (`endpoint_configuration REGIONAL`,
    `disable_execute_api_endpoint True`, no API keys, no authorizer: the
    application authenticates), resources `/` and `/{proxy+}`, method
    `ANY`, `authorization NONE`.
  - `aws.apigateway.Integration`: `type HTTP_PROXY`,
    `connection_type VPC_LINK`, `connection_id` the VPC link id,
    `integration_target` the derived load balancer ARN (GA-1, GR-17),
    `integration_http_method ANY`, `uri https://<fqdn>/{proxy}` (root:
    `https://<fqdn>/`), `request_parameters
    {"integration.request.path.proxy": "method.request.path.proxy"}`,
    `tls_config.insecure_skip_verification False`, timeout 29,000 ms.
  - `aws.apigateway.Deployment` with `triggers` on a hash of the API
    definition, and `aws.apigateway.Stage` `live`.
  - **NLB fallback (V-A1):** only if V-A1 fails in TEST. A reviewed
    variant puts an internal NLB (TCP 443, ALB-type target group) in front
    of the ALB; it needs a USI change (the NLB's group in the ALB's
    ingress) and a new contract field, so it is a new plan revision, never
    a silent switch.
- **AD-A5 Stage logging and throttling (FR-A18; PD-3, PD-5).**
  - Access log group `/aws/apigateway/api-gateway-infrastructure-{env}/access`,
    KMS key per OQ-2, retention PD-5. JSON format:
    `{"requestId":"$context.requestId","ip":"$context.identity.sourceIp","requestTime":"$context.requestTime","httpMethod":"$context.httpMethod","resourcePath":"$context.resourcePath","path":"$context.path","status":"$context.status","protocol":"$context.protocol","responseLength":"$context.responseLength","responseLatency":"$context.responseLatency","integrationLatency":"$context.integration.latency","integrationStatus":"$context.integration.status","wafResponseCode":"$context.wafResponseCode","tlsVersion":"$context.tlsVersion","cipherSuite":"$context.cipherSuite","userAgent":"$context.identity.userAgent","domainName":"$context.domainName"}`.
  - `aws.apigateway.MethodSettings` on `*/*`: `metrics_enabled true`,
    `logging_level OFF`, `data_trace_enabled false`,
    `throttling_rate_limit` and `throttling_burst_limit` per PD-3 or OQ-6,
    `caching_enabled false`.
  - The account's `cloudWatchRoleArn` is BI's (AD-A9); this repository
    never manages `aws.apigateway.Account`.
- **AD-A6 WAF (FR-A19; PD-4, PD-8).**
  - `aws.wafv2.WebAcl` `api-gateway-infrastructure-{env}`, scope `REGIONAL`,
    default action Allow, `visibility_config` with metrics and sampled
    requests on the ACL and every rule.
  - Rules, in priority order: 0 `AWSManagedRulesAmazonIpReputationList`
    (block); 1 `AWSManagedRulesKnownBadInputsRuleSet` (block); 2
    `AWSManagedRulesCommonRuleSet` (TEST: `override_action count` until
    gate A-T step 11 switches it; PROD: block, with any rule overrides the
    TEST evidence justified); 3 `AWSManagedRulesAnonymousIpList` (count);
    10 rate rule on the token path (scope-down: URI path starts with the
    token path that G5.4 reads from the user-service routes, limit PD-4,
    window 300 s, aggregate `IP`, block); 11 global rate rule (limit
    PD-4, window 300 s, aggregate `IP`, block).
  - The aggregation key is the source IP that WAF sees on a Regional REST
    API stage, which is the client's address; no forwarded-IP header is
    trusted.
  - WCU is computed in a unit test from the published capacities and
    must stay ≤ 1,500.
  - `aws.wafv2.WebAclAssociation` to the stage ARN (needs both
    `wafv2:AssociateWebACL` and `apigateway:SetWebACL`, AD-A7);
    `aws.wafv2.WebAclLoggingConfiguration` to
    `aws-waf-logs-api-gateway-infrastructure-{env}` (KMS per OQ-2,
    retention PD-5), `redacted_fields` single header `authorization` and
    `cookie`; log filter: keep all.
- **AD-A7 Identity allows and denies (FR-A04; NFR-A02; V-A3, V-A7, V-A8).**
  `{a}` is the account, `{fqdn}` the stack FQDN, `{zone}` the zone id,
  `P` = `api-gateway-infrastructure-{env}`, `G` the gateway CMK. All
  Regional ARNs are `eu-central-1`. Rows marked **cert** are granted by
  G1.4a (TEST) and G1.7 (PROD); all other rows by G1.4b (TEST) and G1.8
  (PROD).

  | Role | Allow | Resources and conditions | Grant |
  | --- | --- | --- | --- |
  | Preview, Drift, Apply | state and secrets key (BI backend pattern) | the FR-A03 bucket and key | G1.2 |
  | Preview, Drift, Apply | `acm:DescribeCertificate`, `ListTagsForCertificate` | `certificate/*` with `aws:ResourceTag/Owner = api-gateway-infrastructure` (GA-16; V-A7) | cert |
  | Preview, Drift, Apply | `route53:GetHostedZone`, `ListResourceRecordSets`, `ListTagsForResource`; `route53:GetChange` | `hostedzone/{zone}`; `change/*` | cert |
  | Apply | `acm:RequestCertificate`, `AddTagsToCertificate` | `acm:DomainNames` = [`{fqdn}`], `acm:ValidationMethod` = `DNS`, `aws:RequestTag/Owner = api-gateway-infrastructure` on request; `aws:ResourceTag/Owner` on tagging (GA-16) | cert |
  | Apply | `route53:ChangeResourceRecordSets` (validation) | `hostedzone/{zone}`; names `_*.{fqdn}`, type `CNAME`, action `CREATE`; `Null` guards on the three keys (the BI DKIM precedent, GR-14) | cert |
  | Preview, Drift, Apply | `apigateway:GET` | `arn:aws:apigateway:eu-central-1::/restapis`, `/restapis/*`, `/vpclinks`, `/vpclinks/*`, `/domainnames`, `/domainnames/{fqdn}`, `/domainnames/{fqdn}/*`, `/tags/*`, `/account` | |
  | Preview, Drift, Apply | `wafv2:GetWebACL`, `GetLoggingConfiguration`, `GetWebACLForResource`, `ListTagsForResource`, `ListResourcesForWebACL`; `wafv2:DescribeManagedRuleGroup`, `ListAvailableManagedRuleGroups`, `CheckCapacity` | `regional/webacl/P/*` (for a REST stage, `GetWebACLForResource` and `ListResourcesForWebACL` are authorized on the web ACL, GA-17); the managed-rule and capacity actions on `*` only if V-A8 shows no resource-level support | |
  | Preview, Drift, Apply | `logs:DescribeLogGroups`; `logs:ListTagsForResource` | `log-group:*` (V-A8); the two gateway log groups | |
  | Preview, Drift, Apply | `cloudwatch:DescribeAlarms`, `ListTagsForResource`; `sns:GetTopicAttributes`, `ListTagsForResource`, `ListSubscriptionsByTopic`; `kms:DescribeKey` | `alarm:P-*`; `…:sns:…:P-alarms`; `G` | |
  | Preview, Drift, Apply | `elasticloadbalancing:DescribeListeners`, `DescribeLoadBalancers`, `DescribeTags`; `ec2:DescribeSecurityGroups`, `DescribeSecurityGroupRules`, `DescribeSubnets`, `DescribeVpcs` | `*`, the read-only exceptions without resource-level support (V-A8 confirms each from the Service Authorization Reference) | |
  | Drift | evidence reads: `logs:StartQuery`, `GetQueryResults`, `FilterLogEvents`; `wafv2:GetSampledRequests` | the two gateway log groups (`GetQueryResults` on `*` if V-A8 says so); `regional/webacl/P/*` | |
  | Drift | `cloudwatch:PutMetricData` | `cloudwatch:namespace` = `ApiGatewayInfrastructure/{env}` (the probe metric) | |
  | Apply | `apigateway:POST`, `PUT`, `PATCH` | `/restapis`, `/restapis/*`, `/vpclinks`, `/vpclinks/*`, `/domainnames`, `/domainnames/{fqdn}`, `/domainnames/{fqdn}/*`, `/tags/*`; creates and updates of `/restapis` require `apigateway:Request/DisableExecuteApiEndpoint` true (GA-7, V-A11) | |
  | Apply | `apigateway:SetWebACL` | `/restapis/*/stages/*` (required with `wafv2:AssociateWebACL` for REST stages; GA-17) | |
  | Apply | `apigateway:DELETE` | only `/restapis/*/deployments/*` (AD-A10 allowance) | |
  | Apply | `wafv2:CreateWebACL`, `UpdateWebACL`, `AssociateWebACL`, `PutLoggingConfiguration`, `DeleteLoggingConfiguration`, `TagResource` | `regional/webacl/P/*`, the stage ARN, the managed rule groups (`regional/managedruleset/*/*`) | |
  | Apply | `route53:ChangeResourceRecordSets` (alias) | `hostedzone/{zone}`; names `{fqdn}`, types `A`, `AAAA`, actions `CREATE`, `UPSERT`, `DELETE` (an in-place change may be sent as a delete-and-create batch; a lone delete is still stopped by the destructive gate); `Null` guards | |
  | Apply | `logs:CreateLogGroup`, `PutRetentionPolicy`, `AssociateKmsKey`, `TagResource`; `logs:CreateLogDelivery`, `DeleteLogDelivery`, `DescribeResourcePolicies` | the two gateway log groups; the log-delivery actions on `*` (GA-9) | |
  | Apply | `kms:DescribeKey`, `kms:CreateGrant` | `G`, `kms:ViaService = logs.eu-central-1.amazonaws.com` (USI research A-28) | |
  | Apply | `cloudwatch:PutMetricAlarm`, `TagResource`, `SetAlarmState` | `alarm:P-*` (`SetAlarmState` for gate A-T step 9) | |
  | Apply | `sns:CreateTopic`, `SetTopicAttributes`, `TagResource`, `Subscribe` | `…:sns:eu-central-1:{a}:P-alarms` | |

  **Denies on the three CI roles (layer 2):** `iam:*`; `ssm:*`;
  `secretsmanager:GetSecretValue` and `BatchGetSecretValue`;
  `lambda:GetFunction`; `apigateway:PATCH`, `PUT`, `POST` and `DELETE` on
  `/account`; `logs:PutResourcePolicy` and `DeleteResourcePolicy`;
  `route53:ChangeResourceRecordSets` for names `*._domainkey.*` (AD-A8);
  every `Delete*` of `wafv2`, `acm`, `logs`, `sns`, `cloudwatch` and
  `apigateway`, **except** `apigateway:DELETE` on
  `/restapis/*/deployments/*`, `wafv2:DeleteLoggingConfiguration` and
  `logs:DeleteLogDelivery` (the deny uses `NotAction`/`NotResource` for
  these three); `sts:AssumeRole`. Preview and Drift have no write except
  Drift's `PutMetricData`. If V-A7 shows that a certificate read does not
  support the tag condition, the fallback (account-wide `certificate/*`
  metadata reads) is a user decision, as D-15's option (c) is for USI; it
  is not defaulted.

  **TEST recovery role (OQ-8 (a) only, G1.9):**
  `GitHubCiRecovery-api-gateway-infrastructure-test`, trust
  `environment:test-recovery`, the same boundary; allows the Preview
  read set; the state bucket and secrets key read and write (a saved
  destroy writes the checkpoint; G1.9 amends the G1.3 bucket and key
  policies for this role); `apigateway:DELETE` on `/restapis/*`,
  `/vpclinks/*` and `/domainnames/{fqdn}/basepathmappings/*` with
  `aws:ResourceTag/Owner = api-gateway-infrastructure` where API Gateway
  supports the tag condition, otherwise on the exact ids the manifest
  names (set by the G1.9 amendment after the TEST apply); `apigateway:PATCH`
  on `/restapis/*/stages/*` (removing method settings is a stage update);
  and `apigateway:SetWebACL` on `/restapis/*/stages/*` (a REST stage's
  disassociation needs only that action, GA-17); nothing else.
  No PROD recovery role exists.
- **AD-A8 DNS and the shared TEST zone (FR-A14, FR-A20; XP-A6).** The TEST
  zone already holds USI's DKIM CNAMEs (`<token>._domainkey.user.vilnacrmtest.com`,
  GR-14). The gateway owns only `user.vilnacrmtest.com` (alias A and AAAA)
  and the ACM validation CNAME `_<token>.user.vilnacrmtest.com`. The
  `_*.{fqdn}` pattern does not match the DKIM names (their first label
  does not start with `_`); the explicit deny on `*._domainkey.*` is
  defence in depth, so no future pattern of this repository can reach
  USI's records. All gateway records are `protect`ed and
  `retainOnDelete`; the validation CNAME must stay for managed renewal
  (GA-15); `aws:route53/` is a critical type in the destructive gate.
- **AD-A9 Account-level logging role and WAF log policy (FR-A05; OQ-4;
  K-6, K-7).** The BI prerequisites stack, per account:
  - `ApiGatewayCloudWatchLogs-{env}`, trusted by `apigateway.amazonaws.com`
    with `aws:SourceAccount` = the account, with an inline policy of
    `logs:CreateLogStream`, `PutLogEvents`, `DescribeLogStreams` on the
    access-log group ARN and `logs:DescribeLogGroups` on `log-group:*`
    (the same V-A8 scope as AD-A7), instead of the AWS managed policy on
    `*` (GA-4; V-A9);
  - `AWS::ApiGateway::Account` with that role's ARN (after XP-A12);
  - under OQ-4 (a), an `AWS::Logs::ResourcePolicy` allowing
    `delivery.logs.amazonaws.com` to write to
    `aws-waf-logs-api-gateway-infrastructure-*` with `aws:SourceAccount`
    and `aws:SourceArn` conditions (V-A6).

  Execution logging stays off (AD-A5), so the role needs no
  `API-Gateway-Execution-Logs_*` group.
- **AD-A10 Guardrails and the policy pack (FR-A11).**
  - **Destructive gate:** the ported `scripts/pulumi_ci_guardrails.py`
    with `CRITICAL_TYPE_PATTERNS` extended by `aws:apigateway/`,
    `aws:apigatewayv2/`, `aws:wafv2/`, `aws:acm/`, `aws:cloudwatch/logGroup`
    (`aws:route53/` and `aws:kms/` are already there). One allowance,
    pinned by a test: `aws:apigateway/deployment:Deployment` may be
    replaced when the plan is create-before-delete and the stage moves to
    the new deployment in the same plan. Nothing else, no label override.
    The OQ-8 (a) teardown runs in a separate recovery mode that accepts a
    delete only when it matches the reviewed manifest 1:1 (FR-A25).
  - **IAM gate:** any `aws:iam/*` resource in the plan fails.
  - **Policy pack (CrossGuard, mandatory):** every REST API has
    `disable_execute_api_endpoint`; every stage has an access-log
    destination in a gateway log group, `logging_level OFF` and
    throttling on `*/*`; **every stage that a base path mapping
    references** has exactly one web ACL association (a stage without a
    mapping is unreachable, because the default endpoint is disabled, so
    G5.3 can create the stage before G5.4 adds the ACL); every domain uses
    the AD-A4 TLS policy and `STRICT` (or the V-A5 fallback with a
    recorded reason); every log group has a KMS key and a retention;
    every integration with `connection_type VPC_LINK` has
    `insecure_skip_verification False`; every alarm carries a `runbook`
    tag; no `aws:ssm/*` resource.
- **AD-A11 Pipeline and repository controls (FR-A07, FR-A08, FR-A10,
  FR-A12, FR-A13).** Port the generic USI parts (research GR-8): the PR
  battery workflows, `pulumi-pr-guardrails.yml`, `pulumi-pr-commands.yml`,
  `codeql.yml`, `security-scans.yml`, `scheduled-drift.yml`,
  `initialize-stack.yml`, and `scripts/pulumi_ci_guardrails.py`,
  `pulumi_pr_comment.py`, `pulumi_command_preflight.py`,
  `run_pulumi_command.py`, `_pulumi_command_support.py`,
  `configure_github_repository_controls.py`,
  `_github_repository_controls.py`, `_github_environment_controls.py`.
  Not ported: `scripts/poc_*`, `scripts/service_execution_*`, the
  registry and workload stages of `self-deploy.yml`. The deploy workflow
  `deploy.yml` (on `repository_dispatch` `pulumi-pr-command`) has jobs
  `preflight` → `{env}_preview` (Preview role, `{env}-preview`, saved
  plan + sha256 artifact) → `{env}_destructive_diff` → `{env}_iam_gate` →
  `{env}_apply` (`{env}` environment, Apply role, sha256 re-checked, `pulumi
  up --plan`) → `comment_result`; `role-session-name`
  `gha-agi-{env}-{purpose}-${{ github.run_id }}`; no
  `role-duration-seconds` above 3600. PROD preflight requires a
  successful TEST apply of the same head SHA. Drift runs `pulumi preview
  --refresh --expect-no-changes` (USI `scripts/_pulumi_command_support.py`
  line 68). `autorelease.yml` follows PD-11.

  **Required checks (the ruleset):** `Ruff`, `Types`, `Maintainability`,
  `Coverage`, `Bandit`, `Dependency Audit`, `Secrets Scan`, `Actionlint`,
  `Zizmor`, `Yamllint`, `Hadolint`, `Dependency Review`, `CodeQL (python)`,
  `CodeQL (actions)`, `Structural Preview`, `Destructive Diff Gate`,
  `IAM Gate`, `Policy`, `Contract Schema`. Each name equals a job that
  exists by G3.3 (`Contract Schema` validates `contracts/schema/` and
  every file under `contracts/`, and passes with only the schema
  present), and a unit test in G2.2 pins the list against the workflows.
- **AD-A12 Gate model and order against the USI gates (FR-A22, FR-A23,
  FR-A25; D-6; OQ-8).** Three gateway gates:
  - **Gate A-0 (pipeline ready):** rows 1-13 done; `/pulumi test plan` on
    an empty-diff head succeeds; ruleset and environments read back.
  - **Gate A-T (TEST front door):** rows 20-24 applied; the campaign, run
    inside the USI TEST daytime window (PD-13); probes are
    unauthenticated HTTPS and TLS from the runner; evidence reads run
    under the Drift role in `test-drift`; only step 9 uses the Apply role:
    1. preview contract checks pass (AD-A3);
    2. `GET https://user.vilnacrmtest.com/<health path>` returns the
       service's response, and the request id is found in the access log
       (Logs Insights, Drift role);
    3. the default `execute-api` URL returns 403;
    4. the ALB DNS name resolves only to private addresses, and a TCP
       connect from the runner to port 443 fails;
    5. TLS: 1.3 and 1.2 (ECDHE GCM) succeed; 1.1 and a 1.2 CBC suite fail;
       an SNI/Host mismatch is rejected (`STRICT`);
    6. WAF: a known-bad-input probe is blocked, with the terminating rule
       in the WAF log; `GetSampledRequests` shows samples for each rule
       that matched; the `authorization` header is redacted;
    7. rate: a burst above PD-3 gets 429; the token-path rate rule blocks
       after its limit inside one window;
    8. access-log lines carry every AD-A5 field and no header or body;
    9. `SetAlarmState` on each alarm reaches the topic;
    10. two consecutive scheduled drift runs (weekday daytime) are clean
        and their probes succeed;
    11. after at least seven days of WAF logs, a reviewed PR switches
        `AWSManagedRulesCommonRuleSet` to block, with any rule override
        justified from the logs (PD-8);
    12. the evidence bundle (run URLs, artifact sha256s) of steps 1-10 is
        attached to the G5.6 PR and handed to the USI owner for USI S4.6
        step 17 as soon as step 10 passes. Step 11 is **not** part of the
        step-17 bundle, so it never holds the USI campaign; it must pass
        before gate A-P. Step 10 holds step 17 for two weekday drift runs.
  - **Gate A-P (PROD front door):** gate A-T passed; USI gate 2 passed and
    the USI PROD workload applied (USI row 52); the PROD certificate
    issued (G4.2); the PROD contract pinned (G6.1); OQ-3 and OQ-6
    answered; then the same campaign in PROD (daily schedule), with step
    11 already done.

  **Order against the USI ordered list (USI `epics-stories.md`):**

  | Gateway row | Must happen | USI row or step |
  | --- | --- | --- |
  | 15 (G4.1 TEST certificate) applied and handed over | before | row 42 (XP-11 needs the XP-10 ARN), hence before row 43 (gate 1) |
  | 19 (XP-A7 TEST descriptor) | after | row 43, S4.6 step 20 under OQ-8 (c); step 2 under OQ-8 (a) |
  | 20-25 (TEST front door, gate A-T) | before | S4.6 step 17, which under OQ-8 (c) USI runs after step 20 |
  | 26-27 (OQ-8 (a) only: recovery role, teardown, ENI read-back) | before | S4.6 step 18 |
  | 28 (OQ-8 (a) only: re-pin and rebuild) | after | S4.6 step 20 |
  | 30 (G4.2 PROD certificate) applied and handed over | before | row 49 (XP-15), hence before row 52 (gate 2a) |
  | 31 (XP-A7 PROD descriptor), 33-35 (gate A-P) | after | row 52 (gate 2b and the PROD apply) |

  USI S4.6 step 17's "S5.16 has merged" means gateway row 24 applied and
  row 25's evidence published. USI gate 2's "S5.16 with S4.6 step 17
  evidence if PROD is publicly exposed" is met by row 25.
- **AD-A13 Dependabot PRs (FR-A24; PD-10).**
  - **#33** (super-linter 7.1.0 → 8.3.1): **close.** G2.1 removes the
    super-linter workflow, which never fails a PR (`continue-on-error`)
    and pushes with an App token on PR events; its checks fail anyway
    (GR-5).
  - **#32** (virtualenv in `poetry.lock`): **close.** G3.1 replaces Poetry
    with a uv lockfile (PD-2); pip-audit in G3.2 gates every resolved
    version, including any virtualenv advisory.
  - **#26** (all-deps group, `pulumi-aws` 6.62.2): **close.** It stays on
    the 6.x line; G3.1 pins `pulumi-aws` 7.23.0, the version this plan
    verified for `integration_target`. No checks ran on its head.
  - Rebasing any of them would produce a change G2.1 or G3.1 deletes.
    Each is closed with a comment that names the superseding story.
- **AD-A14 KMS (FR-A06; OQ-2).** Under OQ-2 (a), one BI-owned symmetric CMK
  per environment for the two log groups and the topic. Key policy
  statements: the account root (administration through BI only);
  `logs.eu-central-1.amazonaws.com` with `kms:Encrypt*`, `Decrypt*`,
  `ReEncrypt*`, `GenerateDataKey*`, `Describe*`, conditioned on
  `kms:EncryptionContext:aws:logs:arn` equal to the two log-group ARNs;
  `cloudwatch.amazonaws.com` and `sns.amazonaws.com` for the topic
  (`kms:Decrypt`, `GenerateDataKey*`) with `aws:SourceAccount`; the
  gateway Apply role's `kms:DescribeKey` and `kms:CreateGrant` via `logs`.
  Rotation on. Under OQ-2 (b), the same statements go into the D-4 runtime
  CMK's policy by a reviewed BI change.
- **AD-A15 Program structure and feature flags (FR-A09).**
  `pulumi/__main__.py` loads `app/config.py` (stack config, typed, closed)
  and builds, in order: `app/certificate.py` (AD-A2),
  `app/backend_contract.py` (AD-A3: load, offline checks, live invokes),
  `app/observability.py` (log groups, topic, alarms), `app/front_door.py`
  (VPC link, REST API, deployment, stage, method settings), `app/waf.py`,
  `app/domain.py` (domain, mapping, alias records). Two stack-config
  flags gate them: `features.certificate` (the certificate module) and
  `features.front_door` (every module after it; under OQ-8 (a) it also
  takes a `detached` value that keeps the domain, DNS, web ACL, logs and
  alarms but drops the VPC link and the REST API, G5.7). Both start `false` in
  both stacks; the TEST flags turn on in G4.1 and G5.1, the PROD flags in
  G4.2 and G6.1. So a PROD drift run before row 30 previews an empty
  program and needs no PROD grant beyond the backend, and a PROD stack
  never shows pending creates from TEST work. Each module exposes a pure
  builder tested with Pulumi mocks. `contracts/` holds the JSON schema
  and the per-stack contracts; `policy/` the CrossGuard pack;
  `docs/runbooks/` the runbooks.

## 4. IAM and state boundary; single-writer chains

- **No IAM in this repository.** The program declares no `aws:iam/*`
  resource, no `aws.apigateway.Account` and no `aws:ssm/*`.
- **State.** One stack per environment in the FR-A03 backend; no stack
  reads another stack's state.
- **Chains (one writer at a time):**

  | Chain | Files or objects | Order |
  | --- | --- | --- |
  | C-BI-A (seed operations and stack installs, shared with the USI C-BI queue, XP-A4) | BI seed catalogs, `policy_registry.py`, the gateway stacks | G1.2 → G1.1 → G1.3 → G1.4a → G1.5 → G1.6 → G1.4b → [G1.9] → G1.7 → G1.8 (TEST before PROD inside each) |
  | C-controls | `scripts/configure_github_repository_controls.py`, `_github_*`, CODEOWNERS | G2.1 → G2.2 → XP-A3 → [G1.9 part 4: the `test-recovery` environment and its XP-A3 re-apply] |
  | C-pipeline | `.github/workflows/`, `scripts/pulumi_*`, `run_pulumi_command.py`, `Makefile` | G2.1 → G3.1 → G3.2 → G3.3 → G3.4 → G3.5 → [G5.7] |
  | C-policy | `policy/` | G3.3 (later rule changes only with the story that needs them, in C-program order) |
  | C-program | `pulumi/__main__.py`, `pulumi/app/*`, stack config | G3.1 → G4.1 → G5.1 → G5.2 → G5.3 → G5.4 → G5.5 → G5.6 (step-11 rule switch) → [G5.7 → G5.8] → G4.2 → G6.1 → G6.2 |
  | C-contract | `contracts/` | G3.3 (schema) → G5.1 → [G5.8] → G6.1 |

  Brackets mark the OQ-8 (a)-only stories.

## 5. Validation

| ID | What is verified | Method | Story | Fallback |
| --- | --- | --- | --- | --- |
| V-A1 | REST API → VPC link V2 → internal ALB works in `eu-central-1` | docs (GA-1, GA-2) + live TEST (gate A-T step 2) | G5.3, G5.6 | NLB variant (AD-A4), new plan revision |
| V-A2 | `integration_target` takes the load balancer ARN (not the listener ARN the CloudFormation reference names) | provider source (GR-17) + docs (GA-1) + TEST preview and apply | G5.3 | the listener ARN, if the service rejects the load balancer ARN; recorded |
| V-A3 | The exact caller permissions of `CreateVpcLink` (V2) | simulator matrix in G1.4b + the first TEST apply; CloudTrail read-back by the BI owner | G1.4b, G5.3 | add only the denied action, by a stack amendment |
| V-A4 | API Gateway verifies the ALB certificate against the `uri` host | TEST (gate A-T step 2) | G5.6 | — (a failure is a STOP) |
| V-A5 | `SecurityPolicy_TLS13_1_2_PFS_PQ_2025_09` with `STRICT` on a Regional custom domain through `pulumi-aws` 7.23.0 | provider source (GR-17) + TEST apply | G5.5 | `TLS_1_2`, recorded |
| V-A6 | WAF logging succeeds with the BI pre-created resource policy and no `logs:PutResourcePolicy` | TEST apply | G5.4 | OQ-4 (b) or (c), user decision |
| V-A7 | Which ACM actions support `aws:ResourceTag`, `acm:DomainNames` and `acm:ValidationMethod` (GA-16) | Service Authorization Reference (ACM), per action | G1.4a | user decision (AD-A7), not defaulted |
| V-A8 | Which read actions lack resource-level support (`elasticloadbalancing:Describe*`, `ec2:Describe*`, `logs:DescribeLogGroups`, `logs:GetQueryResults`, `wafv2` list and capacity, `logs:CreateLogDelivery`) | Service Authorization Reference JSON (as the USI plan fetched it, revision 12) | G1.4a, G1.4b | none: an action with resource-level support gets exact resources |
| V-A9 | Access logging works with the scoped CloudWatch role and a KMS log group | TEST (gate A-T step 8) | G1.5, G5.6 | the AWS managed policy, only by user decision |
| V-A10 | The registration shape of G1.1 (a new principal kind in `policy_registry.py` for independently created service roles) is acceptable to the seed | BI owner, G1.1 review | G1.1 | STOP; escalate to the BI owner |
| V-A11 | The API Gateway condition key `apigateway:Request/DisableExecuteApiEndpoint` on `/restapis` creates | docs (GA-7) + simulator | G1.4b | the policy pack alone enforces it |

## 6. Well-Architected mapping

| Pillar | Where |
| --- | --- |
| Security | AD-A1 (OIDC trust, no `pull_request`, in-stack guards), AD-A6 (WAF), AD-A4/AD-A5 (TLS, no execute-api, no data trace), AD-A7 (least privilege, denies), AD-A9 (scoped logging role), AD-A14 (KMS), FR-A08 and PD-11 (no PAT, no App private key, SHA pins). Secret rotation: the plan creates no secret; the only long-lived secret the repository used (the App private key) is dropped (PD-11). |
| Reliability | two AZs (USI subnets), VPC-link probe (FR-A13), RTO PD-6, retained certificate and DNS, replicated state (PD-12) |
| Operational excellence | saved plans, drift, alarms with runbooks, gate campaigns, feature flags (AD-A15) |
| Performance efficiency | Regional endpoint, no cache, latency alarm, NFR-A06 |
| Cost optimization | one web ACL, ≤ 1,500 WCU, no paid groups, PD-5 retention |
| Sustainability | no idle compute added; the gateway is serverless |
