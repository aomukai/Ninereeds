#!/usr/bin/env python3
"""
Lang-4 corpus generator — prepositions: location, movement, instrument.

Generates training_data/lang/lang_4/ from a fixed job matrix.
No plan phase — all jobs are pre-defined in JOBS below.

Sub-levels:
  4a          — static location (German Wechselpräpositionen + dative)
  4b_goal     — directed movement: goal (accusative)
  4b_src      — directed movement: source (von/aus + dative)
  4b_path     — directed movement: path (durch/über/entlang + accusative)
  4b_contrast — explicit dative vs accusative contrast pairs
  4c_tool     — instrument: tools
  4c_body     — instrument: body parts
  4c_vehicle  — instrument: means of transport
  4c_contrast — comitative vs instrumental distinction

Usage:
  python3 meta/scripts/lang4.py gen    [--workers 4] [--batch 5] [--limit N] [--dry-run]
  python3 meta/scripts/lang4.py report

Auth:
  1. OPENROUTER_API_KEY env var
  2. OPENAI_API_KEY env var
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR   = REPO_ROOT / "training_data" / "lang" / "lang_4"
BASE_URL  = "https://openrouter.ai/api/v1"
MODEL     = "deepseek/deepseek-v4-flash"

_lock = threading.Lock()

# ─────────────────────────────────────────────────────────────────
# Job matrix — all Level-4 files
# ─────────────────────────────────────────────────────────────────

JOBS: list[dict] = [
    # ── 4A: static location ──────────────────────────────────────
    # auf (on) — dative
    {"frame_id": "4a_on_lie",    "sublevel": "4a", "prep_en": "on",  "prep_de": "auf", "case_de": "dative", "verb_en": "lie",   "desc": "inanimate object rests on a horizontal surface"},
    {"frame_id": "4a_on_sit",    "sublevel": "4a", "prep_en": "on",  "prep_de": "auf", "case_de": "dative", "verb_en": "sit",   "desc": "animate subject sits on a surface"},
    {"frame_id": "4a_on_stand",  "sublevel": "4a", "prep_en": "on",  "prep_de": "auf", "case_de": "dative", "verb_en": "stand", "desc": "subject stands on a surface — floor, stage, ground"},
    {"frame_id": "4a_on_hang",   "sublevel": "4a", "prep_en": "on",  "prep_de": "an",  "case_de": "dative", "verb_en": "hang",  "desc": "object hangs on a wall or hook — DE uses an, not auf"},
    # unter (under) — dative
    {"frame_id": "4a_under_be",  "sublevel": "4a", "prep_en": "under", "prep_de": "unter", "case_de": "dative", "verb_en": "be",   "desc": "object or creature exists beneath something"},
    {"frame_id": "4a_under_sit", "sublevel": "4a", "prep_en": "under", "prep_de": "unter", "case_de": "dative", "verb_en": "sit",  "desc": "animate subject sits under something"},
    {"frame_id": "4a_under_hide","sublevel": "4a", "prep_en": "under", "prep_de": "unter", "case_de": "dative", "verb_en": "hide", "desc": "subject hides under something"},
    {"frame_id": "4a_under_lie", "sublevel": "4a", "prep_en": "under", "prep_de": "unter", "case_de": "dative", "verb_en": "lie",  "desc": "inanimate object lies under something"},
    # in (inside) — dative
    {"frame_id": "4a_in_be",     "sublevel": "4a", "prep_en": "in",  "prep_de": "in",  "case_de": "dative", "verb_en": "be",    "desc": "inanimate object is contained inside something"},
    {"frame_id": "4a_in_sit",    "sublevel": "4a", "prep_en": "in",  "prep_de": "in",  "case_de": "dative", "verb_en": "sit",   "desc": "animate subject sits inside a room or container"},
    {"frame_id": "4a_in_wait",   "sublevel": "4a", "prep_en": "in",  "prep_de": "in",  "case_de": "dative", "verb_en": "wait",  "desc": "subject waits inside a space"},
    {"frame_id": "4a_in_sleep",  "sublevel": "4a", "prep_en": "in",  "prep_de": "in",  "case_de": "dative", "verb_en": "sleep", "desc": "subject sleeps in a bed or room"},
    {"frame_id": "4a_in_work",   "sublevel": "4a", "prep_en": "in/at","prep_de": "in", "case_de": "dative", "verb_en": "work",  "desc": "subject works in a space — JP に vs で distinction: existence vs activity location"},
    # neben (beside) — dative
    {"frame_id": "4a_beside_sit",   "sublevel": "4a", "prep_en": "beside", "prep_de": "neben", "case_de": "dative", "verb_en": "sit",   "desc": "animate subject sits beside something"},
    {"frame_id": "4a_beside_stand", "sublevel": "4a", "prep_en": "beside", "prep_de": "neben", "case_de": "dative", "verb_en": "stand", "desc": "subject stands beside something"},
    {"frame_id": "4a_beside_be",    "sublevel": "4a", "prep_en": "beside", "prep_de": "neben", "case_de": "dative", "verb_en": "be",    "desc": "inanimate object is beside something"},
    # hinter (behind) — dative
    {"frame_id": "4a_behind_hide",  "sublevel": "4a", "prep_en": "behind", "prep_de": "hinter", "case_de": "dative", "verb_en": "hide",  "desc": "subject hides behind something"},
    {"frame_id": "4a_behind_stand", "sublevel": "4a", "prep_en": "behind", "prep_de": "hinter", "case_de": "dative", "verb_en": "stand", "desc": "subject stands behind something"},
    {"frame_id": "4a_behind_be",    "sublevel": "4a", "prep_en": "behind", "prep_de": "hinter", "case_de": "dative", "verb_en": "be",    "desc": "object is behind something"},
    # vor (in front of) — dative
    {"frame_id": "4a_front_stand",  "sublevel": "4a", "prep_en": "in front of", "prep_de": "vor", "case_de": "dative", "verb_en": "stand", "desc": "subject stands in front of something"},
    {"frame_id": "4a_front_wait",   "sublevel": "4a", "prep_en": "in front of", "prep_de": "vor", "case_de": "dative", "verb_en": "wait",  "desc": "subject waits in front of something"},
    {"frame_id": "4a_front_be",     "sublevel": "4a", "prep_en": "in front of", "prep_de": "vor", "case_de": "dative", "verb_en": "be",    "desc": "object is in front of something"},
    # zwischen (between) — dative
    {"frame_id": "4a_between_sit",  "sublevel": "4a", "prep_en": "between", "prep_de": "zwischen", "case_de": "dative", "verb_en": "sit",   "desc": "subject sits between two things"},
    {"frame_id": "4a_between_stand","sublevel": "4a", "prep_en": "between", "prep_de": "zwischen", "case_de": "dative", "verb_en": "stand", "desc": "subject stands between two things"},
    {"frame_id": "4a_between_be",   "sublevel": "4a", "prep_en": "between", "prep_de": "zwischen", "case_de": "dative", "verb_en": "be",    "desc": "object is between two things"},
    # über (above) — dative
    {"frame_id": "4a_above_hang",   "sublevel": "4a", "prep_en": "above", "prep_de": "über", "case_de": "dative", "verb_en": "hang", "desc": "object hangs above something — lamp above table"},
    {"frame_id": "4a_above_fly",    "sublevel": "4a", "prep_en": "above", "prep_de": "über", "case_de": "dative", "verb_en": "fly",  "desc": "subject flies or floats above something"},
    {"frame_id": "4a_above_be",     "sublevel": "4a", "prep_en": "above", "prep_de": "über", "case_de": "dative", "verb_en": "be",   "desc": "object is above something without contact"},
    # an (at/on vertical surface) — dative
    {"frame_id": "4a_at_stand",     "sublevel": "4a", "prep_en": "at", "prep_de": "an", "case_de": "dative", "verb_en": "stand", "desc": "subject stands at a vertical surface — wall, window, door"},
    {"frame_id": "4a_at_wait",      "sublevel": "4a", "prep_en": "at", "prep_de": "an", "case_de": "dative", "verb_en": "wait",  "desc": "subject waits at a point or station — am Bahnhof, an der Haltestelle"},
    {"frame_id": "4a_at_sit",       "sublevel": "4a", "prep_en": "at", "prep_de": "an", "case_de": "dative", "verb_en": "sit",   "desc": "subject sits at a table or desk — an (edge contact) vs auf (surface contact)"},
    # bei/nahe (near) — dative
    {"frame_id": "4a_near_live",    "sublevel": "4a", "prep_en": "near", "prep_de": "bei/nahe", "case_de": "dative", "verb_en": "live",  "desc": "subject lives near a place — habitual proximity"},
    {"frame_id": "4a_near_sit",     "sublevel": "4a", "prep_en": "near", "prep_de": "bei/nahe", "case_de": "dative", "verb_en": "sit",   "desc": "subject sits near something"},
    {"frame_id": "4a_near_be",      "sublevel": "4a", "prep_en": "near", "prep_de": "bei/nahe", "case_de": "dative", "verb_en": "be",    "desc": "object is near something"},
    # JP いる vs ある animate/inanimate contrast
    {"frame_id": "4a_iru_aru_in",   "sublevel": "4a", "prep_en": "in",    "prep_de": "in",    "case_de": "dative", "verb_en": "be", "desc": "JP iru vs aru: animate (iru) vs inanimate (aru) subject inside a space — same DE/EN sentence, different JP verb"},
    {"frame_id": "4a_iru_aru_on",   "sublevel": "4a", "prep_en": "on",    "prep_de": "auf",   "case_de": "dative", "verb_en": "be", "desc": "JP iru vs aru: animate vs inanimate subject on a surface"},
    {"frame_id": "4a_iru_aru_under","sublevel": "4a", "prep_en": "under", "prep_de": "unter", "case_de": "dative", "verb_en": "be", "desc": "JP iru vs aru: animate vs inanimate subject under something"},
    # JP に vs で (existence at location vs activity at location)
    {"frame_id": "4a_ni_de_study",  "sublevel": "4a", "prep_en": "at/in", "prep_de": "in", "case_de": "dative", "verb_en": "study", "desc": "JP ni vs de: studying at the library — de marks where the activity happens, ni marks existence"},
    {"frame_id": "4a_ni_de_play",   "sublevel": "4a", "prep_en": "in",    "prep_de": "in", "case_de": "dative", "verb_en": "play",  "desc": "JP ni vs de: playing in the park — de required with activity verbs"},
    {"frame_id": "4a_ni_de_eat",    "sublevel": "4a", "prep_en": "at/in", "prep_de": "in", "case_de": "dative", "verb_en": "eat",   "desc": "JP ni vs de: eating in the restaurant — で食べる vs に食べに行く"},
    # DE an vs in for institutions
    {"frame_id": "4a_de_an_in",     "sublevel": "4a", "prep_en": "at/in", "prep_de": "an/in", "case_de": "dative", "verb_en": "be", "desc": "DE an der Schule (at the school as institution) vs in der Schule (physically inside the building)"},

    # ── 4B: movement — GOAL ──────────────────────────────────────
    # into / in + accusative
    {"frame_id": "4b_into_run",    "sublevel": "4b_goal", "prep_en": "into", "prep_de": "in+acc", "verb_en": "run",   "desc": "running into an enclosed space — ins Haus laufen"},
    {"frame_id": "4b_into_walk",   "sublevel": "4b_goal", "prep_en": "into", "prep_de": "in+acc", "verb_en": "walk",  "desc": "walking into a space"},
    {"frame_id": "4b_into_jump",   "sublevel": "4b_goal", "prep_en": "into", "prep_de": "in+acc", "verb_en": "jump",  "desc": "jumping into something — water, box, room"},
    {"frame_id": "4b_into_fall",   "sublevel": "4b_goal", "prep_en": "into", "prep_de": "in+acc", "verb_en": "fall",  "desc": "falling into something"},
    {"frame_id": "4b_into_carry",  "sublevel": "4b_goal", "prep_en": "into", "prep_de": "in+acc", "verb_en": "carry", "desc": "carrying something into a space — in die Küche tragen"},
    {"frame_id": "4b_into_drive",  "sublevel": "4b_goal", "prep_en": "into", "prep_de": "in+acc", "verb_en": "drive", "desc": "driving into a space — garage, town — ins Zentrum fahren"},
    # onto / auf + accusative
    {"frame_id": "4b_onto_climb",  "sublevel": "4b_goal", "prep_en": "onto", "prep_de": "auf+acc", "verb_en": "climb", "desc": "climbing onto a surface — table, roof, wall — auf den Tisch klettern"},
    {"frame_id": "4b_onto_jump",   "sublevel": "4b_goal", "prep_en": "onto", "prep_de": "auf+acc", "verb_en": "jump",  "desc": "jumping onto a surface"},
    {"frame_id": "4b_onto_put",    "sublevel": "4b_goal", "prep_en": "onto", "prep_de": "auf+acc", "verb_en": "put",   "desc": "putting something onto a surface — legen/stellen; ZH: 放到...上面"},
    {"frame_id": "4b_onto_step",   "sublevel": "4b_goal", "prep_en": "onto", "prep_de": "auf+acc", "verb_en": "step",  "desc": "stepping onto something"},
    # toward / auf...zu
    {"frame_id": "4b_toward_walk", "sublevel": "4b_goal", "prep_en": "toward", "prep_de": "auf...zu", "verb_en": "walk", "desc": "walking toward something — DE: auf...zu construction; JP: に向かって; ZH: 朝/向"},
    {"frame_id": "4b_toward_run",  "sublevel": "4b_goal", "prep_en": "toward", "prep_de": "auf...zu", "verb_en": "run",  "desc": "running toward something"},
    {"frame_id": "4b_toward_drive","sublevel": "4b_goal", "prep_en": "toward", "prep_de": "auf...zu", "verb_en": "drive","desc": "driving toward a destination"},
    # to / nach / zu
    {"frame_id": "4b_to_go",       "sublevel": "4b_goal", "prep_en": "to", "prep_de": "nach/zu", "verb_en": "go",   "desc": "going to a place — DE nach for countries/cities (nach Berlin); zu for specific places (zur Schule)"},
    {"frame_id": "4b_to_walk",     "sublevel": "4b_goal", "prep_en": "to", "prep_de": "zu",      "verb_en": "walk", "desc": "walking to a specific place — zum Bahnhof, zur Schule"},
    {"frame_id": "4b_to_drive",    "sublevel": "4b_goal", "prep_en": "to", "prep_de": "nach/zu", "verb_en": "drive","desc": "driving to a destination — show nach vs zu distinction across groups"},
    {"frame_id": "4b_to_fly",      "sublevel": "4b_goal", "prep_en": "to", "prep_de": "nach",    "verb_en": "fly",  "desc": "flying to a city or country — DE always nach for geographic destinations"},

    # ── 4B: movement — SOURCE ─────────────────────────────────────
    {"frame_id": "4b_from_come",   "sublevel": "4b_src", "prep_en": "from",    "prep_de": "von",   "verb_en": "come",  "desc": "coming from a place — von for non-enclosed/person/named place; aus for enclosed space"},
    {"frame_id": "4b_from_return", "sublevel": "4b_src", "prep_en": "from",    "prep_de": "von/aus","verb_en": "return","desc": "returning from somewhere — show von vs aus contrast across groups"},
    {"frame_id": "4b_out_run",     "sublevel": "4b_src", "prep_en": "out of",  "prep_de": "aus",   "verb_en": "run",   "desc": "running out of an enclosed space — DE aus + dative; JP: から; ZH: 从...跑出来"},
    {"frame_id": "4b_out_walk",    "sublevel": "4b_src", "prep_en": "out of",  "prep_de": "aus",   "verb_en": "walk",  "desc": "walking out of a space"},
    {"frame_id": "4b_out_jump",    "sublevel": "4b_src", "prep_en": "out of",  "prep_de": "aus",   "verb_en": "jump",  "desc": "jumping out of something"},
    {"frame_id": "4b_off_fall",    "sublevel": "4b_src", "prep_en": "off",     "prep_de": "von",   "verb_en": "fall",  "desc": "falling off a surface — DE von + dative; JP: から落ちる; ZH: 从...掉下来"},
    {"frame_id": "4b_off_jump",    "sublevel": "4b_src", "prep_en": "off",     "prep_de": "von",   "verb_en": "jump",  "desc": "jumping off something"},
    {"frame_id": "4b_away_run",    "sublevel": "4b_src", "prep_en": "away from","prep_de": "von...weg","verb_en": "run","desc": "running away from something — DE von...weg; JP: から逃げる; ZH: 逃离/跑离"},
    {"frame_id": "4b_away_walk",   "sublevel": "4b_src", "prep_en": "away from","prep_de": "von...weg","verb_en": "walk","desc": "walking away from something"},

    # ── 4B: movement — PATH ───────────────────────────────────────
    {"frame_id": "4b_through_run",  "sublevel": "4b_path", "prep_en": "through", "prep_de": "durch+acc",    "verb_en": "run",   "desc": "running through something — JP: を通って (を marks the traversed path, not the object)"},
    {"frame_id": "4b_through_walk", "sublevel": "4b_path", "prep_en": "through", "prep_de": "durch+acc",    "verb_en": "walk",  "desc": "walking through something — park, tunnel, forest"},
    {"frame_id": "4b_through_drive","sublevel": "4b_path", "prep_en": "through", "prep_de": "durch+acc",    "verb_en": "drive", "desc": "driving through a tunnel or city"},
    {"frame_id": "4b_across_walk",  "sublevel": "4b_path", "prep_en": "across",  "prep_de": "über+acc",     "verb_en": "walk",  "desc": "walking across a bridge or field — JP: を渡って; ZH: 穿过/越过"},
    {"frame_id": "4b_across_swim",  "sublevel": "4b_path", "prep_en": "across",  "prep_de": "über+acc",     "verb_en": "swim",  "desc": "swimming across a body of water"},
    {"frame_id": "4b_across_run",   "sublevel": "4b_path", "prep_en": "across",  "prep_de": "über+acc",     "verb_en": "run",   "desc": "running across a surface or bridge"},
    {"frame_id": "4b_along_walk",   "sublevel": "4b_path", "prep_en": "along",   "prep_de": "entlang+acc",  "verb_en": "walk",  "desc": "walking along a path or river — DE: den Fluss entlang (post-nominal); JP: に沿って; ZH: 沿着"},
    {"frame_id": "4b_along_run",    "sublevel": "4b_path", "prep_en": "along",   "prep_de": "entlang+acc",  "verb_en": "run",   "desc": "running along a road or path"},
    {"frame_id": "4b_around_walk",  "sublevel": "4b_path", "prep_en": "around",  "prep_de": "um...herum",   "verb_en": "walk",  "desc": "walking around something — DE: um+acc+herum; JP: の周りを歩く; ZH: 绕着/绕过"},
    {"frame_id": "4b_around_drive", "sublevel": "4b_path", "prep_en": "around",  "prep_de": "um...herum",   "verb_en": "drive", "desc": "driving around something or along a circular route"},
    {"frame_id": "4b_over_jump",    "sublevel": "4b_path", "prep_en": "over",    "prep_de": "über+acc",     "verb_en": "jump",  "desc": "jumping over something — fence, puddle, wall"},
    {"frame_id": "4b_over_climb",   "sublevel": "4b_path", "prep_en": "over",    "prep_de": "über+acc",     "verb_en": "climb", "desc": "climbing over something"},
    # Japanese を for path — highlight files
    {"frame_id": "4b_jp_wo_bridge", "sublevel": "4b_path", "prep_en": "across",  "prep_de": "über+acc",     "verb_en": "cross", "desc": "JP を marks the traversed space: 橋を渡る — the bridge is the path, not the object; contrast with EN 'cross the bridge'"},
    {"frame_id": "4b_jp_wo_park",   "sublevel": "4b_path", "prep_en": "through", "prep_de": "durch+acc",    "verb_en": "walk",  "desc": "JP を for path: 公園を歩く — walking through or across the park; を marks the traversed space"},

    # ── 4B: contrast pairs (dative vs accusative) ─────────────────
    {"frame_id": "4b_contrast_in",      "sublevel": "4b_contrast", "prep_de": "in",      "desc": "CONTRAST: im Haus (dative=static) ↔ ins Haus laufen (accusative=directional)"},
    {"frame_id": "4b_contrast_auf",     "sublevel": "4b_contrast", "prep_de": "auf",     "desc": "CONTRAST: auf dem Tisch (dative=static) ↔ auf den Tisch springen (accusative=directional)"},
    {"frame_id": "4b_contrast_unter",   "sublevel": "4b_contrast", "prep_de": "unter",   "desc": "CONTRAST: unter dem Bett (dative=static) ↔ unter das Bett kriechen (accusative=directional)"},
    {"frame_id": "4b_contrast_hinter",  "sublevel": "4b_contrast", "prep_de": "hinter",  "desc": "CONTRAST: hinter dem Haus (dative=static) ↔ hinter das Haus laufen (accusative=directional)"},
    {"frame_id": "4b_contrast_vor",     "sublevel": "4b_contrast", "prep_de": "vor",     "desc": "CONTRAST: vor dem Haus (dative=static) ↔ vor das Haus gehen (accusative=directional)"},
    {"frame_id": "4b_contrast_neben",   "sublevel": "4b_contrast", "prep_de": "neben",   "desc": "CONTRAST: neben dem Bett (dative=static) ↔ neben das Bett stellen (accusative=directional)"},
    {"frame_id": "4b_contrast_zwischen","sublevel": "4b_contrast", "prep_de": "zwischen","desc": "CONTRAST: zwischen den Stühlen (dative=static) ↔ zwischen die Stühle schieben (accusative=directional)"},
    {"frame_id": "4b_contrast_über",    "sublevel": "4b_contrast", "prep_de": "über",    "desc": "CONTRAST: über dem Tisch (dative=static) ↔ über den Tisch heben (accusative=directional)"},
    {"frame_id": "4b_contrast_an",      "sublevel": "4b_contrast", "prep_de": "an",      "desc": "CONTRAST: an der Wand (dative=static) ↔ an die Wand lehnen (accusative=directional)"},

    # ── 4C: instrument — tools ────────────────────────────────────
    {"frame_id": "4c_scissors_cut",   "sublevel": "4c_tool",     "instrument": "scissors",   "verb_en": "cut",    "desc": "cutting paper or cloth with scissors — DE: mit der Schere; JP: はさみで; ZH: 用剪刀"},
    {"frame_id": "4c_knife_cut",      "sublevel": "4c_tool",     "instrument": "knife",      "verb_en": "cut",    "desc": "cutting food with a knife — DE: mit einem Messer; JP: ナイフで / 包丁で; ZH: 用刀"},
    {"frame_id": "4c_axe_chop",       "sublevel": "4c_tool",     "instrument": "axe",        "verb_en": "chop",   "desc": "chopping wood with an axe — DE: mit der Axt; JP: 斧で; ZH: 用斧子"},
    {"frame_id": "4c_pen_write",      "sublevel": "4c_tool",     "instrument": "pen",        "verb_en": "write",  "desc": "writing with a pen — DE: mit dem Stift; JP: ペンで; ZH: 用笔"},
    {"frame_id": "4c_pencil_draw",    "sublevel": "4c_tool",     "instrument": "pencil",     "verb_en": "draw",   "desc": "drawing with a pencil — DE: mit dem Bleistift; JP: 鉛筆で; ZH: 用铅笔"},
    {"frame_id": "4c_brush_paint",    "sublevel": "4c_tool",     "instrument": "brush",      "verb_en": "paint",  "desc": "painting with a brush — DE: mit dem Pinsel; JP: 筆で; ZH: 用毛笔/用笔刷; note brush types vary culturally"},
    {"frame_id": "4c_spoon_stir",     "sublevel": "4c_tool",     "instrument": "spoon",      "verb_en": "stir",   "desc": "stirring with a spoon — DE: mit dem Löffel; JP: スプーンで; ZH: 用勺子"},
    {"frame_id": "4c_chopsticks_eat", "sublevel": "4c_tool",     "instrument": "chopsticks", "verb_en": "eat",    "desc": "eating with chopsticks — DE: mit Stäbchen (plural, no article); JP: はしで; ZH: 用筷子"},
    {"frame_id": "4c_fork_eat",       "sublevel": "4c_tool",     "instrument": "fork",       "verb_en": "eat",    "desc": "eating with a fork — contrast with chopsticks file"},
    {"frame_id": "4c_hammer_hit",     "sublevel": "4c_tool",     "instrument": "hammer",     "verb_en": "hit",    "desc": "hitting a nail with a hammer — DE: mit dem Hammer; JP: ハンマーで; ZH: 用锤子"},
    {"frame_id": "4c_saw_cut",        "sublevel": "4c_tool",     "instrument": "saw",        "verb_en": "saw",    "desc": "sawing wood with a saw — DE: mit der Säge; JP: のこぎりで; ZH: 用锯子"},
    {"frame_id": "4c_shovel_dig",     "sublevel": "4c_tool",     "instrument": "shovel",     "verb_en": "dig",    "desc": "digging with a shovel — DE: mit dem Spaten; JP: シャベルで; ZH: 用铲子"},
    {"frame_id": "4c_ruler_measure",  "sublevel": "4c_tool",     "instrument": "ruler",      "verb_en": "measure","desc": "measuring with a ruler — DE: mit dem Lineal; JP: 定規で; ZH: 用尺子"},
    # 4C: body part instruments
    {"frame_id": "4c_hand_push",      "sublevel": "4c_body",     "instrument": "hand",       "verb_en": "push",   "desc": "pushing with the hand — DE: mit der Hand; JP: 手で; ZH: 用手"},
    {"frame_id": "4c_hand_write",     "sublevel": "4c_body",     "instrument": "hand",       "verb_en": "write",  "desc": "writing by hand — DE: mit der Hand schreiben; JP: 手で書く; ZH: 用手写"},
    {"frame_id": "4c_hand_carry",     "sublevel": "4c_body",     "instrument": "hand",       "verb_en": "carry",  "desc": "carrying in the hands — DE: mit den Händen tragen; JP: 手で運ぶ; ZH: 用手拿"},
    {"frame_id": "4c_foot_kick",      "sublevel": "4c_body",     "instrument": "foot",       "verb_en": "kick",   "desc": "kicking with the foot — DE: mit dem Fuß; JP: 足で蹴る; ZH: 用脚踢"},
    {"frame_id": "4c_eye_see",        "sublevel": "4c_body",     "instrument": "eyes",       "verb_en": "see",    "desc": "seeing with the eyes — DE: mit den Augen; JP: 目で見る; ZH: 用眼睛看"},
    {"frame_id": "4c_ear_hear",       "sublevel": "4c_body",     "instrument": "ears",       "verb_en": "hear",   "desc": "hearing with the ears — DE: mit den Ohren; JP: 耳で聞く; ZH: 用耳朵听"},
    # 4C: vehicle / means of transport
    {"frame_id": "4c_train_travel",   "sublevel": "4c_vehicle",  "instrument": "train",      "verb_en": "travel", "desc": "travelling by train — DE: mit dem Zug; JP: 電車で; ZH: 坐火车 (sit-train, NOT 用)"},
    {"frame_id": "4c_bike_ride",      "sublevel": "4c_vehicle",  "instrument": "bicycle",    "verb_en": "ride",   "desc": "going by bicycle — DE: mit dem Fahrrad; JP: 自転車で; ZH: 骑自行车 (ride-bicycle, NOT 用)"},
    {"frame_id": "4c_car_go",         "sublevel": "4c_vehicle",  "instrument": "car",        "verb_en": "go",     "desc": "going by car — DE: mit dem Auto; JP: 車で; ZH: 坐车 (passenger) / 开车 (driver); show both"},
    {"frame_id": "4c_plane_fly",      "sublevel": "4c_vehicle",  "instrument": "airplane",   "verb_en": "fly",    "desc": "flying by plane — DE: mit dem Flugzeug; JP: 飛行機で; ZH: 坐飞机 (NOT 用飞机)"},
    {"frame_id": "4c_foot_go",        "sublevel": "4c_vehicle",  "instrument": "foot",       "verb_en": "go",     "desc": "going on foot — DE: zu Fuß (idiomatic, NOT mit dem Fuß); JP: 歩いて / 徒歩で; ZH: 走路 / 步行"},
    # 4C: comitative vs instrumental contrast
    {"frame_id": "4c_contrast_comi",  "sublevel": "4c_contrast", "instrument": "person/tool","verb_en": "walk/write","desc": "JP と (comitative=with a person) vs で (instrumental=with a tool): 友達と歩く vs ペンで書く — EN/DE 'with' is ambiguous; JP は is not"},
    {"frame_id": "4c_contrast_vehicle","sublevel":"4c_contrast", "instrument": "vehicle",    "verb_en": "go",     "desc": "ZH vehicle construction: 坐/骑/开 vs 用 — Mandarin uses specific motion verbs for vehicles, never 用; contrast with EN 'by' and DE 'mit'"},
]


# ─────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────

GLOBAL_RULES = """\
## Global rules

