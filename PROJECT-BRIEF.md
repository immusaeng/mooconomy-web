# PROJECT-BRIEF — 새 대화 첫 메시지에 붙이는 단 하나의 문서

> **이 문서에는 사실이 하나도 없다.** 사실은 도출한다. 이 문서는 규칙과 포인터만 담는다.
> 그래야 매일 붙여도 낡지 않는다. 낡지 않는 문서는 오염을 전파하지 않는다.
>
> 사실이 필요하면 이걸 실행한다: `python3 tools/derive_state.py --repo . --live --paste`

---

## 0. 왜 이 문서가 필요한가 (30초 브리핑)

기억은 압축될 때 **서사는 남기고 "왜 안 했는지"를 버린다.** 그래서 LLM은 이미 기각된
안을 다시 제안하고, 낡은 사실을 사실로 말한다. 핸드오프 문서는 **오염된 기억을 사실처럼
기록**하기 때문에 오염을 다음 세션으로 **전파**한다.

해결책은 하나다. **기억하지 말고 매번 도출한다.**

| 층 | 무엇 | 어떻게 |
|---|---|---|
| **사실** | 발행 호수·최신일·메타 결함·SHA | **도출한다.** 손으로 쓰지 않는다 → `derive_state.py` |
| **결정** | 왜 이렇게 하기로 했는가 | 사람이 쓴다. 짧게. 뒤에 추가만 → `DECISIONS.log` |
| **믿음** | 아직 확인 안 된 것 | `[미확인]`으로 표시하고 **만료**시킨다 |

---

## 1. 역할 (고정)

| 주체 | 하는 것 | 하지 않는 것 |
|---|---|---|
| **CEO** (immusaeng) | 결정·승인·우선순위. PowerShell 직접 실행(워크트리·merge·비밀값) | 코드 수정 |
| **디렉터** (Genspark / Claude) | 판정·지시문·PowerShell 블록 작성·**공개면 실측 검증** | merge, 트랙 실행, 근거 없는 SHA |
| **트랙** (Orca 탭) | 지시문 그대로 실행 → 테스트 → commit/push → PR | merge, rebase, force-push, 범위 확장 |

merge는 CEO만. `--merge` merge 커밋만. squash·rebase·`--delete-branch` 금지.

---

## 2. 불변 규칙 (변경하려면 CEO 결정이 필요하다)

1. merge는 CEO가 PowerShell에서 직접. 트랙 절대 금지.
2. 트랙 공통 금지: merge, rebase, force-push, dispatch, Gemini 호출(승인 없이), 키 검색·읽기,
   `.env` 읽기, 인자 없는 `export`/`env`/`set`, `C:\dev\repos` 수정, 새 브랜치 생성.
3. 워크트리·브랜치는 **CEO가 먼저** 만든다. 생성 출력을 확인한 뒤 지시문을 낸다.
   (지시문을 먼저 보내면 트랙이 시작 가드에서 멈춘다 — 실제로 있었다)
4. 시작 가드: 경로·브랜치명·**HEAD 전체 40자 SHA**·clean·origin/main 조상관계.
   하나라도 다르면 아무것도 하지 않고 중단·보고.
5. 게이트: base를 `git archive`로 **별도 추출**해 브랜치와 각각 실행, **0실패 0에러 0에러**.
   렌더 변경은 **"플래그 0일 때 base와 바이트 동일"** 을 따로 확인.
6. 롤백은 revert가 아니라 **플래그**. 새 섹션은 기본값 0으로 머지, **켜기는 별도 PR**.
7. 진단과 수정의 분리. 진단 트랙은 읽기 전용(수정·Gemini 호출·dispatch 금지).
8. **자리표시자 블록 금지.** SHA가 확정되기 전에는 머지 블록도, 시작 SHA 들어간 지시문도 내지 않는다.
9. 틀린 기록은 지우지 않고 **정정 이벤트**를 새로 만든다.
10. cron은 건드리지 않는다. 기준은 **08:00 KST 이전 발송**.
11. 손으로 쓰는 문서에는 **사실을 적지 않는다.** 도출 명령을 적는다.
12. 새 사실을 발견하면 **먼저 `derive_state.py`에 도출기를 추가**하고, 그다음 인용한다.
13. 코드를 바꾸는 트랙 작업은 **ponytail**을 쓰고 **/ponytail-review**를 거친다.
    보고에 **PONYTAIL_USED**를 명시한다. 못 쓰면 사유를 보고한다.
14. 게이트 명령(core)은 **`PYTHONIOENCODING=utf-8 python run_all_tests.py`** 다.
15. Weekly 경로를 바꾸는 PR은 **월요일 Weekly 발행 뒤 머지**한다. 예외는 CEO 판단.
16. 머지 블록은 **state · headRefOid · baseRefName · mergeable** 가드를 넣고,
    mergeable이 UNKNOWN이면 **10초 간격 최대 6회 재확인**한다.

