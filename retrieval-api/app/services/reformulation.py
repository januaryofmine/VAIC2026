"""Optional LLM query rewrite for context-aware retrieval.

Falls back to the original question whenever no provider is configured or the LLM
call fails — so retrieval works with or without an API key.
"""

import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Bạn viết lại câu hỏi của người dùng thành một truy vấn tìm kiếm ngắn gọn (1-2 câu) bằng tiếng Việt.
Quy tắc:
- Giải quyết đại từ / tham chiếu dựa trên lịch sử hội thoại (vd "điều đó", "khoản này")
- Giữ nguyên thuật ngữ pháp lý quan trọng (số Điều, Khoản, tên văn bản)
- Bỏ phần thừa mang tính hội thoại
- CHỈ trả về câu truy vấn đã viết lại, không giải thích"""


def reformulate_query(
    question: str,
    *,
    model: str,
    provider: str = "none",
    history: list[dict[str, str]] | None = None,
    anthropic_api_key: str = "",
) -> str:
    if provider != "anthropic" or not anthropic_api_key:
        return question  # passthrough: no LLM configured

    try:
        import anthropic

        messages = list(history or []) + [{"role": "user", "content": question}]
        client = anthropic.Anthropic(api_key=anthropic_api_key)
        response = client.messages.create(
            model=model,
            max_tokens=256,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        rewritten = response.content[0].text.strip()
        # The model sometimes answers conversationally ("Tôi cần thêm thông tin…")
        # instead of returning a query. A real query is short and single-line;
        # anything else pollutes retrieval, so fall back to the original question.
        if not rewritten or len(rewritten) > 160 or "\n" in rewritten:
            logger.info("reformulation output not query-like, using original question")
            return question
        return rewritten
    except Exception as e:  # any failure → don't block retrieval
        logger.warning("Reformulation failed, using original question: %s", e)
        return question
