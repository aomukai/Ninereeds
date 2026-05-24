#!/usr/bin/env python3
"""
gen_grammar.py — Generate Ninereeds grammar curriculum files via OpenRouter.

The script is intentionally cluster-scoped and resumable. Generate one grammar
directory at a time, validate, audit, then continue.

Usage:
  python3 meta/scripts/gen_grammar.py --cluster 00_relation --dry-run
  python3 meta/scripts/gen_grammar.py --cluster 00_relation
"""
from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent.parent
GRAMMAR_ROOT = ROOT / "training_data" / "grammar"
MODEL = "deepseek/deepseek-v4-flash"
MAX_TOKENS = 32768
REQUEST_TIMEOUT = 300.0


@dataclass(frozen=True)
class FileSpec:
    path: str
    focus: str
    required_terms: tuple[str, ...]
    notes: str


def make_mit_specs() -> list[FileSpec]:
    """Initial audit batch for `mit` as dative accompaniment/instrument/vehicle."""
    rows: list[tuple[str, str, tuple[str, ...], str]] = [
        ("001_mit_accompaniment_dog.md", "mit as accompaniment with a dog", ("with", "mit dem Hund", "dog"), "Use mit dem Hund. Japanese cue: と. Use realistic actions: walk, play, sit, go."),
        ("002_mit_accompaniment_cat.md", "mit as accompaniment with a cat", ("with", "mit der Katze", "cat"), "Use mit der Katze. Japanese cue: と. Use realistic actions: play, sit, walk, rest."),
        ("003_mit_accompaniment_child.md", "mit as accompaniment with a child", ("with", "mit dem Kind", "child"), "Use mit dem Kind. Japanese cue: と. Use realistic actions: play, walk, read, eat."),
        ("004_mit_accompaniment_woman.md", "mit as accompaniment with a woman", ("with", "mit der Frau", "woman"), "Use mit der Frau. Japanese cue: と. Use realistic actions: walk, talk, sit, go."),
        ("005_mit_instrument_hammer.md", "mit as instrument with a hammer", ("with", "mit dem Hammer", "hammer"), "Use mit dem Hammer. Japanese cue: で. Chinese cue: 用. Use realistic human actions: work, fix a box, fix a chair, fix a table. Use only people as agents. Allowed target nouns: box, chair, table, bench."),
        ("006_mit_instrument_broom.md", "mit as instrument with a broom", ("with", "mit dem Besen", "broom"), "Use mit dem Besen. Japanese cue: で. Chinese cue: 用. Use realistic human actions: sweep floor, sweep room, sweep kitchen. Use only people as agents. Allowed target nouns: floor, room, kitchen."),
        ("007_mit_instrument_pencil.md", "mit as instrument with a pencil", ("with", "mit dem Bleistift", "pencil"), "Use mit dem Bleistift. Japanese cue: で. Chinese cue: 用. Use realistic human actions: write in a book, write on a document, draw in a book, mark a document. Use only people as agents. Allowed target nouns: book, document."),
        ("008_mit_vehicle_bus.md", "mit as vehicle with a bus", ("by bus", "mit dem Bus", "bus"), "Use German mit dem Bus. English should say by bus, not with the bus. Japanese cue: バスで. Chinese cue: 搭公車. Use only people as agents. Use only these destinations: school, city, market, park."),
        ("009_mit_vehicle_car.md", "mit as vehicle with a car", ("by car", "mit dem Auto", "car"), "Use German mit dem Auto. English should say by car, not with the car. Japanese cue: 車で. Chinese cue: 開車 or 搭車. Use only people as agents. Use only these destinations: school, city, market, park."),
        ("010_mit_vehicle_train.md", "mit as vehicle with a train", ("by train", "mit dem Zug", "train"), "Use German mit dem Zug. English should say by train, not with the train. Japanese cue: 電車で. Chinese cue: 搭火車. Use only people as agents."),
    ]

    accompaniment = [
        ("dog", "mit dem Hund", "と", "walk, sit, play, rest"),
        ("cat", "mit der Katze", "と", "sit, play, rest, walk"),
        ("child", "mit dem Kind", "と", "walk, read, eat, play"),
        ("boy", "mit dem Jungen", "と", "walk, play, read, go"),
        ("girl", "mit dem Mädchen", "と", "walk, play, read, sit"),
        ("man", "mit dem Mann", "と", "walk, talk, sit, go"),
        ("woman", "mit der Frau", "と", "walk, talk, sit, go"),
        ("teacher", "mit dem Lehrer", "と", "read, talk, walk, sit"),
        ("doctor", "mit dem Arzt", "と", "talk, walk, sit, go"),
        ("neighbor", "mit dem Nachbarn", "と", "talk, walk, sit, go"),
    ]
    instruments = [
        ("hammer", "mit dem Hammer", "で", "work, fix a box, fix a chair, fix a table", "box, chair, table, bench"),
        ("broom", "mit dem Besen", "で", "sweep the floor, sweep the room, sweep the kitchen", "floor, room, kitchen"),
        ("pencil", "mit dem Bleistift", "で", "write in a book, write on a document, draw in a book, mark a document", "book, document"),
        ("chalk", "mit der Kreide", "で", "write in a book, write on a document, draw in a book, mark a document", "book, document"),
        ("wrench", "mit dem Schraubenschlüssel", "で", "fix a bike, fix a box, fix a bucket", "bike, box, bucket"),
        ("basket", "mit dem Korb", "で", "carry apples, carry bread, carry books", "apple, bread, book"),
        ("bucket", "mit dem Eimer", "で", "carry apples, carry bread, carry books", "apple, bread, book"),
        ("ball", "mit dem Ball", "で", "play with the ball, play together with the ball, play quietly with the ball", "ball"),
        ("book", "mit dem Buch", "で", "read, learn, show the book", "book"),
        ("blanket", "mit der Decke", "で", "cover the bed, cover the child, keep warm", "bed, child"),
    ]
    vehicles = [
        ("bus", "mit dem Bus", "by bus", "バスで", "school, city, market, park"),
        ("car", "mit dem Auto", "by car", "車で", "school, city, market, park"),
        ("train", "mit dem Zug", "by train", "電車で", "school, city, market, park"),
        ("bike", "mit dem Fahrrad", "by bike", "自転車で", "school, market, park"),
        ("boat", "mit dem Boot", "by boat", "ボートで", "city, market, park"),
        ("airplane", "mit dem Flugzeug", "by airplane", "飛行機で", "city"),
        ("truck", "mit dem Lastwagen", "by truck", "トラックで", "market, city, school"),
        ("wagon", "mit dem Wagen", "by wagon", "ワゴンで", "market, park; use wagon as a simple vehicle/cart, never as a horse carriage"),
    ]

    next_id = 11
    while next_id <= 100:
        kind = (next_id - 11) % 3
        if kind == 0:
            noun, dative, jp_cue, actions = accompaniment[((next_id - 11) // 3) % len(accompaniment)]
            filename = f"{next_id:03d}_mit_accompaniment_{noun}.md"
            rows.append((
                filename,
                f"mit as accompaniment with a {noun}",
                ("with", dative, noun),
                f"Use {dative}. Japanese cue: {jp_cue}. Chinese cue: 和. Use realistic actions: {actions}. Do not use this noun as a tool or vehicle.",
            ))
        elif kind == 1:
            noun, dative, jp_cue, actions, targets = instruments[((next_id - 12) // 3) % len(instruments)]
            filename = f"{next_id:03d}_mit_instrument_{noun}.md"
            rows.append((
                filename,
                f"mit as instrument or means with a {noun}",
                ("with", dative, noun),
                f"Use {dative}. Japanese cue: {jp_cue}. Chinese cue: 用. Use realistic human actions: {actions}. Use only people as agents. Do not use animals as agents. Allowed target nouns: {targets}. Do not add any other target nouns.",
            ))
        else:
            noun, dative, english, jp_cue, destinations = vehicles[((next_id - 13) // 3) % len(vehicles)]
            filename = f"{next_id:03d}_mit_vehicle_{noun}.md"
            rows.append((
                filename,
                f"mit as vehicle or transport means with a {noun}",
                (english, dative, noun),
                f"Use German {dative}. English should say {english}, not with the {noun}. Japanese cue: {jp_cue}. Chinese cue: 搭 or 乘. Use only people as agents. Use only these destinations: {destinations}.",
            ))
        next_id += 1

    return [
        FileSpec(
            path=f"01_means_dative_anchor/{filename}",
            focus=focus,
            required_terms=required,
            notes=notes + " Keep German dative form visible in every response. Prefer common nouns such as the boy, the woman, the child, the dog, the cat. Avoid character names in this audit batch.",
        )
        for filename, focus, required, notes in rows
    ]


CLUSTERS: dict[str, list[FileSpec]] = {
    "00_relation": [
        FileSpec(
            path="00_relation/001_relation_receiver.md",
            focus="relation and receiver",
            required_terms=("relation", "receiver"),
            notes="Explain that a receiver gets something or is helped by an action.",
        ),
        FileSpec(
            path="00_relation/002_place_source_target.md",
            focus="place, source, target",
            required_terms=("place", "source", "target"),
            notes="Contrast where something is, where movement begins, and where movement points.",
        ),
        FileSpec(
            path="00_relation/003_path_object_action.md",
            focus="path, object, action",
            required_terms=("path", "object", "action"),
            notes="Keep object as acted-on thing; keep path as route through space.",
        ),
        FileSpec(
            path="00_relation/004_owner_change_means.md",
            focus="owner, change, means",
            required_terms=("owner", "change", "means"),
            notes="Keep means as way/tool/vehicle used to do something.",
        ),
    ],
    "01_means_dative_anchor": make_mit_specs(),
}


BASE_RULES = """
You are generating one small grammar curriculum file for Ninereeds.

Output ONLY the file content. No markdown fences. No preamble.

Format rules:
- Use exactly 4 [user] / [Ninereeds] pairs.
- Each [user] tag and its English question must be on the same line.
- Each [Ninereeds] tag and the English answer must be on the same line.
- Each [Ninereeds] response has exactly four short answer lines:
  1. English, on the same line as [Ninereeds]
  2. German
  3. Japanese
  4. Traditional Chinese
- Keep [user] and [Ninereeds] tags exactly.
- Do not add headings.
- Do not use romaji.

Register:
- English: simple child-facing explanation.
- German: clear Schulbuch style.
- Japanese: plain form, natural, no ですます, no romaji.
- Chinese: Traditional Chinese, standard written register.

Content rules:
- This is a bridge file, not a grammar lecture.
- Keep vocabulary simple and concrete.
- Do not introduce abstract case terminology unless the file notes explicitly ask for it.
- Prefer common nouns over character names in audit batches.
- If a character name is used, keep it as a name and do not translate it.
- Follow the grammar target in the file notes exactly.
- Use only nouns from the grammar lexicon or nouns explicitly allowed in the file notes.
- Do not invent extra tools, places, animals, body parts, furniture, or target objects.
- Avoid pronouns in answer lines. Repeat the noun or name instead.
- Every German line must be a complete sentence, not just a phrase.
- Every English line must be a complete sentence, not just a phrase.
- Preserve the same named subject across all four response lines.
"""


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_api_key() -> str:
    load_dotenv(ROOT / ".env")
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("No API key found. Set OPENROUTER_API_KEY in .env or environment.")
    return key


def build_prompt(spec: FileSpec, previous_errors: list[str] | None = None) -> str:
    required = ", ".join(spec.required_terms)
    retry = ""
    if previous_errors:
        retry = (
            "\nPrevious attempt failed validation. Fix these errors:\n"
            + "\n".join(f"- {e}" for e in previous_errors)
            + "\n"
        )
    return f"""{BASE_RULES}

File focus: {spec.focus}
Required terms: {required}
Notes: {spec.notes}
{retry}
Generate the file now.
"""


def validate(text: str, spec: FileSpec) -> list[str]:
    errors: list[str] = []
    user_count = len(re.findall(r"^\[user\]", text, re.MULTILINE))
    nr_count = len(re.findall(r"^\[Ninereeds\]", text, re.MULTILINE))
    if user_count != 4:
        errors.append(f"expected 4 [user] tags, got {user_count}")
    if nr_count != 4:
        errors.append(f"expected 4 [Ninereeds] tags, got {nr_count}")
    if user_count != nr_count:
        errors.append(f"mismatched tag counts: {user_count} [user] vs {nr_count} [Ninereeds]")
    user_with_content = len(re.findall(r"^\[user\].+", text, re.MULTILINE))
    nr_with_content = len(re.findall(r"^\[Ninereeds\].+", text, re.MULTILINE))
    if user_with_content != user_count:
        errors.append("[user] tags must have the question on the same line")
    if nr_with_content != nr_count:
        errors.append("[Ninereeds] tags must have the English answer on the same line")
    if re.search(r"[A-Za-z]+(?:-[A-Za-z]+)?\s*\([^)]*romaji", text, re.I):
        errors.append("possible romaji explanation found")
    for term in spec.required_terms:
        if term.lower() not in text.lower():
            errors.append(f"missing required term: {term}")
    if "_instrument_" in spec.path and re.search(r"\b(dog|cat|Biscuit|Hund|Katze|犬|猫|狗|貓)\b", text, re.I):
        errors.append("instrument files must use people as agents, not animals")
    if "_instrument_" in spec.path:
        forbidden_instrument_nouns = (
            r"\b(nail|peg|fence|hallway|line|note|paper|circle|shelf|pipe|"
            r"Nagel|Pflock|Zaun|Flur|Linie|Notiz|Papier|Kreis|Regal|Rohr)\b"
            r"|釘|杭|柵|廊下|線|メモ|紙|円|棚|パイプ|"
            r"釘子|木栓|籬笆|走廊|筆記|紙|圓圈|架子|管子"
        )
        if re.search(forbidden_instrument_nouns, text, re.I):
            errors.append("instrument file invented off-lexicon target nouns")
    if "_vehicle_" in spec.path:
        if re.search(r"\b(dog|cat|Biscuit|Hund|Katze|犬|猫|狗|貓)\b", text, re.I):
            errors.append("vehicle files must use people as agents, not animals")
        if re.search(r"with the (bus|car|train)", text, re.I):
            errors.append("vehicle English should use by bus/car/train, not with the vehicle")
        if re.search(r"\b(store|work|Laden|Arbeit|仕事|商店|上班)\b", text, re.I):
            errors.append("vehicle audit files must use only school/city/market/park destinations")
    if re.search(r"\b(She|He|They|We|she|he|they|we|Sie|Er|sie|er|彼女|彼|她|他|我們|我们)\b", text):
        errors.append("pronoun found in answer/prompt; repeat the name or noun")
    if re.search(r"その|あの|この|那個|这个|這個", text):
        errors.append("demonstrative found; repeat the noun without extra pointing words")
    if re.search(r"[锤长扫车门书话马鸟鱼间园]", text):
        errors.append("possible Simplified Chinese character found; use Traditional Chinese")
    if "_vehicle_wagon" in spec.path and re.search(r"馬車|马车", text):
        errors.append("wagon should not become horse carriage")
    if "_vehicle_wagon" in spec.path and re.search(r"\b(horse|Pferd)\b|馬|马", text, re.I):
        errors.append("wagon files must not introduce horses")
    if "_instrument_ball" in spec.path and re.search(r"throws? with the ball|rolls? with the ball|wirft mit dem Ball|rollt mit dem Ball", text, re.I):
        errors.append("ball files should use play-with-ball patterns, not throw/roll-with-ball")

    blocks = re.split(r"(?=^\[user\])", text.strip(), flags=re.MULTILINE)
    blocks = [b for b in blocks if b.strip()]
    for i, block in enumerate(blocks, start=1):
        if "[Ninereeds]" not in block:
            continue
        response = block.split("[Ninereeds]", 1)[1].strip()
        lines = [ln for ln in response.splitlines() if ln.strip()]
        if len(lines) != 4:
            errors.append(f"pair {i}: expected 4 response lines, got {len(lines)}")
        elif not lines[1].rstrip().endswith((".", "!", "?")):
            errors.append(f"pair {i}: German line must be a complete sentence")
    return errors


def generate_file(client: OpenAI, spec: FileSpec, force: bool, dry_run: bool) -> str:
    out_path = GRAMMAR_ROOT / spec.path
    if out_path.exists() and not force:
        return f"SKIP {spec.path} — exists"
    if dry_run:
        return f"WOULD WRITE {spec.path}"

    errors: list[str] | None = None
    for attempt in range(1, 4):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": build_prompt(spec, errors)}],
            )
        except Exception as exc:
            return f"ERROR {spec.path}: {exc}"
        text = (resp.choices[0].message.content or "").strip()
        errors = validate(text, spec)
        if not errors:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(text + "\n", encoding="utf-8")
            return f"OK {spec.path}"
    return f"FAIL {spec.path}: {'; '.join(errors or ['unknown validation error'])}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate grammar curriculum files")
    parser.add_argument("--cluster", choices=sorted(CLUSTERS), required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Overwrite existing generated files")
    parser.add_argument("--limit", type=int, default=None, help="Generate only the first N files in this cluster")
    parser.add_argument("--offset", type=int, default=0, help="Skip the first N files in this cluster")
    parser.add_argument("--match", default=None, help="Only generate specs whose path matches this regex")
    args = parser.parse_args()

    specs = CLUSTERS[args.cluster]
    if args.offset < 0:
        parser.error("--offset must be >= 0.")
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be > 0.")
    specs = specs[args.offset:]
    if args.limit is not None:
        specs = specs[:args.limit]
    if args.match is not None:
        try:
            match_re = re.compile(args.match)
        except re.error as exc:
            parser.error(f"--match is not a valid regex: {exc}")
        specs = [spec for spec in specs if match_re.search(spec.path)]
    print(f"Grammar generation cluster: {args.cluster}", flush=True)
    print(f"Files: {len(specs)}", flush=True)
    print(f"Dry run: {args.dry_run}", flush=True)
    print(flush=True)

    client = None
    if not args.dry_run:
        client = OpenAI(
            api_key=get_api_key(),
            base_url="https://openrouter.ai/api/v1",
            timeout=REQUEST_TIMEOUT,
        )

    for spec in specs:
        if args.dry_run:
            print(generate_file(None, spec, args.force, True), flush=True)  # type: ignore[arg-type]
        else:
            print(generate_file(client, spec, args.force, False), flush=True)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
