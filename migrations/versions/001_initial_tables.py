"""Create user management tables

Revision ID: 001
Revises: 
Create Date: 2025-01-23 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user management tables"""
    
    # 1. Create users table
    op.create_table('users',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('email_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reset_token', sa.String(255), nullable=True),
        sa.Column('reset_token_expires', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('account_locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('account_locked', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('provider', sa.String(50), nullable=False, default='email'),
        sa.Column('provider_id', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, default='active'),
        sa.Column('subscription_tier', sa.String(50), nullable=False, default='free'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('user_id'),
        sa.UniqueConstraint('email'),
        sa.CheckConstraint("provider IN ('email', 'google', 'apple')", name='ck_users_provider'),
        sa.CheckConstraint("status IN ('active', 'inactive', 'suspended')", name='ck_users_status'),
        sa.CheckConstraint("subscription_tier IN ('free', 'premium_monthly', 'premium_yearly')", name='ck_users_subscription_tier'),
        sa.CheckConstraint('failed_login_attempts >= 0', name='ck_users_failed_attempts'),
    )
    
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_user_id', 'users', ['user_id'])
    op.create_index('ix_users_status', 'users', ['status'])
    op.create_index('ix_users_subscription_tier', 'users', ['subscription_tier'])
    
    # 2. Create profiles table
    op.create_table('profiles',
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=True),
        sa.Column('profile_photo', sa.String(500), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('timezone', sa.String(100), nullable=True),
        sa.Column('language', sa.String(10), nullable=False, default='en'),
        sa.Column('theme', sa.String(20), nullable=False, default='auto'),
        sa.Column('experience_level', sa.String(50), nullable=False, default='beginner'),
        sa.Column('interests', postgresql.JSON(), nullable=False, default=[]),
        sa.Column('visibility', sa.String(20), nullable=False, default='public'),
        sa.Column('notification_enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('notification_preferences', postgresql.JSON(), nullable=False, default={}),
        sa.Column('followers_count', sa.Integer(), nullable=False, default=0),
        sa.Column('following_count', sa.Integer(), nullable=False, default=0),
        sa.Column('posts_count', sa.Integer(), nullable=False, default=0),
        sa.Column('activity_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('profile_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id'),
        sa.CheckConstraint("theme IN ('light', 'dark', 'auto')", name='ck_profiles_theme'),
        sa.CheckConstraint("experience_level IN ('beginner', 'intermediate', 'advanced')", name='ck_profiles_experience_level'),
        sa.CheckConstraint("visibility IN ('public', 'friends', 'private')", name='ck_profiles_visibility'),
        sa.CheckConstraint('followers_count >= 0', name='ck_profiles_followers_count'),
        sa.CheckConstraint('following_count >= 0', name='ck_profiles_following_count'),
    )
    
    op.create_index('ix_profiles_user_id', 'profiles', ['user_id'])
    op.create_index('ix_profiles_display_name', 'profiles', ['display_name'])
    op.create_index('ix_profiles_location', 'profiles', ['location'])
    
    # 3. Create subscriptions table
    op.create_table('subscriptions',
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_type', sa.String(50), nullable=False, default='free'),
        sa.Column('status', sa.String(50), nullable=False, default='active'),
        sa.Column('trial_active', sa.Boolean(), nullable=False, default=False),
        sa.Column('trial_start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('subscription_start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('subscription_end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('payment_method', sa.String(50), nullable=True),
        sa.Column('auto_renew', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('subscription_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id'),
        sa.CheckConstraint("plan_type IN ('free', 'premium_monthly', 'premium_yearly')", name='ck_subscriptions_plan_type'),
        sa.CheckConstraint("status IN ('active', 'inactive', 'cancelled', 'expired')", name='ck_subscriptions_status'),
    )
    
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'])
    op.create_index('ix_subscriptions_plan_type', 'subscriptions', ['plan_type'])


def downgrade() -> None:
    """Drop user management tables"""
    op.drop_table('subscriptions')
    op.drop_table('profiles')
    op.drop_table('users')