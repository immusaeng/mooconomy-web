#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MOO:conomy 세션 부트스트랩 (start_session).
===========================================

존재 이유
  새 대화를 열 때마다 '무엇을 붙여야 하는가'를 사람이 기억해야 했다.
  그 기억이 누락되면 2~3일 만에 LLM이 완전히 새로워진다.

  이 스크립트는 그 판단을 없앤다. 명령 하나를 실행하면
  '붙여넣기용 블록 전체'가 출력된다. 사람은 복사만 한다.

      python3 tools/start_session.py --repo . --live > ~/TODAY.md

  그리고 새 대화 첫 메시지에 그 파일 내용을 붙인다.

무엇을 담는가
  A. 규칙      -> PROJECT-BRIEF.md 에서 읽는다 (사실 0개이므로 낡지 않는다)
  B. 사실      -> derive_state.py 로 매번 다시 도출한다 (손으로 쓰지 않는다)
  C. 경보      -> 치명 불일치 (있으면 지시문을 쓰면 안 된다)
  D. 결정      -> DECISIONS.log (사람이 append)
  E. 부족한 증거 -> 이 세션이 볼 수 없는 것 (거짓 확신 방지)

원칙
  출력에 사람이 쓴 '사실'은 한 줄도 없다. 전부 파일이나 도출 결과에서 온다.
  따라서 이 블록은 매일 붙여도 낡지 않는다.

종료코드
  0 = 정상 / 1 = 치명 불일치 존재 / 2 = 실행 오류
"""

import argparse
import datetime as dt
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    from derive_state import Derived  # type: ignore
except Exception as e:  # noqa: BLE001
    print("오류: derive_state.py 를 같은 폴더에서 찾지 못했다: %s" % e, file=sys.stderr)
    sys.exit(2)


EMBEDDED_RULES = """## A. 규칙 (고정 — 변경은 CEO 결정)

**역할**
- CEO: 결정·승인·우선순위. PowerShell 직접 실행(워크트리·merge·비밀값). merge는 CEO만.
- 디렉터(Genspark): 판정·지시문·PowerShell 블록·공개면 실측 검증. merge 금지, 트랙 실행 금지.
- 트랙(Orca 탭): 지시문 그대로 실행 -> 테스트 -> commit/push -> PR. merge 절대 금지.

**불변 규칙**
1. merge는 CEO가 PowerShell에서. `--merge` merge 커밋만. squash·rebase·`--delete-branch` 금지.
2. 트랙 금지: merge, rebase, force-push, dispatch, Gemini 호출(승인 없이), 키 검색·읽기,
   .env 읽기, 인자 없는 export/env/set, C:\\dev\\repos 수정, 새 브랜치 생성.
3. 워크트리·브랜치는 CEO가 먼저 생성. 생성 출력 확인 뒤 지시문을 낸다.
4. 시작 가드: 경로·브랜치명·HEAD 전체 40자 SHA·clean·origin/main 조상관계. 어긋나면 중단·보고.
5. 게이트: base를 `git archive`로 별도 추출해 브랜치와 각각 실행. 0실패 0에러.
   렌더 변경은 "플래그 0일 때 base와 바이트 동일" 별도 확인.
