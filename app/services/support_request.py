from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.contact import Contact
from app.models.enums import (
    SupportRequestPriority,
    SupportRequestStatus,
    UserRole,
)
from app.models.organization import Organization
from app.models.request_message import RequestMessage
from app.models.support_request import SupportRequest
from app.models.user import User
from app.repositories.contact import ContactRepository
from app.repositories.organization import OrganizationRepository
from app.repositories.support_request import SupportRequestRepository
from app.repositories.user import UserRepository
from app.schemas.support_request import (
    SupportRequestCreate,
    SupportRequestCreateMessageResponse,
    SupportRequestCreateResponse,
    SupportRequestListResponse,
    SupportRequestUpdate,
)

ALLOWED_ASSIGNED_USER_ROLES = {
    UserRole.OWNER,
    UserRole.ADMIN,
    UserRole.AGENT,
}

ALLOWED_STATUS_TRANSITIONS = {
    SupportRequestStatus.NEW: {
        SupportRequestStatus.IN_PROGRESS,
        SupportRequestStatus.WAITING_FOR_CONTACT,
        SupportRequestStatus.RESOLVED,
        SupportRequestStatus.CLOSED,
    },
    SupportRequestStatus.IN_PROGRESS: {
        SupportRequestStatus.WAITING_FOR_CONTACT,
        SupportRequestStatus.RESOLVED,
        SupportRequestStatus.CLOSED,
    },
    SupportRequestStatus.WAITING_FOR_CONTACT: {
        SupportRequestStatus.IN_PROGRESS,
        SupportRequestStatus.RESOLVED,
        SupportRequestStatus.CLOSED,
    },
    SupportRequestStatus.RESOLVED: {
        SupportRequestStatus.IN_PROGRESS,
        SupportRequestStatus.CLOSED,
    },
    SupportRequestStatus.CLOSED: {
        SupportRequestStatus.IN_PROGRESS,
    },
}