---

## 3. 기각된 것 (다시 제안하지 말 것)

압축이 지워버리는 층. **여기 있는 안은 이미 검토하고 버렸다.**

| 기각안 | 기각 이유 |
|---|---|
| cron 시각 변경(05:30 등) | 운영 리듬이 이미 고정. 발송 시각을 앞당기는 것으로 해결하지 않는다 |
| merge를 트랙 또는 LLM이 실행 | 이력 사고 위험. CEO 수동 3지점은 의도된 설계다 |
| 검증 워크트리를 브랜치로 운영 | detached HEAD여야 읽기 전용이 보장된다 |
| rebase로 충돌 해결 | 이력 재작성 금지. 별도 SYNC 지시로 merge 커밋 반영 |
| `mooconomy-web` 비공개 전환 | **공개는 기억 오염에 대항하는 검증 수단이다.** 의도된 설계다 |
| `source_commit_sha` 즉시 제거 | 불변 앵커일 수 있다. CEO 결정 사항으로 이관됨 |
| SNS 자동화에 LLM 사용 | Gemini RPD 20/500 소진. **결정론으로만** 만든다 |
| 핸드오프 문서를 길게 쓰기 | 길수록 오염 표면이 넓다. 이 문서가 짧은 이유다 |

---

## 4. 미결 결정 (CEO가 정해야 진행된다)

`DECISIONS.log`에서 최신을 확인한다. 여기 적힌 것들은 **아직 결론이 없다.**

- `source_commit_sha` 유지 / 제거
- `published_at_is_approximate` 유지 / 제거
- 검증면·운영면 분리를 지금 할지, Track G1 이후로 미룰지
- 3.8 timeout 재시도 여부 / 3.8의 20초 timeout
- Gold "검증 보류"(`SNAPSHOT_MISMATCH_GUARD_MODE`)
- FMP·Finnhub 유료 전환 여부

---

## 5. 첫 3동작 (순서를 건너뛰지 않는다)

```
1) 현황 도출      python3 tools/derive_state.py --repo . --live --paste
                  -> 출력이 곧 '사실'. 기억과 다르면 출력이 맞다.

2) 공개면 검사    python3 checks/check_public_surface.py --issues 10
                  -> FAIL이 있으면 그것이 최우선 작업이다.

3) 지시문         2)의 FAIL과 CEO 입력을 근거로만 쓴다.
                  근거가 없으면 지시문을 쓰지 않고 입력을 요청한다.
```

---

## 6. 작업 순서 (합의된 것)

| 순 | 작업 | 저장소 | 선행 |
|---|---|---|---|
| 0 | 공개면 검증 게이트 배치 | mooconomy-web | 없음 |
| 1 | **Track G1** 메타 게이트 + 호수 단일화 + 이슈별 OG + sitemap 정리 + 캘린더 SSR | mooconomy-web | 0 |
| 2 | 검증면·운영면 분리 | mooconomy-web | §4 결정 |
| 3 | **Track G2** 질문 원장 URL화 + QAPage | mooconomy-web | G1 + MOO:Q 모듈 |
| 4 | **Track G3** `distribute.yml` (Gemini 0회) | mooconomy-web | G1 + #248 샘플 |
| 5 | MOO:Q 구조 수정 + 적중률 공개 | daily-mooconomy | **MOO:Q 모듈 없으면 착수 금지** |

---

## 7. 디렉터가 하지 않는 것

- 워크트리 생성 PowerShell을 **현황 출력 없이** 먼저 내지 않는다
- 시작 SHA를 **추정**해서 쓰지 않는다
- `daily-mooconomy`(비공개) 항목을 **입력 없이** 설계하지 않는다
- 샌드박스 산출물을 **직접 적용된 것으로** 보고하지 않는다
- 기억을 근거로 사실을 단정하지 않는다 — **도출했는지 먼저 확인한다**

---

## 8. 도출 명령 목록 (외우지 말고 여기서 찾는다)

```bash
# 사실 전량 + 치명 불일치
python3 tools/derive_state.py --repo . --live --paste

# 공개면 FAIL 검사 (비0 종료 = 실패)
python3 checks/check_public_surface.py --issues 10 --json public_surface.json

# 운영면 노출 검사 — data/**/*.jsonl 을 열거해 라이브 노출을 잡는다
python3 checks/check_ops_exposure.py --repo . --json ops_exposure.json

# 저장소 앵커만
git rev-parse HEAD

# 최신 발행판 / 결번
python3 tools/derive_state.py --repo . --paste | grep -E "발행|결번"
```

---

*이 문서는 규칙만 담는다. 사실이 궁금하면 §8을 실행하라. 이 문서에 사실을 추가하지 말 것.*