Naturalise, don't translate.
  The goal is the same meaning expressed as a native speaker would say it.
  Surface form may differ across languages.

Japanese plain form. No desu/masu. No keigo.
  Past: ta form. Ongoing: te-iru. Future: darou / to omou.
  CRITICAL: Japanese MUST be written in Japanese script (kanji + hiragana + katakana). Never romaji.

German V2 word order. Verb is always the second constituent.
  Use sein (not haben) in Perfekt for intransitive motion verbs:
    ist gelaufen, ist gesprungen, ist gefallen, ist geklettert, ist gefahren, ist geschwommen.
  Use haben for caused motion / placement:
    hat gelegt, hat gestellt, hat gehängt, hat geworfen, hat geschoben.

German dative articles: dem (masc/neut), der (fem), den (pl).
German accusative articles: den (masc), die (fem), das (neut), die (pl).
Contractions: in+dem=im, an+dem=am, in+das=ins, an+das=ans, zu+dem=zum, zu+der=zur.

Mandarin aspect: 了 completed, 在 ongoing, 会 future.
Pronoun drop: Japanese and Mandarin omit pronouns when referent is clear.

Cross-linguistic differences are features, not problems. Surface them clearly.
Do not explain grammar inside generated files."""


RULES_4A = """\
## 4A — Static location rules

