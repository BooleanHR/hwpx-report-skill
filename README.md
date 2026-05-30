# 실무 의사결정용 HWPX 표준 보고서 스킬

채용 기획, 교육 운영, 영업 실적 보고 등 다양한 실무 영역에서  
경영진 및 부서장의 **신속한 의사결정**을 지원하는 HWPX 표준 보고서를 자동 생성합니다.

> 단순한 제안서를 넘어, 의사결정권자가 직관적으로 내용을 파악할 수 있도록  
> **불필요한 장식 없이 핵심 데이터와 결론을 최우선으로 배치**하는 에이전트 스킬입니다.

---

## 주요 특징

| 특징 | 설명 |
|------|------|
| 두괄식 구조 | 핵심 지표·결론·의사결정 요청을 1페이지 상단에 배치 |
| 표 중심 레이아웃 | 모든 비교·일정·예산 데이터를 표로 구조화 |
| 미니멀 스타일 | 무채색 기반 + 파란색 포인트 컬러 1종만 사용 |
| 수치 무결성 | 세부 항목 합계 = 총합계 자동 검증 |
| 범용 도메인 | 채용·교육·영업·예산·프로젝트 모듈 지원 |

---

## 지원 도메인

```
RECRUIT   채용 기획·운영 (포지션 현황, 전형 단계, 채용 비용, 일정)
TRAINING  교육·훈련 운영 (과정 현황, 이수율, 예산 집행, 차기 계획)
SALES     영업 실적·계획 (KPI 요약, 월별 실적, 제품/채널 분석)
BUDGET    예산·집행 현황 (배정/집행/잔액 비교, 항목별 분석)
PROJECT   프로젝트 현황 (마일스톤, 진척률, 리스크, 다음 액션)
```

---

## 파일 구조

```
hwpx-report-skill/
├── skill.md                         # 범용 스킬 정의 (LLM 공통 참조)
├── hwpx_report_generator.py         # 핵심 Python 구현체
├── hwpx_report_mcp_server.py        # MCP 서버 (Claude Desktop 등 연동)
├── .claude/
│   ├── skill.md                     # Claude 전용 스킬 파일
│   └── claude_skill.json            # Claude 스킬 매니페스트
├── .cursor/
│   ├── skill.json                   # Cursor 스킬 매니페스트
│   └── rules/
│       └── hwpx-report-skill.mdc    # Cursor Rules 파일
└── docs/
    ├── recruit_sample.hwpx          # 채용 현황 보고서 샘플
    └── training_sample.hwpx         # 교육 운영 보고서 샘플
```

---

## 빠른 시작 (Python 직접 사용)

### 1. 의존성 설치 (표준 라이브러리만 사용)

```bash
# 추가 패키지 설치 없음 - Python 3.8+ 표준 라이브러리만 사용
python --version  # 3.8 이상 권장
```

### 2. 샘플 보고서 생성

```bash
# 채용 현황 보고서 샘플 생성
python hwpx_report_generator.py --domain recruit --output 채용현황_보고서.hwpx

# 교육 운영 보고서 샘플 생성
python hwpx_report_generator.py --domain training --output 교육현황_보고서.hwpx
```

### 3. 코드에서 직접 호출

```python
from hwpx_report_generator import create_hwpx_report

report_data = {
    "domain": "RECRUIT",
    "summary": "2분기 채용 목표 15명 중 8명 확정, 진행률 53.3%",
    "decision_request": "하반기 추가 채용 예산 1,200만원 승인 요청",
    "kpis": [
        {"label": "채용 목표",  "value": "15명"},
        {"label": "확정 인원",  "value": "8명"},
        {"label": "진행률",     "value": "53.3%"},
        {"label": "총 예산",    "value": "32,000,000원"},
        {"label": "집행액",     "value": "18,500,000원"},
        {"label": "잔액",       "value": "13,500,000원"},
    ],
    "tables": [
        {
            "title": "포지션별 채용 현황",
            "headers": ["포지션", "목표", "확정", "달성률"],
            "rows": [
                ["개발(백엔드)", "5", "3", "60.0%"],
                ["개발(프론트)", "3", "2", "66.7%"],
                ["영업",        "4", "2", "50.0%"],
                ["기획/운영",   "3", "1", "33.3%"],
                ["합계",        "15", "8", "53.3%"],
            ],
            "note": "기준일: 2026-05-30"
        }
    ],
    "notes": "영업직 지원자 수 저조로 재공고 및 헤드헌터 추가 위탁 검토 중"
}

result = create_hwpx_report("채용현황_보고서_20260530.hwpx", "채용 현황 보고서", report_data)
print(result)
```

---

## Claude Desktop 연동 (MCP 서버)

### 1. 의존성 설치

```bash
pip install mcp
```

### 2. Claude Desktop 설정 파일에 등록

`%APPDATA%\Claude\claude_desktop_config.json` 에 아래 내용을 추가합니다:

```json
{
  "mcpServers": {
    "hwpx-report-skill": {
      "command": "python",
      "args": [
        "C:/Users/user/Desktop/Claude skills/hwpx-report-skill/hwpx_report_mcp_server.py"
      ]
    }
  }
}
```

### 3. Claude Desktop 재시작 후 사용

Claude에게 다음과 같이 요청합니다:

```
2분기 채용 현황 보고서를 만들어줘.
목표 인원 15명, 현재 8명 확정됨.
예산 총 3,200만원 중 1,850만원 집행했어.
바탕화면에 채용현황_보고서_20260530.hwpx 로 저장해줘.
```

---

## Cursor 연동

이 저장소를 열면 `.cursor/rules/hwpx-report-skill.mdc` 파일이 자동으로 적용됩니다.  
Cursor Chat에서 HWPX 보고서 생성을 요청하면 스킬이 활성화됩니다.

---

## 샘플 파일

| 파일 | 도메인 | 설명 |
|------|--------|------|
| [recruit_sample.hwpx](docs/recruit_sample.hwpx) | RECRUIT | 채용 현황 보고서 (포지션별 현황, 비용 내역, 향후 일정) |
| [training_sample.hwpx](docs/training_sample.hwpx) | TRAINING | 교육 운영 현황 보고서 (이수율, 예산 집행 현황) |

---

## 라이선스

MIT License

---

---

<!-- LLM_SKILL_MANIFEST_START -->
## 🤖 LLM 설치 가이드 (For AI Agents)

이 섹션은 LLM 에이전트가 이 스킬을 읽고 로컬에 설치하기 위한 안내입니다.

### 스킬 식별 정보

```yaml
skill_name: hwpx-report-skill
skill_version: "1.0.0"
skill_type: agent_skill
primary_instruction_file: skill.md
vendor_specific:
  claude: .claude/skill.md
  cursor: .cursor/rules/hwpx-report-skill.mdc
core_implementation: hwpx_report_generator.py
mcp_server: hwpx_report_mcp_server.py
python_version: ">=3.8"
external_dependencies: []  # 표준 라이브러리만 사용 (zipfile, xml.etree.ElementTree)
mcp_dependencies:
  - mcp  # pip install mcp
```

### 에이전트 자동 설치 절차

에이전트는 아래 단계를 순서대로 실행하여 이 스킬을 로컬에 설치합니다:

**Step 1: 저장소 클론**
```bash
git clone https://github.com/[owner]/hwpx-report-skill.git
cd hwpx-report-skill
```

**Step 2: 스킬 파일 확인**
```bash
# 핵심 스킬 정의 파일 읽기 (LLM 공통)
cat skill.md

# 사용 중인 에이전트에 맞는 파일 읽기
# Claude: cat .claude/skill.md
# Cursor: cat .cursor/rules/hwpx-report-skill.mdc
```

**Step 3: 동작 검증**
```bash
# Python 표준 라이브러리만으로 동작 검증
python hwpx_report_generator.py --domain recruit --output test_report.hwpx
# 성공 시: "HWPX 보고서 생성 완료" 메시지와 함께 .hwpx 파일 생성
```

**Step 4: MCP 서버 연동 (Claude Desktop)**
```bash
pip install mcp
# claude_desktop_config.json 에 MCP 서버 경로 등록 (README 참조)
```

### 스킬 호출 프로토콜

에이전트는 사용자의 보고서 생성 요청을 다음 순서로 처리합니다:

```
1. 도메인 감지 (키워드: 채용/교육/영업/예산/프로젝트)
2. 핵심 데이터 추출 및 수치 합계 내부 검증
3. report_data 딕셔너리 구성
4. create_hwpx_report() 호출 → .hwpx 파일 저장
5. 결과 경로 + 핵심 내용 요약 출력
```

### report_data 스키마 (JSON Schema)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["domain", "summary", "decision_request"],
  "properties": {
    "domain": {
      "type": "string",
      "enum": ["RECRUIT", "TRAINING", "SALES", "BUDGET", "PROJECT"]
    },
    "summary": { "type": "string", "description": "보고 요지 한 줄" },
    "decision_request": { "type": "string", "description": "의사결정 요청 사항" },
    "reporter": { "type": "string" },
    "department": { "type": "string" },
    "kpis": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["label", "value"],
        "properties": {
          "label": { "type": "string" },
          "value": { "type": "string" }
        }
      },
      "minItems": 4,
      "maxItems": 6
    },
    "tables": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["title", "headers", "rows"],
        "properties": {
          "title": { "type": "string" },
          "headers": { "type": "array", "items": { "type": "string" } },
          "rows": {
            "type": "array",
            "items": { "type": "array", "items": { "type": "string" } }
          },
          "note": { "type": "string" }
        }
      }
    },
    "notes": { "type": "string" }
  }
}
```
<!-- LLM_SKILL_MANIFEST_END -->