6. 롤백은 revert가 아니라 플래그. 새 섹션은 기본값 0으로 머지, 켜기는 별도 PR.
7. 진단과 수정의 분리. 진단 트랙은 읽기 전용.
8. 자리표시자 블록 금지. SHA 확정 전에는 머지 블록도 시작 SHA 들어간 지시문도 내지 않는다.
9. 틀린 기록은 지우지 않고 정정 이벤트를 새로 만든다.
10. cron은 건드리지 않는다. 기준은 08:00 KST 이전 발송.
11. 손으로 쓰는 문서에 사실을 적지 않는다. 도출 명령을 적는다.
12. 새 사실을 발견하면 먼저 도출기에 추가하고, 그다음 인용한다.
13. **보고에 없는 것을 사실로 말하지 않는다.** 모르면 모른다고 말한다.
"""


def read(path, default=""):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return default


def main():
    ap = argparse.ArgumentParser(description="MOO:conomy 세션 부트스트랩")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--brief", default=None,
                    help="PROJECT-BRIEF.md 경로 (기본: <repo>/PROJECT-BRIEF.md)")
    ap.add_argument("--live", action="store_true", help="공개 사이트와 대조")
    ap.add_argument("--no-rules", action="store_true", help="규칙 섹션 생략")
    ap.add_argument("--facts-only", action="store_true",
                    help="사실+경보+결정만 출력 (검수자 첨부용)")
    ap.add_argument("--docx", default=None,
                    help="AI Chat 첨부용 .docx 생성 경로")
    args = ap.parse_args()

    repo = os.path.abspath(args.repo)
    if not os.path.isdir(os.path.join(repo, ".git")):
        print("오류: %s 는 git 저장소가 아니다" % repo, file=sys.stderr)
        return 2

    brief_path = args.brief or os.path.join(repo, "PROJECT-BRIEF.md")
    brief_body = read(brief_path)
    decisions = read(os.path.join(repo, "DECISIONS.log"))

    try:
        d = Derived(repo)
        facts, alarms = d.run(do_live=args.live)
    except Exception as e:  # noqa: BLE001
        print("도출 오류: %s" % e, file=sys.stderr)
        return 2

    # derive_state 모듈의 paste_block 재사용
    try:
        from derive_state import paste_block  # type: ignore
    except Exception:  # noqa: BLE001
        paste_block = None

    L = []
    L.append("# MOO:conomy 세션 부트스트랩")
    L.append("<!-- 이 블록은 도구가 생성했다. 손으로 고치지 말 것. "
             "고칠 것이 있으면 원본 파일을 고치고 다시 실행할 것. -->")
    L.append("<!-- 생성: %s · 저장소 HEAD %s -->"
             % (facts.get("derived_at"), facts.get("repo_head_short")))
    L.append("")

    if args.facts_only:
        L = []
        L.append("# MOO:conomy 검수자 첨부 — 도출된 사실")
        L.append("<!-- 도구 생성. 손으로 고치지 말 것. 고칠 것은 원본을 고치고 재실행. -->")
        L.append("")
        if paste_block:
            L.append(paste_block(facts, alarms))
        L.append("")
        L.append("## 경보 — 치명 불일치 %d건" % len(alarms))
        for a in alarms:
            L.append("- %s" % a)
        L.append("")
        L.append("## 결정 (DECISIONS.log)")
        L.append("```")
        L.append(decisions.strip()[:6000] if decisions else "없음")
        L.append("```")
        out = "\n".join(L)
        rc = 1 if alarms else 0
        print(out)
        _emit_docx(args, out, facts)
        return rc

    # A. 규칙
    if not args.no_rules:
        if brief_body:
            L.append(brief_body.strip())
        else:
            L.append("<!-- PROJECT-BRIEF.md 를 찾지 못해 내장 규칙을 사용한다 -->")
            L.append(EMBEDDED_RULES)
        L.append("")

    # B. 사실
    L.append("---")
    L.append("")
    if paste_block:
        L.append(paste_block(facts, alarms))
    else:
        L.append("## B. 도출된 사실")
        L.append("- HEAD `%s`" % facts.get("repo_head_short"))
        L.append("- %s" % facts.get("count_definition"))
    L.append("")

    # C. 경보
    L.append("---")
    L.append("")
    if alarms:
        L.append("## C. 경보 — 치명 불일치 %d건" % len(alarms))
        L.append("**이 상태로 지시문을 쓰지 말 것. 아래가 최우선 작업이다.**")
        for a in alarms:
            L.append("- %s" % a)
    else:
        L.append("## C. 경보")
        L.append("치명 불일치 0건.")
    L.append("")

    # D. 결정
    L.append("---")
    L.append("")
    L.append("## D. 결정 (DECISIONS.log)")
    if decisions:
        L.append("```")
        L.append(decisions.strip()[:4000])
        L.append("```")
    else:
        L.append("`DECISIONS.log` 없음 — CEO 결정을 여기에 쌓아야 한다.")
        L.append("(이 파일이 없으면 '왜 이렇게 했는가'가 세션마다 사라진다)")
    L.append("")

    # E. 부족한 증거
    L.append("---")
    L.append("")
    L.append("## E. 이 세션이 볼 수 없는 것 (거짓 확신 방지)")
    L.append("")
    L.append("디렉터는 아래를 **볼 수 없다.** 없다고 보고하면 추측하지 말 것:")
    L.append("")
    L.append("- `immusaeng/daily-mooconomy` (비공개) — 코드·PR·게이트·워크플로 상태")
    L.append("- Windows 환경, Orca 탭, 워크트리, `.env`, 비밀값")
    L.append("- 저장소에 push된 커밋 (디렉터는 블록만 만들고 CEO가 실행한다)")
    L.append("")
    L.append("볼 수 있는 것: `mooconomy-web`(공개 클론), 모든 공개 URL, "
             "샌드박스 실행 환경(git·gh·python3).")
    L.append("")
    L.append("### 부족한 입력 (있으면 이어서 붙일 것)")
    L.append("- `HANDOFF-METHOD.md` 원문")
    L.append("- MOO:Q 질문 생성·채점 모듈")
    L.append("- `run_all_tests.py` + `.github/workflows/daily.yml`")
    L.append("- `state.md` / `state-head.md` + #248 샘플 4건")
    L.append("")
    L.append("### 첫 3동작")
    L.append("```")
    L.append("1) python3 tools/derive_state.py --repo . --live --paste")
    L.append("2) python3 checks/check_public_surface.py --issues 10")
    L.append("3) 위 FAIL과 입력을 근거로만 지시문을 쓴다. 근거가 없으면 입력을 요청한다.")
    L.append("```")

    out = "\n".join(L)
    print(out)

    _emit_docx(args, out, facts)
    return 1 if alarms else 0


def _emit_docx(args, out, facts):
    if args.docx:
        try:
            from docx import Document
            from docx.shared import Pt
            doc = Document()
            st = doc.styles["Normal"]
            st.font.name = "Malgun Gothic"
            st.font.size = Pt(10)
            doc.add_heading("MOO:conomy 세션 사실 (도출값)", level=1)
            doc.add_paragraph(
                "이 문서는 도구가 저장소에서 도출한 실측값이다. 사람이 쓴 것이 아니다. "
                "문서와 기억이 다르면 이 문서가 맞다. 생성: %s · HEAD %s"
                % (facts.get("derived_at"), facts.get("repo_head_short"))
            )
            for line in out.split("\n"):
                ls = line.strip()
                if not ls:
                    continue
                if ls.startswith("#"):
                    lvl = min(len(ls) - len(ls.lstrip("#")), 3)
                    doc.add_heading(ls.lstrip("# ").strip(), level=lvl)
                elif ls.startswith(("- ", "* ")):
                    doc.add_paragraph(ls[2:], style="List Bullet")
                elif re.match(r"^\d+\.\s", ls):
                    doc.add_paragraph(re.sub(r"^\d+\.\s*", "", ls), style="List Number")
                else:
                    doc.add_paragraph(ls)
            doc.save(args.docx)
            print("[docx] %s 생성" % args.docx, file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print("[docx] 생성 실패: %s" % e, file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
