from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field, RootModel


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    roles: List[str]
    permissions: List[str]
    display_name: str | None = None


class ProfileResponse(RootModel[Dict[str, Any]]):
    pass


class ApplicationTotalLoginsCount(BaseModel):
    model_config = ConfigDict(extra="ignore")

    doc_count: int = 0


class ApplicationTotalLoginsUniqueUsers(BaseModel):
    model_config = ConfigDict(extra="ignore")

    value: int = 0


class ApplicationTotalLoginsReport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    failed_logins: ApplicationTotalLoginsCount = Field(default_factory=ApplicationTotalLoginsCount)
    successful_logins: ApplicationTotalLoginsCount = Field(
        default_factory=ApplicationTotalLoginsCount
    )
    unique_users: ApplicationTotalLoginsUniqueUsers = Field(
        default_factory=ApplicationTotalLoginsUniqueUsers
    )


class ApplicationTotalLoginsBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    report: ApplicationTotalLoginsReport = Field(default_factory=ApplicationTotalLoginsReport)


class ApplicationTotalLoginsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    response: ApplicationTotalLoginsBody = Field(default_factory=ApplicationTotalLoginsBody)
    success: bool = False


class ApplicationAuditTrailData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    applicationname: str | None = None
    origin: str | None = None
    realm: str | None = None
    result: str | None = None
    userid: str | None = None
    username: str | None = None


class ApplicationAuditTrailGeoIP(BaseModel):
    model_config = ConfigDict(extra="ignore")

    country_iso_code: str | None = None
    country_name: str | None = None
    region_name: str | None = None


class ApplicationAuditTrailSource(BaseModel):
    model_config = ConfigDict(extra="ignore")

    data: ApplicationAuditTrailData = Field(default_factory=ApplicationAuditTrailData)
    geoip: ApplicationAuditTrailGeoIP = Field(default_factory=ApplicationAuditTrailGeoIP)
    time: int | None = None