German: always dative with Wechselpräpositionen.
Japanese: NP の LOCALIZER に + いる (animate) / ある (inanimate).
  いる/ある distinction is OBLIGATORY — animate subjects always take いる.
  Exception: で replaces に when the verb is an activity verb (working, studying, eating, playing).
  で marks the location of an activity; に marks existence.
Mandarin: 在 + place NP + localizer word (下面, 上面, 里面, 旁边, 后面, 前面, 中间).

Vary positional verbs across groups: lie, sit, stand, hang, wait, hide, sleep, live, work.
Show animate and inanimate subjects in separate groups where the frame description calls for it."""


RULES_4B_GOAL = """\
## 4B goal — Directed movement (toward/into destination) rules

German: Wechselpräpositionen take ACCUSATIVE for direction. This is the core contrast with 4A.
  Example: im Haus (dative=static) → ins Haus laufen (accusative=directional).
  nach + dative: geographic destinations (cities, countries, named places without article).
  zu + dative: specific locations with article (zum Bahnhof, zur Schule, zur Arbeit).
  auf...zu: movement toward something (auf ihn zu laufen — running toward him).

Japanese: に or へ marks the goal. Motion is in the verb.
  ZH directional complements attach to the motion verb: 跑进 (run-enter), 走进 (walk-enter),
  爬上 (climb-up), 跳上 (jump-onto), 放到...上面 (put onto).

