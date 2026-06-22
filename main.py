"""
커스터마이징 연애 시뮬레이터
NiceGUI + Gemini API 기반 대화형 웹 앱
@ui.page 사용으로 사용자마다 독립된 상태 보장
"""
import os
import asyncio
import traceback
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from nicegui import ui
from ai_engine import get_ai_response
from memory import save_session, load_session


# ============================================================
# 상수
# ============================================================

DEFAULT_CHARACTER = {
    "name":        "연우",
    "personality": "조용하지만 은근 장난기 있고, 친해지면 편하게 대화하는 성격",
    "tone":        "친구처럼 편하게 말하고, 너무 오글거리지 않게 짧고 자연스럽게 답하는 말투",
    "interest":    "게임, 음악, 유튜브",
    "emotion":     "편안함",
    "love":        50,
}

LOVE_MILESTONES = {
    30:  {"emoji": "🌱", "message": "슬슬 친해지는 것 같아요!"},
    70:  {"emoji": "💛", "message": "꽤 친해졌어요!"},
    100: {"emoji": "💜", "message": "최고 호감도 달성!"},
}

MENU_STRUCTURE = [
    ("setup",    "home",        "시작 설정"),
    ("chat",     "chat_bubble", "채팅"),
    ("settings", "tune",        "캐릭터 설정"),
    ("emotion",  "favorite",    "감정 상태"),
    ("info",     "info",        "정보"),
]

CHARACTER_PRESETS = [
    {
        "label": "편안한 친구", "name": "연우",
        "personality": "조용하지만 은근 장난기 있고, 친해지면 편하게 대화하는 성격",
        "tone": "친구처럼 편하게 말하고, 너무 오글거리지 않게 짧고 자연스럽게 답하는 말투",
        "interest": "게임, 음악, 유튜브",
    },
    {
        "label": "다정한 선배", "name": "하린",
        "personality": "차분하고 다정하며, 상대 이야기를 잘 들어주는 성격",
        "tone": "부담스럽지 않게 따뜻하고 안정감 있게 답하는 말투",
        "interest": "카페, 산책, 영화",
    },
    {
        "label": "장난기 많은 친구", "name": "도윤",
        "personality": "밝고 장난기가 많지만 선은 넘지 않는 편한 성격",
        "tone": "짧게 농담을 섞어 말하되 자연스럽고 가볍게 답하는 말투",
        "interest": "게임, 밈, 운동",
    },
]


# ============================================================
# CSS
# ============================================================

_HEAD_HTML = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900&family=Noto+Sans+KR:wght@400;500;600;700;800;900&display=swap">
<link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons+Round">
<style>
/* ═══════════════════════════════════════
   Design Tokens
═══════════════════════════════════════ */
:root {
    /* Surface layers */
    --bg:   #080910;
    --s1:   #0c0d15;   /* sidebar */
    --s2:   #101118;   /* cards */
    --s3:   #161722;   /* elevated / input */
    --s4:   #1c1d2c;   /* hover */
    --s5:   #22233a;   /* active hover */

    /* Borders */
    --b1: rgba(255,255,255,0.045);
    --b2: rgba(255,255,255,0.08);
    --b3: rgba(255,255,255,0.13);

    /* Text */
    --t1: #edeef8;
    --t2: #7e82a2;
    --t3: #454666;

    /* Accent */
    --a:    #6366f1;
    --a2:   #818cf8;
    --a3:   #a5b4fc;
    --adim: rgba(99,102,241,0.13);
    --aglow:rgba(99,102,241,0.28);

    /* Semantic */
    --green: #22c55e;
    --red:   #ef4444;

    /* Motion */
    --spring: cubic-bezier(0.34,1.56,0.64,1);
    --ease:   cubic-bezier(0.16,1,0.3,1);
}

/* ═══════════════════════════════════════
   Base
═══════════════════════════════════════ */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body {
    width: 100%;
    height: 100%;
    margin: 0;
    padding: 0;
    overflow: hidden;
}

body {
    background: var(--bg);
    color: var(--t1);
    font-family: 'Inter', 'Noto Sans KR', 'Malgun Gothic', system-ui, -apple-system, sans-serif;
    font-size: 14px;
    line-height: 1.55;
    letter-spacing: -0.012em;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    font-feature-settings: 'cv02','cv03','cv04','cv11','ss01';
}

/* ── NiceGUI / Quasar 기본값 초기화 ── */
.nicegui-content {
    width: 100vw !important;
    padding: 0 !important;
    height: 100vh !important;
    overflow: hidden !important;
    display: flex !important;
    flex-direction: column !important;
}

.q-page-container { padding-top: 0 !important; }
.q-page { min-height: unset !important; padding: 0 !important; }
#q-app, .q-layout, .q-page-container, .q-page {
    width: 100% !important;
    height: 100% !important;
    overflow: hidden !important;
}

/* Quasar row에서 wrap 방지 (사이드바가 줄바꿈되는 문제) */
.app-shell.row { flex-wrap: nowrap !important; }

/* Quasar column 기본 gap 제거 */
.sidebar.column,
.main-panel.column { gap: 0 !important; }

/* ═══════════════════════════════════════
   App Shell
═══════════════════════════════════════ */
.app-shell {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    align-items: stretch !important;
    width: 100vw !important;
    height: 100vh !important;
    overflow: hidden !important;
}

/* ═══════════════════════════════════════
   Sidebar
═══════════════════════════════════════ */
.sidebar {
    display: flex !important;
    flex-direction: column !important;
    width: 220px !important;
    min-width: 220px !important;
    height: 100vh !important;
    flex-shrink: 0 !important;
    background: var(--s1);
    border-right: 1px solid var(--b1);
    position: relative;
    z-index: 10;
    overflow: hidden;
}

.sidebar-top {
    padding: 18px 14px 14px;
    border-bottom: 1px solid var(--b1);
}

.sidebar-nav {
    padding: 8px;
    flex: 1;
    overflow-y: auto;
}

.sidebar-footer {
    padding: 10px 8px;
    border-top: 1px solid var(--b1);
}

