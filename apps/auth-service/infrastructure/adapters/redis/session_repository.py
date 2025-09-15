import json
import os
import pickle
import sys
from datetime import datetime

import redis.asyncio as redis
import structlog

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from application.ports.session_repository import (
    CipherSessionRepository,
    SessionRepository,
)
from domain.entities.session import CipherSession, Session

logger = structlog.get_logger(__name__)


class RedisSessionRepository(SessionRepository):
    """Redis implementation of session repository"""

    def __init__(self, redis_client: redis.Redis, session_prefix: str = "session:"):
        self.redis = redis_client
        self.session_prefix = session_prefix

    def _session_key(self, sid: str) -> str:
        """Get Redis key for session"""
        return f"{self.session_prefix}{sid}"

    def _user_sessions_key(self, user_id: str) -> str:
        """Get Redis key for user's session list"""
        return f"user_sessions:{user_id}"

    async def save_session(self, session: Session) -> None:
        """Save session to Redis"""
        try:
            key = self._session_key(session.sid)
            user_sessions_key = self._user_sessions_key(session.user_id)

            # Serialize session
            session_data = {
                "sid": session.sid,
                "user_id": session.user_id,
                "provider_sub": session.provider_sub,
                "refresh_token": session.refresh_token,
                "created_at": session.created_at.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "last_accessed": session.last_accessed.isoformat(),
                "version": session.version,
                "device_info": session.device_info,
                "ip_address": session.ip_address,
                "user_agent": session.user_agent,
            }

            # Calculate TTL
            ttl_seconds = int((session.expires_at - datetime.utcnow()).total_seconds())
            if ttl_seconds <= 0:
                logger.warning("Session already expired", sid=session.sid)
                return

            # Use pipeline for atomic operations
            async with self.redis.pipeline() as pipe:
                # Save session data
                await pipe.setex(key, ttl_seconds, json.dumps(session_data))

                # Add session to user's session set
                await pipe.sadd(user_sessions_key, session.sid)
                await pipe.expire(user_sessions_key, ttl_seconds)

                await pipe.execute()

            logger.debug("Session saved to Redis", sid=session.sid, ttl=ttl_seconds)

        except Exception as e:
            logger.error("Failed to save session", sid=session.sid, error=str(e))
            raise

    async def get_session(self, sid: str) -> Session | None:
        """Get session from Redis"""
        try:
            key = self._session_key(sid)
            data = await self.redis.get(key)

            if not data:
                return None

            session_data = json.loads(data)

            # Deserialize session
            session = Session(
                sid=session_data["sid"],
                user_id=session_data["user_id"],
                provider_sub=session_data["provider_sub"],
                refresh_token=session_data["refresh_token"],
                created_at=datetime.fromisoformat(session_data["created_at"]),
                expires_at=datetime.fromisoformat(session_data["expires_at"]),
                last_accessed=datetime.fromisoformat(session_data["last_accessed"]),
                version=session_data["version"],
                device_info=session_data.get("device_info"),
                ip_address=session_data.get("ip_address"),
                user_agent=session_data.get("user_agent"),
            )

            logger.debug("Session retrieved from Redis", sid=sid)
            return session

        except Exception as e:
            logger.error("Failed to get session", sid=sid, error=str(e))
            raise

    async def delete_session(self, sid: str) -> bool:
        """Delete session from Redis"""
        try:
            # Get session first to remove from user sessions
            session = await self.get_session(sid)
            if not session:
                return False

            key = self._session_key(sid)
            user_sessions_key = self._user_sessions_key(session.user_id)

            async with self.redis.pipeline() as pipe:
                # Delete session
                await pipe.delete(key)

                # Remove from user's session set
                await pipe.srem(user_sessions_key, sid)

                result = await pipe.execute()

            deleted = result[0] > 0
            logger.debug("Session deleted from Redis", sid=sid, deleted=deleted)
            return deleted

        except Exception as e:
            logger.error("Failed to delete session", sid=sid, error=str(e))
            raise

    async def update_session(self, session: Session) -> None:
        """Update existing session"""
        # For Redis, update is the same as save
        await self.save_session(session)

    async def get_sessions_by_user(self, user_id: str) -> list[Session]:
        """Get all sessions for a user"""
        try:
            user_sessions_key = self._user_sessions_key(user_id)
            session_ids = await self.redis.smembers(user_sessions_key)

            sessions = []
            for sid in session_ids:
                session = await self.get_session(sid.decode() if isinstance(sid, bytes) else sid)
                if session:
                    sessions.append(session)

            logger.debug("User sessions retrieved", user_id=user_id, count=len(sessions))
            return sessions

        except Exception as e:
            logger.error("Failed to get user sessions", user_id=user_id, error=str(e))
            raise

    async def delete_sessions_by_user(self, user_id: str) -> int:
        """Delete all sessions for a user"""
        try:
            sessions = await self.get_sessions_by_user(user_id)
            count = 0

            for session in sessions:
                if await self.delete_session(session.sid):
                    count += 1

            # Clean up user sessions set
            user_sessions_key = self._user_sessions_key(user_id)
            await self.redis.delete(user_sessions_key)

            logger.info("User sessions deleted", user_id=user_id, count=count)
            return count

        except Exception as e:
            logger.error("Failed to delete user sessions", user_id=user_id, error=str(e))
            raise

    async def invalidate_session(self, sid: str) -> bool:
        """Invalidate a session (same as delete for Redis)"""
        return await self.delete_session(sid)

    async def get_sessions_by_provider_sub(self, provider_sub: str) -> list[Session]:
        """Get all sessions for a provider sub"""
        try:
            # Get all session keys that might contain this provider_sub
            pattern = f"{self.session_prefix}*"
            sessions = []

            async for key in self.redis.scan_iter(match=pattern):
                try:
                    data = await self.redis.get(key)
                    if data:
                        session_data = json.loads(data)
                        if session_data.get("provider_sub") == provider_sub:
                            session = Session(
                                sid=session_data["sid"],
                                user_id=session_data["user_id"],
                                provider_sub=session_data["provider_sub"],
                                refresh_token=session_data["refresh_token"],
                                created_at=datetime.fromisoformat(session_data["created_at"]),
                                expires_at=datetime.fromisoformat(session_data["expires_at"]),
                                last_accessed=datetime.fromisoformat(session_data["last_accessed"]),
                                version=session_data["version"],
                                device_info=session_data.get("device_info"),
                                ip_address=session_data.get("ip_address"),
                                user_agent=session_data.get("user_agent"),
                            )
                            sessions.append(session)
                except Exception as e:
                    logger.warning("Failed to parse session during provider_sub lookup", key=key, error=str(e))
                    continue

            logger.debug("Sessions by provider_sub retrieved", provider_sub=provider_sub, count=len(sessions))
            return sessions

        except Exception as e:
            logger.error("Failed to get sessions by provider_sub", provider_sub=provider_sub, error=str(e))
            raise

    async def get_sessions_by_username(self, username: str) -> list[Session]:
        """Get all sessions for a username (assuming username == provider_sub)"""
        # For most cases, username is the same as provider_sub
        return await self.get_sessions_by_provider_sub(username)


