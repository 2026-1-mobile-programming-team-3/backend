"""seed stores

Revision ID: c1a2b3d4e5f6
Revises: 28b4d318511b
Create Date: 2026-05-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c1a2b3d4e5f6'
down_revision: Union[str, None] = '28b4d318511b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SEED_STORE_NAMES = (
    '배곧생명공원',
    '옥구공원',
    '갯골생태공원',
    '배곧 댕댕카페',
    '정왕 펫프렌들리',
    '대야동 라떼하우스',
    '시흥시청 카페',
)


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO stores (
            name, address, phone, category, location,
            operating_hours, photo_urls, is_pet_allowed,
            status, rating_avg, rating_count
        ) VALUES
        (
            '배곧생명공원', '경기도 시흥시 배곧동 207', NULL, 'PARK',
            ST_SetSRID(ST_MakePoint(126.7281, 37.3752), 4326)::geography,
            '24시간', ARRAY[]::text[], TRUE,
            'APPROVED', 0, 0
        ),
        (
            '옥구공원', '경기도 시흥시 정왕동 1907-1', NULL, 'PARK',
            ST_SetSRID(ST_MakePoint(126.7322, 37.3451), 4326)::geography,
            '05:00-22:00', ARRAY[]::text[], TRUE,
            'APPROVED', 0, 0
        ),
        (
            '갯골생태공원', '경기도 시흥시 장곡동 724-10', NULL, 'PARK',
            ST_SetSRID(ST_MakePoint(126.7898, 37.4008), 4326)::geography,
            '24시간', ARRAY[]::text[], TRUE,
            'APPROVED', 0, 0
        ),
        (
            '배곧 댕댕카페', '경기도 시흥시 배곧동 188-3', NULL, 'CAFE',
            ST_SetSRID(ST_MakePoint(126.7295, 37.3768), 4326)::geography,
            '10:00-22:00', ARRAY[]::text[], TRUE,
            'APPROVED', 0, 0
        ),
        (
            '정왕 펫프렌들리', '경기도 시흥시 정왕동 1822-5', NULL, 'RESTAURANT',
            ST_SetSRID(ST_MakePoint(126.7340, 37.3470), 4326)::geography,
            '11:00-21:00', ARRAY[]::text[], TRUE,
            'APPROVED', 0, 0
        ),
        (
            '대야동 라떼하우스', '경기도 시흥시 대야동 471-2', NULL, 'CAFE',
            ST_SetSRID(ST_MakePoint(126.8005, 37.4115), 4326)::geography,
            '08:00-22:00', ARRAY[]::text[], FALSE,
            'APPROVED', 0, 0
        ),
        (
            '시흥시청 카페', '경기도 시흥시 장현동 300', NULL, 'CAFE',
            ST_SetSRID(ST_MakePoint(126.8030, 37.3795), 4326)::geography,
            '09:00-18:00', ARRAY[]::text[], FALSE,
            'APPROVED', 0, 0
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM stores
        WHERE name IN (
            '배곧생명공원',
            '옥구공원',
            '갯골생태공원',
            '배곧 댕댕카페',
            '정왕 펫프렌들리',
            '대야동 라떼하우스',
            '시흥시청 카페'
        )
        """
    )
