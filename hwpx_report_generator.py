"""
hwpx_report_generator.py  v3.0
================================
실무 의사결정용 HWPX 표준 보고서 생성기 - 템플릿 기반 프리미엄 양식 버전

[작동 방식]
1. docs/ai_policy_report.hwpx 파일을 템플릿으로 로드합니다.
2. 템플릿의 모든 스타일(header.xml), 폰트, 여백, 상단 로고 이미지 등을 100% 그대로 활용합니다.
3. 표와 리스트, 텍스트가 템플릿의 OWPML 스타일 ID (charPrIDRef, paraPrIDRef, borderFillIDRef)를 활용하도록 인젝션합니다.
"""

import os
import zipfile
from datetime import date, datetime
from typing import Optional, List

# ─────────────────────────────────────────────────────────────
# 도메인 상수
# ─────────────────────────────────────────────────────────────
DOMAIN_RECRUIT  = "RECRUIT"
DOMAIN_TRAINING = "TRAINING"
DOMAIN_SALES    = "SALES"
DOMAIN_BUDGET   = "BUDGET"
DOMAIN_PROJECT  = "PROJECT"

# ─────────────────────────────────────────────────────────────
# XML 및 수치 유틸리티
# ─────────────────────────────────────────────────────────────
def xe(text: str) -> str:
    """XML 특수문자 이스케이프"""
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;'))

_id_counter = [1000]

def nid() -> int:
    _id_counter[0] += 1
    return _id_counter[0]

def validate_sum(items: list, amount_key: str, declared_total: float) -> tuple:
    calculated = sum(
        float(str(item.get(amount_key, 0)).replace(',', '').replace('₩', '').strip())
        for item in items
    )
    return abs(calculated - declared_total) < 0.01, calculated

def format_number(n: float, unit: str = "원") -> str:
    return f"{int(n):,}{unit}"

def format_percentage(numerator: float, denominator: float, decimal: int = 1) -> str:
    if denominator == 0:
        return "N/A"
    return f"{(numerator / denominator * 100):.{decimal}f}%"

# ─────────────────────────────────────────────────────────────
# OWPML 컴포넌트 생성기 (스타일 ID 기반)
# ─────────────────────────────────────────────────────────────
def make_empty_para() -> str:
    """빈 단락 (간격용)"""
    return (
        f'<hp:p id="{nid()}" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="0"><hp:t/></hp:run>'
        f'</hp:p>'
    )

def make_bullet_para(level: int, text: str) -> str:
    """참조 스타일 ID 기반의 들여쓰기/정렬 리스트 단락"""
    if level == 1:
        pp_id, bullet, cp_bullet, cp_text = 28, " □ ", 0, 5
    elif level == 2:
        pp_id, bullet, cp_bullet, cp_text = 29, "  ○ ", 18, 18
    elif level == 3:
        pp_id, bullet, cp_bullet, cp_text = 30, "   ― ", 18, 18
    elif level == 4:
        pp_id, bullet, cp_bullet, cp_text = 30, "     ※ ", 20, 20
    else:
        pp_id, bullet, cp_bullet, cp_text = 0, "", 0, 0
        
    return (
        f'<hp:p id="{nid()}" paraPrIDRef="{pp_id}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{cp_bullet}"><hp:t>{xe(bullet)}</hp:t></hp:run>'
        f'<hp:run charPrIDRef="{cp_text}"><hp:t>{xe(text)}</hp:t></hp:run>'
        f'</hp:p>'
    )

def make_cell(
    content_xml: str,
    width: int,
    height: int,
    bf_id: int = 5,
    row_span: int = 1,
    col_span: int = 1,
    row_addr: int = 0,
    col_addr: int = 0,
    v_align: str = 'CENTER',
    margin_lr: int = 100,
    margin_tb: int = 50,
) -> str:
    """표 셀 생성"""
    return (
        f'<hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="{bf_id}">'
        f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="{v_align}" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
        + content_xml +
        '</hp:subList>'
        f'<hp:cellAddr colAddr="{col_addr}" rowAddr="{row_addr}"/>'
        f'<hp:cellSpan colSpan="{col_span}" rowSpan="{row_span}"/>'
        f'<hp:cellSz width="{width}" height="{height}"/>'
        f'<hp:cellMargin left="{margin_lr}" right="{margin_lr}" top="{margin_tb}" bottom="{margin_tb}"/>'
        '</hp:tc>'
    )

