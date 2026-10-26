"""AI Service Layer supporting Deterministic Rule-Based Mock, llama.cpp, and Ollama."""

import abc
import json
import re
import time
from typing import List, Optional, Tuple
import httpx
from backend.models import ExtractedTask, Priority, DeadlineConfidence
from backend.services.date_parser import date_parser
from backend.config import settings

# Action verb triggers
ACTION_VERBS = [
    "finish", "complete", "check", "email", "mail", "send", "review",
    "investigate", "fix", "buy", "purchase", "order", "write", "draft",
    "call", "schedule", "read", "test", "update", "verify", "debug",
    "clean", "organize", "prepare", "deploy", "record", "inspect"
]

CATEGORY_KEYWORDS = {
    "communication": ["email", "mail", "call", "message", "chat", "mentor", "meeting", "reach out", "contact"],
    "project": ["readme", "code", "model", "bug", "git", "test", "deploy", "accuracy", "evaluation", "repo", "project", "build"],
    "errands": ["buy", "groceries", "shop", "store", "order", "pick up", "deliver", "market"],
    "study": ["study", "read", "book", "paper", "learn", "course", "lecture", "tutorial"],
}


class BaseAIProvider(abc.ABC):
    """Abstract interface for task extraction providers."""

    @abc.abstractmethod
    async def extract_tasks(self, raw_thought: str) -> Tuple[List[ExtractedTask], str, bool]:
        """
        Extract tasks from raw thought.
        Returns:
            (tasks, model_or_engine_name, is_mock_boolean)
        """
        pass


class DevMockProvider(BaseAIProvider):
    """
    Deterministic rule-based task extractor.
    Identifies multiple tasks, infers priority, resolves dates, and suggests concrete next steps.
    Never hallucinates deadlines and strictly sets is_mock=True.
    """

    async def extract_tasks(self, raw_thought: str) -> Tuple[List[ExtractedTask], str, bool]:
        text = raw_thought.strip()
        tasks: List[ExtractedTask] = []

        # 1. Normalize bullet points or line breaks
        lines = [line.strip("- *• \t\r") for line in text.splitlines() if line.strip()]
        
        # If single paragraph, split by clauses
        clauses = []
        if len(lines) == 1:
            raw_clauses = re.split(
                r"(?<=[.!?])\s+|\s+(?:and\s+then|also|additionally)\s+|;\s*|,\s*(?:and\s+)?(?=(?:need to|have to|must|should|remember to|finish|check|email|mail|buy|review|investigate|call|write|prepare|schedule)\b)|\s+and\s+(?=(?:need to|have to|must|should|remember to|finish|check|email|mail|buy|review|investigate|call|write|prepare|schedule)\b)",
                lines[0],
                flags=re.IGNORECASE,
            )
            clauses = [c.strip() for c in raw_clauses if c.strip()]
        else:
            clauses = lines

        # Check for global priority cues like "I should probably do the results first"
        global_high_cues = []
        for c in clauses:
            low_c = c.lower()
            if "first" in low_c or "urgently" in low_c:
                # Find what it refers to
                words = re.findall(r"\b\w+\b", low_c)
                global_high_cues.extend(words)

        for clause in clauses:
            low_clause = clause.lower()

            # Skip meta statements that only describe ordering or feelings
            if re.match(r"^(i\s+should\s+probably\s+do|i\s+want\s+to\s+do|first\s+thing\s+is|that\'?s\s+all)\b", low_clause) and not any(v in low_clause for v in ["finish", "check", "email", "buy", "write", "call"]):
                continue

            # Strip leading fillers
            cleaned = re.sub(r"^(i\s+need\s+to|i\s+have\s+to|i\s+must|i\s+should|remember\s+to|please|don\'?t\s+forget\s+to)\s+", "", clause, flags=re.IGNORECASE).strip()
            if not cleaned or len(cleaned) < 3:
                continue

            # Extract deadline using timezone-aware date parser
            iso_deadline, deadline_expr, deadline_conf = date_parser.extract_deadline(cleaned)

            # Clean clause of the date expression for a cleaner title
            clean_title = cleaned
            if deadline_expr:
                # Remove deadline phrase from title
                clean_title = re.sub(re.escape(deadline_expr), "", clean_title, flags=re.IGNORECASE).strip(" ,.-")

            # Capitalize first letter of title
            clean_title = clean_title[0].upper() + clean_title[1:] if clean_title else cleaned

            # Determine Priority
            priority = Priority.MEDIUM
            if any(term in low_clause for term in ["urgent", "urgently", "asap", "critical", "important", "must do first"]):
                priority = Priority.HIGH
            elif any(term in low_clause for term in ["when i have time", "later", "eventually", "low priority", "if possible", "someday"]):
                priority = Priority.LOW
            elif any(term in low_clause and term in global_high_cues for term in ["results", "model", "battery", "first"]):
                priority = Priority.HIGH

            # Determine Category
            category = "general"
            for cat, keywords in CATEGORY_KEYWORDS.items():
                if any(kw in low_clause for kw in keywords):
                    category = cat
                    break

            # Suggest concrete next step
            suggested_step = self._generate_suggested_step(clean_title, category)

            task = ExtractedTask(
                title=clean_title,
                description=f"Extracted from: \"{clause.strip()}\"",
                priority=priority,
                deadline=iso_deadline,
                deadline_expression=deadline_expr,
                deadline_confidence=deadline_conf,
                deadline_confirmed=False,
                suggested_next_step=suggested_step,
                category=category,
            )
            tasks.append(task)

        # Fallback if no task clause was separated
        if not tasks:
            iso_deadline, deadline_expr, deadline_conf = date_parser.extract_deadline(text)
            tasks.append(
                ExtractedTask(
                    title=text[:100],
                    description=text,
                    priority=Priority.MEDIUM,
                    deadline=iso_deadline,
                    deadline_expression=deadline_expr,
                    deadline_confidence=deadline_conf,
                    deadline_confirmed=False,
                    suggested_next_step="Review the captured item and define the first concrete action.",
                    category="general",
                )
            )

        return tasks, "Rule-Based Deterministic Engine", True

    def _generate_suggested_step(self, title: str, category: str) -> str:
        low = title.lower()
        if "readme" in low:
            return "Review installation instructions and project documentation."
        if "battery" in low or "result" in low or "accuracy" in low or "metric" in low:
            return "Review evaluation metrics and record the findings."
        if "email" in low or "mail" in low or "mentor" in low:
            return "Draft the email and review it before sending."
        if "groceries" in low or "buy" in low:
            return "Make a specific shopping checklist and locate needed supplies."
        if "investigate" in low or "error" in low or "bug" in low:
            return "Inspect error logs and reproduce the failure locally."
        if category == "project":
            return "Open codebase, review requirements, and outline implementation steps."
        return "Define the initial acceptance criteria and begin work."


