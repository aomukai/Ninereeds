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
    "01_means_dative_anchor_bei_audit": make_bei_audit_specs(),
    "01_means_dative_anchor_aus_audit": make_aus_audit_specs(),
    "01_means_dative_anchor_von_audit": make_von_audit_specs(),
    "01_means_dative_anchor_zu_audit": make_zu_audit_specs(),
    "01_means_dative_anchor_nach_audit": make_nach_audit_specs(),
    "01_means_dative_anchor_seit_audit": make_seit_specs(),
    "01_means_dative_anchor_gegenueber_audit": make_gegenueber_specs(),
    "02_receiver_dative": make_receiver_dative_specs(),
    "03_place_static_dative": make_place_static_dative_specs(),
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
    if "_bei_" in spec.path:
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
    if "_aus_" in spec.path:
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
    if "_von_" in spec.path:
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
