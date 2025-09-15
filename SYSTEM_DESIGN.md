SYSTEM_DESIGN.md
Cloud-Native App — Istio@EKS · API Gateway · Sidecar-First · Clean Architecture · Custom Auth UI · First-Party JWT · Service Tokens

This document is code-generation ready (for Claude Code or similar). It includes: end-to-end architecture; strict Clean Architecture foldering; full repo scaffold; concrete code examples (PostgreSQL SQL functions & migration runner, DynamoDB schema & migrations, Auth session-cipher, JWT signer & JWKS, BFF adapters, Istio policies, service-token flow); docker-compose; Terraform/Helm structure; CI; milestones & prompts.

1. Executive Summary
   Web: React + Vite SPA (TypeScript, Redux Toolkit + RTK Query). Custom signup/login UI (no Amplify UI).

Mobile: React Native (Expo).

Backends (Python 3.11+/3.12, FastAPI, Pydantic only for API I/O):

BFF (public API, composition only; no DB).

Auth Service (Cognito broker for password/SRP + Google/Facebook; first-party JWT for users; service tokens for svc↔svc; server-side refresh in Redis; session cipher).

UserProfiles Service (Aurora PostgreSQL; CRUD via SQL functions returning rows/boolean).

UserSettings Service (DynamoDB; Terraform-managed; data migration runner + registry).

Events Service (Kafka/MSK; DLQ & replay).

Infra: EKS + Istio (mTLS STRICT, retries, circuit breaking), API Gateway ingress, ElastiCache (Redis), MSK, Cognito, RDS/Aurora, DynamoDB. Optional GCP BigQuery + GCS via WIF (no Vertex AI).

Sidecars: Envoy (mesh), OpenTelemetry Collector (traces/metrics), Fluent Bit (logs).

Observability: structlog (JSON), OpenTelemetry → X-Ray, AMP/AMG, CloudWatch.

2. High-Level Architecture
   Clients
   ├─ Web: React + Vite SPA (custom auth UI, session cipher)
   └─ Mobile: React Native

