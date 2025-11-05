"""Arxiv论文获取服务"""
import arxiv
import hashlib
import json
from pathlib import Path
from typing import List, Dict
from loguru import logger


class ArxivService:
    """Arxiv论文服务"""
    
    def __init__(self, cache_dir: str = "./cache/papers"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def search_papers(self, query: str, max_results: int = 50) -> List[Dict]:
        """搜索论文"""
        key_raw = f"{query}|{max_results}".encode('utf-8')
        key_md5 = hashlib.md5(key_raw).hexdigest()
        cache_file = self.cache_dir / f"search_{key_md5}.json"
        
        # 检查缓存
        if cache_file.exists():
            logger.info(f"从缓存加载: {query}")
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 执行搜索
        logger.info(f"搜索论文: {query} (最多{max_results}篇)")
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )
        
        papers = []
        for result in search.results():
            paper = {
                "id": result.entry_id.split('/')[-1],
                "title": result.title,
                "authors": [author.name for author in result.authors],
                "abstract": result.summary.replace('\n', ' '),
                "published": result.published.strftime('%Y-%m-%d'),
                "url": result.pdf_url,
                "categories": result.categories
            }
            papers.append(paper)
        
        # 保存缓存
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(papers, f, ensure_ascii=False, indent=2)
        
        logger.success(f"找到 {len(papers)} 篇论文")
        return papers

