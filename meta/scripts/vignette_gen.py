#!/usr/bin/env python3
"""Generate sentence rotation vignettes for training_data/01_language/vignettes/.

Each file shows one event from 5 syntactic/lexical angles in 4 languages.
Language order rotates across files (EDJC → DJCE → JCED → CEDJ) so no
language is always the anchor and EN/DE dominance in the weights is countered.

No [user]/[Ninereeds] tags. Format: 5 blocks × 4 lines, blank line between blocks.

Verb types:
  ditransitive — active / bekommen-pass / werden-pass / topicalization / wem-question
  transitive   — active / passive / topicalization / resultative / perspective-shift

Usage:
  python3 meta/scripts/vignette_gen.py plan [--seed 42]
  python3 meta/scripts/vignette_gen.py gen  [--workers 4] [--batch 50]
  python3 meta/scripts/vignette_gen.py status
  python3 meta/scripts/vignette_gen.py verify [--fix]
"""

from __future__ import annotations
import argparse, concurrent.futures, json, os, pathlib, random, re, sys, time

ROOT     = pathlib.Path(__file__).resolve().parents[2]
OUT_DIR  = ROOT / "training_data" / "01_language" / "vignettes"
JOBS_F   = OUT_DIR / "_jobs.jsonl"
DONE_F   = OUT_DIR / "_done.txt"
CLAIM_F  = OUT_DIR / "_claimed.txt"

# ── API (same pattern as arith_gen.py) ────────────────────────────────────────

def _read_dotenv() -> dict:
    env: dict[str, str] = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env

_dotenv = _read_dotenv()

def _get(key: str) -> str | None:
    return os.environ.get(key) or _dotenv.get(key)

def _make_client(key: str, base_url: str):
    from openai import OpenAI
    k = _get(key)
    if not k:
        return None
    return OpenAI(api_key=k, base_url=base_url)

def _sources():
    src = []
    ds = _make_client("DEEPSEEK_API_KEY", "https://api.deepseek.com/v1")
    if ds:
        src.append((ds, "deepseek-chat", {}))
    nim = _make_client("NVIDIA_API_KEY", "https://integrate.api.nvidia.com/v1")
    if nim:
        src.append((nim, "deepseek-ai/deepseek-v4-pro",
                    {"extra_body": {"chat_template_kwargs": {"thinking": False}}}))
    orc = _make_client("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1")
    if orc:
        src.append((orc, "deepseek/deepseek-v4-flash", {}))
    return src

SOURCES = _sources()

def call_api(system: str, user: str) -> tuple[str, str]:
    if not SOURCES:
        raise RuntimeError("No API key. Set NVIDIA_API_KEY or OPENROUTER_API_KEY.")
    last_err = None
    for attempt in range(5):
        for client, model, extra in SOURCES:
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user},
                    ],
                    max_tokens=600,
                    temperature=0.4,
                    **extra,
                )
                content = resp.choices[0].message.content
                if content and content.strip():
                    return content.strip(), model
            except Exception as e:
                last_err = e
        # All sources failed this round — sleep before retrying
        if "429" in str(last_err):
            wait = 10 * (2 ** attempt)   # 10s, 20s, 40s, 80s, 160s
            time.sleep(wait)
    raise RuntimeError(f"All API sources failed after retries: {last_err}")

# ── Language rotation ──────────────────────────────────────────────────────────

LANG_ROTATIONS = [
    ["EN", "DE", "JP", "ZH"],   # EDJC
    ["DE", "JP", "ZH", "EN"],   # DJCE
    ["JP", "ZH", "EN", "DE"],   # JCED
    ["ZH", "EN", "DE", "JP"],   # CEDJ
]

LANG_NAMES = {
    "EN": "English",
    "DE": "German",
    "JP": "Japanese",
    "ZH": "Chinese",
}

# ── Verb table ─────────────────────────────────────────────────────────────────
# type: "ditransitive" = agent gives theme to recipient (all 5 rotations incl. IO)
#        "transitive"  = agent acts on theme (no IO rotation set)