API Gateway (HTTP API: WAF/throttle)
→ NLB → Istio Ingress Gateway → istiod (control plane)
│
┌───────────────────────┼─────────────────────────────┐
│ │ │
BFF Auth Svc UserProfiles Svc
(/api/v1/user*, /auth/*) (Cognito broker) (Aurora PostgreSQL)
│ │ │
│ │ │
└───────► UserSettings Svc (DynamoDB) ◄───────────────┘
│
Kafka (MSK)
│
(optional) GCP BigQuery + GCS via WIF
North-south: API Gateway → Istio Ingress.

East-west: Envoy sidecars (Istio policies).

SDK access to DynamoDB/MSK/RDS with tuned timeouts; no homegrown retries (mesh handles).

3. Security & Auth Overview
   Custom Auth UI (username/password + Google/Facebook via Cognito Hosted UI; iframe typically blocked → use popup/redirect).

Password login: UI uses session cipher (ECDH + HKDF + AES-GCM) to protect password; server decrypts in-memory only; prefer Cognito SRP; fallback USER_PASSWORD_AUTH over TLS.

End-user tokens: Auth Service mints our JWT (ES256). UI receives access token only (short-lived); refresh token lives server-side in Redis keyed by sid httpOnly cookie.

Service tokens: Auth Service mints short-lived service JWTs (client-credentials) for BFF→microservice and other svc↔svc calls (see §6).

Istio validates our JWT (RequestAuthentication/JWKS) and enforces claims/scopes with AuthorizationPolicy.

Mesh security: mTLS STRICT. Secrets via AWS Secrets Manager + ExternalSecrets.

4. Ingress & Service Mesh (Istio on EKS)
   API Gateway (HTTP API) → NLB → Istio Ingress Gateway (SDS via cert-manager).

Routing/Resilience:

VirtualService routes /api/\* → BFF (2s timeout; 3× retries at 600ms).

DestinationRule for BFF→services: outlier detection, CB, ISTIO_MUTUAL TLS.

PeerAuthentication STRICT; RequestAuthentication for JWT; AuthorizationPolicy for scope/claims.

Gateway & routing (example):

apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata: { name: app-ingress-gw, namespace: app-prod }
spec:
selector: { istio: ingressgateway }
servers: - port: { number: 80, name: http, protocol: HTTP }
hosts: ["api.example.com"]
tls: { httpsRedirect: true } - port: { number: 443, name: https, protocol: HTTPS }
hosts: ["api.example.com"]
tls: { mode: SIMPLE, credentialName: app-example-com-tls }

---

apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata: { name: bff-vs, namespace: app-prod }
spec:
hosts: ["api.example.com"]
gateways: ["app-ingress-gw"]
http: - match: [{ uri: { prefix: "/api/" } }]
timeout: 2s
retries: { attempts: 3, perTryTimeout: 600ms, retryOn: "5xx,connect-failure,refused-stream" }
route: - destination: { host: bff.app-prod.svc.cluster.local, port: { number: 8080 } }

---

apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata: { name: default-strict, namespace: app-prod }
spec: { mtls: { mode: STRICT } } 5) End-User JWT (First-Party Access Token)
Header

{ "alg": "ES256", "typ": "JWT", "kid": "2025-09-rotA" }
Payload (claims)

Required: iss, sub (internal UUID), aud="cloud-app", iat, exp≤15m, jti.

Recommended: auth_time, azp (e.g., "spa-web"), amr (e.g., ["pwd"]).

App: sid, sidv, roles (minimal), scope (space-delimited), idp ("cognito"|"google"|"facebook"), tenant_id?, ver, cognito_sub?.

Example

{
"iss":"https://auth.example.com","sub":"3f88...c012","aud":"cloud-app",
"iat":1757419200,"exp":1757420100,"jti":"a2c3...9f21",
"auth_time":1757419200,"azp":"spa-web","amr":["pwd"],
"sid":"1b0b...3444","sidv":3,"roles":["user"],
"scope":"user.read usersettings.read usersettings.write","idp":"cognito","ver":1
}
Istio validation & guard

apiVersion: security.istio.io/v1beta1
kind: RequestAuthentication
metadata: { name: app-jwt, namespace: app-prod }
spec:
jwtRules:

- issuer: "https://auth.example.com"
  jwksUri: "https://auth.example.com/auth/.well-known/jwks.json"
  forwardOriginalToken: true

---

apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata: { name: bff-user-read, namespace: app-prod }
spec:
selector: { matchLabels: { app: bff } }
rules:

- to: [{ operation: { paths: ["/api/v1/user"] } }]
  when:
  - key: request.auth.claims[scope]
    values: ["*user.read*"]

6. Service Tokens — BFF→Microservice & Svc↔Svc Protection (Preferred)
   Rule: all BFF → microservice calls use a short-lived service token (aud=internal, token_use=svc).
   The BFF includes actor context (on-behalf-of end user) via the act claim.

Service token payload

iss: https://auth.example.com

sub: service principal, e.g., spn:bff

aud: "internal"

token_use: "svc"; amr: ["svc"]

scope: e.g., "svc.userprofiles.read svc.usersettings.write"

act: {"sub":"<user-uuid>","scope":"user.read usersettings.write","roles":["user"]}

TTL: 5 min; ES256 signed; JWKS same as user tokens.

Issuance (Auth Service)

POST /auth/svc/token
Body: { client_id, client_secret, sub_spn, scope, actor_sub?, actor_scope?, actor_roles? }
Resp: { access_token, expires_in, token_type }
Minting (example)

# apps/auth-service/application/use_cases/svc_token.py

import time, uuid
from ...infrastructure.adapters.crypto.es256_signer import ES256Signer

def mint_svc_token(signer: ES256Signer, sub_spn: str, scopes: str,
actor_sub: str|None=None, actor_scope: str|None=None, actor_roles: list[str]|None=None,
ttl=300):
extra = {"token_use":"svc","amr":["svc"],"jti":str(uuid.uuid4())}
if actor_sub:
extra["act"] = {"sub": actor_sub}
if actor_scope: extra["act"]["scope"] = actor_scope
if actor_roles: extra["act"]["roles"] = actor_roles
return signer.mint(sub=sub_spn, sid="svc", scopes=scopes, extra=extra, ttl=ttl)
Istio guard for internal routes (tight to BFF)

apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata: { name: svc-only-internal, namespace: app-prod }
spec:
selector: { matchLabels: { app: userprofiles } }
rules:

- to: [{ operation: { paths: ["/internal/*"] } }]
  when: - key: request.auth.claims[token_use]
  values: ["svc"] - key: request.auth.claims[aud]
  values: ["internal"] - key: request.auth.claims[sub]
  values: ["spn:bff"]
  Callee middleware (extract actor)

# apps/<svc>/presentation/middleware/auth_svc.py

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import jwt

class Principal:
def **init**(self, svc_sub:str, actor_sub:str|None, actor_scope:str|None, roles:list[str]|None):
self.svc_sub=svc_sub; self.actor_sub=actor_sub; self.actor_scope=actor_scope; self.roles=roles or []

class RequireServiceToken(BaseHTTPMiddleware):
def **init**(self, app, jwks_client, audience="internal"):
super().**init**(app); self.jwks=jwks_client; self.aud=audience

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/internal/"):
            return await call_next(request)
        auth = request.headers.get("authorization","")
        if not auth.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="missing bearer")
        token = auth.split(" ",1)[1]
        try:
            claims = jwt.decode(token, self.jwks, algorithms=["ES256"], audience=self.aud,
                                options={"require":["exp","aud","sub"]})
            if claims.get("token_use") != "svc":
                raise HTTPException(status_code=403, detail="token_use must be svc")
            act = claims.get("act",{}) if isinstance(claims.get("act"), dict) else {}
            request.state.principal = Principal(
                svc_sub=claims["sub"],
                actor_sub=act.get("sub"),
                actor_scope=act.get("scope"),
                roles=act.get("roles") or []
            )
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="invalid token")
        return await call_next(request)

Shared client (BFF or other callers)

# shared/python/src/bpt/shared/auth/service_tokens.py

import time, httpx, threading

class ServiceTokenClient:
def **init**(self, auth_base, client_id, client_secret, sub_spn, scope):
self.auth_base, self.client_id, self.client_secret = auth_base, client_id, client_secret
self.sub_spn, self.scope = sub_spn, scope
self.\_lock = threading.Lock(); self.\_tok=None; self.\_exp=0

    def get(self, actor_sub: str|None=None, actor_scope: str|None=None, actor_roles: list[str]|None=None):
        # naive: per-scope/actor cache omitted for brevity. Extend if needed.
        with self._lock:
            if self._tok and time.time() < self._exp - 60:
                return self._tok
            payload = {
              "client_id": self.client_id, "client_secret": self.client_secret,
              "sub_spn": self.sub_spn, "scope": self.scope,
              "actor_sub": actor_sub, "actor_scope": actor_scope, "actor_roles": actor_roles,
            }
            r = httpx.post(f"{self.auth_base}/auth/svc/token", json=payload, timeout=2.0)
            r.raise_for_status()
            j = r.json(); self._tok = j["access_token"]; self._exp = time.time()+j["expires_in"]
            return self._tok

7. Clean Architecture — Rules
   Layering: presentation → application → domain; infrastructure depends inward only.

Pydantic only in presentation.

No retries in service code; timeouts required on all I/O.

8. Project Structure (Repo) — Expanded Scaffold
   cloud-app/
   README.md
   Makefile
   .gitignore
   .editorconfig
   .env.example
   .pre-commit-config.yaml
   .importlinter
   docker-compose.dev.yml
   scripts/{dev_bootstrap.sh, check_sidecar_injection.sh, smoke_tests.sh}
   .github/workflows/{ci.yml, deploy.yml, security.yml}
   docs/ADRs/ ; RUNBOOKS/{auth-service.md,bff.md,userprofiles.md,usersettings.md,events.md}
   apps/
   shared/bpt-shared/src/
   auth/{**init**.py, jwt_verify.py, principals.py, service_tokens.py}
   config/{**init**.py, env.py}
   logging/{**init**.py, setup.py}
   telemetry/{**init**.py, otel.py}
   http/{**init**.py, client.py}
   bff/
   pyproject.toml Dockerfile
   domain/{entities,value_objects,services,errors.py}
   application/{ports,use_cases,mappers}
   infrastructure/{adapters,config,telemetry}
   presentation/{app.py, api/, middleware/, schema/}
   tests/{unit,integration,e2e}
   auth-service/
   pyproject.toml Dockerfile
   domain/{...} application/{ports,use_cases(inc. svc_token.py),mappers} infrastructure/{adapters(crypto,redis,cognito,jwks),config,telemetry}
   presentation/{app.py, api/(auth_routes.py,jwks_routes.py,svc_token_routes.py), middleware/, schema/}
   tests/{unit,integration,e2e}
   userprofiles-service/
   pyproject.toml Dockerfile
   db/{init,tables,sql,functions,procedures}
   scripts/run_pg_migrations.py
   domain/{...} application/{...} infrastructure/{adapters(pg,msk),config,telemetry}
   presentation/{app.py, api/(users_routes.py,internal_routes.py,webhook_routes.py), middleware/(auth_svc.py,errors.py), schema/}
   tests/{unit,integration,e2e}
   usersettings-service/
   pyproject.toml Dockerfile
   db/dynamodb/migrations/
   scripts/run_dynamodb_migrations.py
   domain/{...} application/{...} infrastructure/{adapters(ddb,msk),config,telemetry}
   presentation/{app.py, api/(settings_routes.py,internal_routes.py), middleware/(auth_svc.py,errors.py), schema/}
   tests/{unit,integration,e2e}
   events-service/
   pyproject.toml Dockerfile
   domain/{...} application/{ports(consumer,producer,sink_port),use_cases,replay} infrastructure/{adapters(msk,bq,gcs),config,telemetry}
   presentation/{app.py, api/admin_routes.py, middleware/, schema/}
   tests/{unit,integration,e2e}
   frontend/
   web/
   package.json vite.config.ts tsconfig.json
   src/{main.tsx, App.tsx}
   src/pages/{Login.tsx, User.tsx, Settings.tsx}
   src/components/{AuthForm.tsx, SessionCipherProvider.tsx}
   src/store/{index.ts, authSlice.ts, api.ts}
   src/lib/{sessionCipher.ts, http.ts}
   src/types/{tokens.ts}
   public/index.html
   mobile/ (Expo: similar structure)
   infrastructure/
   terraform/
   environments/{dev,prod}/{main.tf,providers.tf,variables.tf,backend.tf,outputs.tf,values-<env>.yaml}
   modules/{networking,eks,rds,dynamodb,redis,kafka,cognito,api-gateway,observability,gcp-wif}
   kubernetes/
   base/{namespaces.yaml, externalsecrets/secrets.yaml}
   istio/{gateway.yaml, virtualservice-bff.yaml, destinationrule-userprofiles.yaml, peerauthentication.yaml, requestauthentication.yaml, authorizationpolicy-user.yaml}
   helm-charts/{bff,auth-service,userprofiles-service,usersettings-service,events-service}/...
   monitoring/{otel-collector-daemonset.yaml, fluent-bit-daemonset.yaml, xray-daemon.yaml, grafana-dashboards/\*.json}
   Makefile (starter)

.PHONY: up down install fmt lint test precommit
up: ; docker compose -f docker-compose.dev.yml up -d
down: ; docker compose -f docker-compose.dev.yml down -v
install:
\tpipx run pre-commit install
fmt: ; ruff format . && isort .
lint: ; ruff check . && import-linter lint
test: ; pytest -q
precommit: ; pre-commit run --all-files
.pre-commit-config.yaml (starter)

repos:

- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.6.9
  hooks: [ { id: ruff }, { id: ruff-format } ]
- repo: https://github.com/pycqa/isort
  rev: 5.13.2
  hooks: [ { id: isort } ]
- repo: https://github.com/psf/black
  rev: 24.8.0
  hooks: [ { id: black } ]
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.10.0
  hooks: [ { id: mypy } ]
- repo: https://github.com/seddonym/import-linter
  rev: v2.0
  hooks: [ { id: import-linter } ]
  .importlinter (enforce layers)

[importlinter]
root_package = apps

[contract:bff_layers]
type = layers
name = BFF layers
layers =
apps.bff.presentation
apps.bff.application
apps.bff.domain
containers =
apps.bff.infrastructure
ignore_imports =
apps.bff.presentation -> apps.bff.infrastructure
Service Dockerfile (example)

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir uv
COPY pyproject.toml .
RUN uv pip install -r pyproject.toml --system
COPY . .
EXPOSE 8080
CMD ["uvicorn","apps.bff.presentation.app:app","--host","0.0.0.0","--port","8080"] 9) BFF — Public & Auth APIs (no DB)
Endpoints

Data: GET /api/v1/user, GET/PUT /api/v1/user/settings.

Auth proxy: /auth/session, /auth/signup, /auth/confirm-signup, /auth/resend-confirmation, /auth/login, /auth/forgot-password, /auth/confirm-forgot-password, /auth/social/providers, /auth/callback, /auth/token, /auth/refresh, /auth/logout.

Route (example)

# apps/bff/presentation/api/user_routes.py

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..middleware.auth_jwt import get_principal
from ...application.use_cases.get_user import GetUser
router = APIRouter()

class UserResp(BaseModel):
id: str; email: str; display_name: str|None; avatar_url: str|None; settings: dict

@router.get("/api/v1/user", response_model=UserResp)
async def get_user(principal=Depends(get_principal), uc: GetUser = Depends()):
data = await uc.execute(principal=principal)
return UserResp(\*\*data)
BFF adapter (uses service token + actor)

# apps/bff/infrastructure/adapters/http_userprofiles_client.py

import httpx
from framework.auth.service_tokens import ServiceTokenClient
from ...application.ports.userprofiles_port import UserProfilesPort

class HttpUserProfilesClient(UserProfilesPort):
def **init**(self, base_url: str, svc_tok: ServiceTokenClient):
self.\_base = base_url.rstrip("/"); self.\_svc_tok = svc_tok

    async def find_by_sub(self, actor_sub: str, actor_scope: str|None):
        token = self._svc_tok.get(actor_sub=actor_sub, actor_scope=actor_scope)
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=2.0) as c:
            r = await c.get(f"{self._base}/internal/users/by-sub/{actor_sub}", headers=headers)
            r.raise_for_status(); return r.json()

10. Auth Service — Session Cipher, Cognito Broker, JWT, JWKS, Service Tokens
    /auth/session returns ECDH pubkey & sid; UI encrypts password with WebCrypto; server decrypts using stored peer pubkey:

# apps/auth-service/infrastructure/adapters/crypto/ecdh_kms.py

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def decrypt_envelope(priv_key: ec.EllipticCurvePrivateKey, peer_pub: ec.EllipticCurvePublicKey,
sid: str, nonce: bytes, ciphertext: bytes) -> str:
shared = priv_key.exchange(ec.ECDH(), peer_pub)
hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=sid.encode(), info=b"pwd-login-v1")
key = hkdf.derive(shared)
return AESGCM(key).decrypt(nonce, ciphertext, sid.encode()).decode()
JWT sign + JWKS

# apps/auth-service/infrastructure/adapters/crypto/es256_signer.py

from cryptography.hazmat.primitives.asymmetric import ec, serialization
import jwt, time

class ES256Signer:
def **init**(self, kid: str, pem: bytes, iss: str, aud: str):
self.kid, self.iss, self.aud = kid, iss, aud
self.\_key = serialization.load_pem_private_key(pem, password=None)

    def mint(self, sub: str, sid: str, scopes: str, extra: dict, ttl=900):
        now = int(time.time())
        payload = {"iss":self.iss,"aud":self.aud,"sub":sub,"iat":now,"exp":now+ttl,"jti":extra.get("jti","")}
        payload |= {"sid":sid,"scope":scopes,"ver":1} | {k:v for k,v in extra.items() if k not in {"jti"}}
        return jwt.encode(payload, self._key, algorithm="ES256", headers={"kid": self.kid})

Service token route (with actor)

# apps/auth-service/presentation/api/svc_token_routes.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os
from ...application.use_cases.svc_token import mint_svc_token
from ...infrastructure.adapters.crypto.es256_signer import ES256Signer
router = APIRouter()

class SvcTokenReq(BaseModel):
client_id: str; client_secret: str; scope: str; sub_spn: str
actor_sub: str|None=None; actor_scope: str|None=None; actor_roles: list[str]|None=None
class SvcTokenResp(BaseModel): access_token: str; token_type: str = "Bearer"; expires_in: int

def validate*client(req: SvcTokenReq) -> bool: # Replace with Secrets Manager per client_id
name = req.sub_spn.split(":")[1].replace("-","*")
return (os.getenv(f"SVC*CLIENT_ID*{name}") == req.client*id
and os.getenv(f"SVC_CLIENT_SECRET*{name}") == req.client_secret)

@router.post("/auth/svc/token", response_model=SvcTokenResp)
async def svc_token(req: SvcTokenReq, signer: ES256Signer = Depends()):
if not validate_client(req): raise HTTPException(status_code=401, detail="invalid client")
ttl = int(os.getenv("SVC_TOKEN_TTL_SECONDS","300"))
tok = mint_svc_token(signer, req.sub_spn, req.scope, req.actor_sub, req.actor_scope, req.actor_roles, ttl=ttl)
return SvcTokenResp(access_token=tok, expires_in=ttl) 11) UserProfiles Service (PostgreSQL; SQL Functions; Migrations)
Init (extensions, schema, grants)

-- apps/userprofiles-service/db/init/000_roles_and_schema.sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "citext";
CREATE SCHEMA IF NOT EXISTS userprofiles AUTHORIZATION CURRENT_USER;

CREATE TABLE IF NOT EXISTS userprofiles.schema_migrations (
filename text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now()
);
Tables

-- apps/userprofiles-service/db/tables/users.sql
CREATE TABLE IF NOT EXISTS userprofiles.users (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
cognito_sub TEXT UNIQUE NOT NULL,
email CITEXT UNIQUE NOT NULL,
display_name TEXT,
avatar_url TEXT,
phone TEXT,
is_active BOOLEAN NOT NULL DEFAULT true,
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON userprofiles.users(email);
CREATE INDEX IF NOT EXISTS idx_users_cognito_sub ON userprofiles.users(cognito_sub);
CREATE INDEX IF NOT EXISTS idx_users_active ON userprofiles.users(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_users_created_at ON userprofiles.users(created_at);

-- Trigger to automatically update updated_at
CREATE OR REPLACE FUNCTION userprofiles.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
NEW.updated_at = NOW();
RETURN NEW;
END;

$$
language 'plpgsql';

DROP TRIGGER IF EXISTS update_users_updated_at ON userprofiles.users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON userprofiles.users
    FOR EACH ROW
    EXECUTE FUNCTION userprofiles.update_updated_at_column();
Versioned SQL (tracked)

-- apps/userprofiles-service/db/sql/20250909-0001_add_user_phone.sql
ALTER TABLE userprofiles.users ADD COLUMN IF NOT EXISTS phone TEXT;
Functions (CRUD: C/R/U return TABLE rows; D returns boolean)

-- apps/userprofiles-service/db/functions/users.sql
-- Create user (returns full row)
CREATE FUNCTION userprofiles.create_user(
    p_id UUID,
    p_cognito_sub TEXT,
    p_email CITEXT,
    p_display_name TEXT,
    p_avatar_url TEXT,
    p_phone TEXT
) RETURNS TABLE(id uuid,
    cognito_sub text,
    email citext,
    display_name text,
    avatar_url text,
    phone text,
    is_active boolean,
    created_at timestamp,
    updated_at timestamp)
LANGUAGE sql AS
$$

    INSERT INTO userprofiles.users (
        id, cognito_sub, email, display_name, avatar_url, phone,
        is_active, created_at, updated_at
    )
    VALUES (
        COALESCE(p_id, gen_random_uuid()),
        p_cognito_sub,
        p_email,
        p_display_name,
        p_avatar_url,
        p_phone,
        TRUE,
        NOW(),
        NOW()
    )
    RETURNING id, cognito_sub, email, display_name, avatar_url, phone,
        is_active, created_at, updated_at;

$$
;

-- Get user by ID (single-statement SQL function)
CREATE FUNCTION userprofiles.get_user_by_id(p_id UUID)
RETURNS TABLE(id uuid,
    cognito_sub text,
    email citext,
    display_name text,
    avatar_url text,
    phone text,
    is_active boolean,
    created_at timestamp,
    updated_at timestamp)
LANGUAGE sql AS
$$

    SELECT
        id, cognito_sub, email, display_name, avatar_url, phone,
        is_active, created_at, updated_at
    FROM userprofiles.users
    WHERE id = p_id;

$$
;

-- Get user by cognito_sub
CREATE FUNCTION userprofiles.get_user_by_sub(p_cognito_sub TEXT)
RETURNS TABLE(id uuid,
    cognito_sub text,
    email citext,
    display_name text,
    avatar_url text,
    phone text,
    is_active boolean,
    created_at timestamp,
    updated_at timestamp)
LANGUAGE sql AS
$$

    SELECT
        id, cognito_sub, email, display_name, avatar_url, phone,
        is_active, created_at, updated_at
    FROM userprofiles.users
    WHERE cognito_sub = p_cognito_sub;

$$
;

-- Get user by email
CREATE FUNCTION userprofiles.get_user_by_email(p_email CITEXT)
RETURNS TABLE(id uuid,
    cognito_sub text,
    email citext,
    display_name text,
    avatar_url text,
    phone text,
    is_active boolean,
    created_at timestamp,
    updated_at timestamp)
LANGUAGE sql AS
$$

    SELECT
        id, cognito_sub, email, display_name, avatar_url, phone,
        is_active, created_at, updated_at
    FROM userprofiles.users
    WHERE email = p_email;

$$
;

-- Update user (returns full row)
CREATE FUNCTION userprofiles.update_user(
    p_id UUID,
    p_email CITEXT DEFAULT NULL,
    p_display_name TEXT DEFAULT NULL,
    p_avatar_url TEXT DEFAULT NULL,
    p_phone TEXT DEFAULT NULL,
    p_is_active BOOLEAN DEFAULT NULL
)
RETURNS TABLE(id uuid,
    cognito_sub text,
    email citext,
    display_name text,
    avatar_url text,
    phone text,
    is_active boolean,
    created_at timestamp,
    updated_at timestamp)
LANGUAGE sql AS
$$

    UPDATE userprofiles.users
    SET
        email = COALESCE(p_email, email),
        display_name = COALESCE(p_display_name, display_name),
        avatar_url = COALESCE(p_avatar_url, avatar_url),
        phone = COALESCE(p_phone, phone),
        is_active = COALESCE(p_is_active, is_active),
        updated_at = NOW()
    WHERE id = p_id
    RETURNING id, cognito_sub, email, display_name, avatar_url, phone,
    is_active, created_at, updated_at;

$$
;

-- Delete user (returns boolean)
CREATE FUNCTION userprofiles.delete_user(p_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql AS
$$

BEGIN
DELETE FROM userprofiles.users WHERE id = p_id;
RETURN FOUND;
END;

$$
;

-- Soft delete user (returns boolean)
CREATE FUNCTION userprofiles.soft_delete_user(p_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql AS
$$

BEGIN
UPDATE userprofiles.users
SET is_active = FALSE, updated_at = NOW()
WHERE id = p_id AND is_active = TRUE;
RETURN FOUND;
END;

$$
;
Procedures (maintenance)

-- apps/userprofiles-service/db/procedures/rebuild_indexes.sql
DO $$ BEGIN RAISE NOTICE 'Rebuild indexes placeholder'; END $$;
Migration runner (order: init → tables → sql → functions → procedures)

# apps/userprofiles-service/scripts/run_pg_migrations.py

import os, glob, psycopg
ORDER = ["init","tables","sql","functions","procedures"]
TRACK = "userprofiles.schema_migrations"
ROOT = os.path.join(os.path.dirname(**file**), "..", "db")

def apply(cur, path): cur.execute(open(path,"r",encoding="utf8").read())
def ensure_track(cur):
cur.execute(f"CREATE TABLE IF NOT EXISTS {TRACK}(filename text PRIMARY KEY, applied_at timestamptz DEFAULT now())")
def already(cur, fname):
cur.execute(f"SELECT 1 FROM {TRACK} WHERE filename=%s", (fname,)); return cur.fetchone() is not None

def run():
dsn = os.environ["PG_DSN"]
with psycopg.connect(dsn, autocommit=True) as conn, conn.cursor() as cur:
ensure_track(cur)
for stage in ORDER:
for path in sorted(glob.glob(f"{ROOT}/{stage}/\*_/_.sql", recursive=True)):
fname = os.path.basename(path)
if stage=="sql":
if already(cur, fname): continue
apply(cur, path); cur.execute(f"INSERT INTO {TRACK}(filename) VALUES(%s)", (fname,))
else:
apply(cur, path)

if **name** == "**main**": run()
Repository (psycopg3 + pool)

# apps/userprofiles-service/infrastructure/adapters/pg_user_repository.py

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from ...application.ports.user_repository import UserRepository
from ...domain.entities.user import User

class PgUserRepository(UserRepository):
def **init**(self, dsn: str):
self.pool = ConnectionPool(dsn, min_size=1, max_size=10)

    def create(self, sub, email, display_name=None, avatar_url=None) -> User:
        q = "SELECT * FROM userprofiles.create_user(%s,%s,%s,%s,%s)"
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(q, (None, sub, email, display_name, avatar_url))
            return self._map(cur.fetchone())

    def find_by_sub(self, sub: str) -> User|None:
        q = "SELECT * FROM userprofiles.find_user_by_sub(%s)"
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(q, (sub,)); row = cur.fetchone()
            return self._map(row) if row else None

    def _map(self, r: dict) -> User:
        return User(id=r["id"], sub=r["cognito_sub"], email=r["email"],
                    display_name=r["display_name"], avatar_url=r["avatar_url"],
                    is_active=r["is_active"], created_at=r["created_at"], updated_at=r["updated_at"])

12. UserSettings Service (DynamoDB; OCC; Migrations)
    Terraform

resource "aws*dynamodb_table" "user_settings" {
name = "user_settings*${var.env}"
billing_mode = "PAY_PER_REQUEST"
hash_key = "user_id"
range_key = "category"
attribute { name = "user_id" type = "S" }
attribute { name = "category" type = "S" }
ttl { attribute_name = "ttl_epoch_s" enabled = true }
point_in_time_recovery { enabled = true }
server_side_encryption { enabled = true }
}

# Also create a small table for migration registry: usersettings*migrations*${var.env}

Repository (OCC)

# apps/usersettings-service/infrastructure/adapters/ddb_settings_repository.py

import boto3, datetime
from botocore.exceptions import ClientError

class DdbSettingsRepository:
def **init**(self, table_name: str, region="us-east-1", endpoint_url=None):
self.t = boto3.resource("dynamodb", region_name=region, endpoint_url=endpoint_url).Table(table_name)

    def get(self, user_id: str, category: str):
        return self.t.get_item(Key={"user_id":user_id,"category":category}, ConsistentRead=True).get("Item")

    def put_with_occ(self, user_id: str, category: str, data: dict, expected_version: int|None):
        now = datetime.datetime.utcnow().isoformat()
        expr = "SET #d=:d, #u=:u, #v = if_not_exists(#v, :zero) + :one"
        cond = "attribute_not_exists(#v)" if expected_version is None else "#v = :ev"
        try:
            r = self.t.update_item(
                Key={"user_id":user_id,"category":category},
                UpdateExpression=expr,
                ConditionExpression=cond,
                ExpressionAttributeNames={"#d":"data","#u":"updated_at","#v":"version"},
                ExpressionAttributeValues={":d":data,":u":now,":one":1,":zero":0,":ev":expected_version or 0},
                ReturnValues="ALL_NEW")
            return r["Attributes"]
        except ClientError as e:
            if e.response["Error"]["Code"]=="ConditionalCheckFailedException":
                return None
            raise

Migrations runner + registry

# apps/usersettings-service/scripts/run_dynamodb_migrations.py

import os, boto3, importlib.util, pathlib, time
REG_TABLE = os.getenv("USERSETTINGS_MIGRATIONS_TABLE","usersettings_migrations_dev")
ddb = boto3.resource("dynamodb"); reg = ddb.Table(REG_TABLE)

def applied(name): return reg.get_item(Key={"id":name}).get("Item") is not None
def mark(name): reg.put_item(Item={"id":name, "applied_at": int(time.time())})

def run_py(path):
spec = importlib.util.spec_from_file_location("m", path)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); m.up(ddb)

def main():
root = pathlib.Path("apps/usersettings-service/db/dynamodb/migrations")
for f in sorted(root.glob("\*.py")):
name = f.name
if applied(name): continue
run_py(str(f)); mark(name)

if **name** == "**main**": main()
Migration example

# apps/usersettings-service/db/dynamodb/migrations/20250909-0001_add_default_language.py

def up(ddb):
t = ddb.Table("user_settings_dev")
scan = t.scan(ProjectionExpression="user_id, #c", ExpressionAttributeNames={"#c":"category"})
for item in scan.get("Items", []):
t.update_item(
Key={"user_id": item["user_id"], "category": item["category"]},
UpdateExpression="SET #d.#lang = if_not_exists(#d.#lang, :en)",
ExpressionAttributeNames={"#d":"data","#lang":"language"},
ExpressionAttributeValues={":en":"en"}) 13) Events (Kafka/MSK)
Envelope

{
"event_id":"uuid","event_type":"userprofiles.created.v1","user_id":"uuid",
"timestamp":"iso8601","payload":{...},
"metadata":{"source":"userprofiles","correlation_id":"...","trace_id":"..."}
}
Producer

# apps/userprofiles-service/infrastructure/adapters/msk_event_producer.py

from confluent_kafka import Producer
import json
class MskProducer:
def **init**(self, conf): self.p = Producer(conf)
def publish(self, topic: str, key: str, value: dict):
self.p.produce(topic, key=key, value=json.dumps(value).encode("utf-8"))
self.p.flush(1) 14) Frontends (React + Vite; RN/Expo) — Redux Toolkit / RTK Query
State/data: Redux Toolkit; RTK Query with baseQuery adding Authorization: Bearer <access_token>.

Token: keep in memory only (not localStorage).

Password login flow: GET /auth/session → WebCrypto ECDH/HKDF/AES-GCM → POST /auth/login → receive OTC → POST /auth/token → access token in memory.

Social: Hosted UI popup/redirect → /#otc=... → /auth/token.

RTK baseQuery

import { fetchBaseQuery } from '@reduxjs/toolkit/query/react';
export const baseQuery = fetchBaseQuery({
baseUrl: '/api',
prepareHeaders: (h, { getState }) => {
const token = (getState() as any).auth.accessToken;
if (token) h.set('Authorization', `Bearer ${token}`);
return h;
},
});
Session cipher (browser)

// frontend/web/src/lib/sessionCipher.ts (excerpt)
export async function encryptPassword({ serverJwk, sid, password }: {serverJwk:JsonWebKey, sid:string, password:string}) {
const clientKey = await crypto.subtle.generateKey({name:"ECDH", namedCurve:"P-256"}, true, ["deriveBits"]);
const serverKey = await crypto.subtle.importKey("jwk", serverJwk, {name:"ECDH", namedCurve:"P-256"}, true, []);
const secretBits = await crypto.subtle.deriveBits({name:"ECDH", public: serverKey}, clientKey.privateKey, 256);
const hkdfKey = await crypto.subtle.importKey("raw", secretBits, "HKDF", false, ["deriveKey"]);
const aeadKey = await crypto.subtle.deriveKey({name:"HKDF", hash:"SHA-256", salt: new TextEncoder().encode(sid), info:new TextEncoder().encode("pwd-login-v1")},
hkdfKey, {name:"AES-GCM", length:256}, false, ["encrypt"]);
const iv = crypto.getRandomValues(new Uint8Array(12));
const ct = await crypto.subtle.encrypt({name:"AES-GCM", iv, additionalData:new TextEncoder().encode(sid)},
aeadKey, new TextEncoder().encode(password));
return { nonce: b64url(iv), password_enc: b64url(new Uint8Array(ct)) };
} 15) Observability & Logging
Traces: OTLP → OTel Collector → X-Ray (Envoy spans included).

Metrics: OTel → AMP; dashboards in AMG.

Logs: app + Envoy → Fluent Bit → CloudWatch Logs.

App logging: structlog JSON (include trace_id, correlation_id).

16. Local Dev (docker-compose)
    version: '3.8'
    services:
    postgres:
    image: postgres:15-alpine
    environment: { POSTGRES_DB: appdb, POSTGRES_USER: postgres, POSTGRES_PASSWORD: password }
    ports: ["5432:5432"]
    volumes: [ "postgres_data:/var/lib/postgresql/data" ]

redis:
image: redis:7-alpine
ports: ["6379:6379"]
command: redis-server --appendonly yes
volumes: [ "redis_data:/data" ]

kafka:
image: bitnami/kafka:3.6
ports: ["9092:9092"]
environment:
KAFKA_ENABLE_KRAFT: "yes"
KAFKA_CFG_PROCESS_ROLES: broker,controller
KAFKA_CFG_CONTROLLER_LISTENER_NAMES: CONTROLLER
KAFKA_CFG_LISTENERS: PLAINTEXT://:9092,CONTROLLER://:9093
KAFKA_CFG_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
volumes: [ "kafka_data:/bitnami/kafka" ]

localstack:
image: localstack/localstack:3.0
ports: ["4566:4566"]
environment: { SERVICES: dynamodb,s3,secretsmanager, DEBUG: 1 }
volumes: - "/var/run/docker.sock:/var/run/docker.sock" - "localstack_data:/var/lib/localstack"

volumes: { postgres_data: {}, redis_data: {}, kafka_data: {}, localstack_data: {} } 17) Environment Variables (Example)
ENV=development
DEBUG=true

# DB

PG_DSN=postgresql://postgres:password@localhost:5432/appdb
REDIS_URL=redis://localhost:6379/0

# AWS

AWS_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
COGNITO_CLIENT_ID=your_cognito_client_id
COGNITO_CLIENT_SECRET=your_cognito_client_secret

# DDB

DYNAMODB_TABLE_USER_SETTINGS=user_settings_dev
DYNAMODB_ENDPOINT_URL=http://localhost:4566
USERSETTINGS_MIGRATIONS_TABLE=usersettings_migrations_dev

# Kafka

KAFKA_BROKERS=localhost:9092

# Optional GCP

GCP_PROJECT_ID=your-gcp-project
GCP_LOCATION=us-central1

# Service URLs

BFF_API_URL=http://localhost:8080
USERPROFILES_URL=http://localhost:8081
USERSETTINGS_URL=http://localhost:8082
AUTHSVC_URL=http://localhost:8083

# OTEL

OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=cloud-app

# JWKS

JWKS_URL=https://auth.example.com/auth/.well-known/jwks.json

# Service tokens (Auth /auth/svc/token)

SVC_TOKEN_AUDIENCE=internal
SVC_TOKEN_TTL_SECONDS=300
SVC_CLIENT_ID_bff=bff-client-id
SVC_CLIENT_SECRET_bff=bff-client-secret
SVC_CLIENT_ID_userprofiles=up-client-id
SVC_CLIENT_SECRET_userprofiles=up-client-secret
SVC_CLIENT_ID_usersettings=us-client-id
SVC_CLIENT_SECRET_usersettings=us-client-secret

18) Milestones & Implementation Status

✅ M1 — Foundation & Shared Libs:
   - ✅ Repo scaffold with Clean Architecture structure
   - ✅ Makefile for development workflows
   - ✅ Docker-compose with all infrastructure services
   - ✅ Shared libs (logging, telemetry, JWT verify, service token client)
   - ✅ Health endpoints structure

✅ M2 — Core Services (Implemented):
   - ✅ Auth Service: ECDH session cipher, ES256 JWT signer, Redis session repository, service tokens with actor claims
   - ✅ BFF: HTTP adapters for microservice communication, service token integration, user composition use cases

   - ✅ UserProfiles: PostgreSQL schema with triggers, migration runner, SQL functions (CRUD), unit tests
   - ✅ UserSettings: DynamoDB repository with OCC, migration runner & registry, unit tests
   - ✅ Events Service: MSK producer adapter structure

🚧 M3 — Events (Partial):
   - ✅ Producer adapter implemented
   - ⏳ Consumer/DLQ/replay (structure ready for implementation)

✅ M4 — Frontend Foundation:
   - ✅ Session cipher implementation (WebCrypto ECDH + HKDF + AES-GCM)
   - ⏳ Complete React+Vite SPA UI (structure exists)
   - ⏳ RTK Query integration
   - ⏳ React Native/Expo app

⏳ M5 — Infrastructure & Deploy:
   - ⏳ Terraform modules (EKS, API Gateway, WAF, etc.)
   - ⏳ Helm charts for K8s deployment
   - ⏳ Migration jobs for K8s

⏳ M6 — Service Mesh & Security:
   - ⏳ Istio configuration (mTLS, JWT validation, AuthorizationPolicy)
   - ⏳ Observability stack (OpenTelemetry, Fluent Bit)
   - ⏳ SLOs and alerting

**Current Status: M1 & M2 Complete, M3-M4 Foundations Ready**

19. Acceptance Criteria
    Auth: custom UI can signup/confirm/login/reset (session cipher); social login; UI gets first-party JWT; server-side refresh via sid cookie.

BFF→Microservices: uses service tokens with act claim for on-behalf-of auth; microservices expose /internal/ only; Istio + middleware enforced.

UserProfiles: CRUD via SQL functions; migration order init → tables → sql → functions → procedures; only db/sql/\* tracked.

UserSettings: DDB table (TTL, Streams, SSE, PITR); migration runner & registry working.

Events: emitted/consumed; DLQ + replay.

Obs: traces in X-Ray, metrics in AMP/AMG, logs in CloudWatch.

Security: mTLS STRICT in mesh; WAF/throttle at edge; secrets managed; IRSA least-priv.

20. Clean Architecture — Folder Structure & Rules (Per Service)
    apps/<service>/
    domain/
    entities/ # dataclasses (pure)
    value_objects/ # Email, UserId...
    services/ # domain logic
    errors.py
    application/
    use_cases/ # orchestrators (no I/O)
    ports/ # interfaces (repos, gateways)
    mappers/ # DTO↔domain
    infrastructure/
    adapters/ # DB/DDB/Kafka/HTTP/Redis impls of ports
    config/ # settings & DI
    telemetry/ # logging/tracing init
    presentation/
    api/ # FastAPI routers (Pydantic DTOs)
    middleware/ # auth, errors, correlation
    schema/ # OpenAPI helpers
    tests/{unit,integration,e2e}
    pyproject.toml
    Dockerfile
    Import boundaries

[importlinter]
root_package = apps
[contract:bff_layers]
type = layers
name = BFF layers
layers =
apps.bff.presentation
apps.bff.application
apps.bff.domain
containers =
apps.bff.infrastructure
ignore_imports =
apps.bff.presentation -> apps.bff.infrastructure
App factory template

# apps/<service>/presentation/app.py

from fastapi import FastAPI
from ..infrastructure.config.container import Container
from ..presentation.api import routers
from ..presentation.middleware import errors
from ..infrastructure.telemetry.tracing import init_tracing
from ..infrastructure.telemetry.logging import init_logging

def create_app() -> FastAPI:
init_logging(); init_tracing(service_name="<service>")
c = Container()
app = FastAPI(title="<Service>", version="1.0.0")
app.include_router(routers.router)
errors.install(app)
app.state.container = c
return app

app = create_app() 21) Claude Code — Step-by-Step Prompts
Phase 1 — Foundation

Scaffold directory tree per §8. Add shared libs (framework.logging.setup, framework.telemetry.otel, framework.auth.jwt_verify, framework.auth.service_tokens). Create docker-compose.dev.yml, Makefile, .pre-commit-config.yaml, .importlinter, GitHub Actions ci.yml. Add /health, /health/ready, /health/live to each service.

Phase 2 — Core Services

Auth Service: /auth/session (ECDH); password (SRP preferred) + social; store refresh in Redis; mint end-user JWT; expose JWKS; POST /auth/svc/token (client-credentials + act support).
BFF: /api/v1/user*; no DB; compose via ports to UserProfiles/UserSettings; use ServiceTokenClient with sub_spn="spn:bff" and scopes; attach actor (principal.sub, scopes) when fetching token.
UserProfiles: migration runner & SQL functions; psycopg3 repo.
UserSettings: DDB repo with OCC; Terraform table; migrations runner & registry.
Wire RequireServiceToken middleware and Istio AuthZ on each microservice’s /internal/*.

Phase 3 — Events

MSK producer/consumer; DLQ + replay; schema validation; tests.

Phase 4 — Frontends

React+Vite SPA: session cipher; custom login/signup; RTK baseQuery; user + settings pages. RN/Expo parity.

Phase 5 — Infra & Deploy

Terraform (EKS, API GW + NLB, WAF, Cognito, Aurora, DDB, MSK, Redis, ExternalSecrets, AMP/AMG, X-Ray, WIF). Helm charts (Deployment/Service/HPA/SA/IRSA/ConfigMaps + Istio Gateway/VS/DR/PeerAuth/RequestAuth/AuthZ). K8s Jobs for PG & DDB migrations.

Phase 6 — Mesh, SLOs & Security

mTLS STRICT; JWT/JWKS; AuthZ for scopes and token_use=svc + aud=internal + sub=spn:bff on /internal/\*. OTel & Fluent Bit; SLOs; perf & security scans.

22. Microservice Protection — Service Tokens (Consolidated)
    Mandatory for BFF→microservice calls.

Include actor in act claim for on-behalf-of authorization.

Istio AuthorizationPolicy + middleware (RequireServiceToken) enforce internal routes.

Rotate client credentials via Secrets Manager; tokens expire quickly (5 min).
$$
