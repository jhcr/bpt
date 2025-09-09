import uuid
from typing import Dict, Any
from ..ports.session_repository import CipherSessionRepository
from ..ports.jwt_signer import CipherService
from ...domain.services.auth_service import AuthDomainService
from ...domain.errors import CipherSessionError
import structlog

logger = structlog.get_logger(__name__)


class CreateCipherSessionUseCase:
    """Use case for creating a cipher session for password encryption"""
    
    def __init__(
        self,
        cipher_session_repository: CipherSessionRepository,
        cipher_service: CipherService
    ):
        self.cipher_session_repository = cipher_session_repository
        self.cipher_service = cipher_service
    
    async def execute(self) -> Dict[str, Any]:
        """
        Create a new cipher session
        
        Returns:
            Dictionary with sid and server_public_key_jwk
        """
        try:
            # Generate session ID
            sid = str(uuid.uuid4())
            
            logger.info("Creating cipher session", sid=sid)
            
            # Generate ECDH key pair
            private_key_pem, public_key_jwk = await self.cipher_service.generate_cipher_session(sid)
            
            # Create cipher session domain object
            cipher_session = AuthDomainService.create_cipher_session(
                sid=sid,
                private_key_pem=private_key_pem,
                public_key_jwk=public_key_jwk,
                ttl_seconds=300  # 5 minutes
            )
            
            # Save cipher session
            await self.cipher_session_repository.save_cipher_session(cipher_session)
            
            logger.info("Cipher session created successfully", sid=sid)
            
            return {
                "sid": sid,
                "server_public_key_jwk": public_key_jwk
            }
            
        except Exception as e:
            logger.error("Failed to create cipher session", error=str(e))
            raise CipherSessionError(f"Failed to create cipher session: {e}")