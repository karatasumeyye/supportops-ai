import base64
import json
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    UnprocessableEntityError,
)
from app.models.contact import Contact
from app.models.enums import (
    MessageAuthorType,
    MessageType,
    SupportRequestStatus,
    UserRole,
)
from app.models.organization import Organization
from app.models.request_message import RequestMessage
from app.models.support_request import SupportRequest
from app.models.user import User
from app.repositories.contact import ContactRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.request_message import RequestMessageRepository
from app.repositories.support_request import SupportRequestRepository
from app.repositories.user import UserRepository
from app.schemas.request_message import (
    ContactMessageCreate,
    RequestMessageCreate,
    RequestMessageListResponse,
    RequestMessageResponse,
    UserMessageCreate,
)

ALLOWED_MESSAGE_USER_ROLES = {
    UserRole.OWNER,
    UserRole.ADMIN,
    UserRole.AGENT,
}


class RequestMessageService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.request_message_repository = RequestMessageRepository(session)
        self.support_request_repository = SupportRequestRepository(session)
        self.organization_repository = OrganizationRepository(session)
        self.contact_repository = ContactRepository(session)
        self.user_repository = UserRepository(session)

    async def create_message(
        self,
        organization_id: UUID,
        conversation_id: UUID,
        message_data: RequestMessageCreate,
    ) -> RequestMessageResponse:
        try:
            organization = await self._get_active_organization(organization_id)
            conversation = await self._get_conversation(
                organization.id,
                conversation_id,
            )

            if conversation.status == SupportRequestStatus.CLOSED:
                raise ConflictError(
                    "Closed conversations cannot accept new messages: "
                    f"{conversation_id}"
                )

            if isinstance(message_data, ContactMessageCreate):
                await self._validate_contact_author(
                    organization.id,
                    conversation,
                    message_data.author_contact_id,
                )
            elif isinstance(message_data, UserMessageCreate):
                await self._validate_user_author(
                    organization.id,
                    message_data.author_user_id,
                )
            else:
                raise UnprocessableEntityError("Unsupported message author type.")

            message = await self.request_message_repository.create_message(
                support_request_id=conversation.id,
                author_type=MessageAuthorType(message_data.author_type),
                author_contact_id=getattr(message_data, "author_contact_id", None),
                author_user_id=getattr(message_data, "author_user_id", None),
                message_type=MessageType(message_data.message_type),
                body=message_data.body,
            )

            await self.session.commit()

            reloaded_message = (
                await self.request_message_repository.get_by_id_and_support_request(
                    message.id,
                    conversation.id,
                )
            )
            assert reloaded_message is not None
            return self._build_message_response(reloaded_message)
        except Exception:
            await self.session.rollback()
            raise

    async def list_messages(
        self,
        organization_id: UUID,
        conversation_id: UUID,
        *,
        limit: int,
        cursor: str | None = None,
    ) -> RequestMessageListResponse:
        await self._get_organization(organization_id)
        conversation = await self._get_conversation(
            organization_id,
            conversation_id,
        )

        cursor_created_at, cursor_id = self._decode_cursor(cursor)
        messages = await self.request_message_repository.list_messages(
            support_request_id=conversation.id,
            limit=limit,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )

        has_more = len(messages) > limit
        visible_messages = messages[:limit]
        next_cursor = None
        if has_more and visible_messages:
            last_message = visible_messages[-1]
            next_cursor = self._encode_cursor(
                created_at=last_message.created_at,
                message_id=last_message.id,
            )

        return RequestMessageListResponse(
            items=[
                self._build_message_response(message) for message in visible_messages
            ],
            next_cursor=next_cursor,
            has_more=has_more,
            limit=limit,
        )

    async def _get_organization(self, organization_id: UUID) -> Organization:
        organization = await self.organization_repository.get_by_id(organization_id)
        if organization is None:
            raise NotFoundError(f"Organization not found: {organization_id}")

        return organization

    async def _get_active_organization(
        self,
        organization_id: UUID,
    ) -> Organization:
        organization = await self._get_organization(organization_id)
        if not organization.is_active:
            raise ConflictError(f"Organization is inactive: {organization_id}")

        return organization

    async def _get_conversation(
        self,
        organization_id: UUID,
        conversation_id: UUID,
    ) -> SupportRequest:
        conversation = await self.support_request_repository.get_by_id_and_organization(
            conversation_id,
            organization_id,
        )
        if conversation is None:
            raise NotFoundError(f"Conversation not found: {conversation_id}")

        return conversation

    async def _validate_contact_author(
        self,
        organization_id: UUID,
        conversation: SupportRequest,
        contact_id: UUID,
    ) -> Contact:
        contact = await self.contact_repository.get_by_id_and_organization(
            contact_id,
            organization_id,
        )
        if contact is None:
            raise NotFoundError(f"Contact not found: {contact_id}")

        if contact.id != conversation.contact_id:
            raise ConflictError(
                f"Contact does not belong to conversation: {contact_id}"
            )

        if not contact.is_active:
            raise ConflictError(f"Contact is inactive: {contact_id}")

        return contact

    async def _validate_user_author(
        self,
        organization_id: UUID,
        user_id: UUID,
    ) -> User:
        user = await self.user_repository.get_by_id_and_organization(
            user_id,
            organization_id,
        )
        if user is None:
            raise NotFoundError(f"User not found: {user_id}")

        if not user.is_active:
            raise ConflictError(f"User is inactive: {user_id}")

        if user.role not in ALLOWED_MESSAGE_USER_ROLES:
            raise ConflictError(f"User role is not assignable: {user_id}")

        return user

    def _build_message_response(
        self,
        message: RequestMessage,
    ) -> RequestMessageResponse:
        return RequestMessageResponse(
            id=message.id,
            conversation_id=message.support_request_id,
            author_type=message.author_type,
            author_contact_id=message.author_contact_id,
            author_user_id=message.author_user_id,
            message_type=message.message_type,
            body=message.content,
            created_at=message.created_at,
        )

    def _encode_cursor(
        self,
        *,
        created_at: datetime,
        message_id: UUID,
    ) -> str:
        payload = {
            "created_at": created_at.isoformat(),
            "id": str(message_id),
        }
        encoded = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode(
            "utf-8"
        )
        return encoded.rstrip("=")

    def _decode_cursor(
        self,
        cursor: str | None,
    ) -> tuple[datetime | None, UUID | None]:
        if cursor is None:
            return None, None

        try:
            padding = "=" * (-len(cursor) % 4)
            decoded = base64.urlsafe_b64decode(f"{cursor}{padding}")
            payload = json.loads(decoded.decode("utf-8"))
        except Exception as error:
            raise UnprocessableEntityError("Invalid cursor.") from error

        if set(payload.keys()) != {"created_at", "id"}:
            raise UnprocessableEntityError("Invalid cursor.")

        try:
            created_at = datetime.fromisoformat(payload["created_at"])
        except Exception as error:
            raise UnprocessableEntityError("Invalid cursor.") from error

        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise UnprocessableEntityError("Invalid cursor.")

        try:
            message_id = UUID(payload["id"])
        except Exception as error:
            raise UnprocessableEntityError("Invalid cursor.") from error

        return created_at, message_id
