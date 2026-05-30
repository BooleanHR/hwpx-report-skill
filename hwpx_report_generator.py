"""
hwpx_report_generator.py
========================
실무 의사결정용 HWPX 표준 보고서 생성기

채용·교육·영업·예산·프로젝트 도메인에서 경영진 의사결정을 지원하는
구조화된 보고서를 HWPX 형식으로 직접 생성합니다.

HWPX 표준: OWPML (Open Word Processing Markup Language)
기반 구조: ZIP 컨테이너 + XML 내부 파일
참조: https://www.hancom.com/etc/hwpDownload.do
"""

import os
import zipfile
from datetime import date
from typing import Optional


# ─────────────────────────────────────────────────────────────
# 도메인 상수 정의
# ─────────────────────────────────────────────────────────────
DOMAIN_RECRUIT  = "RECRUIT"   # 채용 기획·운영
DOMAIN_TRAINING = "TRAINING"  # 교육·훈련 운영
DOMAIN_SALES    = "SALES"     # 영업 실적·계획
DOMAIN_BUDGET   = "BUDGET"    # 예산·집행 현황
DOMAIN_PROJECT  = "PROJECT"   # 프로젝트 현황

# 스타일 색상 상수 (무채색 + 파란색 포인트 1종)
COLOR_PRIMARY   = "1565C0"    # 파란색 포인트 컬러 (헤더, 강조)
COLOR_TEXT      = "1A1A1A"    # 기본 텍스트 (진한 검정)
COLOR_SUBTEXT   = "4A4A4A"    # 보조 텍스트 (진회색)
COLOR_BG_LIGHT  = "F5F5F5"    # 연한 배경 (무채색)


# ─────────────────────────────────────────────────────────────
# 수치 검증 유틸리티
# ─────────────────────────────────────────────────────────────
def validate_sum(items: list[dict], amount_key: str, declared_total: float) -> tuple[bool, float]:
    """
    세부 항목 합계와 선언된 합계를 비교 검증한다.
    
    Returns:
        (is_valid: bool, calculated_total: float)
    """
    calculated = sum(float(str(item.get(amount_key, 0)).replace(',', '').replace('₩', '').strip()) for item in items)
    return abs(calculated - declared_total) < 0.01, calculated


def format_number(n: float, unit: str = "원") -> str:
    """숫자를 천 단위 구분자(,)와 단위로 포맷한다."""
    return f"{int(n):,}{unit}"


def format_percentage(numerator: float, denominator: float, decimal: int = 1) -> str:
    """비율을 퍼센트 문자열로 반환한다. 분모가 0이면 'N/A' 반환."""
    if denominator == 0:
        return "N/A"
    return f"{(numerator / denominator * 100):.{decimal}f}%"


# ─────────────────────────────────────────────────────────────
# HWPX XML 빌더
# ─────────────────────────────────────────────────────────────
class HwpxXmlBuilder:
    """HWPX 내부 XML 파일들을 생성하는 빌더 클래스."""

    @staticmethod
    def mimetype() -> str:
        return "application/hwp+zip"

    @staticmethod
    def container_xml() -> str:
        return '''<?xml version="1.0" encoding="UTF-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles>
    <rootfile full-path="Contents/content.hpf" media-type="application/hwp+xml"/>
  </rootfiles>
</container>'''

    @staticmethod
    def content_hpf(title: str) -> str:
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.hancom.co.kr/HPXML/2011/HPF" version="1.0" unique-identifier="id">
  <metadata>
    <title>{title}</title>
    <language>ko</language>
  </metadata>
  <manifest>
    <item id="header" href="header.xml" media-type="application/hwp+xml"/>
    <item id="section0" href="section0.xml" media-type="application/hwp+xml"/>
  </manifest>
  <spine>
    <itemref idref="section0"/>
  </spine>
</package>'''

    @staticmethod
    def header_xml() -> str:
        return '''<?xml version="1.0" encoding="UTF-8"?>
<hh:hhpml xmlns:hh="http://www.hancom.co.kr/HPXML/2011/Core" version="1.0">
  <hh:head>
    <hh:beginNumber page="1" footnote="1" endnote="1" picture="1" table="1" equation="1"/>
  </hh:head>