def make_cover_title_banner(title: str, department: str) -> str:
    """표지 중앙 대형 타이틀 블록 (Table 1532694252)"""
    return f"""<hp:tbl id="{nid()}" zOrder="6" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="NONE" repeatHeader="1" rowCnt="3" colCnt="3" cellSpacing="0" borderFillIDRef="4" noAdjust="1">
  <hp:sz width="48180" widthRelTo="ABSOLUTE" height="12690" heightRelTo="ABSOLUTE" protect="0"/>
  <hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="0" allowOverlap="0" holdAnchorAndSO="1" vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>
  <hp:outMargin left="0" right="0" top="0" bottom="0"/>
  <hp:inMargin left="0" right="0" top="0" bottom="0"/>
  <hp:tr>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="7">
      <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">
        <hp:p id="2147483648" paraPrIDRef="26" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="16"/></hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="0" rowAddr="0"/><hp:cellSpan colSpan="2" rowSpan="1"/><hp:cellSz width="38219" height="818"/><hp:cellMargin left="0" right="0" top="0" bottom="0"/>
    </hp:tc>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="8">
      <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">
        <hp:p id="2147483648" paraPrIDRef="27" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="16"/></hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="2" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="9961" height="818"/><hp:cellMargin left="0" right="0" top="0" bottom="0"/>
    </hp:tc>
  </hp:tr>
  <hp:tr>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="4">
      <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">
        <hp:p id="2147483648" paraPrIDRef="23" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">
          <hp:run charPrIDRef="22">
            <hp:t>{xe(department)}</hp:t>
          </hp:run>
        </hp:p>
        <hp:p id="0" paraPrIDRef="23" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">
          <hp:run charPrIDRef="22">
            <hp:t>{xe(title)}</hp:t>
          </hp:run>
        </hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="0" rowAddr="1"/><hp:cellSpan colSpan="3" rowSpan="1"/><hp:cellSz width="48180" height="11060"/><hp:cellMargin left="0" right="0" top="0" bottom="0"/>
    </hp:tc>
  </hp:tr>
  <hp:tr>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="7">
      <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">
        <hp:p id="2147483648" paraPrIDRef="27" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="17"/></hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="0" rowAddr="2"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="10466" height="812"/><hp:cellMargin left="0" right="0" top="0" bottom="0"/>
    </hp:tc>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="8">
      <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">
        <hp:p id="2147483648" paraPrIDRef="27" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="17"/></hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="1" rowAddr="2"/><hp:cellSpan colSpan="2" rowSpan="1"/><hp:cellSz width="37714" height="812"/><hp:cellMargin left="0" right="0" top="0" bottom="0"/>
    </hp:tc>
  </hp:tr>
</hp:tbl>"""

def make_body_title_banner(title: str) -> str:
    """본문 첫 페이지 최상단 축소 타이틀 배너 (Table 1532694250)"""
    return f"""<hp:tbl id="{nid()}" zOrder="5" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="NONE" repeatHeader="1" rowCnt="3" colCnt="3" cellSpacing="0" borderFillIDRef="4" noAdjust="1">
  <hp:sz width="48180" widthRelTo="ABSOLUTE" height="4766" heightRelTo="ABSOLUTE" protect="0"/>
  <hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="0" allowOverlap="0" holdAnchorAndSO="1" vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>
  <hp:outMargin left="0" right="0" top="0" bottom="0"/>
  <hp:inMargin left="0" right="0" top="0" bottom="0"/>
  <hp:tr>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="7">
      <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">
        <hp:p id="2147483648" paraPrIDRef="26" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="16"/></hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="0" rowAddr="0"/><hp:cellSpan colSpan="2" rowSpan="1"/><hp:cellSz width="38219" height="600"/><hp:cellMargin left="0" right="0" top="0" bottom="0"/>
    </hp:tc>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="8">
      <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">
        <hp:p id="2147483648" paraPrIDRef="27" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="16"/></hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="2" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="9961" height="600"/><hp:cellMargin left="0" right="0" top="0" bottom="0"/>
    </hp:tc>
  </hp:tr>
  <hp:tr>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="4">
      <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">
        <hp:p id="2147483648" paraPrIDRef="23" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">
          <hp:run charPrIDRef="14">
            <hp:t>{xe(title)}</hp:t>
          </hp:run>
        </hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="0" rowAddr="1"/><hp:cellSpan colSpan="3" rowSpan="1"/><hp:cellSz width="48180" height="3566"/><hp:cellMargin left="0" right="0" top="0" bottom="0"/>
    </hp:tc>
  </hp:tr>
  <hp:tr>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="7">
      <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">
        <hp:p id="2147483648" paraPrIDRef="27" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="17"/></hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="0" rowAddr="2"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="10466" height="600"/><hp:cellMargin left="0" right="0" top="0" bottom="0"/>
    </hp:tc>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="8">
      <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">
        <hp:p id="2147483648" paraPrIDRef="27" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="17"/></hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="1" rowAddr="2"/><hp:cellSpan colSpan="2" rowSpan="1"/><hp:cellSz width="37714" height="600"/><hp:cellMargin left="0" right="0" top="0" bottom="0"/>
    </hp:tc>
  </hp:tr>
</hp:tbl>"""

def make_section_header(roman_num: str, title: str) -> str:
    """본문 로마자 대섹션 헤더 타이틀 블록 (Table 1682151852)"""
    return f"""<hp:tbl id="{nid()}" zOrder="0" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="CELL" repeatHeader="1" rowCnt="1" colCnt="3" cellSpacing="0" borderFillIDRef="5" noAdjust="0">
  <hp:sz width="47688" widthRelTo="ABSOLUTE" height="2832" heightRelTo="ABSOLUTE" protect="0"/>
  <hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>
  <hp:outMargin left="283" right="283" top="283" bottom="283"/>
  <hp:inMargin left="141" right="141" top="141" bottom="141"/>
  <hp:tr>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="9">
      <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">
        <hp:p id="2147483648" paraPrIDRef="3" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="24"><hp:t>{xe(roman_num)}</hp:t></hp:run></hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="0" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="3327" height="2832"/><hp:cellMargin left="141" right="141" top="141" bottom="141"/>
    </hp:tc>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="6">
      <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">
        <hp:p id="2147483648" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="2"/></hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="1" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="848" height="2832"/><hp:cellMargin left="141" right="141" top="141" bottom="141"/>
    </hp:tc>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="10">
      <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">
        <hp:p id="2147483648" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="2"><hp:t> {xe(title)}</hp:t></hp:run></hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="2" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="43513" height="2832"/><hp:cellMargin left="141" right="141" top="141" bottom="141"/>
    </hp:tc>
  </hp:tr>
</hp:tbl>"""

