import struct

from sqladmin import ModelView

from app.models.favorite import StoreFavorite
from app.models.match import ChatMessage, ChatRoom, Match, MatchApplication, MatchReview
from app.models.news import CalendarEvent
from app.models.notification import Notification, NotificationSetting
from app.models.report import Report
from app.models.store import Store, StoreReview
from app.models.user import Device, Pet, RefreshToken, User
from app.models.volunteer import VolunteerRequest


class UserAdmin(ModelView, model=User):
    name = "사용자"
    name_plural = "사용자 목록"
    icon = "fa-solid fa-user"
    column_list = [User.id, User.email, User.nickname, User.role, User.deleted_at, User.created_at]
    column_searchable_list = [User.email, User.nickname]
    column_sortable_list = [User.id, User.created_at]
    form_excluded_columns = ["password_hash", "pets", "devices", "created_at", "updated_at"]


class DeviceAdmin(ModelView, model=Device):
    name = "디바이스"
    name_plural = "디바이스 목록"
    icon = "fa-solid fa-mobile-screen"
    column_list = [Device.id, Device.user_id, Device.device_name, Device.created_at]
    column_sortable_list = [Device.id, Device.created_at]
    form_excluded_columns = ["user", "refresh_tokens", "created_at", "updated_at"]


class RefreshTokenAdmin(ModelView, model=RefreshToken):
    name = "리프레시 토큰"
    name_plural = "리프레시 토큰 목록"
    icon = "fa-solid fa-key"
    column_list = [RefreshToken.id, RefreshToken.user_id, RefreshToken.expires_at, RefreshToken.revoked_at, RefreshToken.created_at]
    column_sortable_list = [RefreshToken.id, RefreshToken.created_at]
    can_create = False
    form_excluded_columns = ["token_hash", "device", "created_at"]


class PetAdmin(ModelView, model=Pet):
    name = "반려동물"
    name_plural = "반려동물 목록"
    icon = "fa-solid fa-paw"
    column_list = [Pet.id, Pet.user_id, Pet.name, Pet.species, Pet.breed, Pet.gender, Pet.is_neutered, Pet.weight_kg, Pet.created_at]
    column_sortable_list = [Pet.id, Pet.created_at]
    form_excluded_columns = ["user", "created_at", "updated_at"]


class StoreFavoriteAdmin(ModelView, model=StoreFavorite):
    name = "즐겨찾기 매장"
    name_plural = "즐겨찾기 매장 목록"
    icon = "fa-solid fa-bookmark"
    column_list = [StoreFavorite.id, StoreFavorite.user_id, StoreFavorite.store_id, StoreFavorite.created_at]
    column_sortable_list = [StoreFavorite.id, StoreFavorite.created_at]
    form_excluded_columns = ["created_at"]


class NotificationSettingAdmin(ModelView, model=NotificationSetting):
    name = "알림 설정"
    name_plural = "알림 설정 목록"
    icon = "fa-solid fa-bell-slash"
    column_list = [NotificationSetting.user_id, NotificationSetting.category, NotificationSetting.push_enabled, NotificationSetting.updated_at]
    column_sortable_list = [NotificationSetting.user_id, NotificationSetting.updated_at]
    form_excluded_columns = ["updated_at"]


class NotificationAdmin(ModelView, model=Notification):
    name = "알림"
    name_plural = "알림 목록"
    icon = "fa-solid fa-bell"
    column_list = [Notification.id, Notification.user_id, Notification.category, Notification.title, Notification.read_at, Notification.created_at]
    column_sortable_list = [Notification.id, Notification.created_at]
    form_excluded_columns = ["created_at"]


class MatchAdmin(ModelView, model=Match):
    name = "매칭"
    name_plural = "매칭 목록"
    icon = "fa-solid fa-handshake"
    column_list = [Match.id, Match.author_id, Match.title, Match.status, Match.desired_date, Match.created_at]
    column_sortable_list = [Match.id, Match.created_at]
    # location is a PostGIS Geography column — not editable via form
    can_create = False
    form_excluded_columns = ["location", "applications", "reviews", "created_at", "updated_at"]


class MatchApplicationAdmin(ModelView, model=MatchApplication):
    name = "매칭 신청"
    name_plural = "매칭 신청 목록"
    icon = "fa-solid fa-file-circle-plus"
    column_list = [MatchApplication.id, MatchApplication.match_id, MatchApplication.applicant_id, MatchApplication.status, MatchApplication.created_at]
    column_sortable_list = [MatchApplication.id, MatchApplication.created_at]
    form_excluded_columns = ["match", "chat_room", "created_at", "updated_at"]


class ChatRoomAdmin(ModelView, model=ChatRoom):
    name = "채팅방"
    name_plural = "채팅방 목록"
    icon = "fa-solid fa-comments"
    column_list = [ChatRoom.id, ChatRoom.application_id, ChatRoom.created_at]
    column_sortable_list = [ChatRoom.id, ChatRoom.created_at]
    form_excluded_columns = ["application", "messages", "created_at"]