class RedisCipherSessionRepository(CipherSessionRepository):
    """Redis implementation of cipher session repository"""

    def __init__(self, redis_client: redis.Redis, cipher_prefix: str = "cipher:"):
        self.redis = redis_client
        self.cipher_prefix = cipher_prefix

    def _cipher_key(self, sid: str) -> str:
        """Get Redis key for cipher session"""
        return f"{self.cipher_prefix}{sid}"

    async def save_cipher_session(self, cipher_session: CipherSession) -> None:
        """Save cipher session to Redis"""
        try:
            key = self._cipher_key(cipher_session.sid)

            # Use pickle for binary data (private key)
            cipher_data = pickle.dumps(
                {
                    "sid": cipher_session.sid,
                    "server_private_key_pem": cipher_session.server_private_key_pem,
                    "server_public_key_jwk": cipher_session.server_public_key_jwk,
                    "created_at": cipher_session.created_at.isoformat(),
                    "expires_at": cipher_session.expires_at.isoformat(),
                }
            )

            # Calculate TTL
            ttl_seconds = int((cipher_session.expires_at - datetime.utcnow()).total_seconds())
            if ttl_seconds <= 0:
                logger.warning("Cipher session already expired", sid=cipher_session.sid)
                return

            await self.redis.setex(key, ttl_seconds, cipher_data)

            logger.debug("Cipher session saved to Redis", sid=cipher_session.sid, ttl=ttl_seconds)

        except Exception as e:
            logger.error("Failed to save cipher session", sid=cipher_session.sid, error=str(e))
            raise

    async def get_cipher_session(self, sid: str) -> CipherSession | None:
        """Get cipher session from Redis"""
        try:
            key = self._cipher_key(sid)
            data = await self.redis.get(key)

            if not data:
                return None

            cipher_data = pickle.loads(data)

            # Deserialize cipher session
            cipher_session = CipherSession(
                sid=cipher_data["sid"],
                server_private_key_pem=cipher_data["server_private_key_pem"],
                server_public_key_jwk=cipher_data["server_public_key_jwk"],
                created_at=datetime.fromisoformat(cipher_data["created_at"]),
                expires_at=datetime.fromisoformat(cipher_data["expires_at"]),
            )

            logger.debug("Cipher session retrieved from Redis", sid=sid)
            return cipher_session

        except Exception as e:
            logger.error("Failed to get cipher session", sid=sid, error=str(e))
            raise

    async def delete_cipher_session(self, sid: str) -> bool:
        """Delete cipher session from Redis"""
        try:
            key = self._cipher_key(sid)
            result = await self.redis.delete(key)

            deleted = result > 0
            logger.debug("Cipher session deleted from Redis", sid=sid, deleted=deleted)
            return deleted

        except Exception as e:
            logger.error("Failed to delete cipher session", sid=sid, error=str(e))
            raise
