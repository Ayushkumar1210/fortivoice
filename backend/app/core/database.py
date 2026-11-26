import json
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

# Fallback in-memory and JSON storage if MongoDB is not running locally
class LocalFallbackDatabase:
    def __init__(self, storage_dir: str = "./data/storage"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self.files = {
            "leads": os.path.join(self.storage_dir, "leads.json"),
            "appointments": os.path.join(self.storage_dir, "appointments.json"),
            "calls": os.path.join(self.storage_dir, "calls.json"),
            "documents": os.path.join(self.storage_dir, "documents.json"),
            "settings": os.path.join(self.storage_dir, "settings.json"),
        }
        for path in self.files.values():
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump([], f)

    def _read(self, collection: str) -> List[Dict[str, Any]]:
        path = self.files.get(collection)
        if not path or not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _write(self, collection: str, data: List[Dict[str, Any]]):
        path = self.files.get(collection)
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

    async def find(self, collection: str, query: Optional[Dict[str, Any]] = None, sort_field: str = "created_at", limit: int = 100) -> List[Dict[str, Any]]:
        items = self._read(collection)
        if query:
            filtered = []
            for item in items:
                match = True
                for k, v in query.items():
                    if item.get(k) != v:
                        match = False
                        break
                if match:
                    filtered.append(item)
            items = filtered
        # Sort descending if field exists
        try:
            items.sort(key=lambda x: str(x.get(sort_field, "")), reverse=True)
        except Exception:
            pass
        return items[:limit]

    async def find_one(self, collection: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        items = self._read(collection)
        for item in items:
            match = True
            for k, v in query.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                return item
        return None

    async def insert_one(self, collection: str, document: Dict[str, Any]) -> str:
        items = self._read(collection)
        doc = dict(document)
        if "_id" not in doc and "id" not in doc:
            doc["_id"] = str(uuid.uuid4())
        elif "_id" not in doc and "id" in doc:
            doc["_id"] = str(doc["id"])
        
        if "created_at" not in doc:
            doc["created_at"] = datetime.utcnow().isoformat()
        if "updated_at" not in doc:
            doc["updated_at"] = datetime.utcnow().isoformat()

        items.insert(0, doc)
        self._write(collection, items)
        return str(doc["_id"])

    async def update_one(self, collection: str, query: Dict[str, Any], update: Dict[str, Any]) -> bool:
        items = self._read(collection)
        updated = False
        set_vals = update.get("$set", update)
        for i, item in enumerate(items):
            match = True
            for k, v in query.items():
                if item.get(k) != v:
                    match = False
                    break
            if match:
                items[i].update(set_vals)
                items[i]["updated_at"] = datetime.utcnow().isoformat()
                updated = True
                break
        if updated:
            self._write(collection, items)
        return updated

    async def delete_one(self, collection: str, query: Dict[str, Any]) -> bool:
        items = self._read(collection)
        new_items = []
        deleted = False
        for item in items:
            match = True
            for k, v in query.items():
                if item.get(k) != v:
                    match = False
                    break
            if match and not deleted:
                deleted = True
                continue
            new_items.append(item)
        if deleted:
            self._write(collection, new_items)
        return deleted

    async def count_documents(self, collection: str, query: Optional[Dict[str, Any]] = None) -> int:
        items = await self.find(collection, query)
        return len(items)


class DatabaseManager:
    def __init__(self):
        self.is_mongo_connected = False
        self.mongo_client = None
        self.mongo_db = None
        self.fallback = LocalFallbackDatabase()

    async def connect(self, uri: str, db_name: str):
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            self.mongo_client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=2000)
            # Ping database
            await self.mongo_client.admin.command('ping')
            self.mongo_db = self.mongo_client[db_name]
            self.is_mongo_connected = True
            logger.info("Successfully connected to live MongoDB!")
        except Exception as e:
            self.is_mongo_connected = False
            logger.warning(f"Live MongoDB not reachable ({e}). Using persistent local fallback database.")

    async def close(self):
        if self.mongo_client:
            self.mongo_client.close()

    # Unified API across MongoDB & Fallback
    async def get_all(self, collection_name: str, query: Optional[Dict[str, Any]] = None, sort_field: str = "created_at", limit: int = 100) -> List[Dict[str, Any]]:
        if self.is_mongo_connected and self.mongo_db is not None:
            try:
                coll = self.mongo_db[collection_name]
                cursor = coll.find(query or {}).sort(sort_field, -1).limit(limit)
                docs = []
                async for doc in cursor:
                    doc["_id"] = str(doc["_id"])
                    docs.append(doc)
                return docs
            except Exception as e:
                logger.error(f"MongoDB read error: {e}, falling back to local DB")
        return await self.fallback.find(collection_name, query, sort_field, limit)

    async def get_by_id(self, collection_name: str, doc_id: str) -> Optional[Dict[str, Any]]:
        if self.is_mongo_connected and self.mongo_db is not None:
            try:
                from bson import ObjectId
                coll = self.mongo_db[collection_name]
                try:
                    query = {"_id": ObjectId(doc_id)}
                except Exception:
                    query = {"_id": doc_id}
                doc = await coll.find_one(query)
                if doc:
                    doc["_id"] = str(doc["_id"])
                    return doc
            except Exception as e:
                logger.error(f"MongoDB get_by_id error: {e}")
        return await self.fallback.find_one(collection_name, {"_id": doc_id})

    async def insert(self, collection_name: str, document: Dict[str, Any]) -> str:
        doc = dict(document)
        doc["created_at"] = doc.get("created_at") or datetime.utcnow().isoformat()
        doc["updated_at"] = doc.get("updated_at") or datetime.utcnow().isoformat()

        if self.is_mongo_connected and self.mongo_db is not None:
            try:
                coll = self.mongo_db[collection_name]
                res = await coll.insert_one(doc)
                return str(res.inserted_id)
            except Exception as e:
                logger.error(f"MongoDB insert error: {e}, falling back")
        return await self.fallback.insert_one(collection_name, doc)

    async def update(self, collection_name: str, doc_id: str, updates: Dict[str, Any]) -> bool:
        clean_updates = {k: v for k, v in updates.items() if k not in ("_id", "id")}
        clean_updates["updated_at"] = datetime.utcnow().isoformat()
        if self.is_mongo_connected and self.mongo_db is not None:
            try:
                from bson import ObjectId
                coll = self.mongo_db[collection_name]
                try:
                    q = {"_id": ObjectId(doc_id)}
                except Exception:
                    q = {"_id": doc_id}
                res = await coll.update_one(q, {"$set": clean_updates})
                return res.modified_count > 0
            except Exception as e:
                logger.error(f"MongoDB update error: {e}")
        return await self.fallback.update_one(collection_name, {"_id": doc_id}, clean_updates)

    async def delete(self, collection_name: str, doc_id: str) -> bool:
        if self.is_mongo_connected and self.mongo_db is not None:
            try:
                from bson import ObjectId
                coll = self.mongo_db[collection_name]
                try:
                    q = {"_id": ObjectId(doc_id)}
                except Exception:
                    q = {"_id": doc_id}
                res = await coll.delete_one(q)
                return res.deleted_count > 0
            except Exception as e:
                logger.error(f"MongoDB delete error: {e}")
        return await self.fallback.delete_one(collection_name, {"_id": doc_id})

    async def count(self, collection_name: str, query: Optional[Dict[str, Any]] = None) -> int:
        if self.is_mongo_connected and self.mongo_db is not None:
            try:
                coll = self.mongo_db[collection_name]
                return await coll.count_documents(query or {})
            except Exception as e:
                logger.error(f"MongoDB count error: {e}")
        return await self.fallback.count_documents(collection_name, query)


db_manager = DatabaseManager()
