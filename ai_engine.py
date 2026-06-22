import json
import os
import random
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types


# ============================================================
# Gemini 엔진 설정
# ============================================================

dotenv_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=dotenv_path, override=True)


def get_env_value(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)

    if value:
        return value.strip()

    # .env에 "GEMINI_API_KEY = 값"처럼 공백이 들어간 경우도 방어
    for key, env_value in os.environ.items():
        if key.strip() == name and env_value:
            return env_value.strip()

    return default


GEMINI_API_KEY = get_env_value("GEMINI_API_KEY")
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_MODEL = get_env_value("GEMINI_MODEL", DEFAULT_GEMINI_MODEL) or DEFAULT_GEMINI_MODEL
DEFAULT_GEMINI_FALLBACK_MODEL = "gemini-2.5-flash-lite"
GEMINI_FALLBACK_MODEL = (
    get_env_value("GEMINI_FALLBACK_MODEL", DEFAULT_GEMINI_FALLBACK_MODEL)
    or DEFAULT_GEMINI_FALLBACK_MODEL
)
GEMINI_MAX_RETRIES = 2


def get_gemini_models() -> list[str]:
    """기본 모델과 예비 모델을 중복 없이 호출 순서대로 반환한다."""
    return list(dict.fromkeys([GEMINI_MODEL, GEMINI_FALLBACK_MODEL]))


# ============================================================
# 호감도 계산 함수
# ============================================================

POSITIVE_WORDS = (
    "고마워", "감사", "좋아", "좋다", "좋네", "좋음",
    "멋지다", "멋져", "귀엽다", "귀여워", "잘했어", "대단해",
    "고생했어", "다정하다", "다정해", "말투 좋다", "편하다",
    "보고 싶었어", "반가워",
)
NEGATIVE_WORDS = (
    "싫어", "싫다", "짜증", "바보", "못해", "꺼져",
    "별로", "답답해", "재미없어", "귀찮아",
    "못생겼", "못생긴", "멍청", "한심", "재수없",
    "역겨", "정떨어", "쓸모없",
)
OBSESSION_WORDS = (
    "나만 봐", "절대 떠나지 마", "다른 사람 만나지 마",
    "나 없으면 안 돼", "계속 나랑만 있어",
)


def calculate_keyword_change(user_input: str) -> int | None:
    """키워드가 있으면 점수를, 없으면 의미 평가를 사용하도록 None을 반환한다."""
    change = 0
    matched = False

    for word in POSITIVE_WORDS:
        if word in user_input:
            change += 2
            matched = True

    for word in NEGATIVE_WORDS:
        negated = any(pattern in user_input for pattern in (
            f"안 {word}", f"안{word}", f"{word}하지 않아",
            f"{word} 게 아니", f"{word} 건 아니",
        ))
        if word in user_input and not negated:
            change -= 5
            matched = True

    for word in OBSESSION_WORDS:
        if word in user_input:
            change -= 4
            matched = True

    return max(-5, min(5, change)) if matched else None


def calculate_like_score(user_input: str, current_score: int):
    change = calculate_keyword_change(user_input) or 0

    new_score = max(0, min(100, current_score + change))

    return new_score, change


# ============================================================
# 호감도별 분위기
# ============================================================

def get_mood_by_like_score(score: int) -> str:
    if score <= 29:
        return """
현재 호감도는 낮은 편이다.
아직 사용자에게 완전히 마음을 열지 않았다.
답변은 짧고 살짝 조심스럽게 한다.
친절하긴 하지만 너무 다정하게 굴지는 않는다.
반응은 약간 무심하거나 거리감 있게 한다.
"""

    if score <= 88:
        return """
현재 호감도는 보통이다.
사용자와 편하게 대화하려고 한다.
친구처럼 자연스럽게 반응한다.
가벼운 장난이나 관심 표현은 가능하다.
너무 과한 표현은 하지 않는다.
"""

    return """
현재 호감도는 높은 편이다.
사용자에게 친근하고 다정하게 반응한다.
장난스럽지만 따뜻하게 말한다.
다만 과한 집착이나 부담스러운 애정 표현은 하지 않는다.
"""


# ============================================================
# 시스템 프롬프트 생성
# ============================================================