</hh:hhpml>'''

    @staticmethod
    def paragraph(text: str) -> str:
        """단락(paragraph) XML 블록 생성."""
        safe_text = (text
                     .replace('&', '&amp;')
                     .replace('<', '&lt;')
                     .replace('>', '&gt;')
                     .replace('"', '&quot;'))
        return f'  <hp:p><hp:run><hp:t>{safe_text}</hp:t></hp:run></hp:p>\n'

    @staticmethod
    def table(headers: list[str], rows: list[list[str]], note: Optional[str] = None) -> str:
        """
        표(table) XML 블록 생성.
        
        Args:
            headers: 헤더 열 목록
            rows: 데이터 행 목록 (2차원 리스트)
            note: 표 하단 주석 (출처 등)
        """
        def safe(t):
            return (str(t)
                    .replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;'))

        col_count = len(headers)
        row_count = len(rows) + 1  # 헤더 포함

        xml = f'  <hp:tbl>\n'
        xml += f'    <hp:tblPr rowCount="{row_count}" colCount="{col_count}" cellSpacing="0"/>\n'

        # 헤더 행
        xml += '    <hp:tr>\n'
        for h in headers:
            xml += (f'      <hp:tc>\n'
                    f'        <hp:p><hp:run><hp:t>{safe(h)}</hp:t></hp:run></hp:p>\n'
                    f'      </hp:tc>\n')
        xml += '    </hp:tr>\n'

        # 데이터 행
        for row in rows:
            xml += '    <hp:tr>\n'
            for cell in row:
                xml += (f'      <hp:tc>\n'
                        f'        <hp:p><hp:run><hp:t>{safe(cell)}</hp:t></hp:run></hp:p>\n'
                        f'      </hp:tc>\n')
            xml += '    </hp:tr>\n'

        xml += '  </hp:tbl>\n'
        return xml

    @staticmethod
    def section_xml(body: str) -> str:
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<hp:section xmlns:hp="http://www.hancom.co.kr/HPXML/2011/Paragraph">
{body}</hp:section>'''