def make_bluf_box(summary: str, decision: str) -> str:
    """핵심 요지 및 의사결정 요청을 감싸는 라벤더 색상의 단일 블록 (Table + borderFill 12)"""
    h = 2500
    content = (
        f'<hp:p id="{nid()}" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="25"><hp:t>▶ 요 지 : </hp:t></hp:run>'
        f'<hp:run charPrIDRef="18"><hp:t>{xe(summary)}</hp:t></hp:run>'
        f'</hp:p>'
        f'<hp:p id="{nid()}" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="25"><hp:t>▶ 의사결정 요청 : </hp:t></hp:run>'
        f'<hp:run charPrIDRef="18"><hp:t>{xe(decision)}</hp:t></hp:run>'
        f'</hp:p>'
    )
    cell = make_cell(content, 48190, h, bf_id=12, margin_lr=200, margin_tb=150)
    row_xml = f'<hp:tr height="{h}" outlineLevel="0" repeatHeader="0" pageBreak="0" mergeInfo="">' + cell + '</hp:tr>'
    
    return (
        f'<hp:tbl id="{nid()}" zOrder="0" numberingType="NONE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="NONE" repeatHeader="0" rowCnt="1" colCnt="1" cellSpacing="0" borderFillIDRef="12" noAdjust="1">'
        f'<hp:sz width="48190" widthRelTo="ABSOLUTE" height="{h}" heightRelTo="ABSOLUTE" protect="0"/>'
        f'<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="0" allowOverlap="0" holdAnchorAndSO="1" vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
        f'<hp:outMargin left="0" right="0" top="100" bottom="100"/>'
        f'<hp:inMargin left="0" right="0" top="0" bottom="0"/>'
        + row_xml + '</hp:tbl>'
    )

def make_kpi_cards(kpis: list) -> str:
    """라벤더 카드 형태로 구분 배열되는 KPI 지표 박스들"""
    n = len(kpis)
    if n == 0:
        return ""
    col_w = 48190 // n
    last_w = 48190 - col_w * (n - 1)
    
    h = 1800
    cells = []
    for i, kpi in enumerate(kpis):
        w = last_w if i == n - 1 else col_w
        label = kpi.get("label", "")
        value = kpi.get("value", "")
        
        content = (
            f'<hp:p id="{nid()}" paraPrIDRef="23" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="26"><hp:t>{xe(label)}</hp:t></hp:run>'
            f'</hp:p>'
            f'<hp:p id="{nid()}" paraPrIDRef="23" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="27"><hp:t>{xe(value)}</hp:t></hp:run>'
            f'</hp:p>'
        )
        cells.append(make_cell(content, w, h, bf_id=12, margin_lr=100, margin_tb=100, v_align='CENTER'))
        
    row_xml = f'<hp:tr height="{h}" outlineLevel="0" repeatHeader="0" pageBreak="0" mergeInfo="">' + "".join(cells) + '</hp:tr>'
    
    return (
        f'<hp:tbl id="{nid()}" zOrder="0" numberingType="NONE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="NONE" repeatHeader="0" rowCnt="1" colCnt="{n}" cellSpacing="100" borderFillIDRef="0" noAdjust="1">'
        f'<hp:sz width="48190" widthRelTo="ABSOLUTE" height="{h}" heightRelTo="ABSOLUTE" protect="0"/>'
        f'<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="0" allowOverlap="0" holdAnchorAndSO="1" vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
        f'<hp:outMargin left="0" right="0" top="100" bottom="100"/>'
        f'<hp:inMargin left="0" right="0" top="0" bottom="0"/>'
        + row_xml + '</hp:tbl>'
    )