VERBS: list[dict] = [
    # ── ditransitive ──────────────────────────────────────────────────────────
    {"en": "give",    "de": "geben",      "jp": "あげる／くれる", "zh": "给",    "type": "ditransitive"},
    {"en": "show",    "de": "zeigen",     "jp": "見せる",         "zh": "给...看","type": "ditransitive"},
    {"en": "bring",   "de": "bringen",    "jp": "持ってくる",     "zh": "带来",  "type": "ditransitive"},
    {"en": "send",    "de": "schicken",   "jp": "送る",           "zh": "寄",    "type": "ditransitive"},
    {"en": "hand",    "de": "reichen",    "jp": "手渡す",         "zh": "递",    "type": "ditransitive"},
    {"en": "offer",   "de": "anbieten",   "jp": "差し出す",       "zh": "提供",  "type": "ditransitive"},
    {"en": "teach",   "de": "beibringen", "jp": "教える",         "zh": "教",    "type": "ditransitive"},
    {"en": "tell",    "de": "erzählen",   "jp": "話す",           "zh": "告诉",  "type": "ditransitive"},
    {"en": "lend",    "de": "leihen",     "jp": "貸す",           "zh": "借给",  "type": "ditransitive"},
    {"en": "pass",    "de": "weitergeben","jp": "渡す",           "zh": "递给",  "type": "ditransitive"},
    {"en": "throw",   "de": "zuwerfen",   "jp": "投げる",         "zh": "扔给",  "type": "ditransitive"},
    {"en": "read",    "de": "vorlesen",   "jp": "読み聞かせる",   "zh": "读给",  "type": "ditransitive"},
    {"en": "make",    "de": "machen",     "jp": "作ってあげる",   "zh": "为...做","type": "ditransitive"},
    {"en": "cook",    "de": "kochen",     "jp": "料理する",       "zh": "做饭给","type": "ditransitive"},
    {"en": "buy",     "de": "kaufen",     "jp": "買ってあげる",   "zh": "买给",  "type": "ditransitive"},
    {"en": "build",   "de": "bauen",      "jp": "作る",           "zh": "为...建","type": "ditransitive"},
    {"en": "fetch",   "de": "holen",      "jp": "取ってくる",     "zh": "取来",  "type": "ditransitive"},
    {"en": "feed",    "de": "füttern",    "jp": "食べさせる",     "zh": "喂",    "type": "ditransitive"},
    {"en": "pay",     "de": "zahlen",     "jp": "払う",           "zh": "付给",  "type": "ditransitive"},
    {"en": "sell",    "de": "verkaufen",  "jp": "売る",           "zh": "卖给",  "type": "ditransitive"},
    {"en": "write",   "de": "schreiben",  "jp": "書いてあげる",   "zh": "写给",  "type": "ditransitive"},
    {"en": "prepare", "de": "vorbereiten","jp": "用意する",       "zh": "为...准备","type": "ditransitive"},
    # ── transitive ────────────────────────────────────────────────────────────
    {"en": "chase",   "de": "jagen",      "jp": "追いかける",     "zh": "追",    "type": "transitive"},
    {"en": "carry",   "de": "tragen",     "jp": "運ぶ",           "zh": "搬",    "type": "transitive"},
    {"en": "hold",    "de": "halten",     "jp": "持つ",           "zh": "拿着",  "type": "transitive"},
    {"en": "pull",    "de": "ziehen",     "jp": "引く",           "zh": "拉",    "type": "transitive"},
    {"en": "push",    "de": "schieben",   "jp": "押す",           "zh": "推",    "type": "transitive"},
    {"en": "lift",    "de": "heben",      "jp": "持ち上げる",     "zh": "举起",  "type": "transitive"},
    {"en": "drop",    "de": "fallen lassen","jp": "落とす",       "zh": "放下",  "type": "transitive"},
    {"en": "catch",   "de": "fangen",     "jp": "捕まえる",       "zh": "抓住",  "type": "transitive"},
    {"en": "kick",    "de": "treten",     "jp": "蹴る",           "zh": "踢",    "type": "transitive"},
    {"en": "hit",     "de": "schlagen",   "jp": "叩く",           "zh": "打",    "type": "transitive"},
    {"en": "bite",    "de": "beißen",     "jp": "噛む",           "zh": "咬",    "type": "transitive"},
    {"en": "drag",    "de": "schleppen",  "jp": "引きずる",       "zh": "拖",    "type": "transitive"},
    {"en": "touch",   "de": "berühren",   "jp": "触る",           "zh": "触摸",  "type": "transitive"},
    {"en": "wash",    "de": "waschen",    "jp": "洗う",           "zh": "洗",    "type": "transitive"},
    {"en": "open",    "de": "öffnen",     "jp": "開ける",         "zh": "打开",  "type": "transitive"},
    {"en": "close",   "de": "schließen",  "jp": "閉める",         "zh": "关上",  "type": "transitive"},
    {"en": "break",   "de": "zerbrechen", "jp": "壊す",           "zh": "打破",  "type": "transitive"},
    {"en": "cut",     "de": "schneiden",  "jp": "切る",           "zh": "切",    "type": "transitive"},
    {"en": "fill",    "de": "füllen",     "jp": "満たす",         "zh": "填满",  "type": "transitive"},
    {"en": "find",    "de": "finden",     "jp": "見つける",       "zh": "找到",  "type": "transitive"},
    {"en": "clean",   "de": "putzen",     "jp": "掃除する",       "zh": "清洁",  "type": "transitive"},
    {"en": "fix",     "de": "reparieren", "jp": "直す",           "zh": "修理",  "type": "transitive"},
    {"en": "move",    "de": "bewegen",    "jp": "動かす",         "zh": "移动",  "type": "transitive"},
    {"en": "paint",   "de": "anmalen",    "jp": "塗る",           "zh": "涂",    "type": "transitive"},
    {"en": "pick",    "de": "pflücken",   "jp": "摘む",           "zh": "摘",    "type": "transitive"},
    {"en": "roll",    "de": "rollen",     "jp": "転がす",         "zh": "滚",    "type": "transitive"},
    {"en": "shake",   "de": "schütteln",  "jp": "振る",           "zh": "摇",    "type": "transitive"},
    {"en": "wrap",    "de": "einwickeln", "jp": "包む",           "zh": "包",    "type": "transitive"},
    {"en": "hug",     "de": "umarmen",    "jp": "抱きしめる",     "zh": "拥抱",  "type": "transitive"},
    {"en": "scratch", "de": "kratzen",    "jp": "引っ掻く",       "zh": "抓",    "type": "transitive"},
    {"en": "pour",    "de": "gießen",     "jp": "注ぐ",           "zh": "倒",    "type": "transitive"},
    {"en": "pack",    "de": "einpacken",  "jp": "詰める",         "zh": "打包",  "type": "transitive"},
    {"en": "fold",    "de": "falten",     "jp": "折る",           "zh": "折叠",  "type": "transitive"},
    {"en": "stack",   "de": "stapeln",    "jp": "積み重ねる",     "zh": "堆",    "type": "transitive"},
    {"en": "draw",    "de": "zeichnen",   "jp": "描く",           "zh": "画",    "type": "transitive"},
    {"en": "hang",    "de": "aufhängen",  "jp": "掛ける",         "zh": "挂",    "type": "transitive"},
    {"en": "plant",   "de": "pflanzen",   "jp": "植える",         "zh": "种",    "type": "transitive"},
    {"en": "water",   "de": "gießen",     "jp": "水をやる",       "zh": "浇水",  "type": "transitive"},
    {"en": "press",   "de": "drücken",    "jp": "押さえる",       "zh": "按",    "type": "transitive"},
    {"en": "squeeze", "de": "quetschen",  "jp": "絞る",           "zh": "挤",    "type": "transitive"},
    {"en": "place",   "de": "legen",      "jp": "置く",           "zh": "放",    "type": "transitive"},
    {"en": "take",    "de": "nehmen",     "jp": "取る",           "zh": "拿",    "type": "transitive"},
    {"en": "keep",    "de": "behalten",   "jp": "持っておく",     "zh": "保留",  "type": "transitive"},
    {"en": "drop",    "de": "fallen lassen","jp": "落とす",       "zh": "丢下",  "type": "transitive"},
    {"en": "put",     "de": "stellen",    "jp": "置く",           "zh": "放",    "type": "transitive"},
    {"en": "set",     "de": "setzen",     "jp": "セットする",     "zh": "放置",  "type": "transitive"},
    {"en": "pick up", "de": "aufheben",   "jp": "拾う",           "zh": "捡起",  "type": "transitive"},
    {"en": "tie",     "de": "binden",     "jp": "縛る",           "zh": "绑",    "type": "transitive"},
    {"en": "release", "de": "loslassen",  "jp": "放す",           "zh": "放开",  "type": "transitive"},
    {"en": "lead",    "de": "führen",     "jp": "連れて行く",     "zh": "带领",  "type": "transitive"},
    {"en": "pull out","de": "herausziehen","jp": "引き出す",      "zh": "拉出",  "type": "transitive"},
    {"en": "collect", "de": "sammeln",    "jp": "集める",         "zh": "收集",  "type": "transitive"},
    {"en": "leave",   "de": "lassen",     "jp": "残す",           "zh": "留下",  "type": "transitive"},
]