class ChatMessageAdmin(ModelView, model=ChatMessage):
    name = "채팅 메시지"
    name_plural = "채팅 메시지 목록"
    icon = "fa-solid fa-message"
    column_list = [ChatMessage.id, ChatMessage.chat_room_id, ChatMessage.sender_id, ChatMessage.read_at, ChatMessage.created_at]
    column_sortable_list = [ChatMessage.id, ChatMessage.created_at]
    form_excluded_columns = ["room", "created_at"]


class MatchReviewAdmin(ModelView, model=MatchReview):
    name = "매칭 후기"
    name_plural = "매칭 후기 목록"
    icon = "fa-solid fa-star"
    column_list = [MatchReview.id, MatchReview.match_id, MatchReview.reviewer_id, MatchReview.reviewee_id, MatchReview.rating, MatchReview.created_at]
    column_sortable_list = [MatchReview.id, MatchReview.created_at]
    # proof_image_urls is a PostgreSQL ARRAY — excluded from form
    form_excluded_columns = ["proof_image_urls", "match", "created_at"]


def _format_store_coords(obj: Store, _attr: str) -> str:
    loc = obj.location
    if loc is None:
        return "-"
    try:
        data = loc.data if hasattr(loc, "data") else loc
        if isinstance(data, str):
            data = bytes.fromhex(data)
        endian = "<" if data[0] == 1 else ">"
        # EWKB Point with SRID: [order:1][type:4][srid:4][x:8][y:8]
        lng, lat = struct.unpack(f"{endian}dd", data[9:25])
        return f"{lat:.6f}, {lng:.6f}"
    except Exception:
        return "-"


class StoreAdmin(ModelView, model=Store):
    name = "매장"
    name_plural = "매장 목록"
    icon = "fa-solid fa-store"
    column_list = [
        Store.id,
        Store.name,
        Store.category,
        Store.status,
        "coords",
        Store.rating_avg,
        Store.created_at,
    ]
    column_details_list = [
        Store.id,
        Store.name,
        Store.address,
        Store.phone,
        Store.category,
        Store.status,
        "coords",
        Store.operating_hours,
        Store.is_pet_allowed,
        Store.photo_urls,
        Store.rating_avg,
        Store.rating_count,
        Store.created_by,
        Store.created_at,
        Store.updated_at,
        Store.deleted_at,
    ]
    column_labels = {"coords": "좌표 (lat, lng)"}
    column_formatters = {"coords": _format_store_coords}
    column_formatters_detail = {"coords": _format_store_coords}
    column_searchable_list = [Store.name, Store.address]
    column_sortable_list = [Store.id, Store.rating_avg, Store.created_at]
    # location is PostGIS Geography; photo_urls is ARRAY — both excluded from form
    can_create = False
    form_excluded_columns = ["location", "photo_urls", "reviews", "created_at", "updated_at"]


class StoreReviewAdmin(ModelView, model=StoreReview):
    name = "매장 후기"
    name_plural = "매장 후기 목록"
    icon = "fa-solid fa-comment"
    column_list = [StoreReview.id, StoreReview.store_id, StoreReview.author_id, StoreReview.rating, StoreReview.is_pet_allowed, StoreReview.created_at]
    column_sortable_list = [StoreReview.id, StoreReview.created_at]
    form_excluded_columns = ["store", "created_at", "updated_at"]


class VolunteerRequestAdmin(ModelView, model=VolunteerRequest):
    name = "봉사 신청"
    name_plural = "봉사 신청 목록"
    icon = "fa-solid fa-hand-holding-heart"
    column_list = [VolunteerRequest.id, VolunteerRequest.user_id, VolunteerRequest.status, VolunteerRequest.processed_at, VolunteerRequest.created_at]
    column_sortable_list = [VolunteerRequest.id, VolunteerRequest.created_at]
    form_excluded_columns = ["created_at"]


class ReportAdmin(ModelView, model=Report):
    name = "신고"
    name_plural = "신고 목록"
    icon = "fa-solid fa-flag"
    column_list = [Report.id, Report.reporter_id, Report.target_user_id, Report.reason, Report.created_at]
    column_sortable_list = [Report.id, Report.created_at]
    form_excluded_columns = ["created_at"]


class CalendarEventAdmin(ModelView, model=CalendarEvent):
    name = "캘린더 이벤트"
    name_plural = "캘린더 이벤트 목록"
    icon = "fa-solid fa-calendar"
    column_list = [CalendarEvent.id, CalendarEvent.title, CalendarEvent.start_date, CalendarEvent.end_date, CalendarEvent.event_time, CalendarEvent.created_at]
    column_sortable_list = [CalendarEvent.id, CalendarEvent.start_date]
    form_excluded_columns = ["created_at", "updated_at"]