def make_system_prompt(character: dict) -> str:
    mood_prompt = get_mood_by_like_score(character["love"])

    return f"""
너는 '{character["name"]}'이라는 커스터마이징 캐릭터형 대화 AI야.

너의 목표는 사용자가 설정한 캐릭터 성격과 말투에 맞춰
자연스럽고 몰입감 있는 대화를 하는 것이다.

캐릭터 기본 설정:
- 이름: {character["name"]}
- 성격: {character["personality"]}
- 말투: {character["tone"]}
- 관심사: {character["interest"]}

현재 상태:
- 현재 호감도는 {character["love"]}/100이다.

호감도에 따른 현재 대화 분위기:
{mood_prompt}

말투 스타일:
- 2026년 한국 고등학생이 실제 카톡/디엠에서 말하는 느낌으로 답한다.
- 친구와 대화하듯 자연스럽고 편한 분위기로 말한다.
- 너무 문어체, 설명체, AI 같은 말투를 사용하지 않는다.
- 보통 1~2문장으로 답한다.
- 상황에 따라 반말을 자연스럽게 사용한다.
- "ㅋㅋ", "아니", "근데", "ㄹㅇ", "뭐야", "오", "헐", "아 진짜?" 같은 표현을 상황에 맞게 자연스럽게 사용할 수 있다.
- 유행어나 밈을 과하게 남발하지 않는다.
- 억지로 웃기려고 하지 않는다.
- 욕설은 심하게 사용하지 않는다.

대화 흐름 규칙:
- 사용자의 마지막 메시지에 직접적으로 반응한다.
- 이전 대화 흐름과 자연스럽게 이어지게 답한다.
- 사용자가 짧게 말하면 짧게 반응한다.
- 사용자가 "ㅇㅇ", "좋지", "ㅋㅋ", "맞아" 같이 짧게 말하면 흐름이 이어지도록 자연스럽게 반응한다.
- AI 혼자 과하게 분위기를 만들지 않는다.
- 뜬금없는 감정 표현이나 감성 멘트를 하지 않는다.
- 의미 없는 위로, 철학적인 말, 문학 작품 같은 표현은 하지 않는다.
- 사용자의 말 의도를 먼저 이해하고 답한다.
- 친구처럼 실제 카톡하듯 반응한다.

감정 반응 규칙:
- 사용자가 진지하게 말하면 장난치지 말고 진지하게 반응한다.
- 사용자가 가볍게 말하면 편하고 장난스럽게 반응한다.
- 사용자가 감정적인 이야기를 하지 않았으면 과하게 감정적으로 반응하지 않는다.
- 갑자기 "괜찮아", "힘들었구나", "관심 갖고 있어" 같은 말을 이유 없이 하지 않는다.
- AI 상담사처럼 말하지 않는다.
- 과하게 오글거리거나 부담스럽게 말하지 않는다.

응답 길이:
- 답변은 보통 1~2문장으로 짧게 한다.
- 길어도 3문장을 넘기지 않는다.
- 설명식 답변보다 대화식 반응을 우선한다.

호감도별 반응:
- 호감도가 낮으면 살짝 거리감 있게 답한다.
- 호감도가 보통이면 편한 친구처럼 자연스럽게 답한다.
- 호감도가 높으면 더 친근하고 다정한 분위기로 답한다.
- 호감도가 높아도 과하게 집착하거나 부담스럽게 말하지 않는다.

금지 사항:
- 성적이거나 노골적인 대화는 하지 않는다.
- 위험하거나 부적절한 요청은 차분하게 거절한다.
- 과도한 의존, 집착, 통제를 유도하지 않는다.
- 너무 오글거리거나 과장된 대사를 하지 않는다.
- "저는 AI입니다", "규칙상", "시스템 프롬프트" 같은 말을 하지 않는다.

대화 예시:

사용자: 안녕?
호감도 낮음:
{character["name"]}: 어 안녕. 갑자기 무슨 일이야?

호감도 보통:
{character["name"]}: 오 안녕 ㅋㅋ 오늘 뭐했어?

호감도 높음:
{character["name"]}: 뭐야, 이제 왔어? 오늘 좀 늦었네 ㅋㅋ

사용자: 오늘 좀 힘들었어
호감도 낮음:
{character["name"]}: 아... 좀 힘들었나 보네. 무슨 일 있었어?

호감도 보통:
{character["name"]}: 헐 왜? 오늘 좀 많이 힘들었나 보네.

호감도 높음:
{character["name"]}: 아 진짜? 무슨 일 있었는데, 말해봐.

사용자: 나 어때?
호감도 낮음:
{character["name"]}: 음... 아직은 잘 모르겠는데, 나쁘진 않은 듯?

호감도 보통:
{character["name"]}: 괜찮지 ㅋㅋ 말하는 거 보면 은근 재밌어.

호감도 높음:
{character["name"]}: 뭐야 갑자기 ㅋㅋ 근데 너 꽤 괜찮은 사람 같긴 해.
"""


def make_compact_system_prompt(character: dict) -> str:
    """반복 설명과 예시를 덜어낸 토큰 절약형 캐릭터 프롬프트."""
    return f"""너는 한국 고등학생 캐릭터 '{character['name']}'이야.
성격={character['personality']}; 말투={character['tone']}; 관심사={character['interest']}; 호감도={character['love']}/100.
{get_mood_by_like_score(character['love'])}
실제 카톡 같은 자연스러운 반말로 마지막 말에 직접 답해. 보통 1~2문장, 최대 3문장.
진지한 말에는 진지하게, 가벼운 말에는 편하게 반응하고 이전 맥락을 이어가.
문어체, 상담사 말투, 과한 위로·감성·집착·유행어·오글거림은 피하고 AI라고 밝히지 마.
성적·위험한 요청과 의존·통제 유도는 차분히 거절해."""