def make_data_table(
    headers: List[str],
    rows: List[List[str]],
    note: Optional[str] = None,
    col_ratios: Optional[List[int]] = None,
) -> str:
    """네이비 헤더와 격자 그리드가 살아있는 정밀 표 컴포넌트"""
    n_cols = len(headers)
    if n_cols == 0:
        return ""
        
    if col_ratios and len(col_ratios) == n_cols:
        total_ratio = sum(col_ratios)
        col_widths = [int(48190 * r / total_ratio) for r in col_ratios]
        col_widths[-1] += 48190 - sum(col_widths)
    else:
        col_w = 48190 // n_cols
        col_widths = [col_w] * (n_cols - 1) + [48190 - col_w * (n_cols - 1)]
        
    n_rows = len(rows) + 1
    total_h = 1100 + 900 * len(rows)
    
    rows_xml = ""
    
    # Header
    rows_xml += '<hp:tr height="1100" outlineLevel="0" repeatHeader="1" pageBreak="0" mergeInfo="">'
    for col_i, (h, w) in enumerate(zip(headers, col_widths)):
        align = 23 # Center align
        content = (
            f'<hp:p id="{nid()}" paraPrIDRef="{align}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="24"><hp:t>{xe(h)}</hp:t></hp:run>'
            f'</hp:p>'
        )
        rows_xml += make_cell(content, w, 1100, bf_id=9, margin_lr=100, margin_tb=50)
    rows_xml += '</hp:tr>'
    
    # Data Rows
    for row_i, row in enumerate(rows):
        first_val = str(row[0]).strip() if row else ""
        is_total = any(first_val.startswith(kw) for kw in ["합계", "계", "Total", "total", "소계"])
        
        cp_text = 25 if is_total else 18
        
        rows_xml += '<hp:tr height="900" outlineLevel="0" repeatHeader="0" pageBreak="0" mergeInfo="">'
        for col_i, (cell_val, w) in enumerate(zip(row, col_widths)):
            align = 0 if col_i == 0 else 23
            content = (
                f'<hp:p id="{nid()}" paraPrIDRef="{align}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
                f'<hp:run charPrIDRef="{cp_text}"><hp:t>{xe(cell_val)}</hp:t></hp:run>'
                f'</hp:p>'
            )
            rows_xml += make_cell(content, w, 900, bf_id=5, margin_lr=100, margin_tb=30)
        rows_xml += '</hp:tr>'
        
    result = (
        f'<hp:tbl id="{nid()}" zOrder="0" numberingType="NONE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="NONE" repeatHeader="1" rowCnt="{n_rows}" colCnt="{n_cols}" cellSpacing="0" borderFillIDRef="5" noAdjust="1">'
        f'<hp:sz width="48190" widthRelTo="ABSOLUTE" height="{total_h}" heightRelTo="ABSOLUTE" protect="0"/>'
        f'<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="0" allowOverlap="0" holdAnchorAndSO="1" vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
        f'<hp:outMargin left="0" right="0" top="100" bottom="100"/>'
        f'<hp:inMargin left="0" right="0" top="0" bottom="0"/>'
        + rows_xml + '</hp:tbl>'
    )
    
    if note:
        result += (
            f'<hp:p id="{nid()}" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="20"><hp:t>  ※ {xe(note)}</hp:t></hp:run>'
            f'</hp:p>'
        )
        
    return result

# ─────────────────────────────────────────────────────────────
# 템플릿 파서 및 빌더
# ─────────────────────────────────────────────────────────────
def get_template_section_prefix(ref_zip_path: str) -> str:
    """참조 HWPX 파일에서 첫번째 단락(secPr, pagePr, header 등 레이아웃 속성)을 추출"""
    with zipfile.ZipFile(ref_zip_path, 'r') as z:
        sec_xml = z.read('Contents/section0.xml').decode('utf-8', 'replace')
        
    idx_header = sec_xml.find('</hp:header></hp:ctrl>')
    if idx_header != -1:
        idx_outer_p = sec_xml.find('</hp:p>', idx_header)
        if idx_outer_p != -1:
            return sec_xml[:idx_outer_p + 7]
            
    # Fallback
    idx = sec_xml.find('</hp:p>')
    if idx != -1:
        return sec_xml[:idx + 7]
    else:
        HWPML_NS = (
            'xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app" '
            'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
            'xmlns:hp10="http://www.hancom.co.kr/hwpml/2016/paragraph" '
            'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
            'xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core" '
            'xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" '
            'xmlns:hhs="http://www.hancom.co.kr/hwpml/2011/history" '
            'xmlns:hm="http://www.hancom.co.kr/hwpml/2011/master-page" '
            'xmlns:opf="http://www.idpf.org/2007/opf/"'
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            f'<hs:sec {HWPML_NS}>'
            f'<hp:p id="{nid()}" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="0"/>'
            f'</hp:p>'
        )

def build_sections(report_data: dict) -> list:
    """report_data로부터 로마자 번호를 가진 정형화된 섹션 목록 구성"""
    sections = []
    
    # 1. Summary
    summary = report_data.get("summary", "")
    decision = report_data.get("decision_request", "")
    if summary or decision:
        content = []
        content.append(make_bullet_para(1, "실무 의사결정을 위한 현황 요약 및 주요 의사결정 요청 사항"))
        content.append(make_empty_para())
        content.append(make_bluf_box(summary, decision))
        sections.append({
            "num": "Ⅰ",
            "title": "보고 요지 및 의사결정 요청",
            "content": "\n".join(content)
        })
        
    # 2. KPIs
    kpis = report_data.get("kpis", [])
    if kpis:
        content = []
        content.append(make_bullet_para(1, "주요 성과 및 핵심 운영 지표 현황"))
        content.append(make_empty_para())
        content.append(make_kpi_cards(kpis))
        sections.append({
            "num": "Ⅱ",
            "title": "핵심 성과 지표 (KPI)",
            "content": "\n".join(content)
        })
        
    # 3. Tables
    tables = report_data.get("tables", [])
    if tables:
        content = []
        content.append(make_bullet_para(1, "각 부문별 상세 실적 및 정량 데이터 분석"))
        content.append(make_empty_para())
        for idx, tbl in enumerate(tables):
            title = tbl.get("title", "")
            headers = tbl.get("headers", [])
            rows = tbl.get("rows", [])
            note = tbl.get("note", None)
            col_ratios = tbl.get("col_ratios", None)
            
            content.append(make_bullet_para(2, f"제 {idx+1}현황 : {title}"))
            content.append(make_data_table(headers, rows, note, col_ratios))
            content.append(make_empty_para())
            
        sections.append({
            "num": "Ⅲ",
            "title": "세부 현황 및 데이터",
            "content": "\n".join(content)
        })
        
    # 4. Notes
    notes = report_data.get("notes", "")
    if notes:
        content = []
        content.append(make_bullet_para(1, "주요 문제점 분석 및 향후 대응 방안 수립"))
        content.append(make_empty_para())
        lines = [line.strip() for line in notes.split("\n") if line.strip()]
        for line in lines:
            content.append(make_bullet_para(2, line))
        sections.append({
            "num": "Ⅳ",
            "title": "특이사항 및 향후 계획",
            "content": "\n".join(content)
        })
        
    return sections

