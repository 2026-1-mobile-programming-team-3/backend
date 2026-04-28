"""initial

Revision ID: b71ae8903b66
Revises:
Create Date: 2026-04-28 14:24:15.472434

"""
from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b71ae8903b66'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table('calendar_events',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=False),
    sa.Column('event_time', sa.Time(), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.CheckConstraint('end_date >= start_date', name='ck_calendar_events_dates'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_calendar_events_dates', 'calendar_events', ['start_date', 'end_date'], unique=False)

    op.create_table('users',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('nickname', sa.String(length=20), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('role', sa.Enum('USER', 'VOLUNTEER', 'ADMIN', name='user_role'), server_default=sa.text("'USER'"), nullable=False),
    sa.Column('profile_image_url', sa.Text(), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('nickname')
    )
    op.create_index('idx_users_role_active', 'users', ['role'], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))

    op.create_table('devices',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('fcm_token', sa.Text(), nullable=False),
    sa.Column('device_name', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('fcm_token')
    )
    op.create_index('idx_devices_user_id', 'devices', ['user_id'], unique=False)

    op.create_table('notifications',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('category', sa.Enum('VOLUNTEER', 'MATCH', 'REVIEW', 'NEWS', 'POLICY', 'SYSTEM', name='notification_category'), nullable=False),
    sa.Column('title', sa.String(length=100), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('link', sa.String(length=255), nullable=True),
    sa.Column('read_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_notifications_user_created', 'notifications', ['user_id', sa.text('created_at DESC')], unique=False)
    op.create_index('idx_notifications_user_unread', 'notifications', ['user_id', sa.text('created_at DESC')], unique=False, postgresql_where=sa.text('read_at IS NULL'))

    op.create_table('pets',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('species', sa.Enum('DOG', 'CAT', 'OTHER', name='pet_species'), nullable=False),
    sa.Column('breed', sa.String(length=50), nullable=True),
    sa.Column('age', sa.SmallInteger(), nullable=True),
    sa.Column('weight_kg', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('is_neutered', sa.Boolean(), server_default=sa.text('FALSE'), nullable=False),
    sa.Column('photo_url', sa.Text(), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_pets_user_id', 'pets', ['user_id'], unique=False)

    op.create_table('reports',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('reporter_id', sa.BigInteger(), nullable=False),
    sa.Column('target_user_id', sa.BigInteger(), nullable=True),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['target_user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('reporter_id', 'target_user_id')
    )
    op.create_index('idx_reports_target_created', 'reports', ['target_user_id', sa.text('created_at DESC')], unique=False)

    op.create_table('stores',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('address', sa.String(length=255), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('category', sa.Enum('CAFE', 'RESTAURANT', 'PARK', name='store_category'), nullable=False),
    sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, spatial_index=False, from_text='ST_GeogFromText', name='geography', nullable=False), nullable=False),
    sa.Column('operating_hours', sa.String(length=100), nullable=True),
    sa.Column('photo_urls', sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
    sa.Column('is_pet_allowed', sa.Boolean(), server_default=sa.text('TRUE'), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='store_status'), server_default=sa.text("'PENDING'"), nullable=False),
    sa.Column('created_by', sa.BigInteger(), nullable=True),
    sa.Column('rating_avg', sa.Numeric(precision=3, scale=2), server_default=sa.text('0'), nullable=False),
    sa.Column('rating_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    # idx_stores_location은 spatial_index=False이므로 자동 생성되지 않음
    op.create_index('idx_stores_location_gist', 'stores', ['location'], unique=False, postgresql_using='gist')
    op.create_index('idx_stores_status_category', 'stores', ['status', 'category'], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))

    op.create_table('volunteer_requests',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='volunteer_request_status'), server_default=sa.text("'PENDING'"), nullable=False),
    sa.Column('processed_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_volunteer_requests_status_created', 'volunteer_requests', ['status', sa.text('created_at DESC')], unique=False)
    op.create_index('uniq_volunteer_requests_one_pending', 'volunteer_requests', ['user_id'], unique=True, postgresql_where=sa.text("status = 'PENDING'"))

    op.create_table('matches',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('author_id', sa.BigInteger(), nullable=False),
    sa.Column('pet_id', sa.BigInteger(), nullable=True),
    sa.Column('title', sa.String(length=100), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, spatial_index=False, from_text='ST_GeogFromText', name='geography', nullable=False), nullable=False),
    sa.Column('address', sa.String(length=255), nullable=True),
    sa.Column('desired_date', sa.Date(), nullable=True),
    sa.Column('status', sa.Enum('WAITING', 'MATCHING', 'PROGRESS', 'DONE', name='match_status'), server_default=sa.text("'WAITING'"), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['pet_id'], ['pets.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    # idx_matches_location은 spatial_index=False이므로 자동 생성되지 않음
    op.create_index('idx_matches_location_gist', 'matches', ['location'], unique=False, postgresql_using='gist')
    op.create_index('idx_matches_status_created', 'matches', ['status', sa.text('created_at DESC')], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))

    op.create_table('refresh_tokens',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('device_id', sa.BigInteger(), nullable=True),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_index('idx_refresh_tokens_user_active', 'refresh_tokens', ['user_id'], unique=False, postgresql_where=sa.text('revoked_at IS NULL'))

    op.create_table('store_reviews',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('store_id', sa.BigInteger(), nullable=False),
    sa.Column('author_id', sa.BigInteger(), nullable=True),
    sa.Column('rating', sa.SmallInteger(), nullable=False),
    sa.Column('is_pet_allowed', sa.Boolean(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.CheckConstraint('rating BETWEEN 1 AND 5', name='ck_store_reviews_rating'),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['store_id'], ['stores.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('store_id', 'author_id')
    )
    op.create_index('idx_store_reviews_store_created', 'store_reviews', ['store_id', sa.text('created_at DESC')], unique=False)

    op.create_table('match_applications',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('match_id', sa.BigInteger(), nullable=False),
    sa.Column('applicant_id', sa.BigInteger(), nullable=False),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('status', sa.Enum('PENDING', 'ACCEPTED', 'REJECTED', name='application_status'), server_default=sa.text("'PENDING'"), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.ForeignKeyConstraint(['applicant_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('match_id', 'applicant_id')
    )
    op.create_index('idx_match_applications_match_status', 'match_applications', ['match_id', 'status'], unique=False)
    op.create_index('uniq_match_applications_one_accepted', 'match_applications', ['match_id'], unique=True, postgresql_where=sa.text("status = 'ACCEPTED'"))

    op.create_table('match_reviews',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('match_id', sa.BigInteger(), nullable=False),
    sa.Column('reviewer_id', sa.BigInteger(), nullable=True),
    sa.Column('reviewee_id', sa.BigInteger(), nullable=True),
    sa.Column('rating', sa.SmallInteger(), nullable=False),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('proof_image_urls', sa.ARRAY(sa.Text()), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.CheckConstraint('rating BETWEEN 1 AND 5', name='ck_match_reviews_rating'),
    sa.CheckConstraint('reviewer_id IS NULL OR reviewee_id IS NULL OR reviewer_id <> reviewee_id', name='ck_match_reviews_different_users'),
    sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['reviewee_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('match_id', 'reviewer_id')
    )
    op.create_index('idx_match_reviews_reviewee', 'match_reviews', ['reviewee_id', sa.text('created_at DESC')], unique=False)

    op.create_table('chat_messages',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('application_id', sa.BigInteger(), nullable=False),
    sa.Column('sender_id', sa.BigInteger(), nullable=True),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('read_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    sa.ForeignKeyConstraint(['application_id'], ['match_applications.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_chat_messages_application_created', 'chat_messages', ['application_id', sa.text('created_at DESC')], unique=False)


def downgrade() -> None:
    op.drop_index('idx_chat_messages_application_created', table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_index('idx_match_reviews_reviewee', table_name='match_reviews')
    op.drop_table('match_reviews')
    op.drop_index('uniq_match_applications_one_accepted', table_name='match_applications', postgresql_where=sa.text("status = 'ACCEPTED'"))
    op.drop_index('idx_match_applications_match_status', table_name='match_applications')
    op.drop_table('match_applications')
    op.drop_index('idx_store_reviews_store_created', table_name='store_reviews')
    op.drop_table('store_reviews')
    op.drop_index('idx_refresh_tokens_user_active', table_name='refresh_tokens', postgresql_where=sa.text('revoked_at IS NULL'))
    op.drop_table('refresh_tokens')
    op.drop_index('idx_matches_status_created', table_name='matches', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_index('idx_matches_location_gist', table_name='matches', postgresql_using='gist')
    op.drop_table('matches')
    op.drop_index('uniq_volunteer_requests_one_pending', table_name='volunteer_requests', postgresql_where=sa.text("status = 'PENDING'"))
    op.drop_index('idx_volunteer_requests_status_created', table_name='volunteer_requests')
    op.drop_table('volunteer_requests')
    op.drop_index('idx_stores_status_category', table_name='stores', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_index('idx_stores_location_gist', table_name='stores', postgresql_using='gist')
    op.drop_table('stores')
    op.drop_index('idx_reports_target_created', table_name='reports')
    op.drop_table('reports')
    op.drop_index('idx_pets_user_id', table_name='pets')
    op.drop_table('pets')
    op.drop_index('idx_notifications_user_unread', table_name='notifications', postgresql_where=sa.text('read_at IS NULL'))
    op.drop_index('idx_notifications_user_created', table_name='notifications')
    op.drop_table('notifications')
    op.drop_index('idx_devices_user_id', table_name='devices')
    op.drop_table('devices')
    op.drop_index('idx_users_role_active', table_name='users', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_table('users')
    op.drop_index('idx_calendar_events_dates', table_name='calendar_events')
    op.drop_table('calendar_events')
