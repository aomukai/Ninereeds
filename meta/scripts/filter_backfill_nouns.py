"""
Filter backfill noun candidates down to wiki-eligible words.
Criterion: can you write 2-4 coherent sentences that describe the concept?
"""

import re

PROPER_NAMES = {
    "alice","anne","arlo","billy","boyd","cade","caleb","chloe","clara",
    "cody","dean","ella","emma","eric","faye","greg","gwen","hugh","jack",
    "jace","jade","joel","jude","june","kent","liam","luke","mason","max",
    "nash","nina","noah","nora","ninereed","oliver","owen","phil","phoebe",
    "roman","ruth","ryan","seth","skye","sophie","tate","toby","troy",
    "vera","willa","wilson","zeno",
}

CODE_ARTIFACTS = {
    "nltk","openai","pathlib","polyglot","spacy","textblob","tagger",
    "tokenization","tokenize","tokenizer","wordfreq","wordnet","dedupe",
    "deduplicated","stdin","exec","traceback","traceability","codex",
    "normalization","normalize","normalized","normalizing","offloading",
    "subcategorization","lemma","workflow","workbench","tagger","spacy",
    "subcase","snippet","pathlib","preserf","serf","sery","cand","carf",
    "clas","chao","bles","sud","flatbed","flier","fluttery","go-kart",
    "click-clack","pitter-pattering","entry-level","open-house",
    "childcaregiver","cross-examining","dedupe","deduplicated","default",
    "exec","filtered","filtering","standalone","stdin","textblob",
    "transformer","polyglot","wordnet","wordfreq","tagger","traceback",
}

# Words that are inflected forms — past tense, past participle, comparative, etc.
# Keep base forms; drop inflected ones when the base is also in the list or is obvious
INFLECTED_AND_JUNK = {
    # past tense / past participle
    "accepted","achieved","amazed","appreciated","arranged","arrived","ate",
    "attached","became","believed","belonged","bent","blew","bought","built",
    "came","carried","caught","changed","chose","closed","decided","dipped",
    "expanded","fallen","felt","figured","filtered","found","gave","gone",
    "got","grown","hugged","hung","intended","knew","laid","liked","planned",
    "promised","sat","said","seemed","seen","selected","spent","stirred",
    "stood","stuck","swept","swung","taken","taught","told","took","tried",
    "understood","went","woke","wrapped",
    # comparative / superlative adjective forms
    "brighter","colder","easier","farther","gentler","hotter","louder",
    "safer","tidier","truer","warmer","calmer",
    # gerunds mislabeled as nouns
    "baking","classifying","computing","digging","dropping","filtering",
    "normalizing","running","slipping","swimming","tapping","wagging",
    "wrapping","pitter-pattering","cross-examining","turn-taking",
    # adverbs / pronouns / particles mislabeled
    "anymore","anyone","anywhere","everyone","myself","none","once","someone",
    "someday","somewhere","whatever","whenever","yourself","instead","later",
    "next","other","somewhere",
    # verb infinitives with no noun sense in context
    "adhere","adjust","agree","allow","appear","argue","arrive","ask","attach",
    "bake","become","believe","belong","bend","breathe","breed","buy",
    "celebrate","choose","classify","come","compute","confuse","consider",
    "contain","continue","decide","decrease","depend","describe","discover",
    "dislike","drink","enter","evaluate","explain","explore","feel","feed",
    "follow","forget","forgive","go","grab","grow","ignore","imagine","imply",
    "import","include","increase","irritate","isolate","live","locate","look",
    "maintain","make","mean","mention","miss","need","organize","pour","predict",
    "prefer","prepare","protect","provide","put","scurry","seem","speak",
    "spend","suggest","take","thank","understand","use","wander","warn","write",
    # truncated / malformed
    "brightnes","celsiu","chao","completenes","consciousnes","correctnes",
    "curiou","darknes","definitenes","deliciou","forgivenes","incorrectnes",
    "indefinitenes","mattres","metamorphosi","nervou","othernes","politenes",
    "preserf","rudenes","sicknes","soundnes","tirednes","unsoundnes","wellnes",
    # other noise
    "aggregate","affordance","baseline","causal","cohesive","comparative",
    "compute","conservative","deduplicated","deficit","dynamic","educational",
    "enumerate","entry-level","exec","extract","extracted","final","forth",
    "grep","halfway","install","installed","intro","kindly","known","local",
    "lowercase","measurer","minus","mode","module","nltk","none","novelty",
    "nudge","once","openai","operation","outlet","overlap","peaceful","pin",
    "plop","polite","provisional","regex","rudder","sanity","saturday",
    "scope","script","secure","separator","serf","session","sole","spacy",
    "stdin","status","store","symbolic","temporal","threshold","tint","tier",
    "twice","type","universal","unlike","unwell","use","used","user",
    "verbose","wiki","wordfreq","wordnet","workbench","workflow","x-ray",
    # names/brands
    "greek","roman",
}

def keep(word):
    if word in PROPER_NAMES:
        return False
    if word in CODE_ARTIFACTS:
        return False
    if word in INFLECTED_AND_JUNK:
        return False
    # hyphenated noise
    if word.count('-') > 1:
        return False
    # single letters or very short noise
    if len(word) <= 2:
        return False
    # truncated words (end in consonant cluster that looks wrong)
    if re.search(r'(nes|tnes|nes|gnes|dnes|pnes|rnes|snes|tnes)$', word) and not word.endswith('ness'):
        return False
    return True

with open('/home/aomukai/Ninereeds/tmp/bp_nouns_final.txt') as f:
    words = [w.strip() for w in f if w.strip()]

kept = [w for w in words if keep(w)]
dropped = [w for w in words if not keep(w)]

print(f"Input:   {len(words)}")
print(f"Kept:    {len(kept)}")
print(f"Dropped: {len(dropped)}")

with open('/home/aomukai/Ninereeds/tmp/backfill_nouns_wiki_candidates.txt', 'w') as f:
    f.write('\n'.join(kept) + '\n')

print("\n--- DROPPED (spot-check) ---")
for w in sorted(dropped)[:40]:
    print(f"  {w}")