def build_section0_xml(prefix: str, title: str, report_data: dict, sections: list) -> str:
    """전면 타이틀 배너, 목차, 각 로마자 섹션으로 이루어진 완전한 section0.xml XML 생성"""
    b = prefix + "\n"
    
    # 1. 표지 (Page 1) 여백용 빈 줄 추가
    for _ in range(4):
        b += make_empty_para()
        
    department = report_data.get("department", "인재개발본부")
    b += f'<hp:p id="{nid()}" paraPrIDRef="31" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
    b += f'<hp:run charPrIDRef="0">'
    b += make_cover_title_banner(title, department)
    b += f'</hp:run></hp:p>\n'
    
    for _ in range(5):
        b += make_empty_para()
        
    # 날짜 표기 (P[11])
    today = date.today().strftime('%Y. %m. %d.')
    b += (
        f'<hp:p id="{nid()}" paraPrIDRef="23" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="23"><hp:t>{xe(today)}</hp:t></hp:run>'
        f'</hp:p>\n'
    )
    
    for _ in range(5):
        b += make_empty_para()
        
    # 하단 로고 이미지 (P[17])
    seoul_logo_pic = (
        '<hp:pic id="1532694255" zOrder="7" numberingType="PICTURE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" href="" groupLevel="0" instid="458952432" reverse="0">'
        '<hp:offset x="4294962103" y="4294965154"/><hp:orgSz width="13944" height="5752"/><hp:curSz width="12299" height="5074"/>'
        '<hp:flip horizontal="0" vertical="0"/><hp:rotationInfo angle="0" centerX="6149" centerY="2537" rotateimage="1"/>'
        '<hp:renderingInfo><hc:transMatrix e1="1" e2="0" e3="-5193" e4="0" e5="1" e6="-2142"/><hc:scaMatrix e1="0.882028" e2="0" e3="5193" e4="0" e5="0.882128" e6="2142"/><hc:rotMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/></hp:renderingInfo>'
        '<hc:img binaryItemIDRef="image1" bright="0" contrast="0" effect="REAL_PIC" alpha="0"/>'
        '<hp:imgRect><hc:pt0 x="0" y="0"/><hc:pt1 x="13944" y="0"/><hc:pt2 x="13944" y="5752"/><hc:pt3 x="0" y="5752"/></hp:imgRect>'
        '<hp:imgClip left="0" right="150000" top="0" bottom="61860"/><hp:inMargin left="0" right="0" top="0" bottom="0"/><hp:imgDim dimwidth="150000" dimheight="61860"/>'
        '<hp:effects/><hp:sz width="12299" widthRelTo="ABSOLUTE" height="5074" heightRelTo="ABSOLUTE" protect="0"/>'
        '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="1" holdAnchorAndSO="0" vertRelTo="PAPER" horzRelTo="PAPER" vertAlign="TOP" horzAlign="LEFT" vertOffset="68401" horzOffset="25510"/>'
        '<hp:outMargin left="0" right="0" top="0" bottom="0"/>'
        '<hp:shapeComment>그림입니다.\n2: 원본 그림의 이름: 2000px_at_b.png\n3: 원본 그림의 크기: 가로 2000pixel, 세로 825pixel</hp:shapeComment></hp:pic>'
    )
    b += (
        f'<hp:p id="{nid()}" paraPrIDRef="23" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="23">{seoul_logo_pic}</hp:run>'
        f'</hp:p>\n'
    )
    
    # 2. 목차 (Page 2, pageBreak="1")
    b += f'<hp:p id="{nid()}" paraPrIDRef="23" styleIDRef="0" pageBreak="1" columnBreak="0" merged="0">'
    b += f'<hp:run charPrIDRef="0">'
    
    toc_title_tbl = f"""<hp:tbl id="{nid()}" zOrder="8" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="CELL" repeatHeader="1" rowCnt="1" colCnt="7" cellSpacing="0" borderFillIDRef="5" noAdjust="0">
  <hp:sz width="18279" widthRelTo="ABSOLUTE" height="3931" heightRelTo="ABSOLUTE" protect="0"/>
  <hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>
  <hp:outMargin left="283" right="283" top="283" bottom="283"/>
  <hp:inMargin left="141" right="141" top="141" bottom="141"/>
  <hp:tr>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="14">
      <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">
        <hp:p id="2147483648" paraPrIDRef="33" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="33"/></hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="0" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="565" height="3931"/><hp:cellMargin left="141" right="141" top="141" bottom="141"/>
    </hp:tc>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="11">
      <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">
        <hp:p id="2147483648" paraPrIDRef="33" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="33"/></hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="1" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="565" height="3931"/><hp:cellMargin left="141" right="141" top="141" bottom="141"/>
    </hp:tc>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="12">
      <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">
        <hp:p id="2147483648" paraPrIDRef="33" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="33"/></hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="2" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="1414" height="3931"/><hp:cellMargin left="141" right="141" top="141" bottom="141"/>
    </hp:tc>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="11">
      <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">
        <hp:p id="2147483648" paraPrIDRef="33" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="34"><hp:t>목  차</hp:t></hp:run></hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="3" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="13191" height="3931"/><hp:cellMargin left="141" right="141" top="141" bottom="141"/>
    </hp:tc>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="12">
      <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">
        <hp:p id="2147483648" paraPrIDRef="33" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="33"/></hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="4" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="1414" height="3931"/><hp:cellMargin left="141" right="141" top="141" bottom="141"/>
    </hp:tc>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="11">
      <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">
        <hp:p id="2147483648" paraPrIDRef="33" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="33"/></hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="5" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="565" height="3931"/><hp:cellMargin left="141" right="141" top="141" bottom="141"/>
    </hp:tc>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="14">
      <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">
        <hp:p id="2147483648" paraPrIDRef="33" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0"><hp:run charPrIDRef="33"/></hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="6" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="565" height="3931"/><hp:cellMargin left="141" right="141" top="141" bottom="141"/>
    </hp:tc>
  </hp:tr>
</hp:tbl>"""
    b += toc_title_tbl
    b += f'</hp:run></hp:p>\n'
    
    b += make_empty_para()
    
    # 목차 아이템 생성
    toc_items_xml = ""
    for idx, sec in enumerate(sections):
        roman = sec["num"]
        sec_title = sec["title"]
        page_val = idx + 1
        tab_w = max(10000, 45208 - 2000 * len(roman + ". " + sec_title))
        toc_items_xml += (
            f'<hp:p id="{nid()}" paraPrIDRef="40" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="27"><hp:t>{xe(roman)}</hp:t></hp:run>'
            f'<hp:run charPrIDRef="35"><hp:t>. {xe(sec_title)}<hp:tab width="{tab_w}" leader="3" type="2"/> {page_val}</hp:t></hp:run>'
            f'</hp:p>\n'
        )
        
    toc_container_tbl = f"""<hp:tbl id="{nid()}" zOrder="9" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="CELL" repeatHeader="1" rowCnt="1" colCnt="1" cellSpacing="0" borderFillIDRef="5" noAdjust="0">
  <hp:sz width="46492" widthRelTo="ABSOLUTE" height="57840" heightRelTo="ABSOLUTE" protect="0"/>
  <hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>
  <hp:outMargin left="283" right="283" top="283" bottom="283"/>
  <hp:inMargin left="141" right="141" top="141" bottom="141"/>
  <hp:tr>
    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="13">
      <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">
        {toc_items_xml}
      </hp:subList>
      <hp:cellAddr colAddr="0" rowAddr="0"/><hp:cellSpan colSpan="1" rowSpan="1"/><hp:cellSz width="46492" height="58199"/><hp:cellMargin left="141" right="141" top="141" bottom="141"/>
    </hp:tc>
  </hp:tr>
</hp:tbl>"""

    b += f'<hp:p id="{nid()}" paraPrIDRef="23" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
    b += f'<hp:run charPrIDRef="0">{toc_container_tbl}</hp:run>'
    b += f'</hp:p>\n'
    
    # 3. 본문 첫 페이지 (Page 3, pageBreak="1", 페이지 번호 1로 재시작)
    b += f'<hp:p id="{nid()}" paraPrIDRef="23" styleIDRef="0" pageBreak="1" columnBreak="0" merged="0">'
    b += f'<hp:run charPrIDRef="17">'
    b += f'<hp:newNum num="1" numType="PAGE"/>'
    b += make_body_title_banner(title)
    b += f'</hp:run></hp:p>\n'
    
    b += make_empty_para()
    
    # 4. 각 로마자 섹션 배치
    for idx, sec in enumerate(sections):
        roman = sec["num"]
        sec_title = sec["title"]
        sec_content = sec["content"]
        
        # 첫 섹션은 배너 바로 뒤에 흐르고, 다음 섹션부터 새 페이지로 나눔
        pb_val = "1" if idx > 0 else "0"
        
        b += f'<hp:p id="{nid()}" paraPrIDRef="23" styleIDRef="0" pageBreak="{pb_val}" columnBreak="0" merged="0">'
        b += f'<hp:run charPrIDRef="0">'
        b += make_section_header(roman, sec_title)
        b += f'</hp:run></hp:p>\n'
        
        b += make_empty_para()
        b += sec_content
        b += make_empty_para()
        
    return b + "</hs:sec>"

