"""
hwpx_report_mcp_server.py
==========================
실무 의사결정용 HWPX 표준 보고서 MCP 서버

Claude Desktop 등 MCP 지원 에이전트에 이 파일을 등록하여
HWPX 보고서 생성 도구(tool)를 사용합니다.

설치 방법: README.md 참조
"""

import json
import os
from datetime import date
from mcp.server.fastmcp import FastMCP

# 내부 생성기 임포트
from hwpx_report_generator import create_hwpx_report, DOMAIN_RECRUIT, DOMAIN_TRAINING, DOMAIN_SALES, DOMAIN_BUDGET, DOMAIN_PROJECT

mcp = FastMCP("HWPX-Report-Skill")


@mcp.tool()
def generate_hwpx_report(
    file_path: str,
    title: str,
    domain: str,
    summary: str,
    decision_request: str,
    kpis_json: str,
    tables_json: str,
    notes: str = "",
    reporter: str = "",
    department: str = "",
) -> str:
    """
    실무 의사결정용 HWPX 표준 보고서를 생성합니다.

    Args:
        file_path: 저장할 .hwpx 파일의 절대 경로
                   예) C:/Users/user/Desktop/채용현황_보고서_20260530.hwpx
        title: 보고서 제목 (예: "2분기 채용 현황 보고")
        domain: 보고 도메인 - RECRUIT | TRAINING | SALES | BUDGET | PROJECT
        summary: 보고 요지 (한 줄 핵심 요약)
        decision_request: 의사결정권자에게 요청할 사항 (예: "추가 예산 1,200만원 승인 요청")
        kpis_json: 핵심 지표 목록 (JSON 문자열)
                   형식: [{"label": "채용 목표", "value": "15명"}, ...]
        tables_json: 표 데이터 목록 (JSON 문자열)
                    형식: [{"title": "...", "headers": [...], "rows": [[...]], "note": "..."}]
        notes: 특이사항 및 건의사항 (줄바꿈으로 구분, optional)
        reporter: 작성자명 (optional)
        department: 부서명 (optional)
    """
    try:
        kpis = json.loads(kpis_json) if kpis_json else []
        tables = json.loads(tables_json) if tables_json else []
    except json.JSONDecodeError as e:
        return f"❌ JSON 파싱 오류: {str(e)}\nkpis_json 또는 tables_json 형식을 확인하세요."

    report_data = {
        "domain": domain.upper(),
        "summary": summary,
        "decision_request": decision_request,
        "kpis": kpis,
        "tables": tables,
        "notes": notes,
        "reporter": reporter,
        "department": department,
    }

    return create_hwpx_report(file_path, title, report_data)


@mcp.tool()
def generate_hwpx_recruit_report(
    file_path: str,
    target_headcount: int,
    confirmed_headcount: int,
    total_budget: int,
    spent_budget: int,
    positions_json: str,
    budget_items_json: str,
    notes: str = "",
) -> str:
    """
    채용 현황 HWPX 보고서를 빠르게 생성합니다 (채용 전용 간편 버전).

    Args:
        file_path: 저장할 .hwpx 파일의 절대 경로
        target_headcount: 채용 목표 인원 수
        confirmed_headcount: 최종 확정 인원 수
        total_budget: 채용 총 예산 (원)
        spent_budget: 집행 금액 (원)
        positions_json: 포지션별 현황 (JSON 문자열)
                        [{"name": "백엔드", "target": 5, "confirmed": 3}, ...]
        budget_items_json: 예산 항목별 현황 (JSON 문자열)
                           [{"name": "광고비", "budget": 8000000, "spent": 6200000}, ...]
        notes: 특이사항 (optional)
    """
    try:
        positions = json.loads(positions_json)
        budget_items = json.loads(budget_items_json)
    except json.JSONDecodeError as e:
        return f"❌ JSON 파싱 오류: {str(e)}"

    progress_pct = f"{confirmed_headcount / target_headcount * 100:.1f}%" if target_headcount > 0 else "N/A"
    budget_exec_pct = f"{spent_budget / total_budget * 100:.1f}%" if total_budget > 0 else "N/A"
    remaining = total_budget - spent_budget

    today_str = date.today().strftime('%Y%m%d')

    report_data = {
        "domain": DOMAIN_RECRUIT,
        "summary": f"채용 목표 {target_headcount:,}명 중 {confirmed_headcount:,}명 확정 (진행률 {progress_pct})",
        "decision_request": f"잔여 예산 {remaining:,}원 집행 계획 승인 요청",
        "kpis": [
            {"label": "채용 목표",  "value": f"{target_headcount:,}명"},
            {"label": "확정 인원",  "value": f"{confirmed_headcount:,}명"},
            {"label": "진행률",     "value": progress_pct},
            {"label": "총 예산",    "value": f"{total_budget:,}원"},
            {"label": "집행액",     "value": f"{spent_budget:,}원"},
            {"label": "예산 집행률", "value": budget_exec_pct},
        ],
        "tables": [
            {
                "title": "포지션별 채용 현황",
                "headers": ["포지션", "목표", "확정", "달성률"],
                "rows": [
                    [
                        p["name"],
                        str(p["target"]),
                        str(p["confirmed"]),
                        f"{p['confirmed']/p['target']*100:.1f}%" if p["target"] > 0 else "N/A"
                    ]
                    for p in positions
                ] + [["합계", str(target_headcount), str(confirmed_headcount), progress_pct]],
                "note": f"기준일: {date.today().strftime('%Y-%m-%d')}"
            },
            {
                "title": "채용 예산 집행 현황",
                "headers": ["항목", "예산", "집행액", "잔액", "집행률"],
                "rows": [
                    [
                        b["name"],
                        f"{b['budget']:,}",
                        f"{b['spent']:,}",
                        f"{b['budget']-b['spent']:,}",
                        f"{b['spent']/b['budget']*100:.1f}%" if b["budget"] > 0 else "N/A"
                    ]
                    for b in budget_items
                ] + [["합계",
                       f"{total_budget:,}",
                       f"{spent_budget:,}",
                       f"{remaining:,}",
                       budget_exec_pct]],
                "note": "금액 단위: 원(₩)"
            }
        ],
        "notes": notes,
    }

    title = f"채용 현황 보고서"
    return create_hwpx_report(file_path, title, report_data)


@mcp.tool()
def read_hwpx_text(file_path: str) -> str:
    """
    HWPX 파일에서 텍스트 본문을 추출합니다.

    Args:
        file_path: 읽을 .hwpx 파일의 절대 경로
    """
    import zipfile
    import xml.etree.ElementTree as ET

    try:
        file_path = os.path.abspath(file_path)
        if not os.path.exists(file_path):
            return f"❌ 파일을 찾을 수 없습니다: {file_path}"

        texts = []
        with zipfile.ZipFile(file_path, 'r') as z:
            names = z.namelist()
            section_files = [n for n in names if n.startswith('Contents/section') and n.endswith('.xml')]
            
            for section_file in sorted(section_files):
                data = z.read(section_file)
                root = ET.fromstring(data)
                for elem in root.iter():
                    if elem.tag.endswith('}t') or elem.tag == 't':
                        if elem.text and elem.text.strip():
                            texts.append(elem.text.strip())

        return "\n".join(texts) if texts else "텍스트 내용 없음"

    except Exception as e:
        return f"❌ HWPX 파싱 실패: {str(e)}"


if __name__ == "__main__":
    mcp.run()