# ── NP tables ──────────────────────────────────────────────────────────────────
# animate: can be agents OR recipients
# For German we just supply the base (nominative) form; DeepSeek handles case inflection.
# The NOM form is included as a hint; the model must apply correct case throughout.

ANIMATE_NPS: list[dict] = [
    {"en": "the boy",      "de": "der Junge",    "jp": "男の子",    "zh": "男孩"},
    {"en": "the girl",     "de": "das Mädchen",  "jp": "女の子",    "zh": "女孩"},
    {"en": "the man",      "de": "der Mann",     "jp": "男の人",    "zh": "男人"},
    {"en": "the woman",    "de": "die Frau",     "jp": "女の人",    "zh": "女人"},
    {"en": "the child",    "de": "das Kind",     "jp": "子ども",    "zh": "孩子"},
    {"en": "the teacher",  "de": "die Lehrerin", "jp": "先生",      "zh": "老师"},
    {"en": "the farmer",   "de": "der Bauer",    "jp": "農家の人",  "zh": "农夫"},
    {"en": "the doctor",   "de": "der Arzt",     "jp": "医者",      "zh": "医生"},
    {"en": "the baker",    "de": "der Bäcker",   "jp": "パン屋さん","zh": "面包师"},
    {"en": "the neighbor", "de": "die Nachbarin","jp": "隣の人",    "zh": "邻居"},
    {"en": "the dog",      "de": "der Hund",     "jp": "犬",        "zh": "狗"},
    {"en": "the cat",      "de": "die Katze",    "jp": "猫",        "zh": "猫"},
    {"en": "the horse",    "de": "das Pferd",    "jp": "馬",        "zh": "马"},
    {"en": "the rabbit",   "de": "der Hase",     "jp": "うさぎ",    "zh": "兔子"},
    {"en": "the bird",     "de": "der Vogel",    "jp": "鳥",        "zh": "鸟"},
    {"en": "the friend",   "de": "die Freundin", "jp": "友達",      "zh": "朋友"},
    {"en": "the mother",   "de": "die Mutter",   "jp": "お母さん",  "zh": "妈妈"},
    {"en": "the father",   "de": "der Vater",    "jp": "お父さん",  "zh": "爸爸"},
    {"en": "the sister",   "de": "die Schwester","jp": "お姉さん",  "zh": "姐姐"},
    {"en": "the brother",  "de": "der Bruder",   "jp": "お兄さん",  "zh": "哥哥"},
    {"en": "the student",  "de": "der Schüler",  "jp": "生徒",      "zh": "学生"},
    {"en": "the fish",     "de": "der Fisch",    "jp": "魚",        "zh": "鱼"},
]