# ─────────────────────────────────────────────────────────────
# 보고서 본문 생성기
# ─────────────────────────────────────────────────────────────
class ReportBodyBuilder:
    """
    도메인별 보고서 본문 XML을 생성하는 빌더.
    
    report_data 스키마:
    {
        "domain": "RECRUIT|TRAINING|SALES|BUDGET|PROJECT",
        "summary": "보고 요지 한 줄",
        "decision_request": "의사결정 요청 사항",
        "kpis": [{"label": str, "value": str}],   # 4~6개
        "tables": [
            {
                "title": str,
                "headers": [str, ...],
                "rows": [[str, ...], ...],
                "note": str  # optional
            }
        ],
        "notes": "특이사항 및 건의사항",
        "reporter": "작성자명 (optional)",
        "department": "부서명 (optional)"
    }
    """

    def __init__(self, title: str, report_data: dict):
        self.title = title
        self.data = report_data
        self.builder = HwpxXmlBuilder()
        self.today = date.today().strftime('%Y년 %m월 %d일')

    def build(self) -> str:
        p = self.builder.paragraph
        t = self.builder.table
        body = ''

        # ── 1. 문서 헤더 ──────────────────────────────────────
        body += p(f'■ {self.title}')
        reporter_line = f'보고일: {self.today}'
        if self.data.get('reporter'):
            reporter_line += f'  |  작성: {self.data["reporter"]}'
        if self.data.get('department'):
            reporter_line += f'  |  부서: {self.data["department"]}'
        body += p(reporter_line)
        body += p('')

        # ── 2. 핵심 요약 블록 (BLUF) ──────────────────────────
        body += p('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        body += p(f'▶ 보고 요지: {self.data.get("summary", "")}')
        body += p(f'▶ 의사결정 요청: {self.data.get("decision_request", "")}')
        body += p('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        body += p('')

        # ── 3. KPI 요약표 ────────────────────────────────────
        kpis = self.data.get('kpis', [])
        if kpis:
            body += p('[핵심 지표 요약 (Key Performance Indicators)]')
            body += t(
                [k['label'] for k in kpis],
                [[k['value'] for k in kpis]]
            )
            body += p('')

        # ── 4. 도메인 표들 ────────────────────────────────────
        for tbl in self.data.get('tables', []):
            body += p(f'[{tbl["title"]}]')
            body += t(tbl['headers'], tbl['rows'])
            if tbl.get('note'):
                body += p(f'※ {tbl["note"]}')
            body += p('')

        # ── 5. 특이사항 ───────────────────────────────────────
        if self.data.get('notes'):
            body += p('■ 특이사항 및 건의사항')
            for line in self.data['notes'].split('\n'):
                if line.strip():
                    body += p(f'  · {line.strip()}')
            body += p('')

        # ── 6. 문서 하단 ──────────────────────────────────────
        body += p('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        body += p(f'※ 본 보고서는 {self.today} 기준으로 작성되었습니다.')
        body += p('※ 수치는 내부 데이터 기준이며, 외부 공개를 금합니다.')

        return body


# ─────────────────────────────────────────────────────────────
# 메인 생성 함수 (공개 API)
# ─────────────────────────────────────────────────────────────
def create_hwpx_report(
    file_path: str,
    title: str,
    report_data: dict
) -> str:
    """
    실무 의사결정용 HWPX 표준 보고서를 생성한다.

    Args:
        file_path (str): 저장할 .hwpx 파일의 절대 경로
        title (str): 보고서 제목 (예: "2분기 채용 현황 보고")
        report_data (dict): 보고서 데이터 (ReportBodyBuilder 스키마 참조)

    Returns:
        str: 성공/실패 메시지
    """
    try:
        file_path = os.path.abspath(file_path)
        parent_dir = os.path.dirname(file_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        xml = HwpxXmlBuilder()
        body = ReportBodyBuilder(title, report_data).build()

        with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("mimetype",                  xml.mimetype())
            zf.writestr("META-INF/container.xml",    xml.container_xml())
            zf.writestr("Contents/content.hpf",      xml.content_hpf(title))
            zf.writestr("Contents/header.xml",       xml.header_xml())
            zf.writestr("Contents/section0.xml",     xml.section_xml(body))

        size_kb = os.path.getsize(file_path) // 1024
        return f"✅ HWPX 보고서 생성 완료\n경로: {file_path}\n크기: {size_kb} KB"

    except Exception as e:
        return f"❌ HWPX 생성 실패: {str(e)}"


# ─────────────────────────────────────────────────────────────
# 도메인별 샘플 데이터 팩토리
# ─────────────────────────────────────────────────────────────
def make_recruit_sample() -> dict:
    """채용 현황 보고서 샘플 데이터."""
    return {
        "domain": DOMAIN_RECRUIT,
        "summary": "2026년 2분기 채용 목표 15명 중 8명 확정, 진행률 53.3%",
        "decision_request": "하반기 추가 채용 예산 1,200만원 승인 요청",
        "reporter": "인사팀 채용담당",
        "kpis": [
            {"label": "채용 목표", "value": "15명"},
            {"label": "확정 인원", "value": "8명"},
            {"label": "진행률",   "value": "53.3%"},
            {"label": "총 예산",  "value": "32,000,000원"},
            {"label": "집행액",   "value": "18,500,000원"},
            {"label": "잔액",     "value": "13,500,000원"},
        ],
        "tables": [
            {
                "title": "포지션별 채용 현황",
                "headers": ["포지션", "목표", "서류전형", "면접", "최종확정", "달성률"],
                "rows": [
                    ["개발(백엔드)", "5", "32", "8", "3", "60.0%"],
                    ["개발(프론트)", "3", "18", "5", "2", "66.7%"],
                    ["영업",        "4", "21", "6", "2", "50.0%"],
                    ["기획/운영",   "3", "14", "4", "1", "33.3%"],
                    ["합계",        "15", "85", "23", "8", "53.3%"],
                ],
                "note": "기준일: 2026-05-30 / 달성률 = 최종확정 ÷ 목표"
            },
            {
                "title": "채용 비용 내역",
                "headers": ["항목", "예산", "집행액", "잔액", "집행률"],
                "rows": [
                    ["채용 플랫폼 광고비", "8,000,000", "6,200,000", "1,800,000", "77.5%"],
                    ["헤드헌터 수수료",    "15,000,000", "9,300,000", "5,700,000", "62.0%"],
                    ["면접 운영비",        "5,000,000", "2,100,000", "2,900,000", "42.0%"],
                    ["기타 부대비용",      "4,000,000",   "900,000", "3,100,000", "22.5%"],
                    ["합계",             "32,000,000", "18,500,000", "13,500,000", "57.8%"],
                ],
                "note": "집행률 = 집행액 ÷ 예산 × 100"
            },
            {
                "title": "향후 채용 일정",
                "headers": ["단계", "기간", "대상 포지션", "담당자", "비고"],
                "rows": [
                    ["서류 접수 마감",   "2026-06-07", "기획/운영 3명", "김채용",  "재공고 포함"],
                    ["1차 면접",        "2026-06-14~20", "전 포지션",    "부서장",  "화상/대면 병행"],
                    ["2차 면접(임원)",  "2026-06-24~25", "최종 후보자",  "인사팀장", ""],
                    ["처우 협의 및 합격 통보", "2026-06-28", "전체",     "인사팀",  ""],
                    ["입사 예정",       "2026-07-01~",   "신규 합류자",  "인사팀",  "온보딩 준비"],
                ],
            }
        ],
        "notes": "영업직 지원자 수가 목표 대비 저조하여 재공고 및 헤드헌터 추가 위탁 검토 중\n하반기 개발 인력 충원 계획(+5명) 수요 조사 완료, 별도 보고 예정"
    }


def make_training_sample() -> dict:
    """교육 운영 보고서 샘플 데이터."""
    return {
        "domain": DOMAIN_TRAINING,
        "summary": "상반기 필수교육 이수율 78.4%, 목표(90%) 대비 미달 - 보완 조치 필요",
        "decision_request": "미이수자 대상 보완 교육 일정 및 예산 75만원 추가 승인 요청",
        "kpis": [
            {"label": "교육 과정 수", "value": "8개"},
            {"label": "대상 인원",   "value": "127명"},
            {"label": "이수 인원",   "value": "99명"},
            {"label": "이수율",      "value": "78.0%"},
            {"label": "예산 집행률", "value": "64.2%"},
            {"label": "목표 이수율", "value": "90.0%"},
        ],
        "tables": [
            {
                "title": "과정별 교육 이수 현황",
                "headers": ["과정명", "대상", "이수", "미이수", "이수율", "비고"],
                "rows": [
                    ["개인정보보호",   "127", "118", "9",  "92.9%", "법정 필수"],
                    ["정보보안",      "127", "115", "12", "90.6%", "법정 필수"],
                    ["직장내괴롭힘방지", "127", "102", "25", "80.3%", "법정 필수"],
                    ["리더십(팀장급)", "23",  "19",  "4",  "82.6%", "대상 한정"],
                    ["OA 활용(엑셀)", "50",  "41",  "9",  "82.0%", "선택"],
                    ["합계",         "127",  "99",  "28", "78.0%", ""],
                ],
                "note": "기준일: 2026-05-30 / 법정 필수교육 미이수 시 과태료 발생 가능"
            }
        ],
        "notes": "직장내 괴롭힘 방지 교육 미이수자 25명 중 18명은 출장·병가 사유 - 6월 보완 일정 필요\n법정 필수교육 이수율 100% 달성 목표, 7월 30일까지 완료 계획"
    }


# ─────────────────────────────────────────────────────────────
# CLI 실행 엔트리포인트
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="실무 의사결정용 HWPX 표준 보고서 생성기"
    )
    parser.add_argument(
        "--domain",
        choices=["recruit", "training", "sales", "budget", "project"],
        default="recruit",
        help="보고서 도메인 (기본값: recruit)"
    )
    parser.add_argument(
        "--output",
        default="",
        help="출력 파일 경로 (기본: 도메인_보고서_YYYYMMDD.hwpx)"
    )
    args = parser.parse_args()

    today_str = date.today().strftime('%Y%m%d')
    domain_map = {
        "recruit":  (make_recruit_sample,  f"채용현황_보고서_{today_str}.hwpx"),
        "training": (make_training_sample, f"교육현황_보고서_{today_str}.hwpx"),
    }

    if args.domain not in domain_map:
        print(f"샘플 데이터가 준비되지 않은 도메인입니다: {args.domain}")
        sys.exit(1)

    factory, default_filename = domain_map[args.domain]
    output_path = args.output or default_filename
    data = factory()
    title_map = {
        "recruit":  "채용 현황 보고서",
        "training": "교육 운영 현황 보고서",
    }
    result = create_hwpx_report(output_path, title_map[args.domain], data)
    print(result)
