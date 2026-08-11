from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SupportRequestPriority, SupportRequestStatus
from app.models.request_message import MessageAuthorType, MessageType, RequestMessage
from app.models.support_request import SupportRequest
from app.models.support_request_sequence import SupportRequestSequence


class SupportRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def next_request_number(
        self,
        organization_id: UUID,
    ) -> str:
        insert_statement = pg_insert(SupportRequestSequence).values(
            organization_id=organization_id,
            last_value=1,
        )
        statement = insert_statement.on_conflict_do_update(
            index_elements=[SupportRequestSequence.organization_id],
            set_={
                "last_value": SupportRequestSequence.last_value + 1,
            },
        ).returning(SupportRequestSequence.last_value)

        result = await self.session.execute(statement)
        next_value = int(result.scalar_one())
        return self._format_request_number(next_value)

    async def create(
        self,
        *,
        organization_id: UUID,
        contact_id: UUID,
        assigned_user_id: UUID | None,
        request_number: str,
        subject: str,
        priority: SupportRequestPriority,
        status: SupportRequestStatus,
    ) -> SupportRequest:
        support_request = SupportRequest(
            organization_id=organization_id,
            contact_id=contact_id,
            assigned_user_id=assigned_user_id,
            request_number=request_number,
            subject=subject,
            priority=priority,
            status=status,
        )

        self.session.add(support_request)
        await self.session.flush()
        return support_request

    async def create_initial_message(
        self,
        *,
        support_request_id: UUID,
        contact_id: UUID,
        content: str,
    ) -> RequestMessage:
        message = RequestMessage(
            support_request_id=support_request_id,
            author_type=MessageAuthorType.CONTACT,
            message_type=MessageType.PUBLIC_REPLY,
            content=content,
            author_contact_id=contact_id,
            author_user_id=None,
        )

        self.session.add(message)
        await self.session.flush()
        return message

    async def get_by_id_and_organization(
        self,
        support_request_id: UUID,
        organization_id: UUID,
    ) -> SupportRequest | None:
        query = select(SupportRequest).where(
            SupportRequest.id == support_request_id,
            SupportRequest.organization_id == organization_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_by_organization(
        self,
        organization_id: UUID,
        *,
        limit: int,
        offset: int,
        status: SupportRequestStatus | None = None,
        priority: SupportRequestPriority | None = None,
        assigned_user_id: UUID | None = None,
        contact_id: UUID | None = None,
        search: str | None = None,
        unassigned: bool | None = None,
    ) -> list[SupportRequest]:
        query = self._build_filtered_query(
            organization_id=organization_id,
            status=status,
            priority=priority,
            assigned_user_id=assigned_user_id,
            contact_id=contact_id,
            search=search,
            unassigned=unassigned,
        ).order_by(
            SupportRequest.created_at.desc(),
            SupportRequest.id.desc(),
        )
        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_organization(
        self,
        organization_id: UUID,
        *,
        status: SupportRequestStatus | None = None,
        priority: SupportRequestPriority | None = None,
        assigned_user_id: UUID | None = None,
        contact_id: UUID | None = None,
        search: str | None = None,
        unassigned: bool | None = None,
    ) -> int:
        query = (
            select(func.count(SupportRequest.id))
            .select_from(SupportRequest)
            .where(SupportRequest.organization_id == organization_id)
        )
        query = self._apply_filters(
            query,
            status=status,
            priority=priority,
            assigned_user_id=assigned_user_id,
            contact_id=contact_id,
            search=search,
            unassigned=unassigned,
        )

        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def update(
        self,
        support_request: SupportRequest,
        updates: dict[str, object],
    ) -> SupportRequest:
        for field, value in updates.items():
            setattr(support_request, field, value)

        await self.session.flush()
        return support_request

    def _build_filtered_query(
        self,
        *,
        organization_id: UUID,
        status: SupportRequestStatus | None,
        priority: SupportRequestPriority | None,
        assigned_user_id: UUID | None,
        contact_id: UUID | None,
        search: str | None,
        unassigned: bool | None,
    ) -> Any:
        query = select(SupportRequest).where(
            SupportRequest.organization_id == organization_id
        )
        return self._apply_filters(
            query,
            status=status,
            priority=priority,
            assigned_user_id=assigned_user_id,
            contact_id=contact_id,
            search=search,
            unassigned=unassigned,
        )

    def _apply_filters(
        self,
        query: Any,
        *,
        status: SupportRequestStatus | None,
        priority: SupportRequestPriority | None,
        assigned_user_id: UUID | None,
        contact_id: UUID | None,
        search: str | None,
        unassigned: bool | None,
    ) -> Any:
        filters = []

        if status is not None:
            filters.append(SupportRequest.status == status)

        if priority is not None:
            filters.append(SupportRequest.priority == priority)

        if assigned_user_id is not None:
            filters.append(SupportRequest.assigned_user_id == assigned_user_id)

        if contact_id is not None:
            filters.append(SupportRequest.contact_id == contact_id)

        if unassigned is True:
            filters.append(SupportRequest.assigned_user_id.is_(None))

        if search:
            pattern = f"%{search}%"
            filters.append(
                or_(
                    SupportRequest.subject.ilike(pattern),
                    SupportRequest.request_number.ilike(pattern),
                )
            )

        if filters:
            query = query.where(and_(*filters))

        return query

    def _format_request_number(self, value: int) -> str:
        return f"CONV-{value:06d}"
