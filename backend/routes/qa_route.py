import json

from flask import Blueprint, Response, jsonify, request, stream_with_context

from models.database import FaultRecord
from services.data_acquisition import daq_system
from services.rag_service import rag_system

qa_bp = Blueprint("qa_bp", __name__)


def get_latest_fault():
    record = FaultRecord.query.order_by(FaultRecord.timestamp.desc()).first()
    if not record:
        return None
    return {
        "fault_type": record.fault_type,
        "severity": record.severity,
        "probability": round((record.probability or 0) * 100, 1),
        "advice": record.advice,
        "timestamp": record.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
    }


@qa_bp.route("/ask", methods=["POST"])
def ask_question():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "请提供问题内容。"}), 400

    current_status = data.get("current_status") or daq_system.fuse_data()
    latest_fault = get_latest_fault()
    answer_mode = data.get("answer_mode") or "model_first"
    deep_thinking = data.get("deep_thinking")
    use_deep_thinking = answer_mode == "model_first" if deep_thinking is None else bool(deep_thinking)
    result = rag_system.generate_answer_with_status(
        question=question,
        status=current_status,
        latest_fault=latest_fault,
        deep_thinking=use_deep_thinking,
    )

    return jsonify({
        "question": question,
        "answer": result["answer"],
        "source_documents": result["sources"],
        "intent": result["intent"],
        "confidence": result["confidence"],
        "risk_level": result["risk_level"],
        "suggested_questions": result["suggested_questions"],
        "latest_fault": latest_fault,
        "deep_thinking": result.get("deep_thinking", False),
        "engine": result.get("engine", "local_expert"),
        "model": result.get("model"),
        "api_status": result.get("api_status"),
        "answer_mode": answer_mode,
    })


@qa_bp.route("/ask_stream", methods=["POST"])
def ask_question_stream():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "请提供问题内容。"}), 400

    current_status = data.get("current_status") or daq_system.fuse_data()
    latest_fault = get_latest_fault()
    answer_mode = data.get("answer_mode") or "model_first"
    deep_thinking = data.get("deep_thinking")
    use_deep_thinking = answer_mode == "model_first" if deep_thinking is None else bool(deep_thinking)

    def sse(event, payload):
        return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    @stream_with_context
    def generate():
        try:
            for event, payload in rag_system.stream_answer_with_status(
                question=question,
                status=current_status,
                latest_fault=latest_fault,
                deep_thinking=use_deep_thinking,
            ):
                if event == "done":
                    payload = {
                        **payload,
                        "question": question,
                        "latest_fault": latest_fault,
                        "answer_mode": answer_mode,
                    }
                yield sse(event, payload)
        except Exception as exc:
            yield sse("error", {"error": f"流式回答失败：{exc}"})

    return Response(generate(), mimetype="text/event-stream")