Use motion verbs with sein in German Perfekt: ist gelaufen, ist gesprungen, ist gefahren."""


RULES_4B_SRC = """\
## 4B source — Movement away from origin rules

German: von + dative for open/non-enclosed sources; aus + dative for enclosed spaces (rooms, buildings).
  von der Schule kommen (from school) vs aus dem Haus laufen (out of the house).
  von...weg / weg von: away from something.

Japanese: から marks the source or origin in all cases.
Mandarin: 从 + source + come/leave construction; 离开 (leave); directional complements 出来/出去 for exiting."""


RULES_4B_PATH = """\
## 4B path — Movement through / across / along / around / over rules

German:
  durch + accusative: through an enclosed or bounded space (durch den Tunnel, durch den Park).
  über + accusative: across or over (über die Brücke, über den Zaun springen).
  entlang + accusative (post-nominal): along (den Fluss entlang, die Straße entlang).
  um + accusative + herum: around (um das Haus herum, um den See herum).

Japanese: を marks the traversed space — this is CRITICAL and must appear in path files.
  橋を渡る (cross the bridge — を marks the bridge as traversed space, not direct object).
  公園を歩く (walk through the park).
  トンネルを通る (go through the tunnel).
  に沿って: along (川に沿って — along the river).
  の周りを: around (木の周りを — around the tree).

