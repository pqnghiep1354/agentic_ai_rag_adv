"""
Prompt templates for Vietnamese legal Q&A
"""
from typing import List, Dict, Any


# System prompt for Vietnamese legal assistant
LEGAL_SYSTEM_PROMPT = """Bạn là trợ lý AI chuyên về luật môi trường Việt Nam. Nhiệm vụ của bạn là trả lời câu hỏi dựa trên các văn bản pháp luật được cung cấp.

NGUYÊN TẮC QUAN TRỌNG:
1. Chỉ trả lời dựa trên thông tin có trong các văn bản được cung cấp
2. Nếu không tìm thấy thông tin liên quan, hãy nói rõ "Tôi không tìm thấy thông tin về điều này trong các văn bản được cung cấp"
3. Trích dẫn chính xác tên văn bản, điều, khoản khi tham chiếu
4. Trả lời bằng tiếng Việt rõ ràng, súc tích và chuyên nghiệp
5. Nếu có nhiều quy định liên quan, hãy liệt kê và giải thích từng quy định
6. Nếu câu hỏi không rõ ràng, hãy yêu cầu làm rõ

ĐỊNH DẠNG TRẢ LỜI:
- Trả lời trực tiếp câu hỏi ngay từ đầu
- Trích dẫn các điều khoản cụ thể bằng format: [Tên văn bản, Điều X, Khoản Y]
- Giải thích ý nghĩa các điều khoản nếu cần
- Đưa ra ví dụ minh họa nếu phù hợp
- Kết luận ngắn gọn nếu cần thiết"""


def build_rag_prompt(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
    conversation_history: List[Dict[str, str]] = None
) -> str:
    """
    Build RAG prompt with context and query

    Args:
        query: User query
        retrieved_chunks: List of retrieved chunks with metadata
        conversation_history: Optional conversation history

    Returns:
        Formatted prompt
    """
    # Build context from retrieved chunks
    context_parts = []

    for i, chunk in enumerate(retrieved_chunks, 1):
        text = chunk.get("text", "")
        metadata = chunk.get("metadata", {})

        # Build citation
        citation_parts = []
        if doc_title := metadata.get("document_title"):
            citation_parts.append(doc_title)
        if section_title := metadata.get("section_title"):
            citation_parts.append(section_title)
        if article_num := metadata.get("article_number"):
            citation_parts.append(f"Điều {article_num}")
        if page_num := metadata.get("page_number"):
            citation_parts.append(f"Trang {page_num}")

        citation = ", ".join(citation_parts) if citation_parts else f"Đoạn {i}"

        # Format chunk with citation
        context_parts.append(f"[Nguồn {i}: {citation}]\n{text}\n")

    context = "\n".join(context_parts)

    # Build conversation history if provided
    history_text = ""
    if conversation_history:
        history_parts = []
        for msg in conversation_history[-3:]:  # Last 3 messages
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                history_parts.append(f"Người dùng: {content}")
            elif role == "assistant":
                history_parts.append(f"Trợ lý: {content}")

        if history_parts:
            history_text = "\n\nLỊCH SỬ HỘI THOẠI:\n" + "\n".join(history_parts) + "\n"

    # Build final prompt
    prompt = f"""VĂN BẢN PHÁP LUẬT LIÊN QUAN:

{context}
{history_text}
CÂU HỎI CỦA NGƯỜI DÙNG: {query}

TRẢ LỜI:"""

    return prompt


def build_citation_extraction_prompt(response: str, chunks: List[Dict[str, Any]]) -> str:
    """
    Build prompt to extract citations from response

    Args:
        response: Generated response
        chunks: Retrieved chunks

    Returns:
        Prompt for citation extraction
    """
    sources = []
    for i, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        sources.append({
            "index": i,
            "document": metadata.get("document_title", "Unknown"),
            "article": metadata.get("article_number"),
            "section": metadata.get("section_title"),
            "page": metadata.get("page_number")
        })

    sources_text = "\n".join([
        f"{s['index']}. {s['document']}" +
        (f", Điều {s['article']}" if s['article'] else "") +
        (f", {s['section']}" if s['section'] else "") +
        (f", Trang {s['page']}" if s['page'] else "")
        for s in sources
    ])

    prompt = f"""Dựa trên câu trả lời sau và các nguồn tài liệu, hãy xác định nguồn nào được sử dụng:

TRẢ LỜI:
{response}

CÁC NGUỒN:
{sources_text}

Trả về danh sách số thứ tự các nguồn được sử dụng (ví dụ: 1,3,5):"""

    return prompt