class SupportRequestService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.support_request_repository = SupportRequestRepository(session)
        self.organization_repository = OrganizationRepository(session)
        self.contact_repository = ContactRepository(session)
        self.user_repository = UserRepository(session)

    async def create_support_request(
        self,
        organization_id: UUID,
        support_request_data: SupportRequestCreate,
    ) -> SupportRequestCreateResponse:
        try:
            organization = await self._get_active_organization(organization_id)
            contact = await self._get_contact_for_create(
                organization.id,
                support_request_data.contact_id,
            )
            assigned_user = await self._get_assignable_user(
                organization.id,
                support_request_data.assigned_user_id,
            )

            request_number = await self.support_request_repository.next_request_number(
                organization.id
            )

            support_request = await self.support_request_repository.create(
                organization_id=organization.id,
                contact_id=contact.id,
                assigned_user_id=assigned_user.id if assigned_user else None,
                request_number=request_number,
                subject=support_request_data.subject,
                priority=support_request_data.priority,
                status=SupportRequestStatus.NEW,
            )

            initial_message = (
                await self.support_request_repository.create_initial_message(
                    support_request_id=support_request.id,
                    contact_id=contact.id,
                    content=support_request_data.initial_message,
                )
            )

            await self.session.commit()

            return self._build_create_response(support_request, initial_message)
        except Exception:
            await self.session.rollback()
            raise

    async def get_support_request(
        self,
        organization_id: UUID,
        support_request_id: UUID,
    ) -> SupportRequest:
        await self._get_organization(organization_id)
        support_request = (
            await self.support_request_repository.get_by_id_and_organization(
                support_request_id,
                organization_id,
            )
        )
        if support_request is None:
            raise NotFoundError(f"Conversation not found: {support_request_id}")

        return support_request

    async def list_support_requests(
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
    ) -> SupportRequestListResponse:
        await self._get_organization(organization_id)
        normalized_search = self._normalize_search(search)

        items = await self.support_request_repository.list_by_organization(
            organization_id,
            limit=limit,
            offset=offset,
            status=status,
            priority=priority,
            assigned_user_id=assigned_user_id,
            contact_id=contact_id,
            search=normalized_search,
            unassigned=unassigned,
        )
        total = await self.support_request_repository.count_by_organization(
            organization_id,
            status=status,
            priority=priority,
            assigned_user_id=assigned_user_id,
            contact_id=contact_id,
            search=normalized_search,
            unassigned=unassigned,
        )

        return SupportRequestListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def update_support_request(
        self,
        organization_id: UUID,
        support_request_id: UUID,
        support_request_data: SupportRequestUpdate,
    ) -> SupportRequest:
        await self._get_active_organization(organization_id)
        support_request = await self.get_support_request(
            organization_id,
            support_request_id,
        )

        updates = support_request_data.model_dump(exclude_unset=True)
        updated_support_request = await self.support_request_repository.update(
            support_request,
            updates,
        )

        await self.session.commit()
        reloaded_support_request = await (
            self.support_request_repository.get_by_id_and_organization(
                updated_support_request.id,
                organization_id,
            )
        )
        assert reloaded_support_request is not None
        return reloaded_support_request

    async def assign_support_request(
        self,
        organization_id: UUID,
        support_request_id: UUID,
        assigned_user_id: UUID,
    ) -> SupportRequest:
        await self._get_active_organization(organization_id)
        support_request = await self.get_support_request(
            organization_id,
            support_request_id,
        )

        if support_request.status == SupportRequestStatus.CLOSED:
            raise ConflictError(
                f"Closed conversation cannot be assigned: {support_request_id}"
            )

        assigned_user = await self._get_assignable_user(
            organization_id,
            assigned_user_id,
        )
        assert assigned_user is not None
        if (
            support_request.assigned_user_id is not None
            and support_request.assigned_user_id == assigned_user.id
        ):
            return support_request

        updated_support_request = await self.support_request_repository.update(
            support_request,
            {"assigned_user_id": assigned_user.id},
        )
        await self.session.commit()
        reloaded_support_request = await (
            self.support_request_repository.get_by_id_and_organization(
                updated_support_request.id,
                organization_id,
            )
        )
        assert reloaded_support_request is not None
        return reloaded_support_request

    async def unassign_support_request(
        self,
        organization_id: UUID,
        support_request_id: UUID,
    ) -> SupportRequest:
        await self._get_active_organization(organization_id)
        support_request = await self.get_support_request(
            organization_id,
            support_request_id,
        )

        if support_request.status == SupportRequestStatus.CLOSED:
            raise ConflictError(
                f"Closed conversation cannot be unassigned: {support_request_id}"
            )

        if support_request.assigned_user_id is None:
            return support_request

        updated_support_request = await self.support_request_repository.update(
            support_request,
            {"assigned_user_id": None},
        )
        await self.session.commit()
        reloaded_support_request = await (
            self.support_request_repository.get_by_id_and_organization(
                updated_support_request.id,
                organization_id,
            )
        )
        assert reloaded_support_request is not None
        return reloaded_support_request

    async def transition_support_request(
        self,
        organization_id: UUID,
        support_request_id: UUID,
        target_status: SupportRequestStatus,
    ) -> SupportRequest:
        await self._get_active_organization(organization_id)
        support_request = await self.get_support_request(
            organization_id,
            support_request_id,
        )

        current_status = support_request.status
        if current_status == target_status:
            raise ConflictError(
                f"Conversation is already in status: {target_status.value}"
            )

        allowed_targets = ALLOWED_STATUS_TRANSITIONS[current_status]
        if target_status not in allowed_targets:
            raise ConflictError(
                f"Invalid status transition: {current_status.value} -> "
                f"{target_status.value}"
            )

        updates = self._build_transition_updates(
            support_request=support_request,
            target_status=target_status,
        )
        updated_support_request = await self.support_request_repository.update(
            support_request,
            updates,
        )
        await self.session.commit()
        reloaded_support_request = await (
            self.support_request_repository.get_by_id_and_organization(
                updated_support_request.id,
                organization_id,
            )
        )
        assert reloaded_support_request is not None
        return reloaded_support_request

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

    async def _get_contact_for_create(
        self,
        organization_id: UUID,
        contact_id: UUID,
    ) -> Contact:
        contact = await self.contact_repository.get_by_id_and_organization(
            contact_id,
            organization_id,
        )
        if contact is None:
            raise NotFoundError(f"Contact not found: {contact_id}")

        if not contact.is_active:
            raise ConflictError(f"Contact is inactive: {contact_id}")

        return contact

    async def _get_assignable_user(
        self,
        organization_id: UUID,
        assigned_user_id: UUID | None,
    ) -> User | None:
        if assigned_user_id is None:
            return None

        user = await self.user_repository.get_by_id_and_organization(
            assigned_user_id,
            organization_id,
        )
        if user is None:
            raise NotFoundError(f"User not found: {assigned_user_id}")

        if not user.is_active:
            raise ConflictError(f"User is inactive: {assigned_user_id}")

        if user.role not in ALLOWED_ASSIGNED_USER_ROLES:
            raise ConflictError(f"User role is not assignable: {assigned_user_id}")

        return user

    def _normalize_search(self, search: str | None) -> str | None:
        if search is None:
            return None

        normalized = search.strip()
        return normalized or None

    def _build_create_response(
        self,
        support_request: SupportRequest,
        initial_message: RequestMessage,
    ) -> SupportRequestCreateResponse:
        return SupportRequestCreateResponse(
            id=support_request.id,
            organization_id=support_request.organization_id,
            contact_id=support_request.contact_id,
            assigned_user_id=support_request.assigned_user_id,
            request_number=support_request.request_number,
            subject=support_request.subject,
            status=support_request.status,
            priority=support_request.priority,
            resolved_at=support_request.resolved_at,
            closed_at=support_request.closed_at,
            created_at=support_request.created_at,
            updated_at=support_request.updated_at,
            initial_message=SupportRequestCreateMessageResponse(
                id=initial_message.id,
                author_type=initial_message.author_type,
                message_type=initial_message.message_type,
                author_contact_id=initial_message.author_contact_id,
                author_user_id=initial_message.author_user_id,
                content=initial_message.content,
                created_at=initial_message.created_at,
            ),
        )

    def _build_transition_updates(
        self,
        *,
        support_request: SupportRequest,
        target_status: SupportRequestStatus,
    ) -> dict[str, object]:
        now = datetime.now(timezone.utc)
        updates: dict[str, object] = {"status": target_status}

        if target_status == SupportRequestStatus.IN_PROGRESS:
            updates["resolved_at"] = None
            updates["closed_at"] = None
            return updates

        if target_status == SupportRequestStatus.WAITING_FOR_CONTACT:
            updates["resolved_at"] = None
            updates["closed_at"] = None
            return updates

        if target_status == SupportRequestStatus.RESOLVED:
            updates["resolved_at"] = now
            updates["closed_at"] = None
            return updates

        if target_status == SupportRequestStatus.CLOSED:
            if support_request.status == SupportRequestStatus.RESOLVED:
                updates["resolved_at"] = support_request.resolved_at
            else:
                updates["resolved_at"] = None
            updates["closed_at"] = now
            return updates

        return updates