Mandarin:
  穿过: through/across (穿过公园, 穿过隧道).
  沿着: along (沿着河边走).
  绕过 / 绕着: around (绕过树).
  越过: over/across (越过山, 越过围墙).

Use sein in German Perfekt for all path motion verbs."""


RULES_4B_CONTRAST = """\
## 4B contrast pair rules — DATIVE vs ACCUSATIVE

Each file covers ONE German Wechselpräposition and shows BOTH:
  - Static location (dative): the subject is at rest at a location
  - Directed movement (accusative): the subject moves to a location

Groups must ALTERNATE: static group, then directional group, then static, then directional.
Produce 4–6 groups total (2–3 static, 2–3 directional, alternating).

Within each pair:
  - Use the same or related noun in both groups to make the case contrast visible.
  - The German sentence should change only the article form (dem/der → den/die/das).
  - Japanese and Mandarin do not change particle/structure for this contrast — show this.

Example contrast for "in":
  Static:     Die Katze liegt im Haus.       / 猫は家の中にいる。/ 猫在房子里。
  Directional: Die Katze läuft ins Haus.     / 猫が家の中に走って入った。/ 猫跑进了房子。"""


RULES_4C_TOOL = """\
## 4C tool instrument rules

German: mit + dative article + tool noun.
  mit der Schere (fem), mit einem Messer (masc), mit dem Hammer (masc), mit den Händen (pl).
  German mit is ambiguous (instrument and comitative both use mit).