class ApplicationAuditTrailHit(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    hit_id: str | None = Field(default=None, alias="_id")
    index: str | None = Field(default=None, alias="_index")
    source: ApplicationAuditTrailSource = Field(
        default_factory=ApplicationAuditTrailSource, alias="_source"
    )
    sort: List[Any] = Field(default_factory=list)


class ApplicationAuditTrailReport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    hits: List[ApplicationAuditTrailHit] = Field(default_factory=list)
    total: int = 0


class ApplicationAuditTrailBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    report: ApplicationAuditTrailReport = Field(default_factory=ApplicationAuditTrailReport)


class ApplicationAuditTrailResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    response: ApplicationAuditTrailBody = Field(default_factory=ApplicationAuditTrailBody)
    success: bool = False


class ClientSecretResponse(RootModel[Dict[str, Any]]):
    pass


class ClientSecretRotatedSecret(BaseModel):
    description: str | None = None
    value: str | None = None
    rotatedAt: int | None = None
    expiredAt: int | None = None


class ClientSecretData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    clientSecret: str | None = None
    rotatedSecrets: List[ClientSecretRotatedSecret] = Field(default_factory=list)


class ClientSecretUpdatePayload(BaseModel):
    deleteRotatedSecrets: bool = False
    description: str = ""
    rotatedSecretExpiredAt: int = 0


class ApplicationEntitlementsResponse(RootModel[Dict[str, Any]]):
    pass


class ApplicationListData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    app_id: str
    app_name: str
    app_type: str
    verify_href: str | None = None

    @property
    def trimmed_id(self) -> str:
        """Return a shorter ID for table display."""
        if len(self.app_id) <= 12:
            return self.app_id
        return f"{self.app_id[:4]}...{self.app_id[-4:]}"


class ApplicationLink(BaseModel):
    href: str


class ApplicationLinks(BaseModel):
    self: ApplicationLink


class ApplicationAttributeMapping(BaseModel):
    sourceId: str
    targetName: str


class ApplicationAuthPolicy(BaseModel):
    grantTypes: List[str]
    id: str
    name: str


class ApplicationCustomization(BaseModel):
    themeId: str | None = None


class ApplicationOwner(BaseModel):
    email: str
    id: str
    name: str
    realm: str
    userName: str
    userType: str
    familyName: str | None = None
    givenName: str | None = None


class ApplicationProperties(BaseModel):
    developers: List[str] = Field(default_factory=list)


class OidcGrantProperties(BaseModel):
    generateDeviceFlowQRCode: str | None = None


class OidcAdditionalConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    allowedClientAssertionVerificationKeys: List[str] = Field(default_factory=list)
    actorTokenRequired: bool | None = None
    actorTokenTypes: List[str] = Field(default_factory=list)
    authorizeRspEncryptionAlg: str | None = None
    authorizeRspEncryptionEnc: str | None = None
    authorizeRspSigningAlg: str | None = None
    certificateBoundAccessTokens: bool | None = None
    clientAuthMethod: str | None = None
    dpopBoundAccessTokens: bool | None = None
    dpopProofSigningAlg: str | None = None
    exchangeForSSOSessionOption: str | None = None
    logoutOption: str | None = None
    logoutRedirectURIs: List[str] = Field(default_factory=list)
    logoutURI: str | None = None
    oidcv3: bool | None = None
    requestObjectMaxExpFromNbf: int | None = None
    requestObjectParametersOnly: bool | None = None
    requestObjectRequireExp: bool | None = None
    requestObjectSigningAlg: str | None = None
    requirePushAuthorize: bool | None = None
    responseModes: List[str] = Field(default_factory=list)
    responseTypes: List[str] = Field(default_factory=list)
    requestUris: List[str] = Field(default_factory=list)
    requestedTokenTypes: List[str] = Field(default_factory=list)
    sessionRequired: bool | None = None
    subjectTokenTypes: List[str] = Field(default_factory=list)
    validateDPoPProofJti: bool | None = None


class OidcGrantTypes(BaseModel):
    model_config = ConfigDict(extra="ignore")

    authorizationCode: str | bool | None = None
    clientCredentials: str | bool | None = None
    deviceFlow: str | bool | None = None
    implicit: str | bool | None = None
    jwtBearer: str | bool | None = None
    policyAuth: str | bool | None = None
    ropc: str | bool | None = None
    tokenExchange: str | bool | None = None


class OidcTokenConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    accessTokenType: str | None = None
    audiences: List[str] = Field(default_factory=list)


class OidcProperties(BaseModel):
    model_config = ConfigDict(extra="ignore")

    accessTokenExpiry: int | None = None
    additionalConfig: OidcAdditionalConfig | None = None
    clientId: str | None = None
    clientSecret: str | None = None
    consentType: str | None = None
    doNotGenerateClientSecret: str | bool | None = None
    generateRefreshToken: str | bool | None = None
    grantTypes: OidcGrantTypes | None = None
    idTokenEncryptAlg: str | None = None
    idTokenEncryptEnc: str | None = None
    idTokenSigningAlg: str | None = None
    redirectUris: List[str] = Field(default_factory=list)
    refreshTokenExpiry: int | None = None
    renewRefreshToken: str | bool | None = None
    renewRefreshTokenExpiry: int | None = None
    sendAllKnownUserAttributes: str | bool | None = None


class OidcProvider(BaseModel):
    model_config = ConfigDict(extra="ignore")

    applicationUrl: str | None = None
    consentAction: str | None = None
    entitlements: List[Any] = Field(default_factory=list)
    grantProperties: OidcGrantProperties | None = None
    properties: OidcProperties | None = None
    requirePkceVerification: str | None = None
    restrictEntitlements: bool | None = None
    scopes: List[Any] = Field(default_factory=list)
    token: OidcTokenConfig | None = None


class SamlProperties(BaseModel):
    model_config = ConfigDict(extra="ignore")

    companyName: str | None = None


class SamlProvider(BaseModel):
    model_config = ConfigDict(extra="ignore")

    justInTimeProvisioning: str | None = None
    properties: SamlProperties | None = None


class SsoProvider(BaseModel):
    model_config = ConfigDict(extra="ignore")

    idpInitiatedSSOSupport: str | None = None
    userOptions: str | None = None


class ApplicationProviders(BaseModel):
    model_config = ConfigDict(extra="ignore")

    oidc: OidcProvider | None = None
    saml: SamlProvider | None = None
    sso: SsoProvider | None = None


class ProvisioningAdoptionPolicy(BaseModel):
    matchingAttributes: List[Any] = Field(default_factory=list)
    remediationPolicy: Dict[str, Any] = Field(default_factory=dict)


class ProvisioningPolicies(BaseModel):
    model_config = ConfigDict(extra="ignore")

    adoptionPolicy: ProvisioningAdoptionPolicy | None = None
    deProvAction: str | None = None
    deProvPolicy: str | None = None
    gracePeriod: int | None = None
    passwordSync: str | None = None
    provPolicy: str | None = None


class ProvisioningConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    attributeMappings: List[Any] = Field(default_factory=list)
    authentication: Dict[str, Any] = Field(default_factory=dict)
    extension: Dict[str, Any] = Field(default_factory=dict)
    generatePassword: bool | None = None
    generatePasswordOnRestore: bool | None = None
    generatedPasswordRecipients: List[Any] = Field(default_factory=list)
    policies: ProvisioningPolicies | None = None
    provisioningState: str | None = None
    reverseAttributeMappings: List[Any] = Field(default_factory=list)
    sendNotifications: bool | None = None


class ApplicationXForce(BaseModel):
    description: str | None = None
    icon: str | None = None
    name: str | None = None


class ApplicationDetailData(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    links: ApplicationLinks = Field(alias="_links")
    adaptiveAuthentication: Dict[str, Any] = Field(default_factory=dict)
    apiAccessClients: List[Any] = Field(default_factory=list)
    applicationRefId: str
    applicationState: bool
    approvalRequired: bool
    attributeMappings: List[ApplicationAttributeMapping] = Field(default_factory=list)
    authPolicy: ApplicationAuthPolicy | None = None
    customIcon: str | None = None
    customization: ApplicationCustomization | None = None
    defaultIcon: str | None = None
    description: str | None = None
    icon: str | None = None
    identitySources: List[str] = Field(default_factory=list)
    name: str
    owners: List[ApplicationOwner] = Field(default_factory=list)
    properties: ApplicationProperties | None = None
    providers: ApplicationProviders | None = None
    provisioning: ProvisioningConfig | None = None
    provisioningMode: str | None = None
    signonState: bool | None = None
    templateId: str | None = None
    type: str | None = None
    visibleOnLaunchpad: bool | None = None
    xforce: ApplicationXForce | None = None


class ApplicationCreation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    visibleOnLaunchpad: bool | None = None
    customization: ApplicationCustomization | None = None
    name: str
    applicationState: bool | None = None
    description: str | None = None
    templateId: str | None = None
    owners: List[str] = Field(default_factory=list)
    provisioning: ProvisioningConfig | None = None
    attributeMappings: List[Any] = Field(default_factory=list)
    providers: ApplicationProviders | None = None
    apiAccessClients: List[Any] = Field(default_factory=list)