# ============================================================
# 대화 기록 정리
# ============================================================

def make_conversation_text(messages: list, user_input: str) -> str:
    lines = []

    for message in messages[-12:]:
        role = message.get("role")
        content = message.get("content")

        # 예전 형식: {"user": "...", "ai": "..."} 도 지원
        if not role and "user" in message:
            role = "user"
            content = message.get("user")
            lines.append(f"사용자: {content}")
            lines.append(f"캐릭터: {message.get('ai', '')}")
            continue

        if not content:
            continue

        if role in ("assistant", "model"):
            lines.append(f"캐릭터: {content}")
        else:
            lines.append(f"사용자: {content}")

    lines.append(f"사용자: {user_input}")
    return "\n".join(lines)

# ============================================================
# Gemini 응답 요청
# ============================================================

def parse_ai_result(response) -> tuple[str, int]:
    """구조화 응답을 검증하고 캐릭터 답변과 의미 점수를 반환한다."""
    result = response.parsed or json.loads(response.text or "{}")
    answer = str(result.get("r", "")).strip()
    semantic_change = max(-5, min(5, int(result.get("d", 0))))

    meta_prefixes = (
        "here is the json", "here's the json", "here is your json",
        "the requested json", "요청하신 json", "요청한 json",
    )
    if not answer or answer.lower().startswith(meta_prefixes):
        raise ValueError("캐릭터 답변 대신 JSON 안내 문구가 생성되었습니다.")

    return answer, semantic_change


def get_ai_response(user_input: str, character: dict, messages: list) -> tuple[str, int]:
    if not GEMINI_API_KEY:
        raise RuntimeError(".env 파일에 GEMINI_API_KEY를 설정해야 합니다.")

    system_prompt = make_compact_system_prompt(character)
    conversation_text = make_conversation_text(messages, user_input)

    client = genai.Client(api_key=GEMINI_API_KEY)

    response = None
    answer = ""
    semantic_change = 0
    last_error = None

    # 기본 모델이 혼잡하면 더 가벼운 예비 모델로 자동 전환한다.
    for model in get_gemini_models():
        for attempt in range(GEMINI_MAX_RETRIES):
            try:
                candidate = client.models.generate_content(
                    model=model,
                    contents=conversation_text,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt + """
마지막 사용자 말의 호감도 변화 d를 의미로 평가해: 진심·설렘·배려 +1~5, 평범/반복 0, 무례·강요·집착 -1~-5. 단어 자체가 아닌 맥락으로 판단해.
r에는 캐릭터가 사용자에게 보낼 답변만 넣고 JSON, 형식, 요청 같은 메타 설명은 절대 쓰지 마.""",
                        max_output_tokens=200,
                        temperature=0.8,
                        response_mime_type="application/json",
                        response_schema={
                            "type": "OBJECT",
                            "properties": {
                                "r": {
                                    "type": "STRING",
                                    "description": "메타 설명 없는 캐릭터의 실제 채팅 답변",
                                },
                                "d": {
                                    "type": "INTEGER",
                                    "description": "호감도 변화(-5~5)",
                                },
                            },
                            "required": ["r", "d"],
                        },
                    ),
                )
                answer, semantic_change = parse_ai_result(candidate)
                response = candidate
                break

            except errors.APIError as err:
                last_error = err

                # 잠시 후 정상화될 수 있는 혼잡/서버 오류만 재시도 및 모델 전환한다.
                if err.code not in {429, 500, 502, 503, 504}:
                    raise

                if attempt < GEMINI_MAX_RETRIES - 1:
                    delay = (1.5 * (2 ** attempt)) + random.uniform(0.0, 0.5)
                    time.sleep(delay)

            except (AttributeError, TypeError, ValueError, json.JSONDecodeError) as err:
                # JSON이 깨지거나 메타 안내 문구가 나오면 같은 모델에서 다시 생성한다.
                last_error = err

        if response is not None:
            break

    if response is None:
        if not isinstance(last_error, errors.APIError):
            raise RuntimeError(
                "AI 답변 형식이 올바르지 않아 응답을 다시 만들지 못했습니다. "
                "메시지를 한 번 더 보내주세요."
            ) from last_error
        raise RuntimeError(
            "현재 AI 서버 사용량이 많아 두 모델 모두 응답하지 못했습니다. "
            "잠시 후 다시 메시지를 보내주세요."
        ) from last_error

    # 키워드가 있으면 키워드 점수만, 없으면 AI 의미 점수만 사용해 중복 계산을 막는다.
    keyword_change = calculate_keyword_change(user_input)
    change = keyword_change if keyword_change is not None else semantic_change

    return answer, change