Japanese: tool + で + verb. で is EXCLUSIVELY instrument — comitative is と.
  はさみで切る (cut with scissors). 友達と行く (go with a friend). These particles do not overlap.

Mandarin: 用 + tool + verb (+ object).
  用剪刀剪纸 (use-scissors cut-paper). 用笔写字 (use-pen write-character).
  Chopsticks: 用筷子吃饭. Fork: 用叉子吃饭. Stäbchen in German is plural, no article needed.

Vary tense (past, present, future) and subject across groups."""


RULES_4C_BODY = """\
## 4C body-part instrument rules

Same pattern as tools: body part acts as instrument.
German: mit + dative: mit der Hand, mit den Augen, mit den Ohren.
  Special idiom: zu Fuß gehen (go on foot) — NOT mit dem Fuß.
Japanese: body part + で: 手で, 足で, 目で, 耳で.
Mandarin: 用 + body part: 用手, 用脚, 用眼睛, 用耳朵.

Vary subjects and objects across groups."""


RULES_4C_VEHICLE = """\
## 4C vehicle / means of transport rules

This is the most important cross-linguistic contrast in 4C.

German: mit + dative vehicle: mit dem Zug, mit dem Fahrrad, mit dem Auto, mit dem Flugzeug.
Japanese: vehicle + で: 電車で, 自転車で, 車で, 飛行機で. Same particle as instruments.
Mandarin: SPECIFIC MOTION VERBS — never 用 for vehicles:
  坐 (sit-in): 坐火车, 坐汽车, 坐飞机, 坐船.
  骑 (ride/straddle): 骑自行车, 骑摩托车.
  开 (drive/operate): 开车 (driving a car), 开船 (sailing a boat).
  On foot: 走路 / 步行 — no motion verb prefix needed.

