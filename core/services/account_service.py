from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
import uuid as uuid_lib
import time

from fastapi import HTTPException, status

from core.services.base import BaseService
from core.models.account import Account
from core.models.service_provider import ServiceProvider
from core.models.models import Model
from core.models.api_key import ApiKey


class AccountService(BaseService):
    def __init__(self, db: Session, user_id: Optional[int] = None, org_id=None):
        super().__init__(db, user_id, org_id=org_id)

    def upsert_account(self, service_provider_id: Optional[int] = None, name: str = "",
                       service_type: str = "",
                       config: Optional[Dict] = None, api_key_id: Optional[int] = None,
                       description: Optional[str] = None,
                       is_default: bool = False, is_public: bool = False,
                       tags: Optional[list] = None, account_uuid: Optional[str] = None,
                       account_status: Optional[str] = None,
                       api_key_value: Optional[str] = None,
                       api_key_name: Optional[str] = None,
                       additional_credentials: Optional[Dict] = None,
                       model_provider_menu_id: Optional[int] = None,
                       hosting_provider_id: Optional[int] = None) -> Dict[str, Any]:
        current_time = int(time.time())

        # Check name uniqueness within the org
        existing = self.query(Account).filter(
            Account.name == name,
            Account.service_type == service_type,
        )
        if account_uuid:
            existing = existing.filter(Account.uuid != UUID(account_uuid))
        existing = existing.first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this name and type already exists in this organization"
            )

        if service_provider_id:
            provider = self.db.query(ServiceProvider).filter(
                ServiceProvider.id == service_provider_id
            ).first()
            if not provider:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Service provider not found"
                )

        if model_provider_menu_id:
            from core.models.model_provider_menu import ModelProviderMenu
            mpm = self.db.query(ModelProviderMenu).filter(
                ModelProviderMenu.id == model_provider_menu_id
            ).first()
            if not mpm:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Model provider menu not found"
                )

        if hosting_provider_id:
            from core.models.hosting_provider import HostingProvider
            hp = self.db.query(HostingProvider).filter(
                HostingProvider.id == hosting_provider_id
            ).first()
            if not hp:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Hosting provider not found"
                )

        if api_key_id:
            api_key = self.db.query(ApiKey).filter(
                ApiKey.id == api_key_id,
                ApiKey.status == 'active'
            ).first()
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="API key not found or inactive"
                )
        elif api_key_value:
            from core.services.api_key_service import ApiKeyService
            api_key_result = ApiKeyService(self.db, user_id=self._user_id, org_id=self.org_id).upsert_api_key(
                service_provider_id=service_provider_id,
                name=api_key_name or f"{name} key",
                api_key_value=api_key_value,
                additional_credentials=additional_credentials,
            )
            api_key_id = api_key_result["id"]

        if is_default:
            self.db.query(Account).filter(
                Account.service_type == service_type,
                Account.is_default == True
            ).update({"is_default": False, "updated_at": current_time})

        values = {
            "uuid": UUID(account_uuid) if account_uuid else uuid_lib.uuid4(),
            "service_provider_id": service_provider_id,
            "model_provider_menu_id": model_provider_menu_id,
            "hosting_provider_id": hosting_provider_id,
            "name": name,
            "description": description,
            "service_type": service_type,
            "config": config or {},
            "is_default": is_default,
            "is_public": is_public,
            "tags": tags,
            "created_by": self._user_id,
            "created_at": current_time,
            "updated_at": current_time
        }

        if account_status is not None:
            values["status"] = account_status

        update_fields = [
            "service_provider_id", "model_provider_menu_id", "hosting_provider_id", "name",
            "description", "service_type", "config", "is_default", "is_public",
            "tags", "updated_at"
        ]
        if account_status is not None:
            update_fields.append("status")

        self.upsert(
            model=Account,
            values=values,
            conflict_fields=["uuid"],
            update_fields=update_fields
        )

        record_uuid = values["uuid"]
        acct = self.db.query(Account).filter(Account.uuid == record_uuid).first()

        # Link the API key to this account (reverse FK direction)
        if api_key_id:
            self.db.query(ApiKey).filter(ApiKey.id == api_key_id).update({"account_id": acct.id})
            self.db.flush()

        # Auto-create ModelInstances for this account (only on new account creation)
        if acct and acct.model_provider_menu_id and not account_uuid:
            from core.models.model_menu import ModelMenu
            from core.models.model_instance import ModelInstance

            model_menus = self.db.query(ModelMenu).filter(
                ModelMenu.model_provider_menu_id == acct.model_provider_menu_id,
                ModelMenu.status == 'active'
            ).all()

            for mm in model_menus:
                exists = self.db.query(ModelInstance).filter(
                    ModelInstance.account_id == acct.id,
                    ModelInstance.model_menu_id == mm.id
                ).first()
                if not exists:
                    mi = ModelInstance(
                        model_menu_id=mm.id,
                        account_id=acct.id,
                        host_region=None,
                        status='active',
                    )
                    self.db.add(mi)
            self.db.flush()

        # Fetch api_key_hint
        api_key_hint = None
        ak = self.db.query(ApiKey).filter(
            ApiKey.account_id == acct.id, ApiKey.status == 'active'
        ).order_by(ApiKey.id.desc()).first()
        if ak:
            api_key_hint = ak.api_key_hint

        return {
            "id": acct.id,
            "uuid": str(acct.uuid),
            "name": acct.name,
            "description": acct.description,
            "service_type": acct.service_type,
            "service_provider_id": acct.service_provider_id,
            "model_provider_menu_id": acct.model_provider_menu_id,
            "hosting_provider_id": acct.hosting_provider_id,
            "api_key_id": ak.id if ak else None,
            "api_key_hint": api_key_hint,
            "config": acct.config,
            "status": acct.status,
            "is_default": acct.is_default,
            "is_public": acct.is_public,
            "tags": acct.tags,
            "created_at": acct.created_at,
            "updated_at": acct.updated_at
        }

    def get_all_accounts(self, service_type: Optional[str] = None,
                         page: Optional[int] = None,
                         page_size: Optional[int] = None):
        from sqlalchemy.orm import aliased
        from core.models.model_provider_menu import ModelProviderMenu
        from core.models.model_menu import ModelMenu

        # Left join both provider paths so accounts with either FK are returned
        SP = aliased(ServiceProvider)
        MPM = aliased(ModelProviderMenu)

        query = (
            self.query(Account)
            .outerjoin(SP, Account.service_provider_id == SP.id)
            .outerjoin(MPM, Account.model_provider_menu_id == MPM.id)
            .filter(Account.status == 'active')
            .add_entity(SP)
            .add_entity(MPM)
        )

        if service_type:
            query = query.filter(Account.service_type == service_type)

        total = query.count() if page and page_size else None

        if page and page_size:
            offset = (page - 1) * page_size
            results = query.offset(offset).limit(page_size).all()
        else:
            results = query.all()

        # Collect account IDs to batch-fetch api_key hints
        account_ids = [acct.id for acct, _, _ in results]
        api_key_hints = {}
        if account_ids:
            hint_rows = self.db.query(ApiKey.account_id, ApiKey.id, ApiKey.api_key_hint).filter(
                ApiKey.account_id.in_(account_ids), ApiKey.status == 'active'
            ).all()
            for row in hint_rows:
                if row.account_id not in api_key_hints:
                    api_key_hints[row.account_id] = (row.id, row.api_key_hint)

        # Batch-fetch models: old path (Model table) + new path (ModelMenu table)
        # Old path: models by service_provider_id
        old_provider_ids = list({acct.service_provider_id for acct, _, _ in results if acct.service_provider_id})
        models_by_provider: Dict[int, List[Dict[str, Any]]] = {}
        if old_provider_ids:
            models = (
                self.db.query(Model)
                .filter(Model.service_provider_id.in_(old_provider_ids), Model.status == "active")
                .order_by(Model.id)
                .all()
            )
            for m in models:
                models_by_provider.setdefault(m.service_provider_id, []).append({
                    "id": m.id,
                    "service_provider_id": m.service_provider_id,
                    "name": m.name,
                    "meta_data": m.meta_data,
                    "created_at": m.created_at,
                    "updated_at": m.updated_at,
                })

        # New path: models by model_provider_menu_id (from ModelMenu)
        mpm_ids = list({acct.model_provider_menu_id for acct, _, _ in results if acct.model_provider_menu_id})
        models_by_mpm: Dict[int, List[Dict[str, Any]]] = {}
        if mpm_ids:
            menus = (
                self.db.query(ModelMenu)
                .filter(ModelMenu.model_provider_menu_id.in_(mpm_ids), ModelMenu.status == "active")
                .order_by(ModelMenu.id)
                .all()
            )
            for mm in menus:
                models_by_mpm.setdefault(mm.model_provider_menu_id, []).append({
                    "id": mm.id,
                    "model_provider_menu_id": mm.model_provider_menu_id,
                    "name": mm.name,
                    "meta_data": mm.meta_data,
                    "created_at": mm.created_at,
                    "updated_at": mm.updated_at,
                })

        data = []
        for acct, sp, mpm in results:
            # Resolve provider info from whichever path is set
            if mpm:
                provider_name = mpm.display_name
                provider_type = mpm.provider_type
                acct_models = models_by_mpm.get(mpm.id, [])
                schema = mpm.meta_data_schema
            elif sp:
                provider_name = sp.display_name
                provider_type = sp.provider_type
                acct_models = models_by_provider.get(sp.id, [])
                schema = sp.meta_data_schema
            else:
                provider_name = None
                provider_type = acct.service_type
                acct_models = []
                schema = None

            ak_info = api_key_hints.get(acct.id)
            data.append({
                "id": acct.id,
                "uuid": str(acct.uuid),
                "name": acct.name,
                "display_name": acct.name,
                "description": acct.description,
                "service_type": acct.service_type,
                "service_provider_id": acct.service_provider_id,
                "model_provider_menu_id": acct.model_provider_menu_id,
                "hosting_provider_id": acct.hosting_provider_id,
                "service_provider_name": provider_name,
                "provider_type": provider_type,
                "api_key_id": ak_info[0] if ak_info else None,
                "api_key_hint": ak_info[1] if ak_info else None,
                "config": acct.config,
                "status": acct.status,
                "is_default": acct.is_default,
                "is_public": acct.is_public,
                "tags": acct.tags,
                "usage_count": acct.usage_count,
                "last_used_at": acct.last_used_at,
                "created_at": acct.created_at,
                "models": acct_models,
                "meta_data_schema": schema,
            })

        if page and page_size and total is not None:
            return {
                "data": data,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": (total + page_size - 1) // page_size,
                }
            }

        return data

    def get_account(self, account_id: int) -> Dict[str, Any]:
        from core.models.model_provider_menu import ModelProviderMenu

        acct = self.query(Account).filter(Account.id == account_id).first()
        if not acct:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )

        # Resolve provider from whichever path is set
        provider_name = None
        provider_type = acct.service_type
        if acct.model_provider_menu_id:
            mpm = self.db.query(ModelProviderMenu).filter(ModelProviderMenu.id == acct.model_provider_menu_id).first()
            if mpm:
                provider_name = mpm.display_name
                provider_type = mpm.provider_type
        elif acct.service_provider_id:
            sp = self.db.query(ServiceProvider).filter(ServiceProvider.id == acct.service_provider_id).first()
            if sp:
                provider_name = sp.display_name
                provider_type = sp.provider_type

        # Get API key via reverse FK
        ak = self.db.query(ApiKey).filter(
            ApiKey.account_id == acct.id, ApiKey.status == 'active'
        ).order_by(ApiKey.id.desc()).first()

        return {
            "id": acct.id,
            "uuid": str(acct.uuid),
            "name": acct.name,
            "description": acct.description,
            "service_type": acct.service_type,
            "service_provider_id": acct.service_provider_id,
            "model_provider_menu_id": acct.model_provider_menu_id,
            "service_provider_name": provider_name,
            "provider_type": provider_type,
            "api_key_id": ak.id if ak else None,
            "api_key_hint": ak.api_key_hint if ak else None,
            "config": acct.config,
            "status": acct.status,
            "is_default": acct.is_default,
            "is_public": acct.is_public,
            "tags": acct.tags,
            "usage_count": acct.usage_count,
            "last_used_at": acct.last_used_at,
            "created_at": acct.created_at,
            "updated_at": acct.updated_at
        }

    def delete_account(self, account_id: int) -> Dict[str, str]:
        acct = self.query(Account).filter(Account.id == account_id).first()

        if not acct:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )

        self.db.delete(acct)
        self.db.commit()

        return {"message": "Account deleted successfully"}

    def delete_account_by_uuid(self, account_uuid: str) -> Dict[str, str]:
        acct = self.query(Account).filter(Account.uuid == account_uuid).first()

        if not acct:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )

        self.db.delete(acct)
        self.db.commit()

        return {"message": "Account deleted successfully"}

    def get_default_account(self, service_type: str) -> Dict[str, Any]:
        from core.models.model_provider_menu import ModelProviderMenu

        acct = self.query(Account).filter(
            Account.service_type == service_type,
            Account.is_default == True,
            Account.status == 'active'
        ).first()

        if not acct:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No default account found for type: {service_type}"
            )

        # Resolve provider name
        provider_name = None
        if acct.model_provider_menu_id:
            mpm = self.db.query(ModelProviderMenu).filter(ModelProviderMenu.id == acct.model_provider_menu_id).first()
            if mpm:
                provider_name = mpm.display_name
        elif acct.service_provider_id:
            sp = self.db.query(ServiceProvider).filter(ServiceProvider.id == acct.service_provider_id).first()
            if sp:
                provider_name = sp.display_name

        # Get API key via reverse FK
        ak = self.db.query(ApiKey).filter(
            ApiKey.account_id == acct.id, ApiKey.status == 'active'
        ).order_by(ApiKey.id.desc()).first()

        return {
            "id": acct.id,
            "uuid": str(acct.uuid),
            "name": acct.name,
            "service_type": acct.service_type,
            "service_provider_id": acct.service_provider_id,
            "model_provider_menu_id": acct.model_provider_menu_id,
            "service_provider_name": provider_name,
            "api_key_id": ak.id if ak else None,
            "api_key_hint": ak.api_key_hint if ak else None,
            "config": acct.config,
            "status": acct.status,
            "is_default": acct.is_default
        }