INANIMATE_NPS: list[dict] = [
    {"en": "the ball",    "de": "der Ball",       "jp": "ボール",    "zh": "球"},
    {"en": "the book",    "de": "das Buch",       "jp": "本",        "zh": "书"},
    {"en": "the apple",   "de": "der Apfel",      "jp": "りんご",    "zh": "苹果"},
    {"en": "the letter",  "de": "der Brief",      "jp": "手紙",      "zh": "信"},
    {"en": "the key",     "de": "der Schlüssel",  "jp": "鍵",        "zh": "钥匙"},
    {"en": "the flower",  "de": "die Blume",      "jp": "花",        "zh": "花"},
    {"en": "the cup",     "de": "die Tasse",      "jp": "カップ",    "zh": "杯子"},
    {"en": "the bag",     "de": "die Tasche",     "jp": "バッグ",    "zh": "包"},
    {"en": "the box",     "de": "der Kasten",     "jp": "箱",        "zh": "箱子"},
    {"en": "the gift",    "de": "das Geschenk",   "jp": "プレゼント","zh": "礼物"},
    {"en": "the stone",   "de": "der Stein",      "jp": "石",        "zh": "石头"},
    {"en": "the stick",   "de": "der Stock",      "jp": "棒",        "zh": "棍子"},
    {"en": "the bone",    "de": "der Knochen",    "jp": "骨",        "zh": "骨头"},
    {"en": "the bread",   "de": "das Brot",       "jp": "パン",      "zh": "面包"},
    {"en": "the cake",    "de": "der Kuchen",     "jp": "ケーキ",    "zh": "蛋糕"},
    {"en": "the coin",    "de": "die Münze",      "jp": "コイン",    "zh": "硬币"},
    {"en": "the ring",    "de": "der Ring",       "jp": "指輪",      "zh": "戒指"},
    {"en": "the toy",     "de": "das Spielzeug",  "jp": "おもちゃ",  "zh": "玩具"},
    {"en": "the hat",     "de": "der Hut",        "jp": "帽子",      "zh": "帽子"},
    {"en": "the coat",    "de": "der Mantel",     "jp": "コート",    "zh": "外套"},
    {"en": "the pen",     "de": "der Stift",      "jp": "ペン",      "zh": "笔"},
    {"en": "the rope",    "de": "das Seil",       "jp": "ロープ",    "zh": "绳子"},
    {"en": "the seed",    "de": "der Samen",      "jp": "種",        "zh": "种子"},
    {"en": "the bottle",  "de": "die Flasche",    "jp": "ボトル",    "zh": "瓶子"},
    {"en": "the basket",  "de": "der Korb",       "jp": "かご",      "zh": "篮子"},
    {"en": "the plate",   "de": "der Teller",     "jp": "お皿",      "zh": "盘子"},
    {"en": "the bowl",    "de": "die Schüssel",   "jp": "ボウル",    "zh": "碗"},
    {"en": "the package", "de": "das Paket",      "jp": "荷物",      "zh": "包裹"},
    {"en": "the shoe",    "de": "der Schuh",      "jp": "靴",        "zh": "鞋子"},
    {"en": "the jar",     "de": "das Glas",       "jp": "ビン",      "zh": "罐子"},
    {"en": "the leaf",    "de": "das Blatt",      "jp": "葉っぱ",    "zh": "叶子"},
    {"en": "the brush",   "de": "der Pinsel",     "jp": "ブラシ",    "zh": "刷子"},
    {"en": "the pot",     "de": "der Topf",       "jp": "鍋",        "zh": "锅"},
    {"en": "the blanket", "de": "die Decke",      "jp": "毛布",      "zh": "毯子"},
    {"en": "the bucket",  "de": "der Eimer",      "jp": "バケツ",    "zh": "水桶"},
    {"en": "the rope",    "de": "das Seil",       "jp": "縄",        "zh": "绳"},
    {"en": "the hammer",  "de": "der Hammer",     "jp": "ハンマー",  "zh": "锤子"},
]