German "on foot": zu Fuß (NOT mit dem Fuß). This is idiomatic.

Show the ZH verb choice explicitly — it varies by vehicle type and role (passenger vs driver)."""


RULES_4C_CONTRAST = """\
## 4C contrast rules

Comitative vs instrumental:
  Japanese: と (comitative, with a person) vs で (instrumental, with a tool) — distinguish clearly.
  Show sentences where EN 'with' covers both, then JP where the particles split.
  Example groups: walk with a friend (友達と) / write with a pen (ペンで).

Vehicle contrast:
  Show ZH vehicle verbs vs EN 'by' and DE 'mit'. Make the structural difference visible.
  Include passenger vs driver perspective in different groups (ZH 坐 vs 开 distinction)."""


SUBLEVEL_RULES: dict[str, str] = {
    "4a":          RULES_4A,
    "4b_goal":     RULES_4B_GOAL,
    "4b_src":      RULES_4B_SRC,
    "4b_path":     RULES_4B_PATH,
    "4b_contrast": RULES_4B_CONTRAST,
    "4c_tool":     RULES_4C_TOOL,
    "4c_body":     RULES_4C_BODY,
    "4c_vehicle":  RULES_4C_VEHICLE,
    "4c_contrast": RULES_4C_CONTRAST,
}


GEN_PROMPT_TPL = """\
Generate Level-4 multilingual language corpus files.
Each file covers one grammatical frame and shows the same meaning naturally expressed
in English, German, Japanese (Japanese script only — kanji/hiragana/katakana, NO romaji), and Mandarin.

{global_rules}

{sublevel_rules}

## Output format

Each file: 3–5 groups separated by blank lines (4–6 for contrast pair files).
Each group: exactly 4 lines in order — English / German / Japanese / Mandarin.
Vary subject, tense, and reference nouns across groups within a file.
No headers. No labels. No grammar commentary inside files.

## Frames to generate

{frames}

