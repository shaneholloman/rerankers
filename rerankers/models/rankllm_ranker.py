from typing import Optional, Union, List
from rerankers.models.ranker import BaseRanker
from rerankers.documents import Document
from rerankers.results import RankedResults, Result
from rerankers.utils import prep_docs

# from rerankers import Reranker

from rank_llm.rerank.reranker import Reranker as rankllm_Reranker
from rank_llm.rerank import PromptMode, get_azure_openai_args, get_genai_api_key, get_openai_api_key
from rank_llm.data import Candidate, Query, Request


class RankLLMRanker(BaseRanker):
    def __init__(
        self,
        model: str = "rank_zephyr",
        api_key: Optional[str] = None,
        lang: str = "en",
        verbose: int = 1,
        # RankLLM specific arguments
        window_size: int = 20,
        context_size: int = 4096,
        prompt_mode: PromptMode = PromptMode.RANK_GPT,
        num_few_shot_examples: int = 0,
        few_shot_file: Optional[str] = None,
        num_gpus: int = 1,
        variable_passages: bool = False,
        use_logits: bool = False,
        use_alpha: bool = False,
        stride: int = 10,
        use_azure_openai: bool = False,
    ) -> "RankLLMRanker":
        self.api_key = api_key
        self.model = model
        self.verbose = verbose
        self.lang = lang
        
        # RankLLM-specific parameters
        self.window_size = window_size
        self.context_size = context_size
        self.prompt_mode = prompt_mode
        self.num_few_shot_examples = num_few_shot_examples
        self.few_shot_file = few_shot_file
        self.num_gpus = num_gpus
        self.variable_passages = variable_passages
        self.use_logits = use_logits
        self.use_alpha = use_alpha
        self.stride = stride
        self.use_azure_openai = use_azure_openai
        
        kwargs = {
            "model_path": self.model,
            "default_model_coordinator": None,
            "context_size": self.context_size,
            "prompt_mode": self.prompt_mode,
            "num_gpus": self.num_gpus,
            "use_logits": self.use_logits,
            "use_alpha": self.use_alpha,
            "num_few_shot_examples": self.num_few_shot_examples,
            "few_shot_file": self.few_shot_file,
            "variable_passages": self.variable_passages,
            "interactive": False,
            "window_size": self.window_size,
            "stride": self.stride,
            "use_azure_openai": self.use_azure_openai,
        }
        model_coordinator = rankllm_Reranker.create_model_coordinator(**kwargs)
        self.reranker = rankllm_Reranker(model_coordinator)

    def rank(
        self,
        query: str,
        docs: Union[str, List[str], Document, List[Document]],
        doc_ids: Optional[Union[List[str], List[int]]] = None,
        metadata: Optional[List[dict]] = None,
        rank_start: int = 0,
        rank_end: int = 0,
    ) -> RankedResults:
        docs = prep_docs(docs, doc_ids, metadata)

        request = Request(
            query=Query(text=query, qid=1),
            candidates=[
                Candidate(doc={"text": doc.text}, docid=doc_idx, score=1)
                for doc_idx, doc in enumerate(docs)
            ],
        )

        rankllm_results = self.reranker.rerank(
            request,
            rank_end=len(docs) if rank_end == 0 else rank_end,
            window_size=min(20, len(docs)),
            step=10,
        )

        ranked_docs = []

        for rank, result in enumerate(rankllm_results.candidates, start=rank_start):
            ranked_docs.append(
                Result(
                    document=docs[result.docid],
                    rank=rank,
                )
            )

        return RankedResults(results=ranked_docs, query=query, has_scores=False)

    def score(self):
        print("Listwise ranking models like RankLLM cannot output scores!")
        return None