# ── Prompt templates ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You generate sentence rotation vignettes for language model training.
Each vignette shows one event from 5 different syntactic or lexical angles.
Output ONLY the requested blocks. No labels, no commentary, no markdown, no tags.
"""

def _lang_order_desc(rotation: list[str]) -> str:
    return " / ".join(LANG_NAMES[c] for c in rotation)

def build_prompt_ditransitive(
    verb: dict, agent: dict, recipient: dict, theme: dict,
    possessor: dict, rotation: list[str]
) -> str:
    lang_desc = _lang_order_desc(rotation)
    # Determine which is first so the question in rotation 5 is in that language
    first_lang = LANG_NAMES[rotation[0]]

    return f"""\
Scenario:
- Event type: ditransitive transfer
- Verb: {verb["en"]} (German: {verb["de"]}, Japanese: {verb["jp"]}, Chinese: {verb["zh"]})
- Agent: {agent["en"]} (German: {agent["de"]}, Japanese: {agent["jp"]}, Chinese: {agent["zh"]})
- Recipient: {recipient["en"]} (German: {recipient["de"]}, Japanese: {recipient["jp"]}, Chinese: {recipient["zh"]})
- Theme: {theme["en"]} (German: {theme["de"]}, Japanese: {theme["jp"]}, Chinese: {theme["zh"]})
- Possessor of theme: {possessor["en"]} (German: {possessor["de"]}, Japanese: {possessor["jp"]}, Chinese: {possessor["zh"]})

Language line order per block: {lang_desc}

Output exactly 5 blocks separated by a blank line.
Each block has exactly 4 lines: one sentence per language, in the order above.
No labels. No tags. No extra text before or after.

