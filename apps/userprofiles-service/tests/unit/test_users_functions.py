# Assumptions:
# - Using pytest for testing framework
# - Testing SQL functions via direct database connection
# - Using psycopg3 for PostgreSQL operations

import os
from uuid import uuid4

import pytest
from psycopg import connect


@pytest.fixture
def db_connection():
    """Database connection fixture"""
    dsn = os.environ.get("PG_DSN", "postgresql://postgres:password@localhost:5432/appdb")
    with connect(dsn, autocommit=True) as conn:
        yield conn


class TestUsersFunctions:
    """Test cases for userprofiles.users SQL functions"""

    def test_create_user(self, db_connection):
        """Test create_user function"""
        with db_connection.cursor() as cur:
            # Test data
            user_id = uuid4()
            cognito_sub = f"test-sub-{uuid4()}"
            email = f"test-{uuid4()}@example.com"
            display_name = "Test User"
            avatar_url = "https://example.com/avatar.jpg"
            phone = "+1234567890"

            # Call function
            cur.execute(
                """
                SELECT * FROM userprofiles.create_user(%s, %s, %s, %s, %s, %s)
            """,
                (user_id, cognito_sub, email, display_name, avatar_url, phone),
            )

            result = cur.fetchone()

            # Assertions
            assert result is not None
            assert result[0] == user_id  # id
            assert result[1] == cognito_sub  # cognito_sub
            assert result[2] == email  # email
            assert result[3] == display_name  # display_name
            assert result[4] == avatar_url  # avatar_url
            assert result[5] == phone  # phone
            assert result[6] is True  # is_active
            assert result[7] is not None  # created_at
            assert result[8] is not None  # updated_at

    def test_get_user_by_id(self, db_connection):
        """Test get_user_by_id function"""
        with db_connection.cursor() as cur:
            # Create user first
            user_id = uuid4()
            cognito_sub = f"test-sub-{uuid4()}"
            email = f"test-{uuid4()}@example.com"

            cur.execute(
                """
                SELECT * FROM userprofiles.create_user(%s, %s, %s, NULL, NULL, NULL)
            """,
                (user_id, cognito_sub, email),
            )

            # Get user by ID
            cur.execute("SELECT * FROM userprofiles.get_user_by_id(%s)", (user_id,))
            result = cur.fetchone()

            # Assertions
            assert result is not None
            assert result[0] == user_id
            assert result[1] == cognito_sub
            assert result[2] == email

    def test_get_user_by_sub(self, db_connection):
        """Test get_user_by_sub function"""
        with db_connection.cursor() as cur:
            # Create user first
            user_id = uuid4()
            cognito_sub = f"test-sub-{uuid4()}"
            email = f"test-{uuid4()}@example.com"

            cur.execute(
                """
                SELECT * FROM userprofiles.create_user(%s, %s, %s, NULL, NULL, NULL)
            """,
                (user_id, cognito_sub, email),
            )

            # Get user by sub
            cur.execute("SELECT * FROM userprofiles.get_user_by_sub(%s)", (cognito_sub,))
            result = cur.fetchone()

            # Assertions
            assert result is not None
            assert result[0] == user_id
            assert result[1] == cognito_sub

    def test_update_user(self, db_connection):
        """Test update_user function"""
        with db_connection.cursor() as cur:
            # Create user first
            user_id = uuid4()
            cognito_sub = f"test-sub-{uuid4()}"
            email = f"test-{uuid4()}@example.com"

            cur.execute(
                """
                SELECT * FROM userprofiles.create_user(%s, %s, %s, NULL, NULL, NULL)
            """,
                (user_id, cognito_sub, email),
            )

            # Update user
            new_email = f"updated-{uuid4()}@example.com"
            new_display_name = "Updated Name"

            cur.execute(
                """
                SELECT * FROM userprofiles.update_user(%s, %s, %s, NULL, NULL, NULL)
            """,
                (user_id, new_email, new_display_name),
            )

            result = cur.fetchone()

            # Assertions
            assert result is not None
            assert result[0] == user_id
            assert result[2] == new_email
            assert result[3] == new_display_name

    def test_delete_user(self, db_connection):
        """Test delete_user function"""
        with db_connection.cursor() as cur:
            # Create user first
            user_id = uuid4()
            cognito_sub = f"test-sub-{uuid4()}"
            email = f"test-{uuid4()}@example.com"

            cur.execute(
                """
                SELECT * FROM userprofiles.create_user(%s, %s, %s, NULL, NULL, NULL)
            """,
                (user_id, cognito_sub, email),
            )

            # Delete user - now returns full user record
            cur.execute("SELECT * FROM userprofiles.delete_user(%s)", (user_id,))
            deleted_user = cur.fetchone()

            # Should return the deleted user record
            assert deleted_user is not None
            assert deleted_user[0] == user_id  # id
            assert deleted_user[1] == cognito_sub  # cognito_sub
            assert deleted_user[2] == email  # email

            # Verify user is gone
            cur.execute("SELECT * FROM userprofiles.get_user_by_id(%s)", (user_id,))
            result = cur.fetchone()
            assert result is None or all(field is None for field in result)

    def test_soft_delete_user(self, db_connection):
        """Test soft_delete_user function"""
        with db_connection.cursor() as cur:
            # Create user first
            user_id = uuid4()
            cognito_sub = f"test-sub-{uuid4()}"
            email = f"test-{uuid4()}@example.com"

            cur.execute(
                """
                SELECT * FROM userprofiles.create_user(%s, %s, %s, NULL, NULL, NULL)
            """,
                (user_id, cognito_sub, email),
            )

            # Soft delete user - now returns full user record
            cur.execute("SELECT * FROM userprofiles.soft_delete_user(%s)", (user_id,))
            soft_deleted_user = cur.fetchone()

            # Should return the soft-deleted user record
            assert soft_deleted_user is not None
            assert soft_deleted_user[0] == user_id  # id
            assert soft_deleted_user[1] == cognito_sub  # cognito_sub
            assert soft_deleted_user[2] == email  # email
            assert soft_deleted_user[6] is False  # is_active should be False

            # Verify user is inactive when retrieved again
            cur.execute("SELECT * FROM userprofiles.get_user_by_id(%s)", (user_id,))
            result = cur.fetchone()
            assert result is not None
            assert result[6] is False  # is_active should be False