Return JSON only — no commentary, no markdown fences:
{{"files": [{{"frame_id": "...", "groups": [["EN", "DE", "JP", "ZH"], ...]}}]}}"""


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    with _lock:
        print(msg, flush=True)


def load_api_key() -> str:
    for var in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        if key := os.environ.get(var):
            return key
    return ""


def pending_jobs() -> list[dict]:
    seen: set[str] = set()
    result = []
    for job in JOBS:
        fid = job["frame_id"]
        if fid in seen:
            continue
        seen.add(fid)
        if not (OUT_DIR / f"{fid}.md").exists():
            result.append(job)
    return result


def group_by_sublevel(jobs: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for job in jobs:
        sl = job["sublevel"]
        groups.setdefault(sl, []).append(job)
    return groups


# ─────────────────────────────────────────────────────────────────
# Gen
# ─────────────────────────────────────────────────────────────────

def _parse_response(raw: str) -> dict | None:
    if raw.startswith("```"):
        raw = re.sub(r"^```[^\n]*\n", "", raw)
        raw = re.sub(r"\n?```$", "", raw.strip())
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return None


def frame_text(job: dict) -> str:
    lines = [f"frame_id: {job['frame_id']}", f"sublevel: {job['sublevel']}", f"desc: {job['desc']}"]
    for key in ("prep_en", "prep_de", "case_de", "verb_en", "instrument"):
        if key in job:
            lines.append(f"{key}: {job[key]}")
    return "\n".join(lines)


def gen_batch(
    jobs: list[dict],
    sublevel: str,
    client: OpenAI,
    dry_run: bool,
) -> tuple[list[str], list[str]]:
    if dry_run:
        log(f"  [DRY-RUN] gen: {[j['frame_id'] for j in jobs]}")
        return [j["frame_id"] for j in jobs], []

    frames_text = "\n\n".join(frame_text(j) for j in jobs)
    rules = SUBLEVEL_RULES.get(sublevel, "")

    prompt = GEN_PROMPT_TPL.format(
        global_rules=GLOBAL_RULES,
        sublevel_rules=rules,
        frames=frames_text,
    )

    for attempt in (1, 2):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=32768,
            )
        except Exception as e:
            log(f"  GEN API ERROR (attempt {attempt}) {jobs[0]['frame_id']}…: {e}")
            if attempt == 2:
                return [], [j["frame_id"] for j in jobs]
            continue

        raw = (resp.choices[0].message.content or "").strip()
        tokens_in  = resp.usage.prompt_tokens     if resp.usage else "?"
        tokens_out = resp.usage.completion_tokens if resp.usage else "?"

        data = _parse_response(raw)
        if data is None:
            log(f"  PARSE FAIL (attempt {attempt}) {jobs[0]['frame_id']}… raw:\n{raw[:200]}")
            if attempt == 2:
                return [], [j["frame_id"] for j in jobs]
            continue

        written, failed = [], []
        min_groups = 4 if sublevel == "4b_contrast" else 3
        max_groups = 7 if sublevel == "4b_contrast" else 6

        for file_data in data.get("files", []):
            fid    = file_data.get("frame_id", "").strip()
            groups = file_data.get("groups", [])

            if not fid:
                continue

            if not (min_groups <= len(groups) <= max_groups):
                log(f"  SKIP {fid}: expected {min_groups}–{max_groups} groups, got {len(groups)}")
                failed.append(fid)
                continue

            bad = False
            for g in groups:
                if len(g) != 4 or not all(isinstance(s, str) and s.strip() for s in g):
                    log(f"  SKIP {fid}: malformed group")
                    bad = True
                    break
            if bad:
                failed.append(fid)
                continue

            content = "\n\n".join("\n".join(g) for g in groups) + "\n"
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            (OUT_DIR / f"{fid}.md").write_text(content, encoding="utf-8")
            log(f"  OK {fid} ({tokens_in}→{tokens_out})")
            written.append(fid)

        returned = {f.get("frame_id", "") for f in data.get("files", [])}
        for job in jobs:
            fid = job["frame_id"]
            if fid not in returned and fid not in written and fid not in failed:
                log(f"  MISSING from response: {fid}")
                failed.append(fid)

        return written, failed

    return [], [j["frame_id"] for j in jobs]


def run_gen(args: argparse.Namespace, client: OpenAI) -> None:
    pending = pending_jobs()

    if args.limit:
        pending = pending[: args.limit]

    total = len(pending)
    if total == 0:
        print("Nothing to generate — all frames already exist.")
        return

    print(f"Pending: {total} frames")

    by_sublevel = group_by_sublevel(pending)
    batches: list[tuple[list[dict], str]] = []
    for sublevel, jobs in by_sublevel.items():
        for i in range(0, len(jobs), args.batch):
            batches.append((jobs[i : i + args.batch], sublevel))

    print(f"Batches: {len(batches)}  (batch size: {args.batch})")

    all_failed: list[str] = []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(gen_batch, b, sl, client, args.dry_run): (b, sl) for b, sl in batches}
        for fut in as_completed(futs):
            _, failed = fut.result()
            all_failed.extend(failed)

    done = total - len(all_failed)
    print(f"\nDone: {done}/{total} written. Failed: {len(all_failed)}")
    if all_failed:
        print("Failed:", sorted(all_failed)[:20])


# ─────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────

def run_report() -> None:
    total = len(JOBS)
    done  = sum(1 for j in JOBS if (OUT_DIR / f"{j['frame_id']}.md").exists())

    print(f"Total frames: {total}")
    print(f"Generated:    {done}")
    print(f"Remaining:    {total - done}")

    by_sl: dict[str, list[int]] = {}
    for job in JOBS:
        sl = job["sublevel"]
        if sl not in by_sl:
            by_sl[sl] = [0, 0]
        by_sl[sl][1] += 1
        if (OUT_DIR / f"{job['frame_id']}.md").exists():
            by_sl[sl][0] += 1

    print()
    print("By sub-level:")
    for sl, (d, n) in sorted(by_sl.items()):
        bar = "#" * d + "." * (n - d)
        print(f"  {sl:<20} {d:>3}/{n:<3}  {bar}")


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Lang-4 corpus generator")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_gen = sub.add_parser("gen", help="Generate files for all pending frames")
    p_gen.add_argument("--workers", type=int, default=4)
    p_gen.add_argument("--batch",   type=int, default=5,
                       help="Frames per API call (default 5)")
    p_gen.add_argument("--limit",   type=int, default=0,
                       help="Max frames to generate this run (0=all pending)")
    p_gen.add_argument("--dry-run", action="store_true")

    sub.add_parser("report", help="Show progress summary")

    args = parser.parse_args()

    if args.cmd == "report":
        run_report()
        return

    api_key = load_api_key()
    if not api_key:
        print("ERROR: set OPENROUTER_API_KEY or OPENAI_API_KEY", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=BASE_URL)
    run_gen(args, client)


if __name__ == "__main__":
    main()