Block 1 — Active: agent {verb["en"]}s the theme (possessor's) to the recipient.
Block 2 — Recipient focus: recipient receives the theme from the agent. German: bekommen-passive. Other languages: natural recipient-as-topic construction.
Block 3 — Theme focus: the theme (possessor's) is {verb["en"]}n to the recipient by the agent. German: werden-passive. Other languages: natural passive or theme-as-topic.
Block 4 — Theme topicalization / contrastive: it is the theme that the agent {verb["en"]}s to the recipient (contrastive or left-dislocation in each language).
Block 5 — Question: who receives the theme? Natural question form in each language. (First line in {first_lang}, then the other three languages in order.)

CRITICAL RULES:
- German: apply correct case marking throughout. NOM for grammatical subject, ACC for direct object, DAT for indirect object/recipient, GEN for possessor. Do NOT use nominative everywhere.
- Japanese: use natural particles (が、を、に、から、で) appropriate to each rotation. Use natural passive (〜られる) for block 3.
- Chinese: use 被 for passive where natural; 把 construction for active where natural; topic-comment structure for topicalization. Natural question with 谁 for block 5.
- English: use natural passive (is given / receives) — no awkward word-for-word renderings.
- Each line must be a complete grammatical sentence.
- The possessor modifies the theme (e.g., "the man's ball", "des Mannes Ball").
- Do NOT output any label, header, or commentary."""

def build_prompt_transitive(
    verb: dict, agent: dict, theme: dict, rotation: list[str]
) -> str:
    lang_desc = _lang_order_desc(rotation)
    first_lang = LANG_NAMES[rotation[0]]

    return f"""\
Scenario:
- Event type: transitive action
- Verb: {verb["en"]} (German: {verb["de"]}, Japanese: {verb["jp"]}, Chinese: {verb["zh"]})
- Agent: {agent["en"]} (German: {agent["de"]}, Japanese: {agent["jp"]}, Chinese: {agent["zh"]})
- Theme/Patient: {theme["en"]} (German: {theme["de"]}, Japanese: {theme["jp"]}, Chinese: {theme["zh"]})

Language line order per block: {lang_desc}

Output exactly 5 blocks separated by a blank line.
Each block has exactly 4 lines: one sentence per language, in the order above.
No labels. No tags. No extra text before or after.

Block 1 — Active: agent {verb["en"]}s the theme.
Block 2 — Passive: the theme is {verb["en"]}d by the agent. German: werden-passive. Japanese: 〜られる. Chinese: 被-construction.
Block 3 — Theme topicalization / contrastive: it is the theme that the agent {verb["en"]}s (left-dislocation or cleft in each language).
Block 4 — Resultative: the agent {verb["en"]}s the theme, with a result or completive phrase describing the outcome state. Use the SAME main verb as Block 1 — do NOT substitute a different verb. Add a result phrase that follows naturally from the action (e.g. "into pieces", "clean", "away", "open", "flat", "apart", "in two"). English: agent + verb + theme + result phrase. German: agent + verb + theme (ACC) + result phrase. Japanese: agent は/が theme を verb + resultative (~てV2 or compound verb). Chinese: agent + 把 + theme + verb + resultative complement (e.g. 切成片, 洗干净, 推开).
Block 5 — Perspective shift: describe the SAME event from the theme/patient's perspective as grammatical subject, but keep the same underlying action and direction. Good: "The dog chases the cat" → "The cat is chased by the dog" or "The cat runs from the dog." BAD: reversing who does what ("the cat chases the dog"). First line in {first_lang}.

CRITICAL RULES:
- German: NOM for grammatical subject, ACC for direct object. Apply correct case to articles and adjectives.
- Japanese: が for subject, を for object; passive 〜られる natural for block 2.
- Chinese: 被 passive for block 2; 把 construction where natural for active; topic-comment for block 3.
- English: idiomatic — avoid word-for-word renderings.
- Each line must be a complete grammatical sentence.
- Do NOT output any label, header, or commentary."""

# ── Verification ───────────────────────────────────────────────────────────────

def verify_text(text: str) -> list[str]:
    """Return list of error strings; empty = clean."""
    errors = []
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    if len(blocks) != 5:
        errors.append(f"expected 5 blocks, got {len(blocks)}")
        return errors  # rest of checks don't make sense if block count wrong
    for i, block in enumerate(blocks, 1):
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if len(lines) != 4:
            errors.append(f"block {i}: expected 4 lines, got {len(lines)}")
        for ln in lines:
            if "[user]" in ln or "[Ninereeds]" in ln:
                errors.append(f"block {i}: contains [user]/[Ninereeds] tag")
    return errors

# ── Job planning ───────────────────────────────────────────────────────────────

def _str_id(job: dict) -> str:
    if job["type"] == "ditransitive":
        return (f"{job['verb']['en']}|{job['agent']['en']}|"
                f"{job['recipient']['en']}|{job['theme']['en']}|{job['possessor']['en']}")
    return f"{job['verb']['en']}|{job['agent']['en']}|{job['theme']['en']}"


def plan(seed: int = 42) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    ditrans_verbs = [v for v in VERBS if v["type"] == "ditransitive"]
    trans_verbs   = [v for v in VERBS if v["type"] == "transitive"]
    # deduplicate verbs that appear twice (e.g. "drop")
    seen_v: set[str] = set()
    ditrans_verbs_u, trans_verbs_u = [], []
    for v in ditrans_verbs:
        if v["en"] not in seen_v:
            ditrans_verbs_u.append(v); seen_v.add(v["en"])
    for v in trans_verbs:
        if v["en"] not in seen_v:
            trans_verbs_u.append(v); seen_v.add(v["en"])

    jobs: list[dict] = []

    # ── ditransitive ──────────────────────────────────────────────────────────
    # For each verb, sample agent × recipient × theme × possessor combos.
    # Constraints: agent ≠ recipient ≠ possessor; theme is always inanimate.
    combos_per_ditrans = 50
    for verb in ditrans_verbs_u:
        pool = []
        for agent in ANIMATE_NPS:
            for recipient in ANIMATE_NPS:
                if agent["en"] == recipient["en"]:
                    continue
                for theme in INANIMATE_NPS:
                    for possessor in ANIMATE_NPS:
                        if possessor["en"] in (agent["en"], recipient["en"]):
                            continue
                        pool.append((agent, recipient, theme, possessor))
        sample = rng.sample(pool, min(combos_per_ditrans, len(pool)))
        for agent, recipient, theme, possessor in sample:
            jobs.append({
                "type": "ditransitive",
                "verb": verb,
                "agent": agent,
                "recipient": recipient,
                "theme": theme,
                "possessor": possessor,
            })

    # ── transitive ────────────────────────────────────────────────────────────
    # agent × theme; animate agents only; theme can be inanimate or (some verbs) animate.
    combos_per_trans = 35
    for verb in trans_verbs_u:
        # Allow animate themes for chase/hug/hold/lead/touch/bite/scratch/hug
        animate_theme_ok = verb["en"] in {
            "chase", "hug", "hold", "touch", "bite", "scratch", "lead",
            "carry", "drag", "push", "pull", "lift", "kick", "hit",
            "release", "tie", "pick up", "collect",
        }
        theme_pool = INANIMATE_NPS[:]
        if animate_theme_ok:
            theme_pool += ANIMATE_NPS
        pool = []
        for agent in ANIMATE_NPS:
            for theme in theme_pool:
                if theme.get("en") == agent.get("en"):
                    continue
                pool.append((agent, theme))
        sample = rng.sample(pool, min(combos_per_trans, len(pool)))
        for agent, theme in sample:
            jobs.append({
                "type": "transitive",
                "verb": verb,
                "agent": agent,
                "theme": theme,
            })

    # Shuffle and assign file numbers + language rotation
    rng.shuffle(jobs)
    for i, job in enumerate(jobs):
        job["id"]       = i + 1
        job["outfile"]  = f"v_{i+1:04d}.md"
        job["rotation"] = LANG_ROTATIONS[i % 4]

    # Write jobs file
    with JOBS_F.open("w", encoding="utf-8") as f:
        for job in jobs:
            f.write(json.dumps(job, ensure_ascii=False) + "\n")

    # Count by type
    n_di = sum(1 for j in jobs if j["type"] == "ditransitive")
    n_tr = sum(1 for j in jobs if j["type"] == "transitive")
    print(f"Planned {len(jobs)} jobs → {JOBS_F.relative_to(ROOT)}")
    print(f"  ditransitive: {n_di}  ({len(ditrans_verbs_u)} verbs × ~{combos_per_ditrans} combos)")
    print(f"  transitive:   {n_tr}  ({len(trans_verbs_u)} verbs × ~{combos_per_trans} combos)")
    print(f"  Language rotations: EDJC={sum(1 for j in jobs if j['rotation']==['EN','DE','JP','ZH'])} "
          f"DJCE={sum(1 for j in jobs if j['rotation']==['DE','JP','ZH','EN'])} "
          f"JCED={sum(1 for j in jobs if j['rotation']==['JP','ZH','EN','DE'])} "
          f"CEDJ={sum(1 for j in jobs if j['rotation']==['ZH','EN','DE','JP'])}")
    print(f"\nRun: python3 meta/scripts/vignette_gen.py gen --workers 4")

# ── Single job processing ──────────────────────────────────────────────────────

def process_job(job: dict) -> dict:
    outpath = OUT_DIR / job["outfile"]
    if outpath.exists():
        return {"id": job["id"], "status": "skip"}

    rotation = job["rotation"]
    try:
        if job["type"] == "ditransitive":
            user_prompt = build_prompt_ditransitive(
                job["verb"], job["agent"], job["recipient"],
                job["theme"], job["possessor"], rotation,
            )
        else:
            user_prompt = build_prompt_transitive(
                job["verb"], job["agent"], job["theme"], rotation,
            )

        text, model = call_api(SYSTEM_PROMPT, user_prompt)

        # Strip any accidental markdown fences
        text = re.sub(r"^```[^\n]*\n?", "", text).rstrip("`").strip()

        errors = verify_text(text)
        if errors:
            return {"id": job["id"], "status": "error",
                    "msg": "; ".join(errors), "raw": text[:200]}

        outpath.write_text(text + "\n", encoding="utf-8")
        return {"id": job["id"], "status": "ok", "model": model}

    except Exception as e:
        return {"id": job["id"], "status": "error", "msg": str(e)}

# ── Generation loop ────────────────────────────────────────────────────────────

def load_jobs() -> list[dict]:
    if not JOBS_F.exists():
        sys.exit(f"No jobs file found. Run: python3 meta/scripts/vignette_gen.py plan")
    return [json.loads(ln) for ln in JOBS_F.read_text(encoding="utf-8").splitlines() if ln.strip()]

def gen(workers: int = 4, batch: int = 0) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jobs = load_jobs()

    # Filter to pending (output file not yet written)
    pending = [j for j in jobs if not (OUT_DIR / j["outfile"]).exists()]
    if batch > 0:
        pending = pending[:batch]

    if not pending:
        print("Nothing to do — all jobs complete.")
        return

    done_count = len(jobs) - len([j for j in jobs if not (OUT_DIR / j["outfile"]).exists()])
    print(f"Pending: {len(pending)} / {len(jobs)}  (done: {done_count})")
    print(f"Workers: {workers}\n")

    results: dict[str, list] = {"ok": [], "skip": [], "error": []}

    if workers == 1:
        for j in pending:
            r = process_job(j)
            results[r["status"]].append(r)
            suffix = f" ({r.get('model','')})" if r["status"] == "ok" else \
                     f" — {r.get('msg','')[:80]}" if r["status"] == "error" else ""
            print(f"  [{j['id']:04d}] {r['status']}{suffix}")
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(process_job, j): j for j in pending}
            for fut in concurrent.futures.as_completed(futs):
                j = futs[fut]
                r = fut.result()
                results[r["status"]].append(r)
                suffix = f" ({r.get('model','')})" if r["status"] == "ok" else \
                         f" — {r.get('msg','')[:80]}" if r["status"] == "error" else ""
                print(f"  [{j['id']:04d}] {r['status']}{suffix}", flush=True)

    print(f"\nDone: {len(results['ok'])} ok  "
          f"{len(results['skip'])} skip  {len(results['error'])} error")
    if results["error"]:
        print("\nErrors:")
        for r in results["error"]:
            print(f"  [{r['id']:04d}] {r.get('msg','')}")

# ── Status ─────────────────────────────────────────────────────────────────────

def status() -> None:
    if not JOBS_F.exists():
        print("No jobs planned yet. Run: plan")
        return
    jobs = load_jobs()
    done   = [j for j in jobs if (OUT_DIR / j["outfile"]).exists()]
    pend   = [j for j in jobs if not (OUT_DIR / j["outfile"]).exists()]
    di_d   = sum(1 for j in done if j["type"] == "ditransitive")
    tr_d   = sum(1 for j in done if j["type"] == "transitive")
    print(f"Total jobs : {len(jobs)}")
    print(f"Done       : {len(done)}  (ditransitive: {di_d}, transitive: {tr_d})")
    print(f"Pending    : {len(pend)}")
    if pend:
        print(f"\nRun: python3 meta/scripts/vignette_gen.py gen --workers 4")

# ── Verify ─────────────────────────────────────────────────────────────────────

def verify(fix: bool = False) -> None:
    files = sorted(OUT_DIR.glob("v_*.md"))
    if not files:
        print("No vignette files found.")
        return
    ok, bad = 0, 0
    for p in files:
        text = p.read_text(encoding="utf-8").strip()
        errs = verify_text(text)
        if errs:
            bad += 1
            print(f"  BAD  {p.name}: {'; '.join(errs)}")
            if fix:
                p.unlink()
                print(f"       → deleted (will regenerate on next gen run)")
        else:
            ok += 1
    print(f"\n{ok} clean, {bad} bad" + (" — deleted bad files" if fix and bad else ""))

# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="Vignette rotation generator")
    sub = ap.add_subparsers(dest="cmd")

    p_plan = sub.add_parser("plan", help="Build job queue")
    p_plan.add_argument("--seed", type=int, default=42)

    p_gen = sub.add_parser("gen", help="Generate files")
    p_gen.add_argument("--workers", type=int, default=4)
    p_gen.add_argument("--batch",   type=int, default=0,
                       help="limit to N jobs this run (0 = all pending)")

    sub.add_parser("status", help="Show progress")

    p_ver = sub.add_parser("verify", help="Check generated files")
    p_ver.add_argument("--fix", action="store_true",
                       help="Delete bad files so they regenerate")

    args = ap.parse_args()

    if args.cmd == "plan":
        plan(seed=args.seed)
    elif args.cmd == "gen":
        gen(workers=args.workers, batch=args.batch)
    elif args.cmd == "status":
        status()
    elif args.cmd == "verify":
        verify(fix=args.fix)
    else:
        ap.print_help()

if __name__ == "__main__":
    main()
