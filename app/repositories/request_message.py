from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import MessageAuthorType, MessageType
from app.models.request_message import RequestMessage


class RequestMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_message(
        self,
        *,
        support_request_id: UUID,
        author_type: MessageAuthorType,
        author_contact_id: UUID | None,
        author_user_id: UUID | None,
        message_type: MessageType,
        body: str,
    ) -> RequestMessage:
        message = RequestMessage(
            support_request_id=support_request_id,
            author_type=author_type,
            author_contact_id=author_contact_id,
            author_user_id=author_user_id,
            message_type=message_type,
            content=body,
        )

        self.session.add(message)
        await self.session.flush()
        return message

    async def get_by_id_and_support_request(
        self,
        message_id: UUID,
        support_request_id: UUID,
    ) -> RequestMessage | None:
        query = select(RequestMessage).where(
            RequestMessage.id == message_id,
            RequestMessage.support_request_id == support_request_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_messages(
        self,
        *,
        support_request_id: UUID,
        limit: int,
        cursor_created_at: datetime | None = None,
        cursor_id: UUID | None = None,
    ) -> list[RequestMessage]:
        query = select(RequestMessage).where(
            RequestMessage.support_request_id == support_request_id
        )

        if cursor_created_at is not None and cursor_id is not None:
            query = query.where(
                or_(
                    RequestMessage.created_at > cursor_created_at,
                    (
                        (RequestMessage.created_at == cursor_created_at)
                        & (RequestMessage.id > cursor_id)
                    ),
                )
            )

        query = query.order_by(RequestMessage.created_at.asc(), RequestMessage.id.asc())
        query = query.limit(limit + 1)

        result = await self.session.execute(query)
        return list(result.scalars().all())
