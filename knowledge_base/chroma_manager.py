"""ChromaDB知识库管理"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Optional, Tuple
from loguru import logger
import logging


class ChromaManager:
    """ChromaDB管理器"""
    
    def __init__(self, persist_dir: str):
        logger.info(f"初始化ChromaDB: {persist_dir}")
        # 屏蔽 ChromaDB 内部的 "Add of existing embedding ID" 噪声日志
        logging.getLogger("chromadb").setLevel(logging.ERROR)
        
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        self.collection = self.client.get_or_create_collection(
            name="paper_knowledge",
            metadata={"description": "论文知识库"}
        )
        logger.success("ChromaDB初始化完成")
    
    def add_papers(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict]
    ):
        """添加论文"""
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        logger.info(f"添加 {len(ids)} 篇论文到知识库")

    def get_documents_by_ids(self, ids: List[str]) -> Dict[str, Optional[str]]:
        """按ID批量获取已存文档内容，未命中返回None"""
        if not ids:
            return {}
        res = self.collection.get(ids=ids, include=["documents"])
        out: Dict[str, Optional[str]] = {i: None for i in ids}
        got_ids = res.get("ids", []) or []
        docs_list = res.get("documents", []) or []
        for i, doc in zip(got_ids, docs_list, strict=False):
            out[i] = doc
        return out

    def upsert_if_changed(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict]
    ) -> Tuple[int, int]:
        """仅在不存在或文档内容变化时写入，返回 (跳过数, 写入数)"""
        if not ids:
            return (0, 0)
        current = self.get_documents_by_ids(ids)
        to_upsert_idx: List[int] = []
        skipped = 0
        for idx, _id in enumerate(ids):
            existing = current.get(_id)
            if existing is None or existing != documents[idx]:
                to_upsert_idx.append(idx)
            else:
                skipped += 1
        if to_upsert_idx:
            sub_ids = [ids[i] for i in to_upsert_idx]
            sub_emb = [embeddings[i] for i in to_upsert_idx]
            sub_docs = [documents[i] for i in to_upsert_idx]
            sub_meta = [metadatas[i] for i in to_upsert_idx]
            self.collection.upsert(
                ids=sub_ids,
                embeddings=sub_emb,
                documents=sub_docs,
                metadatas=sub_meta
            )
            logger.info(f"知识库写入完成（更新/新增 {len(sub_ids)}，跳过 {skipped}）")
            return (skipped, len(sub_ids))
        logger.info(f"知识库写入跳过（全部未变化，共 {skipped}）")
        return (skipped, 0)
    
    def retrieve_similar(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict] = None
    ) -> Dict:
        """检索相似论文"""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        return results
    
    def count(self) -> int:
        """统计论文数量"""
        return self.collection.count()

