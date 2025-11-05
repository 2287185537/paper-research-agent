"""嵌入模型服务"""
import os
from typing import List, Optional
from sentence_transformers import SentenceTransformer
from loguru import logger


class EmbeddingService:
    """嵌入模型服务"""
    
    def __init__(self, model_name: str, cache_dir: str):
        # 设置缓存目录
        os.environ['TRANSFORMERS_CACHE'] = cache_dir
        os.environ['HF_HOME'] = cache_dir

        logger.info(f"加载嵌入模型: {model_name}")

        # 优先尝试本地缓存/路径加载，失败再联机下载
        local_path = self._resolve_local_model_path(model_name, cache_dir)
        if local_path:
            try:
                logger.info(f"优先从本地加载模型: {local_path}")
                self.model = SentenceTransformer(local_path, cache_folder=cache_dir)
                logger.success("嵌入模型加载完成(本地)")
                return
            except Exception as e:
                logger.warning(f"本地加载失败，将尝试在线加载: {e}")

        # 在线加载（将自动落地到 cache_dir）
        self.model = SentenceTransformer(model_name, cache_folder=cache_dir)
        logger.success("嵌入模型加载完成(在线)")
    
    def encode(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """编码文本为向量"""
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False
        )
        return embeddings.tolist()
    
    def encode_single(self, text: str) -> List[float]:
        """编码单个文本"""
        return self.encode([text])[0]

    def _resolve_local_model_path(self, model_name: str, cache_dir: str) -> Optional[str]:
        """解析本地模型路径：
        1) 若传入的是本地目录且存在：
           - 优先使用 snapshots/refs 指向的快照
           - 否则使用该目录
        2) 若传入是模型名：在 cache_dir 下查找 HuggingFace 缓存结构
           - 优先尝试 models--{org}--{name}（若未含org则假定 sentence-transformers）
        返回可用于 SentenceTransformer 的目录路径，若找不到返回 None。
        """

        def _resolve_snapshot_dir(base: str) -> Optional[str]:
            refs_dir = os.path.join(base, 'refs')
            snap_dir = os.path.join(base, 'snapshots')
            # 读取 refs/main 指向的快照
            main_ref = os.path.join(refs_dir, 'main')
            if os.path.isfile(main_ref):
                try:
                    with open(main_ref, 'r', encoding='utf-8') as f:
                        ref = f.read().strip()
                    target = os.path.join(snap_dir, ref)
                    if os.path.isdir(target):
                        return target
                except Exception:
                    pass
            # 否则选择最近修改的快照目录
            if os.path.isdir(snap_dir):
                candidates = [os.path.join(snap_dir, d) for d in os.listdir(snap_dir)]
                candidates = [d for d in candidates if os.path.isdir(d)]
                if candidates:
                    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                    return candidates[0]
            return None

        # 传入的是本地路径
        if os.path.isdir(model_name):
            resolved = _resolve_snapshot_dir(model_name)
            return resolved or model_name

        # 传入是模型名：在 cache_dir 中寻找 HF 缓存结构
        def _to_cache_dir(name: str) -> str:
            return os.path.join(cache_dir, 'models--' + name.replace('/', '--'))

        candidates = [model_name]
        if '/' not in model_name:
            candidates.append(f"sentence-transformers/{model_name}")

        for name in candidates:
            base = _to_cache_dir(name)
            if os.path.isdir(base):
                resolved = _resolve_snapshot_dir(base)
                if resolved:
                    return resolved
        return None