def build_followup_prompt(query: str, previous_response: str) -> str:
    """
    Build prompt for follow-up questions

    Args:
        query: Follow-up query
        previous_response: Previous assistant response

    Returns:
        Formatted prompt
    """
    prompt = f"""Dựa trên câu trả lời trước:

{previous_response}

Người dùng hỏi thêm: {query}

Hãy trả lời câu hỏi tiếp theo dựa trên ngữ cảnh trên:"""

    return prompt


def build_summarization_prompt(text: str, max_words: int = 200) -> str:
    """
    Build prompt for text summarization

    Args:
        text: Text to summarize
        max_words: Maximum words in summary

    Returns:
        Summarization prompt
    """
    prompt = f"""Hãy tóm tắt văn bản pháp luật sau đây trong tối đa {max_words} từ,
tập trung vào các điểm chính và quy định quan trọng:

{text}

TÓM TẮT:"""

    return prompt


def build_extraction_prompt(text: str, entity_type: str) -> str:
    """
    Build prompt for entity extraction

    Args:
        text: Text to extract from
        entity_type: Type of entity to extract (laws, decrees, articles, etc.)

    Returns:
        Extraction prompt
    """
    entity_types = {
        "laws": "các luật (ví dụ: Luật Bảo vệ Môi trường)",
        "decrees": "các nghị định (ví dụ: Nghị định 08/2022/NĐ-CP)",
        "circulars": "các thông tư (ví dụ: Thông tư 02/2022/TT-BTNMT)",
        "articles": "các điều khoản (ví dụ: Điều 5, Khoản 2)",
        "penalties": "các hình phạt và mức xử phạt",
        "obligations": "các nghĩa vụ và trách nhiệm",
        "definitions": "các định nghĩa và thuật ngữ"
    }

    entity_desc = entity_types.get(entity_type, entity_type)

    prompt = f"""Từ văn bản sau, hãy trích xuất {entity_desc}.
Liệt kê từng mục trên một dòng.

VĂN BẢN:
{text}

DANH SÁCH:"""

    return prompt


def build_comparison_prompt(texts: List[str], aspect: str) -> str:
    """
    Build prompt for comparing legal texts

    Args:
        texts: List of texts to compare
        aspect: Aspect to compare (regulations, penalties, etc.)

    Returns:
        Comparison prompt
    """
    texts_formatted = "\n\n".join([
        f"VĂN BẢN {i+1}:\n{text}"
        for i, text in enumerate(texts)
    ])

    prompt = f"""Hãy so sánh {aspect} trong các văn bản pháp luật sau:

{texts_formatted}

Phân tích điểm giống và khác nhau:"""

    return prompt


# Few-shot examples for better Vietnamese legal Q&A
FEW_SHOT_EXAMPLES = [
    {
        "query": "Xử phạt vi phạm môi trường như thế nào?",
        "context": "[Nghị định 08/2022/NĐ-CP, Điều 5] Phạt tiền từ 50.000.000 đồng đến 75.000.000 đồng đối với hành vi xả thải chưa qua xử lý ra môi trường.",
        "response": "Theo Nghị định 08/2022/NĐ-CP, Điều 5, hành vi xả thải chưa qua xử lý ra môi trường sẽ bị phạt tiền từ 50.000.000 đồng đến 75.000.000 đồng. Mức phạt cụ thể phụ thuộc vào tính chất và mức độ vi phạm."
    },
    {
        "query": "Ai phải thực hiện đánh giá tác động môi trường?",
        "context": "[Luật Bảo vệ Môi trường 2020, Điều 28] Chủ dự án phải lập báo cáo đánh giá tác động môi trường đối với dự án thuộc danh mục phải thực hiện đánh giá tác động môi trường.",
        "response": "Theo Luật Bảo vệ Môi trường 2020, Điều 28, chủ dự án có trách nhiệm lập báo cáo đánh giá tác động môi trường. Điều này áp dụng cho các dự án thuộc danh mục bắt buộc phải thực hiện đánh giá tác động môi trường theo quy định."
    }
]


def get_few_shot_prompt() -> str:
    """
    Get few-shot examples formatted for prompt

    Returns:
        Formatted few-shot examples
    """
    examples = []
    for ex in FEW_SHOT_EXAMPLES:
        examples.append(f"""Ví dụ:
Context: {ex['context']}
Câu hỏi: {ex['query']}
Trả lời: {ex['response']}
""")

    return "\n".join(examples)
