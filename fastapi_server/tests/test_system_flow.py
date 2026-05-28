from __future__ import annotations

import importlib
import os
import unittest


class KnowledgeMemoryFlowTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["GATEWAY_MODE"] = "thin"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        os.environ["EMBEDDING_PROVIDER"] = "local"
        os.environ["VECTOR_STORE_PROVIDER"] = "memory"
        os.environ["EMBEDDING_FALLBACK_TO_LOCAL"] = "true"
        os.environ["VECTOR_STORE_FALLBACK_TO_MEMORY"] = "true"
        os.environ["SIMILARITY_THRESHOLD"] = "0.35"

        import app.core.config as config_module
        import app.core.database as database_module
        import app.services.embedding_service as embedding_module
        import app.services.vector_store_service as vector_module
        import app.services.knowledge_repository as knowledge_repository_module
        import app.services.knowledge_service as knowledge_module
        import app.services.retrieval_cache_service as cache_module

        importlib.reload(config_module)
        importlib.reload(database_module)
        importlib.reload(embedding_module)
        importlib.reload(vector_module)
        importlib.reload(cache_module)
        importlib.reload(knowledge_repository_module)
        importlib.reload(knowledge_module)

        cls.knowledge_service = knowledge_module.knowledge_service

    async def test_reindex_and_search_isolates_tenants(self):
        tenant_a = "tenant-system-a"
        tenant_b = "tenant-system-b"

        await self.knowledge_service.reindex_document(
            tenant_id=tenant_a,
            doc_id="billing_doc_a",
            text="Enterprise refunds are processed in seven business days.",
            topic="billing",
            language="en",
            metadata={"document_name": "Billing Policy A", "access_level": "internal"},
        )
        await self.knowledge_service.reindex_document(
            tenant_id=tenant_b,
            doc_id="hr_doc_b",
            text="Vacation requests require manager approval.",
            topic="hr",
            language="en",
            metadata={"document_name": "HR Policy B", "access_level": "internal"},
        )

        hits_a = await self.knowledge_service.search(
            tenant_id=tenant_a,
            query="refund timeline",
            top_k=5,
            filters={"tenant_id": tenant_a, "language": "en"},
            use_cache=False,
        )
        self.assertTrue(all(hit.get("doc_id") != "hr_doc_b" for hit in hits_a))


if __name__ == "__main__":
    unittest.main()
