import os
import uuid

import structlog

from domain.entities.user import ServiceToken
from domain.errors import ServiceTokenError, UnauthorizedClientError
from domain.services.auth_service import AuthDomainService
from infrastructure.adapters.crypto.es256_signer import ES256Signer

logger = structlog.get_logger(__name__)


def validate_service_client(client_id: str, client_secret: str, sub_spn: str) -> bool:
    """
    Validate service client credentials
    In production, this should use AWS Secrets Manager
    """
    try:
        # Extract service name from SPN (spn:service-name -> service_name)
        service_name = sub_spn.replace("spn:", "").replace("-", "_")

        expected_client_id = os.getenv(f"SVC_CLIENT_ID_{service_name}")
        expected_client_secret = os.getenv(f"SVC_CLIENT_SECRET_{service_name}")

        return expected_client_id == client_id and expected_client_secret == client_secret

    except Exception as e:
        logger.error("Client validation error", sub_spn=sub_spn, error=str(e))
        return False


def mint_svc_token(
    signer: ES256Signer,
    sub_spn: str,
    scopes: str,
    actor_sub: str | None = None,
    actor_scope: str | None = None,
    actor_roles: list[str] | None = None,
    ttl: int = 300,
) -> str:
    """Mint a service token with optional actor context"""

    try:
        # Create JWT claims
        claims = AuthDomainService.create_service_jwt_claims(
            sub_spn=sub_spn,
            scopes=scopes.split(),
            issuer=signer.iss,
            audience="internal",  # Service tokens always use "internal" audience
            ttl_seconds=ttl,
            jti=str(uuid.uuid4()),
            actor_sub=actor_sub,
            actor_scope=actor_scope,
            actor_roles=actor_roles,
        )

        # Sign the token
        return signer.mint(
            sub=claims.sub,
            sid="svc",
            scopes=claims.scope or "",
            extra=claims.to_dict(),
            ttl=ttl,
        )

    except Exception as e:
        logger.error("Service token minting failed", sub_spn=sub_spn, error=str(e))
        raise ServiceTokenError(f"Failed to mint service token: {e}") from e


class ServiceTokenUseCase:
    """Use case for issuing service tokens"""

    def __init__(self, signer: ES256Signer):
        self.signer = signer

    async def execute(
        self,
        client_id: str,
        client_secret: str,
        sub_spn: str,
        scope: str,
        actor_sub: str | None = None,
        actor_scope: str | None = None,
        actor_roles: list[str] | None = None,
    ) -> ServiceToken:
        """
        Issue a service token

        Args:
            client_id: Service client ID
            client_secret: Service client secret
            sub_spn: Service principal name (e.g., "spn:bff")
            scope: Requested scopes
            actor_sub: Acting user's subject (for on-behalf-of calls)
            actor_scope: Acting user's scopes
            actor_roles: Acting user's roles

        Returns:
            ServiceToken domain entity
        """
        try:
            # Validate client credentials
            if not validate_service_client(client_id, client_secret, sub_spn):
                logger.warning(
                    "Invalid service client credentials",
                    client_id=client_id,
                    sub_spn=sub_spn,
                )
                raise UnauthorizedClientError("Invalid client credentials")

            # Get TTL from environment
            ttl = int(os.getenv("SVC_TOKEN_TTL_SECONDS", "300"))

            logger.info(
                "Minting service token",
                sub_spn=sub_spn,
                scope=scope,
                actor_sub=actor_sub,
            )

            # Mint the token
            access_token = mint_svc_token(
                signer=self.signer,
                sub_spn=sub_spn,
                scopes=scope,
                actor_sub=actor_sub,
                actor_scope=actor_scope,
                actor_roles=actor_roles,
                ttl=ttl,
            )

            logger.info("Service token minted successfully", sub_spn=sub_spn)

            return ServiceToken(
                access_token=access_token,
                token_type="Bearer",
                expires_in=ttl,
                scope=scope,
                sub_spn=sub_spn,
                actor_sub=actor_sub,
            )

        except UnauthorizedClientError:
            raise
        except Exception as e:
            logger.error("Service token issuance failed", sub_spn=sub_spn, error=str(e))
            raise ServiceTokenError(f"Failed to issue service token: {e}") from e
