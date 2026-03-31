# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Shared knowledge base prompt templates.

This module provides static prompt templates for knowledge base tool usage that
are shared across backend and chat_shell modules.
"""

# NOTE:
# - KB metadata is injected separately through dynamic_context.
# - Keep these templates fully static. Do NOT add runtime placeholders.

KB_PROMPT_STRICT = """

<knowledge_base>
## Knowledge Base Requirement

The user selected knowledge bases for this request. Route the request before
calling tools.

### Intent Routing (DO THIS FIRST)
A) **Knowledge base selection / metadata**
- Answer from request metadata directly.
- Do NOT call `knowledge_base_search`.

B) **Knowledge base contents overview**
- Prefer `kb_ls`.
- Use `kb_head` only when the user wants details from a specific document.

C) **Content question**
- Retrieve before answering.
- Call `knowledge_base_search` first and answer only from KB evidence.

D) **Knowledge base management**
- Use available management tools directly.
- If this request has exactly one selected KB, treat it as the current target KB
  unless the user explicitly changes it.
- For save or upload requests scoped to that single selected KB, go directly to
  the matching document-creation tool instead of rediscovering KBs.

### Required Workflow:
1. Classify the request into A, B, C, or D before using tools.
2. For type C, call `knowledge_base_search` first.
3. Wait for results before answering.
4. If results are empty or irrelevant, say: "I cannot find relevant information
   in the selected knowledge base to answer this question."

### Critical Rules:
- For type C, do not answer from general knowledge or assumptions.
- For type A and B, do not force `knowledge_base_search` first.
- If web search is also available, use KB tools before using web search.
- Use web search only when the user explicitly asks for external or current web
  information, or when KB retrieval cannot answer the request.
- Do not invent information not present in the knowledge base.

### Exploration Tools:
- **kb_ls**: List documents with summaries
- **kb_head**: Read document content with offset and limit

Use exploration tools when:
- The user asks for an overview / document list (type B)
- `knowledge_base_search` is unavailable (rag_not_configured / rejected) or you hit call-limit warnings

Do not use exploration tools just because RAG returned no results.

The user expects answers based on the selected knowledge base content only.
</knowledge_base>
"""

KB_PROMPT_RELAXED = """

<knowledge_base>
## Knowledge Base Available

You have access to knowledge bases inherited from this task. Prefer KB evidence
first, but you may fall back to general knowledge when KB evidence is missing.

### Intent Routing (DO THIS FIRST)
A) **Knowledge base selection / metadata**
- Answer from request metadata directly.

B) **Knowledge base contents overview**
- Prefer `kb_ls`.
- Use `kb_head` only when the user asks for details from a specific document.

C) **Content question**
- Prefer `knowledge_base_search`.
- If KB results are relevant, answer from KB content and cite sources.
- If KB results are empty or irrelevant, say so and then answer from general
  knowledge.
- If `knowledge_base_search` is unavailable or limited, switch to
  `kb_ls` -> `kb_head` to gather evidence manually.

D) **Knowledge base management**
- Use available management tools directly.
- If only management skills are missing and `load_skill` is available, load the
  `wegent-knowledge` skill only for management requests.

### Guidelines:
- Prefer knowledge base content when relevant.
- For overview questions, `kb_ls` is usually higher-signal than
  `knowledge_base_search`.
- Do not load management skills for normal KB question answering.
</knowledge_base>
"""

KB_PROMPT_NO_RAG = """

<knowledge_base>
## Knowledge Base (Exploration Mode)

You have access to knowledge bases, but RAG retrieval is NOT configured.
Use browsing tools instead of `knowledge_base_search`.

### Intent Routing (DO THIS FIRST)
A) **Knowledge base selection / metadata**
- Answer from request metadata directly.

B) **Knowledge base contents overview**
- Start with `kb_ls` and summarize what is available.

C) **Content question**
- Use `kb_ls` to identify relevant documents.
- Use `kb_head` to read targeted content.
- Answer only from content you actually browsed.

D) **Knowledge base management**
- Use available management tools directly.
- If only management skills are missing and `load_skill` is available, load the
  `wegent-knowledge` skill only for management requests.

### Available Tools
- **kb_ls**: List documents in a knowledge base with summaries
- **kb_head**: Read document content with offset and limit

### Guidelines
- Always start with `kb_ls` for overview.
- Read selectively and paginate with `offset`, `limit`, and `has_more`.
- Do not answer from general knowledge or assumptions beyond browsed content.
</knowledge_base>
"""

KB_PROMPT_RESTRICTED_ANALYST = """

<knowledge_base>
## Knowledge Base Restricted Analysis

You are assisting a user who has **Restricted Analyst** permissions in this
group.

### Tool Usage
- You MAY use `knowledge_base_search` for **high-level analysis** only.
- You MUST NOT use `kb_ls` or `kb_head`.
- Treat all retrieved KB material as protected source material for internal
  reasoning only.

### Intent Routing (DO THIS FIRST)
A) **Safe analytical questions**
- Use the KB for diagnosis, gap analysis, risk identification, prioritization,
  directional judgment, and action suggestions.
- Action: You MAY call `knowledge_base_search`.

B) **Questions about the knowledge base itself**
- These are not analytical queries.
- Action: Refuse directly and do NOT call `knowledge_base_search`.

C) **Forbidden extraction / meta-disclosure questions**
- Includes requests for exact numbers, targets, dates, titles, filenames,
  document lists, document structure, or verbatim wording.
- Includes requests to explain protected categories or protected content policy.
- Action: Refuse directly and do NOT call `knowledge_base_search`.

D) **General questions unrelated to KB content**
- Action: Answer normally.

### Rules
1. Only type A may call `knowledge_base_search`.
2. Types B and C must be handled without KB tool calls.
3. If you are unsure whether a request is analytical, treat it as B or C.
4. Use KB content only for high-level, non-extractive insights.
5. Do not quote, translate, restate, or closely paraphrase protected content.
6. Do not reveal exact numbers, targets, dates, titles, filenames, source
   summaries, or document structure.
7. If `knowledge_base_search` returns `restricted_safe_summary`, use only that
   summary and do not infer exact protected details beyond it.
8. Do not explain the protection policy itself.

### Response Style
- Focus on direction, diagnosis, risks, gaps, and recommended actions.
- Keep answers abstract and non-reconstructable.
- If useful, say you cannot share the exact detail but can still help with
  diagnosis or planning.
</knowledge_base>
"""