/* Brand */
.brand-logo {
    width: 30px; height: 30px;
    border-radius: 9px;
    background: linear-gradient(135deg, var(--a) 0%, #a78bfa 100%);
    display: flex; align-items: center; justify-content: center;
    color: #fff; font-weight: 900; font-size: 14px;
    box-shadow: 0 0 0 1px rgba(255,255,255,.12) inset,
                0 4px 16px var(--aglow);
    flex-shrink: 0;
}
.brand-name {
    font-size: 13px; font-weight: 700;
    color: var(--t1); letter-spacing: -.2px;
    line-height: 1.2;
}
.brand-sub { font-size: 11px; color: var(--t3); }

/* Nav label */
.nav-label {
    font-size: 10px; font-weight: 700; color: var(--t3);
    letter-spacing: .1em; text-transform: uppercase;
    padding: 0 10px; margin-bottom: 4px; display: block;
}

/* Nav item */
.nav-item {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 10px; border-radius: 9px;
    cursor: pointer; user-select: none;
    color: var(--t2); font-size: 13px; font-weight: 500;
    width: 100%; margin-bottom: 1px;
    transition: background .14s var(--ease), color .14s, box-shadow .14s;
    position: relative;
}
.nav-item::before {
    content: '';
    position: absolute; left: 0; top: 50%; transform: translateY(-50%);
    width: 3px; height: 0; border-radius: 0 3px 3px 0;
    background: var(--a);
    transition: height .2s var(--spring);
}
.nav-item:hover {
    background: rgba(255,255,255,.04);
    color: var(--t1);
}
.nav-item.active {
    background: var(--adim);
    color: var(--a3);
    font-weight: 600;
}
.nav-item.active::before { height: 22px; }

.mat-icon {
    font-family: 'Material Icons Round';
    font-size: 18px; line-height: 1;
    flex-shrink: 0;
}

/* Sidebar footer char card */
.char-card {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 10px; border-radius: 10px;
    background: var(--s2); border: 1px solid var(--b1);
    cursor: pointer;
    transition: background .15s, border-color .15s, box-shadow .15s;
}
.char-card:hover {
    background: var(--s3);
    border-color: var(--b2);
    box-shadow: 0 4px 16px rgba(0,0,0,.3);
}
.char-name { font-size: 12.5px; font-weight: 700; color: var(--t1); line-height: 1.2; }
.char-sub  { font-size: 11px; color: var(--t2); }

/* ═══════════════════════════════════════
   Main Panel
═══════════════════════════════════════ */
.main-panel {
    flex: 1 1 0 !important;
    height: 100vh !important;
    min-width: 0 !important;
    max-width: calc(100vw - 220px) !important;
    display: flex !important;
    flex-direction: column !important;
    background: var(--bg);
    overflow: hidden;
}

/* ═══════════════════════════════════════
   Avatar — DM profile style
═══════════════════════════════════════ */
.aw { position: relative; flex-shrink: 0; }

.av {
    border-radius: 50%;
    background: linear-gradient(140deg, var(--a) 0%, #a78bfa 55%, #e879f9 100%);
    display: flex; align-items: center; justify-content: center;
    color: #fff; font-weight: 800;
    flex-shrink: 0; letter-spacing: -.5px;
    box-shadow: 0 0 0 2px rgba(255,255,255,.06),
                0 4px 16px var(--aglow);
    transition: box-shadow .2s;
}
.av:hover { box-shadow: 0 0 0 2px rgba(255,255,255,.1), 0 6px 24px var(--aglow); }
.av-xs { width: 26px; height: 26px; font-size: 11px; }
.av-sm { width: 34px; height: 34px; font-size: 13px; }
.av-md { width: 42px; height: 42px; font-size: 17px; }
.av-lg { width: 60px; height: 60px; font-size: 24px; font-weight: 900; }
.av-xl { width: 80px; height: 80px; font-size: 32px; font-weight: 900; }

.online-dot {
    width: 11px; height: 11px; border-radius: 50%;
    background: var(--green);
    border: 2.5px solid var(--s1);
    position: absolute; bottom: 0; right: 0;
    box-shadow: 0 0 8px rgba(34,197,94,.5);
}

/* ═══════════════════════════════════════
   Page & Cards
═══════════════════════════════════════ */
.page {
    width: 100%; height: 100%;
    padding: 36px 40px;
    gap: 28px; overflow-y: auto;
}

.card {
    background: linear-gradient(160deg, var(--s2) 0%, #0d0e18 100%);
    border: 1px solid var(--b1);
    border-radius: 16px;
    box-shadow: 0 1px 0 rgba(255,255,255,.04) inset,
                0 8px 32px rgba(0,0,0,.35);
}

.card-soft {
    background: var(--s3);
    border: 1px solid var(--b1);
    border-radius: 12px;
    transition: background .15s, border-color .15s, transform .15s var(--spring);
}
.card-soft:hover {
    background: var(--s4);
    border-color: var(--b2);
    transform: translateY(-1px);
}

/* Hero character card (setup page) */
.char-hero {
    background: linear-gradient(145deg, #0f1020 0%, #090a12 100%);
    border: 1px solid var(--b2);
    border-radius: 20px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 2px 0 rgba(255,255,255,.05) inset,
                0 20px 60px rgba(0,0,0,.5);
}
.char-hero::before {
    content: '';
    position: absolute; top: -60px; right: -60px;
    width: 200px; height: 200px; border-radius: 50%;
    background: radial-gradient(circle, var(--aglow) 0%, transparent 70%);
    pointer-events: none;
}

.section-label {
    font-size: 10.5px; font-weight: 700; color: var(--t3);
    letter-spacing: .09em; text-transform: uppercase;
}

/* ═══════════════════════════════════════
   Chat Layout
═══════════════════════════════════════ */
.chat-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 22px; flex-shrink: 0;
    background: rgba(8,9,16,.88);
    backdrop-filter: saturate(180%) blur(24px);
    -webkit-backdrop-filter: saturate(180%) blur(24px);
    border-bottom: 1px solid var(--b1);
    position: relative; z-index: 5;
}

.chat-screen {
    width: 100% !important;
    height: 100% !important;
    min-width: 0 !important;
    min-height: 0 !important;
    flex: 1 1 0 !important;
    display: flex !important;
    flex-direction: column !important;
    align-self: stretch !important;
    gap: 0 !important;
    overflow: hidden !important;
}

.chat-messages {
    width: 100% !important;
    flex: 1 1 0 !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    padding: 24px 22px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-height: 0 !important;
}

.chat-area {
    width: 100% !important;
    min-width: 0 !important;
    min-height: 100% !important;
    flex: 1 0 auto !important;
    align-self: stretch !important;
    gap: 4px !important;
}

.chat-footer {
    width: 100%;
    display: flex; align-items: center; gap: 10px;
    padding: 12px 22px; flex-shrink: 0;
    background: rgba(8,9,16,.88);
    backdrop-filter: saturate(180%) blur(24px);
    -webkit-backdrop-filter: saturate(180%) blur(24px);
    border-top: 1px solid var(--b1);
    position: relative; z-index: 5;
}

/* ═══════════════════════════════════════
   Chat Bubbles
═══════════════════════════════════════ */
.bubble-user {
    background: linear-gradient(135deg, #5254d8 0%, var(--a) 50%, #7c79f7 100%);
    color: #fff;
    border-radius: 18px 18px 4px 18px;
    padding: 10px 15px;
    font-size: 14px; line-height: 1.65;
    white-space: pre-wrap; word-break: break-word; max-width: 100%;
    box-shadow: 0 2px 16px rgba(99,102,241,.3),
                0 1px 0 rgba(255,255,255,.12) inset;
}

.bubble-ai {
    background: var(--s3);
    color: var(--t1);
    border: 1px solid var(--b2);
    border-radius: 18px 18px 18px 4px;
    padding: 10px 15px;
    font-size: 14px; line-height: 1.65;
    white-space: pre-wrap; word-break: break-word; max-width: 100%;
    box-shadow: 0 1px 0 rgba(255,255,255,.04) inset,
                0 2px 12px rgba(0,0,0,.25);
}

.msg-ts {
    font-size: 10.5px; color: var(--t3); font-weight: 500;
    letter-spacing: .02em;
}

.msg-name {
    font-size: 11.5px; font-weight: 600; color: var(--t2);
}

/* Message grouping: reduce gap between consecutive messages */
.msg-group { margin-bottom: 14px; }

/* ═══════════════════════════════════════
   Event Milestone
═══════════════════════════════════════ */
.event-pill {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 7px 18px;
    background: linear-gradient(90deg, rgba(99,102,241,.1), rgba(167,139,250,.08));
    border: 1px solid rgba(99,102,241,.22);
    border-radius: 999px;
    color: var(--a3); font-size: 12.5px; font-weight: 600;
    letter-spacing: -.1px;
    box-shadow: 0 0 24px rgba(99,102,241,.1);
}

/* ═══════════════════════════════════════
   Buttons
═══════════════════════════════════════ */
.btn-primary {
    background: linear-gradient(135deg, var(--a) 0%, #7c79f7 100%) !important;
    color: #fff !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    letter-spacing: -.1px;
    box-shadow: 0 4px 16px var(--aglow),
                0 1px 0 rgba(255,255,255,.15) inset !important;
    transition: filter .15s, box-shadow .15s, transform .12s var(--spring) !important;
}
.btn-primary:hover:not([disabled]) {
    filter: brightness(1.1);
    box-shadow: 0 6px 24px var(--aglow),
                0 1px 0 rgba(255,255,255,.15) inset !important;
    transform: translateY(-1px);
}
.btn-primary:active:not([disabled]) { transform: translateY(0); }
.btn-primary[disabled] { opacity: .4 !important; cursor: not-allowed !important; }

.btn-ghost {
    color: var(--t2) !important;
    border-radius: 8px !important;
    transition: color .14s, background .14s !important;
}
.btn-ghost:hover {
    color: var(--t1) !important;
    background: rgba(255,255,255,.05) !important;
}

.btn-send {
    width: 44px !important; height: 44px !important;
    background: linear-gradient(135deg, var(--a), #7c79f7) !important;
    color: #fff !important;
    border-radius: 50% !important; flex-shrink: 0;
    box-shadow: 0 4px 16px var(--aglow),
                0 1px 0 rgba(255,255,255,.15) inset !important;
    transition: filter .15s, transform .12s var(--spring) !important;
}
.btn-send:hover:not([disabled]) {
    filter: brightness(1.12);
    transform: scale(1.06);
}
.btn-send:active:not([disabled]) { transform: scale(0.97); }
.btn-send[disabled] { opacity: .38 !important; }

/* ═══════════════════════════════════════
   Inputs
═══════════════════════════════════════ */
.inp .q-field__control {
    background: var(--s3) !important;
    border-radius: 10px !important;
    min-height: 48px !important;
    transition: box-shadow .15s !important;
}
.inp,
.inp .q-field__inner,
.inp .q-field__control-container {
    width: 100% !important;
    min-width: 0 !important;
}
.inp:not(.q-textarea) .q-field__control,
.inp:not(.q-textarea) .q-field__control-container,
.inp:not(.q-textarea) .q-field__native,
.inp:not(.q-textarea) input {
    height: 48px !important;
    min-height: 48px !important;
}
.inp .q-field__native,
.inp input,
.inp textarea {
    box-sizing: border-box !important;
    margin: 0 !important;
    font-family: inherit !important;
    font-size: 14px !important;
    font-weight: 400 !important;
    line-height: 1.5 !important;
    letter-spacing: -0.01em !important;
    color: var(--t1) !important;
}
.inp:not(.q-textarea) .q-field__native,
.inp:not(.q-textarea) input {
    padding: 14px 8px 2px !important;
}
.inp.q-textarea .q-field__control {
    min-height: 96px !important;
    height: auto !important;
    align-items: stretch !important;
}
.inp.q-textarea .q-field__control-container {
    min-height: 94px !important;
}
.inp.q-textarea .q-field__native,
.inp textarea {
    display: block !important;
    width: 100% !important;
    min-height: 94px !important;
    padding: 22px 8px 10px !important;
    resize: vertical;
    overflow-y: auto !important;
}
.inp .q-field__label {
    max-width: calc(100% - 4px) !important;
    font-family: inherit !important;
    line-height: 1.2 !important;
    letter-spacing: -0.01em !important;
}
.inp .q-field__native::placeholder,
.inp input::placeholder,
.inp textarea::placeholder {
    color: var(--t2) !important;
    opacity: .8 !important;
}
.inp .q-field__control::before { border-color: var(--b2) !important; }
.inp .q-field__control:hover::before { border-color: var(--b3) !important; }
.inp .q-field__control.q-field__control--focused::before {
    border-color: var(--a) !important;
    border-width: 1.5px !important;
}
.inp .q-field__control.q-field__control--focused {
    box-shadow: 0 0 0 3px rgba(99,102,241,.12) !important;
}
.inp-chat .q-field__control {
    background: var(--s3) !important;
    border-radius: 999px !important;
    min-height: 46px !important;
    height: 46px !important;
    padding: 0 18px !important;
}
.inp-chat,
.inp-chat .q-field__inner,
.inp-chat .q-field__control-container {
    min-width: 0 !important;
    width: 100% !important;
}
.inp-chat .q-field__native,
.inp-chat input {
    height: 46px !important;
    min-height: 46px !important;
    padding: 0 !important;
    margin: 0 !important;
    line-height: 1.45 !important;
    font-family: inherit !important;
    font-size: 14px !important;
    font-weight: 400 !important;
    letter-spacing: -0.01em !important;
    color: var(--t1) !important;
}
.inp-chat input::placeholder {
    color: var(--t2) !important;
    opacity: .82 !important;
}
.inp-chat .q-field__control::before {
    border-color: var(--b2) !important;
    border-radius: 999px !important;
}
.inp-chat .q-field__control:hover::before { border-color: var(--b3) !important; }
.inp-chat .q-field__control.q-field__control--focused::before {
    border-color: var(--a) !important;
}
.inp-chat .q-field__control.q-field__control--focused {
    box-shadow: 0 0 0 3px rgba(99,102,241,.12) !important;
}

/* ═══════════════════════════════════════
   Progress Bar
═══════════════════════════════════════ */
.q-linear-progress {
    border-radius: 99px;
    overflow: hidden;
}
.q-linear-progress__track {
    background: rgba(255,255,255,.07) !important;
}
.q-linear-progress__model {
    background: linear-gradient(90deg, var(--a), var(--a2)) !important;
    border-radius: 99px;
    box-shadow: 0 0 10px var(--aglow);
}
/* ═══════════════════════════════════════
   Dialog
═══════════════════════════════════════ */
.q-dialog__backdrop { background: rgba(0,0,0,.75) !important; }
.dialog-card {
    background: linear-gradient(160deg, var(--s2), #0a0b12) !important;
    border: 1px solid var(--b2) !important;
    border-radius: 18px !important;
    min-width: 360px;
    padding: 28px !important;
    gap: 16px !important;
    box-shadow: 0 24px 80px rgba(0,0,0,.6),
                0 1px 0 rgba(255,255,255,.06) inset !important;
}

/* ═══════════════════════════════════════
   Stat Cards
═══════════════════════════════════════ */
.stat-card {
    background: linear-gradient(160deg, var(--s2), #0a0b12);
    border: 1px solid var(--b1);
    border-radius: 16px;
    padding: 24px;
    display: flex; flex-direction: column; gap: 10px;
    box-shadow: 0 8px 32px rgba(0,0,0,.3),
                0 1px 0 rgba(255,255,255,.04) inset;
}
.stat-num {
    font-size: 48px; font-weight: 900; line-height: 1;
    letter-spacing: -3px; color: var(--t1);
}

/* ═══════════════════════════════════════
   Empty State
═══════════════════════════════════════ */
.empty-state {
    width: 100%;
    min-width: 0;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    flex: 1; gap: 12px;
    pointer-events: none; user-select: none;
}

/* ═══════════════════════════════════════
   Animations
═══════════════════════════════════════ */
@keyframes fade-up {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}
.msg-in { animation: fade-up .2s var(--ease) both; }

@keyframes pop-in {
    from { opacity: 0; transform: scale(.92); }
    to   { opacity: 1; transform: scale(1); }
}
.pop-in { animation: pop-in .18s var(--spring) both; }

@keyframes pulse-glow {
    0%,100% { box-shadow: 0 0 0 0 var(--aglow); }
    50%      { box-shadow: 0 0 0 6px transparent; }
}

/* Typing indicator */
.typing-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--t2);
    display: inline-block;
    animation: bounce 1.3s infinite ease-in-out both;
}
.typing-dot:nth-child(1) { animation-delay: 0s; }
.typing-dot:nth-child(2) { animation-delay: .16s; }
.typing-dot:nth-child(3) { animation-delay: .32s; }

@keyframes bounce {
    0%,60%,100% { transform: translateY(0);    opacity: .3; }
    30%         { transform: translateY(-7px); opacity: 1; }
}

/* Tag chip */
.tag {
    display: inline-flex; align-items: center;
    padding: 3px 10px; border-radius: 999px;
    background: var(--adim);
    border: 1px solid rgba(99,102,241,.18);
    color: var(--a3); font-size: 11.5px; font-weight: 600;
    letter-spacing: -.1px;
}

/* Separator with gradient */
.sep {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--b2) 30%, var(--b2) 70%, transparent);
    border: none; margin: 4px 0;
}

/* ═══════════════════════════════════════
   Overflow 방지 — 전역 텍스트 줄바꿈
═══════════════════════════════════════ */

/* ── 텍스트 줄바꿈 (display 건드리지 않음 — flex 레이아웃 보호) */
.q-label,
.bubble-user,
.bubble-ai,
.msg-name,
.msg-ts {
    word-break: break-word !important;
    overflow-wrap: anywhere !important;
    white-space: normal !important;
    max-width: 100% !important;
    min-width: 0 !important;
}

/* flex 자식 min-width 리셋 */
.column > *, .row > * { min-width: 0; }

/* 페이지 직계 자식 전부 full width */
.page > * { width: 100% !important; }

/* 카드 오버플로 */
.card, .card-soft, .char-hero, .stat-card, .dialog-card { overflow: hidden; }

/* 버블 */
.bubble-user, .bubble-ai {
    overflow-wrap: break-word;
    word-break: break-word;
    overflow: hidden;
}

/* 수평 스크롤 방지 */
.page { overflow-x: hidden; }

/* ═══════════════════════════════════════
   Scrollbar
═══════════════════════════════════════ */
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,.08);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,.14); }

/* ═══════════════════════════════════════
   Responsive
═══════════════════════════════════════ */
@media (max-width: 768px) {
    .app-shell { flex-direction: column !important; }
    .sidebar {
        width: 100vw !important;
        min-width: 0 !important;
        height: auto !important;
        max-height: 120px;
        border-right: none;
        border-bottom: 1px solid var(--b1);
    }
    .main-panel {
        width: 100vw !important;
        max-width: 100vw !important;
        height: calc(100dvh - 120px) !important;
        min-height: 0 !important;
    }
    .page { padding: 20px; }
    .chat-header, .chat-footer { padding: 12px 16px; }
    .chat-messages { padding: 16px; }
}
</style>
"""


# ============================================================
# 메인 페이지 — @ui.page 로 사용자마다 독립 실행
# ============================================================

@ui.page("/")
async def index():
    """접속마다 독립된 상태를 가지는 메인 페이지"""

    # CSS를 페이지 함수 안에서 주입 (shared=True 캐싱 우회)
    ui.add_head_html(_HEAD_HTML)

    # ── API 키 체크 ────────────────────────────────────────
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        ui.dark_mode()
        with ui.column().classes("w-full h-screen items-center justify-center gap-4"):
            ui.html('<span class="material-icons-round" style="font-size:52px;color:#f87171">warning</span>')
            ui.label("API 키가 설정되지 않았습니다.").style(
                "font-size:22px;font-weight:800;color:var(--txt-1)"
            )
            ui.label(".env 파일에 GEMINI_API_KEY를 설정해주세요.").style(
                "font-size:14px;color:var(--txt-2)"
            )
            ui.html(
                '<code style="background:var(--s3);padding:8px 16px;border-radius:8px;'
                'font-size:13px;color:#a5a8ff">GEMINI_API_KEY=AIzaSy...</code>'
            )
        return

    # ── 사용자 데이터 (파일에서 복원, 없으면 기본값) ────────
    _saved = load_session()
    character:          dict = _saved["character"]          if _saved else DEFAULT_CHARACTER.copy()
    chat_history:       list = _saved["chat_history"]       if _saved else []
    chat_context:       list = _saved["chat_context"]       if _saved else []
    reached_milestones: set  = _saved["reached_milestones"] if _saved else set()

    # ── 연결별 UI 참조 (dict로 관리 → nonlocal 불필요) ────
    r: dict = {
        "content_area":      None,
        "chat_area":         None,
        "message_input":     None,
        "send_button":       None,
        "chat_status_label": None,
        "empty_state_el":    None,
        "menu_items":        {},
    }

    # ── 저장 (파일에 영구 저장) ───────────────────────────
    def save():
        save_session(character, chat_history, chat_context, reached_milestones)

    # ── 유틸 ──────────────────────────────────────────────
    def initial() -> str:
        return (character.get("name", "AI")[0] or "A").upper()

    def av(size: str = "av-md") -> str:
        return f'<div class="av {size}">{initial()}</div>'

    def av_online() -> str:
        return (
            '<div class="aw">'
            f'<div class="av av-md">{initial()}</div>'
            '<div class="online-dot"></div>'
            '</div>'
        )

    def now() -> str:
        return datetime.now().strftime("%H:%M:%S")

    def update_emotion(change: int, text: str):
        if change > 0:    character["emotion"] = "기분 좋음"
        elif change < 0:  character["emotion"] = "서운함"
        elif "?" in text: character["emotion"] = "궁금함"
        else:             character["emotion"] = "대화 중"

    def check_milestone(old: int, new: int) -> dict | None:
        for threshold, data in sorted(LOVE_MILESTONES.items()):
            if old < threshold <= new and threshold not in reached_milestones:
                reached_milestones.add(threshold)
                return data
        return None

    async def scroll_bottom():
        await ui.run_javascript("""
            setTimeout(() => {
                const el = document.querySelector('.chat-messages');
                if (el) el.scrollTop = el.scrollHeight;
            }, 80);
        """)

    # ── 대화 내보내기 ──────────────────────────────────────
    def export_chat():
        if not chat_history:
            ui.notify("내보낼 대화 기록이 없습니다.", color="warning")
            return
        lines = [
            f"=== {character['name']}와의 대화 ===",
            f"저장일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"호감도: {character['love']}%  |  감정: {character['emotion']}",
            "",
        ]
        for item in chat_history:
            if item["role"] == "event":
                lines.append(f"\n── {item.get('emoji','')} {item['content']} ──\n")
            else:
                who = "나" if item["role"] == "user" else character["name"]
                lines.append(f"[{item['time']}] {who}: {item['content']}")
        filename = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        ui.download("\n".join(lines).encode("utf-8"), filename)
        ui.notify("대화 내보내기 완료", color="positive")

    # ── 버블 렌더링 ────────────────────────────────────────
    def render_ai_bubble(text: str, ts: str | None = None):
        with r["chat_area"]:
            with ui.row().classes("w-full items-end gap-3 msg-in"):
                ui.html(av("av-sm"))
                with ui.column().classes("gap-1").style("max-width:66%;min-width:0;overflow:hidden"):
                    with ui.row().classes("items-center gap-2"):
                        ui.label(character["name"]).classes("msg-meta font-semibold").style("color:var(--txt-2)")
                        ui.label(ts or now()).classes("msg-meta")
                    ui.label(text).classes("bubble-ai")

    def render_user_bubble(text: str, ts: str | None = None):
        with r["chat_area"]:
            with ui.row().classes("w-full justify-end msg-in"):
                with ui.column().classes("gap-1 items-end").style("max-width:66%;min-width:0;overflow:hidden"):
                    ui.label(ts or now()).classes("msg-meta")
                    ui.label(text).classes("bubble-user")

    def render_event(emoji: str, text: str):
        with r["chat_area"]:
            ui.html(
                f'<div class="event-pill"><span>{emoji}</span><span>{text}</span></div>'
            ).classes("w-full")

    def add_user_message(text: str):
        ts = now()
        chat_history.append({"role": "user", "content": text, "time": ts})
        render_user_bubble(text, ts)

    def rerender_history():
        for item in chat_history:
            if   item["role"] == "user":  render_user_bubble(item["content"], item["time"])
            elif item["role"] == "ai":    render_ai_bubble(item["content"], item["time"])
            elif item["role"] == "event": render_event(item.get("emoji", "⭐"), item["content"])

    # ── 메시지 전송 ────────────────────────────────────────
    async def send_message(event=None):
        try:
            text = r["message_input"].value.strip()
            if not text:
                ui.notify("메시지를 입력하세요.", color="warning")
                return

            if r["empty_state_el"] is not None:
                r["empty_state_el"].set_visibility(False)
                r["empty_state_el"] = None

            r["message_input"].disable()
            r["send_button"].disable()

            add_user_message(text)
            r["message_input"].value = ""
            await scroll_bottom()

            old_love = character["love"]

            ts = now()
            with r["chat_area"]:
                with ui.row().classes("w-full items-end gap-3 msg-in"):
                    ui.html(av("av-sm"))
                    with ui.column().classes("gap-1").style("max-width:66%;min-width:0;overflow:hidden"):
                        with ui.row().classes("items-center gap-2"):
                            ui.label(character["name"]).classes("msg-meta font-semibold").style("color:var(--txt-2)")
                            ui.label(ts).classes("msg-meta")
                        typing = ui.html(
                            '<div class="bubble-ai" style="display:flex;align-items:center;gap:6px;padding:12px 16px">'
                            '<span class="typing-dot"></span>'
                            '<span class="typing-dot"></span>'
                            '<span class="typing-dot"></span>'
                            '</div>'
                        )
                        reply = ui.label("").classes("bubble-ai")
                        reply.visible = False

            await scroll_bottom()

            try:
                ai_answer, change = await asyncio.to_thread(
                    get_ai_response, text, dict(character), list(chat_context)
                )

                # AI가 문장의 의미와 대화 맥락으로 평가한 변화량을 반영한다.
                new_love = max(0, min(100, old_love + change))
                character["love"] = new_love
                update_emotion(change, text)

                if change > 0:
                    ui.notify(f"호감도 +{change}", color="positive", timeout=2000, position="top-right")
                elif change < 0:
                    ui.notify(f"호감도 {change}", color="warning", timeout=2000, position="top-right")

                typing.visible = False
                reply.set_text(ai_answer)
                reply.visible = True

                if r["chat_status_label"]:
                    r["chat_status_label"].set_text(
                        f"{character['emotion']}  ·  호감도 {character['love']}%"
                    )

                chat_context.append({"role": "user",      "content": text})
                chat_context.append({"role": "assistant", "content": ai_answer})
                chat_history.append({"role": "ai",        "content": ai_answer, "time": ts})

                milestone = check_milestone(old_love, new_love)
                if milestone:
                    chat_history.append({
                        "role": "event", "emoji": milestone["emoji"],
                        "content": milestone["message"], "time": ts,
                    })
                    render_event(milestone["emoji"], milestone["message"])
                    ui.notify(f"{milestone['emoji']} {milestone['message']}", color="positive", timeout=3500)
                    await scroll_bottom()

                save()

            except Exception as err:
                traceback.print_exc()
                msg = f"AI 응답을 불러오지 못했어. 오류: {err}"
                typing.visible = False
                reply.set_text(msg)
                reply.visible = True
                chat_history.append({"role": "ai", "content": msg, "time": ts})
                ui.notify(str(err), color="negative")

            await scroll_bottom()

        except Exception as err:
            traceback.print_exc()
            ui.notify(f"오류: {err}", color="negative")

        finally:
            if r["message_input"]: r["message_input"].enable()
            if r["send_button"]:   r["send_button"].enable()

    # ── 대화 초기화 ────────────────────────────────────────
    async def reset_chat():
        chat_history.clear()
        chat_context.clear()
        reached_milestones.clear()
        character["emotion"] = "편안함"
        character["love"]    = 50
        save()
        set_active_menu("chat")
        await scroll_bottom()

    # ── 설정 적용 (공용) ───────────────────────────────────
    def apply_settings(name_v: str, pers_v: str, tone_v: str, int_v: str, on_done=None):
        """입력값 검증 후 캐릭터 설정 반영"""
        character["name"]        = (name_v.strip() or "연우")[:20]
        character["personality"] = (pers_v.strip() or "조용하지만 은근 장난기 있는 성격")[:200]
        character["tone"]        = (tone_v.strip() or "친구처럼 편하게 말하는 말투")[:200]
        character["interest"]    = (int_v.strip()  or "음악, 유튜브")[:100]
        save()

        def _keep(dlg):
            dlg.close()
            ui.notify("설정이 적용되었습니다.", color="positive")
            if on_done: on_done()

        def _reset(dlg):
            chat_history.clear()
            chat_context.clear()
            reached_milestones.clear()
            save()
            dlg.close()
            ui.notify("설정 적용 및 대화 초기화 완료.", color="positive")
            if on_done: on_done()

        if chat_history:
            with ui.dialog() as dlg:
                with ui.card().classes("dialog-card"):
                    ui.label("대화 기록 초기화").style(
                        "font-size:16px;font-weight:800;color:var(--txt-1)"
                    )
                    ui.label(
                        "캐릭터 설정이 변경되었어요.\n이전 대화를 초기화할까요?"
                    ).style("font-size:13px;color:var(--txt-2);white-space:pre-line;line-height:1.6")
                    with ui.row().classes("gap-2 w-full justify-end").style("margin-top:8px"):
                        ui.button("유지",    on_click=lambda: _keep(dlg)).props("flat").classes("btn-ghost")
                        ui.button("초기화", on_click=lambda: _reset(dlg)).props("unelevated").classes("btn-primary px-5")
            dlg.open()
        else:
            ui.notify("설정이 적용되었습니다.", color="positive")
            if on_done: on_done()

    # ── 메뉴 전환 ──────────────────────────────────────────
    def set_active_menu(page: str):
        for key, item in r["menu_items"].items():
            if key == page: item.classes(add="active")
            else:           item.classes(remove="active")
        render_content(page)

    def render_content(page: str):
        r["content_area"].clear()
        {
            "setup":    render_setup,
            "chat":     render_chat,
            "settings": render_settings,
            "emotion":  render_emotion,
            "info":     render_info,
        }.get(page, lambda: None)()

    # ── 시작 설정 화면 ─────────────────────────────────────
    def render_setup():
        with r["content_area"]:
            with ui.column().classes("page"):

                # 헤더
                ui.html(
                    '<div style="margin-bottom:4px">'
                    '<div style="font-size:28px;font-weight:900;color:var(--t1);letter-spacing:-.6px;line-height:1.1">시작하기</div>'
                    '<div style="font-size:13.5px;color:var(--t2);margin-top:6px">캐릭터를 설정하고 대화를 시작해보세요.</div>'
                    '</div>'
                )

                # 2열 그리드 레이아웃
                with ui.element("div").style(
                    "display:grid;grid-template-columns:300px 1fr;gap:20px;width:100%;align-items:start"
                ):
                    # ── 왼쪽: 캐릭터 히어로 카드
                    with ui.element("div").classes("char-hero").style("padding:28px;display:flex;flex-direction:column;gap:20px"):
                        with ui.element("div").style("display:flex;flex-direction:column;align-items:center;gap:16px"):
                            ui.html(av("av-xl"))
                            ui.html(
                                f'<div style="text-align:center">'
                                f'<div style="font-size:22px;font-weight:900;color:var(--t1);letter-spacing:-.5px">{character["name"]}</div>'
                                f'<div style="font-size:12px;color:var(--t2);margin-top:3px">{character["emotion"]}  ·  호감도 {character["love"]}%</div>'
                                f'</div>'
                            )

                        ui.html('<hr class="sep">')

                        ui.html(
                            f'<div style="font-size:13px;color:var(--t2);line-height:1.65;text-align:center;word-break:break-word">'
                            f'{character["personality"]}</div>'
                        )

                        ui.html(
                            '<div style="display:flex;flex-wrap:wrap;gap:6px;justify-content:center">'
                            + ''.join(f'<span class="tag">{t.strip()}</span>' for t in character["interest"].split(","))
                            + '</div>'
                        )

                        ui.linear_progress(
                            value=character["love"] / 100,
                            show_value=False,
                        ).classes("w-full").style("height:5px")

                        ui.button(
                            "채팅 시작", icon="chat",
                            on_click=lambda: set_active_menu("chat"),
                        ).props("unelevated").classes("btn-primary w-full").style("height:44px;font-size:14px")

                    # ── 오른쪽: 설정 + 프리셋
                    with ui.element("div").style("display:flex;flex-direction:column;gap:16px;min-width:0"):

                        # 캐릭터 직접 설정
                        with ui.element("div").classes("card").style("padding:24px;display:flex;flex-direction:column;gap:16px"):
                            ui.html('<div style="font-size:10.5px;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.09em">캐릭터 설정</div>')

                            s_name = ui.input(
                                "이름 (최대 20자)", value=character["name"],
                            ).props("outlined dark dense maxlength=20").classes("w-full inp")

                            s_pers = ui.textarea(
                                "성격", value=character["personality"],
                            ).props("outlined dark dense maxlength=200").classes("w-full inp")

                            s_tone = ui.textarea(
                                "말투", value=character["tone"],
                            ).props("outlined dark dense maxlength=200").classes("w-full inp")

                            s_int = ui.input(
                                "관심사 (쉼표로 구분)", value=character["interest"],
                            ).props("outlined dark dense maxlength=100").classes("w-full inp")

                            def _apply_from_setup():
                                apply_settings(
                                    s_name.value, s_pers.value, s_tone.value, s_int.value,
                                    on_done=lambda: render_content("setup"),
                                )

                            ui.button(
                                "설정 적용", icon="check", on_click=_apply_from_setup,
                            ).props("unelevated").classes("btn-primary w-full").style("height:42px")

                        # 빠른 프리셋
                        with ui.element("div").classes("card").style("padding:20px;display:flex;flex-direction:column;gap:12px"):
                            ui.html('<div style="font-size:10.5px;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.09em">빠른 프리셋</div>')

                            for preset in CHARACTER_PRESETS:
                                def _apply_preset(p=preset):
                                    character.update({
                                        "name": p["name"], "personality": p["personality"],
                                        "tone": p["tone"], "interest": p["interest"],
                                        "emotion": "편안함", "love": 50,
                                    })
                                    chat_history.clear()
                                    chat_context.clear()
                                    reached_milestones.clear()
                                    save()
                                    ui.notify(f"'{p['label']}' 프리셋 적용됨", color="positive")
                                    render_content("setup")

                                with ui.element("div").classes("card-soft").style(
                                    "padding:14px 16px;display:flex;align-items:center;gap:12px;cursor:pointer"
                                ):
                                    ui.html(
                                        f'<div class="av av-sm" style="flex-shrink:0">{preset["name"][0]}</div>'
                                    )
                                    with ui.element("div").style("flex:1;min-width:0"):
                                        ui.html(
                                            f'<div style="font-size:13px;font-weight:700;color:var(--t1)">{preset["label"]}</div>'
                                            f'<div style="font-size:11.5px;color:var(--t2);margin-top:2px;word-break:break-word">{preset["personality"]}</div>'
                                        )
                                    ui.button(
                                        "적용", on_click=_apply_preset,
                                    ).props("flat dense").classes("btn-ghost").style(
                                        "font-size:12px;font-weight:700"
                                    )

    # ── 채팅 화면 ──────────────────────────────────────────
    def render_chat():
        with r["content_area"]:
            with ui.column().classes("chat-screen"):

                with ui.element("div").classes("chat-header"):
                    with ui.row().classes("items-center gap-3"):
                        ui.html(av_online())
                        with ui.column().classes("gap-0"):
                            ui.label(character["name"]).style(
                                "font-size:14px;font-weight:700;color:var(--t1);letter-spacing:-.2px"
                            )
                            r["chat_status_label"] = ui.label(
                                f"{character['emotion']}  ·  호감도 {character['love']}%"
                            ).style("font-size:11px;color:var(--t2)")

                    with ui.row().classes("items-center gap-1"):
                        ui.button(icon="file_download", on_click=export_chat).props(
                            "flat round dense"
                        ).classes("btn-ghost").tooltip("대화 내보내기")
                        ui.button(icon="restart_alt", on_click=reset_chat).props(
                            "flat round dense"
                        ).classes("btn-ghost").tooltip("대화 초기화")

                with ui.element("div").classes("chat-messages flex-1").style("overflow-y:auto"):
                    r["chat_area"] = ui.column().classes("chat-area")

                if chat_history:
                    rerender_history()
                else:
                    with r["chat_area"]:
                        empty = ui.column().classes("empty-state").style("min-height:360px;gap:14px")
                        r["empty_state_el"] = empty
                        with empty:
                            ui.html(
                                f'<div class="av av-xl" style="opacity:.15;filter:blur(1px)">'
                                f'{initial()}</div>'
                            )
                            with ui.column().classes("items-center gap-1"):
                                ui.label(f"{character['name']}에게 메시지를 보내보세요").style(
                                    "font-size:15px;font-weight:700;color:var(--t3);letter-spacing:-.2px"
                                )
                                ui.label("Enter 또는 ↑ 버튼으로 전송").style(
                                    "font-size:12px;color:var(--t3)"
                                )

                with ui.element("div").classes("chat-footer"):
                    r["message_input"] = ui.input(
                        placeholder=f"{character['name']}에게 메시지...",
                    ).props("outlined dark dense").classes("flex-1 inp-chat")
                    r["message_input"].on("keydown.enter", send_message)

                    r["send_button"] = ui.button(
                        icon="arrow_upward", on_click=send_message,
                    ).props("unelevated round").classes("btn-send")

    # ── 캐릭터 설정 화면 ───────────────────────────────────
    def render_settings():
        with r["content_area"]:
            with ui.column().classes("page"):

                ui.html(
                    '<div style="margin-bottom:4px">'
                    '<div style="font-size:28px;font-weight:900;color:var(--t1);letter-spacing:-.6px;line-height:1.1">캐릭터 설정</div>'
                    '<div style="font-size:13.5px;color:var(--t2);margin-top:6px">대화 상대의 이름, 성격, 말투, 관심사를 설정합니다.</div>'
                    '</div>'
                )

                with ui.element("div").style(
                    "display:grid;grid-template-columns:1fr 340px;gap:20px;width:100%;align-items:start"
                ):
                    # 왼쪽: 입력 폼
                    with ui.element("div").classes("card").style("padding:24px;display:flex;flex-direction:column;gap:16px"):
                        ui.html('<div style="font-size:10.5px;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.09em">기본 정보</div>')

                        n = ui.input("이름 (최대 20자)", value=character["name"]).props(
                            "outlined dark dense maxlength=20"
                        ).classes("w-full inp")
                        p = ui.textarea("성격 설명", value=character["personality"]).props(
                            "outlined dark dense maxlength=200"
                        ).classes("w-full inp")
                        t = ui.textarea("말투 설명", value=character["tone"]).props(
                            "outlined dark dense maxlength=200"
                        ).classes("w-full inp")
                        i = ui.input("관심사 (쉼표로 구분)", value=character["interest"]).props(
                            "outlined dark dense maxlength=100"
                        ).classes("w-full inp")

                        ui.button(
                            "설정 적용", icon="check",
                            on_click=lambda: apply_settings(
                                n.value, p.value, t.value, i.value,
                                on_done=lambda: render_content("settings"),
                            ),
                        ).props("unelevated").classes("btn-primary w-full").style("height:44px")

                    # 오른쪽: 미리보기
                    with ui.element("div").classes("card").style("padding:24px;display:flex;flex-direction:column;gap:16px"):
                        ui.html('<div style="font-size:10.5px;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.09em">미리보기</div>')

                        with ui.element("div").style("display:flex;flex-direction:column;align-items:center;gap:12px;padding:8px 0"):
                            ui.html(av("av-lg"))
                            ui.html(
                                f'<div style="text-align:center;width:100%">'
                                f'<div style="font-size:18px;font-weight:900;color:var(--t1);letter-spacing:-.4px;word-break:break-word">{character["name"]}</div>'
                                f'<div style="font-size:12px;color:var(--t2);line-height:1.6;margin-top:4px;word-break:break-word">{character["personality"]}</div>'
                                f'</div>'
                            )

                        ui.html('<hr class="sep">')
                        for lbl, val in [
                            ("말투",  character["tone"]),
                            ("관심사", character["interest"]),
                        ]:
                            ui.html(
                                f'<div style="margin-bottom:10px">'
                                f'<div style="font-size:10.5px;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.09em;margin-bottom:4px">{lbl}</div>'
                                f'<div style="font-size:13px;color:var(--t2);line-height:1.55;word-break:break-word">{val}</div>'
                                f'</div>'
                            )

    # ── 감정 상태 화면 ─────────────────────────────────────
    def render_emotion():
        love = character["love"]
        love_color = "#a78bfa" if love >= 70 else ("#6366f1" if love >= 30 else "#454666")
        love_label = "💜 최고 친밀도" if love >= 100 else ("😊 친밀함" if love >= 70 else ("🙂 보통" if love >= 30 else "😶 거리감"))

        milestone_html = ""
        if reached_milestones:
            for threshold in sorted(reached_milestones):
                d = LOVE_MILESTONES.get(threshold, {})
                milestone_html += (
                    f'<div style="display:flex;align-items:center;gap:12px;margin-top:12px">'
                    f'<div style="width:36px;height:36px;border-radius:10px;background:var(--adim);'
                    f'border:1px solid rgba(99,102,241,.2);display:flex;align-items:center;justify-content:center;'
                    f'font-size:18px;flex-shrink:0">{d.get("emoji","⭐")}</div>'
                    f'<div><div style="font-size:13px;font-weight:700;color:var(--t1)">{d.get("message","")}</div>'
                    f'<div style="font-size:11px;color:var(--t2)">호감도 {threshold}% 달성</div></div>'
                    f'</div>'
                )
        else:
            milestone_html = (
                '<div style="font-size:13px;color:var(--t3);margin-top:10px">아직 달성한 이벤트가 없어요</div>'
                '<div style="font-size:12px;color:var(--t3);margin-top:4px">대화를 나눠 호감도를 높여보세요</div>'
            )

        with r["content_area"]:
            with ui.column().classes("page"):

                ui.html(
                    '<div style="margin-bottom:4px">'
                    '<div style="font-size:28px;font-weight:900;color:var(--t1);letter-spacing:-.6px;line-height:1.1">감정 상태</div>'
                    '<div style="font-size:13.5px;color:var(--t2);margin-top:6px">대화에 따라 감정과 호감도가 실시간으로 변화합니다.</div>'
                    '</div>'
                )

                # 3열 스탯 카드
                with ui.element("div").style(
                    "display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;width:100%"
                ):
                    with ui.element("div").classes("stat-card"):
                        ui.html(f'<div style="font-size:10.5px;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.09em">호감도</div>')
                        ui.html(f'<div class="stat-num" style="color:{love_color}">{love}%</div>')
                        ui.linear_progress(
                            value=love / 100,
                            show_value=False,
                        ).classes("w-full").style("height:5px;margin-top:4px")
                        ui.html(f'<div style="font-size:12.5px;color:var(--t2);margin-top:4px">{love_label}</div>')

                    with ui.element("div").classes("stat-card"):
                        ui.html('<div style="font-size:10.5px;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.09em">현재 감정</div>')
                        ui.html(f'<div class="stat-num" style="font-size:32px;letter-spacing:-.5px">{character["emotion"]}</div>')
                        ui.html('<div style="font-size:12px;color:var(--t2)">마지막 대화 기반</div>')

                    with ui.element("div").classes("stat-card"):
                        ui.html('<div style="font-size:10.5px;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.09em">달성한 이벤트</div>')
                        ui.html(milestone_html)

                # 호감도 가이드
                with ui.element("div").classes("card").style("padding:20px;width:100%"):
                    ui.html('<div style="font-size:10.5px;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.09em;margin-bottom:12px">호감도 가이드</div>')
                    with ui.element("div").style("display:grid;grid-template-columns:repeat(4,1fr);gap:12px"):
                        for rng, emoji, desc, clr in [
                            ("0–29%",  "😶", "거리감. 친절하게 말을 걸어보세요.", "#454666"),
                            ("30–69%", "🙂", "조금 친해졌어요.", "#6366f1"),
                            ("70–99%", "😊", "꽤 가까워졌어요.", "#a78bfa"),
                            ("100%",   "💜", "최고 호감도!", "#e879f9"),
                        ]:
                            ui.html(
                                f'<div class="card-soft" style="padding:16px;display:flex;flex-direction:column;gap:6px">'
                                f'<span style="font-size:22px">{emoji}</span>'
                                f'<div style="font-size:13px;font-weight:800;color:{clr};letter-spacing:-.2px">{rng}</div>'
                                f'<div style="font-size:11.5px;color:var(--t2);line-height:1.5">{desc}</div>'
                                f'</div>'
                            )

    # ── 정보 화면 ──────────────────────────────────────────
    def render_info():
        with r["content_area"]:
            with ui.column().classes("page"):

                ui.html(
                    '<div style="margin-bottom:4px">'
                    '<div style="font-size:28px;font-weight:900;color:var(--t1);letter-spacing:-.6px;line-height:1.1">정보</div>'
                    '<div style="font-size:13.5px;color:var(--t2);margin-top:6px">Python NiceGUI 기반 Gemini API 대화형 웹 인터페이스입니다.</div>'
                    '</div>'
                )

                with ui.element("div").style(
                    "display:grid;grid-template-columns:1fr 1fr;gap:16px;width:100%"
                ):
                    with ui.element("div").classes("card").style("padding:20px"):
                        ui.html('<div style="font-size:10.5px;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.09em;margin-bottom:14px">기술 스택</div>')
                        for name, desc in [
                            ("Python 3.12",   "애플리케이션 런타임"),
                            ("NiceGUI",        "웹 UI 프레임워크"),
                            ("Gemini API",     "LLM 생성 엔진"),
                            ("gemini-2.5-flash", "대화 AI 모델"),
                            ("Docker",         "컨테이너 배포"),
                        ]:
                            ui.html(
                                f'<div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:10px">'
                                f'<span class="material-icons-round" style="font-size:14px;color:var(--a);margin-top:2px;flex-shrink:0">circle</span>'
                                f'<div><div style="font-size:13px;font-weight:600;color:var(--t1)">{name}</div>'
                                f'<div style="font-size:11.5px;color:var(--t2)">{desc}</div></div>'
                                f'</div>'
                            )

                    with ui.element("div").classes("card").style("padding:20px"):
                        ui.html('<div style="font-size:10.5px;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.09em;margin-bottom:14px">동작 구조</div>')
                        for i, (title, desc) in enumerate([
                            ("사용자 입력",    "메시지를 입력하면 처리 시작"),
                            ("호감도 계산",    "키워드 기반 점수 변화"),
                            ("프롬프트 구성", "캐릭터 설정 + 대화 맥락 포함"),
                            ("Gemini API 호출", "Gemini 모델이 답변 생성"),
                            ("응답 출력",     "채팅창에 표시 및 세션 저장"),
                        ], 1):
                            ui.html(
                                f'<div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:10px">'
                                f'<div style="width:20px;height:20px;border-radius:50%;background:var(--adim);'
                                f'border:1px solid rgba(99,102,241,.3);display:flex;align-items:center;justify-content:center;'
                                f'font-size:10px;font-weight:800;color:#a5a8ff;flex-shrink:0">{i}</div>'
                                f'<div><div style="font-size:13px;font-weight:600;color:var(--t1)">{title}</div>'
                                f'<div style="font-size:11.5px;color:var(--t2)">{desc}</div></div>'
                                f'</div>'
                            )

    # ── UI 조립 ────────────────────────────────────────────
    ui.dark_mode()

    with ui.row().classes("app-shell"):

        # 사이드바
        with ui.column().classes("sidebar"):
            with ui.element("div").classes("sidebar-top"):
                with ui.row().classes("items-center gap-3"):
                    ui.html('<div class="brand-logo">C</div>')
                    with ui.column().classes("gap-0"):
                        ui.label("커스터마이징").classes("brand-name")
                        ui.label("연애 시뮬레이터").classes("brand-sub")

            with ui.element("div").classes("sidebar-nav"):
                ui.label("메뉴").classes("nav-section-label").style(
                    "margin-bottom:6px;display:block"
                )
                for key, icon, label in MENU_STRUCTURE:
                    item = ui.element("div").classes(
                        f"nav-item {'active' if key == 'setup' else ''}"
                    )
                    with item:
                        ui.html(f'<span class="mat-icon">{icon}</span>')
                        ui.label(label).style("font-size:13.5px")
                    item.on("click", lambda k=key: set_active_menu(k))
                    r["menu_items"][key] = item

            with ui.element("div").classes("sidebar-footer"):
                footer_card = ui.element("div").classes("char-card")
                with footer_card:
                    ui.html(f'<div class="av av-sm">{initial()}</div>')
                    with ui.column().classes("gap-0"):
                        ui.label(character["name"]).classes("char-name")
                        ui.label(f"호감도 {character['love']}%").classes("char-sub")
                footer_card.on("click", lambda: set_active_menu("emotion"))

        # 메인 패널
        with ui.column().classes("main-panel"):
            r["content_area"] = ui.column().classes("w-full h-full min-h-0 gap-0").style(
                "width:100%;min-width:0;flex:1;overflow:hidden;display:flex;flex-direction:column;align-items:stretch"
            )

    render_setup()
    if _saved:
        ui.notify("이전 대화를 불러왔어요", color="info", timeout=2500, position="top-right")


# ============================================================
# 실행
# ============================================================

ui.run(
    title="커스터마이징 연애 시뮬레이터",
    host="0.0.0.0",
    port=int(os.getenv("PORT", "8080")),
    reload=False,
    favicon="💬",
)
