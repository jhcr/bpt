from datetime import datetime, timedelta

from domain.entities.session import CipherSession, Session
from domain.entities.user import User
from domain.value_objects.tokens import JWTClaims


class AuthDomainService:
    """Domain service for authentication business logic"""

    @staticmethod
    def create_user_jwt_claims(
        user: User,
        session: Session,
        issuer: str,
        audience: str,
        ttl_seconds: int,
        jti: str,
        scopes: list[str],
        azp: str = "spa-web",
    ) -> JWTClaims:
        """Create JWT claims for a user"""
        now = int(datetime.utcnow().timestamp())

        return JWTClaims(
            iss=issuer,
            sub=user.id,
            aud=audience,
            exp=now + ttl_seconds,
            iat=now,
            jti=jti,
            auth_time=now,
            azp=azp,
            amr=["pwd"],  # Authentication method reference
            sid=session.sid,
            sidv=session.version,
            roles=["user"],  # Default role
            scope=" ".join(scopes),
            idp="cognito",
            provider_sub=user.provider_sub,
            token_use="access",
            ver=1,
        )

    @staticmethod
    def create_service_jwt_claims(
        sub_spn: str,
        scopes: list[str],
        issuer: str,
        audience: str,
        ttl_seconds: int,
        jti: str,
        actor_sub: str | None = None,
        actor_scope: str | None = None,
        actor_roles: list[str] | None = None,
    ) -> JWTClaims:
        """Create JWT claims for a service token"""
        now = int(datetime.utcnow().timestamp())

        act_claim = None
        if actor_sub:
            act_claim = {"sub": actor_sub}
            if actor_scope:
                act_claim["scope"] = actor_scope
            if actor_roles:
                act_claim["roles"] = actor_roles

        return JWTClaims(
            iss=issuer,
            sub=sub_spn,
            aud=audience,
            exp=now + ttl_seconds,
            iat=now,
            jti=jti,
            amr=["svc"],
            scope=" ".join(scopes),
            token_use="svc",
            act=act_claim,
            ver=1,
        )

    @staticmethod
    def create_session(
        sid: str,
        user: User,
        refresh_token: str,
        ttl_seconds: int,
        device_info: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Session:
        """Create a new user session"""
        now = datetime.utcnow()

        return Session(
            sid=sid,
            user_id=user.id,
            provider_sub=user.provider_sub,
            refresh_token=refresh_token,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
            last_accessed=now,
            version=1,
            device_info=device_info,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    def create_cipher_session(
        sid: str,
        private_key_pem: bytes,
        public_key_jwk: dict,
        ttl_seconds: int = 300,  # 5 minutes
    ) -> CipherSession:
        """Create a cipher session for password encryption"""
        now = datetime.utcnow()

        return CipherSession(
            sid=sid,
            server_private_key_pem=private_key_pem,
            server_public_key_jwk=public_key_jwk,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )

    @staticmethod
    def validate_session(session: Session) -> bool:
        """Validate if session is still valid"""
        if not session:
            return False

        if session.is_expired():
            return False

        return True

    @staticmethod
    def should_refresh_session(session: Session, threshold_seconds: int = 1800) -> bool:
        """Check if session should be refreshed (within threshold of expiry)"""
        if not session or session.is_expired():
            return False

        time_to_expiry = (session.expires_at - datetime.utcnow()).total_seconds()
        return time_to_expiry <= threshold_seconds

    @staticmethod
    def get_default_user_scopes() -> list[str]:
        """Get default scopes for user tokens"""
        return ["user.read", "usersettings.read", "usersettings.write"]

    @staticmethod
    def get_service_scopes(service_name: str) -> list[str]:
        """Get default scopes for service tokens"""
        base_scopes = {
            "bff": [
                "svc.userprofiles.read",
                "svc.usersettings.read",
                "svc.usersettings.write",
            ],
            "userprofiles": ["svc.usersettings.read"],
            "usersettings": ["svc.userprofiles.read"],
        }

        return base_scopes.get(service_name, [f"svc.{service_name}.*"])

    @staticmethod
    def extract_service_name_from_spn(sub_spn: str) -> str:
        """Extract service name from service principal name"""
        if sub_spn.startswith("spn:"):
            return sub_spn[4:]  # Remove "spn:" prefix
        return sub_spn
