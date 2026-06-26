"""Flask 진입점.

Routes:
  GET  /          → 입력 폼
  POST /analyze   → 그래프 실행 (interrupt까지)
  GET  /confirm   → 기업 후보 선택 화면
  POST /confirm   → interrupt resume → 분석 완료
  GET  /result    → 최종 리포트 표시
  GET  /download  → HTML 리포트 다운로드
  GET  /reset     → 세션 초기화
"""
import io
import os
import uuid

from flask import Flask, render_template, request, redirect, url_for, session, send_file
from langgraph.types import Command

from graph.orchestrator import graph
from graph.state import IntelState

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))


def _graph_config() -> dict:
    return {"configurable": {"thread_id": session["thread_id"]}}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    session["thread_id"] = str(uuid.uuid4())

    initial_state = IntelState(
        business_field=request.form["business_field"],
        query_name=request.form["query_name"],
        company_candidates=[],
        confirmed_company=None,
        keywords=[],
        news=[],
        patents=[],
        finance={},
        cross_validation={},
        chapters={},
        final_report_html="",
        errors=[],
    )

    for event in graph.stream(initial_state, _graph_config(), stream_mode="updates"):
        if "__interrupt__" in event:
            session["candidates"] = event["__interrupt__"][0].value["candidates"]
            return redirect(url_for("confirm"))

    return redirect(url_for("result"))


@app.route("/confirm", methods=["GET", "POST"])
def confirm():
    candidates = session.get("candidates", [])

    if request.method == "GET":
        return render_template("confirm.html", candidates=candidates)

    chosen = candidates[int(request.form["chosen_idx"])]

    for _ in graph.stream(Command(resume=chosen), _graph_config(), stream_mode="updates"):
        pass

    return redirect(url_for("result"))


@app.route("/result")
def result():
    final = graph.get_state(_graph_config()).values
    return render_template("result.html", final=final)


@app.route("/download")
def download():
    final = graph.get_state(_graph_config()).values
    company = final.get("confirmed_company", {}).get("name", "report")
    html = final.get("final_report_html", "")
    return send_file(
        io.BytesIO(html.encode("utf-8")),
        mimetype="text/html",
        as_attachment=True,
        download_name=f"intel_{company}.html",
    )


@app.route("/reset")
def reset():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