class LlamaCppProvider(BaseAIProvider):
    """
    llama.cpp / llama-server provider.
    Talks to OpenAI-compatible endpoint with strict JSON schema response.
    """

    def __init__(self, endpoint: str, timeout: int = 45):
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    async def extract_tasks(self, raw_thought: str) -> Tuple[List[ExtractedTask], str, bool]:
        url = f"{self.endpoint}/v1/chat/completions"
        system_prompt = (
            "You are SlowSloth edge task extraction engine. "
            "Extract structured tasks from user thoughts. Output strictly valid JSON conforming to this schema:\n"
            "{\"tasks\": [{\"title\": str, \"description\": str, \"priority\": \"low\"|\"medium\"|\"high\", "
            "\"deadline\": str|null, \"deadline_expression\": str|null, \"deadline_confidence\": \"exact\"|\"suggested\"|\"unknown\", "
            "\"suggested_next_step\": str, \"category\": str}]}\n"
            "Never invent deadlines if none are present in the text. Return only JSON."
        )

        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_thought},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            parsed_json = json.loads(content)
            tasks_data = parsed_json.get("tasks", [])
            tasks = [ExtractedTask(**t) for t in tasks_data]
            model_name = data.get("model", "llama-cpp-gemma")
            return tasks, model_name, False


class OllamaProvider(BaseAIProvider):
    """Ollama API provider using /api/chat with format='json'."""

    def __init__(self, endpoint: str, model: str, timeout: int = 45):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def extract_tasks(self, raw_thought: str) -> Tuple[List[ExtractedTask], str, bool]:
        url = f"{self.endpoint}/api/chat"
        system_prompt = (
            "Extract structured tasks into JSON: {\"tasks\": [{\"title\": string, \"description\": string, "
            "\"priority\": \"low\"|\"medium\"|\"high\", \"deadline\": null, \"deadline_expression\": null, "
            "\"deadline_confidence\": \"unknown\", \"suggested_next_step\": string, \"category\": string}]}"
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_thought},
            ],
            "format": "json",
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["message"]["content"]
            parsed_json = json.loads(content)
            tasks_data = parsed_json.get("tasks", [])
            tasks = [ExtractedTask(**t) for t in tasks_data]
            return tasks, self.model, False


class AIService:
    """Central AI service managing providers, fallback policies, and response validation."""

    def __init__(self):
        self.mock_provider = DevMockProvider()

    def get_provider(self) -> BaseAIProvider:
        backend = settings.AI_BACKEND.lower()
        if backend == "llama_cpp":
            return LlamaCppProvider(
                endpoint=settings.INFERENCE_ENDPOINT,
                timeout=settings.INFERENCE_TIMEOUT_SEC,
            )
        elif backend == "ollama":
            return OllamaProvider(
                endpoint=settings.INFERENCE_ENDPOINT,
                model=settings.AI_MODEL_IDENTIFIER,
                timeout=settings.INFERENCE_TIMEOUT_SEC,
            )
        return self.mock_provider

    async def extract_tasks(self, raw_thought: str) -> Tuple[List[ExtractedTask], str, str, bool, float]:
        """
        Extract tasks with bounded fallback and latency tracking.
        Returns:
            (tasks, backend_name, model_identifier, is_mock, latency_ms)
        """
        start_time = time.perf_counter()
        provider = self.get_provider()
        backend_name = settings.AI_BACKEND

        try:
            tasks, model_id, is_mock = await provider.extract_tasks(raw_thought)
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return tasks, backend_name, model_id, is_mock, round(latency_ms, 2)
        except Exception as e:
            if settings.ALLOW_DEV_FALLBACK:
                tasks, model_id, is_mock = await self.mock_provider.extract_tasks(raw_thought)
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                return tasks, "dev_mock", f"Fallback ({type(e).__name__}): Rule Engine", True, round(latency_ms, 2)
            raise RuntimeError(f"AI extraction failed and dev fallback is disabled: {str(e)}") from e


ai_service = AIService()
