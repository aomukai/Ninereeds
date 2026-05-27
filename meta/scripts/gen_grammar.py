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
        ("book", "mit dem Buch", "で", "read with the book, learn with the book", "book"),
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


def make_bei_audit_specs() -> list[FileSpec]:
    """Initial audit batch for `bei` as static nearby relation / at a person's place."""
    rows: list[tuple[str, str, tuple[str, ...], str]] = [
        ("101_bei_tree_static.md", "bei as nearby relation by a tree", ("by", "bei dem Baum", "tree"), "Use bei dem Baum. Japanese cue: 木のそばに. Chinese cue: 在樹旁邊. Keep the relation static and nearby, not inside or moving into. Use only static actions: is, sits, stands. Prefer questions like Where is X? or Where does X sit/stand?"),
        ("102_bei_house_static.md", "bei as nearby relation by a house", ("by", "bei dem Haus", "house"), "Use bei dem Haus. Japanese cue: 家のそばに. Chinese cue: 在房子旁邊. Keep the relation static and nearby, not inside or moving into. Use only static actions: is, sits, stands. Prefer questions like Where is X? or Where does X sit/stand?"),
        ("103_bei_school_static.md", "bei as nearby relation by a school", ("by", "bei der Schule", "school"), "Use bei der Schule. Japanese cue: 学校のそばに. Chinese cue: 在學校旁邊. Keep the relation static and nearby, not inside or moving into. Use only static actions: is, sits, stands. Prefer questions like Where is X? or Where does X sit/stand?"),
        ("104_bei_market_static.md", "bei as nearby relation by a market", ("by", "bei dem Markt", "market"), "Use bei dem Markt. Japanese cue: 市場のそばに. Chinese cue: 在市場旁邊. Keep the relation static and nearby, not inside or moving into. Use only static actions: is, sits, stands. Prefer questions like Where is X? or Where does X sit/stand?"),
        ("105_bei_park_static.md", "bei as nearby relation by a park", ("by", "bei dem Park", "park"), "Use bei dem Park. Japanese cue: 公園のそばに. Chinese cue: 在公園旁邊. Keep the relation static and nearby, not inside or moving into. Use only static actions: is, sits, stands. Prefer questions like Where is X? or Where does X sit/stand?"),
        ("106_bei_door_static.md", "bei as nearby relation by a door", ("by", "bei der Tür", "door"), "Use bei der Tür. Japanese cue: ドアのそばに. Chinese cue: 在門旁邊. Keep the relation static and nearby, not inside or moving into. Use only static actions: is, sits, stands. Prefer questions like Where is X? or Where does X sit/stand?"),
        ("107_bei_window_static.md", "bei as nearby relation by a window", ("by", "bei dem Fenster", "window"), "Use bei dem Fenster. Japanese cue: 窓のそばに. Chinese cue: 在窗邊. Keep the relation static and nearby, not inside or moving into. Use only static actions: is, sits, stands. Prefer questions like Where is X? or Where does X sit/stand?"),
        ("108_bei_bench_static.md", "bei as nearby relation by a bench", ("by", "bei der Bank", "bench"), "Use bei der Bank. Japanese cue: ベンチのそばに. Chinese cue: 在長椅旁邊. Keep the relation static and nearby, not inside or moving into. Use only static actions: is, sits, stands. Prefer questions like Where is X? or Where does X sit/stand?"),
        ("109_bei_doctor_place.md", "bei as at a person's place with a doctor", ("with", "bei dem Arzt", "doctor"), "Use bei dem Arzt. Japanese cue: 医者のところにいる / 医者のところで待つ. Chinese cue: 在醫生那裡. Keep the relation static or appointment-like, not movement to the doctor. English may say with the doctor or at the doctor's. Use only actions: is, waits, sits. For Japanese, use ところにいる for simple being and ところで for waiting or sitting."),
        ("110_bei_teacher_place.md", "bei as at a person's place with a teacher", ("with", "bei dem Lehrer", "teacher"), "Use bei dem Lehrer. Japanese cue: 先生のところにいる / 先生のところで勉強する. Chinese cue: 在老師那裡. Keep the relation static or appointment-like, not movement to the teacher. English may say with the teacher or at the teacher's place. Use only actions: is, waits, sits, studies. For Japanese, use ところにいる for simple being and ところで for waiting, sitting, or studying."),
    ]

    static_anchors = [
        ("tree", "bei dem Baum", "木のそばに", "在樹旁邊"),
        ("house", "bei dem Haus", "家のそばに", "在房子旁邊"),
        ("school", "bei der Schule", "学校のそばに", "在學校旁邊"),
        ("market", "bei dem Markt", "市場のそばに", "在市場旁邊"),
        ("park", "bei dem Park", "公園のそばに", "在公園旁邊"),
        ("door", "bei der Tür", "ドアのそばに", "在門旁邊"),
        ("window", "bei dem Fenster", "窓のそばに", "在窗邊"),
        ("bench", "bei der Bank", "ベンチのそばに", "在長椅旁邊"),
    ]
    person_places = [
        ("doctor", "bei dem Arzt", "医者のところ", "在醫生那裡"),
        ("teacher", "bei dem Lehrer", "先生のところ", "在老師那裡"),
    ]

    next_id = 111
    while next_id <= 200:
        kind = (next_id - 111) % 3
        if kind in (0, 1):
            noun, dative, jp_cue, zh_cue = static_anchors[((next_id - 111) // 2) % len(static_anchors)]
            filename = f"{next_id:03d}_bei_{noun}_static.md"
            rows.append((
                filename,
                f"bei as static nearby relation by a {noun}",
                ("by", dative, noun),
                f"Use {dative}. Japanese cue: {jp_cue}. Chinese cue: {zh_cue}. Keep the relation static and nearby, not inside or moving into. Use only static actions: is, sits, stands. Prefer simple location questions and answers.",
            ))
        else:
            noun, dative, jp_cue, zh_cue = person_places[((next_id - 113) // 3) % len(person_places)]
            filename = f"{next_id:03d}_bei_{noun}_place.md"
            rows.append((
                filename,
                f"bei as at a person's place with a {noun}",
                ("with", dative, noun),
                f"Use {dative}. Japanese cue: {jp_cue}. Chinese cue: {zh_cue}. Keep the relation static or appointment-like, not movement to the {noun}. English may say with the {noun} or at the {noun}'s place. Use only actions: is, waits, sits, studies if the noun is teacher. For Japanese, use ところにいる for simple being and ところで for waiting, sitting, or studying.",
            ))
        next_id += 1

    return [
        FileSpec(
            path=f"01_means_dative_anchor/{filename}",
            focus=focus,
            required_terms=required,
            notes=notes + " Keep German dative form visible in every response. Use full forms such as bei dem / bei der, not contractions such as beim. Prefer common nouns such as the boy, the woman, the child, the man. Avoid character names in this audit batch.",
        )
        for filename, focus, required, notes in rows
    ]


def make_aus_audit_specs() -> list[FileSpec]:
    """Initial audit batch for `aus` as source from inside / out of."""
    rows: list[tuple[str, str, tuple[str, ...], str]] = [
        ("201_aus_house_source.md", "aus as source out of a house", ("out of", "aus dem Haus", "house"), "Use aus dem Haus. Japanese cue: 家から. Chinese cue: 從房子裡. Keep the relation as source from inside, not nearby and not destination. Use simple movement-out patterns such as comes out of or walks out of."),
        ("202_aus_kitchen_source.md", "aus as source out of a kitchen", ("out of", "aus der Küche", "kitchen"), "Use aus der Küche. Japanese cue: 台所から. Chinese cue: 從廚房裡. Keep the relation as source from inside, not nearby and not destination. Use simple movement-out patterns such as comes out of or walks out of."),
        ("203_aus_room_source.md", "aus as source out of a room", ("out of", "aus dem Zimmer", "room"), "Use aus dem Zimmer. Japanese cue: 部屋から. Chinese cue: 從房間裡. Keep the relation as source from inside, not nearby and not destination. Use simple movement-out patterns such as comes out of or walks out of."),
        ("204_aus_garden_source.md", "aus as source out of a garden", ("out of", "aus dem Garten", "garden"), "Use aus dem Garten. Japanese cue: 庭から. Chinese cue: 從花園裡. Keep the relation as source from inside, not nearby and not destination. Use simple movement-out patterns such as comes out of or runs out of."),
        ("205_aus_school_source.md", "aus as source out of a school", ("out of", "aus der Schule", "school"), "Use aus der Schule. Japanese cue: 学校から. Chinese cue: 從學校裡. Keep the relation as source from inside, not nearby and not destination. Use simple movement-out patterns such as comes out of or walks out of."),
        ("206_aus_box_source.md", "aus as source out of a box", ("out of", "aus der Kiste", "box"), "Use aus der Kiste. Japanese cue: 箱から. Chinese cue: 從箱子裡. Keep the relation as source from inside. Use only concrete object-movement patterns such as comes out of the box or takes the apple out of the box. Allowed target nouns: apple, ball, book."),
        ("207_aus_bag_source.md", "aus as source out of a bag", ("out of", "aus der Tasche", "bag"), "Use aus der Tasche. Japanese cue: かばんから. Chinese cue: 從袋子裡. Keep the relation as source from inside. Use only concrete object-movement patterns such as comes out of the bag or takes the book out of the bag. Allowed target nouns: apple, book, pencil."),
        ("208_aus_bucket_source.md", "aus as source out of a bucket", ("out of", "aus dem Eimer", "bucket"), "Use aus dem Eimer. Japanese cue: バケツから. Chinese cue: 從水桶裡. Keep the relation as source from inside. Use only concrete object-movement patterns such as comes out of the bucket or takes the ball out of the bucket. Allowed target nouns: apple, ball, book."),
        ("209_aus_window_source.md", "aus as source out of a window", ("out of", "aus dem Fenster", "window"), "Use aus dem Fenster. Japanese cue: 窓から. Chinese cue: 從窗戶裡. Keep the relation as source from inside/out through an opening, not nearby and not destination. Use only movement-out patterns such as comes out of or climbs out of. For Japanese climbing-out lines, prefer 窓からよじ出る rather than 窓からよじ登る. Do not use look-out-of patterns in this audit batch."),
        ("210_aus_door_source.md", "aus as source out of a door", ("out of", "aus der Tür", "door"), "Use aus der Tür. Japanese cue: ドアから. Chinese cue: 從門裡. Keep the relation as source out through an opening, not nearby and not destination. Use simple movement-out patterns such as comes out of or walks out of."),
    ]

    people_sources = [
        ("house", "aus dem Haus", "家から", "從房子裡", "comes out of, walks out of, runs out of"),
        ("kitchen", "aus der Küche", "台所から", "從廚房裡", "comes out of, walks out of, runs out of"),
        ("room", "aus dem Zimmer", "部屋から", "從房間裡", "comes out of, walks out of, runs out of"),
        ("garden", "aus dem Garten", "庭から", "從花園裡", "comes out of, runs out of"),
        ("school", "aus der Schule", "学校から", "從學校裡", "comes out of, walks out of"),
        ("window", "aus dem Fenster", "窓から", "從窗戶裡", "comes out of, climbs out of"),
        ("door", "aus der Tür", "ドアから", "從門裡", "comes out of, walks out of"),
    ]
    object_sources = [
        ("box", "aus der Kiste", "箱から", "從箱子裡", "apple, ball, book"),
        ("bag", "aus der Tasche", "かばんから", "從袋子裡", "apple, book, pencil"),
        ("bucket", "aus dem Eimer", "バケツから", "從水桶裡", "apple, ball, book"),
    ]

    next_id = 211
    while next_id <= 300:
        kind = (next_id - 211) % 3
        if kind in (0, 1):
            noun, dative, jp_cue, zh_cue, actions = people_sources[((next_id - 211) // 2) % len(people_sources)]
            filename = f"{next_id:03d}_aus_{noun}_source.md"
            rows.append((
                filename,
                f"aus as source out of a {noun}",
                ("out of", dative, noun),
                f"Use {dative}. Japanese cue: {jp_cue}. Chinese cue: {zh_cue}. Keep the relation as source from inside or out through an opening, not nearby and not destination. Use only movement-out patterns: {actions}. Do not switch into nearby, destination, or ownership meaning.",
            ))
        else:
            noun, dative, jp_cue, zh_cue, targets = object_sources[((next_id - 213) // 3) % len(object_sources)]
            filename = f"{next_id:03d}_aus_{noun}_source.md"
            rows.append((
                filename,
                f"aus as source out of a {noun}",
                ("out of", dative, noun),
                f"Use {dative}. Japanese cue: {jp_cue}. Chinese cue: {zh_cue}. Keep the relation as source from inside. Use only concrete take-out patterns such as takes the apple out of the {noun}. Allowed target nouns: {targets}. Do not add any other target nouns.",
            ))
        next_id += 1

    return [
        FileSpec(
            path=f"01_means_dative_anchor/{filename}",
            focus=focus,
            required_terms=required,
            notes=notes + " Keep German dative form visible in every response. Use full forms such as aus dem / aus der. Prefer common nouns such as the boy, the woman, the child, the man. Avoid character names in this audit batch.",
        )
        for filename, focus, required, notes in rows
    ]


def make_von_audit_specs() -> list[FileSpec]:
    """Initial audit batch for `von` as source from a surface or place of departure."""
    rows: list[tuple[str, str, tuple[str, ...], str]] = [
        ("301_von_table_surface.md", "von as source from a table surface", ("from", "von dem Tisch", "table"), "Use von dem Tisch. Japanese cue: テーブルから. Chinese cue: 從桌子上. Keep the relation as source off a surface, not inside a container and not destination. Use movement-off patterns such as falls from or is taken from. Do not use aus dem Tisch."),
        ("302_von_bench_surface.md", "von as source from a bench surface", ("from", "von der Bank", "bench"), "Use von der Bank. Japanese cue: ベンチから. Chinese cue: 從長椅上. Keep the relation as source off a surface, not inside a container and not destination. Use movement-off patterns such as falls from or is taken from. Do not use aus der Bank."),
        ("303_von_tree_surface.md", "von as source from a tree", ("from", "von dem Baum", "tree"), "Use von dem Baum. Japanese cue: 木から. Chinese cue: 從樹上. Keep the relation as source from above or off the tree, not inside and not destination. Use movement-off patterns such as falls from or jumps from. Do not use aus dem Baum."),
        ("304_von_school_source.md", "von as departure from school as place of origin", ("from", "von der Schule", "school"), "Use von der Schule. Japanese cue: 学校から. Chinese cue: 從學校. Keep the relation as departure from a place of origin, not inside a container and not destination. Use simple departure or return patterns such as comes from or walks from. Do not use aus der Schule."),
        ("305_von_market_source.md", "von as departure from the market as place of origin", ("from", "von dem Markt", "market"), "Use von dem Markt. Japanese cue: 市場から. Chinese cue: 從市場. Keep the relation as departure from a place of origin, not inside and not destination. Use simple departure or return patterns such as comes from or returns from. Do not use aus dem Markt."),
        ("306_von_park_source.md", "von as departure from the park as place of origin", ("from", "von dem Park", "park"), "Use von dem Park. Japanese cue: 公園から. Chinese cue: 從公園. Keep the relation as departure from a place of origin, not inside and not destination. Use simple departure or return patterns such as comes from or walks from. Do not use aus dem Park."),
        ("307_von_house_source.md", "von as departure from the house as place of origin", ("from", "von dem Haus", "house"), "Use von dem Haus. Japanese cue: 家から. Chinese cue: 從房子. Keep the relation as departure from a place, not exiting from inside a container. Do not use aus dem Haus. Use simple departure patterns such as leaves from or walks from."),
        ("308_von_garden_source.md", "von as departure from the garden as place of origin", ("from", "von dem Garten", "garden"), "Use von dem Garten. Japanese cue: 庭から. Chinese cue: 從花園. Keep the relation as departure from a place, not exiting from inside a container. Do not use aus dem Garten. Use simple departure or return patterns such as comes from or returns from."),
        ("309_von_doctor_source.md", "von as departure from the doctor as person origin", ("from", "von dem Arzt", "doctor"), "Use von dem Arzt. Japanese cue: 医者のところから. Chinese cue: 從醫生那裡. Keep the relation as departure from a person's place, not being nearby and not destination. Use simple departure patterns such as comes from or returns from the doctor's."),
        ("310_von_teacher_source.md", "von as departure from the teacher as person origin", ("from", "von dem Lehrer", "teacher"), "Use von dem Lehrer. Japanese cue: 先生のところから. Chinese cue: 從老師那裡. Keep the relation as departure from a person's place, not being nearby and not destination. Use simple departure patterns such as comes from or returns from the teacher's."),
    ]

    surface_sources = [
        ("table", "von dem Tisch", "テーブルから", "從桌子上", "falls from, rolls from, is taken from"),
        ("bench", "von der Bank", "ベンチから", "從長椅上", "falls from, is taken from, jumps from"),
        ("tree", "von dem Baum", "木から", "從樹上", "falls from, jumps from, drops from"),
        ("chair", "von dem Stuhl", "椅子から", "從椅子上", "falls from, is taken from, slides from"),
        ("floor", "von dem Boden", "床から", "從地板上", "is taken from, picks up from, lifts from"),
    ]
    place_and_person_sources = [
        ("school", "von der Schule", "学校から", "從學校", "comes from, walks from, returns from"),
        ("market", "von dem Markt", "市場から", "從市場", "comes from, returns from, walks from"),
        ("park", "von dem Park", "公園から", "從公園", "comes from, walks from, returns from"),
        ("house", "von dem Haus", "家から", "從房子", "leaves from, walks from, comes from"),
        ("garden", "von dem Garten", "庭から", "從花園", "comes from, returns from, walks from"),
        ("kitchen", "von der Küche", "台所から", "從廚房", "comes from, walks from, returns from"),
        ("city", "von der Stadt", "街から", "從城市", "comes from, returns from, travels from"),
        ("doctor", "von dem Arzt", "医者のところから", "從醫生那裡", "comes from, returns from"),
        ("teacher", "von dem Lehrer", "先生のところから", "從老師那裡", "comes from, returns from"),
    ]

    next_id = 311
    while next_id <= 400:
        kind = (next_id - 311) % 3
        if kind in (0, 1):
            noun, dative, jp_cue, zh_cue, actions = place_and_person_sources[((next_id - 311) // 2) % len(place_and_person_sources)]
            filename = f"{next_id:03d}_von_{noun}_source.md"
            rows.append((
                filename,
                f"von as departure from {noun} as place or person origin",
                ("from", dative, noun),
                f"Use {dative}. Japanese cue: {jp_cue}. Chinese cue: {zh_cue}. Keep the relation as departure from a place or person origin, not inside a container and not destination. Use only departure or return patterns: {actions}. Do not use aus forms. Do not switch into ownership or nearby meaning.",
            ))
        else:
            noun, dative, jp_cue, zh_cue, actions = surface_sources[((next_id - 313) // 3) % len(surface_sources)]
            filename = f"{next_id:03d}_von_{noun}_surface.md"
            rows.append((
                filename,
                f"von as source from {noun} surface",
                ("from", dative, noun),
                f"Use {dative}. Japanese cue: {jp_cue}. Chinese cue: {zh_cue}. Keep the relation as source off a surface or elevated point, not inside a container and not destination. Use only movement-off patterns: {actions}. Do not use aus forms. Do not switch into ownership or destination meaning.",
            ))
        next_id += 1

    return [
        FileSpec(
            path=f"01_means_dative_anchor/{filename}",
            focus=focus,
            required_terms=required,
            notes=notes + " Keep German dative form visible in every response. Use full forms such as von dem / von der, not the contraction vom. Prefer common nouns such as the boy, the woman, the child, the man. Avoid character names in this audit batch.",
        )
        for filename, focus, required, notes in rows
    ]


def make_zu_audit_specs() -> list[FileSpec]:
    """Initial audit batch for `zu` as movement toward a person, institution, or object."""
    rows: list[tuple[str, str, tuple[str, ...], str]] = [
        ("401_zu_doctor_person.md", "zu as direction toward the doctor as a person destination", ("to", "zu dem Arzt", "doctor"), "Use zu dem Arzt. Japanese cue: 医者のところへ. Chinese cue: 到醫生那裡. Keep the relation as movement toward a person's location, not static and not source. Use movement-toward patterns such as goes to or walks to. Do not use zum."),
        ("402_zu_teacher_person.md", "zu as direction toward the teacher as a person destination", ("to", "zu dem Lehrer", "teacher"), "Use zu dem Lehrer. Japanese cue: 先生のところへ. Chinese cue: 到老師那裡. Keep the relation as movement toward a person's location, not static and not source. Use movement-toward patterns such as goes to or walks to. Do not use zum."),
        ("403_zu_child_person.md", "zu as direction toward the child as a person destination", ("to", "zu dem Kind", "child"), "Use zu dem Kind. Japanese cue: 子どものところへ. Chinese cue: 到孩子那裡. Keep the relation as movement toward a person's location, not static and not source. Use movement-toward patterns such as goes to or walks to. Do not use zum."),
        ("404_zu_boy_person.md", "zu as direction toward the boy as a person destination", ("to", "zu dem Jungen", "boy"), "Use zu dem Jungen. Japanese cue: 男の子のところへ. Chinese cue: 到男孩那裡. Keep the relation as movement toward a person's location, not static and not source. Use movement-toward patterns such as goes to or walks to. Do not use zum."),
        ("405_zu_school_place.md", "zu as direction toward school as an institution destination", ("to", "zu der Schule", "school"), "Use zu der Schule. Japanese cue: 学校へ. Chinese cue: 到學校. Keep the relation as movement toward an institution destination, not inside and not source. Use movement-toward patterns such as goes to or walks to. Do not use zur. Do not use nach der Schule or in die Schule."),
        ("406_zu_market_place.md", "zu as direction toward the market as a place destination", ("to", "zu dem Markt", "market"), "Use zu dem Markt. Japanese cue: 市場へ. Chinese cue: 到市場. Keep the relation as movement toward a place destination, not inside and not source. Use movement-toward patterns such as goes to or walks to. Do not use zum. Do not use nach dem Markt or in den Markt."),
        ("407_zu_park_place.md", "zu as direction toward the park as a place destination", ("to", "zu dem Park", "park"), "Use zu dem Park. Japanese cue: 公園へ. Chinese cue: 到公園. Keep the relation as movement toward a place destination, not inside and not source. Use movement-toward patterns such as goes to or walks to. Do not use zum. Do not use nach dem Park or in den Park."),
        ("408_zu_house_place.md", "zu as direction toward the house as a place destination", ("to", "zu dem Haus", "house"), "Use zu dem Haus. Japanese cue: 家へ. Chinese cue: 到房子. Keep the relation as movement toward a place destination, not inside and not source. Use movement-toward patterns such as goes to or walks to. Do not use zum. Do not use nach dem Haus, aus dem Haus, or in das Haus."),
        ("409_zu_door_object.md", "zu as direction toward the door as an object destination", ("to", "zu der Tür", "door"), "Use zu der Tür. Japanese cue: ドアへ. Chinese cue: 到門口. Keep the relation as movement toward an object, not through the door and not static. Use movement-toward patterns such as goes to or walks to. Do not use zur."),
        ("410_zu_gate_object.md", "zu as direction toward the gate as an object destination", ("to", "zu dem Tor", "gate"), "Use zu dem Tor. Japanese cue: 門へ. Chinese cue: 到大門. Keep the relation as movement toward an object, not through the gate and not static. Use movement-toward patterns such as goes to or walks to. Do not use zum."),
    ]

    person_destinations = [
        ("doctor", "zu dem Arzt", "医者のところへ", "到醫生那裡"),
        ("teacher", "zu dem Lehrer", "先生のところへ", "到老師那裡"),
        ("child", "zu dem Kind", "子どものところへ", "到孩子那裡"),
        ("boy", "zu dem Jungen", "男の子のところへ", "到男孩那裡"),
        ("girl", "zu dem Mädchen", "女の子のところへ", "到女孩那裡"),
        ("man", "zu dem Mann", "男の人のところへ", "到男人那裡"),
        ("woman", "zu der Frau", "女の人のところへ", "到女人那裡"),
    ]
    place_and_object_destinations = [
        ("school", "zu der Schule", "学校へ", "到學校"),
        ("market", "zu dem Markt", "市場へ", "到市場"),
        ("park", "zu dem Park", "公園へ", "到公園"),
        ("house", "zu dem Haus", "家へ", "到房子"),
        ("garden", "zu dem Garten", "庭へ", "到花園"),
        ("door", "zu der Tür", "ドアへ", "到門口"),
        ("gate", "zu dem Tor", "門へ", "到大門"),
        ("window", "zu dem Fenster", "窓へ", "到窗邊"),
        ("bench", "zu der Bank", "ベンチへ", "到長椅"),
        ("tree", "zu dem Baum", "木へ", "到樹旁"),
        ("table", "zu dem Tisch", "テーブルへ", "到桌子"),
    ]

    next_id = 411
    while next_id <= 500:
        kind = (next_id - 411) % 3
        if kind in (0, 1):
            noun, dative, jp_cue, zh_cue = person_destinations[((next_id - 411) // 2) % len(person_destinations)]
            filename = f"{next_id:03d}_zu_{noun}_person.md"
            rows.append((
                filename,
                f"zu as direction toward {noun} as a person destination",
                ("to", dative, noun),
                f"Use {dative}. Japanese cue: {jp_cue}. Chinese cue: {zh_cue}. Keep the relation as movement toward a person's location, not static and not source. Use only movement-toward patterns: goes to, walks to, runs to. Do not use contractions zum or zur. Do not use aus, von, bei, or nach forms.",
            ))
        else:
            noun, dative, jp_cue, zh_cue = place_and_object_destinations[((next_id - 413) // 3) % len(place_and_object_destinations)]
            filename = f"{next_id:03d}_zu_{noun}_place.md"
            rows.append((
                filename,
                f"zu as direction toward {noun} as a place or object destination",
                ("to", dative, noun),
                f"Use {dative}. Japanese cue: {jp_cue}. Chinese cue: {zh_cue}. Keep the relation as movement toward a place or object, not inside and not source. Use only movement-toward patterns: goes to, walks to, runs to. Do not use contractions zum or zur. Do not use aus, von, bei, nach, or in-accusative forms.",
            ))
        next_id += 1

    return [
        FileSpec(
            path=f"01_means_dative_anchor/{filename}",
            focus=focus,
            required_terms=required,
            notes=notes + " Keep German dative form visible in every response. Use full forms such as zu dem / zu der, not the contractions zum or zur. Prefer common nouns such as the boy, the woman, the child, the man. Avoid character names in this audit batch.",
        )
        for filename, focus, required, notes in rows
    ]


def make_nach_audit_specs() -> list[FileSpec]:
    """Audit batch for `nach` as direction to a city/place or temporal after."""
    rows: list[tuple[str, str, tuple[str, ...], str]] = [
        ("501_nach_berlin_city.md", "nach as direction toward Berlin as a city destination", ("to", "nach Berlin", "Berlin"), "Use nach Berlin with no article. Japanese cue: ベルリンへ. Chinese cue: 往柏林. Keep the relation as movement toward a city. Use movement-toward patterns such as goes to, travels to, flies to. Do not use nach dem or nach der."),
        ("502_nach_japan_city.md", "nach as direction toward Japan as a country destination", ("to", "nach Japan", "Japan"), "Use nach Japan with no article. Japanese cue: 日本へ. Chinese cue: 往日本. Keep the relation as movement toward a country. Use movement-toward patterns such as goes to, travels to, flies to. Do not use nach dem or nach der."),
        ("503_nach_hause_home.md", "nach as direction toward home in the fixed phrase nach Hause", ("home", "nach Hause"), "Use nach Hause. This is a fixed phrase meaning toward home. No article. Japanese cue: 家へ. Chinese cue: 回家. Keep movement-homeward meaning. Do not use nach dem Haus. Do not use static zu Hause."),
        ("504_nach_links_direction.md", "nach as orientation toward the left direction", ("nach links", "left"), "Use nach links with no article. Japanese cue: 左へ. Chinese cue: 向左. Keep the relation as turning or moving toward the left. Do not use nach dem or nach der."),
        ("505_nach_rechts_direction.md", "nach as orientation toward the right direction", ("nach rechts", "right"), "Use nach rechts with no article. Japanese cue: 右へ. Chinese cue: 向右. Keep the relation as turning or moving toward the right. Do not use nach dem or nach der."),
        ("506_nach_school_temporal.md", "nach as temporal meaning after school", ("after", "nach der Schule", "school"), "Use nach der Schule. Japanese cue: 学校の後で. Chinese cue: 上學之後. Keep temporal sequence meaning: something happens after school ends. Do not use zu der Schule or in die Schule. This is a time relation, not a place destination."),
        ("507_nach_breakfast_temporal.md", "nach as temporal meaning after breakfast", ("after", "nach dem Frühstück", "breakfast"), "Use nach dem Frühstück. Japanese cue: 朝食の後で. Chinese cue: 早餐之後. Keep temporal sequence meaning: something happens after breakfast ends. This is a time relation, not a place destination."),
        ("508_nach_hamburg_city.md", "nach as direction toward Hamburg as a city destination", ("to", "nach Hamburg", "Hamburg"), "Use nach Hamburg with no article. Japanese cue: ハンブルクへ. Chinese cue: 往漢堡. Keep the relation as movement toward a city. Use movement-toward patterns such as goes to, travels to, drives to. Do not use nach dem or nach der."),
        ("509_nach_oben_direction.md", "nach as direction upward", ("nach oben", "up"), "Use nach oben with no article. Japanese cue: 上へ. Chinese cue: 向上. Keep the relation as movement upward. Do not use nach dem or nach der."),
        ("510_nach_work_temporal.md", "nach as temporal meaning after work", ("after", "nach der Arbeit", "work"), "Use nach der Arbeit. Japanese cue: 仕事の後で. Chinese cue: 下班之後. Keep temporal sequence meaning: something happens after work ends. This is a time relation, not a place destination."),
    ]

    city_destinations = [
        ("berlin", "nach Berlin", "ベルリンへ", "往柏林"),
        ("hamburg", "nach Hamburg", "ハンブルクへ", "往漢堡"),
        ("munich", "nach München", "ミュンヘンへ", "往慕尼黑"),
        ("vienna", "nach Wien", "ウィーンへ", "往維也納"),
        ("paris", "nach Paris", "パリへ", "往巴黎"),
        ("london", "nach London", "ロンドンへ", "往倫敦"),
        ("japan", "nach Japan", "日本へ", "往日本"),
        ("rome", "nach Rom", "ローマへ", "往羅馬"),
        ("korea", "nach Korea", "韓国へ", "往韓國"),
        ("china", "nach China", "中国へ", "往中國"),
    ]
    direction_words = [
        ("links", "nach links", "左へ", "向左", "left", "toward the left"),
        ("rechts", "nach rechts", "右へ", "向右", "right", "toward the right"),
        ("oben", "nach oben", "上へ", "向上", "up", "upward"),
        ("unten", "nach unten", "下へ", "向下", "down", "downward"),
        ("vorne", "nach vorne", "前へ", "向前", "forward", "forward"),
        ("hinten", "nach hinten", "後ろへ", "向後", "back", "backward"),
        ("norden", "nach Norden", "北へ", "往北", "north", "toward the north"),
        ("sueden", "nach Süden", "南へ", "往南", "south", "toward the south"),
    ]
    temporal_nouns = [
        ("school_temporal", "nach der Schule", "school", "学校の後で", "上學之後"),
        ("work_temporal", "nach der Arbeit", "work", "仕事の後で", "下班之後"),
        ("break_temporal", "nach der Pause", "break", "休憩の後で", "休息之後"),
        ("breakfast_temporal", "nach dem Frühstück", "breakfast", "朝食の後で", "早餐之後"),
        ("lunch_temporal", "nach dem Mittagessen", "lunch", "昼食の後で", "午餐之後"),
        ("dinner_temporal", "nach dem Abendessen", "dinner", "夕食の後で", "晚餐之後"),
        ("game_temporal", "nach dem Spiel", "game", "遊びの後で", "遊戲之後"),
        ("training_temporal", "nach dem Training", "training", "練習の後で", "訓練之後"),
        ("lesson_temporal", "nach dem Unterricht", "lesson", "授業の後で", "課後"),
        ("meal_temporal", "nach dem Essen", "meal", "食事の後で", "用餐之後"),
    ]

    next_id = 511
    while next_id <= 600:
        offset = next_id - 511
        kind = offset % 3
        if kind == 0:
            noun, de_form, jp_cue, zh_cue = city_destinations[(offset // 3) % len(city_destinations)]
            filename = f"{next_id:03d}_nach_{noun}_city.md"
            rows.append((
                filename,
                f"nach as direction toward {noun} as a city or country destination",
                ("to", de_form, noun),
                f"Use {de_form} with no article. Japanese cue: {jp_cue}. Chinese cue: {zh_cue}. Keep the relation as movement toward a destination. Use movement-toward patterns: goes to, travels to, flies to, drives to. Do not use nach dem or nach der.",
            ))
        elif kind == 1:
            slug, de_form, jp_cue, zh_cue, en_req, en_desc = direction_words[(offset // 3) % len(direction_words)]
            filename = f"{next_id:03d}_nach_{slug}_direction.md"
            rows.append((
                filename,
                f"nach as direction {en_desc}",
                (de_form, en_req),
                f"Use {de_form} with no article. Japanese cue: {jp_cue}. Chinese cue: {zh_cue}. Keep the relation as movement or orientation {en_desc}. Do not use nach dem or nach der.",
            ))
        else:
            slug, de_form, en_noun, jp_cue, zh_cue = temporal_nouns[(offset // 3) % len(temporal_nouns)]
            filename = f"{next_id:03d}_nach_{slug}.md"
            rows.append((
                filename,
                f"nach as temporal meaning after {en_noun}",
                ("after", de_form, en_noun),
                f"Use {de_form}. Japanese cue: {jp_cue}. Chinese cue: {zh_cue}. Keep temporal sequence meaning: something happens after {en_noun} ends. This is a time relation, not a place destination.",
            ))
        next_id += 1

    return [
        FileSpec(
            path=f"01_means_dative_anchor/{filename}",
            focus=focus,
            required_terms=required,
            notes=notes + " nach is always dative. For city and direction destinations use the bare name form without article. For temporal after-meaning show the dative article dem or der clearly. Prefer common nouns and avoid character names in this audit batch.",
        )
        for filename, focus, required, notes in rows
    ]


def make_seit_specs() -> list[FileSpec]:
    """Specs for `seit` as ongoing duration/since (always dative, temporal only)."""
    rows: list[tuple[str, str, tuple[str, ...], str]] = [
        ("601_seit_school_temporal.md", "seit as ongoing duration since school", ("since", "seit der Schule", "school"), "Use seit der Schule. Japanese cue: 学校からずっと. Chinese cue: 從上學以來. Keep the ongoing duration meaning: something has been happening since school started or ended. Do not use nach der Schule or zu der Schule."),
        ("602_seit_work_temporal.md", "seit as ongoing duration since work", ("since", "seit der Arbeit", "work"), "Use seit der Arbeit. Japanese cue: 仕事からずっと. Chinese cue: 從工作以來. Keep the ongoing duration meaning: something has been happening since work began or ended. Do not use nach der Arbeit."),
        ("603_seit_breakfast_temporal.md", "seit as ongoing duration since breakfast", ("since", "seit dem Frühstück", "breakfast"), "Use seit dem Frühstück. Japanese cue: 朝食からずっと. Chinese cue: 從早餐以來. Keep the ongoing duration meaning: something has been happening since breakfast. Do not use nach dem Frühstück."),
        ("604_seit_lunch_temporal.md", "seit as ongoing duration since lunch", ("since", "seit dem Mittagessen", "lunch"), "Use seit dem Mittagessen. Japanese cue: 昼食からずっと. Chinese cue: 從午餐以來. Keep the ongoing duration meaning: something has been happening since lunch. Do not use nach dem Mittagessen."),
        ("605_seit_dinner_temporal.md", "seit as ongoing duration since dinner", ("since", "seit dem Abendessen", "dinner"), "Use seit dem Abendessen. Japanese cue: 夕食からずっと. Chinese cue: 從晚餐以來. Keep the ongoing duration meaning: something has been happening since dinner. Do not use nach dem Abendessen."),
        ("606_seit_game_temporal.md", "seit as ongoing duration since the game", ("since", "seit dem Spiel", "game"), "Use seit dem Spiel. Japanese cue: 遊びからずっと. Chinese cue: 從遊戲以來. Keep the ongoing duration meaning: something has been happening since the game. Do not use nach dem Spiel."),
        ("607_seit_training_temporal.md", "seit as ongoing duration since training", ("since", "seit dem Training", "training"), "Use seit dem Training. Japanese cue: 練習からずっと. Chinese cue: 從訓練以來. Keep the ongoing duration meaning: something has been happening since training. Do not use nach dem Training."),
        ("608_seit_lesson_temporal.md", "seit as ongoing duration since the lesson", ("since", "seit dem Unterricht", "lesson"), "Use seit dem Unterricht. Japanese cue: 授業からずっと. Chinese cue: 從課堂以來. Keep the ongoing duration meaning: something has been happening since the lesson. Do not use nach dem Unterricht."),
        ("609_seit_break_temporal.md", "seit as ongoing duration since the break", ("since", "seit der Pause", "break"), "Use seit der Pause. Japanese cue: 休憩からずっと. Chinese cue: 從休息以來. Keep the ongoing duration meaning: something has been happening since the break. Do not use nach der Pause."),
        ("610_seit_meal_temporal.md", "seit as ongoing duration since the meal", ("since", "seit dem Essen", "meal"), "Use seit dem Essen. Japanese cue: 食事からずっと. Chinese cue: 從用餐以來. Keep the ongoing duration meaning: something has been happening since the meal. Do not use nach dem Essen."),
    ]

    temporal_nouns = [
        ("school_temporal", "seit der Schule", "school", "学校からずっと", "從上學以來"),
        ("work_temporal", "seit der Arbeit", "work", "仕事からずっと", "從工作以來"),
        ("break_temporal", "seit der Pause", "break", "休憩からずっと", "從休息以來"),
        ("breakfast_temporal", "seit dem Frühstück", "breakfast", "朝食からずっと", "從早餐以來"),
        ("lunch_temporal", "seit dem Mittagessen", "lunch", "昼食からずっと", "從午餐以來"),
        ("dinner_temporal", "seit dem Abendessen", "dinner", "夕食からずっと", "從晚餐以來"),
        ("game_temporal", "seit dem Spiel", "game", "遊びからずっと", "從遊戲以來"),
        ("training_temporal", "seit dem Training", "training", "練習からずっと", "從訓練以來"),
        ("lesson_temporal", "seit dem Unterricht", "lesson", "授業からずっと", "從課堂以來"),
        ("meal_temporal", "seit dem Essen", "meal", "食事からずっと", "從用餐以來"),
    ]

    next_id = 611
    while next_id <= 700:
        offset = next_id - 611
        slug, de_form, en_noun, jp_cue, zh_cue = temporal_nouns[offset % len(temporal_nouns)]
        filename = f"{next_id:03d}_seit_{slug}.md"
        rows.append((
            filename,
            f"seit as ongoing duration since {en_noun}",
            ("since", de_form, en_noun),
            f"Use {de_form}. Japanese cue: {jp_cue}. Chinese cue: {zh_cue}. Keep the ongoing duration meaning: something has been happening since {en_noun}. Do not use nach or zu forms.",
        ))
        next_id += 1

    return [
        FileSpec(
            path=f"01_means_dative_anchor/{filename}",
            focus=focus,
            required_terms=required,
            notes=notes + " seit is always dative. Show the dative article dem or der clearly. Keep the since/for ongoing-duration meaning, not the after-sequence meaning. Prefer common nouns and avoid character names in this audit batch.",
        )
        for filename, focus, required, notes in rows
    ]


def make_gegenueber_specs() -> list[FileSpec]:
    """Specs for `gegenüber` as static opposite/across-from relation (always dative)."""
    rows: list[tuple[str, str, tuple[str, ...], str]] = [
        ("701_gegenueber_park_static.md", "gegenüber as static opposite relation across from a park", ("opposite", "gegenüber dem Park", "park"), "Use gegenüber dem Park. Japanese cue: 公園の向かいに. Chinese cue: 在公園對面. Keep the relation static and across-from, not nearby and not inside. Use only static actions: is, sits, stands, lies. Do not use bei dem Park."),
        ("702_gegenueber_school_static.md", "gegenüber as static opposite relation across from a school", ("opposite", "gegenüber der Schule", "school"), "Use gegenüber der Schule. Japanese cue: 学校の向かいに. Chinese cue: 在學校對面. Keep the relation static and across-from. Use only static actions: is, sits, stands. Do not use bei der Schule."),
        ("703_gegenueber_market_static.md", "gegenüber as static opposite relation across from a market", ("opposite", "gegenüber dem Markt", "market"), "Use gegenüber dem Markt. Japanese cue: 市場の向かいに. Chinese cue: 在市場對面. Keep the relation static and across-from. Use only static actions: is, sits, stands. Do not use bei dem Markt."),
        ("704_gegenueber_house_static.md", "gegenüber as static opposite relation across from a house", ("opposite", "gegenüber dem Haus", "house"), "Use gegenüber dem Haus. Japanese cue: 家の向かいに. Chinese cue: 在房子對面. Keep the relation static and across-from. Use only static actions: is, sits, stands. Do not use bei dem Haus."),
        ("705_gegenueber_tree_static.md", "gegenüber as static opposite relation across from a tree", ("opposite", "gegenüber dem Baum", "tree"), "Use gegenüber dem Baum. Japanese cue: 木の向かいに. Chinese cue: 在樹對面. Keep the relation static and across-from. Use only static actions: is, sits, stands. Do not use bei dem Baum."),
        ("706_gegenueber_bench_static.md", "gegenüber as static opposite relation across from a bench", ("opposite", "gegenüber der Bank", "bench"), "Use gegenüber der Bank. Japanese cue: ベンチの向かいに. Chinese cue: 在長椅對面. Keep the relation static and across-from. Use only static actions: is, sits, stands. Do not use bei der Bank."),
        ("707_gegenueber_bridge_static.md", "gegenüber as static opposite relation across from a bridge", ("opposite", "gegenüber der Brücke", "bridge"), "Use gegenüber der Brücke. Japanese cue: 橋の向かいに. Chinese cue: 在橋對面. Keep the relation static and across-from. Use only static actions: is, sits, stands. Do not use bei der Brücke."),
        ("708_gegenueber_garden_static.md", "gegenüber as static opposite relation across from a garden", ("opposite", "gegenüber dem Garten", "garden"), "Use gegenüber dem Garten. Japanese cue: 庭の向かいに. Chinese cue: 在花園對面. Keep the relation static and across-from. Use only static actions: is, sits, stands. Do not use bei dem Garten."),
        ("709_gegenueber_doctor_person.md", "gegenüber as sitting opposite a person — the doctor", ("opposite", "gegenüber dem Arzt", "doctor"), "Use gegenüber dem Arzt. Japanese cue: 医者の向かいに. Chinese cue: 在醫生對面. Keep the relation static and face-to-face, not nearby and not movement toward. Use only static actions: is, sits. Do not use bei dem Arzt."),
        ("710_gegenueber_teacher_person.md", "gegenüber as sitting opposite a person — the teacher", ("opposite", "gegenüber dem Lehrer", "teacher"), "Use gegenüber dem Lehrer. Japanese cue: 先生の向かいに. Chinese cue: 在老師對面. Keep the relation static and face-to-face, not nearby and not movement toward. Use only static actions: is, sits. Do not use bei dem Lehrer."),
    ]

    static_anchors = [
        ("park", "gegenüber dem Park", "公園の向かいに", "在公園對面"),
        ("school", "gegenüber der Schule", "学校の向かいに", "在學校對面"),
        ("market", "gegenüber dem Markt", "市場の向かいに", "在市場對面"),
        ("house", "gegenüber dem Haus", "家の向かいに", "在房子對面"),
        ("tree", "gegenüber dem Baum", "木の向かいに", "在樹對面"),
        ("bench", "gegenüber der Bank", "ベンチの向かいに", "在長椅對面"),
        ("bridge", "gegenüber der Brücke", "橋の向かいに", "在橋對面"),
        ("garden", "gegenüber dem Garten", "庭の向かいに", "在花園對面"),
        ("restaurant", "gegenüber dem Restaurant", "レストランの向かいに", "在餐廳對面"),
        ("river", "gegenüber dem Fluss", "川の向かいに", "在河流對面"),
    ]
    person_anchors = [
        ("doctor", "gegenüber dem Arzt", "医者の向かいに", "在醫生對面"),
        ("teacher", "gegenüber dem Lehrer", "先生の向かいに", "在老師對面"),
        ("man", "gegenüber dem Mann", "男の人の向かいに", "在男人對面"),
        ("woman", "gegenüber der Frau", "女の人の向かいに", "在女人對面"),
    ]

    next_id = 711
    while next_id <= 800:
        offset = next_id - 711
        kind = offset % 5
        if kind < 4:
            noun, de_form, jp_cue, zh_cue = static_anchors[(offset // 5 * 4 + kind) % len(static_anchors)]
            filename = f"{next_id:03d}_gegenueber_{noun}_static.md"
            rows.append((
                filename,
                f"gegenüber as static opposite relation across from a {noun}",
                ("opposite", de_form, noun),
                f"Use {de_form}. Japanese cue: {jp_cue}. Chinese cue: {zh_cue}. Keep the relation static and across-from, not nearby and not inside. Use only static actions: is, sits, stands. Do not use bei forms.",
            ))
        else:
            noun, de_form, jp_cue, zh_cue = person_anchors[(offset // 5) % len(person_anchors)]
            filename = f"{next_id:03d}_gegenueber_{noun}_person.md"
            rows.append((
                filename,
                f"gegenüber as sitting opposite a {noun}",
                ("opposite", de_form, noun),
                f"Use {de_form}. Japanese cue: {jp_cue}. Chinese cue: {zh_cue}. Keep the relation static and face-to-face, not nearby and not movement toward. Use only static actions: is, sits. Do not use bei forms.",
            ))
        next_id += 1

    return [
        FileSpec(
            path=f"01_means_dative_anchor/{filename}",
            focus=focus,
            required_terms=required,
            notes=notes + " gegenüber is always dative. Show the dative article dem or der clearly. Keep the opposite/across-from meaning, not the nearby meaning of bei. Prefer common nouns and avoid character names in this audit batch.",
        )
        for filename, focus, required, notes in rows
    ]


def make_receiver_dative_specs() -> list[FileSpec]:
    """Specs for `02_receiver_dative`: recipient and indirect-object patterns with visible dative."""
    rows: list[tuple[str, str, tuple[str, ...], str]] = [
        # give (geben) — ditransitive: dative receiver + accusative object
        ("001_give_dem_jungen.md",
         "give — Emma gibt dem Jungen den Apfel",
         ("dem Jungen", "gibt"),
         "Use Emma as the agent. Core sentence: Emma gibt dem Jungen den Apfel. "
         "Japanese cue: 男の子にあげる (に marks the receiver). Chinese cue: 給男孩. "
         "Vary the object across the 4 pairs: apple, bread, book, cup. "
         "Keep the receiver dem Jungen visible in every German line."),
        ("002_give_der_frau.md",
         "give — Taro gibt der Frau das Buch",
         ("der Frau", "gibt"),
         "Use Taro as the agent. Core sentence: Taro gibt der Frau das Buch. "
         "Japanese cue: 女の人にあげる (に marks the receiver). Chinese cue: 給女人. "
         "Vary the object across the 4 pairs: book, apple, basket, bowl. "
         "Keep the receiver der Frau visible in every German line."),
        # show (zeigen) — ditransitive
        ("003_show_dem_kind.md",
         "show — Gran zeigt dem Kind den Becher",
         ("dem Kind", "zeigt"),
         "Use Gran as the agent. Core sentence: Gran zeigt dem Kind den Becher. "
         "Japanese cue: 子どもに見せる (に marks the receiver). Chinese cue: 給孩子看. "
         "Vary the object across the 4 pairs: cup, book, apple, basket. "
         "Keep the receiver dem Kind visible in every German line."),
        ("004_show_dem_mann.md",
         "show — Emma zeigt dem Mann das Dokument",
         ("dem Mann", "zeigt"),
         "Use Emma as the agent. Core sentence: Emma zeigt dem Mann das Dokument. "
         "Japanese cue: 男の人に見せる (に marks the receiver). Chinese cue: 給男人看. "
         "Vary the object across the 4 pairs: document, book, cup, basket. "
         "Keep the receiver dem Mann visible in every German line."),
        # bring (bringen) — ditransitive
        ("005_bring_dem_maedchen.md",
         "bring — Taro bringt dem Mädchen den Korb",
         ("dem Mädchen", "bringt"),
         "Use Taro as the agent. Core sentence: Taro bringt dem Mädchen den Korb. "
         "Japanese cue: 女の子に持ってくる (に marks the receiver). Chinese cue: 帶來給女孩. "
         "Vary the object across the 4 pairs: basket, apple, book, bread. "
         "Keep the receiver dem Mädchen visible in every German line."),
        ("006_bring_dem_baby.md",
         "bring — Gran bringt dem Baby die Decke",
         ("dem Baby", "bringt"),
         "Use Gran as the agent. Core sentence: Gran bringt dem Baby die Decke. "
         "Japanese cue: 赤ちゃんに持ってくる (に marks the receiver). Chinese cue: 帶來給嬰兒. "
         "Vary the object across the 4 pairs: blanket, apple, bread, cup. "
         "Keep the receiver dem Baby visible in every German line."),
        # send (schicken) — ditransitive
        ("007_send_dem_arzt.md",
         "send — Emma schickt dem Arzt das Buch",
         ("dem Arzt", "schickt"),
         "Use Emma as the agent. Core sentence: Emma schickt dem Arzt das Buch. "
         "Japanese cue: 医者に送る (に marks the receiver). Chinese cue: 送給醫生. "
         "Vary the object across the 4 pairs: book, document, basket, bowl. "
         "Keep the receiver dem Arzt visible in every German line."),
        ("008_send_dem_kind.md",
         "send — Taro schickt dem Kind das Buch",
         ("dem Kind", "schickt"),
         "Use Taro as the agent. Core sentence: Taro schickt dem Kind das Buch. "
         "Japanese cue: 子どもに送る (に marks the receiver). Chinese cue: 送給孩子. "
         "Vary the object across the 4 pairs: book, apple, document, pencil. "
         "Keep the receiver dem Kind visible in every German line."),
        # lend (leihen) — ditransitive
        ("009_lend_der_frau.md",
         "lend — Gran leiht der Frau den Bleistift",
         ("der Frau", "leiht"),
         "Use Gran as the agent. Core sentence: Gran leiht der Frau den Bleistift. "
         "Japanese cue: 女の人に貸す (に marks the receiver). Chinese cue: 借給女人. "
         "Vary the object across the 4 pairs: pencil, book, basket, cup. "
         "Keep the receiver der Frau visible in every German line."),
        ("010_lend_dem_kind.md",
         "lend — Emma leiht dem Kind das Buch",
         ("dem Kind", "leiht"),
         "Use Emma as the agent. Core sentence: Emma leiht dem Kind das Buch. "
         "Japanese cue: 子どもに貸す (に marks the receiver). Chinese cue: 借給孩子. "
         "Vary the object across the 4 pairs: book, pencil, basket, apple. "
         "Keep the receiver dem Kind visible in every German line."),
        # help (helfen) — pure dative verb, no accusative object
        ("011_help_dem_arzt.md",
         "help — Taro hilft dem Arzt (dative only, no accusative object)",
         ("dem Arzt", "hilft"),
         "Use Taro as the agent. Core sentence: Taro hilft dem Arzt. "
         "helfen takes only dative — do not add an accusative object. "
         "Japanese cue: 医者を手伝う or 医者を助ける. Chinese cue: 幫助醫生. "
         "Vary the location or activity context across the 4 pairs (in the garden, in the kitchen, at the market, at the school). "
         "Keep the receiver dem Arzt visible in every German line."),
        ("012_help_dem_nachbarn.md",
         "help — Gran hilft dem Nachbarn (dative only, no accusative object)",
         ("dem Nachbarn", "hilft"),
         "Use Gran as the agent. Core sentence: Gran hilft dem Nachbarn. "
         "helfen takes only dative — do not add an accusative object. "
         "Japanese cue: 隣人を手伝う or 隣人を助ける. Chinese cue: 幫助鄰居. "
         "Vary the location or activity context across the 4 pairs. "
         "Keep the receiver dem Nachbarn visible in every German line."),
        # answer (antworten) — pure dative verb, no accusative object
        ("013_answer_dem_lehrer.md",
         "answer — Emma antwortet dem Lehrer (dative only, no accusative object)",
         ("dem Lehrer", "antwortet"),
         "Use Emma as the agent. Core sentence: Emma antwortet dem Lehrer. "
         "antworten takes only dative — do not add an accusative object. "
         "Japanese cue: 先生に答える (に marks the receiver). Chinese cue: 回答老師. "
         "Vary the question or topic context across the 4 pairs. "
         "Keep the receiver dem Lehrer visible in every German line."),
        ("014_answer_der_frau.md",
         "answer — Taro antwortet der Frau (dative only, no accusative object)",
         ("der Frau", "antwortet"),
         "Use Taro as the agent. Core sentence: Taro antwortet der Frau. "
         "antworten takes only dative — do not add an accusative object. "
         "Japanese cue: 女の人に答える (に marks the receiver). Chinese cue: 回答女人. "
         "Vary the question or topic context across the 4 pairs. "
         "Keep the receiver der Frau visible in every German line."),
        # tell (erzählen) — dative receiver, content may follow with von + dative
        ("015_tell_dem_jungen.md",
         "tell — Gran erzählt dem Jungen (dative receiver)",
         ("dem Jungen", "erzählt"),
         "Use Gran as the agent. Core sentence: Gran erzählt dem Jungen. "
         "Keep telling content short and concrete: erzählt dem Jungen von dem Apfel / von dem Garten / von dem Hund / von dem Baum. "
         "Japanese cue: 男の子に話す (に marks the receiver). Chinese cue: 告訴男孩. "
         "Keep the receiver dem Jungen visible in every German line."),
        ("016_tell_dem_kind.md",
         "tell — Emma erzählt dem Kind (dative receiver)",
         ("dem Kind", "erzählt"),
         "Use Emma as the agent. Core sentence: Emma erzählt dem Kind. "
         "Keep telling content short and concrete: erzählt dem Kind von dem Buch / von dem Garten / von dem Apfel / von dem Hund. "
         "Japanese cue: 子どもに話す (に marks the receiver). Chinese cue: 告訴孩子. "
         "Keep the receiver dem Kind visible in every German line."),
        # ── More geben entries ──
        ("017_give_dem_mann.md",
         "give — Gran gibt dem Mann den Becher",
         ("dem Mann", "gibt"),
         "Use Gran as the agent. Core sentence: Gran gibt dem Mann den Becher. "
         "Japanese cue: 男の人にあげる (に marks the receiver). Chinese cue: 給男人. "
         "Vary the object: cup, apple, book, bread. "
         "Keep the receiver dem Mann visible in every German line."),
        ("018_give_dem_arzt.md",
         "give — Taro gibt dem Arzt das Dokument",
         ("dem Arzt", "gibt"),
         "Use Taro as the agent. Core sentence: Taro gibt dem Arzt das Dokument. "
         "Japanese cue: 医者にあげる (に marks the receiver). Chinese cue: 給醫生. "
         "Vary the object: document, book, basket, apple. "
         "Keep the receiver dem Arzt visible in every German line."),
        ("019_give_dem_nachbarn.md",
         "give — Emma gibt dem Nachbarn das Brot",
         ("dem Nachbarn", "gibt"),
         "Use Emma as the agent. Core sentence: Emma gibt dem Nachbarn das Brot. "
         "Japanese cue: 隣人にあげる (に marks the receiver). Chinese cue: 給鄰居. "
         "Vary the object: bread, apple, cup, book. "
         "Keep the receiver dem Nachbarn visible in every German line."),
        ("020_give_dem_jungen_b.md",
         "give — Gran gibt dem Jungen den Korb",
         ("dem Jungen", "gibt"),
         "Use Gran as the agent. Core sentence: Gran gibt dem Jungen den Korb. "
         "Japanese cue: 男の子にあげる. Chinese cue: 給男孩. "
         "Vary the object: basket, bread, apple, blanket. "
         "Keep the receiver dem Jungen visible in every German line."),
        # ── More zeigen entries ──
        ("021_show_dem_jungen.md",
         "show — Taro zeigt dem Jungen den Apfel",
         ("dem Jungen", "zeigt"),
         "Use Taro as the agent. Core sentence: Taro zeigt dem Jungen den Apfel. "
         "Japanese cue: 男の子に見せる. Chinese cue: 給男孩看. "
         "Vary the object: apple, basket, cup, book. "
         "Keep the receiver dem Jungen visible in every German line."),
        ("022_show_dem_arzt.md",
         "show — Emma zeigt dem Arzt das Dokument",
         ("dem Arzt", "zeigt"),
         "Use Emma as the agent. Core sentence: Emma zeigt dem Arzt das Dokument. "
         "Japanese cue: 医者に見せる. Chinese cue: 給醫生看. "
         "Vary the object: document, book, apple, basket. "
         "Keep the receiver dem Arzt visible in every German line."),
        ("023_show_dem_nachbarn.md",
         "show — Gran zeigt dem Nachbarn den Garten",
         ("dem Nachbarn", "zeigt"),
         "Use Gran as the agent. Core sentence: Gran zeigt dem Nachbarn den Garten. "
         "Japanese cue: 隣人に見せる. Chinese cue: 給鄰居看. "
         "Vary the object: garden, basket, book, apple. "
         "Keep the receiver dem Nachbarn visible in every German line."),
        ("024_show_der_frau_b.md",
         "show — Taro zeigt der Frau den Becher",
         ("der Frau", "zeigt"),
         "Use Taro as the agent. Core sentence: Taro zeigt der Frau den Becher. "
         "Japanese cue: 女の人に見せる. Chinese cue: 給女人看. "
         "Vary the object: cup, book, apple, basket. "
         "Keep the receiver der Frau visible in every German line."),
        # ── More bringen entries ──
        ("025_bring_dem_jungen.md",
         "bring — Emma bringt dem Jungen den Apfel",
         ("dem Jungen", "bringt"),
         "Use Emma as the agent. Core sentence: Emma bringt dem Jungen den Apfel. "
         "Japanese cue: 男の子に持ってくる. Chinese cue: 帶來給男孩. "
         "Vary the object: apple, bread, book, cup. "
         "Keep the receiver dem Jungen visible in every German line."),
        ("026_bring_dem_arzt.md",
         "bring — Taro bringt dem Arzt das Dokument",
         ("dem Arzt", "bringt"),
         "Use Taro as the agent. Core sentence: Taro bringt dem Arzt das Dokument. "
         "Japanese cue: 医者に持ってくる. Chinese cue: 帶來給醫生. "
         "Vary the object: document, book, apple, basket. "
         "Keep the receiver dem Arzt visible in every German line."),
        ("027_bring_dem_mann.md",
         "bring — Gran bringt dem Mann das Brot",
         ("dem Mann", "bringt"),
         "Use Gran as the agent. Core sentence: Gran bringt dem Mann das Brot. "
         "Japanese cue: 男の人に持ってくる. Chinese cue: 帶來給男人. "
         "Vary the object: bread, apple, cup, basket. "
         "Keep the receiver dem Mann visible in every German line."),
        ("028_bring_dem_kind_b.md",
         "bring — Emma bringt dem Kind den Becher",
         ("dem Kind", "bringt"),
         "Use Emma as the agent. Core sentence: Emma bringt dem Kind den Becher. "
         "Japanese cue: 子どもに持ってくる. Chinese cue: 帶來給孩子. "
         "Vary the object: cup, apple, bread, basket. "
         "Keep the receiver dem Kind visible in every German line."),
        # ── More schicken entries ──
        ("029_send_der_frau.md",
         "send — Gran schickt der Frau den Korb",
         ("der Frau", "schickt"),
         "Use Gran as the agent. Core sentence: Gran schickt der Frau den Korb. "
         "Japanese cue: 女の人に送る. Chinese cue: 送給女人. "
         "Vary the object: basket, book, apple, document. "
         "Keep the receiver der Frau visible in every German line."),
        ("030_send_dem_jungen.md",
         "send — Taro schickt dem Jungen das Buch",
         ("dem Jungen", "schickt"),
         "Use Taro as the agent. Core sentence: Taro schickt dem Jungen das Buch. "
         "Japanese cue: 男の子に送る. Chinese cue: 送給男孩. "
         "Vary the object: book, apple, basket, document. "
         "Keep the receiver dem Jungen visible in every German line."),
        ("031_send_dem_mann.md",
         "send — Emma schickt dem Mann das Dokument",
         ("dem Mann", "schickt"),
         "Use Emma as the agent. Core sentence: Emma schickt dem Mann das Dokument. "
         "Japanese cue: 男の人に送る. Chinese cue: 送給男人. "
         "Vary the object: document, book, basket, apple. "
         "Keep the receiver dem Mann visible in every German line."),
        ("032_send_dem_nachbarn.md",
         "send — Gran schickt dem Nachbarn den Korb",
         ("dem Nachbarn", "schickt"),
         "Use Gran as the agent. Core sentence: Gran schickt dem Nachbarn den Korb. "
         "Japanese cue: 隣人に送る. Chinese cue: 送給鄰居. "
         "Vary the object: basket, bread, book, apple. "
         "Keep the receiver dem Nachbarn visible in every German line."),
        # ── More leihen entries ──
        ("033_lend_dem_jungen.md",
         "lend — Taro leiht dem Jungen den Bleistift",
         ("dem Jungen", "leiht"),
         "Use Taro as the agent. Core sentence: Taro leiht dem Jungen den Bleistift. "
         "Japanese cue: 男の子に貸す. Chinese cue: 借給男孩. "
         "Vary the object: pencil, book, basket, cup. "
         "Keep the receiver dem Jungen visible in every German line."),
        ("034_lend_dem_mann.md",
         "lend — Emma leiht dem Mann das Buch",
         ("dem Mann", "leiht"),
         "Use Emma as the agent. Core sentence: Emma leiht dem Mann das Buch. "
         "Japanese cue: 男の人に貸す. Chinese cue: 借給男人. "
         "Vary the object: book, pencil, basket, document. "
         "Keep the receiver dem Mann visible in every German line."),
        ("035_lend_dem_arzt.md",
         "lend — Gran leiht dem Arzt den Bleistift",
         ("dem Arzt", "leiht"),
         "Use Gran as the agent. Core sentence: Gran leiht dem Arzt den Bleistift. "
         "Japanese cue: 医者に貸す. Chinese cue: 借給醫生. "
         "Vary the object: pencil, book, document, basket. "
         "Keep the receiver dem Arzt visible in every German line."),
        ("036_lend_dem_kind_b.md",
         "lend — Taro leiht dem Kind das Buch",
         ("dem Kind", "leiht"),
         "Use Taro as the agent. Core sentence: Taro leiht dem Kind das Buch. "
         "Japanese cue: 子どもに貸す. Chinese cue: 借給孩子. "
         "Vary the object: book, pencil, apple, basket. "
         "Keep the receiver dem Kind visible in every German line."),
        # ── More helfen entries ──
        ("037_help_dem_nachbarn_b.md",
         "help — Emma hilft dem Nachbarn (dative only, no accusative object)",
         ("dem Nachbarn", "hilft"),
         "Use Emma as the agent. Core sentence: Emma hilft dem Nachbarn. "
         "helfen takes only dative — do not add an accusative object. "
         "Japanese cue: 隣人を手伝う. Chinese cue: 幫助鄰居. "
         "Vary the context across 4 pairs: in the garden, in the kitchen, at the school, at the market. "
         "Keep the receiver dem Nachbarn visible in every German line."),
        ("038_help_dem_mann.md",
         "help — Taro hilft dem Mann (dative only)",
         ("dem Mann", "hilft"),
         "Use Taro as the agent. Core sentence: Taro hilft dem Mann. "
         "helfen takes only dative — do not add an accusative object. "
         "Japanese cue: 男の人を手伝う. Chinese cue: 幫助男人. "
         "Vary the context across 4 pairs. "
         "Keep the receiver dem Mann visible in every German line."),
        ("039_help_dem_kind_b.md",
         "help — Gran hilft dem Kind (dative only)",
         ("dem Kind", "hilft"),
         "Use Gran as the agent. Core sentence: Gran hilft dem Kind. "
         "helfen takes only dative — do not add an accusative object. "
         "Japanese cue: 子どもを手伝う. Chinese cue: 幫助孩子. "
         "Vary the context across 4 pairs. "
         "Keep the receiver dem Kind visible in every German line."),
        ("040_help_dem_jungen.md",
         "help — Emma hilft dem Jungen (dative only)",
         ("dem Jungen", "hilft"),
         "Use Emma as the agent. Core sentence: Emma hilft dem Jungen. "
         "helfen takes only dative — do not add an accusative object. "
         "Japanese cue: 男の子を手伝う. Chinese cue: 幫助男孩. "
         "Vary the context across 4 pairs. "
         "Keep the receiver dem Jungen visible in every German line."),
        # ── More antworten entries ──
        ("041_answer_dem_arzt.md",
         "answer — Gran antwortet dem Arzt (dative only)",
         ("dem Arzt", "antwortet"),
         "Use Gran as the agent. Core sentence: Gran antwortet dem Arzt. "
         "antworten takes only dative — do not add an accusative object. "
         "Japanese cue: 医者に答える. Chinese cue: 回答醫生. "
         "Vary the topic context across 4 pairs. "
         "Keep the receiver dem Arzt visible in every German line."),
        ("042_answer_dem_mann.md",
         "answer — Emma antwortet dem Mann (dative only)",
         ("dem Mann", "antwortet"),
         "Use Emma as the agent. Core sentence: Emma antwortet dem Mann. "
         "antworten takes only dative — do not add an accusative object. "
         "Japanese cue: 男の人に答える. Chinese cue: 回答男人. "
         "Vary the topic context across 4 pairs. "
         "Keep the receiver dem Mann visible in every German line."),
        ("043_answer_dem_kind.md",
         "answer — Taro antwortet dem Kind (dative only)",
         ("dem Kind", "antwortet"),
         "Use Taro as the agent. Core sentence: Taro antwortet dem Kind. "
         "antworten takes only dative — do not add an accusative object. "
         "Japanese cue: 子どもに答える. Chinese cue: 回答孩子. "
         "Vary the topic context across 4 pairs. "
         "Keep the receiver dem Kind visible in every German line."),
        ("044_answer_dem_jungen.md",
         "answer — Gran antwortet dem Jungen (dative only)",
         ("dem Jungen", "antwortet"),
         "Use Gran as the agent. Core sentence: Gran antwortet dem Jungen. "
         "antworten takes only dative — do not add an accusative object. "
         "Japanese cue: 男の子に答える. Chinese cue: 回答男孩. "
         "Vary the topic context across 4 pairs. "
         "Keep the receiver dem Jungen visible in every German line."),
        # ── More erzählen entries ──
        ("045_tell_der_frau.md",
         "tell — Taro erzählt der Frau (dative receiver)",
         ("der Frau", "erzählt"),
         "Use Taro as the agent. Core sentence: Taro erzählt der Frau. "
         "Content: erzählt von dem Garten / von dem Hund / von dem Markt / von dem Baum. "
         "Japanese cue: 女の人に話す. Chinese cue: 告訴女人. "
         "Keep the receiver der Frau visible in every German line."),
        ("046_tell_dem_arzt.md",
         "tell — Emma erzählt dem Arzt (dative receiver)",
         ("dem Arzt", "erzählt"),
         "Use Emma as the agent. Core sentence: Emma erzählt dem Arzt. "
         "Content: erzählt von dem Apfel / von dem Garten / von dem Hund / von dem Buch. "
         "Japanese cue: 医者に話す. Chinese cue: 告訴醫生. "
         "Keep the receiver dem Arzt visible in every German line."),
        ("047_tell_dem_nachbarn.md",
         "tell — Gran erzählt dem Nachbarn (dative receiver)",
         ("dem Nachbarn", "erzählt"),
         "Use Gran as the agent. Core sentence: Gran erzählt dem Nachbarn. "
         "Content: erzählt von dem Garten / von dem Apfel / von dem Baum / von dem Hund. "
         "Japanese cue: 隣人に話す. Chinese cue: 告訴鄰居. "
         "Keep the receiver dem Nachbarn visible in every German line."),
        ("048_tell_dem_mann.md",
         "tell — Taro erzählt dem Mann (dative receiver)",
         ("dem Mann", "erzählt"),
         "Use Taro as the agent. Core sentence: Taro erzählt dem Mann. "
         "Content: erzählt von dem Korb / von dem Garten / von dem Buch / von dem Apfel. "
         "Japanese cue: 男の人に話す. Chinese cue: 告訴男人. "
         "Keep the receiver dem Mann visible in every German line."),
        # ── New verbs ──
        ("049_give_for_kochen.md",
         "cook for — Gran kocht dem Kind das Brot (beneficiary dative)",
         ("dem Kind", "kocht"),
         "Use Gran as the agent. Core sentence: Gran kocht dem Kind das Brot. "
         "kochen + dative beneficiary: Gran cooks for the child. "
         "Japanese cue: 子どものために作る (に/のために marks beneficiary). Chinese cue: 為孩子煮. "
         "Vary the food: bread, apple, soup (simple nouns). "
         "Keep the receiver dem Kind visible in every German line."),
        ("050_kochen_dem_mann.md",
         "cook for — Emma kocht dem Mann das Brot (beneficiary dative)",
         ("dem Mann", "kocht"),
         "Use Emma as the agent. Core sentence: Emma kocht dem Mann das Brot. "
         "kochen + dative beneficiary: Emma cooks for the man. "
         "Japanese cue: 男の人のために作る. Chinese cue: 為男人煮. "
         "Vary the food across 4 pairs. "
         "Keep the receiver dem Mann visible in every German line."),
        ("051_schenken_dem_kind.md",
         "gift — Taro schenkt dem Kind den Apfel (give as a present)",
         ("dem Kind", "schenkt"),
         "Use Taro as the agent. Core sentence: Taro schenkt dem Kind den Apfel. "
         "schenken = give as a gift. Japanese cue: 子どもにプレゼントする. Chinese cue: 送給孩子. "
         "Vary the gift: apple, book, basket, cup. "
         "Keep the receiver dem Kind visible in every German line."),
        ("052_schenken_dem_jungen.md",
         "gift — Gran schenkt dem Jungen das Buch (give as a present)",
         ("dem Jungen", "schenkt"),
         "Use Gran as the agent. Core sentence: Gran schenkt dem Jungen das Buch. "
         "schenken = give as a gift. Japanese cue: 男の子にプレゼントする. Chinese cue: 送給男孩. "
         "Vary the gift: book, apple, basket, pencil. "
         "Keep the receiver dem Jungen visible in every German line."),
        ("053_erklaeren_dem_kind.md",
         "explain — Emma erklärt dem Kind den Weg (explain to, dative receiver)",
         ("dem Kind", "erklärt"),
         "Use Emma as the agent. Core sentence: Emma erklärt dem Kind den Weg. "
         "erklären + dative receiver + accusative object. Japanese cue: 子どもに説明する. Chinese cue: 向孩子解釋. "
         "Vary the object: way, task, book content, drawing. "
         "Keep the receiver dem Kind visible in every German line."),
        ("054_erklaeren_dem_jungen.md",
         "explain — Taro erklärt dem Jungen das Buch (explain to)",
         ("dem Jungen", "erklärt"),
         "Use Taro as the agent. Core sentence: Taro erklärt dem Jungen das Buch. "
         "erklären + dative receiver. Japanese cue: 男の子に説明する. Chinese cue: 向男孩解釋. "
         "Vary the object: book, drawing, map, document. "
         "Keep the receiver dem Jungen visible in every German line."),
        ("055_schreiben_dem_arzt.md",
         "write to — Emma schreibt dem Arzt (dative receiver, write to someone)",
         ("dem Arzt", "schreibt"),
         "Use Emma as the agent. Core sentence: Emma schreibt dem Arzt. "
         "schreiben + dative = write to someone. Japanese cue: 医者に書く. Chinese cue: 寫信給醫生. "
         "Vary context across 4 pairs: writes about the garden, the apple, the document, the book. "
         "Keep the receiver dem Arzt visible in every German line."),
        ("056_schreiben_dem_lehrer.md",
         "write to — Taro schreibt dem Lehrer (dative receiver)",
         ("dem Lehrer", "schreibt"),
         "Use Taro as the agent. Core sentence: Taro schreibt dem Lehrer. "
         "schreiben + dative. Japanese cue: 先生に書く. Chinese cue: 寫信給老師. "
         "Vary context across 4 pairs. "
         "Keep the receiver dem Lehrer visible in every German line."),
        ("057_vorlesen_dem_kind.md",
         "read to — Gran liest dem Kind vor (dative receiver, vorlesen)",
         ("dem Kind", "liest"),
         "Use Gran as the agent. Core sentence: Gran liest dem Kind das Buch vor. "
         "vorlesen + dative = read aloud to someone. Japanese cue: 子どもに読み聞かせる. Chinese cue: 給孩子讀. "
         "Vary the object: book, story, document, apple description. "
         "Keep the receiver dem Kind visible in every German line."),
        ("058_vorlesen_dem_jungen.md",
         "read to — Emma liest dem Jungen vor (dative receiver)",
         ("dem Jungen", "liest"),
         "Use Emma as the agent. Core sentence: Emma liest dem Jungen das Buch vor. "
         "vorlesen + dative. Japanese cue: 男の子に読み聞かせる. Chinese cue: 給男孩讀. "
         "Vary the object across 4 pairs. "
         "Keep the receiver dem Jungen visible in every German line."),
        ("059_machen_dem_kind.md",
         "make for — Taro macht dem Kind das Brot (make something for someone)",
         ("dem Kind", "macht"),
         "Use Taro as the agent. Core sentence: Taro macht dem Kind das Brot. "
         "machen + dative beneficiary: Taro makes something for the child. "
         "Japanese cue: 子どものために作る. Chinese cue: 為孩子做. "
         "Vary the object: bread, basket, drawing, book cover. "
         "Keep the receiver dem Kind visible in every German line."),
        ("060_machen_dem_jungen.md",
         "make for — Gran macht dem Jungen das Brot (make for someone)",
         ("dem Jungen", "macht"),
         "Use Gran as the agent. Core sentence: Gran macht dem Jungen das Brot. "
         "machen + dative beneficiary. Japanese cue: 男の子のために作る. Chinese cue: 為男孩做. "
         "Vary the object: bread, apple dish, cup, basket. "
         "Keep the receiver dem Jungen visible in every German line."),
        # ── Named-character receivers ──
        ("061_give_to_taro.md",
         "give — Emma gibt Taro den Apfel (proper name as receiver, no article)",
         ("Taro", "gibt"),
         "Use Emma as the agent. Core sentence: Emma gibt Taro den Apfel. "
         "Proper name in dative position — no article before Taro. "
         "Japanese cue: タロウにあげる. Chinese cue: 給太郎. "
         "Vary the object: apple, book, cup, basket. "
         "Keep Taro as the receiver in every German line."),
        ("062_bring_to_emma.md",
         "bring — Taro bringt Emma den Korb (proper name as receiver)",
         ("Emma", "bringt"),
         "Use Taro as the agent. Core sentence: Taro bringt Emma den Korb. "
         "Proper name in dative position — no article before Emma. "
         "Japanese cue: エマに持ってくる. Chinese cue: 帶來給愛瑪. "
         "Vary the object: basket, apple, book, bread. "
         "Keep Emma as the receiver in every German line."),
        ("063_show_to_gran.md",
         "show — Emma zeigt Gran den Becher (proper name as receiver)",
         ("Gran", "zeigt"),
         "Use Emma as the agent. Core sentence: Emma zeigt Gran den Becher. "
         "Proper name in dative position — no article before Gran. "
         "Japanese cue: グランに見せる. Chinese cue: 給格蘭看. "
         "Vary the object: cup, book, apple, basket. "
         "Keep Gran as the receiver in every German line."),
        ("064_send_to_taro.md",
         "send — Gran schickt Taro das Buch (proper name as receiver)",
         ("Taro", "schickt"),
         "Use Gran as the agent. Core sentence: Gran schickt Taro das Buch. "
         "Proper name in dative — no article. "
         "Japanese cue: タロウに送る. Chinese cue: 寄給太郎. "
         "Vary the object: book, document, apple, basket. "
         "Keep Taro as the receiver in every German line."),
        ("065_help_gran.md",
         "help — Taro hilft Gran (proper name, dative only)",
         ("Gran", "hilft"),
         "Use Taro as the agent. Core sentence: Taro hilft Gran. "
         "helfen + dative only. Proper name, no article. "
         "Japanese cue: グランを手伝う. Chinese cue: 幫助格蘭. "
         "Vary the context across 4 pairs. "
         "Keep Gran as the receiver in every German line."),
        ("066_tell_emma.md",
         "tell — Taro erzählt Emma (proper name as receiver of information)",
         ("Emma", "erzählt"),
         "Use Taro as the agent. Core sentence: Taro erzählt Emma. "
         "erzählen + dative. Proper name, no article. "
         "Content: von dem Garten / von dem Hund / von dem Apfel / von dem Markt. "
         "Japanese cue: エマに話す. Chinese cue: 告訴愛瑪. "
         "Keep Emma as the receiver in every German line."),
        ("067_lend_to_gran.md",
         "lend — Emma leiht Gran den Bleistift (proper name as receiver)",
         ("Gran", "leiht"),
         "Use Emma as the agent. Core sentence: Emma leiht Gran den Bleistift. "
         "leihen + dative. Proper name, no article. "
         "Japanese cue: グランに貸す. Chinese cue: 借給格蘭. "
         "Vary the object: pencil, book, basket, cup. "
         "Keep Gran as the receiver in every German line."),
        ("068_answer_emma.md",
         "answer — Taro antwortet Emma (proper name as receiver, dative only)",
         ("Emma", "antwortet"),
         "Use Taro as the agent. Core sentence: Taro antwortet Emma. "
         "antworten + dative only. Proper name, no article. "
         "Japanese cue: エマに答える. Chinese cue: 回答愛瑪. "
         "Vary the topic context across 4 pairs. "
         "Keep Emma as the receiver in every German line."),
        ("069_give_to_gran.md",
         "give — Taro gibt Gran den Apfel (proper name as receiver)",
         ("Gran", "gibt"),
         "Use Taro as the agent. Core sentence: Taro gibt Gran den Apfel. "
         "Proper name, no article. "
         "Japanese cue: グランにあげる. Chinese cue: 給格蘭. "
         "Vary the object: apple, book, cup, bread. "
         "Keep Gran as the receiver in every German line."),
        ("070_explain_to_emma.md",
         "explain — Gran erklärt Emma den Weg (proper name as receiver)",
         ("Emma", "erklärt"),
         "Use Gran as the agent. Core sentence: Gran erklärt Emma den Weg. "
         "erklären + dative. Proper name, no article. "
         "Japanese cue: エマに説明する. Chinese cue: 向愛瑪解釋. "
         "Vary the object: way, book, drawing, task. "
         "Keep Emma as the receiver in every German line."),
        # ── Wem? question form files ──
        ("071_wem_geben.md",
         "Wem? question — Wem gibt Emma den Apfel? (who is the receiver?)",
         ("Wem", "gibt"),
         "Question form: Wem gibt Emma den Apfel? Answer: dem Jungen. "
         "4 pairs: vary the receiver and the object. "
         "Use dem Jungen, dem Kind, dem Mann, dem Arzt as receivers. "
         "Keep the Wem question and dative answer visible in every pair."),
        ("072_wem_zeigen.md",
         "Wem? question — Wem zeigt Gran das Buch?",
         ("Wem", "zeigt"),
         "Question form: Wem zeigt Gran das Buch? Answer: dem Kind. "
         "4 pairs: vary receiver and object. "
         "Use dem Kind, dem Jungen, der Frau, dem Mann as receivers. "
         "Keep the Wem question and dative answer visible."),
        ("073_wem_bringen.md",
         "Wem? question — Wem bringt Taro den Korb?",
         ("Wem", "bringt"),
         "Question form: Wem bringt Taro den Korb? Answer: dem Mädchen. "
         "4 pairs: vary receiver and object. "
         "Use dem Mädchen, dem Baby, dem Kind, der Frau as receivers. "
         "Keep the Wem question visible."),
        ("074_wem_schicken.md",
         "Wem? question — Wem schickt Emma das Dokument?",
         ("Wem", "schickt"),
         "Question form: Wem schickt Emma das Dokument? Answer: dem Arzt. "
         "4 pairs: vary receiver and object. "
         "Use dem Arzt, dem Lehrer, dem Mann, dem Nachbarn as receivers."),
        ("075_wem_helfen.md",
         "Wem? question — Wem hilft Gran? (dative only, no object)",
         ("Wem", "hilft"),
         "Question form: Wem hilft Gran? Answer: dem Nachbarn. "
         "helfen takes only dative — no accusative object. "
         "4 pairs: vary the receiver. Use dem Nachbarn, dem Kind, dem Mann, dem Jungen."),
        ("076_wem_antworten.md",
         "Wem? question — Wem antwortet Taro?",
         ("Wem", "antwortet"),
         "Question form: Wem antwortet Taro? Answer: dem Lehrer. "
         "antworten takes only dative. "
         "4 pairs: vary the receiver. Use dem Lehrer, dem Kind, der Frau, dem Mann."),
        ("077_wem_erzaehlen.md",
         "Wem? question — Wem erzählt Emma?",
         ("Wem", "erzählt"),
         "Question form: Wem erzählt Emma? Answer: dem Kind. "
         "4 pairs: vary receiver and content topic. "
         "Use dem Kind, dem Jungen, dem Mann, dem Nachbarn."),
        ("078_wem_leihen.md",
         "Wem? question — Wem leiht Gran den Bleistift?",
         ("Wem", "leiht"),
         "Question form: Wem leiht Gran den Bleistift? Answer: der Frau. "
         "4 pairs: vary receiver and object. "
         "Use der Frau, dem Kind, dem Jungen, dem Arzt as receivers."),
        # ── Wem vs. Wen contrast ──
        ("079_wem_vs_wen_a.md",
         "contrast: Wem? (dative receiver) vs. Wen? (accusative direct object)",
         ("Wem", "Wen"),
         "Contrast: Wem gibt Emma den Apfel? → dem Jungen (dative receiver). "
         "Wen sieht Emma? → den Jungen (accusative object). "
         "4 pairs alternating Wem and Wen. Reinforce: Wem = dative, Wen = accusative. "
         "Use familiar agents, receivers, and objects."),
        ("080_wem_vs_wen_b.md",
         "contrast: Wem? vs. Wen? with show and see",
         ("Wem", "Wen"),
         "Contrast: Wem zeigt Gran das Buch? → dem Kind (dative). "
         "Wen sieht Gran? → das Kind (accusative). "
         "4 pairs alternating Wem (zeigen) and Wen (sehen). "
         "Reinforce the dative/accusative distinction."),
        ("081_wem_vs_wen_c.md",
         "contrast: Wem? vs. Wen? with bring and call",
         ("Wem", "Wen"),
         "Contrast: Wem bringt Taro den Korb? → dem Mädchen (dative). "
         "Wen ruft Taro? → das Mädchen (accusative). "
         "4 pairs alternating Wem and Wen."),
        ("082_wem_vs_wen_review.md",
         "review: Wem? vs. Wen? — mixed verbs",
         ("Wem", "Wen"),
         "Mixed review: 4 pairs each with a different verb. "
         "Pair 1: Wem gibt (dative). Pair 2: Wen sieht (accusative). "
         "Pair 3: Wem hilft (dative). Pair 4: Wen nimmt (accusative). "
         "Keep the answer in the correct case."),
        ("083_wem_vs_wen_d.md",
         "contrast: Wem? vs. Wen? with answer and see",
         ("Wem", "Wen"),
         "Contrast: Wem antwortet Emma? → dem Lehrer (dative, antworten). "
         "Wen sieht Emma? → den Lehrer (accusative, sehen). "
         "4 pairs alternating the two question types. "
         "Keep the dative/accusative contrast explicit."),
        ("084_wem_vs_wen_e.md",
         "contrast: Wem? vs. Wen? — full scene with giver, receiver, and observer",
         ("Wem", "Wen"),
         "Scene: Emma gibt dem Kind den Apfel. Wen sieht Gran? → das Kind. Wem gibt Emma? → dem Kind. "
         "4 pairs using the same scene from different angles. "
         "Alternate Wem and Wen questions."),
        # ── Mixed review stories ──
        ("085_review_give_show.md",
         "mixed review: geben + zeigen in one scene",
         ("gibt", "zeigt"),
         "Scene: Emma gibt dem Kind den Apfel. Gran zeigt dem Kind das Buch. "
         "4 pairs mixing geben and zeigen with different receivers and objects. "
         "Keep both receivers in dative visible."),
        ("086_review_bring_send.md",
         "mixed review: bringen + schicken in one scene",
         ("bringt", "schickt"),
         "Scene: Taro bringt dem Jungen den Korb. Emma schickt dem Arzt das Dokument. "
         "4 pairs mixing bringen and schicken. Keep dative receivers visible."),
        ("087_review_help_answer.md",
         "mixed review: helfen + antworten (pure dative verbs)",
         ("hilft", "antwortet"),
         "Scene: Gran hilft dem Nachbarn. Taro antwortet dem Lehrer. "
         "Both verbs take only dative — no accusative object. "
         "4 pairs mixing helfen and antworten."),
        ("088_review_lend_tell.md",
         "mixed review: leihen + erzählen in one scene",
         ("leiht", "erzählt"),
         "Scene: Emma leiht der Frau den Bleistift. Gran erzählt dem Kind von dem Garten. "
         "4 pairs mixing leihen and erzählen with different receivers and objects."),
        ("089_review_all_verbs_a.md",
         "review: all 8 core verbs — one pair per verb",
         ("gibt", "zeigt"),
         "Each of the 4 pairs uses a different verb: geben, zeigen, bringen, schicken. "
         "Keep the dative receiver visible in every pair. "
         "Use Emma/Taro/Gran as agents; use dem Kind, dem Jungen, der Frau, dem Arzt as receivers."),
        ("090_review_all_verbs_b.md",
         "review: all 8 core verbs — second batch",
         ("leiht", "hilft"),
         "Each of the 4 pairs uses a different verb: leihen, helfen, antworten, erzählen. "
         "Keep the dative receiver visible. "
         "For helfen and antworten: no accusative object."),
        ("091_review_story_a.md",
         "review story A: Emma's morning — two receivers, two actions",
         ("gibt", "zeigt"),
         "Story: Emma gibt dem Kind den Apfel. Emma zeigt dem Jungen das Buch. "
         "Emma schickt dem Arzt das Dokument. Emma leiht der Frau den Bleistift. "
         "4 pairs narrating Emma's morning; each uses a different receiver verb."),
        ("092_review_story_b.md",
         "review story B: Taro's afternoon — different verbs and receivers",
         ("bringt", "erzählt"),
         "Story: Taro bringt dem Mädchen den Korb. Taro erzählt dem Jungen von dem Garten. "
         "Taro hilft dem Nachbarn. Taro antwortet dem Lehrer. "
         "4 pairs; each receiver in dative."),
        ("093_review_story_c.md",
         "review story C: Gran gives, shows, and tells",
         ("gibt", "erzählt"),
         "Story: Gran gibt dem Kind die Decke. Gran zeigt dem Jungen den Apfel. "
         "Gran erzählt dem Kind von dem Hund. Gran leiht dem Mann das Buch. "
         "4 pairs; keep all dative receivers explicit."),
        ("094_review_wem_all.md",
         "review: Wem? questions for all 8 core verbs",
         ("Wem", "gibt"),
         "Each pair uses Wem? with a different verb. "
         "Pair 1: Wem gibt Emma? Pair 2: Wem zeigt Gran? "
         "Pair 3: Wem bringt Taro? Pair 4: Wem schickt Emma? "
         "Keep the dative answer explicit."),
        ("095_review_wem_all_b.md",
         "review: Wem? questions — second batch of verbs",
         ("Wem", "leiht"),
         "Each pair uses Wem? with a different verb. "
         "Pair 1: Wem leiht Gran? Pair 2: Wem hilft Taro? "
         "Pair 3: Wem antwortet Emma? Pair 4: Wem erzählt Gran? "
         "Keep the dative answer explicit."),
        ("096_review_full_scene_a.md",
         "full scene review A: three agents, three receivers",
         ("gibt", "bringt"),
         "Scene: Emma gibt dem Kind den Apfel. Taro bringt dem Jungen den Korb. "
         "Gran zeigt dem Mann das Buch. Identify each agent, receiver, and object. "
         "4 pairs cycling through the three agent-receiver-object combinations."),
        ("097_review_full_scene_b.md",
         "full scene review B: pure dative verbs in context",
         ("hilft", "antwortet"),
         "Scene: Gran hilft dem Nachbarn. Emma antwortet dem Lehrer. "
         "Taro hilft dem Kind. Gran antwortet dem Mann. "
         "4 pairs using only pure dative verbs; no accusative objects."),
        ("098_review_mixed_a.md",
         "mixed review: ditransitive + pure dative in one scene",
         ("gibt", "hilft"),
         "Mixed scene: Emma gibt dem Kind den Apfel (ditransitive). "
         "Taro hilft dem Jungen (pure dative). "
         "4 pairs alternating the two types; identify which verb takes an accusative object."),
        ("099_review_mixed_b.md",
         "mixed review: named and unnamed receivers side by side",
         ("gibt", "bringt"),
         "Mixed: Emma gibt Taro den Apfel (named receiver, no article). "
         "Gran bringt dem Kind die Decke (article + noun receiver). "
         "4 pairs alternating named and unnamed receivers."),
        ("100_review_final.md",
         "final review: all receiver patterns in one comprehensive scene",
         ("Wem", "gibt"),
         "Comprehensive review: 4 pairs each highlighting a different aspect of receiver dative. "
         "Pair 1: Wem? question. Pair 2: named vs. unnamed receiver. "
         "Pair 3: pure dative verb (helfen/antworten). Pair 4: ditransitive verb. "
         "Use Emma/Taro/Gran and familiar objects. Keep all dative forms explicit."),
    ]

    shared_suffix = (
        " The German receiver dative must use the full dative article dem or der with a common noun — "
        "not a bare proper name. Do not add nouns outside the grammar lexicon. "
        "Keep vocabulary simple and concrete."
    )

    return [
        FileSpec(
            path=f"02_receiver_dative/{filename}",
            focus=focus,
            required_terms=required,
            notes=notes + shared_suffix,
        )
        for filename, focus, required, notes in rows
    ]


def make_place_static_dative_specs() -> list[FileSpec]:
    """Specs for `03_place_static_dative`: static location with two-way prepositions in dative."""
    rows: list[tuple[str, str, tuple[str, ...], str]] = [
        # ── auf + dative (on a surface, static) ────────────────────────────
        ("001_auf_tisch_static.md",
         "auf + dative — cup is on the table (static location)",
         ("auf dem Tisch", "on", "table"),
         "Core German sentence: Der Becher ist auf dem Tisch. "
         "Static location: the cup is resting on the table. "
         "Japanese cue: テーブルの上に. Chinese cue: 在桌子上. "
         "Use only static verbs: is, sits, lies, stands. "
         "Do not use movement-onto patterns such as puts or places. "
         "Vary the subject across the 4 pairs: cup, apple, book, basket. "
         "Keep auf dem Tisch visible in every German line."),
        ("002_auf_boden_static.md",
         "auf + dative — ball is on the floor (static location)",
         ("auf dem Boden", "on", "floor"),
         "Core German sentence: Der Ball ist auf dem Boden. "
         "Static location: the ball is resting on the floor. "
         "Japanese cue: 床の上に. Chinese cue: 在地板上. "
         "Use only static verbs: is, lies, sits. "
         "Do not use movement-onto patterns. "
         "Vary the subject across the 4 pairs: ball, book, bag, blanket. "
         "Keep auf dem Boden visible in every German line."),
        ("003_auf_bank_static.md",
         "auf + dative — book is on the bench (static location)",
         ("auf der Bank", "on", "bench"),
         "Core German sentence: Das Buch ist auf der Bank. "
         "Static location: the book is resting on the bench. "
         "Japanese cue: ベンチの上に. Chinese cue: 在長椅上. "
         "Use only static verbs: is, lies, sits. "
         "Do not use movement-onto patterns. "
         "Vary the subject across the 4 pairs: book, apple, basket, blanket. "
         "Keep auf der Bank visible in every German line."),
        # ── in + dative (inside, static) ───────────────────────────────────
        ("004_in_kueche_static.md",
         "in + dative — cup is in the kitchen (static location)",
         ("in der Küche", "in", "kitchen"),
         "Core German sentence: Der Becher ist in der Küche. "
         "Static location: the cup is inside the kitchen. "
         "Japanese cue: 台所の中に. Chinese cue: 在廚房裡. "
         "Use only static verbs: is, sits, stands. "
         "Do not use movement-into patterns such as goes into or puts into. "
         "Vary the subject across the 4 pairs: cup, basket, bread, apple. "
         "Keep in der Küche visible in every German line."),
        ("005_in_garten_static.md",
         "in + dative — ball is in the garden (static location)",
         ("in dem Garten", "in", "garden"),
         "Core German sentence: Der Ball ist in dem Garten. "
         "Static location: the ball is inside the garden. "
         "Japanese cue: 庭の中に. Chinese cue: 在花園裡. "
         "Use only static verbs: is, lies, sits, stands. "
         "Do not use movement-into patterns. "
         "Vary the subject across the 4 pairs: ball, bench, dog, boy. Use Hund for dog, Junge for boy. "
         "Keep in dem Garten visible in every German line."),
        ("006_in_zimmer_static.md",
         "in + dative — book is in the room (static location)",
         ("in dem Zimmer", "in", "room"),
         "Core German sentence: Das Buch ist in dem Zimmer. "
         "Static location: the book is inside the room. "
         "Japanese cue: 部屋の中に. Chinese cue: 在房間裡. "
         "Use only static verbs: is, lies, sits, stands. "
         "Do not use movement-into patterns. "
         "Vary the subject across the 4 pairs: book, blanket, basket, ball. "
         "Keep in dem Zimmer visible in every German line."),
        # ── über + dative (above, static) ──────────────────────────────────
        ("007_ueber_berg_static.md",
         "über + dative — cloud is above the mountain (static location)",
         ("über dem Berg", "above", "mountain"),
         "Core German sentence: Die Wolke ist über dem Berg. "
         "Static location above: the cloud is above the mountain. "
         "Japanese cue: 山の上に. Chinese cue: 在山上方. "
         "Use only static verbs: is, floats, hangs. "
         "Preferred subjects: cloud (Wolke), bird (Vogel), sun (Sonne). "
         "Do not use movement-over patterns. "
         "Vary the subject across the 4 pairs: cloud, bird, sun, cloud again. "
         "Keep über dem Berg visible in every German line."),
        ("008_ueber_tisch_static.md",
         "über + dative — lamp is above the table (static location)",
         ("über dem Tisch", "above", "table"),
         "Core German sentence: Die Lampe ist über dem Tisch. "
         "Static location above: the lamp hangs above the table. "
         "Japanese cue: テーブルの上に. Chinese cue: 在桌子上方. "
         "Use only static verbs: is, hangs. "
         "Preferred subjects: lamp (Lampe), bird (Vogel), cloud (Wolke). "
         "Do not use movement-over patterns. "
         "Vary the subject across the 4 pairs: lamp, bird, cloud, lamp again. "
         "Keep über dem Tisch visible in every German line."),
        ("009_ueber_tuer_static.md",
         "über + dative — sign is above the door (static location)",
         ("über der Tür", "above", "door"),
         "Core German sentence: Das Schild ist über der Tür. "
         "Static location above: the sign hangs above the door. "
         "Japanese cue: ドアの上に. Chinese cue: 在門上方. "
         "Use only static verbs: is, hangs. "
         "Preferred subjects: sign (Schild), lamp (Lampe), bird (Vogel). "
         "Do not use movement-over patterns. "
         "Vary the subject across the 4 pairs: sign, lamp, bird, sign again. "
         "Keep über der Tür visible in every German line."),
        # ── unter + dative (under, static) ─────────────────────────────────
        ("010_unter_bank_static.md",
         "unter + dative — ball is under the bench (static location)",
         ("unter der Bank", "under", "bench"),
         "Core German sentence: Der Ball ist unter der Bank. "
         "Static location below: the ball is under the bench. "
         "Japanese cue: ベンチの下に. Chinese cue: 在長椅下面. "
         "Use only static verbs: is, lies, sits. "
         "Do not use movement-under patterns. "
         "Vary the subject across the 4 pairs: ball, bag, book, blanket. "
         "Keep unter der Bank visible in every German line."),
        ("011_unter_tisch_static.md",
         "unter + dative — bag is under the table (static location)",
         ("unter dem Tisch", "under", "table"),
         "Core German sentence: Die Tasche ist unter dem Tisch. "
         "Static location below: the bag is under the table. "
         "Japanese cue: テーブルの下に. Chinese cue: 在桌子下面. "
         "Use only static verbs: is, lies, sits. "
         "Do not use movement-under patterns. "
         "Vary the subject across the 4 pairs: bag, ball, book, cat. Use Katze for cat. "
         "Keep unter dem Tisch visible in every German line."),
        ("012_unter_baum_static.md",
         "unter + dative — bench is under the tree (static location)",
         ("unter dem Baum", "under", "tree"),
         "Core German sentence: Die Bank ist unter dem Baum. "
         "Static location below: the bench is under the tree. "
         "Japanese cue: 木の下に. Chinese cue: 在樹下. "
         "Use only static verbs: is, lies, sits, stands. "
         "Do not use movement-under patterns. "
         "Vary the subject across the 4 pairs: bench, ball, bag, dog. Use Hund for dog. "
         "Keep unter dem Baum visible in every German line."),
        # ── neben + dative (next to, static) ───────────────────────────────
        ("013_neben_baum_static.md",
         "neben + dative — bench is next to the tree (static location)",
         ("neben dem Baum", "next to", "tree"),
         "Core German sentence: Die Bank ist neben dem Baum. "
         "Static location next to: the bench is next to the tree. "
         "Japanese cue: 木の隣に. Chinese cue: 在樹旁邊. "
         "Use only static verbs: is, sits, stands. "
         "Do not use movement-toward patterns. "
         "Vary the subject across the 4 pairs: bench, ball, boy, dog. Use Junge for boy, Hund for dog. "
         "Keep neben dem Baum visible in every German line."),
        ("014_neben_haus_static.md",
         "neben + dative — garden is next to the house (static location)",
         ("neben dem Haus", "next to", "house"),
         "Core German sentence: Der Garten ist neben dem Haus. "
         "Static location next to: the garden is next to the house. "
         "Japanese cue: 家の隣に. Chinese cue: 在房子旁邊. "
         "Use only static verbs: is, sits, stands. "
         "Do not use movement-toward patterns. "
         "Vary the subject across the 4 pairs: garden, bench, tree, ball. "
         "Keep neben dem Haus visible in every German line."),
        ("015_neben_bank_static.md",
         "neben + dative — ball is next to the bench (static location)",
         ("neben der Bank", "next to", "bench"),
         "Core German sentence: Der Ball ist neben der Bank. "
         "Static location next to: the ball is next to the bench. "
         "Japanese cue: ベンチの隣に. Chinese cue: 在長椅旁邊. "
         "Use only static verbs: is, lies, sits. "
         "Do not use movement-toward patterns. "
         "Vary the subject across the 4 pairs: ball, bag, book, apple. "
         "Keep neben der Bank visible in every German line."),
        # ── vor + dative (in front of, static) ─────────────────────────────
        ("016_vor_haus_static.md",
         "vor + dative — dog is in front of the house (static location)",
         ("vor dem Haus", "in front of", "house"),
         "Core German sentence: Der Hund ist vor dem Haus. "
         "Static location in front of: the dog is in front of the house. "
         "Japanese cue: 家の前に. Chinese cue: 在房子前面. "
         "Use only static verbs: is, sits, stands. "
         "Do not use movement-toward or movement-into patterns. "
         "Vary the subject across the 4 pairs: dog, boy, girl, bench. Use Hund, Junge, Mädchen. "
         "Keep vor dem Haus visible in every German line."),
        ("017_vor_tuer_static.md",
         "vor + dative — boy is in front of the door (static location)",
         ("vor der Tür", "in front of", "door"),
         "Core German sentence: Der Junge ist vor der Tür. "
         "Static location in front of: the boy is in front of the door. "
         "Japanese cue: ドアの前に. Chinese cue: 在門前. "
         "Use only static verbs: is, sits, stands. "
         "Do not use movement-through or movement-toward patterns. "
         "Vary the subject across the 4 pairs: boy, girl, man, dog. Use Junge, Mädchen, Mann, Hund. "
         "Keep vor der Tür visible in every German line."),
        ("018_vor_schule_static.md",
         "vor + dative — man is in front of the school (static location)",
         ("vor der Schule", "in front of", "school"),
         "Core German sentence: Der Mann ist vor der Schule. "
         "Static location in front of: the man is in front of the school. "
         "Japanese cue: 学校の前に. Chinese cue: 在學校前面. "
         "Use only static verbs: is, sits, stands. "
         "Do not use movement-toward or entry patterns. "
         "Vary the subject across the 4 pairs: man, woman, boy, dog. Use Mann, Frau, Junge, Hund. "
         "Keep vor der Schule visible in every German line."),
        # ── hinter + dative (behind, static) ───────────────────────────────
        ("019_hinter_tuer_static.md",
         "hinter + dative — bag is behind the door (static location)",
         ("hinter der Tür", "behind", "door"),
         "Core German sentence: Die Tasche ist hinter der Tür. "
         "Static location behind: the bag is behind the door. "
         "Japanese cue: ドアの後ろに. Chinese cue: 在門後面. "
         "Use only static verbs: is, sits, lies. "
         "Do not use movement-behind or hiding-movement patterns. "
         "Vary the subject across the 4 pairs: bag, ball, book, blanket. "
         "Keep hinter der Tür visible in every German line."),
        ("020_hinter_haus_static.md",
         "hinter + dative — garden is behind the house (static location)",
         ("hinter dem Haus", "behind", "house"),
         "Core German sentence: Der Garten ist hinter dem Haus. "
         "Static location behind: the garden is behind the house. "
         "Japanese cue: 家の後ろに. Chinese cue: 在房子後面. "
         "Use only static verbs: is, sits, stands. "
         "Do not use movement-behind patterns. "
         "Vary the subject across the 4 pairs: garden, bench, tree, ball. "
         "Keep hinter dem Haus visible in every German line."),
        ("021_hinter_baum_static.md",
         "hinter + dative — dog is behind the tree (static location)",
         ("hinter dem Baum", "behind", "tree"),
         "Core German sentence: Der Hund ist hinter dem Baum. "
         "Static location behind: the dog is behind the tree. "
         "Japanese cue: 木の後ろに. Chinese cue: 在樹後面. "
         "Use only static verbs: is, sits, stands. "
         "Do not use movement-behind or hiding-movement patterns. "
         "Vary the subject across the 4 pairs: dog, boy, ball, girl. Use Hund, Junge, Mädchen. "
         "Keep hinter dem Baum visible in every German line."),
        # ── zwischen + dative (between, static) ────────────────────────────
        ("022_zwischen_stuehlen_static.md",
         "zwischen + dative — ball is between the chairs (static location)",
         ("zwischen den Stühlen", "between", "chairs"),
         "Core German sentence: Der Ball ist zwischen den Stühlen. "
         "Static location between: the ball is between the chairs. "
         "zwischen takes dative plural: den Stühlen. "
         "Japanese cue: 椅子の間に. Chinese cue: 在椅子之間. "
         "Use only static verbs: is, lies, sits. "
         "Do not use movement-between patterns. "
         "Vary the subject across the 4 pairs: ball, bag, book, blanket. "
         "Keep zwischen den Stühlen visible in every German line."),
        ("023_zwischen_baeumen_static.md",
         "zwischen + dative — bench is between the trees (static location)",
         ("zwischen den Bäumen", "between", "trees"),
         "Core German sentence: Die Bank ist zwischen den Bäumen. "
         "Static location between: the bench is between the trees. "
         "zwischen takes dative plural: den Bäumen. "
         "Japanese cue: 木の間に. Chinese cue: 在樹木之間. "
         "Use only static verbs: is, sits, stands. "
         "Do not use movement-between patterns. "
         "Vary the subject across the 4 pairs: bench, ball, boy, dog. Use Junge, Hund. "
         "Keep zwischen den Bäumen visible in every German line."),
        ("024_zwischen_bank_baum_static.md",
         "zwischen + dative — ball is between the bench and the tree (static location)",
         ("zwischen der Bank", "between", "bench"),
         "Core German sentence: Der Ball ist zwischen der Bank und dem Baum. "
         "Static location between two landmarks: the ball is between the bench and the tree. "
         "zwischen takes dative: zwischen der Bank und dem Baum. "
         "Japanese cue: ベンチと木の間に. Chinese cue: 在長椅和樹之間. "
         "Use only static verbs: is, lies, sits. "
         "Do not use movement-between patterns. "
         "Vary the subject across the 4 pairs: ball, bag, apple, blanket. "
         "Keep zwischen der Bank und dem Baum visible in every German line."),
        # ── More auf entries (025-031) ──
        ("025_auf_stuhl_static.md",
         "auf + dative — bag is on the chair (static location)",
         ("auf dem Stuhl", "on", "chair"),
         "Core German sentence: Die Tasche ist auf dem Stuhl. "
         "Static location: the bag is resting on the chair. "
         "Japanese cue: 椅子の上に. Chinese cue: 在椅子上. "
         "Use only static verbs: is, lies, sits. "
         "Do not use movement-onto patterns. "
         "Vary the subject across the 4 pairs: bag, book, apple, blanket. "
         "Keep auf dem Stuhl visible in every German line."),
        ("026_auf_regal_static.md",
         "auf + dative — book is on the shelf (static location)",
         ("auf dem Regal", "on", "shelf"),
         "Core German sentence: Das Buch ist auf dem Regal. "
         "Static location: the book is resting on the shelf. "
         "Japanese cue: 棚の上に. Chinese cue: 在架子上. "
         "Use only static verbs: is, lies, sits, stands. "
         "Do not use movement-onto patterns. "
         "Vary the subject across the 4 pairs: book, basket, cup, apple. "
         "Keep auf dem Regal visible in every German line."),
        ("027_auf_berg_static.md",
         "auf + dative — bird is on the mountain (static location)",
         ("auf dem Berg", "on", "mountain"),
         "Core German sentence: Der Vogel ist auf dem Berg. "
         "Static location: the bird is on the mountain. "
         "Japanese cue: 山の上に. Chinese cue: 在山上. "
         "Use only static verbs: is, sits, stands. "
         "Preferred subjects: bird (Vogel), dog (Hund), man (Mann). "
         "Do not use movement-onto patterns. "
         "Vary the subject: bird, dog, cloud, boy. Use Vogel, Hund, Wolke, Junge. "
         "Keep auf dem Berg visible in every German line."),
        ("028_auf_matte_static.md",
         "auf + dative — cat is on the mat (static location)",
         ("auf der Matte", "on", "mat"),
         "Core German sentence: Die Katze ist auf der Matte. "
         "Static location: the cat is resting on the mat. "
         "Japanese cue: マットの上に. Chinese cue: 在墊子上. "
         "Use only static verbs: is, lies, sits. "
         "Vary the subject: cat, dog, ball, blanket. Use Katze, Hund. "
         "Keep auf der Matte visible in every German line."),
        ("029_auf_bank_b_static.md",
         "auf + dative — cup is on the bench (static location, second bench file)",
         ("auf der Bank", "on", "bench"),
         "Core German sentence: Der Becher ist auf der Bank. "
         "Static location: the cup is on the bench. "
         "Japanese cue: ベンチの上に. Chinese cue: 在長椅上. "
         "Use only static verbs: is, sits, stands. "
         "Vary the subject: cup, book, bag, basket. "
         "Keep auf der Bank visible in every German line."),
        ("030_auf_boden_b_static.md",
         "auf + dative — basket is on the floor (static, second floor file)",
         ("auf dem Boden", "on", "floor"),
         "Core German sentence: Der Korb ist auf dem Boden. "
         "Static location: the basket is on the floor. "
         "Japanese cue: 床の上に. Chinese cue: 在地板上. "
         "Use only static verbs: is, lies, sits. "
         "Vary the subject: basket, ball, bag, blanket. "
         "Keep auf dem Boden visible in every German line."),
        ("031_auf_tisch_b_static.md",
         "auf + dative — pencil is on the table (static, second table file)",
         ("auf dem Tisch", "on", "table"),
         "Core German sentence: Der Bleistift ist auf dem Tisch. "
         "Static location: the pencil is on the table. "
         "Japanese cue: テーブルの上に. Chinese cue: 在桌子上. "
         "Use only static verbs: is, lies, sits. "
         "Vary the subject: pencil, book, basket, apple. "
         "Keep auf dem Tisch visible in every German line."),
        # ── More in entries (032-038) ──
        ("032_in_schrank_static.md",
         "in + dative — apple is in the cupboard (static location)",
         ("in dem Schrank", "in", "cupboard"),
         "Core German sentence: Der Apfel ist in dem Schrank. "
         "Static location inside the cupboard. "
         "Japanese cue: 戸棚の中に. Chinese cue: 在櫃子裡. "
         "Use only static verbs: is, lies, sits. "
         "Vary the subject: apple, cup, book, basket. "
         "Keep in dem Schrank visible in every German line."),
        ("033_in_korb_static.md",
         "in + dative — apple is in the basket (static location)",
         ("in dem Korb", "in", "basket"),
         "Core German sentence: Der Apfel ist in dem Korb. "
         "Static location inside the basket. "
         "Japanese cue: かごの中に. Chinese cue: 在籃子裡. "
         "Use only static verbs: is, lies, sits. "
         "Vary the subject: apple, bread, book, blanket. "
         "Keep in dem Korb visible in every German line."),
        ("034_in_schule_static.md",
         "in + dative — boy is in the school (static location, animate)",
         ("in der Schule", "in", "school"),
         "Core German sentence: Der Junge ist in der Schule. "
         "Static location inside the school. "
         "Japanese cue: 学校の中に. Chinese cue: 在學校裡. "
         "Use static verbs: is, sits, stands. "
         "Animate subjects: Junge, Mädchen, Mann, Frau. "
         "Vary the subject: boy, girl, man, woman. "
         "Keep in der Schule visible in every German line."),
        ("035_in_haus_static.md",
         "in + dative — dog is in the house (static location)",
         ("in dem Haus", "in", "house"),
         "Core German sentence: Der Hund ist in dem Haus. "
         "Static location inside the house. "
         "Japanese cue: 家の中に. Chinese cue: 在房子裡. "
         "Use static verbs: is, lies, sits, sleeps. "
         "Vary the subject: dog, cat, boy, blanket. Use Hund, Katze, Junge. "
         "Keep in dem Haus visible in every German line."),
        ("036_in_tasche_static.md",
         "in + dative — book is in the bag (static location)",
         ("in der Tasche", "in", "bag"),
         "Core German sentence: Das Buch ist in der Tasche. "
         "Static location inside the bag. "
         "Japanese cue: かばんの中に. Chinese cue: 在袋子裡. "
         "Use only static verbs: is, lies, sits. "
         "Vary the subject: book, apple, pencil, document. "
         "Keep in der Tasche visible in every German line."),
        ("037_in_park_static.md",
         "in + dative — bench is in the park (static location)",
         ("in dem Park", "in", "park"),
         "Core German sentence: Die Bank ist in dem Park. "
         "Static location inside the park. "
         "Japanese cue: 公園の中に. Chinese cue: 在公園裡. "
         "Use only static verbs: is, stands, sits. "
         "Vary the subject: bench, tree, dog, ball. Use Bank, Baum, Hund. "
         "Keep in dem Park visible in every German line."),
        ("038_in_garten_b_static.md",
         "in + dative — tree is in the garden (static, second garden file)",
         ("in dem Garten", "in", "garden"),
         "Core German sentence: Der Baum ist in dem Garten. "
         "Static location inside the garden. "
         "Japanese cue: 庭の中に. Chinese cue: 在花園裡. "
         "Use only static verbs: is, stands, grows. "
         "Vary the subject: tree, bench, dog, ball. Use Baum, Bank, Hund. "
         "Keep in dem Garten visible in every German line."),
        # ── More über entries (039-045) ──
        ("039_ueber_dach_static.md",
         "über + dative — bird is above the roof (static location)",
         ("über dem Dach", "above", "roof"),
         "Core German sentence: Der Vogel ist über dem Dach. "
         "Static location above the roof. "
         "Japanese cue: 屋根の上に. Chinese cue: 在屋頂上方. "
         "Use only static verbs: is, flies, hovers. "
         "Preferred subjects: bird (Vogel), cloud (Wolke). "
         "Vary the subject: bird, cloud, sun, bird again. "
         "Keep über dem Dach visible in every German line."),
        ("040_ueber_bank_static.md",
         "über + dative — lamp is above the bench (static location)",
         ("über der Bank", "above", "bench"),
         "Core German sentence: Die Lampe ist über der Bank. "
         "Static location above the bench. "
         "Japanese cue: ベンチの上に. Chinese cue: 在長椅上方. "
         "Use only static verbs: is, hangs. "
         "Preferred subjects: lamp (Lampe), bird (Vogel), cloud (Wolke). "
         "Vary: lamp, bird, cloud, lamp again. "
         "Keep über der Bank visible in every German line."),
        ("041_ueber_garten_static.md",
         "über + dative — cloud is above the garden (static location)",
         ("über dem Garten", "above", "garden"),
         "Core German sentence: Die Wolke ist über dem Garten. "
         "Static location above. "
         "Japanese cue: 庭の上に. Chinese cue: 在花園上方. "
         "Use only static verbs: is, floats, hangs. "
         "Preferred subjects: cloud (Wolke), bird (Vogel), sun (Sonne). "
         "Vary: cloud, bird, sun, cloud again. "
         "Keep über dem Garten visible in every German line."),
        ("042_ueber_weg_static.md",
         "über + dative — bridge is above the path (static location)",
         ("über dem Weg", "above", "path"),
         "Core German sentence: Die Brücke ist über dem Weg. "
         "Static location above: the bridge is over the path. "
         "Japanese cue: 道の上に. Chinese cue: 在小路上方. "
         "Use only static verbs: is, stands, arches. "
         "Preferred subjects: bridge (Brücke), bird (Vogel), cloud (Wolke). "
         "Vary: bridge, bird, cloud, bridge again. "
         "Keep über dem Weg visible in every German line."),
        ("043_ueber_berg_b_static.md",
         "über + dative — sun is above the mountain (static, second mountain file)",
         ("über dem Berg", "above", "mountain"),
         "Core German sentence: Die Sonne ist über dem Berg. "
         "Static location above the mountain. "
         "Japanese cue: 山の上に. Chinese cue: 在山上方. "
         "Use only static verbs: is, shines, hangs. "
         "Preferred subjects: sun (Sonne), bird (Vogel), cloud (Wolke). "
         "Vary: sun, bird, cloud, sun again. "
         "Keep über dem Berg visible in every German line."),
        ("044_ueber_tisch_b_static.md",
         "über + dative — bird is above the table (static, second table file)",
         ("über dem Tisch", "above", "table"),
         "Core German sentence: Der Vogel ist über dem Tisch. "
         "Static location above. "
         "Japanese cue: テーブルの上に. Chinese cue: 在桌子上方. "
         "Use only static verbs: is, flies, hovers. "
         "Preferred subjects: bird (Vogel), lamp (Lampe), cloud (Wolke). "
         "Vary: bird, lamp, cloud, bird again. "
         "Keep über dem Tisch visible in every German line."),
        ("045_ueber_tuer_b_static.md",
         "über + dative — clock is above the door (static, second door file)",
         ("über der Tür", "above", "door"),
         "Core German sentence: Die Uhr ist über der Tür. "
         "Static location above the door. "
         "Japanese cue: ドアの上に. Chinese cue: 在門上方. "
         "Use only static verbs: is, hangs. "
         "Preferred subjects: clock (Uhr), sign (Schild), lamp (Lampe). "
         "Vary: clock, sign, lamp, clock again. "
         "Keep über der Tür visible in every German line."),
        # ── More unter entries (046-052) ──
        ("046_unter_stuhl_static.md",
         "unter + dative — cat is under the chair (static location)",
         ("unter dem Stuhl", "under", "chair"),
         "Core German sentence: Die Katze ist unter dem Stuhl. "
         "Static location below the chair. "
         "Japanese cue: 椅子の下に. Chinese cue: 在椅子下面. "
         "Use only static verbs: is, lies, sits, sleeps. "
         "Vary the subject: cat, dog, ball, bag. Use Katze, Hund. "
         "Keep unter dem Stuhl visible in every German line."),
        ("047_unter_regal_static.md",
         "unter + dative — bag is under the shelf (static location)",
         ("unter dem Regal", "under", "shelf"),
         "Core German sentence: Die Tasche ist unter dem Regal. "
         "Static location below the shelf. "
         "Japanese cue: 棚の下に. Chinese cue: 在架子下面. "
         "Use only static verbs: is, lies, sits. "
         "Vary the subject: bag, ball, book, blanket. "
         "Keep unter dem Regal visible in every German line."),
        ("048_unter_boden_static.md",
         "unter + dative — something is under the floor (static location below)",
         ("unter dem Boden", "under", "floor"),
         "Core German sentence: Der Ball ist unter dem Boden. "
         "Static location below the floor (through a crack or gap). "
         "Japanese cue: 床の下に. Chinese cue: 在地板下面. "
         "Use only static verbs: is, lies. "
         "Vary the subject: ball, bag, book, blanket. "
         "Keep unter dem Boden visible in every German line."),
        ("049_unter_bank_b_static.md",
         "unter + dative — dog is under the bench (static, second bench file)",
         ("unter der Bank", "under", "bench"),
         "Core German sentence: Der Hund ist unter der Bank. "
         "Static location below the bench. "
         "Japanese cue: ベンチの下に. Chinese cue: 在長椅下面. "
         "Use only static verbs: is, lies, sits, sleeps. "
         "Vary the subject: dog, cat, ball, blanket. Use Hund, Katze. "
         "Keep unter der Bank visible in every German line."),
        ("050_unter_tisch_b_static.md",
         "unter + dative — cat is under the table (static, second table file)",
         ("unter dem Tisch", "under", "table"),
         "Core German sentence: Die Katze ist unter dem Tisch. "
         "Static location below the table. "
         "Japanese cue: テーブルの下に. Chinese cue: 在桌子下面. "
         "Use only static verbs: is, lies, sits, sleeps. "
         "Vary the subject: cat, dog, ball, bag. Use Katze, Hund. "
         "Keep unter dem Tisch visible in every German line."),
        ("051_unter_baum_b_static.md",
         "unter + dative — girl is under the tree (static, animate subject)",
         ("unter dem Baum", "under", "tree"),
         "Core German sentence: Das Mädchen ist unter dem Baum. "
         "Static location: the girl is resting under the tree. "
         "Japanese cue: 木の下に. Chinese cue: 在樹下. "
         "Use only static verbs: is, sits, lies, stands. "
         "Animate subjects: girl (Mädchen), boy (Junge), dog (Hund). "
         "Vary: girl, boy, dog, bench. "
         "Keep unter dem Baum visible in every German line."),
        ("052_unter_dach_static.md",
         "unter + dative — bench is under the roof (static location)",
         ("unter dem Dach", "under", "roof"),
         "Core German sentence: Die Bank ist unter dem Dach. "
         "Static location below/under the roof (sheltered area). "
         "Japanese cue: 屋根の下に. Chinese cue: 在屋頂下. "
         "Use only static verbs: is, sits, stands. "
         "Vary the subject: bench, ball, bag, blanket. "
         "Keep unter dem Dach visible in every German line."),
        # ── More neben entries (053-059) ──
        ("053_neben_tisch_static.md",
         "neben + dative — bag is next to the table (static location)",
         ("neben dem Tisch", "next to", "table"),
         "Core German sentence: Die Tasche ist neben dem Tisch. "
         "Static location next to the table. "
         "Japanese cue: テーブルの隣に. Chinese cue: 在桌子旁邊. "
         "Use only static verbs: is, sits, stands. "
         "Vary the subject: bag, ball, book, basket. "
         "Keep neben dem Tisch visible in every German line."),
        ("054_neben_tuer_static.md",
         "neben + dative — man is next to the door (static location, animate)",
         ("neben der Tür", "next to", "door"),
         "Core German sentence: Der Mann ist neben der Tür. "
         "Static location next to the door. "
         "Japanese cue: ドアの隣に. Chinese cue: 在門旁邊. "
         "Use only static verbs: is, sits, stands. "
         "Animate subjects: man (Mann), woman (Frau), boy (Junge). "
         "Vary: man, woman, boy, dog. Use Mann, Frau, Junge, Hund. "
         "Keep neben der Tür visible in every German line."),
        ("055_neben_stuhl_static.md",
         "neben + dative — ball is next to the chair (static location)",
         ("neben dem Stuhl", "next to", "chair"),
         "Core German sentence: Der Ball ist neben dem Stuhl. "
         "Static location next to the chair. "
         "Japanese cue: 椅子の隣に. Chinese cue: 在椅子旁邊. "
         "Use only static verbs: is, lies, sits. "
         "Vary the subject: ball, bag, book, apple. "
         "Keep neben dem Stuhl visible in every German line."),
        ("056_neben_garten_static.md",
         "neben + dative — school is next to the garden (static location)",
         ("neben dem Garten", "next to", "garden"),
         "Core German sentence: Die Schule ist neben dem Garten. "
         "Static location next to the garden. "
         "Japanese cue: 庭の隣に. Chinese cue: 在花園旁邊. "
         "Use only static verbs: is, sits, stands. "
         "Vary the subject: school, house, bench, tree. Use Schule, Haus, Bank, Baum. "
         "Keep neben dem Garten visible in every German line."),
        ("057_neben_regal_static.md",
         "neben + dative — chair is next to the shelf (static location)",
         ("neben dem Regal", "next to", "shelf"),
         "Core German sentence: Der Stuhl ist neben dem Regal. "
         "Static location next to the shelf. "
         "Japanese cue: 棚の隣に. Chinese cue: 在架子旁邊. "
         "Use only static verbs: is, sits, stands. "
         "Vary the subject: chair, bag, ball, basket. "
         "Keep neben dem Regal visible in every German line."),
        ("058_neben_kueche_static.md",
         "neben + dative — room is next to the kitchen (static location)",
         ("neben der Küche", "next to", "kitchen"),
         "Core German sentence: Das Zimmer ist neben der Küche. "
         "Static location next to the kitchen. "
         "Japanese cue: 台所の隣に. Chinese cue: 在廚房旁邊. "
         "Use only static verbs: is, sits, stands. "
         "Vary the subject: room, garden, bench, tree. Use Zimmer, Garten, Bank, Baum. "
         "Keep neben der Küche visible in every German line."),
        ("059_neben_baum_b_static.md",
         "neben + dative — dog is next to the tree (static, second tree file)",
         ("neben dem Baum", "next to", "tree"),
         "Core German sentence: Der Hund ist neben dem Baum. "
         "Static location next to the tree. "
         "Japanese cue: 木の隣に. Chinese cue: 在樹旁邊. "
         "Use only static verbs: is, sits, lies. "
         "Vary the subject: dog, cat, ball, boy. Use Hund, Katze, Junge. "
         "Keep neben dem Baum visible in every German line."),
        # ── More vor entries (060-066) ──
        ("060_vor_baum_static.md",
         "vor + dative — girl is in front of the tree (static location)",
         ("vor dem Baum", "in front of", "tree"),
         "Core German sentence: Das Mädchen ist vor dem Baum. "
         "Static location in front of the tree. "
         "Japanese cue: 木の前に. Chinese cue: 在樹前面. "
         "Use only static verbs: is, sits, stands. "
         "Vary the subject: girl, boy, dog, bench. Use Mädchen, Junge, Hund, Bank. "
         "Keep vor dem Baum visible in every German line."),
        ("061_vor_garten_static.md",
         "vor + dative — dog is in front of the garden (static location)",
         ("vor dem Garten", "in front of", "garden"),
         "Core German sentence: Der Hund ist vor dem Garten. "
         "Static location in front of the garden. "
         "Japanese cue: 庭の前に. Chinese cue: 在花園前面. "
         "Use only static verbs: is, sits, stands. "
         "Vary the subject: dog, boy, bench, ball. Use Hund, Junge, Bank. "
         "Keep vor dem Garten visible in every German line."),
        ("062_vor_regal_static.md",
         "vor + dative — bag is in front of the shelf (static location)",
         ("vor dem Regal", "in front of", "shelf"),
         "Core German sentence: Die Tasche ist vor dem Regal. "
         "Static location in front of the shelf. "
         "Japanese cue: 棚の前に. Chinese cue: 在架子前面. "
         "Use only static verbs: is, sits, stands. "
         "Vary the subject: bag, ball, book, basket. "
         "Keep vor dem Regal visible in every German line."),
        ("063_vor_bank_static.md",
         "vor + dative — ball is in front of the bench (static location)",
         ("vor der Bank", "in front of", "bench"),
         "Core German sentence: Der Ball ist vor der Bank. "
         "Static location in front of the bench. "
         "Japanese cue: ベンチの前に. Chinese cue: 在長椅前面. "
         "Use only static verbs: is, lies, sits. "
         "Vary the subject: ball, bag, apple, book. "
         "Keep vor der Bank visible in every German line."),
        ("064_vor_stuhl_static.md",
         "vor + dative — cat is in front of the chair (static location)",
         ("vor dem Stuhl", "in front of", "chair"),
         "Core German sentence: Die Katze ist vor dem Stuhl. "
         "Static location in front of the chair. "
         "Japanese cue: 椅子の前に. Chinese cue: 在椅子前面. "
         "Use only static verbs: is, sits, lies. "
         "Vary the subject: cat, dog, ball, bag. Use Katze, Hund. "
         "Keep vor dem Stuhl visible in every German line."),
        ("065_vor_park_static.md",
         "vor + dative — woman is in front of the park (static location)",
         ("vor dem Park", "in front of", "park"),
         "Core German sentence: Die Frau ist vor dem Park. "
         "Static location in front of the park. "
         "Japanese cue: 公園の前に. Chinese cue: 在公園前面. "
         "Use only static verbs: is, sits, stands. "
         "Vary the subject: woman, man, boy, dog. Use Frau, Mann, Junge, Hund. "
         "Keep vor dem Park visible in every German line."),
        ("066_vor_haus_b_static.md",
         "vor + dative — bench is in front of the house (static, second house file)",
         ("vor dem Haus", "in front of", "house"),
         "Core German sentence: Die Bank ist vor dem Haus. "
         "Static location in front of the house. "
         "Japanese cue: 家の前に. Chinese cue: 在房子前面. "
         "Use only static verbs: is, sits, stands. "
         "Vary the subject: bench, ball, bag, tree. Use Bank, Ball, Baum. "
         "Keep vor dem Haus visible in every German line."),
        # ── More hinter entries (067-073) ──
        ("067_hinter_stuhl_static.md",
         "hinter + dative — ball is behind the chair (static location)",
         ("hinter dem Stuhl", "behind", "chair"),
         "Core German sentence: Der Ball ist hinter dem Stuhl. "
         "Static location behind the chair. "
         "Japanese cue: 椅子の後ろに. Chinese cue: 在椅子後面. "
         "Use only static verbs: is, lies, sits. "
         "Vary the subject: ball, bag, book, blanket. "
         "Keep hinter dem Stuhl visible in every German line."),
        ("068_hinter_regal_static.md",
         "hinter + dative — cat is behind the shelf (static location)",
         ("hinter dem Regal", "behind", "shelf"),
         "Core German sentence: Die Katze ist hinter dem Regal. "
         "Static location behind the shelf. "
         "Japanese cue: 棚の後ろに. Chinese cue: 在架子後面. "
         "Use only static verbs: is, sits, lies, hides. "
         "Vary the subject: cat, dog, ball, bag. Use Katze, Hund. "
         "Keep hinter dem Regal visible in every German line."),
        ("069_hinter_bank_static.md",
         "hinter + dative — dog is behind the bench (static location)",
         ("hinter der Bank", "behind", "bench"),
         "Core German sentence: Der Hund ist hinter der Bank. "
         "Static location behind the bench. "
         "Japanese cue: ベンチの後ろに. Chinese cue: 在長椅後面. "
         "Use only static verbs: is, sits, lies. "
         "Vary the subject: dog, cat, ball, boy. Use Hund, Katze, Junge. "
         "Keep hinter der Bank visible in every German line."),
        ("070_hinter_baum_b_static.md",
         "hinter + dative — ball is behind the tree (static, second tree file)",
         ("hinter dem Baum", "behind", "tree"),
         "Core German sentence: Der Ball ist hinter dem Baum. "
         "Static location behind the tree. "
         "Japanese cue: 木の後ろに. Chinese cue: 在樹後面. "
         "Use only static verbs: is, lies, sits. "
         "Vary the subject: ball, bag, book, blanket. "
         "Keep hinter dem Baum visible in every German line."),
        ("071_hinter_haus_b_static.md",
         "hinter + dative — garden is behind the house (static, second house file)",
         ("hinter dem Haus", "behind", "house"),
         "Core German sentence: Der Garten ist hinter dem Haus. "
         "Static location behind the house. "
         "Japanese cue: 家の後ろに. Chinese cue: 在房子後面. "
         "Use only static verbs: is, sits, lies, stands. "
         "Vary the subject: garden, bench, tree, ball. Use Garten, Bank, Baum. "
         "Keep hinter dem Haus visible in every German line."),
        ("072_hinter_tuer_b_static.md",
         "hinter + dative — cat is behind the door (static, second door file)",
         ("hinter der Tür", "behind", "door"),
         "Core German sentence: Die Katze ist hinter der Tür. "
         "Static location behind the door. "
         "Japanese cue: ドアの後ろに. Chinese cue: 在門後面. "
         "Use only static verbs: is, sits, lies, hides. "
         "Vary the subject: cat, dog, ball, bag. Use Katze, Hund. "
         "Keep hinter der Tür visible in every German line."),
        ("073_hinter_garten_static.md",
         "hinter + dative — bench is behind the garden (static location)",
         ("hinter dem Garten", "behind", "garden"),
         "Core German sentence: Die Bank ist hinter dem Garten. "
         "Static location behind the garden. "
         "Japanese cue: 庭の後ろに. Chinese cue: 在花園後面. "
         "Use only static verbs: is, sits, stands. "
         "Vary the subject: bench, tree, ball, bag. Use Bank, Baum. "
         "Keep hinter dem Garten visible in every German line."),
        # ── More zwischen entries (074-080) ──
        ("074_zwischen_haeusern_static.md",
         "zwischen + dative — garden is between the houses (static location)",
         ("zwischen den Häusern", "between", "houses"),
         "Core German sentence: Der Garten ist zwischen den Häusern. "
         "Static location between the houses. "
         "zwischen takes dative plural: den Häusern. "
         "Japanese cue: 家々の間に. Chinese cue: 在房子之間. "
         "Use only static verbs: is, sits, stands. "
         "Vary the subject: garden, bench, tree, ball. "
         "Keep zwischen den Häusern visible in every German line."),
        ("075_zwischen_koerben_static.md",
         "zwischen + dative — apple is between the baskets (static location)",
         ("zwischen den Körben", "between", "baskets"),
         "Core German sentence: Der Apfel ist zwischen den Körben. "
         "Static location between the baskets. "
         "zwischen takes dative plural: den Körben. "
         "Japanese cue: かごの間に. Chinese cue: 在籃子之間. "
         "Use only static verbs: is, lies, sits. "
         "Vary the subject: apple, ball, book, blanket. "
         "Keep zwischen den Körben visible in every German line."),
        ("076_zwischen_tisch_stuhl_static.md",
         "zwischen + dative — bag is between the table and the chair (static location)",
         ("zwischen dem Tisch", "between", "table"),
         "Core German sentence: Die Tasche ist zwischen dem Tisch und dem Stuhl. "
         "Static location between two pieces of furniture. "
         "zwischen takes dative: zwischen dem Tisch und dem Stuhl. "
         "Japanese cue: テーブルと椅子の間に. Chinese cue: 在桌子和椅子之間. "
         "Use only static verbs: is, lies, sits. "
         "Vary the subject: bag, ball, book, apple. "
         "Keep zwischen dem Tisch und dem Stuhl visible in every German line."),
        ("077_zwischen_baum_haus_static.md",
         "zwischen + dative — bench is between the tree and the house (static location)",
         ("zwischen dem Baum", "between", "tree"),
         "Core German sentence: Die Bank ist zwischen dem Baum und dem Haus. "
         "Static location between tree and house. "
         "zwischen takes dative: zwischen dem Baum und dem Haus. "
         "Japanese cue: 木と家の間に. Chinese cue: 在樹和房子之間. "
         "Use only static verbs: is, sits, stands. "
         "Vary the subject: bench, ball, dog, bag. "
         "Keep zwischen dem Baum und dem Haus visible in every German line."),
        ("078_zwischen_baeumen_b_static.md",
         "zwischen + dative — dog is between the trees (static, second trees file)",
         ("zwischen den Bäumen", "between", "trees"),
         "Core German sentence: Der Hund ist zwischen den Bäumen. "
         "Static location between the trees. "
         "zwischen takes dative plural: den Bäumen. "
         "Japanese cue: 木の間に. Chinese cue: 在樹木之間. "
         "Use only static verbs: is, sits, lies. "
         "Vary the subject: dog, cat, ball, boy. Use Hund, Katze, Junge. "
         "Keep zwischen den Bäumen visible in every German line."),
        ("079_zwischen_tischen_static.md",
         "zwischen + dative — ball is between the tables (static location)",
         ("zwischen den Tischen", "between", "tables"),
         "Core German sentence: Der Ball ist zwischen den Tischen. "
         "Static location between the tables. "
         "zwischen takes dative plural: den Tischen. "
         "Japanese cue: テーブルの間に. Chinese cue: 在桌子之間. "
         "Use only static verbs: is, lies, sits. "
         "Vary the subject: ball, bag, book, apple. "
         "Keep zwischen den Tischen visible in every German line."),
        ("080_zwischen_stuehlen_b_static.md",
         "zwischen + dative — dog is between the chairs (static, second chairs file)",
         ("zwischen den Stühlen", "between", "chairs"),
         "Core German sentence: Der Hund ist zwischen den Stühlen. "
         "Static location between the chairs. "
         "zwischen takes dative plural: den Stühlen. "
         "Japanese cue: 椅子の間に. Chinese cue: 在椅子之間. "
         "Use only static verbs: is, lies, sits. "
         "Vary the subject: dog, cat, ball, blanket. Use Hund, Katze. "
         "Keep zwischen den Stühlen visible in every German line."),
        # ── Wo? question form files (081-090) ──
        ("081_wo_becher_static.md",
         "Wo? question — Wo ist der Becher? (auf dem Tisch)",
         ("Wo", "auf dem Tisch"),
         "Question form: Wo ist der Becher? Answer: auf dem Tisch. "
         "4 pairs: vary the location for each pair using auf/in/unter/neben. "
         "Keep the Wo? question form visible in every pair."),
        ("082_wo_ball_static.md",
         "Wo? question — Wo ist der Ball? (unter der Bank)",
         ("Wo", "unter der Bank"),
         "Question form: Wo ist der Ball? Answer: unter der Bank. "
         "4 pairs: vary the location using unter/hinter/neben/zwischen. "
         "Keep the Wo? question form visible."),
        ("083_wo_katze_static.md",
         "Wo? question — Wo ist die Katze? (hinter dem Baum, animate subject)",
         ("Wo", "hinter dem Baum"),
         "Question form: Wo ist die Katze? Answer: hinter dem Baum. "
         "Animate subject: use にいる in Japanese. "
         "4 pairs: vary the location. "
         "Keep the Wo? question form visible."),
        ("084_wo_buch_static.md",
         "Wo? question — Wo ist das Buch? (in dem Regal)",
         ("Wo", "in dem Regal"),
         "Question form: Wo ist das Buch? Answer: in dem Regal. "
         "4 pairs: vary the location using in/auf/unter/neben. "
         "Keep the Wo? question form visible."),
        ("085_wo_hund_static.md",
         "Wo? question — Wo ist der Hund? (vor dem Haus, animate)",
         ("Wo", "vor dem Haus"),
         "Question form: Wo ist der Hund? Answer: vor dem Haus. "
         "Animate subject: use にいる in Japanese. "
         "4 pairs: vary the location using vor/hinter/neben/zwischen. "
         "Keep the Wo? question form visible."),
        ("086_wo_decke_static.md",
         "Wo? question — Wo ist die Decke? (auf dem Boden)",
         ("Wo", "auf dem Boden"),
         "Question form: Wo ist die Decke? Answer: auf dem Boden. "
         "4 pairs: vary the location. "
         "Keep the Wo? question form visible."),
        ("087_wo_junge_static.md",
         "Wo? question — Wo ist der Junge? (neben dem Baum, animate)",
         ("Wo", "neben dem Baum"),
         "Question form: Wo ist der Junge? Answer: neben dem Baum. "
         "Animate subject: use にいる in Japanese. "
         "4 pairs: vary the location. "
         "Keep the Wo? question form visible."),
        ("088_wo_lampe_static.md",
         "Wo? question — Wo ist die Lampe? (über dem Tisch)",
         ("Wo", "über dem Tisch"),
         "Question form: Wo ist die Lampe? Answer: über dem Tisch. "
         "4 pairs: vary the location using über/auf/in/neben. "
         "Keep the Wo? question form visible."),
        ("089_wo_maedchen_static.md",
         "Wo? question — Wo ist das Mädchen? (zwischen den Stühlen, animate)",
         ("Wo", "zwischen den Stühlen"),
         "Question form: Wo ist das Mädchen? Answer: zwischen den Stühlen. "
         "Animate subject: use にいる in Japanese. "
         "4 pairs: vary the location. "
         "Keep the Wo? question form visible."),
        ("090_wo_apfel_static.md",
         "Wo? question — Wo ist der Apfel? (in dem Korb)",
         ("Wo", "in dem Korb"),
         "Question form: Wo ist der Apfel? Answer: in dem Korb. "
         "4 pairs: vary the location. "
         "Keep the Wo? question form visible."),
        # ── Mixed preposition review (091-096) ──
        ("091_mixed_auf_in.md",
         "mixed review: auf + dative vs. in + dative (on vs. in)",
         ("auf dem Tisch", "in der Küche"),
         "Contrast: Der Becher ist auf dem Tisch (on). Das Buch ist in der Küche (in). "
         "4 pairs alternating auf and in with different objects. "
         "Keep the preposition and dative article visible in every pair."),
        ("092_mixed_unter_ueber.md",
         "mixed review: unter + dative vs. über + dative (under vs. above)",
         ("unter dem Tisch", "über dem Tisch"),
         "Contrast: Die Katze ist unter dem Tisch (under). Die Lampe ist über dem Tisch (above). "
         "4 pairs alternating unter and über. "
         "Keep the preposition and dative article visible."),
        ("093_mixed_vor_hinter.md",
         "mixed review: vor + dative vs. hinter + dative (in front of vs. behind)",
         ("vor dem Haus", "hinter dem Haus"),
         "Contrast: Der Hund ist vor dem Haus (in front of). Die Katze ist hinter dem Haus (behind). "
         "4 pairs alternating vor and hinter. "
         "Keep the preposition and dative article visible."),
        ("094_mixed_neben_zwischen.md",
         "mixed review: neben + dative vs. zwischen + dative (next to vs. between)",
         ("neben dem Baum", "zwischen den Bäumen"),
         "Contrast: Der Ball ist neben dem Baum (next to). Das Buch ist zwischen den Bäumen (between). "
         "4 pairs alternating neben and zwischen. "
         "Keep the preposition and dative article visible."),
        ("095_mixed_four_preps.md",
         "mixed review: auf/in/unter/neben — four objects, four places",
         ("auf dem Tisch", "in dem Korb"),
         "Scene: Pair 1: auf. Pair 2: in. Pair 3: unter. Pair 4: neben. "
         "One object per preposition; vary the objects and locations. "
         "Keep all dative forms explicit."),
        ("096_mixed_scene_emma_room.md",
         "mixed scene: Emma's room — multiple objects in different static places",
         ("auf dem Tisch", "neben dem Stuhl"),
         "Scene: Das Buch ist auf dem Tisch. Die Tasche ist neben dem Stuhl. "
         "Die Katze ist unter dem Bett — use unter dem Tisch instead of Bett. "
         "Der Becher ist auf dem Regal. "
         "4 pairs, each placing a different object in Emma's room. "
         "Use only static verbs and dative prepositions."),
        # ── Full scene review (097-100) ──
        ("097_scene_gran_garden.md",
         "scene review: Gran's garden — animate and inanimate in multiple places",
         ("in dem Garten", "vor dem Haus"),
         "Scene: Der Hund ist in dem Garten. Die Bank ist vor dem Haus. "
         "Der Ball ist neben der Bank. Gran ist unter dem Baum. "
         "4 pairs; each describes an object or character in a static place. "
         "Use にある / にいる correctly for Japanese."),
        ("098_final_review_all_preps_a.md",
         "final review A: all 8 prepositions — one per pair, cycling",
         ("auf dem Tisch", "in dem Korb"),
         "Each of the 4 pairs uses a different preposition: auf, in, über, unter. "
         "Keep dative article visible in every German line. "
         "Use familiar objects and locations. "
         "Use Wo? question form for at least 2 pairs."),
        ("099_final_review_all_preps_b.md",
         "final review B: remaining 4 prepositions — neben, vor, hinter, zwischen",
         ("neben dem Baum", "vor dem Haus"),
         "Each of the 4 pairs uses a different preposition: neben, vor, hinter, zwischen. "
         "Keep dative article visible in every German line. "
         "Use familiar objects and animate/inanimate subjects. "
         "Use Wo? question form for at least 2 pairs."),
        ("100_final_review_mixed.md",
         "final comprehensive review: all 8 static prepositions in one complete scene",
         ("auf dem Tisch", "zwischen den Stühlen"),
         "Comprehensive review of all 8 two-way prepositions in static (dative) use. "
         "Pair 1: auf + in. Pair 2: über + unter. Pair 3: vor + hinter. Pair 4: neben + zwischen. "
         "Keep dative article explicit in every line. "
         "Use Wo? question form. Mix animate and inanimate subjects. "
         "Use にある / にいる correctly for Japanese."),
    ]

    shared_suffix = (
        " Static location only — do not use movement-onto, movement-into, or movement-toward patterns. "
        "The German preposition must appear with a dative article (dem, der, or den for plural). "
        "Do not switch from dative to accusative. "
        "JP cross-cue: use にある for inanimate subjects and にいる for animate subjects. "
        "ZH cross-cue: 在…上/下/中/前/後/旁/間 as appropriate. "
        "Keep vocabulary simple and concrete."
    )

    return [
        FileSpec(
            path=f"03_place_static_dative/{filename}",
            focus=focus,
            required_terms=required,
            notes=notes + shared_suffix,
        )
        for filename, focus, required, notes in rows
    ]


def make_object_accusative_specs() -> list[FileSpec]:
    """Specs for `05_object_accusative_patient`: plain transitive verbs with visible accusative object."""
    rows: list[tuple[str, str, tuple[str, ...], str]] = [
        # ── Perception / discovery ─────────────────────────────────────────────
        ("001_see.md",
         "sehen — Emma sieht den Hund (plain transitive: sees the object)",
         ("sieht", "den Hund"),
         "Core German sentence: Emma sieht den Hund. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/den Hund (masc), pair 2 Taro/die Katze (fem), pair 3 Gran/den Vogel (masc), pair 4 das Kind/das Kaninchen (neut). "
         "Japanese cue: 〜を見る (犬を見る). Chinese cue: 看見, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("002_find.md",
         "finden — Taro findet den Ball (plain transitive: finds the object)",
         ("findet", "den Ball"),
         "Core German sentence: Taro findet den Ball. "
         "Vary the agent and object across 4 pairs: "
         "pair 1 Taro/den Ball (masc), pair 2 Emma/den Bleistift (masc), pair 3 Gran/das Buch (neut), pair 4 der Junge/den Korb (masc). "
         "Japanese cue: 〜を見つける (ボールを見つける). Chinese cue: 找到, SVO order. "
         "Keep the German accusative article (den/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("003_call.md",
         "rufen — Gran ruft den Hund (plain transitive: calls the being)",
         ("ruft", "den Hund"),
         "Core German sentence: Gran ruft den Hund. "
         "Vary the agent and object across 4 pairs: "
         "pair 1 Gran/den Hund (masc), pair 2 Emma/das Kind (neut), pair 3 Taro/den Jungen (masc, weak noun: den Jungen), pair 4 die Frau/das Mädchen (neut). "
         "Japanese cue: 〜を呼ぶ (犬を呼ぶ). Chinese cue: 叫/呼叫, SVO order. "
         "Keep the German accusative article (den/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── Carrying / moving objects ──────────────────────────────────────────
        ("004_carry.md",
         "tragen — Taro trägt den Korb (plain transitive: carries the object)",
         ("trägt", "den Korb"),
         "Core German sentence: Taro trägt den Korb. "
         "Vary the agent and object across 4 pairs: "
         "pair 1 Taro/den Korb (masc), pair 2 Emma/den Eimer (masc), pair 3 Gran/das Buch (neut), pair 4 der Mann/die Tasche (fem). "
         "Japanese cue: 〜を運ぶ / 持つ (かごを運ぶ). Chinese cue: 搬/提, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("005_take.md",
         "nehmen — Gran nimmt den Apfel (plain transitive: takes the object)",
         ("nimmt", "den Apfel"),
         "Core German sentence: Gran nimmt den Apfel. "
         "Vary the agent and object across 4 pairs: "
         "pair 1 Gran/den Apfel (masc), pair 2 Taro/das Buch (neut), pair 3 Emma/den Ball (masc), pair 4 der Junge/den Becher (masc). "
         "Japanese cue: 〜を取る (りんごを取る). Chinese cue: 拿, SVO order. "
         "Keep the German accusative article (den/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("006_hold.md",
         "halten — Emma hält den Korb (plain transitive: holds the object)",
         ("hält", "den Korb"),
         "Core German sentence: Emma hält den Korb. "
         "Vary the agent and object across 4 pairs: "
         "pair 1 Emma/den Korb (masc), pair 2 Taro/den Ball (masc), pair 3 Gran/den Becher (masc), pair 4 das Kind/die Decke (fem). "
         "Japanese cue: 〜を持つ (かごを持つ). Chinese cue: 拿著/握住, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        # ── Object manipulation ────────────────────────────────────────────────
        ("007_open.md",
         "öffnen — Emma öffnet die Tür (plain transitive: opens the object)",
         ("öffnet", "die Tür"),
         "Core German sentence: Emma öffnet die Tür. "
         "Vary the agent and object across 4 pairs: "
         "pair 1 Emma/die Tür (fem), pair 2 Taro/das Fenster (neut), pair 3 Gran/die Tasche (fem), pair 4 der Junge/die Kiste (fem). "
         "Japanese cue: 〜を開ける (ドアを開ける). Chinese cue: 打開, SVO order. "
         "Keep the German accusative article (die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("008_wash.md",
         "waschen — Taro wäscht den Becher (plain transitive: washes the object)",
         ("wäscht", "den Becher"),
         "Core German sentence: Taro wäscht den Becher. "
         "Vary the agent and object across 4 pairs: "
         "pair 1 Taro/den Becher (masc), pair 2 Gran/den Ball (masc), pair 3 Emma/die Schüssel (fem), pair 4 die Frau/die Tasche (fem). "
         "Japanese cue: 〜を洗う (コップを洗う). Chinese cue: 洗, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        ("009_cut.md",
         "schneiden — Gran schneidet den Apfel (plain transitive: cuts the object)",
         ("schneidet", "den Apfel"),
         "Core German sentence: Gran schneidet den Apfel. "
         "Vary the agent and object across 4 pairs: "
         "pair 1 Gran/den Apfel (masc), pair 2 Emma/das Brot (neut), pair 3 Taro/den Fisch (masc), pair 4 die Frau/das Brot (neut). "
         "Japanese cue: 〜を切る (りんごを切る). Chinese cue: 切, SVO order. "
         "Keep the German accusative article (den/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── Food and consumption ───────────────────────────────────────────────
        ("010_eat.md",
         "essen — das Kind isst den Apfel (plain transitive: eats the food)",
         ("isst", "den Apfel"),
         "Core German sentence: Das Kind isst den Apfel. "
         "Vary the agent and object across 4 pairs: "
         "pair 1 das Kind/den Apfel (masc), pair 2 Emma/das Brot (neut), pair 3 Taro/den Apfel (masc), pair 4 Gran/das Brot (neut). "
         "Japanese cue: 〜を食べる (りんごを食べる). Chinese cue: 吃, SVO order. "
         "Keep the German accusative article (den/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("011_buy.md",
         "kaufen — Emma kauft den Apfel (plain transitive: buys the object)",
         ("kauft", "den Apfel"),
         "Core German sentence: Emma kauft den Apfel. "
         "Vary the agent and object across 4 pairs: "
         "pair 1 Emma/den Apfel (masc), pair 2 Taro/das Brot (neut), pair 3 Gran/den Becher (masc), pair 4 die Frau/den Korb (masc). "
         "Japanese cue: 〜を買う (りんごを買う). Chinese cue: 買, SVO order. "
         "Keep the German accusative article (den/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── Learning and creation ──────────────────────────────────────────────
        ("012_read.md",
         "lesen — Taro liest das Buch (plain transitive: reads the object)",
         ("liest", "das Buch"),
         "Core German sentence: Taro liest das Buch. "
         "Vary the agent across 4 pairs; keep neuter accusative object: "
         "pair 1 Taro/das Buch (neut), pair 2 Emma/das Buch (neut), pair 3 Gran/das Dokument (neut), pair 4 das Kind/das Buch (neut). "
         "Japanese cue: 〜を読む (本を読む). Chinese cue: 讀/看, SVO order. "
         "Keep the German accusative article das visible in every German line. "
         "Do not add a dative receiver."),
        ("013_write.md",
         "schreiben — Emma schreibt das Dokument (plain transitive: writes the object)",
         ("schreibt", "das Dokument"),
         "Core German sentence: Emma schreibt das Dokument. "
         "Vary the agent and object across 4 pairs: "
         "pair 1 Emma/das Dokument (neut), pair 2 Taro/das Buch (neut), pair 3 Gran/das Dokument (neut), pair 4 der Lehrer/das Dokument (neut). "
         "Japanese cue: 〜を書く (書類を書く). Chinese cue: 寫, SVO order. "
         "Keep the German accusative article das visible in every German line. "
         "Do not add a dative receiver."),
        ("014_draw.md",
         "malen — Gran malt den Baum (plain transitive: draws the object)",
         ("malt", "den Baum"),
         "Core German sentence: Gran malt den Baum. "
         "Vary the agent and object across 4 pairs: "
         "pair 1 Gran/den Baum (masc), pair 2 Emma/das Haus (neut), pair 3 Taro/den Hund (masc), pair 4 das Kind/den Ball (masc). "
         "Japanese cue: 〜を描く (木を描く). Chinese cue: 畫, SVO order. "
         "Keep the German accusative article (den/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── Action verbs ───────────────────────────────────────────────────────
        ("015_need.md",
         "brauchen — Emma braucht den Bleistift (plain transitive: needs the object)",
         ("braucht", "den Bleistift"),
         "Core German sentence: Emma braucht den Bleistift. "
         "Vary the agent and object across 4 pairs: "
         "pair 1 Emma/den Bleistift (masc), pair 2 Taro/das Buch (neut), pair 3 Gran/den Becher (masc), pair 4 der Junge/den Besen (masc). "
         "Japanese cue: 〜が必要だ / 〜を必要とする (鉛筆が必要だ). Chinese cue: 需要, SVO order. "
         "Keep the German accusative article (den/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("016_throw.md",
         "werfen — das Kind wirft den Ball (plain transitive: throws the object)",
         ("wirft", "den Ball"),
         "Core German sentence: Das Kind wirft den Ball. "
         "Vary the agent across 4 pairs; keep den Ball as the object: "
         "pair 1 das Kind/den Ball, pair 2 Taro/den Ball, pair 3 der Junge/den Ball, pair 4 Emma/den Ball. "
         "Japanese cue: 〜を投げる (ボールを投げる). Chinese cue: 丟/扔, SVO order. "
         "Keep den Ball visible in every German line. "
         "Do not add a dative receiver."),
        # ── Extensions: sehen ─────────────────────────────────────────────────
        ("017_see_b.md",
         "sehen — Gran sieht den Mann (seeing people, gender contrast)",
         ("sieht", "den Mann"),
         "Core German sentence: Gran sieht den Mann. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Gran/den Mann (masc), pair 2 Emma/die Frau (fem), "
         "pair 3 Taro/den Jungen (masc), pair 4 das Kind/das Mädchen (neut). "
         "Japanese cue: 〜を見る (男の人を見る). Chinese cue: 看見, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("018_see_c.md",
         "sehen — Emma sieht den Baum (seeing nature and objects)",
         ("sieht", "den Baum"),
         "Core German sentence: Emma sieht den Baum. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/den Baum (masc), pair 2 Taro/das Haus (neut), "
         "pair 3 Gran/den Ball (masc), pair 4 der Junge/die Blume (fem). "
         "Japanese cue: 〜を見る (木を見る). Chinese cue: 看見, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── Extensions: finden ────────────────────────────────────────────────
        ("019_find_b.md",
         "finden — Taro findet die Blume (finding outdoor things)",
         ("findet", "die Blume"),
         "Core German sentence: Taro findet die Blume. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Taro/die Blume (fem), pair 2 Emma/den Ball (masc), "
         "pair 3 Gran/das Kaninchen (neut), pair 4 der Junge/den Vogel (masc). "
         "Japanese cue: 〜を見つける (花を見つける). Chinese cue: 找到, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("020_find_c.md",
         "finden — Emma findet die Tasche (finding household items)",
         ("findet", "die Tasche"),
         "Core German sentence: Emma findet die Tasche. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/die Tasche (fem), pair 2 Taro/den Becher (masc), "
         "pair 3 Gran/das Dokument (neut), pair 4 die Frau/den Besen (masc). "
         "Japanese cue: 〜を見つける (袋を見つける). Chinese cue: 找到, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── Extensions: tragen ────────────────────────────────────────────────
        ("021_carry_b.md",
         "tragen — Gran trägt den Eimer (carrying heavy containers)",
         ("trägt", "den Eimer"),
         "Core German sentence: Gran trägt den Eimer. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Gran/den Eimer (masc), pair 2 Taro/die Kiste (fem), "
         "pair 3 Emma/die Schüssel (fem), pair 4 der Mann/den Tisch (masc). "
         "Japanese cue: 〜を運ぶ (バケツを運ぶ). Chinese cue: 搬/提, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        ("022_carry_c.md",
         "tragen — Emma trägt den Mantel (carrying lighter items)",
         ("trägt", "den Mantel"),
         "Core German sentence: Emma trägt den Mantel. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/den Mantel (masc), pair 2 Taro/die Flasche (fem), "
         "pair 3 Gran/die Decke (fem), pair 4 das Kind/den Ball (masc). "
         "Japanese cue: 〜を持つ / 運ぶ (コートを持つ). Chinese cue: 攜帶/拿, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        # ── Extensions: nehmen ────────────────────────────────────────────────
        ("023_take_b.md",
         "nehmen — Taro nimmt den Besen (taking tools)",
         ("nimmt", "den Besen"),
         "Core German sentence: Taro nimmt den Besen. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Taro/den Besen (masc), pair 2 Emma/den Bleistift (masc), "
         "pair 3 Gran/den Hammer (masc), pair 4 das Kind/den Becher (masc). "
         "Japanese cue: 〜を取る (ほうきを取る). Chinese cue: 拿, SVO order. "
         "Keep the German accusative article den visible in every German line. "
         "Do not add a dative receiver."),
        ("024_take_c.md",
         "nehmen — Gran nimmt den Fisch (taking food items)",
         ("nimmt", "den Fisch"),
         "Core German sentence: Gran nimmt den Fisch. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Gran/den Fisch (masc), pair 2 Emma/das Brot (neut), "
         "pair 3 Taro/den Kuchen (masc), pair 4 die Frau/den Apfel (masc). "
         "Japanese cue: 〜を取る (魚を取る). Chinese cue: 拿, SVO order. "
         "Keep the German accusative article (den/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── Extensions: halten ────────────────────────────────────────────────
        ("025_hold_b.md",
         "halten — Taro hält die Schüssel (holding large containers)",
         ("hält", "die Schüssel"),
         "Core German sentence: Taro hält die Schüssel. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Taro/die Schüssel (fem), pair 2 Emma/den Eimer (masc), "
         "pair 3 Gran/die Flasche (fem), pair 4 die Frau/die Tasche (fem). "
         "Japanese cue: 〜を持つ (ボウルを持つ). Chinese cue: 拿著/捧著, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        ("026_hold_c.md",
         "halten — Emma hält die Decke (holding textiles and documents)",
         ("hält", "die Decke"),
         "Core German sentence: Emma hält die Decke. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/die Decke (fem), pair 2 Taro/das Dokument (neut), "
         "pair 3 Gran/den Mantel (masc), pair 4 das Kind/die Kreide (fem). "
         "Japanese cue: 〜を持つ (毛布を持つ). Chinese cue: 拿著, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── Extensions: öffnen ────────────────────────────────────────────────
        ("027_open_b.md",
         "öffnen — Taro öffnet die Kiste (opening containers)",
         ("öffnet", "die Kiste"),
         "Core German sentence: Taro öffnet die Kiste. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Taro/die Kiste (fem), pair 2 Emma/den Korb (masc), "
         "pair 3 Gran/den Eimer (masc), pair 4 der Junge/die Flasche (fem). "
         "Japanese cue: 〜を開ける (箱を開ける). Chinese cue: 打開, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        # ── Extensions: waschen ───────────────────────────────────────────────
        ("028_wash_b.md",
         "waschen — Emma wäscht den Hund (washing animals)",
         ("wäscht", "den Hund"),
         "Core German sentence: Emma wäscht den Hund. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/den Hund (masc), pair 2 Taro/die Katze (fem), "
         "pair 3 Gran/das Kaninchen (neut), pair 4 das Kind/den Hund (masc). "
         "Japanese cue: 〜を洗う (犬を洗う). Chinese cue: 洗, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("029_wash_c.md",
         "waschen — Gran wäscht den Apfel (washing food and utensils)",
         ("wäscht", "den Apfel"),
         "Core German sentence: Gran wäscht den Apfel. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Gran/den Apfel (masc), pair 2 Emma/das Gemüse (neut), "
         "pair 3 Taro/den Fisch (masc), pair 4 die Frau/die Schüssel (fem). "
         "Japanese cue: 〜を洗う (りんごを洗う). Chinese cue: 洗, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── Extensions: schneiden ─────────────────────────────────────────────
        ("030_cut_b.md",
         "schneiden — Emma schneidet das Gemüse (cutting varied food)",
         ("schneidet", "das Gemüse"),
         "Core German sentence: Emma schneidet das Gemüse. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/das Gemüse (neut), pair 2 Taro/den Fisch (masc), "
         "pair 3 Gran/den Kuchen (masc), pair 4 die Frau/das Brot (neut). "
         "Japanese cue: 〜を切る (野菜を切る). Chinese cue: 切, SVO order. "
         "Keep the German accusative article (den/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── Extensions: essen ─────────────────────────────────────────────────
        ("031_eat_b.md",
         "essen — Taro isst den Fisch (eating varied food)",
         ("isst", "den Fisch"),
         "Core German sentence: Taro isst den Fisch. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Taro/den Fisch (masc), pair 2 Emma/das Gemüse (neut), "
         "pair 3 Gran/den Kuchen (masc), pair 4 der Junge/das Brot (neut). "
         "Japanese cue: 〜を食べる (魚を食べる). Chinese cue: 吃, SVO order. "
         "Keep the German accusative article (den/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("032_eat_c.md",
         "essen — Gran isst den Apfel (eating simple food, all agents)",
         ("isst", "den Apfel"),
         "Core German sentence: Gran isst den Apfel. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Gran/den Apfel (masc), pair 2 Emma/das Brot (neut), "
         "pair 3 Taro/den Fisch (masc), pair 4 das Kind/den Kuchen (masc). "
         "Japanese cue: 〜を食べる (りんごを食べる). Chinese cue: 吃, SVO order. "
         "Keep the German accusative article (den/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── Extensions: kaufen ────────────────────────────────────────────────
        ("033_buy_b.md",
         "kaufen — Taro kauft den Fisch (buying food items)",
         ("kauft", "den Fisch"),
         "Core German sentence: Taro kauft den Fisch. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Taro/den Fisch (masc), pair 2 Emma/das Gemüse (neut), "
         "pair 3 Gran/den Kuchen (masc), pair 4 die Frau/das Brot (neut). "
         "Japanese cue: 〜を買う (魚を買う). Chinese cue: 買, SVO order. "
         "Keep the German accusative article (den/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("034_buy_c.md",
         "kaufen — Gran kauft den Stuhl (buying furniture and tools)",
         ("kauft", "den Stuhl"),
         "Core German sentence: Gran kauft den Stuhl. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Gran/den Stuhl (masc), pair 2 Emma/den Tisch (masc), "
         "pair 3 Taro/das Fahrrad (neut), pair 4 der Mann/den Besen (masc). "
         "Japanese cue: 〜を買う (椅子を買う). Chinese cue: 買, SVO order. "
         "Keep the German accusative article (den/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── Extensions: lesen ─────────────────────────────────────────────────
        ("035_read_b.md",
         "lesen — Emma liest das Dokument (reading documents, varied agents)",
         ("liest", "das Dokument"),
         "Core German sentence: Emma liest das Dokument. "
         "Vary the agent and object across 4 pairs; keep neuter accusative: "
         "pair 1 Emma/das Dokument (neut), pair 2 Taro/das Buch (neut), "
         "pair 3 der Lehrer/das Dokument (neut), pair 4 die Frau/das Buch (neut). "
         "Japanese cue: 〜を読む (書類を読む). Chinese cue: 讀, SVO order. "
         "Keep the German accusative article das visible in every German line. "
         "Do not add a dative receiver."),
        # ── Extensions: schreiben ─────────────────────────────────────────────
        ("036_write_b.md",
         "schreiben — Taro schreibt das Buch (writing, varied agents)",
         ("schreibt", "das Buch"),
         "Core German sentence: Taro schreibt das Buch. "
         "Vary the agent and object across 4 pairs; keep neuter accusative: "
         "pair 1 Taro/das Buch (neut), pair 2 Emma/das Dokument (neut), "
         "pair 3 der Lehrer/das Buch (neut), pair 4 Gran/das Dokument (neut). "
         "Japanese cue: 〜を書く (本を書く). Chinese cue: 寫, SVO order. "
         "Keep the German accusative article das visible in every German line. "
         "Do not add a dative receiver."),
        # ── Extensions: malen ─────────────────────────────────────────────────
        ("037_draw_b.md",
         "malen — Emma malt die Blume (drawing nature)",
         ("malt", "die Blume"),
         "Core German sentence: Emma malt die Blume. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/die Blume (fem), pair 2 Taro/den Baum (masc), "
         "pair 3 Gran/den Vogel (masc), pair 4 das Kind/die Ente (fem). "
         "Japanese cue: 〜を描く (花を描く). Chinese cue: 畫, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        ("038_draw_c.md",
         "malen — Taro malt den Korb (drawing objects and furniture)",
         ("malt", "den Korb"),
         "Core German sentence: Taro malt den Korb. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Taro/den Korb (masc), pair 2 Emma/den Tisch (masc), "
         "pair 3 Gran/den Stuhl (masc), pair 4 der Junge/die Kiste (fem). "
         "Japanese cue: 〜を描く (かごを描く). Chinese cue: 畫, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        # ── Extensions: brauchen ──────────────────────────────────────────────
        ("039_need_b.md",
         "brauchen — Taro braucht den Eimer (needing household tools)",
         ("braucht", "den Eimer"),
         "Core German sentence: Taro braucht den Eimer. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Taro/den Eimer (masc), pair 2 Emma/den Stuhl (masc), "
         "pair 3 Gran/die Decke (fem), pair 4 der Mann/den Besen (masc). "
         "Japanese cue: 〜が必要だ (バケツが必要だ). Chinese cue: 需要, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        ("040_need_c.md",
         "brauchen — Gran braucht den Fisch (needing food items)",
         ("braucht", "den Fisch"),
         "Core German sentence: Gran braucht den Fisch. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Gran/den Fisch (masc), pair 2 Emma/den Apfel (masc), "
         "pair 3 Taro/das Brot (neut), pair 4 die Frau/das Gemüse (neut). "
         "Japanese cue: 〜が必要だ (魚が必要だ). Chinese cue: 需要, SVO order. "
         "Keep the German accusative article (den/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── Extensions: werfen ────────────────────────────────────────────────
        ("041_throw_b.md",
         "werfen — der Arzt wirft den Ball (throwing, varied agents and objects)",
         ("wirft", "den Ball"),
         "Core German sentence: Der Arzt wirft den Ball. "
         "Vary the agent and object across 4 pairs to show some gender contrast: "
         "pair 1 der Arzt/den Ball (masc), pair 2 die Tante/die Flasche (fem), "
         "pair 3 der Lehrer/den Ball (masc), pair 4 das Kind/die Flasche (fem). "
         "Japanese cue: 〜を投げる (ボールを投げる). Chinese cue: 丟/扔, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: trinken ─────────────────────────────────────────────────
        ("042_drink_a.md",
         "trinken — das Kind trinkt das Wasser (drinking liquids, gender contrast)",
         ("trinkt", "das Wasser"),
         "Core German sentence: Das Kind trinkt das Wasser. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 das Kind/das Wasser (neut), pair 2 Emma/die Milch (fem), "
         "pair 3 Taro/den Tee (masc), pair 4 Gran/den Saft (masc). "
         "Japanese cue: 〜を飲む (水を飲む). Chinese cue: 喝, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("043_drink_b.md",
         "trinken — Gran trinkt die Milch (drinking, varied agents)",
         ("trinkt", "die Milch"),
         "Core German sentence: Gran trinkt die Milch. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Gran/die Milch (fem), pair 2 Emma/das Wasser (neut), "
         "pair 3 Taro/den Tee (masc), pair 4 das Kind/die Milch (fem). "
         "Japanese cue: 〜を飲む (牛乳を飲む). Chinese cue: 喝, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: schließen ───────────────────────────────────────────────
        ("044_close_a.md",
         "schließen — Emma schließt die Tür (closing doors and windows)",
         ("schließt", "die Tür"),
         "Core German sentence: Emma schließt die Tür. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/die Tür (fem), pair 2 Taro/das Fenster (neut), "
         "pair 3 Gran/die Tür (fem), pair 4 der Junge/das Fenster (neut). "
         "Japanese cue: 〜を閉める (ドアを閉める). Chinese cue: 關上, SVO order. "
         "Keep the German accusative article (die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("045_close_b.md",
         "schließen — Taro schließt die Kiste (closing containers)",
         ("schließt", "die Kiste"),
         "Core German sentence: Taro schließt die Kiste. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Taro/die Kiste (fem), pair 2 Emma/das Buch (neut), "
         "pair 3 Gran/die Flasche (fem), pair 4 die Frau/die Tasche (fem). "
         "Japanese cue: 〜を閉める (箱を閉める). Chinese cue: 關上, SVO order. "
         "Keep the German accusative article (die/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: holen ───────────────────────────────────────────────────
        ("046_fetch_a.md",
         "holen — Gran holt den Ball (fetching objects)",
         ("holt", "den Ball"),
         "Core German sentence: Gran holt den Ball. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Gran/den Ball (masc), pair 2 Emma/das Buch (neut), "
         "pair 3 Taro/den Becher (masc), pair 4 der Junge/die Tasche (fem). "
         "Japanese cue: 〜を取ってくる (ボールを取ってくる). Chinese cue: 去拿/取來, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("047_fetch_b.md",
         "holen — Emma holt den Apfel (fetching food items)",
         ("holt", "den Apfel"),
         "Core German sentence: Emma holt den Apfel. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/den Apfel (masc), pair 2 Taro/das Brot (neut), "
         "pair 3 Gran/den Fisch (masc), pair 4 die Frau/das Gemüse (neut). "
         "Japanese cue: 〜を取ってくる (りんごを取ってくる). Chinese cue: 去拿/取來, SVO order. "
         "Keep the German accusative article (den/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: kochen ──────────────────────────────────────────────────
        ("048_cook_a.md",
         "kochen — Emma kocht die Suppe (cooking food)",
         ("kocht", "die Suppe"),
         "Core German sentence: Emma kocht die Suppe. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/die Suppe (fem), pair 2 Gran/den Fisch (masc), "
         "pair 3 Taro/das Gemüse (neut), pair 4 die Frau/die Suppe (fem). "
         "Japanese cue: 〜を料理する / 煮る (スープを作る). Chinese cue: 煮/做, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("049_cook_b.md",
         "kochen — Taro kocht den Fisch (cooking varied food, different agents)",
         ("kocht", "den Fisch"),
         "Core German sentence: Taro kocht den Fisch. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Taro/den Fisch (masc), pair 2 Emma/die Suppe (fem), "
         "pair 3 der Bäcker/das Gemüse (neut), pair 4 Gran/den Kuchen (masc). "
         "Japanese cue: 〜を料理する (魚を料理する). Chinese cue: 煮/做, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: backen ──────────────────────────────────────────────────
        ("050_bake_a.md",
         "backen — Gran bäckt das Brot (baking bread, gender contrast)",
         ("bäckt", "das Brot"),
         "Core German sentence: Gran bäckt das Brot. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Gran/das Brot (neut), pair 2 Emma/den Kuchen (masc), "
         "pair 3 der Bäcker/das Brot (neut), pair 4 die Frau/den Kuchen (masc). "
         "Japanese cue: 〜を焼く (パンを焼く). Chinese cue: 烤/烘培, SVO order. "
         "Keep the German accusative article (den/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("051_bake_b.md",
         "backen — Emma bäckt den Kuchen (baking cake, varied agents)",
         ("bäckt", "den Kuchen"),
         "Core German sentence: Emma bäckt den Kuchen. "
         "Vary the agent and object across 4 pairs: "
         "pair 1 Emma/den Kuchen (masc), pair 2 Taro/das Brot (neut), "
         "pair 3 der Bäcker/den Kuchen (masc), pair 4 Gran/das Brot (neut). "
         "Japanese cue: 〜を焼く (ケーキを焼く). Chinese cue: 烤, SVO order. "
         "Keep the German accusative article (den/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: heben ───────────────────────────────────────────────────
        ("052_lift_a.md",
         "heben — Gran hebt den Korb (lifting containers)",
         ("hebt", "den Korb"),
         "Core German sentence: Gran hebt den Korb. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Gran/den Korb (masc), pair 2 Taro/den Eimer (masc), "
         "pair 3 Emma/die Kiste (fem), pair 4 der Mann/den Tisch (masc). "
         "Japanese cue: 〜を持ち上げる (かごを持ち上げる). Chinese cue: 舉起/提起, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        ("053_lift_b.md",
         "heben — Emma hebt das Buch (lifting lighter objects)",
         ("hebt", "das Buch"),
         "Core German sentence: Emma hebt das Buch. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/das Buch (neut), pair 2 Taro/die Tasche (fem), "
         "pair 3 Gran/den Ball (masc), pair 4 das Kind/den Stuhl (masc). "
         "Japanese cue: 〜を持ち上げる (本を持ち上げる). Chinese cue: 舉起, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: putzen ──────────────────────────────────────────────────
        ("054_clean_a.md",
         "putzen — Emma putzt den Boden (cleaning surfaces)",
         ("putzt", "den Boden"),
         "Core German sentence: Emma putzt den Boden. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/den Boden (masc), pair 2 Taro/das Fenster (neut), "
         "pair 3 Gran/die Schüssel (fem), pair 4 der Hausmeister/den Tisch (masc). "
         "Japanese cue: 〜を掃除する (床を掃除する). Chinese cue: 打掃/清潔, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("055_clean_b.md",
         "putzen — Taro putzt den Ball (cleaning objects)",
         ("putzt", "den Ball"),
         "Core German sentence: Taro putzt den Ball. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Taro/den Ball (masc), pair 2 Emma/die Tasche (fem), "
         "pair 3 Gran/den Stuhl (masc), pair 4 die Frau/den Becher (masc). "
         "Japanese cue: 〜を磨く / きれいにする (ボールを磨く). Chinese cue: 清潔, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: reparieren ──────────────────────────────────────────────
        ("056_repair_a.md",
         "reparieren — Gran repariert das Fahrrad (repairing vehicles and furniture)",
         ("repariert", "das Fahrrad"),
         "Core German sentence: Gran repariert das Fahrrad. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Gran/das Fahrrad (neut), pair 2 Taro/den Stuhl (masc), "
         "pair 3 Emma/den Tisch (masc), pair 4 der Tischler/die Kiste (fem). "
         "Japanese cue: 〜を直す / 修理する (自転車を直す). Chinese cue: 修理, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("057_repair_b.md",
         "reparieren — Emma repariert den Ball (repairing smaller objects)",
         ("repariert", "den Ball"),
         "Core German sentence: Emma repariert den Ball. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/den Ball (masc), pair 2 Taro/die Tasche (fem), "
         "pair 3 Gran/den Becher (masc), pair 4 der Tischler/den Korb (masc). "
         "Japanese cue: 〜を修理する (ボールを修理する). Chinese cue: 修理, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: suchen ──────────────────────────────────────────────────
        ("058_search_a.md",
         "suchen — Taro sucht den Ball (searching for objects)",
         ("sucht", "den Ball"),
         "Core German sentence: Taro sucht den Ball. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Taro/den Ball (masc), pair 2 Emma/das Buch (neut), "
         "pair 3 Gran/den Bleistift (masc), pair 4 das Kind/die Tasche (fem). "
         "Japanese cue: 〜を探す (ボールを探す). Chinese cue: 尋找, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("059_search_b.md",
         "suchen — Emma sucht den Mann (searching for people)",
         ("sucht", "den Mann"),
         "Core German sentence: Emma sucht den Mann. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/den Mann (masc), pair 2 Gran/die Frau (fem), "
         "pair 3 Taro/das Kind (neut), pair 4 der Junge/den Hund (masc). "
         "Japanese cue: 〜を探す (男の人を探す). Chinese cue: 尋找, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: verlieren ───────────────────────────────────────────────
        ("060_lose_a.md",
         "verlieren — das Kind verliert den Ball (losing small objects)",
         ("verliert", "den Ball"),
         "Core German sentence: Das Kind verliert den Ball. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 das Kind/den Ball (masc), pair 2 Emma/den Bleistift (masc), "
         "pair 3 Taro/das Buch (neut), pair 4 Gran/den Becher (masc). "
         "Japanese cue: 〜をなくす (ボールをなくす). Chinese cue: 丟失/遺失, SVO order. "
         "Keep the German accusative article (den/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("061_lose_b.md",
         "verlieren — Emma verliert die Tasche (losing containers and clothing)",
         ("verliert", "die Tasche"),
         "Core German sentence: Emma verliert die Tasche. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/die Tasche (fem), pair 2 Taro/den Korb (masc), "
         "pair 3 Gran/die Decke (fem), pair 4 der Mann/den Eimer (masc). "
         "Japanese cue: 〜をなくす (袋をなくす). Chinese cue: 丟失/遺失, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: schlagen ────────────────────────────────────────────────
        ("062_hit_a.md",
         "schlagen — Taro schlägt den Ball (hitting objects)",
         ("schlägt", "den Ball"),
         "Core German sentence: Taro schlägt den Ball. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Taro/den Ball (masc), pair 2 Emma/die Tür (fem), "
         "pair 3 Gran/den Tisch (masc), pair 4 der Junge/den Ball (masc). "
         "Japanese cue: 〜を打つ / 叩く (ボールを打つ). Chinese cue: 打/擊, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        ("063_hit_b.md",
         "schlagen — Emma schlägt den Ball (hitting the ball, varied agents)",
         ("schlägt", "den Ball"),
         "Core German sentence: Emma schlägt den Ball. "
         "Vary the agent across 4 pairs; keep den Ball as the object: "
         "pair 1 Emma/den Ball, pair 2 Taro/den Ball, pair 3 der Junge/den Ball, pair 4 Gran/den Ball. "
         "Japanese cue: 〜を打つ (ボールを打つ). Chinese cue: 打球, SVO order. "
         "Keep den Ball visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: hören ───────────────────────────────────────────────────
        ("064_hear_a.md",
         "hören — Gran hört den Hund (hearing animals)",
         ("hört", "den Hund"),
         "Core German sentence: Gran hört den Hund. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Gran/den Hund (masc), pair 2 Emma/die Katze (fem), "
         "pair 3 Taro/den Vogel (masc), pair 4 das Kind/die Ente (fem). "
         "Japanese cue: 〜を聞く / 聞こえる (犬の声を聞く). Chinese cue: 聽到, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        ("065_hear_b.md",
         "hören — Emma hört die Musik (hearing sounds and voices)",
         ("hört", "die Musik"),
         "Core German sentence: Emma hört die Musik. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/die Musik (fem), pair 2 Taro/den Zug (masc), "
         "pair 3 Gran/den Hund (masc), pair 4 das Kind/die Musik (fem). "
         "Japanese cue: 〜を聞く (音楽を聞く). Chinese cue: 聽到, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: fangen ──────────────────────────────────────────────────
        ("066_catch_a.md",
         "fangen — Taro fängt den Fisch (catching animals)",
         ("fängt", "den Fisch"),
         "Core German sentence: Taro fängt den Fisch. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Taro/den Fisch (masc), pair 2 Emma/die Ente (fem), "
         "pair 3 Gran/das Kaninchen (neut), pair 4 der Junge/den Frosch (masc). "
         "Japanese cue: 〜を捕まえる (魚を捕まえる). Chinese cue: 捉/抓, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("067_catch_b.md",
         "fangen — Emma fängt den Ball (catching the ball, varied agents)",
         ("fängt", "den Ball"),
         "Core German sentence: Emma fängt den Ball. "
         "Vary the agent across 4 pairs; keep den Ball as the object: "
         "pair 1 Emma/den Ball, pair 2 Taro/den Ball, pair 3 der Junge/den Ball, pair 4 Gran/den Ball. "
         "Japanese cue: 〜を捕まえる (ボールを捕まえる). Chinese cue: 接住/抓住, SVO order. "
         "Keep den Ball visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: streicheln ──────────────────────────────────────────────
        ("068_pet_a.md",
         "streicheln — Emma streichelt den Hund (stroking animals)",
         ("streichelt", "den Hund"),
         "Core German sentence: Emma streichelt den Hund. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/den Hund (masc), pair 2 Taro/die Katze (fem), "
         "pair 3 Gran/das Kaninchen (neut), pair 4 das Kind/den Vogel (masc). "
         "Japanese cue: 〜を撫でる (犬を撫でる). Chinese cue: 撫摸, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("069_pet_b.md",
         "streicheln — das Kind streichelt die Katze (petting animals, different agents)",
         ("streichelt", "die Katze"),
         "Core German sentence: Das Kind streichelt die Katze. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 das Kind/die Katze (fem), pair 2 Emma/den Hund (masc), "
         "pair 3 Gran/das Kaninchen (neut), pair 4 Taro/die Katze (fem). "
         "Japanese cue: 〜を撫でる (猫を撫でる). Chinese cue: 撫摸, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: kennen ──────────────────────────────────────────────────
        ("070_know_a.md",
         "kennen — Gran kennt den Mann (knowing people)",
         ("kennt", "den Mann"),
         "Core German sentence: Gran kennt den Mann. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Gran/den Mann (masc), pair 2 Emma/die Frau (fem), "
         "pair 3 Taro/den Jungen (masc), pair 4 die Frau/das Mädchen (neut). "
         "Japanese cue: 〜を知っている (男の人を知っている). Chinese cue: 認識, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("071_know_b.md",
         "kennen — Emma kennt den Arzt (knowing professionals)",
         ("kennt", "den Arzt"),
         "Core German sentence: Emma kennt den Arzt. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/den Arzt (masc), pair 2 Gran/den Lehrer (masc), "
         "pair 3 Taro/die Tante (fem), pair 4 das Kind/den Nachbarn (masc). "
         "Japanese cue: 〜を知っている (医者を知っている). Chinese cue: 認識, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: beobachten ──────────────────────────────────────────────
        ("072_watch_a.md",
         "beobachten — Gran beobachtet den Vogel (observing animals)",
         ("beobachtet", "den Vogel"),
         "Core German sentence: Gran beobachtet den Vogel. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Gran/den Vogel (masc), pair 2 Emma/die Katze (fem), "
         "pair 3 Taro/den Hund (masc), pair 4 das Kind/das Kaninchen (neut). "
         "Japanese cue: 〜を観察する (鳥を観察する). Chinese cue: 觀察/觀看, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("073_watch_b.md",
         "beobachten — Emma beobachtet das Kind (observing people)",
         ("beobachtet", "das Kind"),
         "Core German sentence: Emma beobachtet das Kind. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/das Kind (neut), pair 2 Gran/den Jungen (masc), "
         "pair 3 Taro/den Mann (masc), pair 4 der Arzt/die Frau (fem). "
         "Japanese cue: 〜を観察する (子供を観察する). Chinese cue: 觀察/觀看, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: packen ──────────────────────────────────────────────────
        ("074_pack_a.md",
         "packen — Taro packt den Korb (packing containers)",
         ("packt", "den Korb"),
         "Core German sentence: Taro packt den Korb. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Taro/den Korb (masc), pair 2 Emma/die Kiste (fem), "
         "pair 3 Gran/die Tasche (fem), pair 4 der Mann/den Eimer (masc). "
         "Japanese cue: 〜を詰め込む (かごを詰め込む). Chinese cue: 抓住/打包, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        ("075_pack_b.md",
         "packen — Gran packt das Buch (packing items into a bag)",
         ("packt", "das Buch"),
         "Core German sentence: Gran packt das Buch. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Gran/das Buch (neut), pair 2 Emma/den Ball (masc), "
         "pair 3 Taro/die Decke (fem), pair 4 das Kind/den Becher (masc). "
         "Japanese cue: 〜を詰める (本を詰める). Chinese cue: 打包/裝, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: füllen ──────────────────────────────────────────────────
        ("076_fill_a.md",
         "füllen — Emma füllt den Becher (filling cups and bowls)",
         ("füllt", "den Becher"),
         "Core German sentence: Emma füllt den Becher. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/den Becher (masc), pair 2 Taro/die Schüssel (fem), "
         "pair 3 Gran/den Eimer (masc), pair 4 der Junge/den Korb (masc). "
         "Japanese cue: 〜をいっぱいにする (コップをいっぱいにする). Chinese cue: 裝滿/填滿, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        ("077_fill_b.md",
         "füllen — Taro füllt die Kiste (filling boxes and bottles)",
         ("füllt", "die Kiste"),
         "Core German sentence: Taro füllt die Kiste. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Taro/die Kiste (fem), pair 2 Emma/die Flasche (fem), "
         "pair 3 Gran/den Eimer (masc), pair 4 die Frau/die Schüssel (fem). "
         "Japanese cue: 〜をいっぱいにする (箱をいっぱいにする). Chinese cue: 裝滿/填滿, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: pflücken ────────────────────────────────────────────────
        ("078_pick_a.md",
         "pflücken — Emma pflückt den Apfel (picking fruit and flowers)",
         ("pflückt", "den Apfel"),
         "Core German sentence: Emma pflückt den Apfel. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/den Apfel (masc), pair 2 Taro/die Blume (fem), "
         "pair 3 Gran/das Gemüse (neut), pair 4 der Junge/den Apfel (masc). "
         "Japanese cue: 〜を摘む (りんごを摘む). Chinese cue: 採摘, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("079_pick_b.md",
         "pflücken — Gran pflückt die Blume (picking flowers, varied agents)",
         ("pflückt", "die Blume"),
         "Core German sentence: Gran pflückt die Blume. "
         "Vary the agent and object across 4 pairs: "
         "pair 1 Gran/die Blume (fem), pair 2 Emma/den Apfel (masc), "
         "pair 3 Taro/die Blume (fem), pair 4 das Kind/den Apfel (masc). "
         "Japanese cue: 〜を摘む (花を摘む). Chinese cue: 採摘, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: wiegen ──────────────────────────────────────────────────
        ("080_weigh_a.md",
         "wiegen — Emma wiegt den Apfel (weighing food and objects)",
         ("wiegt", "den Apfel"),
         "Core German sentence: Emma wiegt den Apfel. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/den Apfel (masc), pair 2 Taro/das Brot (neut), "
         "pair 3 Gran/die Tasche (fem), pair 4 der Junge/den Ball (masc). "
         "Japanese cue: 〜を量る (りんごを量る). Chinese cue: 量重量/稱重, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("081_weigh_b.md",
         "wiegen — der Arzt wiegt das Kind (weighing people and animals)",
         ("wiegt", "das Kind"),
         "Core German sentence: Der Arzt wiegt das Kind. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 der Arzt/das Kind (neut), pair 2 Gran/den Hund (masc), "
         "pair 3 Emma/die Katze (fem), pair 4 der Junge/das Kaninchen (neut). "
         "Japanese cue: 〜の体重を量る (子供の体重を量る). Chinese cue: 量重量/稱重, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: bauen ───────────────────────────────────────────────────
        ("082_build_a.md",
         "bauen — Gran baut den Tisch (building furniture)",
         ("baut", "den Tisch"),
         "Core German sentence: Gran baut den Tisch. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Gran/den Tisch (masc), pair 2 Taro/den Stuhl (masc), "
         "pair 3 Emma/die Kiste (fem), pair 4 der Tischler/das Haus (neut). "
         "Japanese cue: 〜を作る / 建てる (テーブルを作る). Chinese cue: 建造/製作, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("083_build_b.md",
         "bauen — der Tischler baut das Haus (building structures, different agents)",
         ("baut", "das Haus"),
         "Core German sentence: Der Tischler baut das Haus. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 der Tischler/das Haus (neut), pair 2 Gran/den Stuhl (masc), "
         "pair 3 Taro/die Kiste (fem), pair 4 Emma/den Tisch (masc). "
         "Japanese cue: 〜を建てる (家を建てる). Chinese cue: 建造/蓋, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: schieben ────────────────────────────────────────────────
        ("084_push_a.md",
         "schieben — Taro schiebt den Korb (pushing containers)",
         ("schiebt", "den Korb"),
         "Core German sentence: Taro schiebt den Korb. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Taro/den Korb (masc), pair 2 Emma/den Eimer (masc), "
         "pair 3 Gran/den Tisch (masc), pair 4 der Junge/die Kiste (fem). "
         "Japanese cue: 〜を押す (かごを押す). Chinese cue: 推, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        ("085_push_b.md",
         "schieben — Emma schiebt das Fahrrad (pushing vehicles and furniture)",
         ("schiebt", "das Fahrrad"),
         "Core German sentence: Emma schiebt das Fahrrad. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/das Fahrrad (neut), pair 2 Taro/den Stuhl (masc), "
         "pair 3 Gran/den Ball (masc), pair 4 der Mann/die Bank (fem). "
         "Japanese cue: 〜を押す (自転車を押す). Chinese cue: 推, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: messen ──────────────────────────────────────────────────
        ("086_measure_a.md",
         "messen — Gran misst den Tisch (measuring furniture and objects)",
         ("misst", "den Tisch"),
         "Core German sentence: Gran misst den Tisch. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Gran/den Tisch (masc), pair 2 Taro/den Stuhl (masc), "
         "pair 3 Emma/das Brot (neut), pair 4 der Tischler/die Bank (fem). "
         "Japanese cue: 〜を測る (テーブルを測る). Chinese cue: 量/測量, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("087_measure_b.md",
         "messen — der Arzt misst das Kind (measuring people and food)",
         ("misst", "das Kind"),
         "Core German sentence: Der Arzt misst das Kind. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 der Arzt/das Kind (neut), pair 2 Gran/den Mann (masc), "
         "pair 3 Emma/das Gemüse (neut), pair 4 Taro/den Fisch (masc). "
         "Japanese cue: 〜を測る (子供を測る). Chinese cue: 量/測量, SVO order. "
         "Keep the German accusative article (den/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: wischen ─────────────────────────────────────────────────
        ("088_wipe_a.md",
         "wischen — Emma wischt den Boden (wiping surfaces)",
         ("wischt", "den Boden"),
         "Core German sentence: Emma wischt den Boden. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/den Boden (masc), pair 2 Taro/das Fenster (neut), "
         "pair 3 Gran/die Schüssel (fem), pair 4 der Hausmeister/den Tisch (masc). "
         "Japanese cue: 〜を拭く (床を拭く). Chinese cue: 擦/拭, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("089_wipe_b.md",
         "wischen — Taro wischt den Ball (wiping objects)",
         ("wischt", "den Ball"),
         "Core German sentence: Taro wischt den Ball. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Taro/den Ball (masc), pair 2 Emma/die Tasche (fem), "
         "pair 3 Gran/den Stuhl (masc), pair 4 die Frau/den Becher (masc). "
         "Japanese cue: 〜を拭く (ボールを拭く). Chinese cue: 擦/拭, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: schütteln ───────────────────────────────────────────────
        ("090_shake_a.md",
         "schütteln — Taro schüttelt den Ball (shaking objects)",
         ("schüttelt", "den Ball"),
         "Core German sentence: Taro schüttelt den Ball. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Taro/den Ball (masc), pair 2 Emma/den Korb (masc), "
         "pair 3 Gran/die Flasche (fem), pair 4 der Junge/den Eimer (masc). "
         "Japanese cue: 〜を振る (ボールを振る). Chinese cue: 搖動/搖晃, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        ("091_shake_b.md",
         "schütteln — Gran schüttelt die Tasche (shaking bags and containers)",
         ("schüttelt", "die Tasche"),
         "Core German sentence: Gran schüttelt die Tasche. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Gran/die Tasche (fem), pair 2 Taro/die Kiste (fem), "
         "pair 3 Emma/den Baum (masc), pair 4 das Kind/die Flasche (fem). "
         "Japanese cue: 〜を振る (袋を振る). Chinese cue: 搖動/搖晃, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: drücken ─────────────────────────────────────────────────
        ("092_press_a.md",
         "drücken — Emma drückt den Ball (pressing objects)",
         ("drückt", "den Ball"),
         "Core German sentence: Emma drückt den Ball. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/den Ball (masc), pair 2 Taro/den Korb (masc), "
         "pair 3 Gran/den Becher (masc), pair 4 der Junge/die Kiste (fem). "
         "Japanese cue: 〜を押す (ボールを押す). Chinese cue: 按壓/擠壓, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        ("093_press_b.md",
         "drücken — Gran drückt die Tasche (pressing bags and furniture)",
         ("drückt", "die Tasche"),
         "Core German sentence: Gran drückt die Tasche. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Gran/die Tasche (fem), pair 2 Emma/den Eimer (masc), "
         "pair 3 Taro/den Tisch (masc), pair 4 die Frau/den Stuhl (masc). "
         "Japanese cue: 〜を押す (袋を押す). Chinese cue: 按壓, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        # ── Extensions: rufen ─────────────────────────────────────────────────
        ("094_call_b.md",
         "rufen — Taro ruft die Katze (calling animals)",
         ("ruft", "die Katze"),
         "Core German sentence: Taro ruft die Katze. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Taro/die Katze (fem), pair 2 Emma/den Hund (masc), "
         "pair 3 Gran/das Pferd (neut), pair 4 das Kind/das Schaf (neut). "
         "Japanese cue: 〜を呼ぶ (猫を呼ぶ). Chinese cue: 叫/呼叫, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("095_call_c.md",
         "rufen — Emma ruft den Arzt (calling professionals)",
         ("ruft", "den Arzt"),
         "Core German sentence: Emma ruft den Arzt. "
         "Vary the agent and object across 4 pairs: "
         "pair 1 Emma/den Arzt (masc), pair 2 Taro/den Fahrer (masc), "
         "pair 3 Gran/den Kellner (masc), pair 4 die Frau/den Lehrer (masc). "
         "Japanese cue: 〜を呼ぶ (医者を呼ぶ). Chinese cue: 叫/呼叫, SVO order. "
         "Keep den visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: rollen ──────────────────────────────────────────────────
        ("096_roll_a.md",
         "rollen — Taro rollt den Ball (rolling objects)",
         ("rollt", "den Ball"),
         "Core German sentence: Taro rollt den Ball. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Taro/den Ball (masc), pair 2 Emma/den Eimer (masc), "
         "pair 3 Gran/die Flasche (fem), pair 4 der Junge/den Korb (masc). "
         "Japanese cue: 〜を転がす (ボールを転がす). Chinese cue: 滾動, SVO order. "
         "Keep the German accusative article (den/die) visible in every German line. "
         "Do not add a dative receiver."),
        ("097_roll_b.md",
         "rollen — Emma rollt den Ball (rolling the ball, varied agents)",
         ("rollt", "den Ball"),
         "Core German sentence: Emma rollt den Ball. "
         "Vary the agent across 4 pairs; keep den Ball as the object: "
         "pair 1 Emma/den Ball, pair 2 Taro/den Ball, pair 3 der Junge/den Ball, pair 4 Gran/den Ball. "
         "Japanese cue: 〜を転がす (ボールを転がす). Chinese cue: 滾動球, SVO order. "
         "Keep den Ball visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: falten ──────────────────────────────────────────────────
        ("098_fold_a.md",
         "falten — Emma faltet die Decke (folding textiles and documents)",
         ("faltet", "die Decke"),
         "Core German sentence: Emma faltet die Decke. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Emma/die Decke (fem), pair 2 Taro/das Dokument (neut), "
         "pair 3 Gran/die Tasche (fem), pair 4 die Frau/das Dokument (neut). "
         "Japanese cue: 〜を折りたたむ (毛布を折りたたむ). Chinese cue: 折疊, SVO order. "
         "Keep the German accusative article (die/das) visible in every German line. "
         "Do not add a dative receiver."),
        ("099_fold_b.md",
         "falten — Taro faltet das Dokument (folding, varied agents)",
         ("faltet", "das Dokument"),
         "Core German sentence: Taro faltet das Dokument. "
         "Vary the agent and object across 4 pairs: "
         "pair 1 Taro/das Dokument (neut), pair 2 Emma/die Decke (fem), "
         "pair 3 Gran/das Dokument (neut), pair 4 der Lehrer/die Decke (fem). "
         "Japanese cue: 〜を折りたたむ (書類を折りたたむ). Chinese cue: 折疊, SVO order. "
         "Keep the German accusative article (die/das) visible in every German line. "
         "Do not add a dative receiver."),
        # ── New verb: wählen ──────────────────────────────────────────────────
        ("100_choose_a.md",
         "wählen — Gran wählt den Apfel (choosing objects, gender contrast)",
         ("wählt", "den Apfel"),
         "Core German sentence: Gran wählt den Apfel. "
         "Vary the agent and object across 4 pairs to show gender contrast: "
         "pair 1 Gran/den Apfel (masc), pair 2 Emma/den Becher (masc), "
         "pair 3 Taro/das Buch (neut), pair 4 das Kind/die Tasche (fem). "
         "Japanese cue: 〜を選ぶ (りんごを選ぶ). Chinese cue: 選擇, SVO order. "
         "Keep the German accusative article (den/die/das) visible in every German line. "
         "Do not add a dative receiver."),
    ]

    shared_suffix = (
        " Plain transitive construction only — one agent, one accusative object, no dative receiver. "
        "The German accusative object must show the article: den for masculine, die for feminine, das for neuter. "
        "JP: direct object takes を particle (〜を + verb). "
        "ZH: subject–verb–object word order; no case particle needed. "
        "Keep vocabulary strictly within the grammar lexicon. "
        "Do not use verbs from the receiver_dative cluster: geben, zeigen, bringen, schicken, leihen, helfen, antworten, erzählen."
    )

    return [
        FileSpec(
            path=f"05_object_accusative_patient/{filename}",
            focus=focus,
            required_terms=required,
            notes=notes + shared_suffix,
        )
        for filename, focus, required, notes in rows
    ]


def make_change_state_specs() -> list[FileSpec]:
    """Specs for `04_change_state`: state-change copula werden + adjective predicate."""
    rows: list[tuple[str, str, tuple[str, ...], str]] = [
        # ── Temperature: becomes cold ──────────────────────────────────────────
        ("001_change_kalt.md",
         "werden + kalt — things become cold",
         ("wird kalt", "cold"),
         "Core German sentence: Das Wasser wird kalt. "
         "State changes toward cold. "
         "Japanese cue: 〜くなる (水が冷たくなる). Chinese cue: 變得冷 or 變冷了. "
         "Vary the subject across the 4 pairs: water (Wasser), soup (Suppe), room (Zimmer), air (Luft). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird kalt visible in every German line."),
        # ── Temperature: becomes warm ──────────────────────────────────────────
        ("002_change_warm.md",
         "werden + warm — things become warm",
         ("wird warm", "warm"),
         "Core German sentence: Die Suppe wird warm. "
         "State changes toward warm. "
         "Japanese cue: 〜くなる (スープが温かくなる). Chinese cue: 變得暖 or 變暖了. "
         "Vary the subject across the 4 pairs: soup (Suppe), water (Wasser), room (Zimmer), bread (Brot). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird warm visible in every German line."),
        # ── Temperature: becomes hot ───────────────────────────────────────────
        ("003_change_heiss.md",
         "werden + heiß — things become hot",
         ("wird heiß", "hot"),
         "Core German sentence: Das Wasser wird heiß. "
         "State changes toward hot. "
         "Japanese cue: 〜くなる (水が熱くなる). Chinese cue: 變得熱 or 變熱了. "
         "Vary the subject across the 4 pairs: water (Wasser), soup (Suppe), stone (Stein), cup (Becher). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird heiß visible in every German line."),
        # ── Temperature: becomes cool ──────────────────────────────────────────
        ("004_change_kuehl.md",
         "werden + kühl — things become cool",
         ("wird kühl", "cool"),
         "Core German sentence: Das Zimmer wird kühl. "
         "State changes toward cool. "
         "Japanese cue: 〜くなる (部屋が涼しくなる). Chinese cue: 變得涼 or 變涼了. "
         "Vary the subject across the 4 pairs: room (Zimmer), water (Wasser), air (Luft), soup (Suppe). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird kühl visible in every German line."),
        # ── Physical state: becomes hard ───────────────────────────────────────
        ("005_change_hart.md",
         "werden + hart — things become hard",
         ("wird hart", "hard"),
         "Core German sentence: Das Brot wird hart. "
         "State changes toward hard. "
         "Japanese cue: 〜くなる (パンが固くなる). Chinese cue: 變得硬 or 變硬了. "
         "Vary the subject across the 4 pairs: bread (Brot), clay (Ton), apple (Apfel), dough (Teig). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird hart visible in every German line."),
        # ── Physical state: becomes soft ───────────────────────────────────────
        ("006_change_weich.md",
         "werden + weich — things become soft",
         ("wird weich", "soft"),
         "Core German sentence: Das Brot wird weich. "
         "State changes toward soft. "
         "Japanese cue: 〜くなる (パンが柔らかくなる). Chinese cue: 變得軟 or 變軟了. "
         "Vary the subject across the 4 pairs: bread (Brot), butter (Butter), clay (Ton), apple (Apfel). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird weich visible in every German line."),
        # ── Physical state: becomes wet ────────────────────────────────────────
        ("007_change_nass.md",
         "werden + nass — things become wet",
         ("wird nass", "wet"),
         "Core German sentence: Der Boden wird nass. "
         "State changes toward wet. "
         "Japanese cue: 〜くなる (床が濡れていく). Chinese cue: 變得濕 or 變濕了. "
         "Vary the subject across the 4 pairs: floor (Boden), cloth (Tuch), bench (Bank), book (Buch). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird nass visible in every German line."),
        # ── Physical state: becomes dry ────────────────────────────────────────
        ("008_change_trocken.md",
         "werden + trocken — things become dry",
         ("wird trocken", "dry"),
         "Core German sentence: Der Boden wird trocken. "
         "State changes toward dry. "
         "Japanese cue: 〜くなる (床が乾いていく). Chinese cue: 變得乾 or 變乾了. "
         "Vary the subject across the 4 pairs: floor (Boden), cloth (Tuch), bread (Brot), bench (Bank). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird trocken visible in every German line."),
        # ── Living state: becomes tired ────────────────────────────────────────
        ("009_change_muede.md",
         "werden + müde — beings become tired",
         ("wird müde", "tired"),
         "Core German sentence: Das Kind wird müde. "
         "State changes toward tired. "
         "Japanese cue: 〜になる (子どもが疲れる or 眠くなる). Chinese cue: 變得累 or 變累了. "
         "Vary the subject across the 4 pairs: child (Kind), dog (Hund), man (Mann), woman (Frau). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird müde visible in every German line."),
        # ── Living state: becomes awake ────────────────────────────────────────
        ("010_change_wach.md",
         "werden + wach — beings become awake",
         ("wird wach", "awake"),
         "Core German sentence: Das Kind wird wach. "
         "State changes toward awake. "
         "Japanese cue: 〜になる (子どもが目を覚ます). Chinese cue: 變得清醒 or 醒了. "
         "Vary the subject across the 4 pairs: child (Kind), man (Mann), woman (Frau), dog (Hund). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird wach visible in every German line."),
        # ── Living state: becomes sick ─────────────────────────────────────────
        ("011_change_krank.md",
         "werden + krank — beings become sick",
         ("wird krank", "sick"),
         "Core German sentence: Der Mann wird krank. "
         "State changes toward sick. "
         "Japanese cue: 〜になる (男の人が病気になる). Chinese cue: 生病了 or 變得生病. "
         "Vary the subject across the 4 pairs: man (Mann), child (Kind), woman (Frau), boy (Junge). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird krank visible in every German line."),
        # ── Living state: becomes healthy ──────────────────────────────────────
        ("012_change_gesund.md",
         "werden + gesund — beings become healthy",
         ("wird gesund", "healthy"),
         "Core German sentence: Der Mann wird gesund. "
         "State changes toward healthy. "
         "Japanese cue: 〜になる (男の人が元気になる). Chinese cue: 恢復健康 or 變得健康. "
         "Vary the subject across the 4 pairs: man (Mann), child (Kind), woman (Frau), boy (Junge). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird gesund visible in every German line."),
        # ── Full / empty ───────────────────────────────────────────────────────
        ("013_change_voll.md",
         "werden + voll — containers become full",
         ("wird voll", "full"),
         "Core German sentence: Der Becher wird voll. "
         "State changes toward full. "
         "Japanese cue: 〜になる (コップがいっぱいになる). Chinese cue: 變滿 or 裝滿了. "
         "Vary the subject across the 4 pairs: cup (Becher), bucket (Eimer), basket (Korb), bowl (Schüssel). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird voll visible in every German line."),
        ("014_change_leer.md",
         "werden + leer — containers become empty",
         ("wird leer", "empty"),
         "Core German sentence: Der Becher wird leer. "
         "State changes toward empty. "
         "Japanese cue: 〜になる (コップが空になる). Chinese cue: 變空 or 空掉了. "
         "Vary the subject across the 4 pairs: cup (Becher), bucket (Eimer), bottle (Flasche), bowl (Schüssel). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird leer visible in every German line."),
        # ── Clean / dirty ──────────────────────────────────────────────────────
        ("015_change_sauber.md",
         "werden + sauber — surfaces and objects become clean",
         ("wird sauber", "clean"),
         "Core German sentence: Der Boden wird sauber. "
         "State changes toward clean. "
         "Japanese cue: 〜になる (床がきれいになる). Chinese cue: 變乾淨 or 乾淨了. "
         "Vary the subject across the 4 pairs: floor (Boden), bowl (Schüssel), cup (Becher), window (Fenster). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird sauber visible in every German line."),
        ("016_change_schmutzig.md",
         "werden + schmutzig — surfaces become dirty",
         ("wird schmutzig", "dirty"),
         "Core German sentence: Der Boden wird schmutzig. "
         "State changes toward dirty. "
         "Japanese cue: 〜くなる (床が汚くなる). Chinese cue: 變髒 or 髒了. "
         "Vary the subject across the 4 pairs: floor (Boden), cup (Becher), ball (Ball), window (Fenster). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird schmutzig visible in every German line."),
        # ── Broken ────────────────────────────────────────────────────────────
        ("017_change_kaputt.md",
         "werden + kaputt — objects break",
         ("wird kaputt", "broken"),
         "Core German sentence: Der Stuhl wird kaputt. "
         "State changes toward broken. "
         "Japanese cue: 〜になる (椅子が壊れる). Chinese cue: 壞掉了 or 壞了. "
         "Vary the subject across the 4 pairs: chair (Stuhl), table (Tisch), bike (Fahrrad), cup (Becher). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird kaputt visible in every German line."),
        # ── Light / dark ──────────────────────────────────────────────────────
        ("018_change_hell.md",
         "werden + hell — spaces become bright",
         ("wird hell", "bright"),
         "Core German sentence: Das Zimmer wird hell. "
         "State changes toward bright/light. "
         "Japanese cue: 〜くなる (部屋が明るくなる). Chinese cue: 變亮 or 亮起來了. "
         "Vary the subject across the 4 pairs: room (Zimmer), garden (Garten), floor (Boden), road (Straße). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird hell visible in every German line."),
        ("019_change_dunkel.md",
         "werden + dunkel — spaces become dark",
         ("wird dunkel", "dark"),
         "Core German sentence: Das Zimmer wird dunkel. "
         "State changes toward dark. "
         "Japanese cue: 〜くなる (部屋が暗くなる). Chinese cue: 變暗 or 暗下來了. "
         "Vary the subject across the 4 pairs: room (Zimmer), garden (Garten), forest (Wald), road (Straße). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird dunkel visible in every German line."),
        # ── Loud / quiet ──────────────────────────────────────────────────────
        ("020_change_laut.md",
         "werden + laut — beings and spaces become loud",
         ("wird laut", "loud"),
         "Core German sentence: Der Hund wird laut. "
         "State changes toward loud. "
         "Japanese cue: 〜くなる (犬がうるさくなる). Chinese cue: 變吵 or 吵起來了. "
         "Vary the subject across the 4 pairs: dog (Hund), child (Kind), man (Mann), room (Zimmer). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird laut visible in every German line."),
        ("021_change_leise.md",
         "werden + leise — beings and spaces become quiet",
         ("wird leise", "quiet"),
         "Core German sentence: Das Kind wird leise. "
         "State changes toward quiet. "
         "Japanese cue: 〜になる (子どもが静かになる). Chinese cue: 變安靜 or 安靜下來了. "
         "Vary the subject across the 4 pairs: child (Kind), dog (Hund), room (Zimmer), forest (Wald). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird leise visible in every German line."),
        # ── Heavy / light ─────────────────────────────────────────────────────
        ("022_change_schwer.md",
         "werden + schwer — objects become heavy",
         ("wird schwer", "heavy"),
         "Core German sentence: Der Korb wird schwer. "
         "State changes toward heavy. "
         "Japanese cue: 〜くなる (かごが重くなる). Chinese cue: 變重 or 重了. "
         "Vary the subject across the 4 pairs: basket (Korb), bucket (Eimer), bag (Tasche), book (Buch). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird schwer visible in every German line."),
        ("023_change_leicht.md",
         "werden + leicht — objects become light",
         ("wird leicht", "light"),
         "Core German sentence: Der Korb wird leicht. "
         "State changes toward light in weight. "
         "Japanese cue: 〜くなる (かごが軽くなる). Chinese cue: 變輕 or 輕了. "
         "Vary the subject across the 4 pairs: basket (Korb), bucket (Eimer), bag (Tasche), ball (Ball). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird leicht visible in every German line."),
        # ── Open / closed ─────────────────────────────────────────────────────
        ("024_change_offen.md",
         "werden + offen — doors and containers become open",
         ("wird offen", "open"),
         "Core German sentence: Die Tür wird offen. "
         "State changes toward open. "
         "Japanese cue: 〜になる (ドアが開いた状態になる). Chinese cue: 變開了 or 開著了. "
         "Vary the subject across the 4 pairs: door (Tür), window (Fenster), box (Kiste), basket (Korb). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird offen visible in every German line."),
        ("025_change_geschlossen.md",
         "werden + geschlossen — doors and spaces become closed",
         ("wird geschlossen", "closed"),
         "Core German sentence: Die Tür wird geschlossen. "
         "State changes toward closed. "
         "Japanese cue: 〜になる (ドアが閉まった状態になる). Chinese cue: 變關了 or 關上了. "
         "Vary the subject across the 4 pairs: door (Tür), window (Fenster), box (Kiste), school (Schule). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird geschlossen visible in every German line."),
        # ── Fresh / icy ───────────────────────────────────────────────────────
        ("026_change_frisch.md",
         "werden + frisch — food and air become fresh",
         ("wird frisch", "fresh"),
         "Core German sentence: Das Brot wird frisch. "
         "State changes toward fresh. "
         "Japanese cue: 〜になる (パンが新鮮になる). Chinese cue: 變新鮮 or 新鮮了. "
         "Vary the subject across the 4 pairs: bread (Brot), apple (Apfel), air (Luft), room (Zimmer). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird frisch visible in every German line."),
        ("027_change_eisig.md",
         "werden + eisig — water and surfaces become icy",
         ("wird eisig", "icy"),
         "Core German sentence: Das Wasser wird eisig. "
         "State changes toward icy cold. "
         "Japanese cue: 〜くなる (水が氷のように冷たくなる). Chinese cue: 變冰冷 or 結冰了. "
         "Vary the subject across the 4 pairs: water (Wasser), floor (Boden), air (Luft), cup (Becher). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird eisig visible in every German line."),
        # ── Smooth / rough ────────────────────────────────────────────────────
        ("028_change_glatt.md",
         "werden + glatt — surfaces become smooth",
         ("wird glatt", "smooth"),
         "Core German sentence: Der Boden wird glatt. "
         "State changes toward smooth. "
         "Japanese cue: 〜になる (床が滑らかになる). Chinese cue: 變光滑 or 光滑了. "
         "Vary the subject across the 4 pairs: floor (Boden), wall (Wand), road (Straße), table (Tisch). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird glatt visible in every German line."),
        ("029_change_rau.md",
         "werden + rau — surfaces become rough",
         ("wird rau", "rough"),
         "Core German sentence: Der Boden wird rau. "
         "State changes toward rough. "
         "Japanese cue: 〜くなる (床が荒くなる). Chinese cue: 變粗糙 or 粗糙了. "
         "Vary the subject across the 4 pairs: floor (Boden), wall (Wand), table (Tisch), road (Straße). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird rau visible in every German line."),
        # ── Sweet ─────────────────────────────────────────────────────────────
        ("030_change_suss.md",
         "werden + süß — food becomes sweet",
         ("wird süß", "sweet"),
         "Core German sentence: Der Apfel wird süß. "
         "State changes toward sweet. "
         "Japanese cue: 〜くなる (りんごが甘くなる). Chinese cue: 變甜 or 甜了. "
         "Vary the subject across the 4 pairs: apple (Apfel), cake (Kuchen), milk (Milch), soup (Suppe). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird süß visible in every German line."),
        # ── Hunger / thirst / satiation ───────────────────────────────────────
        ("031_change_hungrig.md",
         "werden + hungrig — beings become hungry",
         ("wird hungrig", "hungry"),
         "Core German sentence: Das Kind wird hungrig. "
         "State changes toward hungry. "
         "Japanese cue: 〜になる (子どもがお腹が空くようになる). Chinese cue: 變餓 or 餓了. "
         "Vary the subject across the 4 pairs: child (Kind), dog (Hund), man (Mann), woman (Frau). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird hungrig visible in every German line."),
        ("032_change_durstig.md",
         "werden + durstig — beings become thirsty",
         ("wird durstig", "thirsty"),
         "Core German sentence: Das Kind wird durstig. "
         "State changes toward thirsty. "
         "Japanese cue: 〜になる (子どものどが渇くようになる). Chinese cue: 變口渴 or 渴了. "
         "Vary the subject across the 4 pairs: child (Kind), dog (Hund), man (Mann), woman (Frau). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird durstig visible in every German line."),
        ("033_change_satt.md",
         "werden + satt — beings become full/satiated",
         ("wird satt", "full"),
         "Core German sentence: Das Kind wird satt. "
         "State changes toward full/satiated. "
         "Japanese cue: 〜になる (子どもがお腹がいっぱいになる). Chinese cue: 吃飽了 or 變飽了. "
         "Vary the subject across the 4 pairs: child (Kind), dog (Hund), man (Mann), woman (Frau). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird satt visible in every German line."),
        # ── Strong / weak ─────────────────────────────────────────────────────
        ("034_change_stark.md",
         "werden + stark — beings become strong",
         ("wird stark", "strong"),
         "Core German sentence: Der Junge wird stark. "
         "State changes toward strong. "
         "Japanese cue: 〜くなる (男の子が強くなる). Chinese cue: 變強壯 or 強了. "
         "Vary the subject across the 4 pairs: boy (Junge), man (Mann), dog (Hund), horse (Pferd). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird stark visible in every German line."),
        ("035_change_schwach.md",
         "werden + schwach — beings become weak",
         ("wird schwach", "weak"),
         "Core German sentence: Der Mann wird schwach. "
         "State changes toward weak. "
         "Japanese cue: 〜くなる (男の人が弱くなる). Chinese cue: 變虛弱 or 弱了. "
         "Vary the subject across the 4 pairs: man (Mann), child (Kind), woman (Frau), dog (Hund). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird schwach visible in every German line."),
        # ── Calm / still ──────────────────────────────────────────────────────
        ("036_change_ruhig.md",
         "werden + ruhig — beings and spaces become calm",
         ("wird ruhig", "calm"),
         "Core German sentence: Das Kind wird ruhig. "
         "State changes toward calm. "
         "Japanese cue: 〜になる (子どもが静かになる). Chinese cue: 變平靜 or 安靜下來了. "
         "Vary the subject across the 4 pairs: child (Kind), dog (Hund), room (Zimmer), forest (Wald). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird ruhig visible in every German line."),
        ("037_change_still.md",
         "werden + still — beings and spaces become still/silent",
         ("wird still", "still"),
         "Core German sentence: Das Kind wird still. "
         "State changes toward still/silent. "
         "Japanese cue: 〜になる (子どもが静まりかえる). Chinese cue: 變寂靜 or 安靜了. "
         "Vary the subject across the 4 pairs: child (Kind), room (Zimmer), dog (Hund), forest (Wald). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird still visible in every German line."),
        # ── Happy / sad emotions ───────────────────────────────────────────────
        ("038_change_gluecklich.md",
         "werden + glücklich — beings become happy",
         ("wird glücklich", "happy"),
         "Core German sentence: Das Kind wird glücklich. "
         "State changes toward happy. "
         "Japanese cue: 〜になる (子どもが幸せになる). Chinese cue: 變快樂 or 快樂了. "
         "Vary the subject across the 4 pairs: child (Kind), man (Mann), woman (Frau), boy (Junge). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird glücklich visible in every German line."),
        ("039_change_traurig.md",
         "werden + traurig — beings become sad",
         ("wird traurig", "sad"),
         "Core German sentence: Das Kind wird traurig. "
         "State changes toward sad. "
         "Japanese cue: 〜くなる (子どもが悲しくなる). Chinese cue: 變悲傷 or 難過了. "
         "Vary the subject across the 4 pairs: child (Kind), man (Mann), woman (Frau), dog (Hund). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird traurig visible in every German line."),
        ("040_change_froh.md",
         "werden + froh — beings become glad",
         ("wird froh", "glad"),
         "Core German sentence: Das Kind wird froh. "
         "State changes toward glad. "
         "Japanese cue: 〜くなる (子どもが嬉しくなる). Chinese cue: 變開心 or 高興了. "
         "Vary the subject across the 4 pairs: child (Kind), man (Mann), woman (Frau), girl (Mädchen). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird froh visible in every German line."),
        # ── Anger emotions ────────────────────────────────────────────────────
        ("041_change_boese.md",
         "werden + böse — beings become angry/cross",
         ("wird böse", "angry"),
         "Core German sentence: Das Kind wird böse. "
         "State changes toward angry or naughty. "
         "Japanese cue: 〜になる (子どもが怒るようになる). Chinese cue: 變生氣 or 生氣了. "
         "Vary the subject across the 4 pairs: child (Kind), dog (Hund), man (Mann), woman (Frau). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird böse visible in every German line."),
        ("042_change_wuetend.md",
         "werden + wütend — beings become furious",
         ("wird wütend", "furious"),
         "Core German sentence: Der Mann wird wütend. "
         "State changes toward furious. "
         "Japanese cue: 〜になる (男の人が怒りっぽくなる). Chinese cue: 變憤怒 or 怒了. "
         "Vary the subject across the 4 pairs: man (Mann), child (Kind), woman (Frau), dog (Hund). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird wütend visible in every German line."),
        # ── Nervous / excited ─────────────────────────────────────────────────
        ("043_change_nervos.md",
         "werden + nervös — beings become nervous",
         ("wird nervös", "nervous"),
         "Core German sentence: Das Kind wird nervös. "
         "State changes toward nervous. "
         "Japanese cue: 〜になる (子どもが緊張するようになる). Chinese cue: 變緊張 or 緊張了. "
         "Vary the subject across the 4 pairs: child (Kind), man (Mann), woman (Frau), dog (Hund). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird nervös visible in every German line."),
        ("044_change_aufgeregt.md",
         "werden + aufgeregt — beings become excited",
         ("wird aufgeregt", "excited"),
         "Core German sentence: Das Kind wird aufgeregt. "
         "State changes toward excited. "
         "Japanese cue: 〜になる (子どもが興奮するようになる). Chinese cue: 變興奮 or 興奮了. "
         "Vary the subject across the 4 pairs: child (Kind), man (Mann), woman (Frau), boy (Junge). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird aufgeregt visible in every German line."),
        # ── Proud / pale ──────────────────────────────────────────────────────
        ("045_change_stolz.md",
         "werden + stolz — beings become proud",
         ("wird stolz", "proud"),
         "Core German sentence: Der Junge wird stolz. "
         "State changes toward proud. "
         "Japanese cue: 〜になる (男の子が誇らしくなる). Chinese cue: 變得驕傲 or 驕傲了. "
         "Vary the subject across the 4 pairs: boy (Junge), man (Mann), woman (Frau), girl (Mädchen). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird stolz visible in every German line."),
        ("046_change_blass.md",
         "werden + blass — beings become pale",
         ("wird blass", "pale"),
         "Core German sentence: Das Kind wird blass. "
         "State changes toward pale. "
         "Japanese cue: 〜くなる (子どもが青白くなる). Chinese cue: 變蒼白 or 臉色發白. "
         "Vary the subject across the 4 pairs: child (Kind), man (Mann), woman (Frau), boy (Junge). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird blass visible in every German line."),
        # ── Ready / done ──────────────────────────────────────────────────────
        ("047_change_fertig.md",
         "werden + fertig — things and beings become finished/ready",
         ("wird fertig", "finished"),
         "Core German sentence: Das Brot wird fertig. "
         "State changes toward finished/ready. "
         "Japanese cue: 〜になる (パンが仕上がる). Chinese cue: 完成了 or 好了. "
         "Vary the subject across the 4 pairs: bread (Brot), cake (Kuchen), child (Kind), man (Mann). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird fertig visible in every German line."),
        ("048_change_bereit.md",
         "werden + bereit — beings become ready",
         ("wird bereit", "ready"),
         "Core German sentence: Das Kind wird bereit. "
         "State changes toward ready/prepared. "
         "Japanese cue: 〜になる (子どもが準備できるようになる). Chinese cue: 準備好了 or 變得準備好了. "
         "Vary the subject across the 4 pairs: child (Kind), man (Mann), woman (Frau), boy (Junge). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird bereit visible in every German line."),
        # ── Active / big ──────────────────────────────────────────────────────
        ("049_change_aktiv.md",
         "werden + aktiv — beings become active",
         ("wird aktiv", "active"),
         "Core German sentence: Das Kind wird aktiv. "
         "State changes toward active. "
         "Japanese cue: 〜になる (子どもが活発になる). Chinese cue: 變活躍 or 活躍了. "
         "Vary the subject across the 4 pairs: child (Kind), dog (Hund), man (Mann), boy (Junge). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird aktiv visible in every German line."),
        ("050_change_gross.md",
         "werden + groß — beings and things become big",
         ("wird groß", "big"),
         "Core German sentence: Das Kind wird groß. "
         "State changes toward big/tall. "
         "Japanese cue: 〜くなる (子どもが大きくなる). Chinese cue: 變大 or 長大了. "
         "Vary the subject across the 4 pairs: child (Kind), tree (Baum), dog (Hund), flower (Blume). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird groß visible in every German line."),
        # ── Old ───────────────────────────────────────────────────────────────
        ("051_change_alt.md",
         "werden + alt — objects become old/stale",
         ("wird alt", "old"),
         "Core German sentence: Das Brot wird alt. "
         "State changes toward old/stale. "
         "Japanese cue: 〜くなる (パンが古くなる). Chinese cue: 變舊 or 老了. "
         "Vary the subject across the 4 pairs: bread (Brot), cup (Becher), chair (Stuhl), table (Tisch). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird alt visible in every German line."),
        # ── Red ───────────────────────────────────────────────────────────────
        ("052_change_rot.md",
         "werden + rot — things become red",
         ("wird rot", "red"),
         "Core German sentence: Der Apfel wird rot. "
         "State changes toward red. "
         "Japanese cue: 〜くなる (りんごが赤くなる). Chinese cue: 變紅 or 紅了. "
         "Vary the subject across the 4 pairs: apple (Apfel), flower (Blume), child (Kind), boy (Junge). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird rot visible in every German line."),
        # ── Second-wave temperature (new subjects) ────────────────────────────
        ("053_change_kalt_b.md",
         "werden + kalt — drinks and surfaces become cold",
         ("wird kalt", "cold"),
         "Core German sentence: Die Milch wird kalt. "
         "State changes toward cold. "
         "Japanese cue: 〜くなる (牛乳が冷たくなる). Chinese cue: 變冷 or 冷掉了. "
         "Vary the subject across the 4 pairs: milk (Milch), tea (Tee), floor (Boden), wall (Wand). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird kalt visible in every German line."),
        ("054_change_warm_b.md",
         "werden + warm — drinks and spaces become warm",
         ("wird warm", "warm"),
         "Core German sentence: Die Milch wird warm. "
         "State changes toward warm. "
         "Japanese cue: 〜くなる (牛乳が温かくなる). Chinese cue: 變暖 or 暖了. "
         "Vary the subject across the 4 pairs: milk (Milch), tea (Tee), floor (Boden), road (Straße). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird warm visible in every German line."),
        ("055_change_heiss_b.md",
         "werden + heiß — different subjects become hot",
         ("wird heiß", "hot"),
         "Core German sentence: Die Milch wird heiß. "
         "State changes toward hot. "
         "Japanese cue: 〜くなる (牛乳が熱くなる). Chinese cue: 變熱 or 熱了. "
         "Vary the subject across the 4 pairs: milk (Milch), tea (Tee), floor (Boden), soup (Suppe). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird heiß visible in every German line."),
        ("056_change_kuehl_b.md",
         "werden + kühl — different subjects become cool",
         ("wird kühl", "cool"),
         "Core German sentence: Die Milch wird kühl. "
         "State changes toward cool. "
         "Japanese cue: 〜くなる (牛乳が涼しくなる). Chinese cue: 變涼 or 涼了. "
         "Vary the subject across the 4 pairs: milk (Milch), tea (Tee), floor (Boden), room (Zimmer). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird kühl visible in every German line."),
        # ── Second-wave physical (new subjects) ───────────────────────────────
        ("057_change_nass_b.md",
         "werden + nass — outdoor things and beings become wet",
         ("wird nass", "wet"),
         "Core German sentence: Der Hund wird nass. "
         "State changes toward wet. "
         "Japanese cue: 〜くなる (犬が濡れてくる). Chinese cue: 變濕 or 濕了. "
         "Vary the subject across the 4 pairs: dog (Hund), child (Kind), garden (Garten), road (Straße). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird nass visible in every German line."),
        ("058_change_trocken_b.md",
         "werden + trocken — outdoor things and beings become dry",
         ("wird trocken", "dry"),
         "Core German sentence: Der Hund wird trocken. "
         "State changes toward dry. "
         "Japanese cue: 〜くなる (犬が乾いてくる). Chinese cue: 變乾 or 乾了. "
         "Vary the subject across the 4 pairs: dog (Hund), child (Kind), garden (Garten), road (Straße). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird trocken visible in every German line."),
        ("059_change_hart_b.md",
         "werden + hart — surfaces become hard",
         ("wird hart", "hard"),
         "Core German sentence: Der Boden wird hart. "
         "State changes toward hard. "
         "Japanese cue: 〜くなる (床が固くなる). Chinese cue: 變硬 or 硬了. "
         "Vary the subject across the 4 pairs: floor (Boden), wall (Wand), road (Straße), table (Tisch). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird hart visible in every German line."),
        ("060_change_weich_b.md",
         "werden + weich — food becomes soft through cooking",
         ("wird weich", "soft"),
         "Core German sentence: Das Gemüse wird weich. "
         "State changes toward soft. "
         "Japanese cue: 〜くなる (野菜が柔らかくなる). Chinese cue: 變軟 or 軟了. "
         "Vary the subject across the 4 pairs: vegetables (Gemüse), bread (Brot), cake (Kuchen), soup (Suppe). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird weich visible in every German line."),
        # ── Second-wave living states (new subjects) ───────────────────────────
        ("061_change_muede_b.md",
         "werden + müde — different beings become tired",
         ("wird müde", "tired"),
         "Core German sentence: Der Junge wird müde. "
         "State changes toward tired. "
         "Japanese cue: 〜になる (男の子が疲れる). Chinese cue: 變累 or 累了. "
         "Vary the subject across the 4 pairs: boy (Junge), girl (Mädchen), teacher (Lehrer), horse (Pferd). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird müde visible in every German line."),
        ("062_change_wach_b.md",
         "werden + wach — different beings become awake",
         ("wird wach", "awake"),
         "Core German sentence: Der Junge wird wach. "
         "State changes toward awake. "
         "Japanese cue: 〜になる (男の子が目を覚ます). Chinese cue: 醒了 or 清醒了. "
         "Vary the subject across the 4 pairs: boy (Junge), girl (Mädchen), teacher (Lehrer), cat (Katze). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird wach visible in every German line."),
        ("063_change_krank_b.md",
         "werden + krank — different beings become sick",
         ("wird krank", "sick"),
         "Core German sentence: Die Frau wird krank. "
         "State changes toward sick. "
         "Japanese cue: 〜になる (女の人が病気になる). Chinese cue: 生病了 or 變得生病. "
         "Vary the subject across the 4 pairs: woman (Frau), girl (Mädchen), teacher (Lehrer), dog (Hund). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird krank visible in every German line."),
        ("064_change_gesund_b.md",
         "werden + gesund — different beings become healthy",
         ("wird gesund", "healthy"),
         "Core German sentence: Die Frau wird gesund. "
         "State changes toward healthy. "
         "Japanese cue: 〜になる (女の人が元気になる). Chinese cue: 恢復健康 or 健康了. "
         "Vary the subject across the 4 pairs: woman (Frau), girl (Mädchen), teacher (Lehrer), dog (Hund). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird gesund visible in every German line."),
        # ── Third-wave extensions ─────────────────────────────────────────────
        ("065_change_gross_b.md",
         "werden + groß — different subjects grow big",
         ("wird groß", "big"),
         "Core German sentence: Der Junge wird groß. "
         "State changes toward big/tall. "
         "Japanese cue: 〜くなる (男の子が大きくなる). Chinese cue: 變大 or 長大了. "
         "Vary the subject across the 4 pairs: boy (Junge), girl (Mädchen), horse (Pferd), bird (Vogel). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird groß visible in every German line."),
        ("066_change_hell_b.md",
         "werden + hell — different spaces become bright",
         ("wird hell", "bright"),
         "Core German sentence: Der Garten wird hell. "
         "State changes toward bright. "
         "Japanese cue: 〜くなる (庭が明るくなる). Chinese cue: 變亮 or 亮起來了. "
         "Vary the subject across the 4 pairs: garden (Garten), room (Zimmer), forest (Wald), floor (Boden). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird hell visible in every German line."),
        ("067_change_dunkel_b.md",
         "werden + dunkel — different spaces become dark",
         ("wird dunkel", "dark"),
         "Core German sentence: Der Garten wird dunkel. "
         "State changes toward dark. "
         "Japanese cue: 〜くなる (庭が暗くなる). Chinese cue: 變暗 or 暗下來了. "
         "Vary the subject across the 4 pairs: garden (Garten), room (Zimmer), forest (Wald), road (Straße). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird dunkel visible in every German line."),
        ("068_change_laut_b.md",
         "werden + laut — different beings and spaces become loud",
         ("wird laut", "loud"),
         "Core German sentence: Der Junge wird laut. "
         "State changes toward loud. "
         "Japanese cue: 〜くなる (男の子がうるさくなる). Chinese cue: 變吵 or 吵鬧起來了. "
         "Vary the subject across the 4 pairs: boy (Junge), girl (Mädchen), dog (Hund), room (Zimmer). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird laut visible in every German line."),
        ("069_change_leise_b.md",
         "werden + leise — different beings and spaces become quiet",
         ("wird leise", "quiet"),
         "Core German sentence: Der Junge wird leise. "
         "State changes toward quiet. "
         "Japanese cue: 〜になる (男の子が静かになる). Chinese cue: 變安靜 or 安靜下來了. "
         "Vary the subject across the 4 pairs: boy (Junge), girl (Mädchen), room (Zimmer), garden (Garten). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird leise visible in every German line."),
        ("070_change_sauber_b.md",
         "werden + sauber — different surfaces become clean",
         ("wird sauber", "clean"),
         "Core German sentence: Der Tisch wird sauber. "
         "State changes toward clean. "
         "Japanese cue: 〜になる (テーブルがきれいになる). Chinese cue: 變乾淨 or 乾淨了. "
         "Vary the subject across the 4 pairs: table (Tisch), chair (Stuhl), window (Fenster), bag (Tasche). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird sauber visible in every German line."),
        ("071_change_schmutzig_b.md",
         "werden + schmutzig — beings and objects become dirty",
         ("wird schmutzig", "dirty"),
         "Core German sentence: Der Hund wird schmutzig. "
         "State changes toward dirty. "
         "Japanese cue: 〜くなる (犬が汚くなる). Chinese cue: 變髒 or 髒了. "
         "Vary the subject across the 4 pairs: dog (Hund), child (Kind), chair (Stuhl), bag (Tasche). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird schmutzig visible in every German line."),
        ("072_change_kaputt_b.md",
         "werden + kaputt — different objects break",
         ("wird kaputt", "broken"),
         "Core German sentence: Die Flasche wird kaputt. "
         "State changes toward broken. "
         "Japanese cue: 〜になる (ボトルが壊れる). Chinese cue: 壞掉了 or 破了. "
         "Vary the subject across the 4 pairs: bottle (Flasche), basket (Korb), bowl (Schüssel), bag (Tasche). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird kaputt visible in every German line."),
        ("073_change_schwer_b.md",
         "werden + schwer — different objects become heavy",
         ("wird schwer", "heavy"),
         "Core German sentence: Die Tasche wird schwer. "
         "State changes toward heavy. "
         "Japanese cue: 〜くなる (袋が重くなる). Chinese cue: 變重 or 重了. "
         "Vary the subject across the 4 pairs: bag (Tasche), box (Kiste), basket (Korb), bottle (Flasche). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird schwer visible in every German line."),
        ("074_change_leicht_b.md",
         "werden + leicht — different objects become light",
         ("wird leicht", "light"),
         "Core German sentence: Die Tasche wird leicht. "
         "State changes toward light in weight. "
         "Japanese cue: 〜くなる (袋が軽くなる). Chinese cue: 變輕 or 輕了. "
         "Vary the subject across the 4 pairs: bag (Tasche), box (Kiste), bottle (Flasche), bowl (Schüssel). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird leicht visible in every German line."),
        ("075_change_voll_b.md",
         "werden + voll — different containers become full",
         ("wird voll", "full"),
         "Core German sentence: Die Kiste wird voll. "
         "State changes toward full. "
         "Japanese cue: 〜になる (箱がいっぱいになる). Chinese cue: 變滿 or 裝滿了. "
         "Vary the subject across the 4 pairs: box (Kiste), bottle (Flasche), bag (Tasche), bowl (Schüssel). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird voll visible in every German line."),
        ("076_change_leer_b.md",
         "werden + leer — different containers become empty",
         ("wird leer", "empty"),
         "Core German sentence: Die Kiste wird leer. "
         "State changes toward empty. "
         "Japanese cue: 〜になる (箱が空になる). Chinese cue: 變空 or 空了. "
         "Vary the subject across the 4 pairs: box (Kiste), bottle (Flasche), bag (Tasche), basket (Korb). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird leer visible in every German line."),
        # ── Fourth-wave emotion extensions ────────────────────────────────────
        ("077_change_gluecklich_b.md",
         "werden + glücklich — different beings become happy",
         ("wird glücklich", "happy"),
         "Core German sentence: Der Junge wird glücklich. "
         "State changes toward happy. "
         "Japanese cue: 〜になる (男の子が幸せになる). Chinese cue: 變快樂 or 快樂了. "
         "Vary the subject across the 4 pairs: boy (Junge), girl (Mädchen), dog (Hund), teacher (Lehrer). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird glücklich visible in every German line."),
        ("078_change_traurig_b.md",
         "werden + traurig — different beings become sad",
         ("wird traurig", "sad"),
         "Core German sentence: Der Junge wird traurig. "
         "State changes toward sad. "
         "Japanese cue: 〜くなる (男の子が悲しくなる). Chinese cue: 變悲傷 or 難過了. "
         "Vary the subject across the 4 pairs: boy (Junge), girl (Mädchen), dog (Hund), teacher (Lehrer). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird traurig visible in every German line."),
        ("079_change_kalt_c.md",
         "werden + kalt — animals and rooms become cold",
         ("wird kalt", "cold"),
         "Core German sentence: Der Hund wird kalt. "
         "State changes toward cold. "
         "Japanese cue: 〜くなる (犬が冷たくなる). Chinese cue: 變冷 or 冷了. "
         "Vary the subject across the 4 pairs: dog (Hund), cat (Katze), room (Zimmer), floor (Boden). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird kalt visible in every German line."),
        ("080_change_warm_c.md",
         "werden + warm — spaces and nature become warm",
         ("wird warm", "warm"),
         "Core German sentence: Der Garten wird warm. "
         "State changes toward warm. "
         "Japanese cue: 〜くなる (庭が温かくなる). Chinese cue: 變暖 or 暖了. "
         "Vary the subject across the 4 pairs: garden (Garten), room (Zimmer), road (Straße), floor (Boden). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird warm visible in every German line."),
        ("081_change_stark_b.md",
         "werden + stark — different beings become strong",
         ("wird stark", "strong"),
         "Core German sentence: Das Kind wird stark. "
         "State changes toward strong. "
         "Japanese cue: 〜くなる (子どもが強くなる). Chinese cue: 變強壯 or 強了. "
         "Vary the subject across the 4 pairs: child (Kind), girl (Mädchen), cat (Katze), bird (Vogel). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird stark visible in every German line."),
        ("082_change_schwach_b.md",
         "werden + schwach — different beings become weak",
         ("wird schwach", "weak"),
         "Core German sentence: Das Kind wird schwach. "
         "State changes toward weak. "
         "Japanese cue: 〜くなる (子どもが弱くなる). Chinese cue: 變虛弱 or 弱了. "
         "Vary the subject across the 4 pairs: child (Kind), girl (Mädchen), cat (Katze), bird (Vogel). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird schwach visible in every German line."),
        ("083_change_hungrig_b.md",
         "werden + hungrig — different beings become hungry",
         ("wird hungrig", "hungry"),
         "Core German sentence: Der Junge wird hungrig. "
         "State changes toward hungry. "
         "Japanese cue: 〜になる (男の子がお腹が空くようになる). Chinese cue: 變餓 or 餓了. "
         "Vary the subject across the 4 pairs: boy (Junge), girl (Mädchen), cat (Katze), horse (Pferd). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird hungrig visible in every German line."),
        ("084_change_durstig_b.md",
         "werden + durstig — different beings become thirsty",
         ("wird durstig", "thirsty"),
         "Core German sentence: Der Junge wird durstig. "
         "State changes toward thirsty. "
         "Japanese cue: 〜になる (男の子のどが渇くようになる). Chinese cue: 變口渴 or 渴了. "
         "Vary the subject across the 4 pairs: boy (Junge), girl (Mädchen), cat (Katze), horse (Pferd). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird durstig visible in every German line."),
        ("085_change_ruhig_b.md",
         "werden + ruhig — different spaces and beings become calm",
         ("wird ruhig", "calm"),
         "Core German sentence: Der Garten wird ruhig. "
         "State changes toward calm. "
         "Japanese cue: 〜になる (庭が静かになる). Chinese cue: 變平靜 or 平靜了. "
         "Vary the subject across the 4 pairs: garden (Garten), road (Straße), boy (Junge), dog (Hund). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird ruhig visible in every German line."),
        ("086_change_still_b.md",
         "werden + still — different spaces and beings become still",
         ("wird still", "still"),
         "Core German sentence: Der Garten wird still. "
         "State changes toward still/silent. "
         "Japanese cue: 〜になる (庭が静まりかえる). Chinese cue: 變寂靜 or 沉靜了. "
         "Vary the subject across the 4 pairs: garden (Garten), road (Straße), boy (Junge), cat (Katze). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird still visible in every German line."),
        ("087_change_fertig_b.md",
         "werden + fertig — different things become finished",
         ("wird fertig", "finished"),
         "Core German sentence: Das Haus wird fertig. "
         "State changes toward finished. "
         "Japanese cue: 〜になる (家が仕上がる). Chinese cue: 完成了 or 好了. "
         "Vary the subject across the 4 pairs: house (Haus), table (Tisch), basket (Korb), man (Mann). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird fertig visible in every German line."),
        ("088_change_boese_b.md",
         "werden + böse — different beings become angry",
         ("wird böse", "angry"),
         "Core German sentence: Der Junge wird böse. "
         "State changes toward angry or cross. "
         "Japanese cue: 〜になる (男の子が怒るようになる). Chinese cue: 變生氣 or 生氣了. "
         "Vary the subject across the 4 pairs: boy (Junge), girl (Mädchen), teacher (Lehrer), cat (Katze). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird böse visible in every German line."),
        ("089_change_wuetend_b.md",
         "werden + wütend — different beings become furious",
         ("wird wütend", "furious"),
         "Core German sentence: Der Junge wird wütend. "
         "State changes toward furious. "
         "Japanese cue: 〜になる (男の子が怒りっぽくなる). Chinese cue: 變憤怒 or 怒了. "
         "Vary the subject across the 4 pairs: boy (Junge), girl (Mädchen), teacher (Lehrer), dog (Hund). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird wütend visible in every German line."),
        ("090_change_nervos_b.md",
         "werden + nervös — different beings become nervous",
         ("wird nervös", "nervous"),
         "Core German sentence: Der Junge wird nervös. "
         "State changes toward nervous. "
         "Japanese cue: 〜になる (男の子が緊張するようになる). Chinese cue: 變緊張 or 緊張了. "
         "Vary the subject across the 4 pairs: boy (Junge), girl (Mädchen), teacher (Lehrer), cat (Katze). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird nervös visible in every German line."),
        ("091_change_froh_b.md",
         "werden + froh — different beings become glad",
         ("wird froh", "glad"),
         "Core German sentence: Der Junge wird froh. "
         "State changes toward glad. "
         "Japanese cue: 〜くなる (男の子が嬉しくなる). Chinese cue: 變開心 or 高興了. "
         "Vary the subject across the 4 pairs: boy (Junge), girl (Mädchen), teacher (Lehrer), dog (Hund). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird froh visible in every German line."),
        ("092_change_stolz_b.md",
         "werden + stolz — different beings become proud",
         ("wird stolz", "proud"),
         "Core German sentence: Das Mädchen wird stolz. "
         "State changes toward proud. "
         "Japanese cue: 〜になる (女の子が誇らしくなる). Chinese cue: 變得驕傲 or 驕傲了. "
         "Vary the subject across the 4 pairs: girl (Mädchen), boy (Junge), teacher (Lehrer), doctor (Arzt). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird stolz visible in every German line."),
        ("093_change_blass_b.md",
         "werden + blass — different beings become pale",
         ("wird blass", "pale"),
         "Core German sentence: Der Junge wird blass. "
         "State changes toward pale. "
         "Japanese cue: 〜くなる (男の子が青白くなる). Chinese cue: 變蒼白 or 臉色發白. "
         "Vary the subject across the 4 pairs: boy (Junge), girl (Mädchen), teacher (Lehrer), doctor (Arzt). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird blass visible in every German line."),
        ("094_change_aufgeregt_b.md",
         "werden + aufgeregt — different beings become excited",
         ("wird aufgeregt", "excited"),
         "Core German sentence: Der Junge wird aufgeregt. "
         "State changes toward excited. "
         "Japanese cue: 〜になる (男の子が興奮するようになる). Chinese cue: 變興奮 or 興奮了. "
         "Vary the subject across the 4 pairs: boy (Junge), girl (Mädchen), dog (Hund), teacher (Lehrer). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird aufgeregt visible in every German line."),
        ("095_change_satt_b.md",
         "werden + satt — different beings become satiated",
         ("wird satt", "full"),
         "Core German sentence: Der Junge wird satt. "
         "State changes toward full/satiated. "
         "Japanese cue: 〜になる (男の子がお腹がいっぱいになる). Chinese cue: 吃飽了 or 飽了. "
         "Vary the subject across the 4 pairs: boy (Junge), girl (Mädchen), cat (Katze), horse (Pferd). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird satt visible in every German line."),
        ("096_change_aktiv_b.md",
         "werden + aktiv — different beings become active",
         ("wird aktiv", "active"),
         "Core German sentence: Das Mädchen wird aktiv. "
         "State changes toward active. "
         "Japanese cue: 〜になる (女の子が活発になる). Chinese cue: 變活躍 or 活躍了. "
         "Vary the subject across the 4 pairs: girl (Mädchen), boy (Junge), cat (Katze), horse (Pferd). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird aktiv visible in every German line."),
        ("097_change_alt_b.md",
         "werden + alt — different objects become old",
         ("wird alt", "old"),
         "Core German sentence: Die Tasche wird alt. "
         "State changes toward old/worn. "
         "Japanese cue: 〜くなる (袋が古くなる). Chinese cue: 變舊 or 舊了. "
         "Vary the subject across the 4 pairs: bag (Tasche), basket (Korb), blanket (Decke), book (Buch). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird alt visible in every German line."),
        ("098_change_frisch_b.md",
         "werden + frisch — different foods and spaces become fresh",
         ("wird frisch", "fresh"),
         "Core German sentence: Das Gemüse wird frisch. "
         "State changes toward fresh. "
         "Japanese cue: 〜になる (野菜が新鮮になる). Chinese cue: 變新鮮 or 新鮮了. "
         "Vary the subject across the 4 pairs: vegetables (Gemüse), apple (Apfel), room (Zimmer), air (Luft). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird frisch visible in every German line."),
        ("099_change_offen_b.md",
         "werden + offen — different containers and spaces become open",
         ("wird offen", "open"),
         "Core German sentence: Die Flasche wird offen. "
         "State changes toward open. "
         "Japanese cue: 〜になる (ボトルが開いた状態になる). Chinese cue: 變開了 or 開了. "
         "Vary the subject across the 4 pairs: bottle (Flasche), bag (Tasche), bowl (Schüssel), school (Schule). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird offen visible in every German line."),
        ("100_change_geschlossen_b.md",
         "werden + geschlossen — different spaces and containers become closed",
         ("wird geschlossen", "closed"),
         "Core German sentence: Die Flasche wird geschlossen. "
         "State changes toward closed. "
         "Japanese cue: 〜になる (ボトルが閉まった状態になる). Chinese cue: 變關了 or 關了. "
         "Vary the subject across the 4 pairs: bottle (Flasche), bag (Tasche), bowl (Schüssel), school (Schule). "
         "Use werden as the change-of-state copula only. Do not use movement verbs. "
         "Keep wird geschlossen visible in every German line."),
    ]

    shared_suffix = (
        " Use werden as the change-of-state copula throughout — not as an auxiliary or future tense. "
        "Avoid all movement verbs (goes, walks, runs, geht, läuft). "
        "JP: use 〜くなる for i-adjective predicates (cold, hot, warm, hard, soft, wet, dry) "
        "and 〜になる for na-adjective or noun predicates (tired, awake, sick, healthy). "
        "ZH: use 變得〜 or 變〜了 pattern. "
        "Keep vocabulary simple and concrete. Use only the nouns in the grammar lexicon."
    )

    return [
        FileSpec(
            path=f"04_change_state/{filename}",
            focus=focus,
            required_terms=required,
            notes=notes + shared_suffix,
        )
        for filename, focus, required, notes in rows
    ]


def make_bridge_specs() -> list[FileSpec]:
    """100 bridge course annotation files in three groups."""
    specs: list[FileSpec] = []
    agents = ["Emma", "Taro", "Gran"]

    # ── Group A (001–050): ditransitive — Wer/Wem/Was + plain ──────────────
    ga_verbs = [
        ("gives", "gibt", "gibt"),
        ("shows", "zeigt", "zeigt"),
        ("brings", "bringt", "bringt"),
        ("sends", "schickt", "schickt"),
        ("lends", "leiht", "leiht"),
    ]
    ga_receivers = [
        ("dem Jungen", "the boy", "jungen"),
        ("der Frau", "the woman", "frau"),
        ("dem Kind", "the child", "kind"),
        ("dem Arzt", "the doctor", "arzt"),
        ("dem Mann", "the man", "mann"),
        ("dem Lehrer", "the teacher", "lehrer"),
        ("dem Mädchen", "the girl", "maedchen"),
        ("dem Baby", "the baby", "baby"),
        ("dem Nachbarn", "the neighbor", "nachbarn"),
        ("dem Kind", "the child", "kindb"),
    ]
    ga_objects = [
        # (de_acc, en_obj, de_noun_stem, slug)
        ("den Apfel", "the apple", "Apfel", "apfel"),
        ("das Buch", "the book", "Buch", "buch"),
        ("den Becher", "the cup", "Becher", "becher"),
        ("den Ball", "the ball", "Ball", "ball"),
        ("den Korb", "the basket", "Korb", "korb"),
        ("das Brot", "the bread", "Brot", "brot"),
        ("den Bleistift", "the pencil", "Bleistift", "bleistift"),
        ("die Decke", "the blanket", "Decke", "decke"),
        ("den Apfel", "the apple", "Apfel", "apfelb"),
        ("das Buch", "the book", "Buch", "buchb"),
    ]

    fid = 1
    for vi, (en_v, de_v, v_slug) in enumerate(ga_verbs):
        for i in range(10):
            de_dat, en_recv, r_slug = ga_receivers[i]
            de_acc, en_obj, acc_noun, o_slug = ga_objects[i]
            agent = agents[(vi * 10 + i) % 3]
            fname = f"{fid:03d}_bridge_{v_slug}_{r_slug}.md"
            notes = (
                f"Bridge file Group A — ditransitive, 3 role question pairs (Wer/Wem/Was) plus plain block. "
                f"Core German sentence: {agent} {de_v} {de_dat} {de_acc}. "
                f"SECTION 1 annotated DE line: ({agent}) *{de_v}* [{de_dat}] {{{de_acc}}}. "
                f"SECTION 1 annotated EN line: ({agent}) *{en_v}* [{en_recv}] {{{en_obj}}}. "
                f"Generate matching JP annotated line: () for が-subject, [] for に-receiver, {{}} for を-object, ** at sentence end wrapping the verb. "
                f"Generate matching ZH annotated line: () for subject, [] for beneficiary receiver, {{}} for direct object, ** wrapping the verb. "
                f"SECTION 2: generate only Wer, Wem, Was question pairs in that order. No genitive question. "
                f"SECTION 3: plain sentences with no bracket markers."
            )
            specs.append(FileSpec(
                path=f"bridge_course/{fname}",
                focus=f"bridge ditransitive: {agent} {en_v} {en_recv} {en_obj}",
                required_terms=(de_dat, de_v, acc_noun),
                notes=notes,
            ))
            fid += 1

    assert fid == 51

    # ── Group B (051–070): ditransitive + genitive — Wer/Wem/Was/Wessen + plain ──
    gb_verbs = [
        ("gives", "gibt", "gibt"),
        ("shows", "zeigt", "zeigt"),
        ("brings", "bringt", "bringt"),
        ("sends", "schickt", "schickt"),
    ]
    gb_configs = [
        # (de_dat, en_recv, r_slug, de_acc_base, en_obj_base, de_gen, en_gen, acc_noun, slug)
        ("dem Jungen", "the boy", "jungen", "den Ball", "the ball", "des Mannes", "the man's", "Ball", "ball_mannes"),
        ("der Frau", "the woman", "frau", "das Buch", "the book", "des Kindes", "the child's", "Buch", "buch_kindes"),
        ("dem Kind", "the child", "kind", "den Apfel", "the apple", "der Frau", "the woman's", "Apfel", "apfel_frau"),
        ("dem Arzt", "the doctor", "arzt", "den Becher", "the cup", "des Jungen", "the boy's", "Becher", "becher_jungen"),
        ("dem Mann", "the man", "mann", "den Korb", "the basket", "des Mädchens", "the girl's", "Korb", "korb_maedchens"),
    ]

    for vi, (en_v, de_v, v_slug) in enumerate(gb_verbs):
        for i in range(5):
            de_dat, en_recv, r_slug, de_acc_base, en_obj_base, de_gen, en_gen, acc_noun, cfg_slug = gb_configs[i]
            agent = agents[(vi * 5 + i) % 3]
            fname = f"{fid:03d}_bridge_{v_slug}_{r_slug}_{cfg_slug}.md"
            notes = (
                f"Bridge file Group B — ditransitive with genitive modifier, 4 role question pairs (Wer/Wem/Was/Wessen) plus plain block. "
                f"Core German sentence: {agent} {de_v} {de_dat} {de_acc_base} {de_gen}. "
                f"SECTION 1 annotated DE line: ({agent}) *{de_v}* [{de_dat}] {{{de_acc_base} <{de_gen}>}}. "
                f"SECTION 1 annotated EN line: ({agent}) *{en_v}* [{en_recv}] {{{en_obj_base} <{en_gen}>}}. "
                f"The <> genitive bracket is nested inside the {{}} accusative bracket. "
                f"Generate matching JP annotated line: () for が-subject, [] for に-receiver, {{}} for を-object containing <> genitive, ** at sentence end. "
                f"Generate matching ZH annotated line: () for subject, [] for receiver, {{}} for object containing <> genitive, ** for verb. "
                f"SECTION 2: generate Wer, Wem, Was, Wessen question pairs in that order. "
                f"SECTION 3: plain sentences with no bracket markers."
            )
            specs.append(FileSpec(
                path=f"bridge_course/{fname}",
                focus=f"bridge ditransitive+genitive: {agent} {en_v} {en_recv} {en_gen} {en_obj_base}",
                required_terms=(de_dat, de_v, acc_noun, de_gen),
                notes=notes,
            ))
            fid += 1

    assert fid == 71

    # ── Group C (071–100): pure-dative verbs — Wer/Wem + plain ─────────────
    gc_verbs = [
        ("helps", "hilft", "hilft"),
        ("answers", "antwortet", "antwortet"),
        ("tells", "erzählt", "erzaehlt"),
    ]
    gc_receivers = [
        ("dem Jungen", "the boy", "jungen"),
        ("der Frau", "the woman", "frau"),
        ("dem Kind", "the child", "kind"),
        ("dem Arzt", "the doctor", "arzt"),
        ("dem Mann", "the man", "mann"),
        ("dem Lehrer", "the teacher", "lehrer"),
        ("dem Mädchen", "the girl", "maedchen"),
        ("dem Baby", "the baby", "baby"),
        ("dem Nachbarn", "the neighbor", "nachbarn"),
        ("dem Kind", "the child", "kindb"),
    ]

    for vi, (en_v, de_v, v_slug) in enumerate(gc_verbs):
        for i in range(10):
            de_dat, en_recv, r_slug = gc_receivers[i]
            agent = agents[(vi * 10 + i) % 3]
            fname = f"{fid:03d}_bridge_{v_slug}_{r_slug}.md"
            notes = (
                f"Bridge file Group C — pure dative verb, 2 role question pairs (Wer/Wem) plus plain block. "
                f"Core German sentence: {agent} {de_v} {de_dat}. "
                f"SECTION 1 annotated DE line: ({agent}) *{de_v}* [{de_dat}]. "
                f"SECTION 1 annotated EN line: ({agent}) *{en_v}* [{en_recv}]. "
                f"Generate matching JP annotated line: () for が-subject, [] for に-receiver, ** at sentence end. "
                f"Generate matching ZH annotated line: () for subject, [] for receiver, ** for verb. "
                f"SECTION 2: generate only Wer and Wem question pairs in that order. No Was, no genitive question. "
                f"SECTION 3: plain sentences with no bracket markers. "
                f"Do not add {{}} accusative or <> genitive brackets anywhere."
            )
            specs.append(FileSpec(
                path=f"bridge_course/{fname}",
                focus=f"bridge pure-dative: {agent} {en_v} {en_recv}",
                required_terms=(de_dat, de_v),
                notes=notes,
            ))
            fid += 1

    assert fid == 101
    return specs


def make_target_accusative_endpoint_specs() -> list[FileSpec]:
    """Specs for `06_target_accusative_endpoint`: two-way prepositions + accusative (movement endpoint)."""
    rows: list[tuple[str, str, tuple[str, ...], str]] = [
        # ── auf (onto) ─────────────────────────────────────────────────────
        ("001_auf_stellen_a.md",
         "auf + accusative — Emma stellt den Becher auf den Tisch (masc endpoint)",
         ("auf den Tisch", "stellt"),
         "Core German sentence: Emma stellt den Becher auf den Tisch. "
         "Movement endpoint: placing an object ONTO a surface. Accusative: auf den Tisch (masc). "
         "Vary the agent and placed object across the 4 pairs, keeping auf den Tisch every time. "
         "Use stellen (place upright) as the placement verb. "
         "JP cue: テーブルの上に置く (〜の上に + placement verb). ZH cue: 放到桌子上. "
         "Keep auf den Tisch visible in every German line."),
        ("002_auf_legen_a.md",
         "auf + accusative — Taro legt das Buch auf die Bank (fem endpoint)",
         ("auf die Bank", "legt"),
         "Core German sentence: Taro legt das Buch auf die Bank. "
         "Movement endpoint: laying an object ONTO a surface. Accusative: auf die Bank (fem). "
         "Vary the agent and object across 4 pairs, keeping auf die Bank every time. "
         "Use legen (lay flat) as the placement verb. "
         "JP cue: ベンチの上に置く (〜の上に + placement verb). ZH cue: 放到長椅上. "
         "Keep auf die Bank visible in every German line."),
        ("003_auf_legen_b.md",
         "auf + accusative — Gran legt die Decke auf das Bett (neut endpoint)",
         ("auf das Bett", "legt"),
         "Core German sentence: Gran legt die Decke auf das Bett. "
         "Movement endpoint: laying an object ONTO a surface. Accusative: auf das Bett (neut). "
         "Vary the agent and object across 4 pairs, keeping auf das Bett every time. "
         "Use legen (lay flat) as the placement verb. "
         "JP cue: ベッドの上に置く (〜の上に + placement verb). ZH cue: 放到床上. "
         "Keep auf das Bett visible in every German line."),
        ("004_auf_setzen_a.md",
         "auf + accusative — Das Kind setzt sich auf den Stuhl (masc endpoint, reflexive seating)",
         ("auf den Stuhl", "setzt"),
         "Core German sentence: Das Kind setzt sich auf den Stuhl. "
         "Movement endpoint: a person seats themselves ONTO a surface. Accusative: auf den Stuhl (masc). "
         "Vary the agent across 4 pairs: das Kind, Emma, Taro, Gran. Keep auf den Stuhl every time. "
         "Use setzen (seat/place). "
         "JP cue: 椅子に座る (に + 座る). ZH cue: 坐到椅子上. "
         "Keep auf den Stuhl visible in every German line."),
        ("005_auf_gehen_a.md",
         "auf + accusative — Emma geht auf den Markt (masc movement endpoint)",
         ("auf den Markt", "geht"),
         "Core German sentence: Emma geht auf den Markt. "
         "Movement endpoint: a person walks TO a destination. Accusative: auf den Markt (masc). "
         "Vary the agent across 4 pairs: Emma, Taro, Gran, das Kind. Keep auf den Markt every time. "
         "Use gehen (walk/go). "
         "JP cue: 市場へ行く (〜へ行く direction endpoint). ZH cue: 去到市場. "
         "Keep auf den Markt visible in every German line."),
        ("006_auf_gender_a.md",
         "auf + accusative — gender contrast: auf den Tisch / auf die Bank / auf das Bett",
         ("auf den", "auf die", "auf das"),
         "Gender contrast file: show accusative article changing with noun gender using the preposition auf. "
         "Pair 1: Emma stellt etwas auf den Tisch (masc → den). "
         "Pair 2: Taro legt etwas auf die Bank (fem → die). "
         "Pair 3: Gran legt etwas auf das Bett (neut → das). "
         "Pair 4: Das Kind setzt sich auf den Stuhl (masc → den, repeat for reinforcement). "
         "JP cue: use に/の上に for all pairs. ZH cue: 放到〜上 or 坐到〜上. "
         "Make the German accusative article (den/die/das) clearly visible in each German line."),
        ("007_auf_bringen_a.md",
         "auf + accusative — Taro bringt den Teller auf den Tisch (bring + masc endpoint)",
         ("auf den Tisch", "bringt"),
         "Core German sentence: Taro bringt den Teller auf den Tisch. "
         "Movement endpoint: bringing an object ONTO a surface. Accusative: auf den Tisch (masc). "
         "Vary the agent and brought object across 4 pairs, keeping auf den Tisch every time. "
         "Use bringen (bring). "
         "JP cue: テーブルの上に持ってくる. ZH cue: 帶到桌子上. "
         "Keep auf den Tisch visible in every German line."),
        ("008_auf_stellen_b.md",
         "auf + accusative — Gran stellt die Flasche auf die Bank (fem endpoint, stellen)",
         ("auf die Bank", "stellt"),
         "Core German sentence: Gran stellt die Flasche auf die Bank. "
         "Movement endpoint: placing an object upright ONTO a surface. Accusative: auf die Bank (fem). "
         "Vary agent and object across 4 pairs, keeping auf die Bank every time. "
         "Use stellen (place upright). "
         "JP cue: ベンチの上に立てる / 置く. ZH cue: 放到長椅上. "
         "Keep auf die Bank visible in every German line."),
        ("009_auf_legen_c.md",
         "auf + accusative — Emma legt den Apfel auf das Feld (neut endpoint, legen)",
         ("auf das Feld", "legt"),
         "Core German sentence: Emma legt den Apfel auf das Feld. "
         "Movement endpoint: laying an object ONTO a surface. Accusative: auf das Feld (neut). "
         "Vary agent and object across 4 pairs, keeping auf das Feld every time. "
         "Use legen (lay flat). "
         "JP cue: 畑の上に置く. ZH cue: 放到田野上. "
         "Keep auf das Feld visible in every German line."),
        ("010_auf_setzen_b.md",
         "auf + accusative — Das Kind setzt sich auf den Boden (masc endpoint, seating on floor)",
         ("auf den Boden", "setzt"),
         "Core German sentence: Das Kind setzt sich auf den Boden. "
         "Movement endpoint: a person seats themselves ONTO the floor. Accusative: auf den Boden (masc). "
         "Vary agent across 4 pairs: das Kind, Emma, Taro, Gran. Keep auf den Boden every time. "
         "Use setzen (seat). "
         "JP cue: 床に座る (床に + 座る). ZH cue: 坐到地板上. "
         "Keep auf den Boden visible in every German line."),
        ("011_auf_legen_d.md",
         "auf + accusative — agent variety: laying onto surface, masc/fem/neut targets",
         ("auf den", "auf die"),
         "Show different agents placing things ONTO different surfaces. "
         "Pair 1: Emma legt das Buch auf den Tisch (masc). "
         "Pair 2: Taro legt den Apfel auf die Bank (fem). "
         "Pair 3: Gran legt das Heft auf den Boden (masc). "
         "Pair 4: Das Kind legt den Becher auf das Bett (neut). "
         "Use legen throughout. Make accusative article (den/die/das) visible. "
         "JP cue: 〜の上に置く. ZH cue: 放到〜上. "
         "Allow: Heft (notebook, neut)."),
        ("012_auf_bringen_b.md",
         "auf + accusative — Gran bringt die Tasse auf den Tisch (bring, mixed gender focus)",
         ("auf den Tisch", "bringt"),
         "Core German sentence: Gran bringt die Tasse auf den Tisch. "
         "Movement endpoint: bringing object ONTO a surface. Accusative: auf den Tisch (masc). "
         "Vary agent and object across 4 pairs, keeping auf den Tisch every time. "
         "Use bringen (bring). "
         "JP cue: テーブルの上に持ってくる. ZH cue: 帶到桌子上. "
         "Allow: Tasse (cup, fem). Keep auf den Tisch visible in every German line."),
        ("013_auf_stellen_c.md",
         "auf + accusative — stellen, neut endpoint: Emma stellt das Glas auf das Bett",
         ("auf das Bett", "stellt"),
         "Core German sentence: Emma stellt das Glas auf das Bett. "
         "Movement endpoint: placing object upright ONTO a surface. Accusative: auf das Bett (neut). "
         "Vary agent and object across 4 pairs, keeping auf das Bett every time. "
         "Use stellen (place upright). "
         "JP cue: ベッドの上に置く. ZH cue: 放到床上. "
         "Allow: Glas (glass, neut). Keep auf das Bett visible in every German line."),
        # ── in (into) ─────────────────────────────────────────────────────
        ("014_in_gehen_a.md",
         "in + accusative — Emma geht in den Garten (masc movement endpoint)",
         ("in den Garten", "geht"),
         "Core German sentence: Emma geht in den Garten. "
         "Movement endpoint: a person walks INTO a space. Accusative: in den Garten (masc). "
         "Vary agent across 4 pairs: Emma, Taro, Gran, das Kind. Keep in den Garten every time. "
         "Use gehen (walk/go). "
         "JP cue: 庭に入る / 庭へ行く (に/へ + direction). ZH cue: 走進花園. "
         "Keep in den Garten visible in every German line."),
        ("015_in_gehen_b.md",
         "in + accusative — Taro geht in die Küche (fem movement endpoint)",
         ("in die Küche", "geht"),
         "Core German sentence: Taro geht in die Küche. "
         "Movement endpoint: a person walks INTO a space. Accusative: in die Küche (fem). "
         "Vary agent across 4 pairs: Taro, Emma, Gran, das Kind. Keep in die Küche every time. "
         "Use gehen (walk/go). "
         "JP cue: 台所に入る / 台所へ行く. ZH cue: 走進廚房. "
         "Keep in die Küche visible in every German line."),
        ("016_in_gehen_c.md",
         "in + accusative — Gran geht in das Zimmer (neut movement endpoint)",
         ("in das Zimmer", "geht"),
         "Core German sentence: Gran geht in das Zimmer. "
         "Movement endpoint: a person walks INTO a space. Accusative: in das Zimmer (neut). "
         "Vary agent across 4 pairs: Gran, Emma, Taro, das Kind. Keep in das Zimmer every time. "
         "Use gehen (walk/go). "
         "JP cue: 部屋に入る / 部屋へ行く. ZH cue: 走進房間. "
         "Keep in das Zimmer visible in every German line."),
        ("017_in_legen_a.md",
         "in + accusative — Emma legt den Apfel in den Korb (masc container endpoint)",
         ("in den Korb", "legt"),
         "Core German sentence: Emma legt den Apfel in den Korb. "
         "Movement endpoint: placing an object INTO a container. Accusative: in den Korb (masc). "
         "Vary agent and placed object across 4 pairs, keeping in den Korb every time. "
         "Use legen (lay/place). "
         "JP cue: かごの中に入れる (〜の中に + 入れる). ZH cue: 放進籃子裡. "
         "Allow: Korb (basket, masc). Keep in den Korb visible in every German line."),
        ("018_in_stellen_a.md",
         "in + accusative — Taro stellt die Flasche in die Küche (fem space endpoint, stellen)",
         ("in die Küche", "stellt"),
         "Core German sentence: Taro stellt die Flasche in die Küche. "
         "Movement endpoint: placing an object INTO a space. Accusative: in die Küche (fem). "
         "Vary agent and object across 4 pairs, keeping in die Küche every time. "
         "Use stellen (place upright). "
         "JP cue: 台所に置く. ZH cue: 放進廚房. "
         "Keep in die Küche visible in every German line."),
        ("019_in_legen_b.md",
         "in + accusative — Gran legt das Buch in das Zimmer (neut space endpoint, legen)",
         ("in das Zimmer", "legt"),
         "Core German sentence: Gran legt das Buch in das Zimmer. "
         "Movement endpoint: placing an object INTO a space. Accusative: in das Zimmer (neut). "
         "Vary agent and object across 4 pairs, keeping in das Zimmer every time. "
         "Use legen (lay/place). "
         "JP cue: 部屋に置く. ZH cue: 放進房間. "
         "Keep in das Zimmer visible in every German line."),
        ("020_in_gender_a.md",
         "in + accusative — gender contrast: in den Garten / in die Küche / in das Zimmer",
         ("in den", "in die", "in das"),
         "Gender contrast file: show accusative article changing with noun gender using the preposition in. "
         "Pair 1: Emma geht in den Garten (masc → den). "
         "Pair 2: Taro geht in die Küche (fem → die). "
         "Pair 3: Gran geht in das Zimmer (neut → das). "
         "Pair 4: Das Kind läuft in den Park (masc → den, second reinforcement). "
         "JP cue: use に/へ for all pairs. ZH cue: 走進/進入 + location. "
         "Make the German accusative article (den/die/das) clearly visible in each German line."),
        ("021_in_laufen_a.md",
         "in + accusative — Das Kind läuft in den Park (masc movement endpoint, laufen)",
         ("in den Park", "läuft"),
         "Core German sentence: Das Kind läuft in den Park. "
         "Movement endpoint: a person runs INTO a space. Accusative: in den Park (masc). "
         "Vary agent across 4 pairs: das Kind, Emma, Taro, Gran. Keep in den Park every time. "
         "Use laufen (run/walk). "
         "JP cue: 公園に走って入る / 公園へ走る. ZH cue: 跑進公園. "
         "Keep in den Park visible in every German line."),
        ("022_in_bringen_a.md",
         "in + accusative — Emma bringt den Apfel in die Küche (bring + fem endpoint)",
         ("in die Küche", "bringt"),
         "Core German sentence: Emma bringt den Apfel in die Küche. "
         "Movement endpoint: bringing an object INTO a space. Accusative: in die Küche (fem). "
         "Vary agent and brought object across 4 pairs, keeping in die Küche every time. "
         "Use bringen (bring). "
         "JP cue: 台所に持ってくる. ZH cue: 帶進廚房. "
         "Keep in die Küche visible in every German line."),
        ("023_in_legen_c.md",
         "in + accusative — Taro legt das Heft in das Haus (neut space endpoint, legen)",
         ("in das Haus", "legt"),
         "Core German sentence: Taro legt das Heft in das Haus. "
         "Movement endpoint: placing an object INTO a space. Accusative: in das Haus (neut). "
         "Vary agent and object across 4 pairs, keeping in das Haus every time. "
         "Use legen (lay/place). "
         "JP cue: 家の中に置く. ZH cue: 放進房子裡. "
         "Allow: Heft (notebook, neut). Keep in das Haus visible in every German line."),
        ("024_in_gehen_d.md",
         "in + accusative — Emma geht in den Wald (masc movement endpoint, forest)",
         ("in den Wald", "geht"),
         "Core German sentence: Emma geht in den Wald. "
         "Movement endpoint: a person walks INTO a forest. Accusative: in den Wald (masc). "
         "Vary agent across 4 pairs: Emma, Taro, Gran, das Kind. Keep in den Wald every time. "
         "Use gehen (walk/go). "
         "JP cue: 森に入る / 森へ行く. ZH cue: 走進森林. "
         "Keep in den Wald visible in every German line."),
        ("025_in_laufen_b.md",
         "in + accusative — Das Kind läuft in die Schule (fem movement endpoint, laufen)",
         ("in die Schule", "läuft"),
         "Core German sentence: Das Kind läuft in die Schule. "
         "Movement endpoint: a person runs INTO a building. Accusative: in die Schule (fem). "
         "Vary agent across 4 pairs: das Kind, Emma, Taro, Gran. Keep in die Schule every time. "
         "Use laufen (run/walk). "
         "JP cue: 学校に走って入る / 学校へ走る. ZH cue: 跑進學校. "
         "Keep in die Schule visible in every German line."),
        ("026_in_gender_b.md",
         "in + accusative — second gender contrast set with different agents and verbs",
         ("in den", "in die", "in das"),
         "Gender contrast file: show accusative article changing with noun gender using the preposition in. "
         "Pair 1: Taro bringt den Teller in das Haus (neut → das). "
         "Pair 2: Emma stellt die Flasche in die Küche (fem → die). "
         "Pair 3: Gran legt den Apfel in den Korb (masc → den). "
         "Pair 4: Das Kind geht in das Zimmer (neut → das). "
         "Use varied verbs: bringen, stellen, legen, gehen. "
         "JP cue: 〜に/の中に + verb. ZH cue: 進入/放進 + location. "
         "Allow: Korb (basket, masc). Make accusative article (den/die/das) visible."),
        # ── über (over/above) ──────────────────────────────────────────────
        ("027_ueber_haengen_a.md",
         "über + accusative — Taro hängt die Lampe über den Tisch (hang over, masc endpoint)",
         ("über den Tisch", "hängt"),
         "Core German sentence: Taro hängt die Lampe über den Tisch. "
         "Movement endpoint: hanging something OVER a surface. Accusative: über den Tisch (masc). "
         "Vary agent and hung object across 4 pairs, keeping über den Tisch every time. "
         "Use hängen (hang). "
         "JP cue: テーブルの上に掛ける (の上に + 掛ける). ZH cue: 掛到桌子上方. "
         "Allow: Lampe (lamp, fem). Keep über den Tisch visible in every German line."),
        ("028_ueber_haengen_b.md",
         "über + accusative — Emma hängt das Tuch über die Bank (hang over, fem endpoint)",
         ("über die Bank", "hängt"),
         "Core German sentence: Emma hängt das Tuch über die Bank. "
         "Movement endpoint: hanging something OVER a surface. Accusative: über die Bank (fem). "
         "Vary agent and hung object across 4 pairs, keeping über die Bank every time. "
         "Use hängen (hang). "
         "JP cue: ベンチの上に掛ける. ZH cue: 掛到長椅上方. "
         "Allow: Tuch (cloth, neut). Keep über die Bank visible in every German line."),
        ("029_ueber_haengen_c.md",
         "über + accusative — Gran hängt das Bild über das Bett (hang over, neut endpoint)",
         ("über das Bett", "hängt"),
         "Core German sentence: Gran hängt das Bild über das Bett. "
         "Movement endpoint: hanging something OVER a surface. Accusative: über das Bett (neut). "
         "Vary agent and hung object across 4 pairs, keeping über das Bett every time. "
         "Use hängen (hang). "
         "JP cue: ベッドの上に掛ける. ZH cue: 掛到床上方. "
         "Allow: Bild (picture, neut). Keep über das Bett visible in every German line."),
        ("030_ueber_legen_a.md",
         "über + accusative — Emma legt die Decke über den Stuhl (lay over, masc endpoint)",
         ("über den Stuhl", "legt"),
         "Core German sentence: Emma legt die Decke über den Stuhl. "
         "Movement endpoint: laying something OVER an object. Accusative: über den Stuhl (masc). "
         "Vary agent and laid object across 4 pairs, keeping über den Stuhl every time. "
         "Use legen (lay/drape). "
         "JP cue: 椅子の上に掛ける / 被せる. ZH cue: 蓋到椅子上. "
         "Keep über den Stuhl visible in every German line."),
        ("031_ueber_legen_b.md",
         "über + accusative — Taro legt das Tuch über die Bank (lay over, fem endpoint)",
         ("über die Bank", "legt"),
         "Core German sentence: Taro legt das Tuch über die Bank. "
         "Movement endpoint: laying something OVER a surface. Accusative: über die Bank (fem). "
         "Vary agent and laid object across 4 pairs, keeping über die Bank every time. "
         "Use legen (lay/drape). "
         "JP cue: ベンチの上に掛ける / 被せる. ZH cue: 蓋到長椅上. "
         "Allow: Tuch (cloth, neut). Keep über die Bank visible in every German line."),
        ("032_ueber_legen_c.md",
         "über + accusative — Gran legt die Jacke über das Bett (lay over, neut endpoint)",
         ("über das Bett", "legt"),
         "Core German sentence: Gran legt die Jacke über das Bett. "
         "Movement endpoint: laying something OVER a surface. Accusative: über das Bett (neut). "
         "Vary agent and laid object across 4 pairs, keeping über das Bett every time. "
         "Use legen (lay/drape). "
         "JP cue: ベッドの上に掛ける / 被せる. ZH cue: 蓋到床上. "
         "Allow: Jacke (jacket, fem). Keep über das Bett visible in every German line."),
        ("033_ueber_gender_a.md",
         "über + accusative — gender contrast: über den Tisch / über die Bank / über das Bett",
         ("über den", "über die", "über das"),
         "Gender contrast file: show accusative article changing with noun gender using the preposition über. "
         "Pair 1: Taro hängt etwas über den Tisch (masc → den). "
         "Pair 2: Emma hängt etwas über die Bank (fem → die). "
         "Pair 3: Gran legt etwas über das Bett (neut → das). "
         "Pair 4: Das Kind legt etwas über den Stuhl (masc → den, reinforcement). "
         "JP cue: 〜の上に掛ける / 被せる. ZH cue: 掛到/蓋到〜上. "
         "Make the German accusative article (den/die/das) clearly visible in each German line."),
        ("034_ueber_haengen_d.md",
         "über + accusative — hängen, varied agents and hung objects",
         ("über den", "hängt"),
         "Show different agents hanging different objects over surfaces. "
         "Pair 1: Emma hängt das Bild über den Tisch (masc). "
         "Pair 2: Taro hängt die Decke über die Bank (fem). "
         "Pair 3: Gran hängt das Tuch über das Bett (neut). "
         "Pair 4: Emma hängt das Bild über den Stuhl (masc). "
         "Use hängen throughout. Make accusative article (den/die/das) visible. "
         "JP cue: 〜の上に掛ける. ZH cue: 掛到〜上方."),
        ("035_ueber_bringen_a.md",
         "über + accusative — Emma bringt die Decke über den Tisch (bring over, masc endpoint)",
         ("über den Tisch", "bringt"),
         "Core German sentence: Emma bringt die Decke über den Tisch. "
         "Movement endpoint: bringing something OVER a surface. Accusative: über den Tisch (masc). "
         "Vary agent and object across 4 pairs, keeping über den Tisch every time. "
         "Use bringen (bring). "
         "JP cue: テーブルの上方に持ってくる. ZH cue: 帶到桌子上方. "
         "Keep über den Tisch visible in every German line."),
        ("036_ueber_legen_d.md",
         "über + accusative — legen, varied agents: different people draping over surfaces",
         ("über das", "legt"),
         "Show different agents laying objects OVER surfaces. "
         "Pair 1: Emma legt das Tuch über das Bett (neut). "
         "Pair 2: Taro legt die Decke über den Stuhl (masc). "
         "Pair 3: Gran legt das Buch über die Bank (fem). "
         "Pair 4: Das Kind legt das Tuch über das Bett (neut). "
         "Use legen throughout. Make accusative article (den/die/das) visible. "
         "JP cue: 〜の上に掛ける. ZH cue: 蓋到/放到〜上."),
        ("037_ueber_stellen_a.md",
         "über + accusative — Taro stellt die Flasche über den Tisch (place above, masc endpoint)",
         ("über den Tisch", "stellt"),
         "Core German sentence: Taro stellt die Flasche über den Tisch. "
         "Movement endpoint: placing something ABOVE a surface (holding it over). Accusative: über den Tisch (masc). "
         "Vary agent and object across 4 pairs, keeping über den Tisch every time. "
         "Use stellen (place/hold upright). "
         "JP cue: テーブルの上に立てる / 持ち上げる. ZH cue: 放到桌子上方. "
         "Keep über den Tisch visible in every German line."),
        ("038_ueber_bringen_b.md",
         "über + accusative — Gran bringt das Buch über die Bank (bring over, fem endpoint)",
         ("über die Bank", "bringt"),
         "Core German sentence: Gran bringt das Buch über die Bank. "
         "Movement endpoint: bringing something OVER/to a surface. Accusative: über die Bank (fem). "
         "Vary agent and object across 4 pairs, keeping über die Bank every time. "
         "Use bringen (bring). "
         "JP cue: ベンチの上方に持ってくる. ZH cue: 帶到長椅上方. "
         "Keep über die Bank visible in every German line."),
        # ── unter (under/below) ────────────────────────────────────────────
        ("039_unter_legen_a.md",
         "unter + accusative — Emma legt den Apfel unter den Tisch (masc endpoint)",
         ("unter den Tisch", "legt"),
         "Core German sentence: Emma legt den Apfel unter den Tisch. "
         "Movement endpoint: placing an object UNDER a surface. Accusative: unter den Tisch (masc). "
         "Vary agent and placed object across 4 pairs, keeping unter den Tisch every time. "
         "Use legen (lay/place). "
         "JP cue: テーブルの下に置く (の下に + 置く). ZH cue: 放到桌子下面. "
         "Keep unter den Tisch visible in every German line."),
        ("040_unter_legen_b.md",
         "unter + accusative — Taro legt das Buch unter die Bank (fem endpoint)",
         ("unter die Bank", "legt"),
         "Core German sentence: Taro legt das Buch unter die Bank. "
         "Movement endpoint: placing an object UNDER a surface. Accusative: unter die Bank (fem). "
         "Vary agent and placed object across 4 pairs, keeping unter die Bank every time. "
         "Use legen (lay/place). "
         "JP cue: ベンチの下に置く. ZH cue: 放到長椅下面. "
         "Keep unter die Bank visible in every German line."),
        ("041_unter_legen_c.md",
         "unter + accusative — Gran legt den Becher unter das Bett (neut endpoint)",
         ("unter das Bett", "legt"),
         "Core German sentence: Gran legt den Becher unter das Bett. "
         "Movement endpoint: placing an object UNDER a surface. Accusative: unter das Bett (neut). "
         "Vary agent and placed object across 4 pairs, keeping unter das Bett every time. "
         "Use legen (lay/place). "
         "JP cue: ベッドの下に置く. ZH cue: 放到床下面. "
         "Keep unter das Bett visible in every German line."),
        ("042_unter_stellen_a.md",
         "unter + accusative — Emma stellt den Stuhl unter den Tisch (masc endpoint, stellen)",
         ("unter den Tisch", "stellt"),
         "Core German sentence: Emma stellt den Stuhl unter den Tisch. "
         "Movement endpoint: placing an object UNDER a surface. Accusative: unter den Tisch (masc). "
         "Vary agent and placed object across 4 pairs, keeping unter den Tisch every time. "
         "Use stellen (place upright). "
         "JP cue: テーブルの下に置く. ZH cue: 放到桌子下面. "
         "Keep unter den Tisch visible in every German line."),
        ("043_unter_stellen_b.md",
         "unter + accusative — Taro stellt die Flasche unter die Bank (fem endpoint, stellen)",
         ("unter die Bank", "stellt"),
         "Core German sentence: Taro stellt die Flasche unter die Bank. "
         "Movement endpoint: placing an object UNDER a surface. Accusative: unter die Bank (fem). "
         "Vary agent and placed object across 4 pairs, keeping unter die Bank every time. "
         "Use stellen (place upright). "
         "JP cue: ベンチの下に置く. ZH cue: 放到長椅下面. "
         "Keep unter die Bank visible in every German line."),
        ("044_unter_stellen_c.md",
         "unter + accusative — Gran stellt das Glas unter das Bett (neut endpoint, stellen)",
         ("unter das Bett", "stellt"),
         "Core German sentence: Gran stellt das Glas unter das Bett. "
         "Movement endpoint: placing an object UNDER a surface. Accusative: unter das Bett (neut). "
         "Vary agent and placed object across 4 pairs, keeping unter das Bett every time. "
         "Use stellen (place upright). "
         "JP cue: ベッドの下に置く. ZH cue: 放到床下面. "
         "Allow: Glas (glass, neut). Keep unter das Bett visible in every German line."),
        ("045_unter_gender_a.md",
         "unter + accusative — gender contrast: unter den Tisch / unter die Bank / unter das Bett",
         ("unter den", "unter die", "unter das"),
         "Gender contrast file: show accusative article changing with noun gender using the preposition unter. "
         "Pair 1: Emma legt etwas unter den Tisch (masc → den). "
         "Pair 2: Taro legt etwas unter die Bank (fem → die). "
         "Pair 3: Gran legt etwas unter das Bett (neut → das). "
         "Pair 4: Das Kind schiebt etwas unter den Stuhl (masc → den, reinforcement). "
         "JP cue: 〜の下に置く. ZH cue: 放到〜下面. "
         "Allow: schiebt (pushes, from schieben). Make accusative article (den/die/das) clearly visible."),
        ("046_unter_kriechen_a.md",
         "unter + accusative — Das Kind kriecht unter den Tisch (crawl under, masc endpoint)",
         ("unter den Tisch", "kriecht"),
         "Core German sentence: Das Kind kriecht unter den Tisch. "
         "Movement endpoint: a person crawls UNDER a surface. Accusative: unter den Tisch (masc). "
         "Vary agent across 4 pairs: das Kind, Emma, Taro, Gran. Keep unter den Tisch every time. "
         "Use kriechen (crawl). "
         "JP cue: テーブルの下に潜り込む. ZH cue: 爬到桌子下面. "
         "Allow: kriecht/kriechen (crawl). Keep unter den Tisch visible in every German line."),
        ("047_unter_bringen_a.md",
         "unter + accusative — Emma bringt das Buch unter die Bank (bring under, fem endpoint)",
         ("unter die Bank", "bringt"),
         "Core German sentence: Emma bringt das Buch unter die Bank. "
         "Movement endpoint: bringing something UNDER a surface. Accusative: unter die Bank (fem). "
         "Vary agent and brought object across 4 pairs, keeping unter die Bank every time. "
         "Use bringen (bring). "
         "JP cue: ベンチの下に持ってくる. ZH cue: 帶到長椅下面. "
         "Keep unter die Bank visible in every German line."),
        ("048_unter_legen_d.md",
         "unter + accusative — Taro legt das Kissen unter das Bett (neut endpoint, soft object)",
         ("unter das Bett", "legt"),
         "Core German sentence: Taro legt das Kissen unter das Bett. "
         "Movement endpoint: placing a soft object UNDER a surface. Accusative: unter das Bett (neut). "
         "Vary agent and object across 4 pairs, keeping unter das Bett every time. "
         "Use legen (lay/place). "
         "JP cue: ベッドの下に置く. ZH cue: 放到床下面. "
         "Allow: Kissen (pillow, neut). Keep unter das Bett visible in every German line."),
        ("049_unter_stellen_d.md",
         "unter + accusative — stellen, varied agents: different people placing under surfaces",
         ("unter den", "stellt"),
         "Show different agents placing objects UNDER surfaces. "
         "Pair 1: Emma stellt die Flasche unter den Tisch (masc). "
         "Pair 2: Taro stellt den Becher unter die Bank (fem). "
         "Pair 3: Gran stellt das Glas unter das Bett (neut). "
         "Pair 4: Das Kind stellt den Stuhl unter den Tisch (masc). "
         "Use stellen throughout. Make accusative article (den/die/das) visible. "
         "JP cue: 〜の下に置く. ZH cue: 放到〜下面."),
        ("050_unter_legen_e.md",
         "unter + accusative — legen, agent variety: mixed gender targets",
         ("unter die", "unter das"),
         "Show different agents laying objects UNDER surfaces with mixed gender. "
         "Pair 1: Emma legt die Decke unter das Bett (neut). "
         "Pair 2: Taro legt den Apfel unter die Bank (fem). "
         "Pair 3: Gran legt das Buch unter den Tisch (masc). "
         "Pair 4: Das Kind legt den Becher unter die Bank (fem). "
         "Use legen throughout. Make accusative article (den/die/das) visible. "
         "JP cue: 〜の下に置く. ZH cue: 放到〜下面."),
        # ── neben (beside) ────────────────────────────────────────────────
        ("051_neben_stellen_a.md",
         "neben + accusative — Emma stellt den Becher neben den Stuhl (masc endpoint)",
         ("neben den Stuhl", "stellt"),
         "Core German sentence: Emma stellt den Becher neben den Stuhl. "
         "Movement endpoint: placing an object BESIDE another object. Accusative: neben den Stuhl (masc). "
         "Vary agent and placed object across 4 pairs, keeping neben den Stuhl every time. "
         "Use stellen (place upright). "
         "JP cue: 椅子の隣に置く (の隣に + 置く). ZH cue: 放到椅子旁邊. "
         "Keep neben den Stuhl visible in every German line."),
        ("052_neben_stellen_b.md",
         "neben + accusative — Taro stellt die Flasche neben die Bank (fem endpoint)",
         ("neben die Bank", "stellt"),
         "Core German sentence: Taro stellt die Flasche neben die Bank. "
         "Movement endpoint: placing an object BESIDE a surface. Accusative: neben die Bank (fem). "
         "Vary agent and placed object across 4 pairs, keeping neben die Bank every time. "
         "Use stellen (place upright). "
         "JP cue: ベンチの隣に置く. ZH cue: 放到長椅旁邊. "
         "Keep neben die Bank visible in every German line."),
        ("053_neben_stellen_c.md",
         "neben + accusative — Gran stellt das Glas neben das Bett (neut endpoint)",
         ("neben das Bett", "stellt"),
         "Core German sentence: Gran stellt das Glas neben das Bett. "
         "Movement endpoint: placing an object BESIDE a surface. Accusative: neben das Bett (neut). "
         "Vary agent and placed object across 4 pairs, keeping neben das Bett every time. "
         "Use stellen (place upright). "
         "JP cue: ベッドの隣に置く. ZH cue: 放到床旁邊. "
         "Allow: Glas (glass, neut). Keep neben das Bett visible in every German line."),
        ("054_neben_legen_a.md",
         "neben + accusative — Emma legt den Apfel neben den Tisch (masc endpoint, legen)",
         ("neben den Tisch", "legt"),
         "Core German sentence: Emma legt den Apfel neben den Tisch. "
         "Movement endpoint: placing an object BESIDE a surface. Accusative: neben den Tisch (masc). "
         "Vary agent and placed object across 4 pairs, keeping neben den Tisch every time. "
         "Use legen (lay/place). "
         "JP cue: テーブルの隣に置く. ZH cue: 放到桌子旁邊. "
         "Keep neben den Tisch visible in every German line."),
        ("055_neben_legen_b.md",
         "neben + accusative — Taro legt das Buch neben die Bank (fem endpoint, legen)",
         ("neben die Bank", "legt"),
         "Core German sentence: Taro legt das Buch neben die Bank. "
         "Movement endpoint: placing an object BESIDE a surface. Accusative: neben die Bank (fem). "
         "Vary agent and placed object across 4 pairs, keeping neben die Bank every time. "
         "Use legen (lay/place). "
         "JP cue: ベンチの隣に置く. ZH cue: 放到長椅旁邊. "
         "Keep neben die Bank visible in every German line."),
        ("056_neben_legen_c.md",
         "neben + accusative — Gran legt die Decke neben das Bett (neut endpoint, legen)",
         ("neben das Bett", "legt"),
         "Core German sentence: Gran legt die Decke neben das Bett. "
         "Movement endpoint: placing an object BESIDE a surface. Accusative: neben das Bett (neut). "
         "Vary agent and placed object across 4 pairs, keeping neben das Bett every time. "
         "Use legen (lay/place). "
         "JP cue: ベッドの隣に置く. ZH cue: 放到床旁邊. "
         "Keep neben das Bett visible in every German line."),
        ("057_neben_gender_a.md",
         "neben + accusative — gender contrast: neben den Stuhl / neben die Bank / neben das Bett",
         ("neben den", "neben die", "neben das"),
         "Gender contrast file: show accusative article changing with noun gender using the preposition neben. "
         "Pair 1: Emma stellt etwas neben den Stuhl (masc → den). "
         "Pair 2: Taro stellt etwas neben die Bank (fem → die). "
         "Pair 3: Gran stellt etwas neben das Bett (neut → das). "
         "Pair 4: Das Kind stellt etwas neben den Tisch (masc → den, reinforcement). "
         "JP cue: 〜の隣に置く. ZH cue: 放到〜旁邊. "
         "Make the German accusative article (den/die/das) clearly visible in each German line."),
        ("058_neben_gehen_a.md",
         "neben + accusative — Emma geht neben den Park (movement beside, masc endpoint)",
         ("neben den Park", "geht"),
         "Core German sentence: Emma geht neben den Park. "
         "Movement endpoint: a person moves to a position BESIDE something. Accusative: neben den Park (masc). "
         "Vary agent across 4 pairs: Emma, Taro, Gran, das Kind. Keep neben den Park every time. "
         "Use gehen (walk/go). "
         "JP cue: 公園の隣に行く (の隣に + 行く). ZH cue: 走到公園旁邊. "
         "Keep neben den Park visible in every German line."),
        ("059_neben_bringen_a.md",
         "neben + accusative — Taro bringt den Teller neben den Tisch (bring beside, masc endpoint)",
         ("neben den Tisch", "bringt"),
         "Core German sentence: Taro bringt den Teller neben den Tisch. "
         "Movement endpoint: bringing an object to a position BESIDE something. Accusative: neben den Tisch (masc). "
         "Vary agent and brought object across 4 pairs, keeping neben den Tisch every time. "
         "Use bringen (bring). "
         "JP cue: テーブルの隣に持ってくる. ZH cue: 帶到桌子旁邊. "
         "Keep neben den Tisch visible in every German line."),
        ("060_neben_stellen_d.md",
         "neben + accusative — stellen, varied agents and objects, mixed gender",
         ("neben den", "stellt"),
         "Show different agents placing objects BESIDE targets with mixed gender. "
         "Pair 1: Emma stellt den Becher neben den Stuhl (masc). "
         "Pair 2: Taro stellt das Glas neben die Bank (fem). "
         "Pair 3: Gran stellt die Flasche neben das Bett (neut). "
         "Pair 4: Das Kind stellt den Becher neben den Tisch (masc). "
         "Use stellen throughout. Make accusative article (den/die/das) visible. "
         "JP cue: 〜の隣に置く. ZH cue: 放到〜旁邊."),
        ("061_neben_legen_d.md",
         "neben + accusative — legen, varied targets: agent variety beside surfaces",
         ("neben die", "neben das"),
         "Show different agents laying objects BESIDE surfaces. "
         "Pair 1: Emma legt das Buch neben die Bank (fem). "
         "Pair 2: Taro legt die Decke neben das Bett (neut). "
         "Pair 3: Gran legt den Apfel neben den Tisch (masc). "
         "Pair 4: Das Kind legt das Heft neben die Bank (fem). "
         "Use legen throughout. Make accusative article (den/die/das) visible. "
         "JP cue: 〜の隣に置く. ZH cue: 放到〜旁邊. "
         "Allow: Heft (notebook, neut)."),
        ("062_neben_bringen_b.md",
         "neben + accusative — Gran bringt das Buch neben das Bett (bring beside, neut endpoint)",
         ("neben das Bett", "bringt"),
         "Core German sentence: Gran bringt das Buch neben das Bett. "
         "Movement endpoint: bringing something to a position BESIDE something. Accusative: neben das Bett (neut). "
         "Vary agent and brought object across 4 pairs, keeping neben das Bett every time. "
         "Use bringen (bring). "
         "JP cue: ベッドの隣に持ってくる. ZH cue: 帶到床旁邊. "
         "Keep neben das Bett visible in every German line."),
        # ── vor (in front of) ─────────────────────────────────────────────
        ("063_vor_stellen_a.md",
         "vor + accusative — Emma stellt den Stuhl vor den Tisch (masc endpoint)",
         ("vor den Tisch", "stellt"),
         "Core German sentence: Emma stellt den Stuhl vor den Tisch. "
         "Movement endpoint: placing an object IN FRONT OF another object. Accusative: vor den Tisch (masc). "
         "Vary agent and placed object across 4 pairs, keeping vor den Tisch every time. "
         "Use stellen (place upright). "
         "JP cue: テーブルの前に置く (の前に + 置く). ZH cue: 放到桌子前面. "
         "Keep vor den Tisch visible in every German line."),
        ("064_vor_stellen_b.md",
         "vor + accusative — Taro stellt die Flasche vor die Bank (fem endpoint)",
         ("vor die Bank", "stellt"),
         "Core German sentence: Taro stellt die Flasche vor die Bank. "
         "Movement endpoint: placing an object IN FRONT OF a surface. Accusative: vor die Bank (fem). "
         "Vary agent and placed object across 4 pairs, keeping vor die Bank every time. "
         "Use stellen (place upright). "
         "JP cue: ベンチの前に置く. ZH cue: 放到長椅前面. "
         "Keep vor die Bank visible in every German line."),
        ("065_vor_stellen_c.md",
         "vor + accusative — Gran stellt das Glas vor das Bett (neut endpoint)",
         ("vor das Bett", "stellt"),
         "Core German sentence: Gran stellt das Glas vor das Bett. "
         "Movement endpoint: placing an object IN FRONT OF a surface. Accusative: vor das Bett (neut). "
         "Vary agent and placed object across 4 pairs, keeping vor das Bett every time. "
         "Use stellen (place upright). "
         "JP cue: ベッドの前に置く. ZH cue: 放到床前面. "
         "Allow: Glas (glass, neut). Keep vor das Bett visible in every German line."),
        ("066_vor_legen_a.md",
         "vor + accusative — Emma legt den Apfel vor den Stuhl (masc endpoint, legen)",
         ("vor den Stuhl", "legt"),
         "Core German sentence: Emma legt den Apfel vor den Stuhl. "
         "Movement endpoint: placing an object IN FRONT OF a surface. Accusative: vor den Stuhl (masc). "
         "Vary agent and placed object across 4 pairs, keeping vor den Stuhl every time. "
         "Use legen (lay/place). "
         "JP cue: 椅子の前に置く. ZH cue: 放到椅子前面. "
         "Keep vor den Stuhl visible in every German line."),
        ("067_vor_legen_b.md",
         "vor + accusative — Taro legt das Buch vor die Bank (fem endpoint, legen)",
         ("vor die Bank", "legt"),
         "Core German sentence: Taro legt das Buch vor die Bank. "
         "Movement endpoint: placing an object IN FRONT OF a surface. Accusative: vor die Bank (fem). "
         "Vary agent and placed object across 4 pairs, keeping vor die Bank every time. "
         "Use legen (lay/place). "
         "JP cue: ベンチの前に置く. ZH cue: 放到長椅前面. "
         "Keep vor die Bank visible in every German line."),
        ("068_vor_legen_c.md",
         "vor + accusative — Gran legt die Decke vor das Bett (neut endpoint, legen)",
         ("vor das Bett", "legt"),
         "Core German sentence: Gran legt die Decke vor das Bett. "
         "Movement endpoint: placing an object IN FRONT OF a surface. Accusative: vor das Bett (neut). "
         "Vary agent and placed object across 4 pairs, keeping vor das Bett every time. "
         "Use legen (lay/place). "
         "JP cue: ベッドの前に置く. ZH cue: 放到床前面. "
         "Keep vor das Bett visible in every German line."),
        ("069_vor_gender_a.md",
         "vor + accusative — gender contrast: vor den Tisch / vor die Bank / vor das Haus",
         ("vor den", "vor die", "vor das"),
         "Gender contrast file: show accusative article changing with noun gender using the preposition vor. "
         "Pair 1: Emma stellt etwas vor den Tisch (masc → den). "
         "Pair 2: Taro stellt etwas vor die Bank (fem → die). "
         "Pair 3: Gran stellt etwas vor das Haus (neut → das). "
         "Pair 4: Das Kind stellt etwas vor den Stuhl (masc → den, reinforcement). "
         "JP cue: 〜の前に置く. ZH cue: 放到〜前面. "
         "Make the German accusative article (den/die/das) clearly visible in each German line."),
        ("070_vor_gehen_a.md",
         "vor + accusative — Das Kind geht vor den Tisch (movement to in-front-of, masc endpoint)",
         ("vor den Tisch", "geht"),
         "Core German sentence: Das Kind geht vor den Tisch. "
         "Movement endpoint: a person moves to a position IN FRONT OF something. Accusative: vor den Tisch (masc). "
         "Vary agent across 4 pairs: das Kind, Emma, Taro, Gran. Keep vor den Tisch every time. "
         "Use gehen (walk/go). "
         "JP cue: テーブルの前に行く (の前に + 行く). ZH cue: 走到桌子前面. "
         "Keep vor den Tisch visible in every German line."),
        ("071_vor_bringen_a.md",
         "vor + accusative — Emma bringt den Becher vor den Stuhl (bring in front of, masc endpoint)",
         ("vor den Stuhl", "bringt"),
         "Core German sentence: Emma bringt den Becher vor den Stuhl. "
         "Movement endpoint: bringing something to a position IN FRONT OF something. Accusative: vor den Stuhl (masc). "
         "Vary agent and brought object across 4 pairs, keeping vor den Stuhl every time. "
         "Use bringen (bring). "
         "JP cue: 椅子の前に持ってくる. ZH cue: 帶到椅子前面. "
         "Keep vor den Stuhl visible in every German line."),
        ("072_vor_stellen_d.md",
         "vor + accusative — stellen, varied agents and objects, mixed gender",
         ("vor den", "stellt"),
         "Show different agents placing objects IN FRONT OF targets with mixed gender. "
         "Pair 1: Emma stellt den Becher vor den Stuhl (masc). "
         "Pair 2: Taro stellt die Flasche vor die Bank (fem). "
         "Pair 3: Gran stellt das Glas vor das Bett (neut). "
         "Pair 4: Das Kind stellt den Becher vor den Tisch (masc). "
         "Use stellen throughout. Make accusative article (den/die/das) visible. "
         "JP cue: 〜の前に置く. ZH cue: 放到〜前面."),
        ("073_vor_legen_d.md",
         "vor + accusative — legen, varied agents: different people placing in front of surfaces",
         ("vor die", "vor das"),
         "Show different agents laying objects IN FRONT OF surfaces. "
         "Pair 1: Emma legt das Buch vor die Bank (fem). "
         "Pair 2: Taro legt die Decke vor das Bett (neut). "
         "Pair 3: Gran legt den Apfel vor den Tisch (masc). "
         "Pair 4: Das Kind legt das Heft vor die Bank (fem). "
         "Use legen throughout. Make accusative article (den/die/das) visible. "
         "JP cue: 〜の前に置く. ZH cue: 放到〜前面. "
         "Allow: Heft (notebook, neut)."),
        ("074_vor_gehen_b.md",
         "vor + accusative — Taro geht vor das Haus (movement to in-front-of, neut endpoint)",
         ("vor das Haus", "geht"),
         "Core German sentence: Taro geht vor das Haus. "
         "Movement endpoint: a person moves to a position IN FRONT OF a building. Accusative: vor das Haus (neut). "
         "Vary agent across 4 pairs: Taro, Emma, Gran, das Kind. Keep vor das Haus every time. "
         "Use gehen (walk/go). "
         "JP cue: 家の前に行く. ZH cue: 走到房子前面. "
         "Keep vor das Haus visible in every German line."),
        ("075_vor_bringen_b.md",
         "vor + accusative — Gran bringt das Buch vor die Bank (bring in front of, fem endpoint)",
         ("vor die Bank", "bringt"),
         "Core German sentence: Gran bringt das Buch vor die Bank. "
         "Movement endpoint: bringing something to a position IN FRONT OF a surface. Accusative: vor die Bank (fem). "
         "Vary agent and brought object across 4 pairs, keeping vor die Bank every time. "
         "Use bringen (bring). "
         "JP cue: ベンチの前に持ってくる. ZH cue: 帶到長椅前面. "
         "Keep vor die Bank visible in every German line."),
        # ── hinter (behind) ───────────────────────────────────────────────
        ("076_hinter_stellen_a.md",
         "hinter + accusative — Emma stellt den Becher hinter den Stuhl (masc endpoint)",
         ("hinter den Stuhl", "stellt"),
         "Core German sentence: Emma stellt den Becher hinter den Stuhl. "
         "Movement endpoint: placing an object BEHIND another object. Accusative: hinter den Stuhl (masc). "
         "Vary agent and placed object across 4 pairs, keeping hinter den Stuhl every time. "
         "Use stellen (place upright). "
         "JP cue: 椅子の後ろに置く (の後ろに + 置く). ZH cue: 放到椅子後面. "
         "Keep hinter den Stuhl visible in every German line."),
        ("077_hinter_stellen_b.md",
         "hinter + accusative — Taro stellt die Flasche hinter die Bank (fem endpoint)",
         ("hinter die Bank", "stellt"),
         "Core German sentence: Taro stellt die Flasche hinter die Bank. "
         "Movement endpoint: placing an object BEHIND a surface. Accusative: hinter die Bank (fem). "
         "Vary agent and placed object across 4 pairs, keeping hinter die Bank every time. "
         "Use stellen (place upright). "
         "JP cue: ベンチの後ろに置く. ZH cue: 放到長椅後面. "
         "Keep hinter die Bank visible in every German line."),
        ("078_hinter_stellen_c.md",
         "hinter + accusative — Gran stellt das Glas hinter das Bett (neut endpoint)",
         ("hinter das Bett", "stellt"),
         "Core German sentence: Gran stellt das Glas hinter das Bett. "
         "Movement endpoint: placing an object BEHIND a surface. Accusative: hinter das Bett (neut). "
         "Vary agent and placed object across 4 pairs, keeping hinter das Bett every time. "
         "Use stellen (place upright). "
         "JP cue: ベッドの後ろに置く. ZH cue: 放到床後面. "
         "Allow: Glas (glass, neut). Keep hinter das Bett visible in every German line."),
        ("079_hinter_legen_a.md",
         "hinter + accusative — Emma legt den Apfel hinter den Tisch (masc endpoint, legen)",
         ("hinter den Tisch", "legt"),
         "Core German sentence: Emma legt den Apfel hinter den Tisch. "
         "Movement endpoint: placing an object BEHIND a surface. Accusative: hinter den Tisch (masc). "
         "Vary agent and placed object across 4 pairs, keeping hinter den Tisch every time. "
         "Use legen (lay/place). "
         "JP cue: テーブルの後ろに置く. ZH cue: 放到桌子後面. "
         "Keep hinter den Tisch visible in every German line."),
        ("080_hinter_legen_b.md",
         "hinter + accusative — Taro legt das Buch hinter die Bank (fem endpoint, legen)",
         ("hinter die Bank", "legt"),
         "Core German sentence: Taro legt das Buch hinter die Bank. "
         "Movement endpoint: placing an object BEHIND a surface. Accusative: hinter die Bank (fem). "
         "Vary agent and placed object across 4 pairs, keeping hinter die Bank every time. "
         "Use legen (lay/place). "
         "JP cue: ベンチの後ろに置く. ZH cue: 放到長椅後面. "
         "Keep hinter die Bank visible in every German line."),
        ("081_hinter_legen_c.md",
         "hinter + accusative — Gran legt die Decke hinter das Bett (neut endpoint, legen)",
         ("hinter das Bett", "legt"),
         "Core German sentence: Gran legt die Decke hinter das Bett. "
         "Movement endpoint: placing an object BEHIND a surface. Accusative: hinter das Bett (neut). "
         "Vary agent and placed object across 4 pairs, keeping hinter das Bett every time. "
         "Use legen (lay/place). "
         "JP cue: ベッドの後ろに置く. ZH cue: 放到床後面. "
         "Keep hinter das Bett visible in every German line."),
        ("082_hinter_gender_a.md",
         "hinter + accusative — gender contrast: hinter den Stuhl / hinter die Bank / hinter das Haus",
         ("hinter den", "hinter die", "hinter das"),
         "Gender contrast file: show accusative article changing with noun gender using the preposition hinter. "
         "Pair 1: Emma stellt etwas hinter den Stuhl (masc → den). "
         "Pair 2: Taro stellt etwas hinter die Bank (fem → die). "
         "Pair 3: Gran geht hinter das Haus (neut → das). "
         "Pair 4: Das Kind legt etwas hinter den Tisch (masc → den, reinforcement). "
         "JP cue: 〜の後ろに置く/行く. ZH cue: 放到/走到〜後面. "
         "Make the German accusative article (den/die/das) clearly visible in each German line."),
        ("083_hinter_gehen_a.md",
         "hinter + accusative — Das Kind geht hinter das Haus (neut movement endpoint)",
         ("hinter das Haus", "geht"),
         "Core German sentence: Das Kind geht hinter das Haus. "
         "Movement endpoint: a person moves BEHIND a building. Accusative: hinter das Haus (neut). "
         "Vary agent across 4 pairs: das Kind, Emma, Taro, Gran. Keep hinter das Haus every time. "
         "Use gehen (walk/go). "
         "JP cue: 家の後ろに行く (の後ろに + 行く). ZH cue: 走到房子後面. "
         "Keep hinter das Haus visible in every German line."),
        ("084_hinter_bringen_a.md",
         "hinter + accusative — Emma bringt den Teller hinter den Tisch (bring behind, masc endpoint)",
         ("hinter den Tisch", "bringt"),
         "Core German sentence: Emma bringt den Teller hinter den Tisch. "
         "Movement endpoint: bringing something BEHIND a surface. Accusative: hinter den Tisch (masc). "
         "Vary agent and brought object across 4 pairs, keeping hinter den Tisch every time. "
         "Use bringen (bring). "
         "JP cue: テーブルの後ろに持ってくる. ZH cue: 帶到桌子後面. "
         "Keep hinter den Tisch visible in every German line."),
        ("085_hinter_stellen_d.md",
         "hinter + accusative — stellen, varied agents and objects, mixed gender",
         ("hinter den", "stellt"),
         "Show different agents placing objects BEHIND targets with mixed gender. "
         "Pair 1: Emma stellt den Becher hinter den Stuhl (masc). "
         "Pair 2: Taro stellt die Flasche hinter die Bank (fem). "
         "Pair 3: Gran stellt das Glas hinter das Bett (neut). "
         "Pair 4: Das Kind stellt den Becher hinter den Tisch (masc). "
         "Use stellen throughout. Make accusative article (den/die/das) visible. "
         "JP cue: 〜の後ろに置く. ZH cue: 放到〜後面."),
        ("086_hinter_legen_d.md",
         "hinter + accusative — legen, varied agents: different people placing behind surfaces",
         ("hinter die", "hinter das"),
         "Show different agents laying objects BEHIND surfaces. "
         "Pair 1: Emma legt das Buch hinter die Bank (fem). "
         "Pair 2: Taro legt die Decke hinter das Bett (neut). "
         "Pair 3: Gran legt den Apfel hinter den Tisch (masc). "
         "Pair 4: Das Kind legt das Heft hinter die Bank (fem). "
         "Use legen throughout. Make accusative article (den/die/das) visible. "
         "JP cue: 〜の後ろに置く. ZH cue: 放到〜後面. "
         "Allow: Heft (notebook, neut)."),
        ("087_hinter_gehen_b.md",
         "hinter + accusative — Taro geht hinter den Garten (movement behind, masc endpoint)",
         ("hinter den Garten", "geht"),
         "Core German sentence: Taro geht hinter den Garten. "
         "Movement endpoint: a person moves to a position BEHIND a space. Accusative: hinter den Garten (masc). "
         "Vary agent across 4 pairs: Taro, Emma, Gran, das Kind. Keep hinter den Garten every time. "
         "Use gehen (walk/go). "
         "JP cue: 庭の後ろに行く. ZH cue: 走到花園後面. "
         "Keep hinter den Garten visible in every German line."),
        ("088_hinter_bringen_b.md",
         "hinter + accusative — Gran bringt das Buch hinter die Bank (bring behind, fem endpoint)",
         ("hinter die Bank", "bringt"),
         "Core German sentence: Gran bringt das Buch hinter die Bank. "
         "Movement endpoint: bringing something BEHIND a surface. Accusative: hinter die Bank (fem). "
         "Vary agent and brought object across 4 pairs, keeping hinter die Bank every time. "
         "Use bringen (bring). "
         "JP cue: ベンチの後ろに持ってくる. ZH cue: 帶到長椅後面. "
         "Keep hinter die Bank visible in every German line."),
        # ── zwischen (between) ────────────────────────────────────────────
        ("089_zwischen_stellen_a.md",
         "zwischen + accusative — Emma stellt den Becher zwischen den Stuhl und den Tisch (masc pair)",
         ("zwischen den Stuhl", "stellt"),
         "Core German sentence: Emma stellt den Becher zwischen den Stuhl und den Tisch. "
         "Movement endpoint: placing an object BETWEEN two masc targets. Accusative: zwischen den Stuhl und den Tisch. "
         "Vary agent and placed object across 4 pairs, keeping zwischen den Stuhl und den Tisch every time. "
         "Use stellen (place upright). "
         "JP cue: 椅子とテーブルの間に置く (の間に + 置く). ZH cue: 放到椅子和桌子之間. "
         "Keep zwischen den Stuhl und den Tisch visible in every German line."),
        ("090_zwischen_stellen_b.md",
         "zwischen + accusative — Taro stellt die Flasche zwischen die Bank und den Stuhl (mixed gender)",
         ("zwischen die Bank", "stellt"),
         "Core German sentence: Taro stellt die Flasche zwischen die Bank und den Stuhl. "
         "Movement endpoint: placing an object BETWEEN two targets. Accusative: zwischen die Bank (fem) und den Stuhl (masc). "
         "Vary agent and placed object across 4 pairs, keeping zwischen die Bank und den Stuhl every time. "
         "Use stellen (place upright). "
         "JP cue: ベンチと椅子の間に置く. ZH cue: 放到長椅和椅子之間. "
         "Keep zwischen die Bank visible in every German line."),
        ("091_zwischen_legen_a.md",
         "zwischen + accusative — Gran legt das Buch zwischen den Tisch und das Bett (masc + neut pair)",
         ("zwischen den Tisch", "legt"),
         "Core German sentence: Gran legt das Buch zwischen den Tisch und das Bett. "
         "Movement endpoint: placing an object BETWEEN two targets. Accusative: zwischen den Tisch (masc) und das Bett (neut). "
         "Vary agent and placed object across 4 pairs, keeping zwischen den Tisch und das Bett every time. "
         "Use legen (lay/place). "
         "JP cue: テーブルとベッドの間に置く. ZH cue: 放到桌子和床之間. "
         "Keep zwischen den Tisch und das Bett visible in every German line."),
        ("092_zwischen_legen_b.md",
         "zwischen + accusative — Emma legt den Apfel zwischen die Bank und den Stuhl (fem + masc pair)",
         ("zwischen die Bank", "legt"),
         "Core German sentence: Emma legt den Apfel zwischen die Bank und den Stuhl. "
         "Movement endpoint: placing an object BETWEEN two targets. Accusative: zwischen die Bank (fem) und den Stuhl (masc). "
         "Vary agent and placed object across 4 pairs, keeping zwischen die Bank und den Stuhl every time. "
         "Use legen (lay/place). "
         "JP cue: ベンチと椅子の間に置く. ZH cue: 放到長椅和椅子之間. "
         "Keep zwischen die Bank und den Stuhl visible in every German line."),
        ("093_zwischen_stellen_c.md",
         "zwischen + accusative — Taro stellt das Glas zwischen das Bett und den Tisch (neut + masc pair)",
         ("zwischen das Bett", "stellt"),
         "Core German sentence: Taro stellt das Glas zwischen das Bett und den Tisch. "
         "Movement endpoint: placing an object BETWEEN two targets. Accusative: zwischen das Bett (neut) und den Tisch (masc). "
         "Vary agent and placed object across 4 pairs, keeping zwischen das Bett und den Tisch every time. "
         "Use stellen (place upright). "
         "JP cue: ベッドとテーブルの間に置く. ZH cue: 放到床和桌子之間. "
         "Allow: Glas (glass, neut). Keep zwischen das Bett und den Tisch visible in every German line."),
        ("094_zwischen_gender_a.md",
         "zwischen + accusative — gender contrast: zwischen den / zwischen die / zwischen das",
         ("zwischen den", "zwischen die", "zwischen das"),
         "Gender contrast file: show accusative article changing with noun gender using the preposition zwischen. "
         "Pair 1: Emma stellt etwas zwischen den Stuhl und den Tisch (masc → den). "
         "Pair 2: Taro stellt etwas zwischen die Bank und den Stuhl (fem → die). "
         "Pair 3: Gran legt etwas zwischen das Bett und den Tisch (neut → das). "
         "Pair 4: Das Kind stellt etwas zwischen den Tisch und die Bank (masc → den + fem → die). "
         "JP cue: 〜の間に置く. ZH cue: 放到〜之間. "
         "Make the German accusative article (den/die/das) clearly visible in each German line."),
        ("095_zwischen_gehen_a.md",
         "zwischen + accusative — Das Kind geht zwischen den Stuhl und den Tisch (movement between, masc pair)",
         ("zwischen den Stuhl", "geht"),
         "Core German sentence: Das Kind geht zwischen den Stuhl und den Tisch. "
         "Movement endpoint: a person moves BETWEEN two objects. Accusative: zwischen den Stuhl und den Tisch (masc pair). "
         "Vary agent across 4 pairs: das Kind, Emma, Taro, Gran. Keep zwischen den Stuhl und den Tisch every time. "
         "Use gehen (walk/go). "
         "JP cue: 椅子とテーブルの間に行く (の間に + 行く). ZH cue: 走到椅子和桌子之間. "
         "Keep zwischen den Stuhl und den Tisch visible in every German line."),
        ("096_zwischen_bringen_a.md",
         "zwischen + accusative — Emma bringt den Becher zwischen den Tisch und die Bank (bring between)",
         ("zwischen den Tisch", "bringt"),
         "Core German sentence: Emma bringt den Becher zwischen den Tisch und die Bank. "
         "Movement endpoint: bringing something BETWEEN two targets. Accusative: zwischen den Tisch (masc) und die Bank (fem). "
         "Vary agent and brought object across 4 pairs, keeping zwischen den Tisch und die Bank every time. "
         "Use bringen (bring). "
         "JP cue: テーブルと長椅子の間に持ってくる. ZH cue: 帶到桌子和長椅之間. "
         "Keep zwischen den Tisch und die Bank visible in every German line."),
        ("097_zwischen_legen_c.md",
         "zwischen + accusative — Gran legt die Decke zwischen das Bett und den Stuhl (neut + masc pair)",
         ("zwischen das Bett", "legt"),
         "Core German sentence: Gran legt die Decke zwischen das Bett und den Stuhl. "
         "Movement endpoint: placing an object BETWEEN two targets. Accusative: zwischen das Bett (neut) und den Stuhl (masc). "
         "Vary agent and placed object across 4 pairs, keeping zwischen das Bett und den Stuhl every time. "
         "Use legen (lay/place). "
         "JP cue: ベッドと椅子の間に置く. ZH cue: 放到床和椅子之間. "
         "Keep zwischen das Bett und den Stuhl visible in every German line."),
        ("098_zwischen_stellen_d.md",
         "zwischen + accusative — stellen, varied objects and pairs: mixed gender combinations",
         ("zwischen den", "zwischen die"),
         "Show different agents placing objects BETWEEN target pairs with mixed gender. "
         "Pair 1: Emma stellt den Becher zwischen den Stuhl und die Bank (masc + fem). "
         "Pair 2: Taro stellt das Glas zwischen das Bett und den Tisch (neut + masc). "
         "Pair 3: Gran stellt die Flasche zwischen den Tisch und die Bank (masc + fem). "
         "Pair 4: Das Kind stellt den Becher zwischen das Bett und den Stuhl (neut + masc). "
         "Use stellen throughout. Make accusative article (den/die/das) visible. "
         "JP cue: 〜の間に置く. ZH cue: 放到〜之間."),
        ("099_zwischen_gehen_b.md",
         "zwischen + accusative — Taro geht zwischen die Bank und den Stuhl (movement between, fem + masc)",
         ("zwischen die Bank", "geht"),
         "Core German sentence: Taro geht zwischen die Bank und den Stuhl. "
         "Movement endpoint: a person moves BETWEEN two objects. Accusative: zwischen die Bank (fem) und den Stuhl (masc). "
         "Vary agent across 4 pairs: Taro, Emma, Gran, das Kind. Keep zwischen die Bank und den Stuhl every time. "
         "Use gehen (walk/go). "
         "JP cue: ベンチと椅子の間に行く. ZH cue: 走到長椅和椅子之間. "
         "Keep zwischen die Bank und den Stuhl visible in every German line."),
        ("100_zwischen_gender_b.md",
         "zwischen + accusative — second gender contrast set: varied agents and article combinations",
         ("zwischen den", "zwischen das"),
         "Gender contrast file: reinforce accusative article with zwischen using different agents. "
         "Pair 1: Emma bringt etwas zwischen den Tisch und das Bett (masc → den + neut → das). "
         "Pair 2: Taro stellt etwas zwischen das Bett und die Bank (neut → das + fem → die). "
         "Pair 3: Gran legt etwas zwischen den Stuhl und die Bank (masc → den + fem → die). "
         "Pair 4: Das Kind geht zwischen den Tisch und das Bett (masc → den + neut → das). "
         "JP cue: 〜の間に + verb. ZH cue: 帶到/放到/走到〜之間. "
         "Make the German accusative article (den/die/das) clearly visible in each German line."),
    ]

    shared_suffix = (
        " Two-way preposition + accusative = movement endpoint. "
        "The accusative article is the key: den for masc, die for fem, das for neut. "
        "Contrast with dative (dem/der/dem) which marks static location. "
        "JP: movement endpoint uses に / へ. "
        "ZH: 到/往/進入 + location; Traditional Chinese throughout. "
        "Use movement or placement verbs: gehen, laufen, legen, stellen, setzen, hängen, bringen, kriechen. "
        "Do not use static verbs (liegen, stehen, sein) as the primary verb. "
        "Do not use dative forms (im, in dem, auf dem, etc.) anywhere in the file."
    )

    return [
        FileSpec(
            path=f"06_target_accusative_endpoint/{filename}",
            focus=focus,
            required_terms=required,
            notes=notes + shared_suffix,
        )
        for filename, focus, required, notes in rows
    ]


def make_place_target_contrast_specs() -> list[FileSpec]:
    """Specs for `07_place_target_contrast`: dative static location vs. accusative movement endpoint."""
    rows: list[tuple[str, str, tuple[str, ...], str]] = [
        # ── auf (onto / on) ───────────────────────────────────────────────
        ("001_auf_contrast_masc.md",
         "auf contrast masc — auf dem Tisch (static) vs. auf den Tisch (endpoint)",
         ("auf dem Tisch", "auf den Tisch"),
         "Direct contrast file: alternate static dative and movement accusative within the same file. "
         "Pair 1 (STATIC): Der Becher ist auf dem Tisch. — the cup is already on the table. "
         "Pair 2 (ENDPOINT): Emma stellt den Becher auf den Tisch. — Emma places the cup onto the table. "
         "Pair 3 (STATIC): Das Buch liegt auf dem Tisch. — the book is lying on the table. "
         "Pair 4 (ENDPOINT): Taro legt das Buch auf den Tisch. — Taro lays the book onto the table. "
         "German: dative pairs use auf dem (masc), accusative pairs use auf den (masc). "
         "JP: static pairs use テーブルの上にある, endpoint pairs use テーブルの上に置く. "
         "ZH: static pairs use 在桌子上, endpoint pairs use 放到桌子上. "
         "Make the German article contrast (dem vs. den) clearly visible in every line."),
        ("002_auf_contrast_fem.md",
         "auf contrast fem — auf der Bank (static) vs. auf die Bank (endpoint)",
         ("auf der Bank", "auf die Bank"),
         "Direct contrast file: alternate static dative and movement accusative within the same file. "
         "Pair 1 (STATIC): Das Buch liegt auf der Bank. — the book is lying on the bench. "
         "Pair 2 (ENDPOINT): Taro legt das Buch auf die Bank. — Taro lays the book onto the bench. "
         "Pair 3 (STATIC): Der Apfel liegt auf der Bank. — the apple is lying on the bench. "
         "Pair 4 (ENDPOINT): Gran legt den Apfel auf die Bank. — Gran lays the apple onto the bench. "
         "German: dative pairs use auf der (fem), accusative pairs use auf die (fem). "
         "JP: static pairs use ベンチの上にある, endpoint pairs use ベンチの上に置く. "
         "ZH: static pairs use 在長椅上, endpoint pairs use 放到長椅上. "
         "Make the German article contrast (der vs. die) clearly visible in every line."),
        ("003_auf_contrast_neut.md",
         "auf contrast neut — auf dem Bett (static) vs. auf das Bett (endpoint)",
         ("auf dem Bett", "auf das Bett"),
         "Direct contrast file: alternate static dative and movement accusative within the same file. "
         "Pair 1 (STATIC): Die Decke liegt auf dem Bett. — the blanket is lying on the bed. "
         "Pair 2 (ENDPOINT): Emma legt die Decke auf das Bett. — Emma lays the blanket onto the bed. "
         "Pair 3 (STATIC): Das Buch liegt auf dem Bett. — the book is lying on the bed. "
         "Pair 4 (ENDPOINT): Gran legt das Buch auf das Bett. — Gran lays the book onto the bed. "
         "German: dative pairs use auf dem (neut), accusative pairs use auf das (neut). "
         "JP: static pairs use ベッドの上にある, endpoint pairs use ベッドの上に置く. "
         "ZH: static pairs use 在床上, endpoint pairs use 放到床上. "
         "Make the German article contrast (dem vs. das) clearly visible in every line. "
         "Allow: Decke (blanket, fem)."),
        ("004_auf_gender_contrast.md",
         "auf gender contrast — masc/fem/neut: show dem/der/dem (static) vs. den/die/das (endpoint)",
         ("auf dem", "auf der", "auf den", "auf die"),
         "Four-way gender and case contrast for auf. "
         "Pair 1 (STATIC masc): Der Becher steht auf dem Tisch. (auf dem — dative masc). "
         "Pair 2 (ENDPOINT masc): Emma stellt den Becher auf den Tisch. (auf den — accusative masc). "
         "Pair 3 (STATIC fem): Das Buch liegt auf der Bank. (auf der — dative fem). "
         "Pair 4 (ENDPOINT fem): Taro legt das Buch auf die Bank. (auf die — accusative fem). "
         "JP: static pairs use の上にある/の上にいる, endpoint pairs use の上に置く/の上に乗る. "
         "ZH: static pairs use 在〜上, endpoint pairs use 放到〜上. "
         "Make the article change (dem→den, der→die) the visual anchor of each pair."),
        ("005_auf_contrast_masc_b.md",
         "auf contrast masc b — auf dem Stuhl (static) vs. auf den Stuhl (endpoint)",
         ("auf dem Stuhl", "auf den Stuhl"),
         "Direct contrast file with a second masc target. "
         "Pair 1 (STATIC): Das Kind sitzt auf dem Stuhl. — the child is sitting on the chair. "
         "Pair 2 (ENDPOINT): Das Kind setzt sich auf den Stuhl. — the child sits down onto the chair. "
         "Pair 3 (STATIC): Die Katze sitzt auf dem Stuhl. — the cat is sitting on the chair. "
         "Pair 4 (ENDPOINT): Gran setzt die Katze auf den Stuhl. — Gran places the cat onto the chair. "
         "German: dative auf dem (masc), accusative auf den (masc). "
         "JP: static pairs use 椅子の上にいる/座っている, endpoint pairs use 椅子の上に座る/置く. "
         "ZH: static pairs use 在椅子上, endpoint pairs use 坐到椅子上/放到椅子上. "
         "Allow: Katze (cat, fem)."),
        ("006_auf_contrast_neut_b.md",
         "auf contrast neut b — auf dem Boden (static) vs. auf den Boden (endpoint)",
         ("auf dem Boden", "auf den Boden"),
         "Direct contrast file with a second neut target. "
         "Pair 1 (STATIC): Der Ball liegt auf dem Boden. — the ball is lying on the floor. "
         "Pair 2 (ENDPOINT): Emma legt den Ball auf den Boden. — Emma lays the ball onto the floor. "
         "Pair 3 (STATIC): Das Buch liegt auf dem Boden. — the book is lying on the floor. "
         "Pair 4 (ENDPOINT): Taro legt das Buch auf den Boden. — Taro lays the book onto the floor. "
         "German: dative auf dem (neut), accusative auf den (neut). "
         "JP: static pairs use 床の上にある, endpoint pairs use 床の上に置く. "
         "ZH: static pairs use 在地板上, endpoint pairs use 放到地板上. "
         "Allow: Ball (ball, masc)."),
        ("007_auf_question_masc.md",
         "auf question contrast masc — Wo? (dative) vs. Wohin? (accusative) for Tisch",
         ("auf dem Tisch", "auf den Tisch"),
         "Question-driven contrast file for auf + masc. "
         "Pair 1 (Wo? — STATIC): [user] asks where the cup is. [Ninereeds] answers: Der Becher steht auf dem Tisch. "
         "Pair 2 (Wohin? — ENDPOINT): [user] asks where Emma puts the cup. [Ninereeds] answers: Emma stellt den Becher auf den Tisch. "
         "Pair 3 (Wo? — STATIC): [user] asks where the apple is. [Ninereeds] answers: Der Apfel liegt auf dem Tisch. "
         "Pair 4 (Wohin? — ENDPOINT): [user] asks where Taro lays the apple. [Ninereeds] answers: Taro legt den Apfel auf den Tisch. "
         "The Wo? question gets a dative answer; the Wohin? question gets an accusative answer. "
         "JP: static 〜の上にある, endpoint 〜の上に置く. ZH: static 在〜上, endpoint 放到〜上."),
        ("008_auf_question_fem.md",
         "auf question contrast fem — Wo? (dative) vs. Wohin? (accusative) for Bank",
         ("auf der Bank", "auf die Bank"),
         "Question-driven contrast file for auf + fem. "
         "Pair 1 (Wo? — STATIC): [user] asks where the book is. [Ninereeds] answers: Das Buch liegt auf der Bank. "
         "Pair 2 (Wohin? — ENDPOINT): [user] asks where Taro lays the book. [Ninereeds] answers: Taro legt das Buch auf die Bank. "
         "Pair 3 (Wo? — STATIC): [user] asks where the bag is. [Ninereeds] answers: Die Tasche liegt auf der Bank. "
         "Pair 4 (Wohin? — ENDPOINT): [user] asks where Gran lays the bag. [Ninereeds] answers: Gran legt die Tasche auf die Bank. "
         "The Wo? question gets a dative answer; the Wohin? question gets an accusative answer. "
         "JP: static 〜の上にある, endpoint 〜の上に置く. ZH: static 在〜上, endpoint 放到〜上. "
         "Allow: Tasche (bag, fem)."),
        ("009_auf_question_neut.md",
         "auf question contrast neut — Wo? (dative) vs. Wohin? (accusative) for Bett",
         ("auf dem Bett", "auf das Bett"),
         "Question-driven contrast file for auf + neut. "
         "Pair 1 (Wo? — STATIC): [user] asks where the blanket is. [Ninereeds] answers: Die Decke liegt auf dem Bett. "
         "Pair 2 (Wohin? — ENDPOINT): [user] asks where Emma lays the blanket. [Ninereeds] answers: Emma legt die Decke auf das Bett. "
         "Pair 3 (Wo? — STATIC): [user] asks where the book is. [Ninereeds] answers: Das Buch liegt auf dem Bett. "
         "Pair 4 (Wohin? — ENDPOINT): [user] asks where Gran lays the book. [Ninereeds] answers: Gran legt das Buch auf das Bett. "
         "The Wo? question gets a dative answer; the Wohin? question gets an accusative answer. "
         "JP: static 〜の上にある, endpoint 〜の上に置く. ZH: static 在〜上, endpoint 放到〜上. "
         "Allow: Decke (blanket, fem)."),
        ("010_auf_stellen_vs_steht.md",
         "auf stellen vs. steht — verb contrast: steht auf dem Tisch (static) vs. stellt auf den Tisch (endpoint)",
         ("auf dem Tisch", "auf den Tisch", "stellt"),
         "Verb-focused contrast file for auf + masc. Focus on steht (stands, static) vs. stellt (places, endpoint). "
         "Pair 1 (STATIC): Der Becher steht auf dem Tisch. — the cup stands on the table. "
         "Pair 2 (ENDPOINT): Emma stellt den Becher auf den Tisch. — Emma places the cup onto the table. "
         "Pair 3 (STATIC): Die Flasche steht auf dem Tisch. — the bottle stands on the table. "
         "Pair 4 (ENDPOINT): Taro stellt die Flasche auf den Tisch. — Taro places the bottle onto the table. "
         "German: dem (static) vs. den (endpoint). Use steht for static, stellt for endpoint. "
         "JP: 〜の上に立っている (static) vs. 〜の上に立てる/置く (endpoint). ZH: 在〜上 vs. 放到〜上."),
        ("011_auf_legen_vs_liegt.md",
         "auf legen vs. liegt — verb contrast: liegt auf der Bank (static) vs. legt auf die Bank (endpoint)",
         ("auf der Bank", "auf die Bank", "legt"),
         "Verb-focused contrast file for auf + fem. Focus on liegt (lies, static) vs. legt (lays, endpoint). "
         "Pair 1 (STATIC): Das Buch liegt auf der Bank. — the book lies on the bench. "
         "Pair 2 (ENDPOINT): Gran legt das Buch auf die Bank. — Gran lays the book onto the bench. "
         "Pair 3 (STATIC): Der Apfel liegt auf der Bank. — the apple lies on the bench. "
         "Pair 4 (ENDPOINT): Emma legt den Apfel auf die Bank. — Emma lays the apple onto the bench. "
         "German: der (static fem) vs. die (endpoint fem). Use liegt for static, legt for endpoint. "
         "JP: 〜の上にある (static) vs. 〜の上に置く (endpoint). ZH: 在〜上 vs. 放到〜上."),
        ("012_auf_legen_vs_liegt_b.md",
         "auf legen vs. liegt b — verb contrast: liegt auf dem Bett (static) vs. legt auf das Bett (endpoint)",
         ("auf dem Bett", "auf das Bett", "legt"),
         "Verb-focused contrast file for auf + neut. Focus on liegt (lies, static) vs. legt (lays, endpoint). "
         "Pair 1 (STATIC): Die Decke liegt auf dem Bett. — the blanket lies on the bed. "
         "Pair 2 (ENDPOINT): Emma legt die Decke auf das Bett. — Emma lays the blanket onto the bed. "
         "Pair 3 (STATIC): Das Kissen liegt auf dem Bett. — the pillow lies on the bed. "
         "Pair 4 (ENDPOINT): Taro legt das Kissen auf das Bett. — Taro lays the pillow onto the bed. "
         "German: dem (static neut) vs. das (endpoint neut). Use liegt for static, legt for endpoint. "
         "JP: 〜の上にある (static) vs. 〜の上に置く (endpoint). ZH: 在〜上 vs. 放到〜上. "
         "Allow: Kissen (pillow, neut), Decke (blanket, fem)."),
        ("013_auf_full_contrast.md",
         "auf full contrast — mixed static/endpoint across masc, fem, neut targets",
         ("auf dem", "auf den"),
         "Mixed contrast file for auf. Cover all three genders, alternating static and endpoint. "
         "Pair 1 (STATIC masc): Der Becher steht auf dem Tisch. "
         "Pair 2 (ENDPOINT masc): Emma stellt den Becher auf den Tisch. "
         "Pair 3 (STATIC fem): Das Buch liegt auf der Bank. "
         "Pair 4 (ENDPOINT neut): Gran legt das Kissen auf das Bett. "
         "Mix dative (dem/der/dem) and accusative (den/die/das) across the 4 pairs. "
         "JP: alternate にある (static) and に置く (endpoint). ZH: alternate 在〜上 (static) and 放到〜上 (endpoint). "
         "Allow: Kissen (pillow, neut)."),
        # ── in (into / in) ────────────────────────────────────────────────
        ("014_in_contrast_masc.md",
         "in contrast masc — in dem Garten (static) vs. in den Garten (endpoint)",
         ("in dem Garten", "in den Garten"),
         "Direct contrast file: alternate static dative and movement accusative within the same file. "
         "Pair 1 (STATIC): Emma ist in dem Garten. — Emma is in the garden. "
         "Pair 2 (ENDPOINT): Emma geht in den Garten. — Emma goes into the garden. "
         "Pair 3 (STATIC): Der Ball ist in dem Garten. — the ball is in the garden. "
         "Pair 4 (ENDPOINT): Taro bringt den Ball in den Garten. — Taro brings the ball into the garden. "
         "German: dative in dem (masc), accusative in den (masc). "
         "JP: static pairs use 庭にいる/庭にある, endpoint pairs use 庭に入る/庭に持っていく. "
         "ZH: static pairs use 在花園裡, endpoint pairs use 走進花園/帶進花園. "
         "Allow: Ball (ball, masc)."),
        ("015_in_contrast_fem.md",
         "in contrast fem — in der Küche (static) vs. in die Küche (endpoint)",
         ("in der Küche", "in die Küche"),
         "Direct contrast file: alternate static dative and movement accusative within the same file. "
         "Pair 1 (STATIC): Gran ist in der Küche. — Gran is in the kitchen. "
         "Pair 2 (ENDPOINT): Gran geht in die Küche. — Gran goes into the kitchen. "
         "Pair 3 (STATIC): Der Apfel ist in der Küche. — the apple is in the kitchen. "
         "Pair 4 (ENDPOINT): Emma bringt den Apfel in die Küche. — Emma brings the apple into the kitchen. "
         "German: dative in der (fem), accusative in die (fem). "
         "JP: static pairs use 台所にいる/台所にある, endpoint pairs use 台所に入る/台所に持ってくる. "
         "ZH: static pairs use 在廚房裡, endpoint pairs use 走進廚房/帶進廚房."),
        ("016_in_contrast_neut.md",
         "in contrast neut — in dem Zimmer (static) vs. in das Zimmer (endpoint)",
         ("in dem Zimmer", "in das Zimmer"),
         "Direct contrast file: alternate static dative and movement accusative within the same file. "
         "Pair 1 (STATIC): Taro ist in dem Zimmer. — Taro is in the room. "
         "Pair 2 (ENDPOINT): Taro geht in das Zimmer. — Taro goes into the room. "
         "Pair 3 (STATIC): Das Buch ist in dem Zimmer. — the book is in the room. "
         "Pair 4 (ENDPOINT): Gran legt das Buch in das Zimmer. — Gran lays the book into the room. "
         "German: dative in dem (neut), accusative in das (neut). "
         "JP: static pairs use 部屋にいる/部屋にある, endpoint pairs use 部屋に入る/部屋に置く. "
         "ZH: static pairs use 在房間裡, endpoint pairs use 走進房間/放進房間."),
        ("017_in_gender_contrast.md",
         "in gender contrast — masc/fem/neut: in dem/der/dem (static) vs. in den/die/das (endpoint)",
         ("in dem", "in der", "in den", "in die"),
         "Four-way gender and case contrast for in. "
         "Pair 1 (STATIC masc): Emma ist in dem Garten. (in dem — dative masc). "
         "Pair 2 (ENDPOINT masc): Emma geht in den Garten. (in den — accusative masc). "
         "Pair 3 (STATIC fem): Gran ist in der Küche. (in der — dative fem). "
         "Pair 4 (ENDPOINT fem): Gran geht in die Küche. (in die — accusative fem). "
         "JP: static pairs use 〜にいる, endpoint pairs use 〜に入る/〜に行く. "
         "ZH: static pairs use 在〜裡, endpoint pairs use 走進〜. "
         "Make the article change (dem→den, der→die) the visual anchor of each pair."),
        ("018_in_contrast_masc_b.md",
         "in contrast masc b — in dem Park (static) vs. in den Park (endpoint)",
         ("in dem Park", "in den Park"),
         "Direct contrast file with a second masc space. "
         "Pair 1 (STATIC): Das Kind spielt in dem Park. — the child plays in the park. "
         "Pair 2 (ENDPOINT): Das Kind läuft in den Park. — the child runs into the park. "
         "Pair 3 (STATIC): Emma ist in dem Park. — Emma is in the park. "
         "Pair 4 (ENDPOINT): Emma geht in den Park. — Emma goes into the park. "
         "German: dative in dem (masc), accusative in den (masc). "
         "JP: static 公園にいる, endpoint 公園に走って入る/公園へ行く. ZH: static 在公園裡, endpoint 走進公園."),
        ("019_in_contrast_neut_b.md",
         "in contrast neut b — in dem Haus (static) vs. in das Haus (endpoint)",
         ("in dem Haus", "in das Haus"),
         "Direct contrast file with a second neut space. "
         "Pair 1 (STATIC): Gran ist in dem Haus. — Gran is in the house. "
         "Pair 2 (ENDPOINT): Gran geht in das Haus. — Gran goes into the house. "
         "Pair 3 (STATIC): Der Hund ist in dem Haus. — the dog is in the house. "
         "Pair 4 (ENDPOINT): Taro bringt den Hund in das Haus. — Taro brings the dog into the house. "
         "German: dative in dem (neut), accusative in das (neut). "
         "JP: static 家の中にいる, endpoint 家に入る/家に連れていく. ZH: static 在房子裡, endpoint 走進房子/帶進房子."),
        ("020_in_question_masc.md",
         "in question contrast masc — Wo? (dative) vs. Wohin? (accusative) for Garten",
         ("in dem Garten", "in den Garten"),
         "Question-driven contrast file for in + masc. "
         "Pair 1 (Wo? — STATIC): [user] asks where Emma is. [Ninereeds] answers: Emma ist in dem Garten. "
         "Pair 2 (Wohin? — ENDPOINT): [user] asks where Emma goes. [Ninereeds] answers: Emma geht in den Garten. "
         "Pair 3 (Wo? — STATIC): [user] asks where the dog is. [Ninereeds] answers: Der Hund ist in dem Garten. "
         "Pair 4 (Wohin? — ENDPOINT): [user] asks where Taro brings the dog. [Ninereeds] answers: Taro bringt den Hund in den Garten. "
         "Wo? → dative answer (in dem). Wohin? → accusative answer (in den). "
         "JP: static 庭にいる, endpoint 庭に行く. ZH: static 在花園裡, endpoint 走進花園."),
        ("021_in_question_fem.md",
         "in question contrast fem — Wo? (dative) vs. Wohin? (accusative) for Küche",
         ("in der Küche", "in die Küche"),
         "Question-driven contrast file for in + fem. "
         "Pair 1 (Wo? — STATIC): [user] asks where Gran is. [Ninereeds] answers: Gran ist in der Küche. "
         "Pair 2 (Wohin? — ENDPOINT): [user] asks where Gran goes. [Ninereeds] answers: Gran geht in die Küche. "
         "Pair 3 (Wo? — STATIC): [user] asks where the apple is. [Ninereeds] answers: Der Apfel ist in der Küche. "
         "Pair 4 (Wohin? — ENDPOINT): [user] asks where Emma brings the apple. [Ninereeds] answers: Emma bringt den Apfel in die Küche. "
         "Wo? → dative answer (in der). Wohin? → accusative answer (in die). "
         "JP: static 台所にいる/ある, endpoint 台所に行く/持ってくる. ZH: static 在廚房裡, endpoint 走進廚房."),
        ("022_in_question_neut.md",
         "in question contrast neut — Wo? (dative) vs. Wohin? (accusative) for Zimmer",
         ("in dem Zimmer", "in das Zimmer"),
         "Question-driven contrast file for in + neut. "
         "Pair 1 (Wo? — STATIC): [user] asks where Taro is. [Ninereeds] answers: Taro ist in dem Zimmer. "
         "Pair 2 (Wohin? — ENDPOINT): [user] asks where Taro goes. [Ninereeds] answers: Taro geht in das Zimmer. "
         "Pair 3 (Wo? — STATIC): [user] asks where the book is. [Ninereeds] answers: Das Buch ist in dem Zimmer. "
         "Pair 4 (Wohin? — ENDPOINT): [user] asks where Gran lays the book. [Ninereeds] answers: Gran legt das Buch in das Zimmer. "
         "Wo? → dative answer (in dem). Wohin? → accusative answer (in das). "
         "JP: static 部屋にいる/ある, endpoint 部屋に行く/置く. ZH: static 在房間裡, endpoint 走進房間."),
        ("023_in_stehen_vs_stellt.md",
         "in stehen vs. stellt — in der Küche steht (static) vs. in die Küche stellt (endpoint)",
         ("in der Küche", "in die Küche", "stellt"),
         "Verb-focused contrast file for in + fem. Focus on steht (stands, static) vs. stellt (places, endpoint). "
         "Pair 1 (STATIC): Die Flasche steht in der Küche. — the bottle stands in the kitchen. "
         "Pair 2 (ENDPOINT): Taro stellt die Flasche in die Küche. — Taro places the bottle into the kitchen. "
         "Pair 3 (STATIC): Der Becher steht in der Küche. — the cup stands in the kitchen. "
         "Pair 4 (ENDPOINT): Emma stellt den Becher in die Küche. — Emma places the cup into the kitchen. "
         "German: in der (static fem) vs. in die (endpoint fem). Use steht for static, stellt for endpoint. "
         "JP: 〜にある (static) vs. 〜に置く (endpoint). ZH: 在〜裡 vs. 放進〜."),
        ("024_in_liegen_vs_legt.md",
         "in liegen vs. legt — in dem Zimmer liegt (static) vs. in das Zimmer legt (endpoint)",
         ("in dem Zimmer", "in das Zimmer", "legt"),
         "Verb-focused contrast file for in + neut. Focus on liegt (lies, static) vs. legt (lays, endpoint). "
         "Pair 1 (STATIC): Das Buch liegt in dem Zimmer. — the book lies in the room. "
         "Pair 2 (ENDPOINT): Gran legt das Buch in das Zimmer. — Gran lays the book into the room. "
         "Pair 3 (STATIC): Der Apfel liegt in dem Zimmer. — the apple lies in the room. "
         "Pair 4 (ENDPOINT): Emma legt den Apfel in das Zimmer. — Emma lays the apple into the room. "
         "German: in dem (static neut) vs. in das (endpoint neut). Use liegt for static, legt for endpoint. "
         "JP: 〜にある (static) vs. 〜に置く (endpoint). ZH: 在〜裡 vs. 放進〜."),
        ("025_in_ist_vs_geht.md",
         "in ist vs. geht — ist in dem Haus (static) vs. geht in das Haus (endpoint)",
         ("in dem Haus", "in das Haus", "geht"),
         "Verb-focused contrast for in + neut: ist (is, static) vs. geht (goes, endpoint). "
         "Pair 1 (STATIC): Gran ist in dem Haus. — Gran is in the house. "
         "Pair 2 (ENDPOINT): Gran geht in das Haus. — Gran goes into the house. "
         "Pair 3 (STATIC): Emma ist in dem Haus. — Emma is in the house. "
         "Pair 4 (ENDPOINT): Emma geht in das Haus. — Emma goes into the house. "
         "German: in dem (static neut) vs. in das (endpoint neut). Use ist for static, geht for endpoint. "
         "JP: 家の中にいる (static) vs. 家に入る (endpoint). ZH: 在房子裡 vs. 走進房子."),
        ("026_in_full_contrast.md",
         "in full contrast — mixed static/endpoint across masc, fem, neut targets",
         ("in dem", "in den"),
         "Mixed contrast file for in. Cover masc, fem, and neut, alternating static and endpoint. "
         "Pair 1 (STATIC masc): Emma ist in dem Garten. "
         "Pair 2 (ENDPOINT masc): Emma geht in den Garten. "
         "Pair 3 (STATIC fem): Gran ist in der Küche. "
         "Pair 4 (ENDPOINT neut): Taro geht in das Zimmer. "
         "Mix dative (dem/der/dem) and accusative (den/die/das) across the 4 pairs. "
         "JP: alternate にいる (static) and に入る (endpoint). ZH: alternate 在〜裡 (static) and 走進〜 (endpoint)."),
        # ── über (over/above) ─────────────────────────────────────────────
        ("027_ueber_contrast_masc.md",
         "über contrast masc — über dem Tisch (static) vs. über den Tisch (endpoint)",
         ("über dem Tisch", "über den Tisch"),
         "Direct contrast file: alternate static dative and movement accusative within the same file. "
         "Pair 1 (STATIC): Die Lampe hängt über dem Tisch. — the lamp hangs over the table. "
         "Pair 2 (ENDPOINT): Taro hängt die Lampe über den Tisch. — Taro hangs the lamp over the table. "
         "Pair 3 (STATIC): Das Bild hängt über dem Tisch. — the picture hangs over the table. "
         "Pair 4 (ENDPOINT): Emma hängt das Bild über den Tisch. — Emma hangs the picture over the table. "
         "German: dative über dem (masc), accusative über den (masc). "
         "JP: static テーブルの上にかかっている, endpoint テーブルの上に掛ける. "
         "ZH: static 在桌子上方, endpoint 掛到桌子上方. "
         "Allow: Lampe (lamp, fem), Bild (picture, neut)."),
        ("028_ueber_contrast_fem.md",
         "über contrast fem — über der Bank (static) vs. über die Bank (endpoint)",
         ("über der Bank", "über die Bank"),
         "Direct contrast file for über + fem. "
         "Pair 1 (STATIC): Das Tuch hängt über der Bank. — the cloth hangs over the bench. "
         "Pair 2 (ENDPOINT): Emma hängt das Tuch über die Bank. — Emma hangs the cloth over the bench. "
         "Pair 3 (STATIC): Die Decke liegt über der Bank. — the blanket lies over the bench. "
         "Pair 4 (ENDPOINT): Gran legt die Decke über die Bank. — Gran lays the blanket over the bench. "
         "German: dative über der (fem), accusative über die (fem). "
         "JP: static ベンチの上にかかっている/ある, endpoint ベンチの上に掛ける/置く. "
         "ZH: static 在長椅上方, endpoint 掛到/蓋到長椅上方. "
         "Allow: Tuch (cloth, neut), Decke (blanket, fem)."),
        ("029_ueber_contrast_neut.md",
         "über contrast neut — über dem Bett (static) vs. über das Bett (endpoint)",
         ("über dem Bett", "über das Bett"),
         "Direct contrast file for über + neut. "
         "Pair 1 (STATIC): Das Bild hängt über dem Bett. — the picture hangs over the bed. "
         "Pair 2 (ENDPOINT): Gran hängt das Bild über das Bett. — Gran hangs the picture over the bed. "
         "Pair 3 (STATIC): Die Decke liegt über dem Bett. — the blanket lies over the bed. "
         "Pair 4 (ENDPOINT): Emma legt die Decke über das Bett. — Emma lays the blanket over the bed. "
         "German: dative über dem (neut), accusative über das (neut). "
         "JP: static ベッドの上にかかっている/ある, endpoint ベッドの上に掛ける/置く. "
         "ZH: static 在床上方, endpoint 掛到/蓋到床上方. "
         "Allow: Bild (picture, neut), Decke (blanket, fem)."),
        ("030_ueber_gender_contrast.md",
         "über gender contrast — masc/fem/neut: über dem/der/dem (static) vs. über den/die/das (endpoint)",
         ("über dem", "über der", "über den", "über die"),
         "Four-way gender and case contrast for über. "
         "Pair 1 (STATIC masc): Das Bild hängt über dem Tisch. (über dem — dative masc). "
         "Pair 2 (ENDPOINT masc): Emma hängt das Bild über den Tisch. (über den — accusative masc). "
         "Pair 3 (STATIC fem): Die Lampe hängt über der Bank. (über der — dative fem). "
         "Pair 4 (ENDPOINT fem): Taro hängt die Lampe über die Bank. (über die — accusative fem). "
         "JP: static の上にかかっている, endpoint の上に掛ける. ZH: static 在〜上方, endpoint 掛到〜上方. "
         "Allow: Lampe (lamp, fem). Make article change (dem→den, der→die) the visual anchor."),
        ("031_ueber_contrast_masc_b.md",
         "über contrast masc b — über dem Stuhl (static) vs. über den Stuhl (endpoint)",
         ("über dem Stuhl", "über den Stuhl"),
         "Direct contrast file with a second masc target. "
         "Pair 1 (STATIC): Die Jacke hängt über dem Stuhl. — the jacket hangs over the chair. "
         "Pair 2 (ENDPOINT): Gran hängt die Jacke über den Stuhl. — Gran hangs the jacket over the chair. "
         "Pair 3 (STATIC): Das Tuch liegt über dem Stuhl. — the cloth lies over the chair. "
         "Pair 4 (ENDPOINT): Emma legt das Tuch über den Stuhl. — Emma lays the cloth over the chair. "
         "German: dative über dem (masc), accusative über den (masc). "
         "JP: static 椅子の上にかかっている, endpoint 椅子の上に掛ける. ZH: static 在椅子上方, endpoint 掛到椅子上方. "
         "Allow: Jacke (jacket, fem), Tuch (cloth, neut)."),
        ("032_ueber_question_masc.md",
         "über question contrast masc — Wo? (dative) vs. Wohin? (accusative) for Tisch",
         ("über dem Tisch", "über den Tisch"),
         "Question-driven contrast file for über + masc. "
         "Pair 1 (Wo? — STATIC): [user] asks where the lamp is. [Ninereeds] answers: Die Lampe hängt über dem Tisch. "
         "Pair 2 (Wohin? — ENDPOINT): [user] asks where Taro hangs the lamp. [Ninereeds] answers: Taro hängt die Lampe über den Tisch. "
         "Pair 3 (Wo? — STATIC): [user] asks where the picture is. [Ninereeds] answers: Das Bild hängt über dem Tisch. "
         "Pair 4 (Wohin? — ENDPOINT): [user] asks where Emma hangs the picture. [Ninereeds] answers: Emma hängt das Bild über den Tisch. "
         "Wo? → dative (über dem). Wohin? → accusative (über den). "
         "Allow: Lampe (lamp, fem), Bild (picture, neut)."),
        ("033_ueber_question_fem.md",
         "über question contrast fem — Wo? (dative) vs. Wohin? (accusative) for Bank",
         ("über der Bank", "über die Bank"),
         "Question-driven contrast file for über + fem. "
         "Pair 1 (Wo? — STATIC): [user] asks where the cloth is. [Ninereeds] answers: Das Tuch hängt über der Bank. "
         "Pair 2 (Wohin? — ENDPOINT): [user] asks where Emma hangs the cloth. [Ninereeds] answers: Emma hängt das Tuch über die Bank. "
         "Pair 3 (Wo? — STATIC): [user] asks where the blanket is. [Ninereeds] answers: Die Decke liegt über der Bank. "
         "Pair 4 (Wohin? — ENDPOINT): [user] asks where Gran lays the blanket. [Ninereeds] answers: Gran legt die Decke über die Bank. "
         "Wo? → dative (über der). Wohin? → accusative (über die). "
         "Allow: Tuch (cloth, neut), Decke (blanket, fem)."),
        ("034_ueber_haengt_vs_haengt.md",
         "über hängt vs. hängt — Das Bild hängt über dem Bett (static) vs. Emma hängt das Bild über das Bett (endpoint)",
         ("über dem Bett", "über das Bett", "hängt"),
         "Verb-focused contrast file for über + neut. Focus on hängt (hangs, static) vs. hängt ... (hangs, endpoint action). "
         "Pair 1 (STATIC): Das Bild hängt über dem Bett. — the picture hangs over the bed (already there). "
         "Pair 2 (ENDPOINT): Gran hängt das Bild über das Bett. — Gran hangs the picture over the bed (puts it there). "
         "Pair 3 (STATIC): Die Lampe hängt über dem Bett. — the lamp hangs over the bed. "
         "Pair 4 (ENDPOINT): Emma hängt die Lampe über das Bett. — Emma hangs the lamp over the bed. "
         "German: dative über dem (neut) for static, accusative über das (neut) for endpoint. "
         "JP: static ベッドの上にかかっている, endpoint ベッドの上に掛ける. ZH: static 在床上方, endpoint 掛到床上方. "
         "Allow: Bild (picture, neut), Lampe (lamp, fem)."),
        ("035_ueber_legt_vs_liegt.md",
         "über legt vs. liegt — liegt über der Bank (static) vs. legt über die Bank (endpoint)",
         ("über der Bank", "über die Bank", "legt"),
         "Verb-focused contrast for über + fem: liegt (lies, static) vs. legt (lays, endpoint). "
         "Pair 1 (STATIC): Die Decke liegt über der Bank. — the blanket lies over the bench. "
         "Pair 2 (ENDPOINT): Emma legt die Decke über die Bank. — Emma lays the blanket over the bench. "
         "Pair 3 (STATIC): Das Tuch liegt über der Bank. — the cloth lies over the bench. "
         "Pair 4 (ENDPOINT): Taro legt das Tuch über die Bank. — Taro lays the cloth over the bench. "
         "German: über der (static fem) vs. über die (endpoint fem). "
         "JP: static 〜の上にある, endpoint 〜の上に置く/かける. ZH: static 在〜上方, endpoint 蓋到〜上. "
         "Allow: Decke (blanket, fem), Tuch (cloth, neut)."),
        ("036_ueber_full_contrast.md",
         "über full contrast — mixed static/endpoint across masc, fem, neut targets",
         ("über dem", "über den"),
         "Mixed contrast file for über. Cover all three genders, alternating static and endpoint. "
         "Pair 1 (STATIC masc): Das Bild hängt über dem Tisch. "
         "Pair 2 (ENDPOINT masc): Emma hängt das Bild über den Tisch. "
         "Pair 3 (STATIC fem): Die Lampe hängt über der Bank. "
         "Pair 4 (ENDPOINT neut): Gran hängt die Lampe über das Bett. "
         "Mix dative (dem/der/dem) and accusative (den/die/das) across the 4 pairs. "
         "JP: alternate かかっている (static) and 掛ける (endpoint). ZH: alternate 在〜上方 (static) and 掛到〜上方 (endpoint). "
         "Allow: Bild (picture, neut), Lampe (lamp, fem)."),
        ("037_ueber_contrast_neut_b.md",
         "über contrast neut b — über dem Boden (static) vs. über den Boden (endpoint)",
         ("über dem Boden", "über den Boden"),
         "Direct contrast file with a second neut target. "
         "Pair 1 (STATIC): Die Brücke liegt über dem Boden. — the bridge lies over the ground. "
         "Pair 2 (ENDPOINT): Emma hält die Decke über den Boden. — Emma holds the blanket over the ground. "
         "Pair 3 (STATIC): Das Netz hängt über dem Boden. — the net hangs over the ground. "
         "Pair 4 (ENDPOINT): Taro hängt das Netz über den Boden. — Taro hangs the net over the ground. "
         "German: dative über dem (neut), accusative über den (neut). "
         "JP: static 地面の上にある, endpoint 地面の上に掛ける/かざす. ZH: static 在地面上方, endpoint 掛到地面上方. "
         "Allow: Brücke (bridge, fem), Netz (net, neut), hält (holds, from halten)."),
        ("038_ueber_verb_contrast.md",
         "über verb contrast — different static and endpoint verbs across masc targets",
         ("über dem Tisch", "über den Tisch"),
         "Verb variety contrast file for über + masc. Use different verbs for static and endpoint. "
         "Pair 1 (STATIC): Das Bild hängt über dem Tisch. "
         "Pair 2 (ENDPOINT): Taro stellt die Vase über den Tisch. "
         "Pair 3 (STATIC): Die Lampe leuchtet über dem Tisch. "
         "Pair 4 (ENDPOINT): Emma hängt die Lampe über den Tisch. "
         "German: dative über dem, accusative über den. "
         "JP: static の上にある/かかっている, endpoint の上に掛ける/置く. ZH: static 在〜上方, endpoint 掛到/放到〜上方. "
         "Allow: Vase (vase, fem), leuchtet (shines/lights, from leuchten), Lampe (lamp, fem)."),
        # ── unter (under/below) ───────────────────────────────────────────
        ("039_unter_contrast_masc.md",
         "unter contrast masc — unter dem Tisch (static) vs. unter den Tisch (endpoint)",
         ("unter dem Tisch", "unter den Tisch"),
         "Direct contrast file for unter + masc. "
         "Pair 1 (STATIC): Der Hund liegt unter dem Tisch. — the dog lies under the table. "
         "Pair 2 (ENDPOINT): Der Hund kriecht unter den Tisch. — the dog crawls under the table. "
         "Pair 3 (STATIC): Das Buch liegt unter dem Tisch. — the book lies under the table. "
         "Pair 4 (ENDPOINT): Emma legt das Buch unter den Tisch. — Emma lays the book under the table. "
         "German: dative unter dem (masc), accusative unter den (masc). "
         "JP: static テーブルの下にいる/ある, endpoint テーブルの下に潜り込む/置く. "
         "ZH: static 在桌子下面, endpoint 爬到桌子下面/放到桌子下面."),
        ("040_unter_contrast_fem.md",
         "unter contrast fem — unter der Bank (static) vs. unter die Bank (endpoint)",
         ("unter der Bank", "unter die Bank"),
         "Direct contrast file for unter + fem. "
         "Pair 1 (STATIC): Der Apfel liegt unter der Bank. — the apple lies under the bench. "
         "Pair 2 (ENDPOINT): Emma legt den Apfel unter die Bank. — Emma lays the apple under the bench. "
         "Pair 3 (STATIC): Das Buch liegt unter der Bank. — the book lies under the bench. "
         "Pair 4 (ENDPOINT): Taro legt das Buch unter die Bank. — Taro lays the book under the bench. "
         "German: dative unter der (fem), accusative unter die (fem). "
         "JP: static ベンチの下にある, endpoint ベンチの下に置く. "
         "ZH: static 在長椅下面, endpoint 放到長椅下面."),
        ("041_unter_contrast_neut.md",
         "unter contrast neut — unter dem Bett (static) vs. unter das Bett (endpoint)",
         ("unter dem Bett", "unter das Bett"),
         "Direct contrast file for unter + neut. "
         "Pair 1 (STATIC): Der Becher liegt unter dem Bett. — the cup lies under the bed. "
         "Pair 2 (ENDPOINT): Gran legt den Becher unter das Bett. — Gran lays the cup under the bed. "
         "Pair 3 (STATIC): Das Buch liegt unter dem Bett. — the book lies under the bed. "
         "Pair 4 (ENDPOINT): Emma legt das Buch unter das Bett. — Emma lays the book under the bed. "
         "German: dative unter dem (neut), accusative unter das (neut). "
         "JP: static ベッドの下にある, endpoint ベッドの下に置く. "
         "ZH: static 在床下面, endpoint 放到床下面."),
        ("042_unter_gender_contrast.md",
         "unter gender contrast — masc/fem/neut: unter dem/der/dem (static) vs. unter den/die/das (endpoint)",
         ("unter dem", "unter der", "unter den", "unter die"),
         "Four-way gender and case contrast for unter. "
         "Pair 1 (STATIC masc): Das Buch liegt unter dem Tisch. (unter dem — dative masc). "
         "Pair 2 (ENDPOINT masc): Emma legt das Buch unter den Tisch. (unter den — accusative masc). "
         "Pair 3 (STATIC fem): Der Apfel liegt unter der Bank. (unter der — dative fem). "
         "Pair 4 (ENDPOINT fem): Taro legt den Apfel unter die Bank. (unter die — accusative fem). "
         "JP: static の下にある, endpoint の下に置く. ZH: static 在〜下面, endpoint 放到〜下面. "
         "Make article change (dem→den, der→die) the visual anchor of each pair."),
        ("043_unter_contrast_masc_b.md",
         "unter contrast masc b — unter dem Stuhl (static) vs. unter den Stuhl (endpoint)",
         ("unter dem Stuhl", "unter den Stuhl"),
         "Direct contrast file with a second masc target. "
         "Pair 1 (STATIC): Die Katze liegt unter dem Stuhl. — the cat lies under the chair. "
         "Pair 2 (ENDPOINT): Die Katze kriecht unter den Stuhl. — the cat crawls under the chair. "
         "Pair 3 (STATIC): Das Buch liegt unter dem Stuhl. — the book lies under the chair. "
         "Pair 4 (ENDPOINT): Emma legt das Buch unter den Stuhl. — Emma lays the book under the chair. "
         "German: dative unter dem (masc), accusative unter den (masc). "
         "JP: static 椅子の下にいる/ある, endpoint 椅子の下に潜り込む/置く. "
         "ZH: static 在椅子下面, endpoint 爬到/放到椅子下面. Allow: Katze (cat, fem)."),
        ("044_unter_question_masc.md",
         "unter question contrast masc — Wo? (dative) vs. Wohin? (accusative) for Tisch",
         ("unter dem Tisch", "unter den Tisch"),
         "Question-driven contrast file for unter + masc. "
         "Pair 1 (Wo? — STATIC): [user] asks where the dog is. [Ninereeds] answers: Der Hund liegt unter dem Tisch. "
         "Pair 2 (Wohin? — ENDPOINT): [user] asks where the dog crawls. [Ninereeds] answers: Der Hund kriecht unter den Tisch. "
         "Pair 3 (Wo? — STATIC): [user] asks where the apple is. [Ninereeds] answers: Der Apfel liegt unter dem Tisch. "
         "Pair 4 (Wohin? — ENDPOINT): [user] asks where Gran lays the apple. [Ninereeds] answers: Gran legt den Apfel unter den Tisch. "
         "Wo? → dative (unter dem). Wohin? → accusative (unter den)."),
        ("045_unter_question_fem.md",
         "unter question contrast fem — Wo? (dative) vs. Wohin? (accusative) for Bank",
         ("unter der Bank", "unter die Bank"),
         "Question-driven contrast file for unter + fem. "
         "Pair 1 (Wo? — STATIC): [user] asks where the book is. [Ninereeds] answers: Das Buch liegt unter der Bank. "
         "Pair 2 (Wohin? — ENDPOINT): [user] asks where Taro lays the book. [Ninereeds] answers: Taro legt das Buch unter die Bank. "
         "Pair 3 (Wo? — STATIC): [user] asks where the ball is. [Ninereeds] answers: Der Ball liegt unter der Bank. "
         "Pair 4 (Wohin? — ENDPOINT): [user] asks where Emma kicks the ball. [Ninereeds] answers: Emma schiebt den Ball unter die Bank. "
         "Wo? → dative (unter der). Wohin? → accusative (unter die). "
         "Allow: schiebt (pushes/slides, from schieben), Ball (ball, masc)."),
        ("046_unter_liegt_vs_legt.md",
         "unter liegt vs. legt — liegt unter dem Bett (static) vs. legt unter das Bett (endpoint)",
         ("unter dem Bett", "unter das Bett", "legt"),
         "Verb-focused contrast file for unter + neut. Focus on liegt (lies, static) vs. legt (lays, endpoint). "
         "Pair 1 (STATIC): Der Becher liegt unter dem Bett. — the cup lies under the bed. "
         "Pair 2 (ENDPOINT): Gran legt den Becher unter das Bett. — Gran lays the cup under the bed. "
         "Pair 3 (STATIC): Das Kissen liegt unter dem Bett. — the pillow lies under the bed. "
         "Pair 4 (ENDPOINT): Emma legt das Kissen unter das Bett. — Emma lays the pillow under the bed. "
         "German: unter dem (static neut) vs. unter das (endpoint neut). "
         "JP: 〜の下にある (static) vs. 〜の下に置く (endpoint). ZH: 在〜下面 vs. 放到〜下面. "
         "Allow: Kissen (pillow, neut)."),
        ("047_unter_ist_vs_kriecht.md",
         "unter ist vs. kriecht — ist unter dem Tisch (static) vs. kriecht unter den Tisch (endpoint)",
         ("unter dem Tisch", "unter den Tisch", "kriecht"),
         "Verb-focused contrast for unter + masc: ist (is, static) vs. kriecht (crawls, endpoint). "
         "Pair 1 (STATIC): Der Hund ist unter dem Tisch. — the dog is under the table. "
         "Pair 2 (ENDPOINT): Der Hund kriecht unter den Tisch. — the dog crawls under the table. "
         "Pair 3 (STATIC): Das Kind ist unter dem Tisch. — the child is under the table. "
         "Pair 4 (ENDPOINT): Das Kind kriecht unter den Tisch. — the child crawls under the table. "
         "German: unter dem (static masc) vs. unter den (endpoint masc). "
         "JP: テーブルの下にいる (static) vs. テーブルの下に潜り込む (endpoint). "
         "ZH: 在桌子下面 vs. 爬到桌子下面."),
        ("048_unter_contrast_neut_b.md",
         "unter contrast neut b — unter dem Boden (static) vs. unter den Boden (endpoint)",
         ("unter dem Boden", "unter den Boden"),
         "Direct contrast file with a second neut target. "
         "Pair 1 (STATIC): Das Rohr liegt unter dem Boden. — the pipe lies under the floor. "
         "Pair 2 (ENDPOINT): Gran legt das Rohr unter den Boden. — Gran lays the pipe under the floor. "
         "Pair 3 (STATIC): Der Stein liegt unter dem Boden. — the stone lies under the floor. "
         "Pair 4 (ENDPOINT): Emma legt den Stein unter den Boden. — Emma lays the stone under the floor. "
         "German: dative unter dem (neut), accusative unter den (neut). "
         "JP: static 地面の下にある, endpoint 地面の下に置く. ZH: static 在地面下面, endpoint 放到地面下面. "
         "Allow: Rohr (pipe, neut), Stein (stone, masc)."),
        ("049_unter_full_contrast.md",
         "unter full contrast — mixed static/endpoint across masc, fem, neut targets",
         ("unter dem", "unter den"),
         "Mixed contrast file for unter. Cover all three genders, alternating static and endpoint. "
         "Pair 1 (STATIC masc): Das Buch liegt unter dem Tisch. "
         "Pair 2 (ENDPOINT masc): Emma legt das Buch unter den Tisch. "
         "Pair 3 (STATIC fem): Der Apfel liegt unter der Bank. "
         "Pair 4 (ENDPOINT neut): Gran legt das Kissen unter das Bett. "
         "Mix dative (dem/der/dem) and accusative (den/die/das) across the 4 pairs. "
         "JP: alternate の下にある (static) and の下に置く (endpoint). ZH: alternate 在〜下面 (static) and 放到〜下面 (endpoint). "
         "Allow: Kissen (pillow, neut)."),
        ("050_unter_verb_contrast.md",
         "unter verb contrast — different agents and verbs: liegt/kriecht/legt across masc targets",
         ("unter dem Stuhl", "unter den Stuhl"),
         "Verb variety contrast file for unter + masc. Use different verbs for static and endpoint. "
         "Pair 1 (STATIC): Die Katze liegt unter dem Stuhl. "
         "Pair 2 (ENDPOINT): Die Katze kriecht unter den Stuhl. "
         "Pair 3 (STATIC): Das Buch liegt unter dem Stuhl. "
         "Pair 4 (ENDPOINT): Emma schiebt das Buch unter den Stuhl. "
         "German: dative unter dem, accusative unter den. "
         "JP: static 椅子の下にいる/ある, endpoint 椅子の下に潜る/押し込む. "
         "ZH: static 在椅子下面, endpoint 爬到/推到椅子下面. "
         "Allow: Katze (cat, fem), schiebt (pushes, from schieben)."),
        # ── neben (beside) ────────────────────────────────────────────────
        ("051_neben_contrast_masc.md",
         "neben contrast masc — neben dem Stuhl (static) vs. neben den Stuhl (endpoint)",
         ("neben dem Stuhl", "neben den Stuhl"),
         "Direct contrast file for neben + masc. "
         "Pair 1 (STATIC): Der Becher steht neben dem Stuhl. — the cup stands beside the chair. "
         "Pair 2 (ENDPOINT): Emma stellt den Becher neben den Stuhl. — Emma places the cup beside the chair. "
         "Pair 3 (STATIC): Das Buch liegt neben dem Stuhl. — the book lies beside the chair. "
         "Pair 4 (ENDPOINT): Taro legt das Buch neben den Stuhl. — Taro lays the book beside the chair. "
         "German: dative neben dem (masc), accusative neben den (masc). "
         "JP: static 椅子の隣にある, endpoint 椅子の隣に置く. "
         "ZH: static 在椅子旁邊, endpoint 放到椅子旁邊."),
        ("052_neben_contrast_fem.md",
         "neben contrast fem — neben der Bank (static) vs. neben die Bank (endpoint)",
         ("neben der Bank", "neben die Bank"),
         "Direct contrast file for neben + fem. "
         "Pair 1 (STATIC): Der Becher steht neben der Bank. — the cup stands beside the bench. "
         "Pair 2 (ENDPOINT): Taro stellt den Becher neben die Bank. — Taro places the cup beside the bench. "
         "Pair 3 (STATIC): Das Buch liegt neben der Bank. — the book lies beside the bench. "
         "Pair 4 (ENDPOINT): Gran legt das Buch neben die Bank. — Gran lays the book beside the bench. "
         "German: dative neben der (fem), accusative neben die (fem). "
         "JP: static ベンチの隣にある, endpoint ベンチの隣に置く. "
         "ZH: static 在長椅旁邊, endpoint 放到長椅旁邊."),
        ("053_neben_contrast_neut.md",
         "neben contrast neut — neben dem Bett (static) vs. neben das Bett (endpoint)",
         ("neben dem Bett", "neben das Bett"),
         "Direct contrast file for neben + neut. "
         "Pair 1 (STATIC): Das Glas steht neben dem Bett. — the glass stands beside the bed. "
         "Pair 2 (ENDPOINT): Emma stellt das Glas neben das Bett. — Emma places the glass beside the bed. "
         "Pair 3 (STATIC): Der Becher steht neben dem Bett. — the cup stands beside the bed. "
         "Pair 4 (ENDPOINT): Gran stellt den Becher neben das Bett. — Gran places the cup beside the bed. "
         "German: dative neben dem (neut), accusative neben das (neut). "
         "JP: static ベッドの隣にある, endpoint ベッドの隣に置く. "
         "ZH: static 在床旁邊, endpoint 放到床旁邊. Allow: Glas (glass, neut)."),
        ("054_neben_gender_contrast.md",
         "neben gender contrast — masc/fem/neut: neben dem/der/dem (static) vs. neben den/die/das (endpoint)",
         ("neben dem", "neben der", "neben den", "neben die"),
         "Four-way gender and case contrast for neben. "
         "Pair 1 (STATIC masc): Der Becher steht neben dem Stuhl. (neben dem — dative masc). "
         "Pair 2 (ENDPOINT masc): Emma stellt den Becher neben den Stuhl. (neben den — accusative masc). "
         "Pair 3 (STATIC fem): Das Buch liegt neben der Bank. (neben der — dative fem). "
         "Pair 4 (ENDPOINT fem): Taro legt das Buch neben die Bank. (neben die — accusative fem). "
         "JP: static の隣にある, endpoint の隣に置く. ZH: static 在〜旁邊, endpoint 放到〜旁邊. "
         "Make article change (dem→den, der→die) the visual anchor of each pair."),
        ("055_neben_contrast_masc_b.md",
         "neben contrast masc b — neben dem Tisch (static) vs. neben den Tisch (endpoint)",
         ("neben dem Tisch", "neben den Tisch"),
         "Direct contrast file with a second masc target. "
         "Pair 1 (STATIC): Die Flasche steht neben dem Tisch. — the bottle stands beside the table. "
         "Pair 2 (ENDPOINT): Gran stellt die Flasche neben den Tisch. — Gran places the bottle beside the table. "
         "Pair 3 (STATIC): Das Glas steht neben dem Tisch. — the glass stands beside the table. "
         "Pair 4 (ENDPOINT): Emma stellt das Glas neben den Tisch. — Emma places the glass beside the table. "
         "German: dative neben dem (masc), accusative neben den (masc). "
         "JP: static テーブルの隣にある, endpoint テーブルの隣に置く. ZH: static 在桌子旁邊, endpoint 放到桌子旁邊. "
         "Allow: Glas (glass, neut)."),
        ("056_neben_question_masc.md",
         "neben question contrast masc — Wo? (dative) vs. Wohin? (accusative) for Stuhl",
         ("neben dem Stuhl", "neben den Stuhl"),
         "Question-driven contrast file for neben + masc. "
         "Pair 1 (Wo? — STATIC): [user] asks where the cup is. [Ninereeds] answers: Der Becher steht neben dem Stuhl. "
         "Pair 2 (Wohin? — ENDPOINT): [user] asks where Emma puts the cup. [Ninereeds] answers: Emma stellt den Becher neben den Stuhl. "
         "Pair 3 (Wo? — STATIC): [user] asks where the bag is. [Ninereeds] answers: Die Tasche steht neben dem Stuhl. "
         "Pair 4 (Wohin? — ENDPOINT): [user] asks where Taro puts the bag. [Ninereeds] answers: Taro stellt die Tasche neben den Stuhl. "
         "Wo? → dative (neben dem). Wohin? → accusative (neben den). "
         "Allow: Tasche (bag, fem)."),
        ("057_neben_question_fem.md",
         "neben question contrast fem — Wo? (dative) vs. Wohin? (accusative) for Bank",
         ("neben der Bank", "neben die Bank"),
         "Question-driven contrast file for neben + fem. "
         "Pair 1 (Wo? — STATIC): [user] asks where the book is. [Ninereeds] answers: Das Buch liegt neben der Bank. "
         "Pair 2 (Wohin? — ENDPOINT): [user] asks where Gran lays the book. [Ninereeds] answers: Gran legt das Buch neben die Bank. "
         "Pair 3 (Wo? — STATIC): [user] asks where the cup is. [Ninereeds] answers: Der Becher steht neben der Bank. "
         "Pair 4 (Wohin? — ENDPOINT): [user] asks where Emma puts the cup. [Ninereeds] answers: Emma stellt den Becher neben die Bank. "
         "Wo? → dative (neben der). Wohin? → accusative (neben die)."),
        ("058_neben_steht_vs_stellt.md",
         "neben steht vs. stellt — steht neben dem Tisch (static) vs. stellt neben den Tisch (endpoint)",
         ("neben dem Tisch", "neben den Tisch", "stellt"),
         "Verb-focused contrast for neben + masc: steht (stands, static) vs. stellt (places, endpoint). "
         "Pair 1 (STATIC): Die Flasche steht neben dem Tisch. "
         "Pair 2 (ENDPOINT): Gran stellt die Flasche neben den Tisch. "
         "Pair 3 (STATIC): Der Becher steht neben dem Tisch. "
         "Pair 4 (ENDPOINT): Emma stellt den Becher neben den Tisch. "
         "German: neben dem (static masc) vs. neben den (endpoint masc). "
         "JP: static テーブルの隣にある, endpoint テーブルの隣に置く. ZH: static 在桌子旁邊, endpoint 放到桌子旁邊."),
        ("059_neben_liegt_vs_legt.md",
         "neben liegt vs. legt — liegt neben der Bank (static) vs. legt neben die Bank (endpoint)",
         ("neben der Bank", "neben die Bank", "legt"),
         "Verb-focused contrast for neben + fem: liegt (lies, static) vs. legt (lays, endpoint). "
         "Pair 1 (STATIC): Das Buch liegt neben der Bank. "
         "Pair 2 (ENDPOINT): Taro legt das Buch neben die Bank. "
         "Pair 3 (STATIC): Der Apfel liegt neben der Bank. "
         "Pair 4 (ENDPOINT): Emma legt den Apfel neben die Bank. "
         "German: neben der (static fem) vs. neben die (endpoint fem). "
         "JP: static ベンチの隣にある, endpoint ベンチの隣に置く. ZH: static 在長椅旁邊, endpoint 放到長椅旁邊."),
        ("060_neben_contrast_neut_b.md",
         "neben contrast neut b — neben dem Feld (static) vs. neben das Feld (endpoint)",
         ("neben dem Feld", "neben das Feld"),
         "Direct contrast file with a second neut target. "
         "Pair 1 (STATIC): Der Baum steht neben dem Feld. — the tree stands beside the field. "
         "Pair 2 (ENDPOINT): Emma geht neben das Feld. — Emma goes beside the field. "
         "Pair 3 (STATIC): Das Haus steht neben dem Feld. — the house stands beside the field. "
         "Pair 4 (ENDPOINT): Taro stellt das Schild neben das Feld. — Taro places the sign beside the field. "
         "German: dative neben dem (neut), accusative neben das (neut). "
         "JP: static 畑の隣にある, endpoint 畑の隣に行く/置く. ZH: static 在田野旁邊, endpoint 走到/放到田野旁邊. "
         "Allow: Baum (tree, masc), Schild (sign, neut)."),
        ("061_neben_full_contrast.md",
         "neben full contrast — mixed static/endpoint across masc, fem, neut targets",
         ("neben dem", "neben den"),
         "Mixed contrast file for neben. Cover all three genders, alternating static and endpoint. "
         "Pair 1 (STATIC masc): Der Becher steht neben dem Stuhl. "
         "Pair 2 (ENDPOINT masc): Emma stellt den Becher neben den Stuhl. "
         "Pair 3 (STATIC fem): Das Buch liegt neben der Bank. "
         "Pair 4 (ENDPOINT neut): Gran stellt das Glas neben das Bett. "
         "Mix dative (dem/der/dem) and accusative (den/die/das) across the 4 pairs. "
         "JP: alternate の隣にある (static) and の隣に置く (endpoint). ZH: alternate 在〜旁邊 (static) and 放到〜旁邊 (endpoint). "
         "Allow: Glas (glass, neut)."),
        ("062_neben_verb_contrast.md",
         "neben verb contrast — different verbs: steht/stellt/liegt/legt across masc and fem targets",
         ("neben dem Tisch", "neben die Bank"),
         "Verb variety contrast for neben. Use steht/liegt for static, stellt/legt for endpoint. "
         "Pair 1 (STATIC masc): Der Becher steht neben dem Tisch. "
         "Pair 2 (ENDPOINT masc): Emma stellt den Becher neben den Tisch. "
         "Pair 3 (STATIC fem): Das Buch liegt neben der Bank. "
         "Pair 4 (ENDPOINT fem): Taro legt das Buch neben die Bank. "
         "German: dem/der for static, den/die for endpoint. "
         "JP: static の隣にある, endpoint の隣に置く. ZH: static 在〜旁邊, endpoint 放到〜旁邊."),
        # ── vor (in front of) ─────────────────────────────────────────────
        ("063_vor_contrast_masc.md",
         "vor contrast masc — vor dem Tisch (static) vs. vor den Tisch (endpoint)",
         ("vor dem Tisch", "vor den Tisch"),
         "Direct contrast file for vor + masc. "
         "Pair 1 (STATIC): Der Stuhl steht vor dem Tisch. — the chair stands in front of the table. "
         "Pair 2 (ENDPOINT): Emma stellt den Stuhl vor den Tisch. — Emma places the chair in front of the table. "
         "Pair 3 (STATIC): Der Becher steht vor dem Tisch. — the cup stands in front of the table. "
         "Pair 4 (ENDPOINT): Taro stellt den Becher vor den Tisch. — Taro places the cup in front of the table. "
         "German: dative vor dem (masc), accusative vor den (masc). "
         "JP: static テーブルの前にある, endpoint テーブルの前に置く. "
         "ZH: static 在桌子前面, endpoint 放到桌子前面."),
        ("064_vor_contrast_fem.md",
         "vor contrast fem — vor der Bank (static) vs. vor die Bank (endpoint)",
         ("vor der Bank", "vor die Bank"),
         "Direct contrast file for vor + fem. "
         "Pair 1 (STATIC): Das Buch liegt vor der Bank. — the book lies in front of the bench. "
         "Pair 2 (ENDPOINT): Emma legt das Buch vor die Bank. — Emma lays the book in front of the bench. "
         "Pair 3 (STATIC): Der Becher steht vor der Bank. — the cup stands in front of the bench. "
         "Pair 4 (ENDPOINT): Taro stellt den Becher vor die Bank. — Taro places the cup in front of the bench. "
         "German: dative vor der (fem), accusative vor die (fem). "
         "JP: static ベンチの前にある, endpoint ベンチの前に置く. "
         "ZH: static 在長椅前面, endpoint 放到長椅前面."),
        ("065_vor_contrast_neut.md",
         "vor contrast neut — vor dem Haus (static) vs. vor das Haus (endpoint)",
         ("vor dem Haus", "vor das Haus"),
         "Direct contrast file for vor + neut. "
         "Pair 1 (STATIC): Das Kind steht vor dem Haus. — the child stands in front of the house. "
         "Pair 2 (ENDPOINT): Das Kind geht vor das Haus. — the child goes in front of the house. "
         "Pair 3 (STATIC): Das Auto steht vor dem Haus. — the car stands in front of the house. "
         "Pair 4 (ENDPOINT): Taro fährt das Auto vor das Haus. — Taro drives the car in front of the house. "
         "German: dative vor dem (neut), accusative vor das (neut). "
         "JP: static 家の前にある/いる, endpoint 家の前に行く/持ってくる. "
         "ZH: static 在房子前面, endpoint 走到/開到房子前面. "
         "Allow: Auto (car, neut), fährt (drives, from fahren)."),
        ("066_vor_gender_contrast.md",
         "vor gender contrast — masc/fem/neut: vor dem/der/dem (static) vs. vor den/die/das (endpoint)",
         ("vor dem", "vor der", "vor den", "vor die"),
         "Four-way gender and case contrast for vor. "
         "Pair 1 (STATIC masc): Der Stuhl steht vor dem Tisch. (vor dem — dative masc). "
         "Pair 2 (ENDPOINT masc): Emma stellt den Stuhl vor den Tisch. (vor den — accusative masc). "
         "Pair 3 (STATIC fem): Das Buch liegt vor der Bank. (vor der — dative fem). "
         "Pair 4 (ENDPOINT fem): Taro legt das Buch vor die Bank. (vor die — accusative fem). "
         "JP: static の前にある, endpoint の前に置く. ZH: static 在〜前面, endpoint 放到〜前面. "
         "Make article change (dem→den, der→die) the visual anchor of each pair."),
        ("067_vor_contrast_masc_b.md",
         "vor contrast masc b — vor dem Stuhl (static) vs. vor den Stuhl (endpoint)",
         ("vor dem Stuhl", "vor den Stuhl"),
         "Direct contrast file with a second masc target. "
         "Pair 1 (STATIC): Der Becher steht vor dem Stuhl. — the cup stands in front of the chair. "
         "Pair 2 (ENDPOINT): Emma stellt den Becher vor den Stuhl. — Emma places the cup in front of the chair. "
         "Pair 3 (STATIC): Der Apfel liegt vor dem Stuhl. — the apple lies in front of the chair. "
         "Pair 4 (ENDPOINT): Gran legt den Apfel vor den Stuhl. — Gran lays the apple in front of the chair. "
         "German: dative vor dem (masc), accusative vor den (masc). "
         "JP: static 椅子の前にある, endpoint 椅子の前に置く. ZH: static 在椅子前面, endpoint 放到椅子前面."),
        ("068_vor_contrast_neut_b.md",
         "vor contrast neut b — vor dem Bett (static) vs. vor das Bett (endpoint)",
         ("vor dem Bett", "vor das Bett"),
         "Direct contrast file with a second neut target. "
         "Pair 1 (STATIC): Das Buch liegt vor dem Bett. — the book lies in front of the bed. "
         "Pair 2 (ENDPOINT): Emma legt das Buch vor das Bett. — Emma lays the book in front of the bed. "
         "Pair 3 (STATIC): Der Becher steht vor dem Bett. — the cup stands in front of the bed. "
         "Pair 4 (ENDPOINT): Taro stellt den Becher vor das Bett. — Taro places the cup in front of the bed. "
         "German: dative vor dem (neut), accusative vor das (neut). "
         "JP: static ベッドの前にある, endpoint ベッドの前に置く. ZH: static 在床前面, endpoint 放到床前面."),
        ("069_vor_question_masc.md",
         "vor question contrast masc — Wo? (dative) vs. Wohin? (accusative) for Tisch",
         ("vor dem Tisch", "vor den Tisch"),
         "Question-driven contrast file for vor + masc. "
         "Pair 1 (Wo? — STATIC): [user] asks where the chair is. [Ninereeds] answers: Der Stuhl steht vor dem Tisch. "
         "Pair 2 (Wohin? — ENDPOINT): [user] asks where Emma puts the chair. [Ninereeds] answers: Emma stellt den Stuhl vor den Tisch. "
         "Pair 3 (Wo? — STATIC): [user] asks where the cup is. [Ninereeds] answers: Der Becher steht vor dem Tisch. "
         "Pair 4 (Wohin? — ENDPOINT): [user] asks where Gran puts the cup. [Ninereeds] answers: Gran stellt den Becher vor den Tisch. "
         "Wo? → dative (vor dem). Wohin? → accusative (vor den)."),
        ("070_vor_question_fem.md",
         "vor question contrast fem — Wo? (dative) vs. Wohin? (accusative) for Bank",
         ("vor der Bank", "vor die Bank"),
         "Question-driven contrast file for vor + fem. "
         "Pair 1 (Wo? — STATIC): [user] asks where the bag is. [Ninereeds] answers: Die Tasche steht vor der Bank. "
         "Pair 2 (Wohin? — ENDPOINT): [user] asks where Taro puts the bag. [Ninereeds] answers: Taro stellt die Tasche vor die Bank. "
         "Pair 3 (Wo? — STATIC): [user] asks where the book is. [Ninereeds] answers: Das Buch liegt vor der Bank. "
         "Pair 4 (Wohin? — ENDPOINT): [user] asks where Emma lays the book. [Ninereeds] answers: Emma legt das Buch vor die Bank. "
         "Wo? → dative (vor der). Wohin? → accusative (vor die). "
         "Allow: Tasche (bag, fem)."),
        ("071_vor_question_neut.md",
         "vor question contrast neut — Wo? (dative) vs. Wohin? (accusative) for Haus",
         ("vor dem Haus", "vor das Haus"),
         "Question-driven contrast file for vor + neut. "
         "Pair 1 (Wo? — STATIC): [user] asks where the child is. [Ninereeds] answers: Das Kind steht vor dem Haus. "
         "Pair 2 (Wohin? — ENDPOINT): [user] asks where the child goes. [Ninereeds] answers: Das Kind geht vor das Haus. "
         "Pair 3 (Wo? — STATIC): [user] asks where the bicycle is. [Ninereeds] answers: Das Fahrrad steht vor dem Haus. "
         "Pair 4 (Wohin? — ENDPOINT): [user] asks where Taro rides his bicycle. [Ninereeds] answers: Taro fährt das Fahrrad vor das Haus. "
         "Wo? → dative (vor dem). Wohin? → accusative (vor das). "
         "Allow: Fahrrad (bicycle, neut), fährt (rides, from fahren)."),
        ("072_vor_steht_vs_stellt.md",
         "vor steht vs. stellt — steht vor dem Tisch (static) vs. stellt vor den Tisch (endpoint)",
         ("vor dem Tisch", "vor den Tisch", "stellt"),
         "Verb-focused contrast for vor + masc: steht (stands, static) vs. stellt (places, endpoint). "
         "Pair 1 (STATIC): Der Stuhl steht vor dem Tisch. "
         "Pair 2 (ENDPOINT): Emma stellt den Stuhl vor den Tisch. "
         "Pair 3 (STATIC): Der Becher steht vor dem Tisch. "
         "Pair 4 (ENDPOINT): Taro stellt den Becher vor den Tisch. "
         "German: vor dem (static masc) vs. vor den (endpoint masc). "
         "JP: static テーブルの前にある, endpoint テーブルの前に置く. ZH: static 在桌子前面, endpoint 放到桌子前面."),
        ("073_vor_ist_vs_geht.md",
         "vor ist vs. geht — ist vor dem Haus (static) vs. geht vor das Haus (endpoint)",
         ("vor dem Haus", "vor das Haus", "geht"),
         "Verb-focused contrast for vor + neut: ist (is, static) vs. geht (goes, endpoint). "
         "Pair 1 (STATIC): Emma ist vor dem Haus. "
         "Pair 2 (ENDPOINT): Emma geht vor das Haus. "
         "Pair 3 (STATIC): Taro ist vor dem Haus. "
         "Pair 4 (ENDPOINT): Taro geht vor das Haus. "
         "German: vor dem (static neut) vs. vor das (endpoint neut). "
         "JP: static 家の前にいる, endpoint 家の前に行く. ZH: static 在房子前面, endpoint 走到房子前面."),
        ("074_vor_full_contrast.md",
         "vor full contrast — mixed static/endpoint across masc, fem, neut targets",
         ("vor dem", "vor den"),
         "Mixed contrast file for vor. Cover all three genders, alternating static and endpoint. "
         "Pair 1 (STATIC masc): Der Stuhl steht vor dem Tisch. "
         "Pair 2 (ENDPOINT masc): Emma stellt den Stuhl vor den Tisch. "
         "Pair 3 (STATIC fem): Das Buch liegt vor der Bank. "
         "Pair 4 (ENDPOINT neut): Gran geht vor das Haus. "
         "Mix dative (dem/der/dem) and accusative (den/die/das) across the 4 pairs. "
         "JP: alternate の前にある (static) and の前に置く/行く (endpoint). ZH: alternate 在〜前面 (static) and 放到/走到〜前面 (endpoint)."),
        ("075_vor_verb_contrast.md",
         "vor verb contrast — different verbs: steht/liegt/stellt/legt across fem and neut targets",
         ("vor der Bank", "vor das Bett"),
         "Verb variety contrast for vor. "
         "Pair 1 (STATIC fem): Das Buch liegt vor der Bank. "
         "Pair 2 (ENDPOINT fem): Taro legt das Buch vor die Bank. "
         "Pair 3 (STATIC neut): Der Becher steht vor dem Bett. "
         "Pair 4 (ENDPOINT neut): Emma stellt den Becher vor das Bett. "
         "German: vor der/dem for static, vor die/das for endpoint. "
         "JP: static の前にある, endpoint の前に置く. ZH: static 在〜前面, endpoint 放到〜前面."),
        # ── hinter (behind) ───────────────────────────────────────────────
        ("076_hinter_contrast_masc.md",
         "hinter contrast masc — hinter dem Stuhl (static) vs. hinter den Stuhl (endpoint)",
         ("hinter dem Stuhl", "hinter den Stuhl"),
         "Direct contrast file for hinter + masc. "
         "Pair 1 (STATIC): Der Becher steht hinter dem Stuhl. — the cup stands behind the chair. "
         "Pair 2 (ENDPOINT): Emma stellt den Becher hinter den Stuhl. — Emma places the cup behind the chair. "
         "Pair 3 (STATIC): Das Buch liegt hinter dem Stuhl. — the book lies behind the chair. "
         "Pair 4 (ENDPOINT): Taro legt das Buch hinter den Stuhl. — Taro lays the book behind the chair. "
         "German: dative hinter dem (masc), accusative hinter den (masc). "
         "JP: static 椅子の後ろにある, endpoint 椅子の後ろに置く. "
         "ZH: static 在椅子後面, endpoint 放到椅子後面."),
        ("077_hinter_contrast_fem.md",
         "hinter contrast fem — hinter der Bank (static) vs. hinter die Bank (endpoint)",
         ("hinter der Bank", "hinter die Bank"),
         "Direct contrast file for hinter + fem. "
         "Pair 1 (STATIC): Das Buch liegt hinter der Bank. — the book lies behind the bench. "
         "Pair 2 (ENDPOINT): Emma legt das Buch hinter die Bank. — Emma lays the book behind the bench. "
         "Pair 3 (STATIC): Der Becher steht hinter der Bank. — the cup stands behind the bench. "
         "Pair 4 (ENDPOINT): Gran stellt den Becher hinter die Bank. — Gran places the cup behind the bench. "
         "German: dative hinter der (fem), accusative hinter die (fem). "
         "JP: static ベンチの後ろにある, endpoint ベンチの後ろに置く. "
         "ZH: static 在長椅後面, endpoint 放到長椅後面."),
        ("078_hinter_contrast_neut.md",
         "hinter contrast neut — hinter dem Haus (static) vs. hinter das Haus (endpoint)",
         ("hinter dem Haus", "hinter das Haus"),
         "Direct contrast file for hinter + neut. "
         "Pair 1 (STATIC): Das Kind ist hinter dem Haus. — the child is behind the house. "
         "Pair 2 (ENDPOINT): Das Kind geht hinter das Haus. — the child goes behind the house. "
         "Pair 3 (STATIC): Der Hund ist hinter dem Haus. — the dog is behind the house. "
         "Pair 4 (ENDPOINT): Taro bringt den Hund hinter das Haus. — Taro brings the dog behind the house. "
         "German: dative hinter dem (neut), accusative hinter das (neut). "
         "JP: static 家の後ろにいる/ある, endpoint 家の後ろに行く/連れていく. "
         "ZH: static 在房子後面, endpoint 走到/帶到房子後面."),
        ("079_hinter_gender_contrast.md",
         "hinter gender contrast — masc/fem/neut: hinter dem/der/dem (static) vs. hinter den/die/das (endpoint)",
         ("hinter dem", "hinter der", "hinter den", "hinter die"),
         "Four-way gender and case contrast for hinter. "
         "Pair 1 (STATIC masc): Der Becher steht hinter dem Stuhl. (hinter dem — dative masc). "
         "Pair 2 (ENDPOINT masc): Emma stellt den Becher hinter den Stuhl. (hinter den — accusative masc). "
         "Pair 3 (STATIC fem): Das Buch liegt hinter der Bank. (hinter der — dative fem). "
         "Pair 4 (ENDPOINT fem): Taro legt das Buch hinter die Bank. (hinter die — accusative fem). "
         "JP: static の後ろにある, endpoint の後ろに置く. ZH: static 在〜後面, endpoint 放到〜後面. "
         "Make article change (dem→den, der→die) the visual anchor of each pair."),
        ("080_hinter_contrast_masc_b.md",
         "hinter contrast masc b — hinter dem Tisch (static) vs. hinter den Tisch (endpoint)",
         ("hinter dem Tisch", "hinter den Tisch"),
         "Direct contrast file with a second masc target. "
         "Pair 1 (STATIC): Die Flasche steht hinter dem Tisch. — the bottle stands behind the table. "
         "Pair 2 (ENDPOINT): Gran stellt die Flasche hinter den Tisch. — Gran places the bottle behind the table. "
         "Pair 3 (STATIC): Das Glas steht hinter dem Tisch. — the glass stands behind the table. "
         "Pair 4 (ENDPOINT): Emma stellt das Glas hinter den Tisch. — Emma places the glass behind the table. "
         "German: dative hinter dem (masc), accusative hinter den (masc). "
         "JP: static テーブルの後ろにある, endpoint テーブルの後ろに置く. ZH: static 在桌子後面, endpoint 放到桌子後面. "
         "Allow: Glas (glass, neut)."),
        ("081_hinter_contrast_neut_b.md",
         "hinter contrast neut b — hinter dem Bett (static) vs. hinter das Bett (endpoint)",
         ("hinter dem Bett", "hinter das Bett"),
         "Direct contrast file with a second neut target. "
         "Pair 1 (STATIC): Das Kissen liegt hinter dem Bett. — the pillow lies behind the bed. "
         "Pair 2 (ENDPOINT): Emma legt das Kissen hinter das Bett. — Emma lays the pillow behind the bed. "
         "Pair 3 (STATIC): Der Becher steht hinter dem Bett. — the cup stands behind the bed. "
         "Pair 4 (ENDPOINT): Taro stellt den Becher hinter das Bett. — Taro places the cup behind the bed. "
         "German: dative hinter dem (neut), accusative hinter das (neut). "
         "JP: static ベッドの後ろにある, endpoint ベッドの後ろに置く. ZH: static 在床後面, endpoint 放到床後面. "
         "Allow: Kissen (pillow, neut)."),
        ("082_hinter_question_masc.md",
         "hinter question contrast masc — Wo? (dative) vs. Wohin? (accusative) for Tisch",
         ("hinter dem Tisch", "hinter den Tisch"),
         "Question-driven contrast file for hinter + masc. "
         "Pair 1 (Wo? — STATIC): [user] asks where the bottle is. [Ninereeds] answers: Die Flasche steht hinter dem Tisch. "
         "Pair 2 (Wohin? — ENDPOINT): [user] asks where Gran puts the bottle. [Ninereeds] answers: Gran stellt die Flasche hinter den Tisch. "
         "Pair 3 (Wo? — STATIC): [user] asks where the bag is. [Ninereeds] answers: Die Tasche liegt hinter dem Tisch. "
         "Pair 4 (Wohin? — ENDPOINT): [user] asks where Taro puts the bag. [Ninereeds] answers: Taro legt die Tasche hinter den Tisch. "
         "Wo? → dative (hinter dem). Wohin? → accusative (hinter den). "
         "Allow: Tasche (bag, fem)."),
        ("083_hinter_question_fem.md",
         "hinter question contrast fem — Wo? (dative) vs. Wohin? (accusative) for Bank",
         ("hinter der Bank", "hinter die Bank"),
         "Question-driven contrast file for hinter + fem. "
         "Pair 1 (Wo? — STATIC): [user] asks where the book is. [Ninereeds] answers: Das Buch liegt hinter der Bank. "
         "Pair 2 (Wohin? — ENDPOINT): [user] asks where Emma lays the book. [Ninereeds] answers: Emma legt das Buch hinter die Bank. "
         "Pair 3 (Wo? — STATIC): [user] asks where the cup is. [Ninereeds] answers: Der Becher steht hinter der Bank. "
         "Pair 4 (Wohin? — ENDPOINT): [user] asks where Taro puts the cup. [Ninereeds] answers: Taro stellt den Becher hinter die Bank. "
         "Wo? → dative (hinter der). Wohin? → accusative (hinter die)."),
        ("084_hinter_question_neut.md",
         "hinter question contrast neut — Wo? (dative) vs. Wohin? (accusative) for Haus",
         ("hinter dem Haus", "hinter das Haus"),
         "Question-driven contrast file for hinter + neut. "
         "Pair 1 (Wo? — STATIC): [user] asks where the child is. [Ninereeds] answers: Das Kind ist hinter dem Haus. "
         "Pair 2 (Wohin? — ENDPOINT): [user] asks where the child goes. [Ninereeds] answers: Das Kind geht hinter das Haus. "
         "Pair 3 (Wo? — STATIC): [user] asks where the dog is. [Ninereeds] answers: Der Hund ist hinter dem Haus. "
         "Pair 4 (Wohin? — ENDPOINT): [user] asks where Emma brings the dog. [Ninereeds] answers: Emma bringt den Hund hinter das Haus. "
         "Wo? → dative (hinter dem). Wohin? → accusative (hinter das)."),
        ("085_hinter_steht_vs_stellt.md",
         "hinter steht vs. stellt — steht hinter dem Stuhl (static) vs. stellt hinter den Stuhl (endpoint)",
         ("hinter dem Stuhl", "hinter den Stuhl", "stellt"),
         "Verb-focused contrast for hinter + masc: steht (stands, static) vs. stellt (places, endpoint). "
         "Pair 1 (STATIC): Die Flasche steht hinter dem Stuhl. "
         "Pair 2 (ENDPOINT): Gran stellt die Flasche hinter den Stuhl. "
         "Pair 3 (STATIC): Der Becher steht hinter dem Stuhl. "
         "Pair 4 (ENDPOINT): Emma stellt den Becher hinter den Stuhl. "
         "German: hinter dem (static masc) vs. hinter den (endpoint masc). "
         "JP: static 椅子の後ろにある, endpoint 椅子の後ろに置く. ZH: static 在椅子後面, endpoint 放到椅子後面."),
        ("086_hinter_ist_vs_geht.md",
         "hinter ist vs. geht — ist hinter dem Haus (static) vs. geht hinter das Haus (endpoint)",
         ("hinter dem Haus", "hinter das Haus", "geht"),
         "Verb-focused contrast for hinter + neut: ist (is, static) vs. geht (goes, endpoint). "
         "Pair 1 (STATIC): Emma ist hinter dem Haus. "
         "Pair 2 (ENDPOINT): Emma geht hinter das Haus. "
         "Pair 3 (STATIC): Taro ist hinter dem Haus. "
         "Pair 4 (ENDPOINT): Taro geht hinter das Haus. "
         "German: hinter dem (static neut) vs. hinter das (endpoint neut). "
         "JP: static 家の後ろにいる, endpoint 家の後ろに行く. ZH: static 在房子後面, endpoint 走到房子後面."),
        ("087_hinter_full_contrast.md",
         "hinter full contrast — mixed static/endpoint across masc, fem, neut targets",
         ("hinter dem", "hinter den"),
         "Mixed contrast file for hinter. Cover all three genders, alternating static and endpoint. "
         "Pair 1 (STATIC masc): Der Becher steht hinter dem Stuhl. "
         "Pair 2 (ENDPOINT masc): Emma stellt den Becher hinter den Stuhl. "
         "Pair 3 (STATIC fem): Das Buch liegt hinter der Bank. "
         "Pair 4 (ENDPOINT neut): Gran geht hinter das Haus. "
         "Mix dative (dem/der/dem) and accusative (den/die/das) across the 4 pairs. "
         "JP: alternate の後ろにある (static) and の後ろに置く/行く (endpoint). ZH: alternate 在〜後面 (static) and 放到/走到〜後面 (endpoint)."),
        ("088_hinter_verb_contrast.md",
         "hinter verb contrast — steht/liegt/stellt/legt across masc and fem targets",
         ("hinter der Bank", "hinter den Tisch"),
         "Verb variety contrast for hinter. "
         "Pair 1 (STATIC fem): Das Buch liegt hinter der Bank. "
         "Pair 2 (ENDPOINT fem): Taro legt das Buch hinter die Bank. "
         "Pair 3 (STATIC masc): Der Becher steht hinter dem Tisch. "
         "Pair 4 (ENDPOINT masc): Emma stellt den Becher hinter den Tisch. "
         "German: hinter der/dem for static, hinter die/den for endpoint. "
         "JP: static の後ろにある, endpoint の後ろに置く. ZH: static 在〜後面, endpoint 放到〜後面."),
        # ── zwischen (between) ────────────────────────────────────────────
        ("089_zwischen_contrast_masc.md",
         "zwischen contrast masc — zwischen dem Stuhl und dem Tisch (static) vs. zwischen den Stuhl und den Tisch (endpoint)",
         ("zwischen dem Stuhl", "zwischen den Stuhl"),
         "Direct contrast file for zwischen + masc pair. "
         "Pair 1 (STATIC): Der Becher steht zwischen dem Stuhl und dem Tisch. — the cup stands between the chair and the table. "
         "Pair 2 (ENDPOINT): Emma stellt den Becher zwischen den Stuhl und den Tisch. — Emma places the cup between the chair and the table. "
         "Pair 3 (STATIC): Das Buch liegt zwischen dem Stuhl und dem Tisch. — the book lies between the chair and the table. "
         "Pair 4 (ENDPOINT): Taro legt das Buch zwischen den Stuhl und den Tisch. — Taro lays the book between the chair and the table. "
         "German: dative zwischen dem (masc pair), accusative zwischen den (masc pair). "
         "JP: static 椅子と机の間にある, endpoint 椅子と机の間に置く. "
         "ZH: static 在椅子和桌子之間, endpoint 放到椅子和桌子之間."),
        ("090_zwischen_contrast_mixed.md",
         "zwischen contrast mixed — zwischen der Bank und dem Stuhl (static) vs. zwischen die Bank und den Stuhl (endpoint)",
         ("zwischen der Bank", "zwischen die Bank"),
         "Direct contrast file for zwischen + mixed gender pair. "
         "Pair 1 (STATIC): Der Becher steht zwischen der Bank und dem Stuhl. — static: between bench (fem) and chair (masc). "
         "Pair 2 (ENDPOINT): Emma stellt den Becher zwischen die Bank und den Stuhl. — endpoint: between bench (fem) and chair (masc). "
         "Pair 3 (STATIC): Das Buch liegt zwischen der Bank und dem Stuhl. "
         "Pair 4 (ENDPOINT): Gran legt das Buch zwischen die Bank und den Stuhl. "
         "German: dative zwischen der (fem) / dem (masc), accusative zwischen die (fem) / den (masc). "
         "JP: static ベンチと椅子の間にある, endpoint ベンチと椅子の間に置く. "
         "ZH: static 在長椅和椅子之間, endpoint 放到長椅和椅子之間."),
        ("091_zwischen_contrast_neut.md",
         "zwischen contrast neut — zwischen dem Bett und dem Tisch (static) vs. zwischen das Bett und den Tisch (endpoint)",
         ("zwischen dem Bett", "zwischen das Bett"),
         "Direct contrast file for zwischen + neut/masc pair. "
         "Pair 1 (STATIC): Das Buch liegt zwischen dem Bett und dem Tisch. — static: between bed (neut) and table (masc). "
         "Pair 2 (ENDPOINT): Emma legt das Buch zwischen das Bett und den Tisch. — endpoint: between bed (neut) and table (masc). "
         "Pair 3 (STATIC): Der Becher steht zwischen dem Bett und dem Tisch. "
         "Pair 4 (ENDPOINT): Taro stellt den Becher zwischen das Bett und den Tisch. "
         "German: dative zwischen dem (neut/masc), accusative zwischen das (neut) / den (masc). "
         "JP: static ベッドと机の間にある, endpoint ベッドと机の間に置く. "
         "ZH: static 在床和桌子之間, endpoint 放到床和桌子之間."),
        ("092_zwischen_gender_contrast.md",
         "zwischen gender contrast — dative pair vs. accusative pair across masc, fem, neut",
         ("zwischen dem", "zwischen der", "zwischen den", "zwischen die"),
         "Four-way gender and case contrast for zwischen. "
         "Pair 1 (STATIC masc+masc): Der Becher steht zwischen dem Stuhl und dem Tisch. (zwischen dem — dative masc). "
         "Pair 2 (ENDPOINT masc+masc): Emma stellt den Becher zwischen den Stuhl und den Tisch. (zwischen den — accusative masc). "
         "Pair 3 (STATIC fem+masc): Das Buch liegt zwischen der Bank und dem Stuhl. (zwischen der — dative fem). "
         "Pair 4 (ENDPOINT fem+masc): Taro legt das Buch zwischen die Bank und den Stuhl. (zwischen die — accusative fem). "
         "JP: static 〜の間にある, endpoint 〜の間に置く. ZH: static 在〜之間, endpoint 放到〜之間. "
         "Make article change (dem→den, der→die) the visual anchor of each pair."),
        ("093_zwischen_contrast_b.md",
         "zwischen contrast b — between Tisch and Bank: mixed neut/fem static vs. endpoint",
         ("zwischen dem Tisch", "zwischen den Tisch"),
         "Direct contrast file with a different target pair. "
         "Pair 1 (STATIC): Der Becher steht zwischen dem Tisch und der Bank. "
         "Pair 2 (ENDPOINT): Emma stellt den Becher zwischen den Tisch und die Bank. "
         "Pair 3 (STATIC): Das Glas steht zwischen dem Tisch und der Bank. "
         "Pair 4 (ENDPOINT): Gran stellt das Glas zwischen den Tisch und die Bank. "
         "German: dative zwischen dem/der, accusative zwischen den/die. "
         "JP: static 机と長椅子の間にある, endpoint 机と長椅子の間に置く. "
         "ZH: static 在桌子和長椅之間, endpoint 放到桌子和長椅之間. Allow: Glas (glass, neut)."),
        ("094_zwischen_question.md",
         "zwischen question contrast — Wo? (dative) vs. Wohin? (accusative) for Stuhl+Tisch pair",
         ("zwischen dem Stuhl", "zwischen den Stuhl"),
         "Question-driven contrast file for zwischen + masc pair. "
         "Pair 1 (Wo? — STATIC): [user] asks where the cup is. [Ninereeds] answers: Der Becher steht zwischen dem Stuhl und dem Tisch. "
         "Pair 2 (Wohin? — ENDPOINT): [user] asks where Emma puts the cup. [Ninereeds] answers: Emma stellt den Becher zwischen den Stuhl und den Tisch. "
         "Pair 3 (Wo? — STATIC): [user] asks where the apple is. [Ninereeds] answers: Der Apfel liegt zwischen dem Stuhl und dem Tisch. "
         "Pair 4 (Wohin? — ENDPOINT): [user] asks where Taro puts the apple. [Ninereeds] answers: Taro legt den Apfel zwischen den Stuhl und den Tisch. "
         "Wo? → dative (zwischen dem). Wohin? → accusative (zwischen den)."),
        ("095_zwischen_steht_vs_stellt.md",
         "zwischen steht vs. stellt — steht zwischen dem/der (static) vs. stellt zwischen den/die (endpoint)",
         ("zwischen dem Stuhl", "zwischen den Stuhl", "stellt"),
         "Verb-focused contrast for zwischen: steht (stands, static) vs. stellt (places, endpoint). "
         "Pair 1 (STATIC): Die Flasche steht zwischen dem Stuhl und der Bank. "
         "Pair 2 (ENDPOINT): Gran stellt die Flasche zwischen den Stuhl und die Bank. "
         "Pair 3 (STATIC): Der Becher steht zwischen dem Tisch und dem Stuhl. "
         "Pair 4 (ENDPOINT): Emma stellt den Becher zwischen den Tisch und den Stuhl. "
         "German: zwischen dem/der for static, zwischen den/die for endpoint. "
         "JP: static 〜の間にある, endpoint 〜の間に置く. ZH: static 在〜之間, endpoint 放到〜之間."),
        ("096_zwischen_liegt_vs_legt.md",
         "zwischen liegt vs. legt — liegt zwischen dem/der (static) vs. legt zwischen den/die (endpoint)",
         ("zwischen der Bank", "zwischen die Bank", "legt"),
         "Verb-focused contrast for zwischen: liegt (lies, static) vs. legt (lays, endpoint). "
         "Pair 1 (STATIC): Das Buch liegt zwischen der Bank und dem Stuhl. "
         "Pair 2 (ENDPOINT): Taro legt das Buch zwischen die Bank und den Stuhl. "
         "Pair 3 (STATIC): Der Apfel liegt zwischen der Bank und dem Tisch. "
         "Pair 4 (ENDPOINT): Emma legt den Apfel zwischen die Bank und den Tisch. "
         "German: zwischen der/dem for static, zwischen die/den for endpoint. "
         "JP: static 〜の間にある, endpoint 〜の間に置く. ZH: static 在〜之間, endpoint 放到〜之間."),
        ("097_zwischen_ist_vs_geht.md",
         "zwischen ist vs. geht — ist zwischen dem/dem (static) vs. geht zwischen den/den (endpoint)",
         ("zwischen dem Stuhl", "zwischen den Stuhl", "geht"),
         "Verb-focused contrast for zwischen: ist (is, static) vs. geht (goes, endpoint). "
         "Pair 1 (STATIC): Emma ist zwischen dem Stuhl und dem Tisch. "
         "Pair 2 (ENDPOINT): Emma geht zwischen den Stuhl und den Tisch. "
         "Pair 3 (STATIC): Das Kind ist zwischen dem Stuhl und dem Tisch. "
         "Pair 4 (ENDPOINT): Das Kind geht zwischen den Stuhl und den Tisch. "
         "German: zwischen dem for static, zwischen den for endpoint. "
         "JP: static 椅子と机の間にいる, endpoint 椅子と机の間に行く. ZH: static 在椅子和桌子之間, endpoint 走到椅子和桌子之間."),
        ("098_zwischen_full_contrast_a.md",
         "zwischen full contrast a — mixed static/endpoint pairs with varied genders and objects",
         ("zwischen dem", "zwischen den"),
         "Mixed contrast file for zwischen. Cover masc, fem, and mixed gender pairs. "
         "Pair 1 (STATIC masc): Der Becher steht zwischen dem Stuhl und dem Tisch. "
         "Pair 2 (ENDPOINT masc): Emma stellt den Becher zwischen den Stuhl und den Tisch. "
         "Pair 3 (STATIC fem+masc): Das Buch liegt zwischen der Bank und dem Stuhl. "
         "Pair 4 (ENDPOINT fem+masc): Taro legt das Buch zwischen die Bank und den Stuhl. "
         "Mix dative (dem/der) and accusative (den/die) across the 4 pairs. "
         "JP: alternate の間にある (static) and の間に置く (endpoint). ZH: alternate 在〜之間 (static) and 放到〜之間 (endpoint)."),
        ("099_zwischen_full_contrast_b.md",
         "zwischen full contrast b — second mixed set: neut+masc pairs",
         ("zwischen dem Bett", "zwischen das Bett"),
         "Mixed contrast file for zwischen. Focus on neut+masc combinations. "
         "Pair 1 (STATIC neut+masc): Der Apfel liegt zwischen dem Bett und dem Tisch. "
         "Pair 2 (ENDPOINT neut+masc): Emma legt den Apfel zwischen das Bett und den Tisch. "
         "Pair 3 (STATIC neut+masc): Das Glas steht zwischen dem Bett und dem Stuhl. "
         "Pair 4 (ENDPOINT neut+masc): Gran stellt das Glas zwischen das Bett und den Stuhl. "
         "German: dative zwischen dem (neut/masc), accusative zwischen das (neut) / den (masc). "
         "JP: alternate の間にある (static) and の間に置く (endpoint). ZH: alternate 在〜之間 (static) and 放到〜之間 (endpoint). "
         "Allow: Glas (glass, neut)."),
        ("100_zwischen_verb_contrast.md",
         "zwischen verb contrast — different verbs and agents: liegt/steht/legt/stellt across pairs",
         ("zwischen dem Tisch", "zwischen den Tisch"),
         "Verb variety contrast for zwischen. "
         "Pair 1 (STATIC masc): Der Becher steht zwischen dem Tisch und dem Stuhl. "
         "Pair 2 (ENDPOINT masc): Emma stellt den Becher zwischen den Tisch und den Stuhl. "
         "Pair 3 (STATIC fem+masc): Das Buch liegt zwischen der Bank und dem Tisch. "
         "Pair 4 (ENDPOINT fem+masc): Taro legt das Buch zwischen die Bank und den Tisch. "
         "German: dem/der for static, den/die for endpoint. "
         "JP: static 〜の間にある, endpoint 〜の間に置く. ZH: static 在〜之間, endpoint 放到〜之間."),
    ]

    shared_suffix = (
        " CONTRAST FILE: every file must contain BOTH static dative and movement accusative. "
        "The dative article (dem/der) marks static location; the accusative article (den/die/das) marks movement endpoint. "
        "Alternate between STATIC pairs (dative, static verb: ist/liegt/steht/hängt/sitzt) and "
        "ENDPOINT pairs (accusative, placement/movement verb: stellt/legt/geht/hängt/bringt). "
        "Do not write a file that uses only dative or only accusative — both must appear. "
        "JP: static pairs use にある/にいる/かかっている; endpoint pairs use に置く/に行く/に入る. "
        "ZH: static pairs use 在〜 (location); endpoint pairs use 放到〜/走到〜/帶到〜. "
        "Traditional Chinese throughout. No romaji. Keep vocabulary simple and concrete."
    )

    return [
        FileSpec(
            path=f"07_place_target_contrast/{filename}",
            focus=focus,
            required_terms=required,
            notes=notes + shared_suffix,
        )
        for filename, focus, required, notes in rows
    ]


def make_source_path_destination_specs() -> list[FileSpec]:
    """Specs for `08_source_path_destination`: source, path, and destination movement chains."""
    shared_suffix = (
        " SOURCE-PATH-DESTINATION file. "
        "Core German prepositions: aus (from inside, always dative: aus dem/der), "
        "von (from surface/person, always dative: vom/von dem/von der), "
        "durch (through, accusative: durch den/die/das), "
        "in+accusative (into: in den/die/das), auf+accusative (onto: auf den/die/das), "
        "nach (toward city/direction, no article), zu (toward person/place, dative: zum/zur). "
        "Each response pair must show the movement chain clearly — where from, and where to. "
        "JP: から for source, を通って for path, に/へ/まで for destination. "
        "ZH: 從〜到〜 pattern; Traditional Chinese throughout. "
        "Keep vocabulary concrete. Cast: Emma, Taro, Gran, Biscuit. "
        "Locations: Küche, Garten, Zimmer, Haus, Tisch, Bank, Baum, Boden."
    )

    rows: list[tuple[str, str, tuple[str, ...], str]] = [
        # Group 1: aus-source (from inside a room/space) 001-015
        ("001_aus_kueche_a.md",
         "Emma comes aus der Küche",
         ("aus der Küche",),
         "Focus: source movement aus der Küche. "
         "Emma exits the kitchen. All 4 pairs use aus der Küche as the source. "
         "Vary the agents and destinations."),
        ("002_aus_kueche_b.md",
         "Taro comes aus der Küche",
         ("aus der Küche",),
         "Focus: source movement aus der Küche. "
         "Taro exits the kitchen. All 4 pairs use aus der Küche as the source. "
         "Vary the actions and what they carry."),
        ("003_aus_garten_a.md",
         "aus dem Garten — coming from the garden",
         ("aus dem Garten",),
         "Focus: source movement aus dem Garten. "
         "Agents exit the garden. All 4 pairs use aus dem Garten as the source. "
         "Vary the agents and their actions."),
        ("004_aus_garten_b.md",
         "Biscuit runs aus dem Garten",
         ("aus dem Garten",),
         "Focus: source movement aus dem Garten. "
         "Biscuit or other agents exit the garden. Vary what they carry or where they go next."),
        ("005_aus_zimmer_a.md",
         "aus dem Zimmer — leaving the room",
         ("aus dem Zimmer",),
         "Focus: source movement aus dem Zimmer. "
         "Emma or Taro exits the room. Vary agents across 4 pairs."),
        ("006_aus_zimmer_b.md",
         "Gran comes aus dem Zimmer",
         ("aus dem Zimmer",),
         "Focus: source movement aus dem Zimmer. "
         "Gran exits the room. Vary what they carry and where they go."),
        ("007_aus_haus_a.md",
         "aus dem Haus — leaving the house",
         ("aus dem Haus",),
         "Focus: source movement aus dem Haus. "
         "Emma or Taro exits the house. Vary agents and actions across 4 pairs."),
        ("008_aus_haus_b.md",
         "Biscuit runs aus dem Haus",
         ("aus dem Haus",),
         "Focus: source movement aus dem Haus. "
         "Biscuit exits the house. Vary what follows."),
        ("009_aus_schule_a.md",
         "aus der Schule — leaving school",
         ("aus der Schule",),
         "Focus: source movement aus der Schule. "
         "Children exit school. Vary agents across 4 pairs."),
        ("010_aus_schule_b.md",
         "Taro comes aus der Schule",
         ("aus der Schule",),
         "Focus: source movement aus der Schule. "
         "Taro or other agent exits school carrying something. Vary across 4 pairs."),
        ("011_aus_kueche_taro.md",
         "Taro carries something aus der Küche",
         ("aus der Küche",),
         "Focus: Taro as agent, aus der Küche source. "
         "Taro carries objects out of the kitchen. "
         "Vary the objects (Apfel, Buch, Becher, Ball) across 4 pairs."),
        ("012_aus_garten_gran.md",
         "Gran comes aus dem Garten",
         ("aus dem Garten",),
         "Focus: Gran as agent, aus dem Garten source. "
         "Gran exits the garden. Vary what Gran carries or does next."),
        ("013_aus_zimmer_biscuit.md",
         "Biscuit runs aus dem Zimmer",
         ("aus dem Zimmer",),
         "Focus: Biscuit as agent, aus dem Zimmer source. "
         "Biscuit exits the room. Use animal-appropriate actions."),
        ("014_aus_haus_emma.md",
         "Emma walks aus dem Haus",
         ("aus dem Haus",),
         "Focus: Emma as agent, aus dem Haus source. "
         "Emma exits the house. Vary what she carries or where she goes."),
        ("015_aus_source_review.md",
         "mixed aus sources — review",
         ("aus",),
         "Review file: mix different aus-sources across 4 pairs. "
         "Use aus dem Garten, aus der Küche, aus dem Zimmer, aus dem Haus in different pairs. "
         "Vary agents. Keep German dative form visible after aus."),

        # Group 2: von-source (from surface/person/place) 016-030
        ("016_von_tisch_a.md",
         "Emma takes something vom Tisch",
         ("vom Tisch", "von dem Tisch"),
         "Focus: source movement vom Tisch (= von dem Tisch). "
         "Emma takes an object from the table. Vary the objects across 4 pairs."),
        ("017_von_tisch_b.md",
         "Taro takes something vom Tisch",
         ("vom Tisch", "von dem Tisch"),
         "Focus: source movement vom Tisch. "
         "Taro takes objects from the table. Vary the objects."),
        ("018_von_bank_a.md",
         "Gran picks something von der Bank",
         ("von der Bank",),
         "Focus: source movement von der Bank. "
         "Gran or Emma takes something from the bench. Vary agents and objects."),
        ("019_von_bank_b.md",
         "Biscuit jumps von der Bank",
         ("von der Bank",),
         "Focus: source movement von der Bank. "
         "Biscuit or other agent moves from the bench. "
         "Use animal-appropriate actions for Biscuit."),
        ("020_von_baum_a.md",
         "Emma picks something vom Baum",
         ("vom Baum", "von dem Baum"),
         "Focus: source movement vom Baum (= von dem Baum). "
         "Emma picks an apple from the tree. Vary agents and objects across 4 pairs."),
        ("021_von_baum_b.md",
         "Taro climbs down vom Baum",
         ("vom Baum", "von dem Baum"),
         "Focus: source movement vom Baum. "
         "Taro or Biscuit descends from the tree. Vary agents and actions."),
        ("022_von_boden_a.md",
         "Emma picks something vom Boden",
         ("vom Boden", "von dem Boden"),
         "Focus: source movement vom Boden (= von dem Boden). "
         "Emma picks an object from the floor. Vary objects across 4 pairs."),
        ("023_von_boden_b.md",
         "Taro lifts something vom Boden",
         ("vom Boden", "von dem Boden"),
         "Focus: source movement vom Boden. "
         "Taro lifts objects from the floor. Vary objects."),
        ("024_von_fenster_a.md",
         "Emma looks out vom Fenster / takes something vom Fensterbrett",
         ("vom Fenster", "von dem Fenster"),
         "Focus: source movement or removal from the window area. "
         "Emma or Gran takes something from the windowsill. Vary agents and objects."),
        ("025_von_tisch_taro.md",
         "Taro lifts the cup vom Tisch",
         ("vom Tisch",),
         "Focus: Taro as agent, vom Tisch source. "
         "Taro lifts different objects from the table. Vary the objects."),
        ("026_von_bank_gran.md",
         "Gran takes something von der Bank",
         ("von der Bank",),
         "Focus: Gran as agent, von der Bank source. "
         "Gran takes objects from the bench. Vary objects and actions."),
        ("027_von_baum_biscuit.md",
         "Biscuit jumps vom Baum",
         ("vom Baum",),
         "Focus: Biscuit as agent, vom Baum source. "
         "Biscuit leaps from the tree. Use animal-appropriate verbs."),
        ("028_von_boden_emma.md",
         "Emma picks up something vom Boden",
         ("vom Boden",),
         "Focus: Emma as agent, vom Boden source. "
         "Emma picks up various objects from the floor. Vary the objects."),
        ("029_von_person_a.md",
         "receiving something von Emma / von dem Kind",
         ("von Emma", "von dem Kind"),
         "Focus: von + person as source. "
         "Taro receives something from Emma; Gran receives something from the child. "
         "Use von + dative person phrase. Vary agents and objects."),
        ("030_von_source_review.md",
         "mixed von-sources review",
         ("von",),
         "Review file: mix different von-sources across 4 pairs. "
         "Use vom Tisch, von der Bank, vom Baum, von Emma in different pairs. "
         "Keep German dative form visible after von."),

        # Group 3: aus+in chains (from room/container into room/space) 031-050
        ("031_chain_aus_in_kueche_a.md",
         "Emma goes aus dem Zimmer in die Küche",
         ("aus dem Zimmer", "in die Küche"),
         "Focus: two-step chain aus dem Zimmer → in die Küche. "
         "Emma moves from the room into the kitchen. "
         "German must show dative source (aus dem) and accusative endpoint (in die). "
         "Vary agents across 4 pairs."),
        ("032_chain_aus_in_kueche_b.md",
         "Taro carries something aus dem Zimmer in die Küche",
         ("aus dem Zimmer", "in die Küche"),
         "Focus: two-step chain aus dem Zimmer → in die Küche with carried object. "
         "Taro or Gran carries an object. Vary objects across 4 pairs."),
        ("033_chain_aus_in_garten_a.md",
         "Emma goes aus dem Haus in den Garten",
         ("aus dem Haus", "in den Garten"),
         "Focus: two-step chain aus dem Haus → in den Garten. "
         "Emma moves from house into garden. Vary agents."),
        ("034_chain_aus_in_garten_b.md",
         "Biscuit runs aus dem Haus in den Garten",
         ("aus dem Haus", "in den Garten"),
         "Focus: Biscuit runs aus dem Haus in den Garten. "
         "Use animal-appropriate verbs for Biscuit. Vary agents for other pairs."),
        ("035_chain_aus_in_zimmer_a.md",
         "Gran goes aus der Küche in das Zimmer",
         ("aus der Küche", "in das Zimmer"),
         "Focus: two-step chain aus der Küche → in das Zimmer. "
         "Gran or Taro moves from kitchen into room. Vary agents."),
        ("036_chain_aus_in_zimmer_b.md",
         "Emma carries something aus der Küche in das Zimmer",
         ("aus der Küche", "in das Zimmer"),
         "Focus: Emma carries an object aus der Küche in das Zimmer. "
         "Vary the objects across 4 pairs."),
        ("037_chain_aus_in_haus_a.md",
         "Taro goes aus dem Garten in das Haus",
         ("aus dem Garten", "in das Haus"),
         "Focus: two-step chain aus dem Garten → in das Haus. "
         "Taro or Gran moves from garden into house. Vary agents."),
        ("038_chain_aus_in_haus_b.md",
         "Biscuit runs aus dem Garten in das Haus",
         ("aus dem Garten", "in das Haus"),
         "Focus: Biscuit runs aus dem Garten in das Haus. "
         "Use animal-appropriate verbs. Vary other agents for remaining pairs."),
        ("039_chain_aus_auf_a.md",
         "Emma takes something aus der Küche auf den Tisch",
         ("aus der Küche", "auf den Tisch"),
         "Focus: chain aus der Küche → auf den Tisch. "
         "Emma moves an object from the kitchen onto the table. "
         "German: aus der Küche (dative source) + auf den Tisch (accusative endpoint). "
         "Vary objects across 4 pairs."),
        ("040_chain_aus_auf_b.md",
         "Taro brings something aus dem Garten auf die Bank",
         ("aus dem Garten", "auf die Bank"),
         "Focus: chain aus dem Garten → auf die Bank. "
         "Taro brings an object from garden to bench. Vary agents and objects."),
        ("041_chain_aus_in_emma.md",
         "Emma journeys from room to kitchen — full chain",
         ("aus",  "in die"),
         "Focus: Emma as main agent across all 4 pairs. "
         "Each pair uses a different aus-source and in-destination. "
         "Vary sources (Zimmer/Haus/Garten) and destinations (Küche/Zimmer/Garten)."),
        ("042_chain_aus_in_taro.md",
         "Taro journeys aus → in — full chain",
         ("aus", "in den"),
         "Focus: Taro as main agent across all 4 pairs. "
         "Each pair uses a different aus-source and in-destination. "
         "Vary sources and destinations."),
        ("043_chain_aus_in_gran.md",
         "Gran journeys aus → in — full chain",
         ("aus", "in"),
         "Focus: Gran as main agent across all 4 pairs. "
         "Each pair uses a different aus-source and in-destination."),
        ("044_chain_aus_in_biscuit.md",
         "Biscuit runs aus → in — full chain",
         ("aus", "in"),
         "Focus: Biscuit as main agent across all 4 pairs. "
         "Use animal-appropriate verbs. Vary aus-sources and in-destinations."),
        ("045_chain_aus_in_review.md",
         "mixed aus → in chains review",
         ("aus", "in"),
         "Review file: mix different aus-sources and in-destinations across 4 pairs. "
         "Vary agents and objects. Keep German case forms visible (dative after aus, accusative after in)."),

        # Group 4: von+auf chains (from surface onto surface / to destination) 046-060
        ("046_chain_von_auf_tisch_a.md",
         "Emma moves something vom Tisch auf die Bank",
         ("vom Tisch", "auf die Bank"),
         "Focus: chain vom Tisch → auf die Bank. "
         "Emma takes an object from the table and puts it on the bench. "
         "German: vom Tisch (dative source) + auf die Bank (accusative endpoint). "
         "Vary agents and objects."),
        ("047_chain_von_auf_tisch_b.md",
         "Taro moves something vom Tisch auf den Boden",
         ("vom Tisch", "auf den Boden"),
         "Focus: chain vom Tisch → auf den Boden. "
         "Taro moves objects from table to floor. Vary objects."),
        ("048_chain_von_auf_bank_a.md",
         "Gran moves something von der Bank auf den Tisch",
         ("von der Bank", "auf den Tisch"),
         "Focus: chain von der Bank → auf den Tisch. "
         "Gran moves objects from bench to table. Vary agents and objects."),
        ("049_chain_von_auf_bank_b.md",
         "Emma moves something von der Bank auf den Boden",
         ("von der Bank", "auf den Boden"),
         "Focus: chain von der Bank → auf den Boden. "
         "Emma moves objects from bench to floor. Vary objects."),
        ("050_chain_von_auf_boden_a.md",
         "Taro lifts something vom Boden auf den Tisch",
         ("vom Boden", "auf den Tisch"),
         "Focus: chain vom Boden → auf den Tisch. "
         "Taro lifts objects from the floor onto the table. Vary objects."),
        ("051_chain_von_auf_boden_b.md",
         "Gran lifts something vom Boden auf die Bank",
         ("vom Boden", "auf die Bank"),
         "Focus: chain vom Boden → auf die Bank. "
         "Gran lifts objects from floor to bench. Vary objects."),
        ("052_chain_von_in_a.md",
         "Emma takes something vom Tisch in den Korb",
         ("vom Tisch", "in den Korb"),
         "Focus: chain vom Tisch → in den Korb (into a container). "
         "Emma takes objects from the table and places them into a basket. "
         "German: vom Tisch (dative) + in den Korb (accusative). Vary objects."),
        ("053_chain_von_in_b.md",
         "Taro takes something von der Bank in das Haus",
         ("von der Bank", "in das Haus"),
         "Focus: chain von der Bank → in das Haus. "
         "Taro carries objects from bench into the house. Vary objects."),
        ("054_chain_von_auf_emma.md",
         "Emma moves objects between surfaces — full chain",
         ("vom", "auf"),
         "Focus: Emma as agent, varies both source and destination across 4 pairs. "
         "Use vom Tisch/von der Bank/vom Baum as sources; auf den Tisch/auf die Bank/auf den Boden as destinations."),
        ("055_chain_von_auf_review.md",
         "mixed von → auf chains review",
         ("von", "auf"),
         "Review file: mix von-sources and auf-destinations across 4 pairs. "
         "Vary agents and objects. Keep German dative source and accusative destination visible."),

        # Group 5: nach/zu destination chains 056-070
        ("056_nach_destination_a.md",
         "Emma goes nach Hause",
         ("nach Hause",),
         "Focus: nach Hause as destination. "
         "Emma, Taro, or Gran goes home. Vary agents across 4 pairs. "
         "JP: 家に帰る / 家に行く. ZH: 回家 / 去家裡."),
        ("057_nach_destination_b.md",
         "Taro goes nach draußen",
         ("nach draußen",),
         "Focus: nach draußen as destination. "
         "Agents go outside. Vary agents across 4 pairs. "
         "JP: 外に出る. ZH: 出去."),
        ("058_nach_destination_c.md",
         "Emma goes nach oben / nach unten",
         ("nach oben", "nach unten"),
         "Focus: nach oben (upstairs/up) and nach unten (downstairs/down). "
         "Use both directions across 4 pairs. Vary agents."),
        ("059_nach_destination_d.md",
         "Taro runs nach draußen aus dem Haus",
         ("nach draußen", "aus dem Haus"),
         "Focus: aus dem Haus + nach draußen chain. "
         "Agents exit the house and go outside. Vary agents and verbs."),
        ("060_nach_destination_e.md",
         "Gran goes back nach Hause from the garden",
         ("nach Hause", "aus dem Garten"),
         "Focus: aus dem Garten + nach Hause chain. "
         "Agents leave garden and head home. Vary across 4 pairs."),
        ("061_zu_person_a.md",
         "Emma goes zu dem Kind / zum Kind",
         ("zum Kind", "zu dem Kind"),
         "Focus: zu + person-dative as destination. "
         "Emma goes to the child. Vary agents and destination persons across 4 pairs. "
         "Use visibly marked dative person phrases: dem Kind, dem Mann, der Frau, dem Arzt."),
        ("062_zu_person_b.md",
         "Taro goes zu dem Arzt / zum Arzt",
         ("zum Arzt", "zu dem Arzt"),
         "Focus: zu + person-dative — professional destination. "
         "Taro goes to the doctor or teacher. Vary across 4 pairs."),
        ("063_zu_person_c.md",
         "Gran goes zu dem Mann / zu der Frau",
         ("zu dem Mann", "zu der Frau"),
         "Focus: zu + person-dative — social destination. "
         "Gran or Emma goes to the man or woman. Vary across 4 pairs."),
        ("064_zu_person_d.md",
         "Emma goes zu dem Baum / zur Bank",
         ("zur Bank", "zu dem Baum"),
         "Focus: zu + place-dative as destination (tree, bench). "
         "Vary agents and zu-destinations across 4 pairs."),
        ("065_zu_person_e.md",
         "mixed zu-destinations review",
         ("zu",),
         "Review file: mix zu + person and zu + place destinations across 4 pairs. "
         "Use zum/zur contractions where appropriate. Keep German dative visible."),
        ("066_aus_nach_chain_a.md",
         "Emma goes aus dem Haus nach draußen",
         ("aus dem Haus", "nach draußen"),
         "Focus: aus dem Haus + nach draußen — two-step out. "
         "Vary agents across 4 pairs."),
        ("067_aus_nach_chain_b.md",
         "Taro goes aus dem Zimmer nach oben",
         ("aus dem Zimmer", "nach oben"),
         "Focus: aus dem Zimmer + nach oben chain. "
         "Vary agents across 4 pairs."),
        ("068_aus_zu_chain_a.md",
         "Emma goes aus dem Haus zum Kind",
         ("aus dem Haus", "zum Kind"),
         "Focus: aus dem Haus + zum Kind/zum Mann/zur Frau chain. "
         "Vary person-destinations across 4 pairs."),
        ("069_aus_zu_chain_b.md",
         "Gran goes aus der Küche zur Bank",
         ("aus der Küche", "zur Bank"),
         "Focus: aus der Küche + zur Bank chain. "
         "Vary agents and destinations across 4 pairs."),
        ("070_nach_zu_review.md",
         "mixed nach/zu destination review",
         ("nach", "zu"),
         "Review file: mix nach and zu destinations across 4 pairs. "
         "Vary agents and destinations. Contractions (zum/zur) are fine here."),

        # Group 6: durch path 071-080
        ("071_durch_path_a.md",
         "Emma walks durch den Garten",
         ("durch den Garten",),
         "Focus: durch + accusative as path. "
         "Emma walks through the garden. Vary agents across 4 pairs. "
         "German: durch + accusative article (den/die/das). "
         "JP: を通って / を通り抜けて. ZH: 穿過〜."),
        ("072_durch_path_b.md",
         "Taro runs durch das Haus",
         ("durch das Haus",),
         "Focus: durch das Haus as path. "
         "Taro or Biscuit moves through the house. Vary agents and verbs."),
        ("073_durch_path_c.md",
         "Biscuit runs durch den Garten",
         ("durch den Garten",),
         "Focus: Biscuit as agent, durch den Garten path. "
         "Use animal-appropriate verbs. Vary other agents."),
        ("074_durch_path_d.md",
         "Gran walks durch die Küche",
         ("durch die Küche",),
         "Focus: durch die Küche as path. "
         "Gran or Emma walks through the kitchen. Vary agents."),
        ("075_durch_path_e.md",
         "mixed durch paths — garden/house/kitchen",
         ("durch",),
         "Review file: mix durch den Garten / durch das Haus / durch die Küche across 4 pairs. "
         "Vary agents and verbs. Keep accusative article visible after durch."),
        ("076_durch_in_chain_a.md",
         "Emma goes durch den Garten in das Haus",
         ("durch den Garten", "in das Haus"),
         "Focus: durch den Garten → in das Haus path+endpoint chain. "
         "Emma passes through garden and enters the house. Vary agents."),
        ("077_durch_in_chain_b.md",
         "Taro goes durch das Zimmer in den Garten",
         ("durch das Zimmer", "in den Garten"),
         "Focus: durch das Zimmer → in den Garten chain. "
         "Taro passes through the room and enters the garden. Vary agents."),
        ("078_durch_in_chain_c.md",
         "Biscuit runs durch den Garten in das Haus",
         ("durch den Garten", "in das Haus"),
         "Focus: Biscuit as main agent, durch den Garten → in das Haus chain. "
         "Use animal-appropriate verbs. Vary other agents."),
        ("079_durch_path_biscuit.md",
         "Biscuit runs through multiple spaces",
         ("durch",),
         "Focus: Biscuit as agent, varied durch-paths across 4 pairs. "
         "Biscuit runs through garden, house, room, kitchen. Use animal-appropriate verbs."),
        ("080_durch_path_review.md",
         "mixed durch path review",
         ("durch",),
         "Review file: mix durch paths across 4 pairs, including path+endpoint chains. "
         "Vary agents and endpoints. Keep accusative after durch."),

        # Group 7: full 3-part chains 081-090
        ("081_full_chain_aus_durch_in_a.md",
         "Emma goes aus dem Haus, durch den Garten, in das Zimmer",
         ("aus dem Haus", "durch den Garten", "in das Zimmer"),
         "Focus: full 3-part chain: source (aus, dative) + path (durch, accusative) + endpoint (in, accusative). "
         "Emma exits the house, walks through the garden, and enters the room. "
         "Vary agents across 4 pairs but keep the 3-part structure."),
        ("082_full_chain_aus_durch_in_b.md",
         "Taro goes aus der Küche, durch das Zimmer, in den Garten",
         ("aus der Küche", "durch das Zimmer", "in den Garten"),
         "Focus: full 3-part chain: aus der Küche + durch das Zimmer + in den Garten. "
         "Vary agents across 4 pairs."),
        ("083_full_chain_aus_durch_in_c.md",
         "Biscuit runs aus dem Garten, durch das Haus, in das Zimmer",
         ("aus dem Garten", "durch das Haus", "in das Zimmer"),
         "Focus: full 3-part chain with Biscuit as main agent. "
         "Use animal-appropriate verbs. Vary other agents."),
        ("084_full_chain_von_durch_auf_a.md",
         "Emma takes something vom Tisch, durch die Küche, auf die Bank",
         ("vom Tisch", "durch die Küche", "auf die Bank"),
         "Focus: full 3-part object chain: vom Tisch (source) + durch die Küche (path) + auf die Bank (endpoint). "
         "Emma moves an object. Vary objects across 4 pairs."),
        ("085_full_chain_von_durch_auf_b.md",
         "Taro takes something von der Bank, durch den Garten, auf den Tisch",
         ("von der Bank", "durch den Garten", "auf den Tisch"),
         "Focus: full 3-part object chain: von der Bank + durch den Garten + auf den Tisch. "
         "Vary agents and objects."),
        ("086_full_chain_person_a.md",
         "Emma goes from the kitchen through the garden to the bench — full person chain",
         ("aus der Küche", "durch den Garten", "zur Bank"),
         "Focus: person journey full chain: aus der Küche + durch den Garten + zur Bank. "
         "Vary agents across 4 pairs."),
        ("087_full_chain_person_b.md",
         "Taro goes from the room through the house to the garden — full person chain",
         ("aus dem Zimmer", "durch das Haus", "in den Garten"),
         "Focus: person journey full chain: aus dem Zimmer + durch das Haus + in den Garten. "
         "Vary agents."),
        ("088_full_chain_object_a.md",
         "Taro carries the apple from the table, through the kitchen, to the garden",
         ("vom Tisch", "durch die Küche", "in den Garten"),
         "Focus: object transport full chain: vom Tisch + durch die Küche + in den Garten. "
         "Taro carries an apple. Vary agents and objects."),
        ("089_full_chain_object_b.md",
         "Gran carries something from the bench through the garden to the house",
         ("von der Bank", "durch den Garten", "in das Haus"),
         "Focus: object transport full chain: von der Bank + durch den Garten + in das Haus. "
         "Gran carries an object. Vary agents and objects."),
        ("090_full_chain_review.md",
         "full 3-part chain review — mixed sources, paths, endpoints",
         ("aus", "durch", "in"),
         "Review file: 4 pairs each with a full 3-part chain. "
         "Vary sources (aus/von), paths (durch), and endpoints (in/auf/zu) across pairs. "
         "Keep German case forms clearly visible throughout."),

        # Group 8: person journey chains 091-100
        ("091_journey_emma_a.md",
         "Emma's morning journey — aus dem Haus, durch den Garten, zur Bank",
         ("aus dem Haus", "durch den Garten", "zur Bank"),
         "Focus: narrative journey for Emma. "
         "4 pairs describing Emma's movement through different spaces. "
         "Vary the chain in each pair: different source, path, destination."),
        ("092_journey_emma_b.md",
         "Emma carries objects on a journey — full chain",
         ("aus der Küche", "in den Garten"),
         "Focus: Emma carries objects on her journey. "
         "4 pairs, each showing Emma moving an object through space. "
         "Vary objects and chains."),
        ("093_journey_taro_a.md",
         "Taro's journey — aus dem Zimmer, durch den Garten, in die Küche",
         ("aus dem Zimmer", "in die Küche"),
         "Focus: narrative journey for Taro. "
         "4 pairs describing Taro's movement. Vary chains."),
        ("094_journey_taro_b.md",
         "Taro carries objects across spaces",
         ("vom Tisch", "in den Garten"),
         "Focus: Taro carries objects across different spaces. "
         "4 pairs, each with a different aus/von source and in/auf/zu endpoint."),
        ("095_journey_gran_a.md",
         "Gran's journey — aus der Küche, durch das Zimmer, in den Garten",
         ("aus der Küche", "durch das Zimmer", "in den Garten"),
         "Focus: narrative journey for Gran. "
         "4 pairs describing Gran's movement. Vary chains."),
        ("096_journey_gran_b.md",
         "Gran brings things on a journey",
         ("von der Bank", "in das Haus"),
         "Focus: Gran carries objects. "
         "4 pairs with different source-endpoint chains."),
        ("097_journey_biscuit_a.md",
         "Biscuit runs aus dem Haus, durch den Garten, unter die Bank",
         ("aus dem Haus", "durch den Garten", "unter die Bank"),
         "Focus: Biscuit's running journey. "
         "Use animal-appropriate verbs. "
         "4 pairs describing Biscuit's movement through different spaces."),
        ("098_journey_biscuit_b.md",
         "Biscuit's journey around the garden and house",
         ("aus", "in"),
         "Focus: Biscuit as main agent across all 4 pairs. "
         "Vary Biscuit's aus-sources and in/auf/unter endpoints. "
         "Use animal-appropriate verbs."),
        ("099_journey_mixed.md",
         "mixed cast journey — all agents across 4 pairs",
         ("aus", "in"),
         "Focus: one pair per agent (Emma, Taro, Gran, Biscuit). "
         "Each pair uses a different source-path-endpoint chain. "
         "Vary the chains to cover the full range of aus/von, durch, in/auf/zu."),
        ("100_source_path_review.md",
         "full source-path-destination review — all patterns",
         ("aus", "von", "in"),
         "Final review file: 4 pairs covering the full range of source-path-destination patterns. "
         "Pair 1: aus-source + in-endpoint. "
         "Pair 2: von-source + auf-endpoint. "
         "Pair 3: durch-path + in-endpoint. "
         "Pair 4: full 3-part chain (aus/von + durch + in/auf). "
         "Vary agents and objects. Keep German case forms visible throughout."),
    ]

    return [
        FileSpec(
            path=f"08_source_path_destination/{filename}",
            focus=focus,
            required_terms=required,
            notes=notes + shared_suffix,
        )
        for filename, focus, required, notes in rows
    ]


def make_owner_genitive_specs() -> list[FileSpec]:
    """Specs for `09_owner_genitive`: ownership and attribute possession."""
    shared_suffix = (
        " OWNERSHIP / GENITIVE file. "
        "Core German possession forms: "
        "proper name possessive (Emmas Becher, Taros Ball — add -s to name), "
        "von + dative alternative (der Becher von Emma, der Ball vom Kind), "
        "formal genitive with des (masc/neut: des Tisches, des Hauses, des Kindes), "
        "formal genitive with der (fem: der Küche, der Frau, der Schule). "
        "Wessen? is the genitive question word. "
        "JP: の particle for all possession types. "
        "ZH: 的 particle; Traditional Chinese throughout. "
        "Keep vocabulary concrete — familiar objects, cast members, locations. "
        "Do not introduce abstract ownership concepts."
    )

    rows: list[tuple[str, str, tuple[str, ...], str]] = [
        # Group 1: proper name possessive — Emma 001-010
        ("001_emmas_becher.md",
         "Emmas Becher — Emma's cup",
         ("Emmas Becher",),
         "Focus: Emmas Becher (possessive -s). "
         "4 pairs about Emma's cup — where it is, who has it, what happens to it. "
         "German: Emmas Becher throughout. JP: エマのコップ. ZH: 艾瑪的杯子."),
        ("002_emmas_buch.md",
         "Emmas Buch — Emma's book",
         ("Emmas Buch",),
         "Focus: Emmas Buch (possessive -s). "
         "4 pairs about Emma's book. JP: エマの本. ZH: 艾瑪的書."),
        ("003_emmas_ball.md",
         "Emmas Ball — Emma's ball",
         ("Emmas Ball",),
         "Focus: Emmas Ball (possessive -s). "
         "4 pairs about Emma's ball. JP: エマのボール. ZH: 艾瑪的球."),
        ("004_emmas_korb.md",
         "Emmas Korb — Emma's basket",
         ("Emmas Korb",),
         "Focus: Emmas Korb (possessive -s). "
         "4 pairs about Emma's basket — what is in it, where it is. "
         "JP: エマのかご. ZH: 艾瑪的籃子."),
        ("005_emmas_apfel.md",
         "Emmas Apfel — Emma's apple",
         ("Emmas Apfel",),
         "Focus: Emmas Apfel (possessive -s). "
         "4 pairs — who has Emma's apple, where it is, what happens to it. "
         "JP: エマのリンゴ. ZH: 艾瑪的蘋果."),
        ("006_emmas_stuhl.md",
         "Emmas Stuhl — Emma's chair",
         ("Emmas Stuhl",),
         "Focus: Emmas Stuhl (possessive -s). "
         "4 pairs about Emma's chair — where it stands, who sits on it. "
         "JP: エマの椅子. ZH: 艾瑪的椅子."),
        ("007_emmas_hund.md",
         "Emmas Hund — Emma's dog (Biscuit)",
         ("Emmas Hund",),
         "Focus: Emmas Hund (possessive -s). "
         "Biscuit is Emma's dog. 4 pairs about Biscuit as Emma's dog. "
         "JP: エマの犬. ZH: 艾瑪的狗."),
        ("008_emmas_mixed.md",
         "mixed Emmas possessives",
         ("Emmas",),
         "Focus: mix of Emma's possessives across 4 pairs. "
         "Use Emmas Becher, Emmas Buch, Emmas Ball, Emmas Apfel in different pairs."),
        ("009_emmas_review.md",
         "Emmas things — where are they?",
         ("Emmas",),
         "Review: 4 pairs asking and answering where Emma's things are. "
         "Use Wessen? question and name-possessive answer."),
        ("010_emmas_questions.md",
         "Wessen Becher ist das? — Emmas Becher.",
         ("Wessen", "Emmas"),
         "Focus: Wessen? question targeting Emma's objects. "
         "4 pairs: Wessen [Becher/Buch/Ball/Korb] ist das? — Emmas [object]. "
         "JP: これは誰の〜ですか？ ZH: 這是誰的〜？"),

        # Group 1 continued: proper name possessive — Taro 011-017
        ("011_taros_ball.md",
         "Taros Ball — Taro's ball",
         ("Taros Ball",),
         "Focus: Taros Ball (possessive -s). "
         "4 pairs about Taro's ball. JP: タロウのボール. ZH: 太郎的球."),
        ("012_taros_buch.md",
         "Taros Buch — Taro's book",
         ("Taros Buch",),
         "Focus: Taros Buch (possessive -s). "
         "4 pairs about Taro's book. JP: タロウの本. ZH: 太郎的書."),
        ("013_taros_becher.md",
         "Taros Becher — Taro's cup",
         ("Taros Becher",),
         "Focus: Taros Becher (possessive -s). "
         "4 pairs about Taro's cup. JP: タロウのコップ. ZH: 太郎的杯子."),
        ("014_taros_apfel.md",
         "Taros Apfel — Taro's apple",
         ("Taros Apfel",),
         "Focus: Taros Apfel (possessive -s). "
         "4 pairs about Taro's apple. JP: タロウのリンゴ. ZH: 太郎的蘋果."),
        ("015_taros_korb.md",
         "Taros Korb — Taro's basket",
         ("Taros Korb",),
         "Focus: Taros Korb (possessive -s). "
         "4 pairs about Taro's basket. JP: タロウのかご. ZH: 太郎的籃子."),
        ("016_taros_mixed.md",
         "mixed Taros possessives",
         ("Taros",),
         "Focus: mix of Taro's possessives across 4 pairs. "
         "Use Taros Becher, Taros Buch, Taros Ball, Taros Apfel in different pairs."),
        ("017_taros_questions.md",
         "Wessen Ball ist das? — Taros Ball.",
         ("Wessen", "Taros"),
         "Focus: Wessen? question targeting Taro's objects. "
         "4 pairs: Wessen [Ball/Buch/Becher/Apfel] ist das? — Taros [object]."),

        # Group 1 continued: Gran 018-022
        ("018_grans_tisch.md",
         "Grans Tisch — Gran's table",
         ("Grans Tisch",),
         "Focus: Grans Tisch (possessive -s). "
         "4 pairs about Gran's table. JP: グランのテーブル. ZH: 格蘭的桌子."),
        ("019_grans_becher.md",
         "Grans Becher — Gran's cup",
         ("Grans Becher",),
         "Focus: Grans Becher (possessive -s). "
         "4 pairs about Gran's cup. JP: グランのコップ. ZH: 格蘭的杯子."),
        ("020_grans_korb.md",
         "Grans Korb — Gran's basket",
         ("Grans Korb",),
         "Focus: Grans Korb (possessive -s). "
         "4 pairs about Gran's basket. JP: グランのかご. ZH: 格蘭的籃子."),
        ("021_grans_mixed.md",
         "mixed Grans possessives",
         ("Grans",),
         "Focus: mix of Gran's possessives across 4 pairs. "
         "Use Grans Tisch, Grans Becher, Grans Korb, Grans Stuhl in different pairs."),
        ("022_grans_questions.md",
         "Wessen Tisch ist das? — Grans Tisch.",
         ("Wessen", "Grans"),
         "Focus: Wessen? question targeting Gran's objects. "
         "4 pairs: Wessen [Tisch/Becher/Korb/Ball] ist das? — Grans [object]."),

        # Group 1 continued: Biscuit 023-025
        ("023_biscuits_ball.md",
         "Biscuits Ball — Biscuit's ball",
         ("Biscuits Ball",),
         "Focus: Biscuits Ball (possessive -s). "
         "Biscuit is a dog — 4 pairs about Biscuit's ball. "
         "JP: ビスケットのボール. ZH: 餅乾的球."),
        ("024_biscuits_becher.md",
         "Biscuits Korb — Biscuit's basket",
         ("Biscuits Korb",),
         "Focus: Biscuits Korb (possessive -s). "
         "4 pairs about Biscuit's basket. JP: ビスケットのかご. ZH: 餅乾的籃子."),
        ("025_biscuits_mixed.md",
         "mixed Biscuits possessives",
         ("Biscuits",),
         "Focus: mix of Biscuit's possessives. "
         "4 pairs about different things belonging to Biscuit."),

        # Mixed name possessives 026-030
        ("026_possessive_review_a.md",
         "whose cup? — mixed name possessives",
         ("Emmas", "Taros"),
         "Review: 4 pairs contrasting Emmas and Taros possessives. "
         "Each pair asks Wessen? and answers with one of their things."),
        ("027_possessive_review_b.md",
         "whose book? — mixed name possessives",
         ("Emmas", "Grans"),
         "Review: 4 pairs contrasting Emmas and Grans possessives. "
         "Each pair asks Wessen? and answers with one of their things."),
        ("028_possessive_contrast_a.md",
         "Emma vs Taro — whose object is where?",
         ("Emmas", "Taros"),
         "Focus: contrast Emma's and Taro's objects in the same file. "
         "Pair 1: Emmas Becher ist auf dem Tisch. Pair 2: Taros Ball liegt auf der Bank. Etc."),
        ("029_possessive_contrast_b.md",
         "Gran vs Biscuit — whose object is where?",
         ("Grans", "Biscuits"),
         "Focus: contrast Gran's and Biscuit's objects. "
         "Vary across 4 pairs."),
        ("030_possessive_mixed.md",
         "mixed name possessives — full review",
         ("Emmas", "Taros", "Grans"),
         "Review: 4 pairs using different name possessives (Emma, Taro, Gran, Biscuit). "
         "One pair per person. Ask Wessen? and answer with the possessive."),

        # Group 2: von + dative alternative 031-050
        ("031_von_emma_a.md",
         "der Becher von Emma — the cup belonging to Emma",
         ("von Emma",),
         "Focus: von + proper name as possession alternative to Emmas. "
         "4 pairs using der Becher von Emma, das Buch von Emma, etc. "
         "JP: エマの〜. ZH: 艾瑪的〜."),
        ("032_von_emma_b.md",
         "Wessen Becher? — der Becher von Emma",
         ("von Emma",),
         "Focus: Wessen? answered with von + name. "
         "4 pairs: Wessen ist das? — Das ist von Emma. Vary objects."),
        ("033_von_taro_a.md",
         "der Ball von Taro — von + proper name",
         ("von Taro",),
         "Focus: von Taro as possession. "
         "4 pairs. JP: タロウの〜. ZH: 太郎的〜."),
        ("034_von_taro_b.md",
         "Wessen Ball? — der Ball von Taro",
         ("von Taro",),
         "Focus: Wessen? answered with von Taro. 4 pairs, vary objects."),
        ("035_von_gran_a.md",
         "der Tisch von Gran — von + proper name",
         ("von Gran",),
         "Focus: von Gran as possession. 4 pairs. ZH: 格蘭的〜."),
        ("036_von_gran_b.md",
         "Wessen Tisch? — der Tisch von Gran",
         ("von Gran",),
         "Focus: Wessen? answered with von Gran. 4 pairs."),
        ("037_von_dem_jungen_a.md",
         "der Ball von dem Jungen — possession by the boy",
         ("von dem Jungen",),
         "Focus: von dem Jungen (= vom Jungen) as possession. "
         "4 pairs about the boy's ball. JP: 男の子の〜. ZH: 那個男孩的〜."),
        ("038_von_dem_jungen_b.md",
         "Wessen Ball? — der Ball von dem Jungen",
         ("von dem Jungen",),
         "Focus: Wessen? answered with von dem Jungen. 4 pairs."),
        ("039_von_dem_mann_a.md",
         "das Buch von dem Mann — possession by the man",
         ("von dem Mann",),
         "Focus: von dem Mann as possession. 4 pairs. JP: あの男の人の〜. ZH: 那個男人的〜."),
        ("040_von_dem_mann_b.md",
         "Wessen Buch? — das Buch von dem Mann",
         ("von dem Mann",),
         "Focus: Wessen? answered with von dem Mann. 4 pairs."),
        ("041_von_der_frau_a.md",
         "der Becher von der Frau — possession by the woman",
         ("von der Frau",),
         "Focus: von der Frau as possession. 4 pairs. JP: あの女の人の〜. ZH: 那個女人的〜."),
        ("042_von_der_frau_b.md",
         "Wessen Becher? — der Becher von der Frau",
         ("von der Frau",),
         "Focus: Wessen? answered with von der Frau. 4 pairs."),
        ("043_von_dem_kind_a.md",
         "der Apfel von dem Kind — possession by the child",
         ("von dem Kind",),
         "Focus: von dem Kind as possession. 4 pairs. JP: その子の〜. ZH: 那個孩子的〜."),
        ("044_von_dem_kind_b.md",
         "Wessen Apfel? — der Apfel von dem Kind",
         ("von dem Kind",),
         "Focus: Wessen? answered with von dem Kind. 4 pairs."),
        ("045_von_dem_arzt_a.md",
         "das Buch von dem Arzt — possession by the doctor",
         ("von dem Arzt",),
         "Focus: von dem Arzt as possession. 4 pairs. JP: お医者さんの〜. ZH: 醫生的〜."),
        ("046_von_dem_arzt_b.md",
         "Wessen Buch? — das Buch von dem Arzt",
         ("von dem Arzt",),
         "Focus: Wessen? answered with von dem Arzt. 4 pairs."),
        ("047_von_dem_lehrer_a.md",
         "der Becher von dem Lehrer — possession by the teacher",
         ("von dem Lehrer",),
         "Focus: von dem Lehrer as possession. 4 pairs. JP: 先生の〜. ZH: 老師的〜."),
        ("048_von_dem_lehrer_b.md",
         "Wessen Becher? — der Becher von dem Lehrer",
         ("von dem Lehrer",),
         "Focus: Wessen? answered with von dem Lehrer. 4 pairs."),
        ("049_von_review_a.md",
         "mixed von-possession review — named persons",
         ("von Emma", "von Taro"),
         "Review: 4 pairs mixing von + name possessives (Emma, Taro, Gran). "
         "Each pair uses a different owner and object."),
        ("050_von_review_b.md",
         "mixed von-possession review — role nouns",
         ("von dem Kind", "von dem Mann"),
         "Review: 4 pairs mixing von + role noun possessives. "
         "Use von dem Kind, von dem Mann, von der Frau, von dem Arzt."),

        # Group 3: formal genitive with des (masc/neut) 051-065
        ("051_des_hauses_a.md",
         "die Tür des Hauses — the door of the house",
         ("des Hauses",),
         "Focus: formal genitive des Hauses. "
         "4 pairs about parts of the house: die Tür des Hauses, das Dach des Hauses, etc. "
         "JP: 家の〜. ZH: 房子的〜."),
        ("052_des_hauses_b.md",
         "das Fenster des Hauses — the window of the house",
         ("des Hauses",),
         "Focus: formal genitive des Hauses. "
         "4 pairs about different parts or things of the house. Vary the nouns."),
        ("053_des_hauses_c.md",
         "Wessen Tür? — die Tür des Hauses",
         ("des Hauses", "Wessen"),
         "Focus: Wessen? answered with des Hauses genitive. "
         "4 pairs varying the part of the house."),
        ("054_des_baumes_a.md",
         "der Ast des Baumes — the branch of the tree",
         ("des Baumes",),
         "Focus: formal genitive des Baumes. "
         "4 pairs about parts of the tree: der Ast, die Wurzel, der Apfel des Baumes. "
         "JP: 木の〜. ZH: 樹的〜."),
        ("055_des_baumes_b.md",
         "Wessen Ast? — der Ast des Baumes",
         ("des Baumes", "Wessen"),
         "Focus: Wessen? answered with des Baumes. 4 pairs."),
        ("056_des_kindes_a.md",
         "der Ball des Kindes — the ball of the child",
         ("des Kindes",),
         "Focus: formal genitive des Kindes. "
         "4 pairs: der Ball des Kindes, das Buch des Kindes, der Becher des Kindes, der Apfel des Kindes. "
         "JP: 子供の〜. ZH: 孩子的〜."),
        ("057_des_kindes_b.md",
         "Wessen Ball? — der Ball des Kindes",
         ("des Kindes", "Wessen"),
         "Focus: Wessen? answered with des Kindes. 4 pairs."),
        ("058_des_mannes_a.md",
         "der Hut des Mannes — the hat of the man",
         ("des Mannes",),
         "Focus: formal genitive des Mannes. "
         "4 pairs about the man's possessions: Hut, Buch, Becher, Ball. "
         "JP: 男の人の〜. ZH: 那個男人的〜."),
        ("059_des_mannes_b.md",
         "Wessen Hut? — der Hut des Mannes",
         ("des Mannes", "Wessen"),
         "Focus: Wessen? answered with des Mannes. 4 pairs."),
        ("060_des_hundes_a.md",
         "der Ball des Hundes — the ball of the dog (Biscuit)",
         ("des Hundes",),
         "Focus: formal genitive des Hundes. "
         "4 pairs about the dog's things: Ball, Korb, Becher, Apfel. "
         "JP: 犬の〜. ZH: 狗的〜."),
        ("061_des_hundes_b.md",
         "Wessen Ball? — der Ball des Hundes",
         ("des Hundes", "Wessen"),
         "Focus: Wessen? answered with des Hundes. 4 pairs."),
        ("062_des_gartens_a.md",
         "der Baum des Gartens — the tree of the garden",
         ("des Gartens",),
         "Focus: formal genitive des Gartens. "
         "4 pairs: der Baum des Gartens, die Bank des Gartens, der Weg des Gartens. "
         "JP: 庭の〜. ZH: 花園的〜."),
        ("063_des_gartens_b.md",
         "Wessen Baum? — der Baum des Gartens",
         ("des Gartens", "Wessen"),
         "Focus: Wessen? answered with des Gartens. 4 pairs."),
        ("064_des_genitive_review_a.md",
         "mixed des-genitive review — masc/neut nouns",
         ("des",),
         "Review: 4 pairs mixing des-genitive forms. "
         "Use des Hauses, des Baumes, des Kindes, des Mannes in different pairs."),
        ("065_des_genitive_review_b.md",
         "Wessen? answered with des-genitive — mixed review",
         ("des", "Wessen"),
         "Review: 4 Wessen? pairs, each answered with a different des-genitive. "
         "Vary the possessor nouns."),

        # Group 4: formal genitive with der (fem) 066-075
        ("066_der_frau_a.md",
         "der Becher der Frau — the cup of the woman",
         ("der Frau",),
         "Focus: formal genitive der Frau (feminine genitive). "
         "4 pairs about the woman's things: Becher, Buch, Ball, Korb. "
         "JP: 女の人の〜. ZH: 那個女人的〜."),
        ("067_der_frau_b.md",
         "Wessen Becher? — der Becher der Frau",
         ("der Frau", "Wessen"),
         "Focus: Wessen? answered with der Frau (genitive). 4 pairs."),
        ("068_der_frau_c.md",
         "mixed der-Frau genitive",
         ("der Frau",),
         "Focus: der Frau genitive in varied sentence patterns. "
         "4 pairs — describe where the woman's things are."),
        ("069_der_schule_a.md",
         "die Tür der Schule — the door of the school",
         ("der Schule",),
         "Focus: formal genitive der Schule (feminine). "
         "4 pairs about parts of the school. JP: 学校の〜. ZH: 學校的〜."),
        ("070_der_schule_b.md",
         "Wessen Tür? — die Tür der Schule",
         ("der Schule", "Wessen"),
         "Focus: Wessen? answered with der Schule. 4 pairs."),
        ("071_der_kueche_a.md",
         "der Tisch der Küche — the table of the kitchen",
         ("der Küche",),
         "Focus: formal genitive der Küche (feminine). "
         "4 pairs about things in or belonging to the kitchen. JP: 台所の〜. ZH: 廚房的〜."),
        ("072_der_kueche_b.md",
         "Wessen Tisch? — der Tisch der Küche",
         ("der Küche", "Wessen"),
         "Focus: Wessen? answered with der Küche. 4 pairs."),
        ("073_der_genitive_review_a.md",
         "mixed der-genitive review — fem nouns",
         ("der",),
         "Review: 4 pairs mixing der-genitive forms (feminine). "
         "Use der Frau, der Schule, der Küche in different pairs."),
        ("074_der_genitive_review_b.md",
         "Wessen? answered with der-genitive — mixed review",
         ("der", "Wessen"),
         "Review: 4 Wessen? pairs answered with different der-genitive (feminine) forms."),
        ("075_des_der_genitive_contrast.md",
         "des vs der genitive contrast — masc/neut vs fem",
         ("des", "der"),
         "Focus: contrast des-genitive (masc/neut) and der-genitive (fem) in the same file. "
         "Pair 1: des Hauses. Pair 2: der Küche. Pair 3: des Kindes. Pair 4: der Frau. "
         "Make the gender distinction visible."),

        # Group 5: Wessen questions 076-085
        ("076_wessen_becher_a.md",
         "Wessen Becher ist das? — mixed answers",
         ("Wessen Becher",),
         "Focus: Wessen Becher? across 4 pairs. "
         "Each pair uses a different owner (Emmas / Taros / von dem Kind / des Mannes)."),
        ("077_wessen_becher_b.md",
         "Whose cup is on the table? — Wessen Becher liegt auf dem Tisch?",
         ("Wessen Becher", "auf dem Tisch"),
         "Focus: Wessen Becher? with location context. "
         "4 pairs asking about the cup's location and ownership together."),
        ("078_wessen_ball_a.md",
         "Wessen Ball ist das? — mixed answers",
         ("Wessen Ball",),
         "Focus: Wessen Ball? across 4 pairs. "
         "Each pair uses a different owner."),
        ("079_wessen_ball_b.md",
         "Whose ball is under the bench? — location + ownership",
         ("Wessen Ball", "unter der Bank"),
         "Focus: Wessen Ball? with location context. "
         "4 pairs combining ownership question with location."),
        ("080_wessen_buch_a.md",
         "Wessen Buch ist das? — mixed answers",
         ("Wessen Buch",),
         "Focus: Wessen Buch? across 4 pairs. "
         "Each pair uses a different owner."),
        ("081_wessen_buch_b.md",
         "Whose book is on the table? — Wessen Buch liegt auf dem Tisch?",
         ("Wessen Buch", "auf dem Tisch"),
         "Focus: Wessen Buch? with location context. 4 pairs."),
        ("082_wessen_apfel_a.md",
         "Wessen Apfel ist das? — mixed answers",
         ("Wessen Apfel",),
         "Focus: Wessen Apfel? across 4 pairs. "
         "Each pair uses a different owner."),
        ("083_wessen_apfel_b.md",
         "Whose apple is in the basket? — Wessen Apfel liegt im Korb?",
         ("Wessen Apfel",),
         "Focus: Wessen Apfel? with location context. 4 pairs."),
        ("084_wessen_review_a.md",
         "Wessen? review — mixed objects and owners",
         ("Wessen",),
         "Review: 4 Wessen? pairs with different objects (Becher/Ball/Buch/Apfel) "
         "and different owner types (name-possessive / von+person / des+noun)."),
        ("085_wessen_review_b.md",
         "Wessen? review — with location",
         ("Wessen",),
         "Review: 4 Wessen? pairs each combining ownership question with a location. "
         "Vary objects, owners, and locations."),

        # Group 6: mixed contrast 086-100
        ("086_contrast_name_vs_von_a.md",
         "Emmas Becher vs der Becher von Emma — same thing, two forms",
         ("Emmas Becher", "von Emma"),
         "Focus: contrast name-possessive and von-alternative for the same ownership. "
         "Pair 1: Emmas Becher ist auf dem Tisch. "
         "Pair 2: Der Becher von Emma ist auf dem Tisch. "
         "Make clear both express the same meaning. Vary objects across 4 pairs."),
        ("087_contrast_name_vs_von_b.md",
         "Taros Ball vs der Ball von Taro — same thing, two forms",
         ("Taros Ball", "von Taro"),
         "Focus: contrast Taros Ball and der Ball von Taro. "
         "4 pairs showing both forms for the same ownership. Vary objects."),
        ("088_contrast_name_vs_des_a.md",
         "Emmas Becher vs der Becher des Kindes — name vs formal genitive",
         ("Emmas", "des Kindes"),
         "Focus: contrast name-possessive (Emmas) and formal genitive (des Kindes). "
         "2 pairs with Emmas, 2 pairs with des Kindes."),
        ("089_contrast_name_vs_des_b.md",
         "Grans Tisch vs der Tisch des Hauses — name vs genitive",
         ("Grans", "des Hauses"),
         "Focus: contrast Grans Tisch and der Tisch des Hauses. "
         "2 pairs with each form."),
        ("090_contrast_von_vs_des_a.md",
         "der Becher von dem Kind vs der Becher des Kindes — same thing, two forms",
         ("von dem Kind", "des Kindes"),
         "Focus: contrast von + dative and formal genitive for the same ownership. "
         "Both express 'the child's cup.' 2 pairs each."),
        ("091_contrast_von_vs_des_b.md",
         "der Hut von dem Mann vs der Hut des Mannes — two forms",
         ("von dem Mann", "des Mannes"),
         "Focus: contrast von dem Mann and des Mannes. "
         "Both express 'the man's hat.' 2 pairs each."),
        ("092_mixed_review_a.md",
         "mixed possession forms — name, von, des, der",
         ("Emmas", "von", "des"),
         "Review: 4 pairs each using a different possession form. "
         "Pair 1: name-possessive. Pair 2: von+name. Pair 3: des-genitive. Pair 4: der-genitive."),
        ("093_mixed_review_b.md",
         "Wessen? — answered with all three forms",
         ("Wessen", "Emmas", "von", "des"),
         "Review: 4 Wessen? pairs, each answered with a different possession form. "
         "Vary the objects and owners."),
        ("094_mixed_review_c.md",
         "ownership + location — all possession forms",
         ("Emmas", "auf dem"),
         "Review: 4 pairs combining ownership with a static location. "
         "Each pair uses a different possession form and preposition."),
        ("095_mixed_review_d.md",
         "ownership + receiver — giving someone's thing",
         ("Emmas", "dem Kind"),
         "Review: 4 pairs combining ownership with receiver dative. "
         "Emma gives Taro's apple to the child, etc."),
        ("096_genitive_stories_a.md",
         "short narrative with ownership — Emma and Taro",
         ("Emmas", "Taros"),
         "Story review: short narrative 4 pairs involving Emma's and Taro's possessions. "
         "Each pair advances a simple story: finding, giving, losing, or placing an object."),
        ("097_genitive_stories_b.md",
         "short narrative with ownership — Gran and Biscuit",
         ("Grans", "Biscuits"),
         "Story review: 4 pairs involving Gran's and Biscuit's possessions. "
         "Simple narrative arc."),
        ("098_genitive_stories_c.md",
         "short narrative — formal genitive in context",
         ("des", "der"),
         "Story review: 4 pairs using formal genitive (des/der) in a narrative context. "
         "E.g. the tree's apples fall, the house's door opens, the child's ball rolls."),
        ("099_genitive_stories_d.md",
         "Wessen? story — who owns what in a short narrative",
         ("Wessen",),
         "Story review: 4 pairs where ownership is established narratively. "
         "Each pair uses Wessen? or an equivalent question to identify the owner."),
        ("100_genitive_final_review.md",
         "final genitive review — all possession forms, all contexts",
         ("Emmas", "von", "des"),
         "Final review: 4 pairs covering the full range of German possession forms. "
         "Pair 1: name-possessive (Emmas). "
         "Pair 2: von + dative (von dem Kind). "
         "Pair 3: des-genitive (des Hauses). "
         "Pair 4: der-genitive (der Küche). "
         "Each pair uses Wessen? or a location to give context. "
         "JP: の throughout. ZH: 的 throughout. Traditional Chinese."),
    ]

    return [
        FileSpec(
            path=f"09_owner_genitive/{filename}",
            focus=focus,
            required_terms=required,
            notes=notes + shared_suffix,
        )
        for filename, focus, required, notes in rows
    ]


def make_review_stories_specs() -> list[FileSpec]:
    """Specs for `10_review_stories`: grounded reinforcement stories."""
    shared_suffix = (
        " REVIEW STORY file. "
        "Reinforce earlier grammar clusters through short concrete narrative pairs. "
        "Draw on any combination of: "
        "static dative location (auf dem Tisch, in der Küche, unter der Bank — Wo?), "
        "movement endpoint (auf den Tisch, in die Küche, unter die Bank — Wohin?), "
        "receiver dative (dem Kind geben, dem Mann zeigen, der Frau bringen), "
        "direct object accusative (den Apfel nehmen, das Buch lesen, die Tür öffnen), "
        "source movement (aus der Küche, vom Tisch), "
        "possession (Emmas Becher, von dem Kind, des Hauses). "
        "Do NOT introduce new grammar targets — reinforce only. "
        "Keep vocabulary concrete and cast familiar: Emma, Taro, Gran, Biscuit. "
        "Locations: Tisch, Bank, Küche, Garten, Zimmer, Haus, Baum, Boden. "
        "JP and ZH should follow naturally. Traditional Chinese throughout. No romaji."
    )

    rows: list[tuple[str, str, tuple[str, ...], str]] = [
        # Group 1: static location review (Wo?) 001-020
        ("001_static_auf_a.md",
         "static location review — auf dem Tisch, auf der Bank",
         ("auf dem Tisch",),
         "Review: 4 pairs about objects in static location on the table or bench. "
         "German: auf dem Tisch / auf der Bank (dative). "
         "JP: テーブルの上にある/ベンチの上にある. ZH: 在桌子上/在長凳上."),
        ("002_static_auf_b.md",
         "static location review — auf dem Boden, auf dem Baum",
         ("auf dem Boden",),
         "Review: 4 pairs about objects resting on the floor or tree. "
         "German: auf dem Boden / auf dem Baum (dative)."),
        ("003_static_in_a.md",
         "static location review — in der Küche, in dem Zimmer",
         ("in der Küche",),
         "Review: 4 pairs about people or objects located in the kitchen or room. "
         "German: in der Küche / in dem Zimmer (dative). "
         "JP: 台所にいる/部屋にいる. ZH: 在廚房/在房間."),
        ("004_static_in_b.md",
         "static location review — in dem Garten, in dem Haus",
         ("in dem Garten",),
         "Review: 4 pairs about people or objects in the garden or house. "
         "German: in dem Garten / in dem Haus (dative)."),
        ("005_static_ueber_a.md",
         "static location review — über dem Tisch, über der Bank",
         ("über dem Tisch",),
         "Review: 4 pairs about things hanging or positioned above the table or bench. "
         "German: über dem Tisch / über der Bank (dative). Use hangs/liegt."),
        ("006_static_ueber_b.md",
         "static location review — über dem Baum, über dem Boden",
         ("über dem Baum",),
         "Review: 4 pairs about things above the tree or floor. "
         "German: über dem Baum / über dem Boden (dative)."),
        ("007_static_unter_a.md",
         "static location review — unter dem Tisch, unter der Bank",
         ("unter dem Tisch",),
         "Review: 4 pairs about objects or Biscuit under the table or bench. "
         "German: unter dem Tisch / unter der Bank (dative)."),
        ("008_static_unter_b.md",
         "static location review — unter dem Baum, unter dem Boden",
         ("unter dem Baum",),
         "Review: 4 pairs about objects under the tree or floor. "
         "German: unter dem Baum / unter dem Boden (dative)."),
        ("009_static_neben_a.md",
         "static location review — neben dem Tisch, neben der Bank",
         ("neben dem Tisch",),
         "Review: 4 pairs about people or objects beside the table or bench. "
         "German: neben dem Tisch / neben der Bank (dative)."),
        ("010_static_neben_b.md",
         "static location review — neben dem Baum, neben dem Haus",
         ("neben dem Baum",),
         "Review: 4 pairs about people or objects beside the tree or house. "
         "German: neben dem Baum / neben dem Haus (dative)."),
        ("011_static_vor_a.md",
         "static location review — vor dem Tisch, vor der Tür",
         ("vor dem Tisch",),
         "Review: 4 pairs about people or objects in front of the table or door. "
         "German: vor dem Tisch / vor der Tür (dative)."),
        ("012_static_vor_b.md",
         "static location review — vor dem Haus, vor dem Baum",
         ("vor dem Haus",),
         "Review: 4 pairs about people or objects in front of the house or tree."),
        ("013_static_hinter_a.md",
         "static location review — hinter dem Tisch, hinter der Bank",
         ("hinter dem Tisch",),
         "Review: 4 pairs about people or objects behind the table or bench. "
         "German: hinter dem Tisch / hinter der Bank (dative)."),
        ("014_static_hinter_b.md",
         "static location review — hinter dem Haus, hinter dem Baum",
         ("hinter dem Baum",),
         "Review: 4 pairs about people or objects behind the house or tree."),
        ("015_static_zwischen_a.md",
         "static location review — zwischen dem Tisch und der Bank",
         ("zwischen dem Tisch", "und der Bank"),
         "Review: 4 pairs about objects between the table and bench. "
         "Core sentence: Der Ball ist zwischen dem Tisch und der Bank. "
         "German: zwischen dem Tisch und der Bank (dative for both). "
         "Keep zwischen dem Tisch und der Bank visible in at least one German line. "
         "JP: テーブルとベンチの間にある. ZH: 在桌子和長椅之間."),
        ("016_static_zwischen_b.md",
         "static location review — zwischen dem Baum und dem Haus",
         ("zwischen dem Baum", "und dem Haus"),
         "Review: 4 pairs about objects between the tree and house. "
         "Core sentence: Die Katze ist zwischen dem Baum und dem Haus. "
         "German: zwischen dem Baum und dem Haus (dative for both). "
         "Keep zwischen dem Baum und dem Haus visible in at least one German line. "
         "JP: 木と家の間にある. ZH: 在樹和房子之間."),
        ("017_static_multi_a.md",
         "multi-preposition static location review",
         ("auf dem", "in dem"),
         "Review: 4 pairs each using a different static location preposition. "
         "Pair 1: auf dem. Pair 2: in dem. Pair 3: unter dem. Pair 4: neben dem. "
         "Keep German dative form visible in every pair."),
        ("018_static_multi_b.md",
         "multi-preposition static location review — set 2",
         ("vor dem", "hinter dem"),
         "Review: 4 pairs each using a different static preposition. "
         "Pair 1: vor dem. Pair 2: hinter dem. Pair 3: über dem. Pair 4: zwischen dem und dem."),
        ("019_static_multi_c.md",
         "Wo? question review — static location",
         ("Wo", "auf dem"),
         "Review: 4 Wo? pairs asking where things are. "
         "Each pair uses a different static preposition. "
         "JP: どこ？. ZH: 在哪裡？"),
        ("020_static_review.md",
         "full static location review — all 8 prepositions",
         ("auf dem", "in dem"),
         "Final static review: 4 pairs covering different two-way prepositions in dative. "
         "Vary agents, objects, and prepositions. No movement verbs."),

        # Group 2: movement endpoint review (Wohin?) 021-040
        ("021_endpoint_auf_a.md",
         "movement endpoint review — auf den Tisch, auf die Bank",
         ("auf den Tisch",),
         "Review: 4 pairs about placing objects onto the table or bench. "
         "German: auf den Tisch / auf die Bank (accusative). "
         "JP: テーブルの上に置く. ZH: 放到桌子上."),
        ("022_endpoint_auf_b.md",
         "movement endpoint review — auf den Boden, auf den Baum",
         ("auf den Boden",),
         "Review: 4 pairs about moving objects onto the floor or tree. "
         "German: auf den Boden / auf den Baum (accusative)."),
        ("023_endpoint_in_a.md",
         "movement endpoint review — in die Küche, in das Zimmer",
         ("in die Küche",),
         "Review: 4 pairs about moving into the kitchen or room. "
         "German: in die Küche / in das Zimmer (accusative)."),
        ("024_endpoint_in_b.md",
         "movement endpoint review — in den Garten, in das Haus",
         ("in den Garten",),
         "Review: 4 pairs about moving into the garden or house. "
         "German: in den Garten / in das Haus (accusative)."),
        ("025_endpoint_ueber_a.md",
         "movement endpoint review — über den Tisch, über die Bank",
         ("über den Tisch",),
         "Review: 4 pairs about hanging or moving things above the table or bench. "
         "German: über den Tisch / über die Bank (accusative)."),
        ("026_endpoint_ueber_b.md",
         "movement endpoint review — über den Baum, über den Boden",
         ("über den Baum",),
         "Review: 4 pairs about moving things above the tree or floor."),
        ("027_endpoint_unter_a.md",
         "movement endpoint review — unter den Tisch, unter die Bank",
         ("unter den Tisch",),
         "Review: 4 pairs about moving objects or Biscuit under the table or bench. "
         "German: unter den Tisch / unter die Bank (accusative)."),
        ("028_endpoint_unter_b.md",
         "movement endpoint review — unter den Baum, unter das Bett",
         ("unter den Baum",),
         "Review: 4 pairs about moving under the tree or bed."),
        ("029_endpoint_neben_a.md",
         "movement endpoint review — neben den Tisch, neben die Bank",
         ("neben den Tisch",),
         "Review: 4 pairs about placing objects beside the table or bench. "
         "German: neben den Tisch / neben die Bank (accusative)."),
        ("030_endpoint_neben_b.md",
         "movement endpoint review — neben den Baum, neben das Haus",
         ("neben den Baum",),
         "Review: 4 pairs about moving beside the tree or house."),
        ("031_endpoint_vor_a.md",
         "movement endpoint review — vor den Tisch, vor die Tür",
         ("vor den Tisch",),
         "Review: 4 pairs about placing objects in front of the table or door. "
         "German: vor den Tisch / vor die Tür (accusative)."),
        ("032_endpoint_vor_b.md",
         "movement endpoint review — vor das Haus, vor den Baum",
         ("vor das Haus",),
         "Review: 4 pairs about moving in front of the house or tree."),
        ("033_endpoint_hinter_a.md",
         "movement endpoint review — hinter den Tisch, hinter die Bank",
         ("hinter den Tisch",),
         "Review: 4 pairs about placing objects behind the table or bench. "
         "German: hinter den Tisch / hinter die Bank (accusative)."),
        ("034_endpoint_hinter_b.md",
         "movement endpoint review — hinter das Haus, hinter den Baum",
         ("hinter das Haus",),
         "Review: 4 pairs about moving behind the house or tree."),
        ("035_endpoint_zwischen_a.md",
         "movement endpoint review — zwischen den Tisch und die Bank",
         ("zwischen den Tisch", "zwischen die Bank"),
         "Review: 4 pairs about placing objects between the table and bench. "
         "German: zwischen den Tisch und die Bank (accusative). "
         "JP: テーブルとベンチの間に置く."),
        ("036_endpoint_zwischen_b.md",
         "movement endpoint review — zwischen den Baum und das Haus",
         ("zwischen den Baum", "und das Haus"),
         "Review: 4 pairs about placing objects between the tree and house. "
         "Core sentence: Emma legt den Ball zwischen den Baum und das Haus. "
         "German: zwischen den Baum und das Haus (accusative for both). "
         "Keep zwischen den Baum und das Haus visible in at least one German line. "
         "JP: 木と家の間に置く. ZH: 放在樹和房子之間."),
        ("037_endpoint_multi_a.md",
         "multi-preposition endpoint review",
         ("auf den", "in die"),
         "Review: 4 pairs each using a different endpoint preposition. "
         "Pair 1: auf den. Pair 2: in die. Pair 3: unter den. Pair 4: neben den."),
        ("038_endpoint_multi_b.md",
         "multi-preposition endpoint review — set 2",
         ("vor den", "hinter das"),
         "Review: 4 pairs each using a different endpoint preposition. "
         "Pair 1: vor den. Pair 2: hinter das. Pair 3: über die. Pair 4: zwischen den und die."),
        ("039_endpoint_multi_c.md",
         "Wohin? question review — endpoint",
         ("Wohin", "auf den"),
         "Review: 4 Wohin? pairs asking where things go. "
         "Each pair uses a different endpoint preposition. "
         "JP: どこへ？/ どこに？. ZH: 到哪裡？"),
        ("040_endpoint_review.md",
         "full endpoint review — all 8 prepositions, accusative",
         ("auf den", "in die"),
         "Final endpoint review: 4 pairs covering different two-way prepositions in accusative. "
         "Vary agents, objects, and prepositions. Use movement/placement verbs."),

        # Group 3: receiver dative review 041-060
        ("041_receiver_give_a.md",
         "receiver review — Emma gibt dem Kind den Apfel",
         ("dem Kind", "den Apfel"),
         "Review: 4 pairs with geben as the verb. "
         "Emma gives various objects to various dative receivers. "
         "Keep receiver dative visibly marked (dem Kind, dem Mann, der Frau, dem Arzt)."),
        ("042_receiver_give_b.md",
         "receiver review — Taro gibt dem Mann das Buch",
         ("dem Mann", "das Buch"),
         "Review: 4 pairs with geben. "
         "Taro gives objects to various receivers. Vary objects and receivers."),
        ("043_receiver_give_c.md",
         "receiver review — Gran gibt der Frau den Becher",
         ("der Frau", "den Becher"),
         "Review: 4 pairs with geben. "
         "Gran gives objects to various receivers. Vary objects and receivers."),
        ("044_receiver_give_d.md",
         "receiver review — mixed givers and receivers",
         ("dem Kind", "dem Arzt"),
         "Review: 4 give-pairs with mixed agents, receivers, and objects. "
         "Vary givers (Emma/Taro/Gran), receivers, and objects across all 4 pairs."),
        ("045_receiver_show_a.md",
         "receiver review — zeigen: Emma zeigt dem Kind das Buch",
         ("dem Kind", "das Buch"),
         "Review: 4 pairs with zeigen. "
         "Agents show objects to receivers. Vary across pairs."),
        ("046_receiver_show_b.md",
         "receiver review — zeigen: Taro zeigt dem Arzt den Ball",
         ("dem Arzt", "den Ball"),
         "Review: 4 pairs with zeigen. Vary receivers and objects."),
        ("047_receiver_bring_a.md",
         "receiver review — bringen: Emma bringt dem Mann den Apfel",
         ("dem Mann", "den Apfel"),
         "Review: 4 pairs with bringen. "
         "Agents bring objects to receivers. Vary across pairs."),
        ("048_receiver_bring_b.md",
         "receiver review — bringen: Gran bringt der Frau den Becher",
         ("der Frau", "den Becher"),
         "Review: 4 pairs with bringen. Vary agents, receivers, and objects."),
        ("049_receiver_help_a.md",
         "receiver review — helfen: Emma hilft dem Kind",
         ("dem Kind",),
         "Review: 4 pairs with helfen (pure dative, no accusative object). "
         "Agents help receivers. Vary receivers."),
        ("050_receiver_help_b.md",
         "receiver review — helfen: Taro hilft dem Arzt",
         ("dem Arzt",),
         "Review: 4 pairs with helfen. Vary agents and receivers."),
        ("051_receiver_tell_a.md",
         "receiver review — sagen: Emma sagt dem Kind etwas",
         ("dem Kind",),
         "Review: 4 pairs with sagen. Agents say something to receivers. "
         "Keep German simple: Emma sagt dem Kind [something]."),
        ("052_receiver_tell_b.md",
         "receiver review — sagen: Taro sagt dem Mann etwas",
         ("dem Mann",),
         "Review: 4 pairs with sagen. Vary agents and receivers."),
        ("053_receiver_send_a.md",
         "receiver review — schicken: Emma schickt dem Kind das Buch",
         ("dem Kind", "das Buch"),
         "Review: 4 pairs with schicken. Vary objects and receivers."),
        ("054_receiver_send_b.md",
         "receiver review — schicken: Gran schickt der Frau den Apfel",
         ("der Frau", "den Apfel"),
         "Review: 4 pairs with schicken. Vary agents, receivers, objects."),
        ("055_receiver_lend_a.md",
         "receiver review — leihen: Emma leiht dem Kind das Buch",
         ("dem Kind", "das Buch"),
         "Review: 4 pairs with leihen (to lend). Vary objects and receivers."),
        ("056_receiver_lend_b.md",
         "receiver review — leihen: Taro leiht dem Arzt den Ball",
         ("dem Arzt", "den Ball"),
         "Review: 4 pairs with leihen. Vary agents, receivers, objects."),
        ("057_receiver_multi_a.md",
         "receiver review — mixed verbs: geben, zeigen, bringen",
         ("dem Kind", "dem Mann"),
         "Review: 4 pairs with mixed receiver verbs. "
         "Pair 1: geben. Pair 2: zeigen. Pair 3: bringen. Pair 4: helfen."),
        ("058_receiver_multi_b.md",
         "receiver review — mixed verbs: sagen, schicken, leihen",
         ("der Frau", "dem Arzt"),
         "Review: 4 pairs with mixed receiver verbs. "
         "Pair 1: sagen. Pair 2: schicken. Pair 3: leihen. Pair 4: zeigen."),
        ("059_receiver_multi_c.md",
         "receiver review — mixed agents, receivers, and verbs",
         ("dem Kind", "dem Lehrer"),
         "Review: 4 pairs with fully mixed agents, receivers, and verbs. "
         "Vary everything across all 4 pairs."),
        ("060_receiver_review.md",
         "full receiver dative review — all verbs, all receivers",
         ("dem", "den"),
         "Final receiver review: 4 pairs covering the full range of receiver dative patterns. "
         "Vary verbs (geben/zeigen/bringen/helfen), receivers, and objects. "
         "Keep receiver dative visibly marked."),

        # Group 4: mixed dative+accusative 061-080
        ("061_mixed_give_place_a.md",
         "give + place on table — receiver dative + endpoint accusative",
         ("dem Kind", "auf den Tisch"),
         "Mix: receiver dative + endpoint accusative in the same file. "
         "Pair 1-2: Emma gibt dem Kind den Apfel. "
         "Pair 3-4: Emma stellt den Becher auf den Tisch. "
         "Keep both patterns distinct."),
        ("062_mixed_give_place_b.md",
         "show + place on bench — receiver dative + endpoint accusative",
         ("dem Mann", "auf die Bank"),
         "Mix: zeigen (receiver dative) + stellen (endpoint accusative). "
         "2 pairs each. Vary objects."),
        ("063_mixed_static_endpoint_a.md",
         "static + endpoint contrast — Wo? vs Wohin?",
         ("auf dem Tisch", "auf den Tisch"),
         "Mix: static location and endpoint in the same file. "
         "Pair 1-2 (STATIC): Der Becher ist auf dem Tisch. "
         "Pair 3-4 (ENDPOINT): Emma stellt den Becher auf den Tisch."),
        ("064_mixed_static_endpoint_b.md",
         "static + endpoint — in der Küche vs in die Küche",
         ("in der Küche", "in die Küche"),
         "Mix: static dative and endpoint accusative for in. "
         "Pair 1-2 (STATIC): Taro ist in der Küche. "
         "Pair 3-4 (ENDPOINT): Taro geht in die Küche."),
        ("065_mixed_receiver_object_a.md",
         "receiver + direct object — dem Kind + den Apfel",
         ("dem Kind", "den Apfel"),
         "Mix: receiver dative and direct object accusative in the same file. "
         "4 pairs using both — Emma gibt dem Kind den Apfel. "
         "Vary verbs and objects."),
        ("066_mixed_receiver_object_b.md",
         "receiver + direct object — dem Mann + das Buch",
         ("dem Mann", "das Buch"),
         "Mix: receiver dative and direct object. "
         "4 pairs: Taro zeigt dem Mann das Buch, etc. Vary verbs and objects."),
        ("067_mixed_source_endpoint_a.md",
         "source + endpoint chain — aus der Küche + auf den Tisch",
         ("aus der Küche", "auf den Tisch"),
         "Mix: source movement and endpoint. "
         "4 pairs using aus-source + auf/in-endpoint chains. "
         "Vary agents and objects."),
        ("068_mixed_source_endpoint_b.md",
         "source + endpoint chain — vom Tisch + in den Garten",
         ("vom Tisch", "in den Garten"),
         "Mix: source and endpoint movement. "
         "4 pairs: agents take objects from the table to the garden. Vary agents and objects."),
        ("069_mixed_all_dative_a.md",
         "all dative patterns — aus, von, dem receiver, static location",
         ("dem Kind", "aus der Küche"),
         "Mix: multiple dative patterns in one file. "
         "Pair 1: receiver dative (gibt dem Kind). "
         "Pair 2: source aus (aus der Küche). "
         "Pair 3: static location (auf dem Tisch). "
         "Pair 4: combined (aus der Küche + dem Kind geben)."),
        ("070_mixed_all_dative_b.md",
         "all dative patterns — set 2",
         ("dem Mann", "von der Bank"),
         "Mix: multiple dative patterns. "
         "Vary the dative contexts across 4 pairs."),
        ("071_mixed_all_accusative_a.md",
         "all accusative patterns — endpoint + direct object",
         ("auf den Tisch", "den Apfel"),
         "Mix: endpoint accusative and direct object accusative. "
         "Pair 1-2: endpoint (stellt auf den Tisch). "
         "Pair 3-4: direct object (nimmt den Apfel). "
         "Keep German accusative markers visible."),
        ("072_mixed_all_accusative_b.md",
         "all accusative patterns — set 2",
         ("in die Küche", "das Buch"),
         "Mix: endpoint and direct object accusative. Vary across 4 pairs."),
        ("073_mixed_possession_place_a.md",
         "possession + static location — Emmas Becher ist auf dem Tisch",
         ("Emmas Becher", "auf dem Tisch"),
         "Mix: possession and static location. "
         "4 pairs describing where possessions are. "
         "E.g. Emmas Becher ist auf dem Tisch. Taros Ball liegt unter der Bank."),
        ("074_mixed_possession_place_b.md",
         "possession + static location — set 2",
         ("Taros Ball", "unter der Bank"),
         "Mix: possession and static location. 4 pairs. Vary owners and locations."),
        ("075_mixed_possession_receiver_a.md",
         "possession + receiver — Emma gibt dem Kind Taros Apfel",
         ("Taros Apfel", "dem Kind"),
         "Mix: possession and receiver dative. "
         "4 pairs where someone gives another person's thing to a receiver. "
         "E.g. Emma gibt dem Kind Taros Apfel."),
        ("076_mixed_possession_receiver_b.md",
         "possession + receiver — set 2",
         ("Emmas Buch", "dem Mann"),
         "Mix: possession and receiver. 4 pairs. Vary owners, receivers, objects. "
         "Do NOT use demonstratives (dieser, diese, dieses, jener, etc.) — repeat the noun or name instead."),
        ("077_mixed_review_a.md",
         "mixed review — static, endpoint, receiver",
         ("auf dem Tisch", "auf den Tisch", "dem Kind"),
         "Review: 4 pairs mixing static location, endpoint, and receiver patterns. "
         "Pair 1: static. Pair 2: endpoint. Pair 3: receiver. Pair 4: combined."),
        ("078_mixed_review_b.md",
         "mixed review — source, endpoint, receiver",
         ("aus der Küche", "auf den Tisch", "dem Mann"),
         "Review: 4 pairs mixing source, endpoint, and receiver. Vary across pairs."),
        ("079_mixed_review_c.md",
         "mixed review — all patterns in sequence",
         ("dem Kind", "auf dem Tisch", "auf den Tisch"),
         "Review: 4 pairs each targeting a different grammar cluster. "
         "Pair 1: receiver. Pair 2: static. Pair 3: endpoint. Pair 4: source+endpoint."),
        ("080_mixed_review_d.md",
         "mixed review — full combination",
         ("dem", "auf dem", "auf den"),
         "Review: 4 fully mixed pairs drawing on all grammar clusters. "
         "Vary patterns, agents, and objects across all 4 pairs."),

        # Group 5: full review stories 081-100
        ("081_full_emma_a.md",
         "Emma's story — static location and endpoint",
         ("Emma", "auf dem Tisch"),
         "Story: Emma's day involving static location and movement. "
         "4 narrative pairs: Emma sees where something is, then moves it. "
         "Use natural story flow. Keep grammar clean."),
        ("082_full_emma_b.md",
         "Emma's story — giving and receiving",
         ("Emma", "dem Kind"),
         "Story: Emma gives things to people. "
         "4 pairs: Emma gives the child an apple, shows the man the book, etc. "
         "Mix receiver dative verbs."),
        ("083_full_emma_c.md",
         "Emma's story — journey with objects",
         ("Emma", "aus der Küche"),
         "Story: Emma carries objects on a journey. "
         "4 narrative pairs: Emma takes something from the kitchen to the garden, gives it away, etc. "
         "Mix source + endpoint + receiver in natural sequence."),
        ("084_full_taro_a.md",
         "Taro's story — static location and endpoint",
         ("Taro", "auf den Tisch"),
         "Story: Taro's day involving static and movement patterns. "
         "4 narrative pairs. Use natural story flow."),
        ("085_full_taro_b.md",
         "Taro's story — giving and receiving",
         ("Taro", "dem Arzt"),
         "Story: Taro gives things to people. "
         "4 pairs: Taro gives the doctor the book, shows the child the ball, etc."),
        ("086_full_taro_c.md",
         "Taro's story — journey with objects",
         ("Taro", "aus dem Garten"),
         "Story: Taro carries objects on a journey. "
         "4 narrative pairs mixing source + endpoint + receiver."),
        ("087_full_gran_a.md",
         "Gran's story — static location and endpoint",
         ("Gran", "auf dem Boden"),
         "Story: Gran's day. 4 narrative pairs with static and movement patterns."),
        ("088_full_gran_b.md",
         "Gran's story — giving and receiving",
         ("Gran", "dem Kind"),
         "Story: Gran gives things to people. 4 pairs with receiver dative."),
        ("089_full_gran_c.md",
         "Gran's story — journey with objects",
         ("Gran", "von der Bank"),
         "Story: Gran carries objects on a journey. "
         "4 narrative pairs mixing von-source + auf/in endpoint."),
        ("090_full_biscuit_a.md",
         "Biscuit's story — running and finding",
         ("Biscuit", "unter dem Tisch"),
         "Story: Biscuit's adventure. "
         "4 narrative pairs: Biscuit runs to locations, finds things, goes home. "
         "Use animal-appropriate verbs."),
        ("091_full_biscuit_b.md",
         "Biscuit's story — chasing and fetching",
         ("Biscuit", "in den Garten"),
         "Story: Biscuit chases and fetches objects. "
         "4 pairs with movement verbs appropriate for a dog. "
         "Mix static and endpoint patterns."),
        ("092_full_biscuit_c.md",
         "Biscuit's story — Biscuit and Emma",
         ("Biscuit", "Emma"),
         "Story: Biscuit and Emma together. "
         "4 narrative pairs where Biscuit and Emma interact — Biscuit fetches, Emma gives, etc."),
        ("093_full_cast_a.md",
         "full cast story — all four characters",
         ("Emma", "Taro", "Gran", "Biscuit"),
         "Story: short narrative with all four characters. "
         "4 pairs, one per character. Each does something grammatically distinct. "
         "Natural story arc."),
        ("094_full_cast_b.md",
         "full cast story — giving and moving",
         ("Emma", "dem Kind", "auf den Tisch"),
         "Story: all characters involved in giving and moving objects. "
         "4 pairs mixing receiver dative and endpoint accusative across characters."),
        ("095_full_cast_c.md",
         "full cast story — morning in the garden",
         ("Emma", "aus der Küche", "in den Garten"),
         "Story: morning scene. Characters move from kitchen to garden. "
         "4 narrative pairs with source + endpoint chains."),
        ("096_full_cast_d.md",
         "full cast story — possession and location",
         ("Emmas", "auf dem Tisch", "dem Kind"),
         "Story: whose things are where? Characters give and receive possessions. "
         "4 pairs combining ownership, location, and receiver dative."),
        ("097_final_review_a.md",
         "final review story — static, endpoint, receiver",
         ("auf dem Tisch", "auf den Tisch", "dem Kind"),
         "Final review: narrative 4 pairs covering static dative, endpoint accusative, and receiver dative. "
         "Natural story arc. Keep grammar clean."),
        ("098_final_review_b.md",
         "final review story — source, endpoint, possession",
         ("aus der Küche", "auf den Tisch", "Emmas"),
         "Final review: narrative covering source, endpoint, and possession. "
         "4 pairs with natural story flow."),
        ("099_final_review_c.md",
         "final review story — all dative patterns",
         ("aus der Küche", "auf dem Tisch", "dem Kind"),
         "Final review: narrative covering all dative patterns (source/static/receiver). "
         "4 pairs. Keep German dative forms visible throughout."),
        ("100_final_review_d.md",
         "final review story — all patterns combined",
         ("auf dem Tisch", "auf den Tisch", "dem Kind", "Emmas"),
         "Final review: 4 narrative pairs drawing on all grammar clusters. "
         "Static dative, endpoint accusative, receiver dative, source, possession. "
         "Natural story. Familiar cast and locations. "
         "JP and ZH should follow naturally. Traditional Chinese throughout."),
    ]

    return [
        FileSpec(
            path=f"10_review_stories/{filename}",
            focus=focus,
            required_terms=required,
            notes=notes + shared_suffix,
        )
        for filename, focus, required, notes in rows
    ]


def make_relation_specs() -> list[FileSpec]:
    """Specs for `00_relation`: meta-concept definitions and applied examples."""
    rows: list[tuple[str, str, tuple[str, ...], str]] = [
        # ── Abstract concept definitions ──
        ("001_relation_receiver.md",
         "relation and receiver",
         ("relation", "receiver"),
         "Explain that a receiver gets something or is helped by an action."),
        ("002_place_source_target.md",
         "place, source, target",
         ("place", "source", "target"),
         "Contrast where something is, where movement begins, and where movement points."),
        ("003_path_object_action.md",
         "path, object, action",
         ("path", "object", "action"),
         "Keep object as acted-on thing; keep path as route through space."),
        ("004_owner_change_means.md",
         "owner, change, means",
         ("owner", "change", "means"),
         "Keep means as way/tool/vehicle used to do something."),
        # ── Applied receiver examples ──
        ("005_receiver_give.md",
         "receiver concept applied: Emma gives the boy the apple",
         ("receiver", "gives"),
         "Applied example: Emma gibt dem Jungen den Apfel. Ask who the receiver is. "
         "The receiver (dem Jungen) gets the apple. Vary the object across 4 pairs: apple, book, cup, bread. "
         "Use dem Jungen as the receiver in every German line."),
        ("006_receiver_show.md",
         "receiver concept applied: Gran shows the child the cup",
         ("receiver", "shows"),
         "Applied example: Gran zeigt dem Kind den Becher. Ask who the receiver is. "
         "The receiver (dem Kind) sees the cup. Vary the object: cup, book, apple, basket. "
         "Use dem Kind as the receiver in every German line."),
        ("007_receiver_bring.md",
         "receiver concept applied: Taro brings the girl the basket",
         ("receiver", "brings"),
         "Applied example: Taro bringt dem Mädchen den Korb. Ask who the receiver is. "
         "The receiver (dem Mädchen) gets the basket. Vary: basket, bread, book, apple."),
        ("008_receiver_help.md",
         "receiver concept applied: Gran helps the neighbor (pure dative beneficiary)",
         ("receiver", "helps"),
         "Applied example: Gran hilft dem Nachbarn. The neighbor is the receiver (beneficiary). "
         "helfen takes only dative — no accusative object. "
         "Vary context: garden, kitchen, school, market."),
        ("009_receiver_tell.md",
         "receiver concept applied: Gran tells the child (receiver of information)",
         ("receiver", "tells"),
         "Applied example: Gran erzählt dem Kind. The child is the receiver of information. "
         "Vary content: tells about the garden, the dog, the apple, the book."),
        ("010_receiver_send.md",
         "receiver concept applied: Emma sends the doctor the book",
         ("receiver", "sends"),
         "Applied example: Emma schickt dem Arzt das Buch. Identify the receiver. "
         "Vary the object: book, document, basket, apple. Use dem Arzt in every German line."),
        # ── Applied place examples ──
        ("011_place_on_surface.md",
         "place concept applied: cup on the table (auf dem Tisch)",
         ("place", "on"),
         "Applied example: Der Becher ist auf dem Tisch. The table is the place. "
         "Use static verbs: is, sits, lies. "
         "Vary the subject: cup, apple, book, basket."),
        ("012_place_inside.md",
         "place concept applied: ball in the garden (in dem Garten)",
         ("place", "in"),
         "Applied example: Der Ball ist in dem Garten. The garden is the place. "
         "Use static verbs: is, lies, sits. "
         "Vary the subject: ball, dog, bench, boy. Use Hund, Bank, Junge."),
        ("013_place_below.md",
         "place concept applied: bag under the bench (unter der Bank)",
         ("place", "under"),
         "Applied example: Die Tasche ist unter der Bank. "
         "Use static verbs: is, lies, sits. "
         "Vary the subject: bag, ball, book, blanket."),
        ("014_place_beside.md",
         "place concept applied: bench next to the tree (neben dem Baum)",
         ("place", "next to"),
         "Applied example: Die Bank ist neben dem Baum. "
         "Use static verbs: is, sits, stands. "
         "Vary the subject: bench, ball, dog, boy. Use Hund, Junge."),
        ("015_place_in_front.md",
         "place concept applied: dog in front of the house (vor dem Haus)",
         ("place", "in front of"),
         "Applied example: Der Hund ist vor dem Haus. "
         "Use static verbs: is, sits, stands. "
         "Vary the subject: dog, boy, girl, bench. Use Hund, Junge, Mädchen."),
        ("016_place_behind.md",
         "place concept applied: cat behind the tree (hinter dem Baum)",
         ("place", "behind"),
         "Applied example: Die Katze ist hinter dem Baum. "
         "Use static verbs: is, sits, hides. "
         "Vary the subject: cat, dog, ball, bag. Use Katze, Hund."),
        # ── Applied source and target examples ──
        ("017_source_aus.md",
         "source concept applied: Emma comes from the kitchen (aus der Küche)",
         ("source", "from"),
         "Applied example: Emma kommt aus der Küche. The kitchen is the source. "
         "aus = always dative. Vary: Emma/Küche, Taro/Garten, Gran/Zimmer, Emma/Schule."),
        ("018_source_von.md",
         "source concept applied: Taro comes from the market (vom Markt)",
         ("source", "from"),
         "Applied example: Taro kommt vom Markt. The market is the source. "
         "von = always dative. Vary: Taro/Markt, Gran/Schule, Emma/Park, Taro/Garten."),
        ("019_target_nach_zu.md",
         "target concept applied: Emma goes to the park (nach/zu + dative)",
         ("target", "to"),
         "Applied example: Emma geht in den Park / Emma geht zum Markt. "
         "nach + place names; zu + dative nouns. Ask where Emma goes. "
         "Vary: Emma/Park, Taro/Markt, Gran/Schule, Biscuit/Garten."),
        ("020_target_in_accusative.md",
         "target concept applied: Emma puts the cup into the box (in + accusative = endpoint)",
         ("target", "into"),
         "Applied example: Emma legt den Becher in die Kiste. in + accusative marks the endpoint. "
         "This contrasts with in + dative (static place). "
         "Vary: cup into box, apple into basket, book into bag, bread into basket."),
        ("021_path_durch.md",
         "path concept applied: Biscuit runs through the garden (durch den Garten)",
         ("path", "through"),
         "Applied example: Biscuit läuft durch den Garten. durch = through, always accusative. "
         "The garden is the path — Biscuit passes through it. "
         "Vary: through the garden, through the room, through the park, through the school."),
        # ── Applied owner examples ──
        ("022_owner_possessive.md",
         "owner concept applied: Emma's cup (Emmas Becher)",
         ("owner", "Emma"),
         "Applied example: Das ist Emmas Becher. The owner is Emma. "
         "Ask whose cup it is. "
         "Vary: Emma's cup, Taro's book, Gran's basket, Biscuit's ball."),
        ("023_owner_wessen.md",
         "owner concept applied: Wessen Becher ist das? (Whose cup is it?)",
         ("owner", "whose"),
         "Applied example: Wessen Becher ist das? Das ist Emmas Becher. "
         "Wessen asks about the owner. "
         "Vary the object: cup, book, basket, ball."),
        ("024_owner_von.md",
         "owner concept applied: the cup of the woman (von der Frau)",
         ("owner", "of"),
         "Applied example: Das ist der Becher von der Frau. "
         "von + dative as alternative to name-s possessive. "
         "Vary: cup of the woman, book of the man, basket of the child, ball of the boy."),
        # ── Applied change and means examples ──
        ("025_change_put.md",
         "change concept applied: Emma puts the cup on the table (change of location)",
         ("change", "puts"),
         "Applied example: Emma legt den Becher auf den Tisch. The cup changes location. "
         "Vary: cup on table, apple in basket, book on bench, bread in bag."),
        ("026_means_instrument.md",
         "means concept applied: Emma sweeps with a broom (mit dem Besen)",
         ("means", "with"),
         "Applied example: Emma fegt mit dem Besen. The broom is the means (instrument). "
         "mit + dative. Vary: sweep with broom, write with pencil, fix with hammer, carry with basket."),
        ("027_means_vehicle.md",
         "means concept applied: Taro goes to school by bus (mit dem Bus)",
         ("means", "bus"),
         "Applied example: Taro fährt mit dem Bus zur Schule. The bus is the means (vehicle). "
         "English: by bus (not with the bus). Vary: by bus, by car, by train, by bike."),
        ("028_means_accompaniment.md",
         "means concept applied: Gran walks with Biscuit (mit dem Hund)",
         ("means", "with"),
         "Applied example: Gran geht mit dem Hund spazieren. The dog is a companion (also mit). "
         "mit marks accompaniment here, not a tool. "
         "Vary: walks with dog, sits with child, reads with Emma, goes with Gran."),
        # ── Contrast exercises ──
        ("029_contrast_receiver_vs_object.md",
         "contrast: receiver (dative) vs. object (accusative)",
         ("receiver", "object"),
         "Contrast: Emma gibt dem Jungen den Apfel. "
         "dem Jungen = receiver (dative), den Apfel = object (accusative). "
         "4 pairs asking which is the receiver and which is the object. "
         "Vary the verb: give, show, bring, send."),
        ("030_contrast_place_vs_target.md",
         "contrast: place (dative) vs. target/endpoint (accusative)",
         ("place", "target"),
         "Contrast: Der Becher ist auf dem Tisch (place, dative). "
         "Emma legt den Becher auf den Tisch (target, accusative). "
         "4 pairs alternating place and target with same preposition. "
         "Use auf dem/auf den, in dem/in den."),
        ("031_contrast_source_vs_place.md",
         "contrast: source (aus/von + dative) vs. place (in/auf + dative)",
         ("source", "place"),
         "Contrast: Emma kommt aus der Küche (source). Der Becher ist in der Küche (place). "
         "aus marks where something comes from; in+dative marks where it is. "
         "4 pairs contrasting source and place."),
        ("032_contrast_path_vs_target.md",
         "contrast: path (durch + accusative) vs. target (in/auf + accusative)",
         ("path", "target"),
         "Contrast: Biscuit läuft durch den Garten (path). Emma geht in den Garten (target endpoint). "
         "durch = through (path); in+accusative = into (endpoint). "
         "4 pairs contrasting durch and in+accusative."),
        ("033_contrast_owner_vs_receiver.md",
         "contrast: owner (Emmas / von Emma) vs. receiver (who gets something)",
         ("owner", "receiver"),
         "Contrast: Das ist Emmas Becher (owner, static). "
         "Emma gibt dem Jungen den Becher (Emma is giver, not receiver here). "
         "Ownership is a static relation; receiver is who gets something in an action. "
         "4 pairs clarifying the distinction."),
        ("034_contrast_action_vs_change.md",
         "contrast: action (what happens) vs. change (what result follows)",
         ("action", "change"),
         "Contrast: Emma legt den Becher auf den Tisch (action). "
         "Der Becher ist jetzt auf dem Tisch (change = new state). "
         "4 pairs showing action → change pattern."),
        ("035_contrast_means_vs_object.md",
         "contrast: means (mit + dative) vs. object (accusative)",
         ("means", "object"),
         "Contrast: Emma fegt mit dem Besen (means = broom is tool). "
         "Emma nimmt den Besen (object = broom is taken). "
         "4 pairs where the same noun alternates as means and object."),
        # ── Mixed applied stories ──
        ("036_story_give_and_place.md",
         "story: receiver + place — Emma gives Taro the cup, it is on the table",
         ("receiver", "place"),
         "Story: Emma gibt Taro den Becher. Der Becher steht auf dem Tisch. "
         "Identify the receiver (Taro) and the place (auf dem Tisch). "
         "Vary object and location across 4 pairs."),
        ("037_story_source_and_target.md",
         "story: source + target — Gran comes from the kitchen, goes to the garden",
         ("source", "target"),
         "Story: Gran kommt aus der Küche. Gran geht in den Garten. "
         "Identify source (Küche) and target (Garten). "
         "Vary agent and locations across 4 pairs."),
        ("038_story_owner_and_change.md",
         "story: owner + change — Emmas cup moves from the table to the basket",
         ("owner", "change"),
         "Story: Emmas Becher steht auf dem Tisch. Emma legt den Becher in den Korb. "
         "Identify owner (Emma) and change (cup moved). "
         "Vary object and location across 4 pairs."),
        ("039_story_path_and_destination.md",
         "story: path + target — Taro walks through the garden to the house",
         ("path", "target"),
         "Story: Taro geht durch den Garten zum Haus. "
         "Identify path (den Garten) and destination (zum Haus). "
         "Vary agent and route across 4 pairs."),
        ("040_story_means_and_receiver.md",
         "story: means + receiver — Gran writes with a pencil and gives Emma the book",
         ("means", "receiver"),
         "Story: Gran schreibt mit dem Bleistift. Gran gibt Emma das Buch. "
         "Identify means (Bleistift) and receiver (Emma). "
         "Vary tool and receiver across 4 pairs."),
        # ── Question form practice ──
        ("041_question_wem.md",
         "Wem? question — who is the receiver? (Wem gibt Emma den Apfel?)",
         ("Wem", "receiver"),
         "Question form: Wem gibt Emma den Apfel? Answer: dem Jungen. "
         "4 pairs using Wem with different receiver/object pairs. "
         "Use dem Jungen, dem Kind, der Frau, dem Arzt as receivers."),
        ("042_question_wo.md",
         "Wo? question — where is it? (Wo ist der Becher?)",
         ("Wo", "place"),
         "Question form: Wo ist der Becher? Answer: auf dem Tisch. "
         "4 pairs using Wo with different object/place pairs. "
         "Keep the dative article explicit in every answer."),
        ("043_question_woher.md",
         "Woher? question — where from? (Woher kommt Emma?)",
         ("Woher", "source"),
         "Question form: Woher kommt Emma? Answer: aus der Küche. "
         "4 pairs using Woher with different agent/source pairs."),
        ("044_question_wohin.md",
         "Wohin? question — where to? (Wohin geht Taro?)",
         ("Wohin", "target"),
         "Question form: Wohin geht Taro? Answer: in den Garten. "
         "4 pairs using Wohin with different agent/target pairs."),
        ("045_question_wessen.md",
         "Wessen? question — whose? (Wessen Becher ist das?)",
         ("Wessen", "owner"),
         "Question form: Wessen Becher ist das? Answer: Das ist Emmas Becher. "
         "4 pairs using Wessen with different object/owner pairs."),
        ("046_question_womit.md",
         "Womit? question — with what? (Womit fegt Emma?)",
         ("Womit", "means"),
         "Question form: Womit fegt Emma? Answer: mit dem Besen. "
         "4 pairs using Womit with different action/means pairs. "
         "Include instrument, vehicle, and accompaniment examples."),
        # ── Review and mixed files ──
        ("047_review_receiver_place.md",
         "review: receiver and place in one scene",
         ("receiver", "place"),
         "Review: Emma gibt dem Jungen den Becher. Der Junge sitzt auf der Bank. "
         "4 pairs cycling through giver, receiver, object, and place. Keep all four roles visible."),
        ("048_review_source_path_target.md",
         "review: source, path, and target in one journey",
         ("source", "target"),
         "Review: Taro kommt aus dem Garten. Taro geht durch den Park. Taro geht in das Haus. "
         "Identify source, path, target in each pair. Use 4 different journey scenarios."),
        ("049_review_owner_means.md",
         "review: owner and means in one scene",
         ("owner", "means"),
         "Review: Emmas Besen steht in der Küche. Emma fegt mit dem Besen. "
         "Identify owner (Emma) and means (Besen). Use 4 object/agent combinations."),
        ("050_review_all_concepts.md",
         "full review: all 11 meta-concepts in context",
         ("receiver", "place"),
         "Full review with one concept per pair. "
         "Pair 1: receiver. Pair 2: place. Pair 3: source/target. Pair 4: owner/means. "
         "Use Emma/Taro/Gran/Biscuit and familiar objects."),
        # ── Extended applied examples ──
        ("051_applied_receiver_lend.md",
         "applied: Gran lends the woman the pencil (leihen + dative receiver)",
         ("receiver", "lends"),
         "Applied: Gran leiht der Frau den Bleistift. Identify the receiver (der Frau). "
         "Vary the object: pencil, book, basket, cup."),
        ("052_applied_receiver_answer.md",
         "applied: Emma answers the teacher (antworten + pure dative)",
         ("receiver", "answers"),
         "Applied: Emma antwortet dem Lehrer. The teacher is the receiver of the answer. "
         "antworten takes only dative. Vary receiver: Lehrer, Frau, Kind, Arzt."),
        ("053_applied_place_above.md",
         "applied: lamp above the table (über dem Tisch — static place above)",
         ("place", "above"),
         "Applied: Die Lampe ist über dem Tisch. Use static verbs: is, hangs. "
         "Vary: lamp above table, bird above mountain, cloud above roof."),
        ("054_applied_place_between.md",
         "applied: ball between the chairs (zwischen den Stühlen — static place between)",
         ("place", "between"),
         "Applied: Der Ball ist zwischen den Stühlen. zwischen takes dative plural. "
         "Vary: ball between chairs, bag between trees, apple between boxes."),
        ("055_applied_owner_taros.md",
         "applied: Taros ball is in the garden (Taros possessive)",
         ("owner", "Taro"),
         "Applied: Taros Ball ist in dem Garten. Identify the owner (Taro). "
         "Vary: Taros ball, Emmas cup, Grans basket, Biscuits blanket."),
        ("056_applied_means_vehicle.md",
         "applied: Emma goes by train (mit dem Zug — vehicle as means)",
         ("means", "train"),
         "Applied: Emma fährt mit dem Zug. The train is the means of travel. "
         "English: by train (not with the train). Vary: train, car, bus, bike."),
        ("057_applied_change_give.md",
         "applied: cup changes hands — Emma gives, Taro now has it",
         ("change", "gives"),
         "Applied: Emma gibt Taro den Becher. Taro hat jetzt den Becher. "
         "The cup changed from Emma's possession to Taro's. "
         "Vary the object: apple, book, basket, pencil."),
        ("058_applied_action_sweep.md",
         "applied: Emma sweeps the kitchen (action + object + means)",
         ("action", "sweeps"),
         "Applied: Emma fegt die Küche mit dem Besen. "
         "Identify: action (fegen), object (Küche), means (Besen). "
         "Vary: sweep kitchen, write document, fix chair, carry basket."),
        ("059_applied_path_walk.md",
         "applied: Taro walks through the park (durch den Park — path)",
         ("path", "through"),
         "Applied: Taro geht durch den Park. The park is the path. "
         "Vary the path: park, garden, room, school."),
        ("060_applied_source_person.md",
         "applied: the book comes from Gran (von Gran — person as source)",
         ("source", "from"),
         "Applied: Das Buch kommt von Gran. Gran is the source (person origin). "
         "Vary: from Gran, from Emma, from the doctor, from the neighbor."),
        # ── More contrast and review ──
        ("061_contrast_wem_wen.md",
         "contrast: Wem? (receiver, dative) vs. Wen? (object, accusative)",
         ("Wem", "Wen"),
         "Contrast: Wem gibt Emma den Apfel? (receiver, dative) vs. Wen sieht Emma? (object, accusative). "
         "4 pairs alternating Wem and Wen. Reinforce: Wem = dative receiver, Wen = accusative object."),
        ("062_contrast_wo_wohin_woher.md",
         "contrast: Wo? (place) vs. Wohin? (target) vs. Woher? (source)",
         ("Wo", "Wohin"),
         "Contrast: Wo ist Emma? (place). Wohin geht Emma? (target). Woher kommt Emma? (source). "
         "4 pairs using a different question word. Use Emma/Taro/Gran/Biscuit."),
        ("063_contrast_mit_durch.md",
         "contrast: mit + dative (means/accompaniment) vs. durch + accusative (path)",
         ("mit", "durch"),
         "Contrast: Gran geht mit dem Hund (mit = accompaniment). "
         "Gran geht durch den Garten (durch = path). "
         "4 pairs contrasting mit and durch."),
        ("064_contrast_in_dative_accusative.md",
         "contrast: in + dative (place) vs. in + accusative (target/endpoint)",
         ("in dem", "in den"),
         "Contrast: Der Becher ist in der Küche (place, dative). "
         "Emma legt den Becher in die Küche (target, accusative). "
         "4 pairs contrasting in + dative vs. in + accusative."),
        ("065_contrast_aus_von.md",
         "contrast: aus (from inside) vs. von (from near, from person)",
         ("aus", "von"),
         "Contrast: Emma kommt aus der Küche (aus = from inside a space). "
         "Das Buch kommt von Gran (von = from a person or surface). "
         "4 pairs contrasting aus and von."),
        # ── More mixed stories ──
        ("066_story_full_chain_a.md",
         "story: complete chain — source, path, target, receiver",
         ("source", "receiver"),
         "Story: Taro kommt aus der Küche (source). Taro geht durch den Garten (path). "
         "Taro geht zum Haus (target). Taro gibt Gran den Apfel (receiver). "
         "4 pairs narrating the full journey with all role-labels."),
        ("067_story_full_chain_b.md",
         "story: complete chain — owner, action, receiver, change",
         ("owner", "receiver"),
         "Story: Das ist Emmas Apfel (owner). Emma nimmt den Apfel (action). "
         "Emma gibt dem Kind den Apfel (receiver). Das Kind hat jetzt den Apfel (change). "
         "4 pairs with all role-labels."),
        ("068_story_biscuit_journey.md",
         "story: Biscuit's journey — place, path, target",
         ("place", "path"),
         "Story: Biscuit ist in dem Garten (place). Biscuit läuft durch das Haus (path). "
         "Biscuit geht in das Zimmer (target). Biscuit liegt auf dem Boden (new place). "
         "4 pairs; identify each role."),
        ("069_story_gran_cook_give.md",
         "story: Gran cooks and gives — means, receiver, change",
         ("means", "receiver"),
         "Story: Gran kocht mit dem Topf (means). Gran gibt dem Kind das Brot (receiver). "
         "Das Kind hat jetzt das Brot (change). "
         "4 pairs narrating the scene."),
        ("070_story_emma_write.md",
         "story: Emma writes with a pencil and gives — means, action, receiver",
         ("means", "receiver"),
         "Story: Emma schreibt mit dem Bleistift (means). Emma gibt Gran das Buch (receiver). "
         "Gran liest das Buch (action). "
         "4 pairs; identify each role."),
        ("071_story_taro_send.md",
         "story: Taro sends from home — source, action, receiver, change",
         ("source", "receiver"),
         "Story: Taro schickt dem Arzt das Dokument (receiver). Das Dokument kommt von Taro (source). "
         "Der Arzt hat das Dokument (change). "
         "4 pairs; identify each role."),
        ("072_story_owner_lend.md",
         "story: Emma's pencil is lent to the boy",
         ("owner", "receiver"),
         "Story: Das ist Emmas Bleistift (owner). Emma leiht dem Jungen den Bleistift (receiver). "
         "Der Junge hat den Bleistift (change). Der Bleistift ist auf dem Tisch (place). "
         "4 pairs."),
        ("073_story_biscuit_fetch.md",
         "story: Biscuit fetches the ball — path, object, receiver",
         ("path", "object"),
         "Story: Der Ball ist in dem Garten (place). Biscuit läuft durch den Garten (path). "
         "Biscuit nimmt den Ball (object). Biscuit bringt Gran den Ball (receiver). "
         "4 pairs."),
        ("074_story_gran_market.md",
         "story: Gran travels to the market — means, source, target",
         ("means", "target"),
         "Story: Gran fährt mit dem Bus (means). Gran geht zum Markt (target). "
         "Gran kommt vom Markt (source, return). Gran bringt Taro das Brot (receiver). "
         "4 pairs."),
        ("075_story_emma_place_things.md",
         "story: Emma places objects — action, object, target, place",
         ("action", "place"),
         "Story: Emma legt den Becher auf den Tisch (target). Der Becher ist auf dem Tisch (place). "
         "Emma legt das Buch in den Korb (target). Das Buch ist in dem Korb (place). "
         "4 pairs; alternate placing and resting."),
        # ── More review files ──
        ("076_review_questions_a.md",
         "review: Wo? Woher? Wohin? with Emma",
         ("Wo", "Woher"),
         "Mixed question review with Emma. Use Wo? Woher? Wohin? questions. "
         "4 pairs: Wo ist Emma?, Woher kommt Emma?, Wohin geht Emma?, Wo ist Emma jetzt? "
         "Use familiar locations: Küche, Garten, Zimmer, Schule."),
        ("077_review_questions_b.md",
         "review: Wem? Wessen? Womit? with Taro",
         ("Wem", "Wessen"),
         "Mixed question review with Taro. Use Wem? Wessen? Womit? questions. "
         "4 pairs: Wem gibt Taro den Apfel?, Wessen Buch ist das?, "
         "Womit schreibt Taro?, Wem antwortet Taro?"),
        ("078_review_all_questions.md",
         "review: 4 question words — Wo, Woher, Wohin, Wem",
         ("Wo", "Wem"),
         "Each of the 4 pairs uses a different question word: Wo, Woher, Wohin, Wem. "
         "Keep the answers clear and explicit. Use Emma/Taro/Gran."),
        ("079_review_story_combined_a.md",
         "review story A: Gran's morning — source, place, receiver, means",
         ("source", "means"),
         "Story: Gran kommt aus der Küche (source). Gran setzt sich auf die Bank (place). "
         "Gran gibt Biscuit den Ball (receiver). Gran geht mit Biscuit in den Garten (accompaniment). "
         "4 pairs narrating Gran's morning."),
        ("080_review_story_combined_b.md",
         "review story B: Taro's afternoon — target, path, owner, receiver",
         ("target", "owner"),
         "Story: Taro geht in den Garten (target). Taro läuft durch den Park (path). "
         "Das ist Taros Ball (owner). Taro gibt Emma den Ball (receiver). "
         "4 pairs narrating Taro's afternoon."),
        ("081_review_story_combined_c.md",
         "review story C: Emma's errand — source, means, target, change",
         ("source", "target"),
         "Story: Emma kommt aus der Schule (source). Emma fährt mit dem Bus (means). "
         "Emma geht zum Markt (target). Emma bringt Gran das Brot (change). "
         "4 pairs narrating Emma's errand."),
        ("082_review_story_combined_d.md",
         "review story D: the cup's journey — owner, place, action, receiver",
         ("owner", "place"),
         "Story: Das ist Emmas Becher (owner). Der Becher ist auf dem Tisch (place). "
         "Emma nimmt den Becher (action). Emma gibt Taro den Becher (receiver). "
         "4 pairs narrating the cup's journey."),
        ("083_applied_receiver_complex.md",
         "applied: complex receiver scene — two givers, two receivers",
         ("receiver", "gives"),
         "Scene: Emma gibt dem Jungen den Apfel. Gran gibt dem Mädchen das Buch. "
         "Two givers and two receivers. Ask who receives what in each case. "
         "Vary the objects and receivers across 4 pairs."),
        ("084_applied_place_complex.md",
         "applied: multiple objects in different static places",
         ("place", "on"),
         "Scene: Der Becher ist auf dem Tisch. Das Buch ist auf dem Regal. "
         "Der Ball ist unter der Bank. Die Katze ist hinter dem Baum. "
         "4 pairs; each places a different object in a different static place."),
        ("085_applied_journey_full.md",
         "applied: full journey with source, path, target, and arrival place",
         ("source", "path"),
         "Journey: Taro kommt aus der Schule (source). Taro geht durch den Park (path). "
         "Taro geht in das Haus (target). Taro ist jetzt in dem Haus (arrival place). "
         "4 pairs narrating the full journey; label each segment."),
        ("086_applied_ownership_transfer.md",
         "applied: ownership transfer — Emmas cup becomes Taros cup",
         ("owner", "change"),
         "Transfer: Das ist Emmas Becher. Emma gibt Taro den Becher. "
         "Jetzt ist das Taros Becher. Identify owner before and after. "
         "Vary the object: cup, book, ball, basket."),
        ("087_applied_means_complex.md",
         "applied: vehicle + accompaniment in the same scene (both use mit)",
         ("means", "with"),
         "Scene: Gran fährt mit dem Bus (vehicle). Gran geht mit Biscuit spazieren (accompaniment). "
         "Both use mit; one is vehicle, the other is companion. "
         "4 pairs; identify whether each mit marks vehicle or accompaniment."),
        ("088_applied_action_chain.md",
         "applied: action chain — each step uses a different relation",
         ("action", "receiver"),
         "Chain: Emma nimmt den Apfel (object). Emma bringt den Apfel in die Küche (target). "
         "Emma gibt Gran den Apfel (receiver). Gran legt den Apfel auf den Tisch (place). "
         "4 pairs; each labels the key relation in that step."),
        # ── Final review files ──
        ("089_review_final_a.md",
         "final review A: identify the relation — receiver/place/source/target",
         ("receiver", "place"),
         "Each pair presents a sentence; ask which relation it shows. "
         "Pair 1: receiver. Pair 2: place. Pair 3: source. Pair 4: target. "
         "Use Emma/Taro/Gran and familiar objects."),
        ("090_review_final_b.md",
         "final review B: identify the relation — path/owner/means/change",
         ("path", "owner"),
         "Each pair presents a sentence; ask which relation it shows. "
         "Pair 1: path. Pair 2: owner. Pair 3: means. Pair 4: change. "
         "Use Emma/Taro/Gran and familiar objects."),
        ("091_review_final_c.md",
         "final review C: mixed — 4 pairs, 4 different question words",
         ("Wem", "Wohin"),
         "Pair 1: Wem gibt Emma den Apfel? Pair 2: Wo liegt der Ball? "
         "Pair 3: Woher kommt Taro? Pair 4: Wohin geht Gran? "
         "Keep dative/accusative answers explicit."),
        ("092_review_final_d.md",
         "final review D: complete scene with all 11 concepts present",
         ("receiver", "source"),
         "Scene: Taro kommt aus der Küche (source). Taros Apfel liegt auf dem Tisch (owner + place). "
         "Taro nimmt den Apfel (object + action). Taro gibt Emma den Apfel (receiver + change). "
         "4 pairs; label all relations visible in the scene."),
        ("093_review_final_e.md",
         "final review E: Wo vs. Wohin contrast in a full scene",
         ("Wo", "Wohin"),
         "Scene: Der Ball liegt auf dem Tisch (Wo?). Emma legt den Ball in den Korb (Wohin?). "
         "4 pairs alternating Wo and Wohin. "
         "Reinforce: same preposition, different case = different relation."),
        ("094_review_final_f.md",
         "final review F: Wem vs. Wen with give and see",
         ("Wem", "Wen"),
         "Pair 1: Wem gibt Emma den Apfel? (receiver). Pair 2: Wen sieht Emma? (direct object). "
         "Pair 3: Wem zeigt Taro das Buch? (receiver). Pair 4: Wen ruft Gran? (direct object)."),
        ("095_review_final_g.md",
         "final review G: Wessen vs. von + dative (owner two ways)",
         ("Wessen", "owner"),
         "Pair 1: Wessen Becher ist das? → Emmas Becher. "
         "Pair 2: Wessen Buch ist das? → Das Buch von Gran. "
         "Pair 3: Wessen Ball ist das? → Taros Ball. "
         "Pair 4: Wessen Korb ist das? → Der Korb von der Frau. "
         "Show both name-s form and von+dative form."),
        ("096_review_final_h.md",
         "final review H: Womit? — instrument vs. vehicle vs. accompaniment",
         ("Womit", "means"),
         "Pair 1: Womit fegt Emma? → mit dem Besen (instrument). "
         "Pair 2: Womit fährt Taro? → mit dem Bus (vehicle). "
         "Pair 3: Womit schreibt Gran? → mit dem Bleistift (instrument). "
         "Pair 4: Womit geht Biscuit? → mit Gran (accompaniment). "
         "Distinguish instrument, vehicle, accompaniment."),
        ("097_review_story_emma_full.md",
         "review story: Emma's full day — all 11 concepts touched",
         ("source", "receiver"),
         "Emma kommt aus der Schule (source). Emma hat Emmas Rucksack (owner). "
         "Emma fährt mit dem Bus (means). Emma bringt Gran das Buch (receiver). "
         "4 pairs; name at least one relation per pair."),
        ("098_review_story_taro_full.md",
         "review story: Taro's full day — path, means, receiver",
         ("path", "means"),
         "Taro geht durch den Park (path). Taro trägt den Korb (object). "
         "Taro bringt dem Kind den Apfel (receiver). Taro fährt mit dem Fahrrad (means). "
         "4 pairs; name at least one relation per pair."),
        ("099_review_story_gran_full.md",
         "review story: Gran's full day — owner, place, target, source",
         ("owner", "place"),
         "Grans Hund schläft auf der Bank (owner + place). Gran geht in den Garten (target). "
         "Gran gibt Emma die Decke (receiver). Gran kommt aus der Küche (source). "
         "4 pairs; name at least one relation per pair."),
        ("100_review_final_mixed.md",
         "final comprehensive review: all 11 concepts in one complete scene",
         ("receiver", "place"),
         "4 pairs each covering multiple concepts: "
         "Pair 1: owner + place. Pair 2: source + path. "
         "Pair 3: target + receiver. Pair 4: object + action + means + change. "
         "Use Emma, Taro, Gran, Biscuit, and familiar objects. "
         "Label every relation explicitly in the Ninereeds response."),
    ]

    return [
        FileSpec(
            path=f"00_relation/{filename}",
            focus=focus,
            required_terms=required,
            notes=notes,
        )
        for filename, focus, required, notes in rows
    ]


CLUSTERS: dict[str, list[FileSpec]] = {
    "00_relation": make_relation_specs(),
    "01_means_dative_anchor": make_mit_specs(),
    "01_means_dative_anchor_bei_audit": make_bei_audit_specs(),
    "01_means_dative_anchor_aus_audit": make_aus_audit_specs(),
    "01_means_dative_anchor_von_audit": make_von_audit_specs(),
    "01_means_dative_anchor_zu_audit": make_zu_audit_specs(),
    "01_means_dative_anchor_nach_audit": make_nach_audit_specs(),
    "01_means_dative_anchor_seit_audit": make_seit_specs(),
    "01_means_dative_anchor_gegenueber_audit": make_gegenueber_specs(),
    "02_receiver_dative": make_receiver_dative_specs(),
    "03_place_static_dative": make_place_static_dative_specs(),
    "04_change_state": make_change_state_specs(),
    "05_object_accusative_patient": make_object_accusative_specs(),
    "06_target_accusative_endpoint": make_target_accusative_endpoint_specs(),
    "07_place_target_contrast": make_place_target_contrast_specs(),
    "08_source_path_destination": make_source_path_destination_specs(),
    "09_owner_genitive": make_owner_genitive_specs(),
    "10_review_stories": make_review_stories_specs(),
    "bridge_course": make_bridge_specs(),
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
- Keep the same basic relation across the four response lines. Do not switch from static relation to movement unless the file notes explicitly allow that.
"""


BRIDGE_RULES = """
You are generating one bridge course annotation file for Ninereeds.
This is NOT a [user]/[Ninereeds] dialogue file. Do not use those tags.

Output ONLY the file content. No markdown fences. No preamble. No explanatory text.

BRACKET SEMANTICS:
  () = actor / subject  (nominative, German Nominativ)
  [] = anchor — receiver, location, or state  (dative, German Dativ)
  {} = target — direct object or endpoint  (accusative, German Akkusativ)
  ** = action / verb  (wrap the verb word only: *gives*, *gibt*, *あげた*)
  <> = ownership or source relation  (genitive, German Genitiv; nested inside {} or [])

FILE FORMAT — produce exactly three sections in this exact order:

SECTION 1 — ANNOTATED BLOCK (exactly 4 consecutive lines, EN then DE then JP then ZH):
  Apply role brackets consistently across all 4 lines.
  JP verb goes at sentence end; ** wraps it there.
  Example (ditransitive + nested genitive):
    (The man) *gave* [the dog] {the <boy's> ball}.
    (Der Mann) *gab* [dem Hund] {den Ball <des Jungen>}.
    (男の人が)[犬に]{<男の子の>ボールを}*あげた*。
    (男人)*给了*[狗]{<男孩的>球}。

SECTION 2 — ROLE QUESTION PAIRS (blank line between each pair):
  Generate one pair for each bracket type present in SECTION 1, in this order:
    () → (Wer / Who / 誰が / 谁)
    [] → [Wem / To whom / 誰に / 给谁]
    {} → {Was / What / 何を / 什么}
    <> → <Wessen / Whose / 誰の / 谁的>
  Skip bracket types not present in SECTION 1. Do NOT generate a pair for **.
  Question line: starts with the bracket-tagged multilingual interrogative, then an English question.
  Answer line: 4 bracketed answers separated by / in EN / DE / JP / ZH order.
  Example pair for []:
    [Wem / To whom / 誰に / 给谁] did the man give the boy's ball?
    [The dog]. / [Dem Hund]. / [犬に]. / [狗].

SECTION 3 — PLAIN BLOCK (exactly 4 consecutive lines, EN then DE then JP then ZH):
  The same sentence with NO bracket markers at all.
  Forbidden in the plain block: ( ) [ ] { } < > *
  Example:
    The man gave the dog the boy's ball.
    Der Mann gab dem Hund den Ball des Jungen.
    男の人が犬に男の子のボールを あげた。
    男人给了狗男孩的球。

Register:
- English: simple, natural, child-facing.
- German: correct Schulbuch style; case must match the bracket role: dative for [], accusative for {}, genitive for <>.
- Japanese: plain form, no ですます, no romaji; particle に for dative [], を for accusative {}.
- Chinese: Traditional Chinese; 給 or similar beneficiary marker for a dative receiver.

Capitalization rules for answer lines:
- Common nouns in bracket answers use lowercase: [the boy], {the apple}, <the man's>.
- Proper names preserve their case: (Emma), (Gran), (Taro).
- German nouns always capitalize as normal: [dem Jungen], {den Apfel}, (Der Mann).
- Japanese and Chinese answers follow their standard conventions.
- Do NOT sentence-capitalize isolated bracket answers: [the woman] not [The woman].

Content rules:
- Avoid pronouns; repeat the name or noun.
- Do not add nouns outside those specified in the file notes.
- German dative must use dem or der with a visible common noun.
- German accusative must use den / das / die with a visible common noun.
- Genitive modifier follows the noun it modifies: den Ball des Jungen.
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
    rules = BRIDGE_RULES if "bridge_course" in spec.path else BASE_RULES
    required = ", ".join(spec.required_terms)
    retry = ""
    if previous_errors:
        retry = (
            "\nPrevious attempt failed validation. Fix these errors:\n"
            + "\n".join(f"- {e}" for e in previous_errors)
            + "\n"
        )
    return f"""{rules}

File focus: {spec.focus}
Required terms: {required}
Notes: {spec.notes}
{retry}
Generate the file now.
"""


def validate_bridge(text: str, spec: FileSpec) -> list[str]:
    errors: list[str] = []

    if "[user]" in text or "[Ninereeds]" in text:
        errors.append("bridge files must not contain [user] or [Ninereeds] tags")
        return errors

    if re.search(r"^SECTION\b", text, re.MULTILINE):
        errors.append("file contains SECTION header labels; output only the content, not section labels")
        return errors

    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 8:
        errors.append(f"bridge file too short: {len(lines)} non-empty lines (need at least 8)")
        return errors

    # Section 1: first 4 non-empty lines = annotated block
    annotated = lines[:4]
    ann_text = "\n".join(annotated)

    has = {
        "actor":     bool(re.search(r"\([^)]+\)", ann_text)),
        "dative":    bool(re.search(r"\[[^\]]+\]", ann_text)),
        "accusative":bool(re.search(r"\{[^}]+\}", ann_text)),
        "genitive":  bool(re.search(r"<[^>]+>", ann_text)),
        "verb":      bool(re.search(r"\*[^*]+\*", ann_text)),
    }

    if not has["actor"]:
        errors.append("annotated block (first 4 lines) missing () actor bracket")
    if not has["dative"]:
        errors.append("annotated block (first 4 lines) missing [] dative bracket")
    if not has["verb"]:
        errors.append("annotated block (first 4 lines) missing ** verb marker")

    # Section 2: Q&A pairs — check presence matches annotated block
    q_patterns = {
        "actor":     re.compile(r"^\(Wer\s*/\s*Who\s*/", re.MULTILINE),
        "dative":    re.compile(r"^\[Wem\s*/\s*To whom\s*/", re.MULTILINE),
        "accusative":re.compile(r"^\{Was\s*/\s*What\s*/", re.MULTILINE),
        "genitive":  re.compile(r"^<Wessen\s*/\s*Whose\s*/", re.MULTILINE),
    }
    for role, pattern in q_patterns.items():
        in_ann = has[role]
        in_qa  = bool(pattern.search(text))
        if in_ann and not in_qa:
            errors.append(f"{role} bracket in annotated block but no role question found")
        if not in_ann and in_qa:
            errors.append(f"{role} role question found but bracket not in annotated block")

    # Section 3: last 4 non-empty lines = plain block (no brackets)
    plain_text = " ".join(lines[-4:])
    if re.search(r"[()[\]{}<>*]", plain_text):
        errors.append("plain block (last 4 lines) must not contain bracket markers ( ) [ ] { } < > *")

    # Answer line checks: ". / " is the multi-language separator
    for line in text.splitlines():
        if ". / " not in line:
            continue
        # EN answer is the first bracketed segment before the first ". /"
        m = re.match(r"^[(\[{<](.*?)[)\]}>]\.", line.strip())
        if not m:
            continue
        en_answer = m.group(1)
        # Uppercase article check
        if re.match(r"(The|A|An) [a-z]", en_answer):
            errors.append(
                f"English answer uses uppercase article — use lowercase: {en_answer!r}"
            )
        # German-in-EN-position check
        if re.search(r"^\s*(dem|der|des|den|die|das)\b", en_answer, re.I):
            errors.append(
                f"English answer position contains German article — check language order: {en_answer!r}"
            )

    # Simplified 给 in non-question lines (question lines end with ?)
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.endswith("?") or not stripped:
            continue
        if "给" in stripped:
            errors.append("Simplified 给 in non-question line; use Traditional 給")
            break

    # Required terms
    for term in spec.required_terms:
        if term.lower() not in text.lower():
            errors.append(f"missing required term: {term}")

    if re.search(r"[锤长扫车门书话马鸟鱼间园苹玛铅篮邻个]", text):
        errors.append("possible Simplified Chinese character found; use Traditional Chinese")
    if re.search(r"\b(She|He|They|We|she|he|they|we|Sie|Er|sie|er|彼女|彼|她|他|我們|我们)\b", text):
        errors.append("pronoun found; repeat the name or noun")

    return errors


def validate(text: str, spec: FileSpec) -> list[str]:
    if "bridge_course" in spec.path:
        return validate_bridge(text, spec)
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
    if "[/user]" in text or "[/Ninereeds]" in text:
        errors.append("closing tags are not allowed")
    if re.search(r"^(German|Japanese|Traditional Chinese|Chinese|English):", text, re.MULTILINE):
        errors.append("language labels are not allowed in response lines")
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
    if "_instrument_book" in spec.path and re.search(r"shows? with the book|zeigt mit dem Buch", text, re.I):
        errors.append("book files should use read/learn patterns, not show-with-book")
    if "_vehicle_airplane" in spec.path and re.search(r"\bfährt mit dem Flugzeug\b", text, re.I):
        errors.append("airplane files should use fliegt mit dem Flugzeug")
    if "_bei_" in spec.path and "01_means_dative_anchor" in spec.path:
        if re.search(r"\bbeim\b", text, re.I):
            errors.append("bei audit files should use full forms like bei dem / bei der, not contractions")
        if re.search(r"\b(go|goes|come|comes|travel|travels|move|moves|walk|walks|run|runs)\b", text, re.I):
            errors.append("bei audit files should stay static and avoid movement verbs in English")
        if re.search(r"\b(gehen|kommt|kommen|reist|reisen|läuft|laufen|fährt|fahren|bewegt|arbeitet)\b", text, re.I):
            errors.append("bei audit files should stay static and avoid movement verbs in German")
        if re.search(r"\b(行く|来る|歩く|走る|向かう|移動する)\b|去|來|走路|跑|前往|移動", text):
            errors.append("bei audit files should stay static and avoid movement verbs in Japanese or Chinese")
        if "_static" in spec.path and re.search(r"\b(wait|waits|work|works)\b|\b(wartet|arbeitet)\b|待つ|待って|働く|等待|工作", text):
            errors.append("bei static files should stay with is/sits/stands, not wait/work")
        if re.search(r"そばに待|そばに働|そばに勉強|ところに待|ところに座|ところに勉強", text):
            errors.append("bei audit files have a bad Japanese location particle for static activity")
    if "_aus_" in spec.path and "01_means_dative_anchor" in spec.path:
        if re.search(r"\baus das\b|\baus die\b|\baus den\b", text, re.I):
            errors.append("aus audit files must keep the German dative form")
        if re.search(r"\bbei\b|\bvon\b", text, re.I):
            errors.append("aus audit files should not drift into bei/von forms")
        if re.search(r"\b(by|near|at)\b", text, re.I):
            errors.append("aus audit files should keep source/out-of meaning, not nearby meaning")
        if re.search(r"そば|近く|旁邊", text):
            errors.append("aus audit files should keep source meaning, not nearby meaning")
        if re.search(r"\b(to|into|toward|onto)\b", text, re.I):
            errors.append("aus audit files should not drift into destination meaning")
        if "_window_" in spec.path and re.search(r"looks? out of|schaut aus dem Fenster|窓から見|窗戶裡看", text, re.I):
            errors.append("aus window audit file should stay with movement-out patterns")
        if "_window_" in spec.path and re.search(r"窓からよじ登|窓から登り出", text):
            errors.append("aus window audit file should use Japanese climb-out phrasing, not climb-up phrasing")
    if "_von_" in spec.path and "01_means_dative_anchor" in spec.path:
        if re.search(r"\bvom\b", text, re.I):
            errors.append("von audit files should use full forms like von dem / von der, not the contraction vom")
        if re.search(r"\baus dem\b|\baus der\b|\baus den\b", text, re.I):
            errors.append("von audit files should not drift into aus forms")
        if re.search(r"\bbei dem\b|\bbei der\b|\bbeim\b", text, re.I):
            errors.append("von audit files should not drift into bei forms")
        if re.search(r"\b(into|onto|toward|inside|out of)\b", text, re.I):
            errors.append("von audit files should keep source/from meaning, not destination or container meaning")
        if re.search(r"\b(belongs|owned|possesses|Besitz|gehört)\b|所有|屬於", text, re.I):
            errors.append("von audit files should keep source meaning, not ownership meaning")
        if re.search(r"そば|近く|旁邊", text):
            errors.append("von audit files should keep source meaning, not nearby meaning")
        if re.search(r"の中から|の中に", text):
            errors.append("von audit files should use surface or place-of-origin meaning, not interior container meaning")
    if "_zu_" in spec.path:
        if re.search(r"\bzum\b|\bzur\b", text, re.I):
            errors.append("zu audit files should use full forms like zu dem / zu der, not contractions zum or zur")
        if re.search(r"\bnach dem\b|\bnach der\b|\bnach den\b", text, re.I):
            errors.append("zu audit files should not drift into nach forms with article")
        if re.search(r"\bin die\b|\bin das\b|\bin den\b", text, re.I):
            errors.append("zu audit files should not drift into in-accusative endpoint forms")
        if re.search(r"\baus dem\b|\baus der\b|\bvon dem\b|\bvon der\b|\bbei dem\b|\bbei der\b", text, re.I):
            errors.append("zu audit files should not drift into aus/von/bei forms")
        if re.search(r"\b(is at|sits at|stands at|waits at)\b", text, re.I):
            errors.append("zu audit files should keep movement-toward meaning, not static location")
        if re.search(r"\bsteht bei\b|\bsitzt bei\b|\bist bei\b", text, re.I):
            errors.append("zu audit files should keep movement-toward meaning, not static bei location")
        if re.search(r"にいる|にある|のそばに", text):
            errors.append("zu audit files should keep movement-toward meaning in Japanese, not static forms")
        if re.search(r"[锤长扫车门书话马鸟鱼间园]", text):
            errors.append("possible Simplified Chinese character found; use Traditional Chinese")
    if "_nach_" in spec.path:
        if re.search(r"\bzum\b|\bzur\b", text, re.I):
            errors.append("nach audit files should not use zu contractions zum or zur")
        if re.search(r"\bzu dem\b|\bzu der\b|\bbei dem\b|\bbei der\b|\baus dem\b|\baus der\b|\bvon dem\b|\bvon der\b", text, re.I):
            errors.append("nach audit files should not drift into zu/bei/aus/von dative forms")
        if re.search(r"\bin die\b|\bin das\b|\bin den\b", text, re.I):
            errors.append("nach audit files should not drift into in-accusative endpoint forms")
        if "_city_" in spec.path or "_direction_" in spec.path or "_hause_" in spec.path:
            if re.search(r"\bnach dem\b|\bnach der\b|\bnach den\b", text, re.I):
                errors.append("nach city and direction files should use bare name form, not nach dem or nach der")
            if re.search(r"\b(is in|is at|sits in|stands in|lives in)\b|\bwohnt in\b|\bist in\b|\bist bei\b|\bliegt in\b", text, re.I):
                errors.append("nach city/direction files should keep movement-toward meaning, not static location")
        if "_hause_" in spec.path:
            if re.search(r"\bnach dem Haus\b", text, re.I):
                errors.append("nach Hause files should use the fixed phrase nach Hause, not nach dem Haus")
            if re.search(r"\bzu Hause\b|\bzuhause\b", text, re.I):
                errors.append("nach Hause files should not use the static zu Hause form")
        if "_temporal_" in spec.path:
            if not re.search(r"\bnach dem\b|\bnach der\b", text, re.I):
                errors.append("nach temporal files should contain nach dem or nach der dative form")
            if re.search(r"\bflies to\b|\btravels to\b|\btakes? (a flight|the train|the bus) to\b", text, re.I):
                errors.append("nach temporal files should keep time/after meaning, not place-destination movement")
    if "_seit_" in spec.path:
        if re.search(r"\bnach dem\b|\bnach der\b|\bnach den\b", text, re.I):
            errors.append("seit files should not drift into nach temporal forms")
        if re.search(r"\bzu dem\b|\bzu der\b|\bbei dem\b|\bbei der\b|\baus dem\b|\baus der\b|\bvon dem\b|\bvon der\b", text, re.I):
            errors.append("seit files should not drift into zu/bei/aus/von dative forms")
        if not re.search(r"\bseit dem\b|\bseit der\b", text, re.I):
            errors.append("seit files should contain seit dem or seit der dative form")
        if re.search(r"\b(goes to|walks to|travels to|flies to|after)\b", text, re.I):
            errors.append("seit files should keep since/ongoing-duration meaning, not after-sequence or destination meaning")
    if "_gegenueber_" in spec.path:
        if re.search(r"\bbei dem\b|\bbei der\b|\bbeim\b", text, re.I):
            errors.append("gegenüber files should not drift into bei nearby forms")
        if re.search(r"\bneben dem\b|\bneben der\b", text, re.I):
            errors.append("gegenüber files should keep opposite meaning, not next-to meaning")
        if re.search(r"\b(go|goes|come|comes|walk|walks|run|runs|travel|travels)\b", text, re.I):
            errors.append("gegenüber files should stay static and avoid movement verbs in English")
        if re.search(r"\b(gehen|kommt|kommen|läuft|laufen|fährt|fahren|geht)\b", text, re.I):
            errors.append("gegenüber files should stay static and avoid movement verbs in German")
        if re.search(r"\b(行く|来る|歩く|走る|向かう)\b|去|走路|跑|前往", text):
            errors.append("gegenüber files should stay static and avoid movement verbs in Japanese or Chinese")
        if not re.search(r"\bgegenüber dem\b|\bgegenüber der\b", text, re.I):
            errors.append("gegenüber files should contain gegenüber dem or gegenüber der dative form")
    if "02_receiver_dative" in spec.path:
        if re.search(r"\b(goes to|walks to|runs to|flies to|travels to)\b", text, re.I):
            errors.append("receiver dative files should not use movement-toward verbs")
        if re.search(r"\baus dem\b|\baus der\b|\bbei dem\b|\bbei der\b", text, re.I):
            errors.append("receiver dative files should not drift into aus/bei source or nearby forms")
        if re.search(r"\bzum\b|\bzur\b|\bbeim\b|\bvom\b", text, re.I):
            errors.append("receiver dative files should use full dative forms, not contractions")
        if not re.search(r"\bdem \w|\bder \w", text):
            errors.append("receiver dative files must contain a visible dative article dem or der")
    if "03_place_static_dative" in spec.path:
        # Accusative forms signal movement — ban them
        if re.search(r"\bin die\b|\bin das\b|\bin den\b", text, re.I):
            errors.append("place static dative: in-accusative (in die/das/den) signals movement — keep in dem/in der")
        if re.search(r"\bauf die\b|\bauf das\b|\bauf den\b", text, re.I):
            errors.append("place static dative: auf-accusative (auf die/das/den) signals movement — keep auf dem/auf der")
        for _prep in ("unter", "über", "neben", "vor", "hinter"):
            if re.search(rf"\b{_prep} die\b|\b{_prep} das\b", text, re.I):
                errors.append(f"place static dative: {_prep}-accusative signals movement — keep dative form")
        if re.search(r"\bzwischen die\b", text, re.I):
            errors.append("place static dative: zwischen-accusative signals movement — keep dative form")
        # Movement verbs
        if re.search(r"\b(puts|places|sets down|goes into|walks into|steps onto|climbs onto|crawls under)\b", text, re.I):
            errors.append("place static dative: movement verb found — use static verbs only (is/sits/lies/stands/hangs)")
        if re.search(r"\b(stellt|legt|geht in|geht auf|läuft in|klettert auf|kriecht unter|setzt sich auf)\b", text, re.I):
            errors.append("place static dative: German movement verb found — use static verbs (ist/sitzt/liegt/steht/hängt)")
        # Must have a two-way preposition in dative form
        if not re.search(
            r"\b(auf dem|auf der|in dem|in der|über dem|über der|unter dem|unter der|"
            r"neben dem|neben der|vor dem|vor der|hinter dem|hinter der|zwischen dem|zwischen der|zwischen den)\b",
            text, re.I,
        ):
            errors.append("place static dative: must contain a two-way preposition in dative form")

    if "05_object_accusative_patient" in spec.path:
        if not re.search(r"を", text):
            errors.append("object_accusative files must contain Japanese を particle marking the direct object")
        if not re.search(r"\bden \w+|\bdie \w+|\bdas \w+", text):
            errors.append("object_accusative files must contain a visible German accusative article (den/die/das + noun)")
        if re.search(r"\bwird\b", text, re.I):
            errors.append("object_accusative files should not use werden (state-change belongs to 04_change_state)")
        if re.search(r"\b(gibt|zeigt|bringt|schickt|leiht|hilft|antwortet|erzählt)\b", text, re.I):
            errors.append("object_accusative files should not use ditransitive or pure-dative verbs from receiver_dative cluster")
    if "04_change_state" in spec.path:
        if not re.search(r"\bwird\b", text, re.I):
            errors.append("change_state files must contain wird (state-change copula)")
        if re.search(r"\b(goes|walks|runs|moves|falls|climbs|jumps|travels)\b", text, re.I):
            errors.append("change_state files should not use movement verbs in English")
        if re.search(r"\b(geht|läuft|rennt|bewegt|fällt|klettert|springt|reist)\b", text, re.I):
            errors.append("change_state files should not use movement verbs in German")
        if re.search(r"\bin die\b|\bin das\b|\bin den\b|\bauf die\b|\bauf das\b|\bauf den\b", text, re.I):
            errors.append("change_state files should not use movement prepositions (in/auf + accusative)")
        if re.search(r"\b(is at|goes to|walks to|runs to|travels to)\b", text, re.I):
            errors.append("change_state files should use state-change meaning only, not destination meaning")

    if "06_target_accusative_endpoint" in spec.path:
        # Must have a two-way preposition in accusative form
        if not re.search(
            r"\b(in den|in die|in das|auf den|auf die|auf das"
            r"|über den|über die|über das|unter den|unter die|unter das"
            r"|neben den|neben die|neben das|vor den|vor die|vor das"
            r"|hinter den|hinter die|hinter das|zwischen den|zwischen die|zwischen das)\b",
            text, re.I,
        ):
            errors.append(
                "target_accusative files must contain a two-way preposition with accusative article "
                "(in den/die/das, auf den/die/das, etc.)"
            )
        # Must not contain dative forms of two-way prepositions
        if re.search(
            r"\b(im\b|in dem\b|auf dem\b|über dem\b|unter dem\b"
            r"|neben dem\b|vor dem\b|hinter dem\b|zwischen dem\b"
            r"|auf der\b|in der\b|über der\b|unter der\b"
            r"|neben der\b|vor der\b|hinter der\b|zwischen der\b)",
            text, re.I,
        ):
            errors.append(
                "target_accusative files must not use dative forms of two-way prepositions "
                "(im/auf dem/in der etc.) — use accusative (in den/die/das, auf den/die/das)"
            )
        # Must have a movement or placement verb
        if not re.search(
            r"\b(geht|läuft|rennt|legt|stellt|setzt|hängt|bringt|kriecht|trägt|geht|fährt"
            r"|goes|walks|runs|places|puts|sets|hangs|brings|crawls|carries)\b",
            text, re.I,
        ):
            errors.append(
                "target_accusative files must contain a movement or placement verb "
                "(gehen, laufen, legen, stellen, setzen, hängen, bringen, kriechen)"
            )

    if "07_place_target_contrast" in spec.path:
        # Must contain a dative two-way preposition (static location)
        if not re.search(
            r"\b(auf dem|auf der|in dem|in der|im\b|über dem|über der"
            r"|unter dem|unter der|neben dem|neben der"
            r"|vor dem|vor der|hinter dem|hinter der"
            r"|zwischen dem|zwischen der)\b",
            text, re.I,
        ):
            errors.append(
                "contrast files must contain a dative two-way preposition "
                "(auf dem/auf der/in dem/in der/im etc.) for the static location pairs"
            )
        # Must contain an accusative two-way preposition (movement endpoint)
        if not re.search(
            r"\b(in den|in die|in das|auf den|auf die|auf das"
            r"|über den|über die|über das|unter den|unter die|unter das"
            r"|neben den|neben die|neben das|vor den|vor die|vor das"
            r"|hinter den|hinter die|hinter das|zwischen den|zwischen die|zwischen das)\b",
            text, re.I,
        ):
            errors.append(
                "contrast files must contain an accusative two-way preposition "
                "(auf den/die/das, in den/die/das, etc.) for the movement endpoint pairs"
            )
        # Must have both a static verb and a placement/movement verb
        if not re.search(
            r"\b(ist|sind|liegt|steht|hängt|sitzt|is|lies|stands|hangs|sits)\b",
            text, re.I,
        ):
            errors.append(
                "contrast files must contain a static verb (ist/liegt/steht/hängt/sitzt) "
                "for the static location pairs"
            )
        if not re.search(
            r"\b(geht|läuft|rennt|legt|stellt|setzt|hängt|bringt|kriecht|trägt|fährt"
            r"|goes|walks|runs|places|puts|sets|brings|crawls|carries)\b",
            text, re.I,
        ):
            errors.append(
                "contrast files must contain a movement or placement verb "
                "(stellen/legen/gehen/bringen etc.) for the endpoint pairs"
            )

    if "08_source_path_destination" in spec.path:
        # Must contain a source preposition (aus, von, vom)
        if not re.search(
            r"\b(aus dem\b|aus der\b|aus dem\b|vom\b|von dem\b|von der\b|von Emma\b|von Taro\b|von Gran\b)",
            text, re.I,
        ):
            errors.append(
                "source_path_destination files must contain a source preposition "
                "(aus dem/der, vom, von dem/der)"
            )
        # Must not use Simplified Chinese characters
        simplified_chars = "给苹玛铅篮邻个来说"
        if any(ch in text for ch in simplified_chars):
            errors.append(
                "source_path_destination files must use Traditional Chinese, not Simplified"
            )

    if "09_owner_genitive" in spec.path:
        # Must contain a possession marker (name-s, von+dative, or des/der genitive)
        if not re.search(
            r"\b(Emmas\b|Taros\b|Grans\b|Biscuits\b"
            r"|von Emma\b|von Taro\b|von Gran\b"
            r"|von dem\b|von der\b|vom\b"
            r"|des Hauses\b|des Baumes\b|des Kindes\b|des Mannes\b|des Hundes\b|des Gartens\b"
            r"|der Frau\b|der Schule\b|der Küche\b|Wessen\b)",
            text, re.I,
        ):
            errors.append(
                "owner_genitive files must contain a possession form "
                "(name-s possessive, von+dative, des/der genitive, or Wessen)"
            )
        # Must contain の in JP lines
        if "の" not in text:
            errors.append(
                "owner_genitive files must contain の in the Japanese lines"
            )
        # Must not use Simplified Chinese
        simplified_chars = "给苹玛铅篮邻个来说"
        if any(ch in text for ch in simplified_chars):
            errors.append(
                "owner_genitive files must use Traditional Chinese, not Simplified"
            )

    if "10_review_stories" in spec.path:
        # Must not use Simplified Chinese
        simplified_chars = "给苹玛铅篮邻个来说"
        if any(ch in text for ch in simplified_chars):
            errors.append(
                "review_stories files must use Traditional Chinese, not Simplified"
            )
        # Must contain at least one German case marker (dative or accusative)
        if not re.search(
            r"\b(dem\b|der\b|den\b|des\b|die\b|das\b)",
            text, re.I,
        ):
            errors.append(
                "review_stories files must contain German article forms "
                "(dem/der/den/des/die/das)"
            )

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