# ─────────────────────────────────────────────────────────────
# 메인 보고서 생성 API
# ─────────────────────────────────────────────────────────────
def create_hwpx_report(file_path: str, title: str, report_data: dict) -> str:
    """실무 의사결정용 HWPX 표준 보고서 생성 (템플릿 주입 방식)"""
    try:
        file_path = os.path.abspath(file_path)
        parent = os.path.dirname(file_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
            
        ref_path = r"c:\Users\user\Desktop\Claude skills\docs\ai_policy_report.hwpx"
        if not os.path.exists(ref_path):
            ref_path = os.path.join(os.path.dirname(__file__), "..", "docs", "ai_policy_report.hwpx")
            ref_path = os.path.abspath(ref_path)
            
        if not os.path.exists(ref_path):
            return f"FAIL: 참조 템플릿 파일을 찾을 수 없습니다: {ref_path}"
            
        # 템플릿의 section0 prefix 추출 (페이지 속성 및 상단 로고 이미지 포함)
        prefix = get_template_section_prefix(ref_path)
        
        # 콘텐츠 섹션 빌드
        sections = build_sections(report_data)
        
        # section0.xml 콘텐츠 조립
        section0_xml_content = build_section0_xml(prefix, title, report_data, sections)
        
        with zipfile.ZipFile(ref_path, 'r') as z_in:
            with zipfile.ZipFile(file_path, 'w') as z_out:
                # mimetype은 압축 없이 첫번째 파일로 기록해야 함
                z_out.writestr(zipfile.ZipInfo("mimetype"), b"application/hwp+zip")
                
                for info in z_in.infolist():
                    if info.filename == "mimetype":
                        continue
                        
                    data = z_in.read(info.filename)
                    
                    # HPF 패키지 메타데이터 타이틀 주입
                    if info.filename == "Contents/content.hpf":
                        hpf_str = data.decode('utf-8', 'replace')
                        if "<opf:title/>" in hpf_str:
                            hpf_str = hpf_str.replace("<opf:title/>", f"<opf:title>{xe(title)}</opf:title>")
                        elif "<opf:title>" in hpf_str:
                            start_idx = hpf_str.find("<opf:title>")
                            end_idx = hpf_str.find("</opf:title>")
                            if start_idx != -1 and end_idx != -1:
                                hpf_str = hpf_str[:start_idx + 11] + xe(title) + hpf_str[end_idx:]
                        data = hpf_str.encode('utf-8')
                        
                    # 본문 콘텐츠 주입
                    elif info.filename == "Contents/section0.xml":
                        data = section0_xml_content.encode('utf-8')
                        
                    z_out.writestr(
                        zipfile.ZipInfo(info.filename),
                        data,
                        compress_type=zipfile.ZIP_DEFLATED
                    )
                    
        size_kb = max(1, os.path.getsize(file_path) // 1024)
        return f"OK HWPX 보고서 생성 완료\n경로: {file_path}\n크기: {size_kb} KB"
        
    except Exception as e:
        import traceback
        return f"FAIL 생성 실패: {str(e)}\n{traceback.format_exc()}"

# ─────────────────────────────────────────────────────────────
# 도메인별 샘플 데이터 팩토리
# ─────────────────────────────────────────────────────────────
def make_recruit_sample() -> dict:
    return {
        "domain": DOMAIN_RECRUIT,
        "summary": "2026년 2분기 채용 목표 15명 중 8명 확정 (진행률 53.3%) — 영업직 재공고 필요, 7월 전원 합류 목표",
        "decision_request": "하반기 헤드헌터 추가 계약 및 예산 12,000,000원 추가 집행 승인 요청",
        "reporter": "인사팀 채용담당",
        "department": "인재개발본부",
        "kpis": [
            {"label": "채용 목표 인원",  "value": "15명"},
            {"label": "확정 인원",       "value": "8명"},
            {"label": "진행률",          "value": "53.3%"},
            {"label": "총 예산",         "value": "32,000,000원"},
            {"label": "집행액",          "value": "18,500,000원"},
            {"label": "예산 집행률",     "value": "57.8%"},
        ],
        "tables": [
            {
                "title": "포지션별 채용 현황",
                "headers": ["포지션", "목표", "서류", "면접", "확정", "달성률"],
                "col_ratios": [3, 1, 1, 1, 1, 1],
                "rows": [
                    ["개발 (백엔드)",  "5",  "32",  "8",  "3",  "60.0%"],
                    ["개발 (프론트)", "3",  "18",  "5",  "2",  "66.7%"],
                    ["영업",          "4",  "21",  "6",  "2",  "50.0%"],
                    ["기획·운영",     "3",  "14",  "4",  "1",  "33.3%"],
                    ["합계",          "15", "85", "23",  "8",  "53.3%"],
                ],
                "note": "달성률 = 최종확정 ÷ 목표",
            },
            {
                "title": "채용 예산 집행 현황",
                "headers": ["항목", "예산(원)", "집행액(원)", "잔액(원)", "집행률"],
                "col_ratios": [3, 2, 2, 2, 1],
                "rows": [
                    ["채용 플랫폼 광고비",  "8,000,000",  "6,200,000",  "1,800,000",  "77.5%"],
                    ["헤드헌터 수수료",    "15,000,000",  "9,300,000",  "5,700,000",  "62.0%"],
                    ["면접 운영비",         "5,000,000",  "2,100,000",  "2,900,000",  "42.0%"],
                    ["기타 부대비용",       "4,000,000",    "900,000",  "3,100,000",  "22.5%"],
                    ["합계",              "32,000,000", "18,500,000", "13,500,000",  "57.8%"],
                ],
                "note": "집행률 = 집행액 ÷ 예산 × 100",
            },
            {
                "title": "향후 채용 추진 일정",
                "headers": ["단계", "기간", "대상 포지션", "담당", "비고"],
                "col_ratios": [2, 2, 2, 1, 2],
                "rows": [
                    ["서류 접수 마감",      "2026-06-07",    "기획·운영 3명",   "김채용",    "재공고 포함"],
                    ["1차 면접",           "2026-06-14~20", "전 포지션",       "부서장",    "화상·대면 병행"],
                    ["2차 면접 (임원)",    "2026-06-24~25", "최종 후보자",     "인사팀장",  ""],
                    ["처우 협의·합격 통보", "2026-06-28",   "전체",            "인사팀",    ""],
                    ["입사 예정",          "2026-07-01~",   "신규 합류자",     "인사팀",    "온보딩 준비"],
                ],
            },
        ],
        "notes": (
            "영업직 지원자 수 목표 대비 저조 → 재공고 및 헤드헌터 추가 위탁 검토 중\n"
            "하반기 개발 인력 충원 계획(+5명) 수요 조사 완료, 별도 보고 예정\n"
            "채용 리드타임 단축을 위해 서류 합격자 면접 일정 사전 확정 운영 예정"
        ),
    }

def make_training_sample() -> dict:
    return {
        "domain": DOMAIN_TRAINING,
        "summary": "2026년 상반기 필수교육 이수율 78.0% (목표 90% 대비 -12%p) — 법정 미이수자 집중 관리 필요",
        "decision_request": "미이수자 보완 교육 6월 추가 실시 승인 및 예산 750,000원 집행 승인 요청",
        "reporter": "HRD팀 교육담당",
        "department": "인재개발본부",
        "kpis": [
            {"label": "운영 과정 수",    "value": "5개"},
            {"label": "교육 대상",       "value": "127명"},
            {"label": "이수 인원",       "value": "99명"},
            {"label": "전체 이수율",     "value": "78.0%"},
            {"label": "법정 이수율",     "value": "87.9%"},
            {"label": "목표 이수율",     "value": "90.0%"},
        ],
        "tables": [
            {
                "title": "과정별 교육 이수 현황",
                "headers": ["과정명", "구분", "대상", "이수", "미이수", "이수율"],
                "col_ratios": [3, 1, 1, 1, 1, 1],
                "rows": [
                    ["개인정보 보호",        "법정 필수", "127", "118",  "9",  "92.9%"],
                    ["정보보안",             "법정 필수", "127", "115", "12",  "90.6%"],
                    ["직장 내 괴롭힘 방지",  "법정 필수", "127", "102", "25",  "80.3%"],
                    ["리더십 (팀장급)",      "직책 교육",  "23",  "19",  "4",  "82.6%"],
                    ["OA 활용 (엑셀)",       "선택",       "50",  "41",  "9",  "82.0%"],
                    ["합계",                 "",          "127",  "99", "28",  "78.0%"],
                ],
                "note": "법정 미이수 시 기업 과태료(최대 500만원) 발생 가능",
            },
            {
                "title": "교육 예산 집행 현황",
                "headers": ["항목", "배정 예산(원)", "집행액(원)", "잔액(원)", "집행률"],
                "col_ratios": [3, 2, 2, 2, 1],
                "rows": [
                    ["외부 강사비",       "3,500,000", "2,200,000", "1,300,000", "62.9%"],
                    ["교재·자료비",         "800,000",   "650,000",   "150,000", "81.3%"],
                    ["장소 임차비",       "1,200,000",   "900,000",   "300,000", "75.0%"],
                    ["온라인 플랫폼 이용료", "500,000",  "450,000",    "50,000", "90.0%"],
                    ["합계",             "6,000,000", "4,200,000", "1,800,000", "70.0%"],
                ],
                "note": "보완 교육 추가 소요 예산: 750,000원",
            },
        ],
        "notes": (
            "직장 내 괴롭힘 방지 미이수 25명 중 18명은 출장·병가 불가피 사유 → 6월 보완 일정 별도 운영 필요\n"
            "법정 교육 이수율 100% 달성 목표: 7월 30일까지 완료 계획\n"
            "하반기 신규 입사자 온보딩 교육 프로그램 설계 진행 중 (7월 오픈 목표)"
        ),
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="실무 의사결정용 HWPX 표준 보고서 생성기 v3.0")
    parser.add_argument("--domain", choices=["recruit", "training"], default="recruit")
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    
    today_str = date.today().strftime('%Y%m%d')
    MAP = {
        "recruit":  (make_recruit_sample,  f"recruit_report_{today_str}.hwpx",  "채용 현황 보고서"),
        "training": (make_training_sample, f"training_report_{today_str}.hwpx", "교육 운영 현황 보고서"),
    }
    factory, default_name, title = MAP[args.domain]
    result = create_hwpx_report(args.output or default_name, title, factory())
    print(result)
