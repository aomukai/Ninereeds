#!/usr/bin/env python3
"""Extract vocabulary from pending reasoning files and update vocab/ files."""

from pathlib import Path
import re

reasoning_dir = Path("D:/Ninereeds/training_data/reasoning")
vocab_dir = reasoning_dir / "vocab"
progress_path = reasoning_dir / "progress_reasoning_words.txt"

# ===== KNOWN WORD LISTS =====
function_words = {
    "a","an","the","this","that","these","those","it","its","i","me","my","mine",
    "myself","you","your","yours","yourself","he","him","his","himself","she","her",
    "hers","herself","we","us","our","ours","ourselves","they","them","their","theirs",
    "themselves","who","whom","whose","which","what","whatever","whoever",
    "is","am","are","was","were","be","been","being","have","has","had","having",
    "do","does","did","doing","done","will","would","can","could","shall","should",
    "may","might","must","not","no","nor","and","but","or","yet","so","for",
    "if","then","else","in","on","at","to","by","with","from","of","about","into",
    "through","during","above","below","between","under","over","out","off","up","down",
    "as","each","few","just","like","more","most","much","one","only","other","own",
    "per","same","some","such","than","too","two","very","also","even","first","last",
    "many","still","well","because","every","long","both","else","near","next","old",
    "once","since","until","without","always","away","go","going","gone","came","come",
    "good","great","keep","know","known","leave","left","little","look","mean","might",
    "move","need","never","own","part","right","said","see","seem","set","show","side",
    "tell","think","thought","three","time","us","use","used","want","went","year",
    "big","call","called","change","coming","course","different","done","end","enough",
    "far","felt","follow","full","gave","getting","give","given","got","group","hand",
    "head","help","high","home","idea","important","keep","kept","kind","large","later",
    "lead","life","line","live","lived","living","lot","man","may","men","name","new",
    "open","people","person","place","point","question","quite","rather","read","real",
    "really","room","small","soon","stand","start","sure","thing","things","together",
    "told","top","toward","try","turn","upon","value","want","within","without","word",
    "words","work","worked","working","world","would","write","yes","now","then","here",
    "there","before","after","above","below","inside","outside","later","earlier","soon",
    "today","tomorrow","yesterday","always","never","sometimes","often","usually",
    "there","been","both","can","cannot","comes","done","doesn","don","every","few",
    "get","gets","getting","goes","going","gone","got","having","let","lets","made",
    "make","making","may","might","much","must","need","needs","needing","non",
    "nothing","off","onto","ought","put","puts","putting","quite","rather","said",
    "says","shall","since","something","still","such","take","takes","taking",
    "taken","than","that","these","those","through","too","unto","upon","used",
    "uses","using","very","was","well","went","were","what","whatever","when",
    "where","whether","which","while","who","whoever","whom","whose","will",
    "with","within","without","would","yes","yet","already","also","although",
    "amid","among","anyway","back","because","become","becomes","becoming",
}

skip_words = {str(i) for i in range(100)}
skip_words.update({
    "one","two","three","four","five","six","seven","eight","nine","ten",
    "eleven","twelve","thirteen","fourteen","fifteen","sixteen","seventeen","eighteen",
    "nineteen","twenty","thirty","forty","fifty","sixty","seventy","eighty","ninety",
    "hundred","thousand","plus","minus","times","divided","equals","equal","zero",
    "first","second","third","fourth","fifth","sixth","seventh","eighth","ninth","tenth",
    "num","nums","digit","digits",
})

# Known nouns
known_nouns = set()
nouns_file = vocab_dir / "nouns.txt"
if nouns_file.exists():
    for line in nouns_file.read_text().splitlines():
        line = line.strip().lower()
        if line:
            known_nouns.add(line)

known_nouns.update({
    "successor","contradiction","story","stories","mode","symbol","symbols",
    "chain","chains","word","number","numbers","object","objects","quantity",
    "quantities","invitation","nothing","result","order","size","side","step",
    "value","task","total","trip","story","piece","place","seat","seed","shop",
    "sign","stone","store","table","tank","theater","thing","time","toy","tree",
    "triangle","wire","work","rest","ground","half","group","friend","fruit",
    "fur","girl","part","bird","ball","bag","apple","animal","answer","amount",
    "balloon","banana","basket","book","bowl","box","boy","branch","cake",
    "calculation","candy","car","card","cat","chair","child","chocolate","color",
    "cookie","corner","cup","cupcake","dog","dollar","duck","eye","farmer","finger",
    "fish","flour","kitten","lemon","letter","lettuce","lime","marble","page",
    "pencil","person","pet","plant","plate","pond","potato","row","shoe","square",
    "worm","toy","duck","pond","cookies","sun","sky","night","day","ball","box",
    "inside","morning","child","children","boy","girl","men","women","man","woman",
    "decrease","increase","group","change","addition","subtraction","multiplication",
    "division","thing","things","idea","ideas","way","ways","end","ends","day","days",
    "home","person","people","world","life","part","parts","hand","hands","head",
    "water","food","air","ground","tree","trees","house","door","window","room",
    "bed","table","chair","floor","wall","roof","garden","yard","street","road",
    "friend","friends","family","mother","father","sister","brother","baby","child",
    "children","name","game","toy","toys","ball","book","song","picture","line",
    "sound","smell","taste","touch","color","shape","size","number","letter",
    "word","sentence","page","cover","title","author","school","class","teacher",
    "student","lesson","homework","test","answer","question","problem","solution",
    "rule","reason","cause","effect","difference","similarity","pattern","order",
    "time","minute","hour","week","month","year","season","spring","summer","fall",
    "winter","weather","rain","snow","wind","sun","cloud","sky","star","moon",
    "earth","ground","field","hill","mountain","river","lake","ocean","sea","wave",
    "sand","rock","stone","plant","flower","tree","leaf","branch","root","seed",
    "fruit","vegetable","animal","bird","fish","insect","mammal","cat","dog","horse",
    "cow","sheep","pig","chicken","duck","goose","rabbit","mouse","rat","bat","bear",
    "deer","fox","wolf","body","head","face","eye","ear","nose","mouth","tooth",
    "tongue","neck","shoulder","arm","hand","finger","thumb","leg","foot","toe",
    "knee","elbow","back","chest","stomach","skin","bone","muscle","heart","lung",
    "brain","blood","health","illness","medicine","doctor","nurse","hospital",
    "kitchen","food","meal","bread","rice","meat","fish","egg","milk","cheese",
    "butter","oil","sugar","salt","pepper","soup","salad","fruit","apple","banana",
    "orange","grape","berry","lemon","lime","vegetable","carrot","potato","tomato",
    "corn","bean","pea","onion","garlic","cookie","cake","pie","candy","chocolate",
    "water","juice","tea","coffee","cup","glass","plate","bowl","fork","knife",
    "spoon","pot","pan","oven","stove","sink","table","chair","bed","lamp","clock",
    "mirror","towel","soap","brush","comb","toothbrush","toothpaste","bath","shower",
    "toilet","door","window","wall","floor","roof","stairs","hall","room","bedroom",
    "bathroom","kitchen","living room","garage","basement","attic","yard","fence",
    "gate","path","driveway","sidewalk","street","road","highway","bridge","tunnel",
    "car","truck","bus","train","plane","boat","ship","bike","motorcycle","wheel",
    "tire","engine","fuel","gas","oil","light","horn","seat","belt","helmet",
    "map","trip","journey","travel","visit","stop","start","turn","direction",
    "north","south","east","west","left","right","front","back","top","bottom",
    "side","corner","edge","center","middle","inside","outside","surface","line",
    "row","column","list","set","group","pair","bunch","pile","stack","heap","load",
    "piece","bit","chunk","slice","drop","pinch","dash","cup","pound","ounce",
    "inch","foot","yard","mile","meter","centimeter","kilogram","gram","liter",
    "dozen","pair","half","quarter","third","whole","total","sum","difference",
    "product","quotient","remainder","count","number","numeral","digit","figure",
    "value","amount","quantity","measure","size","length","width","height","depth",
    "weight","volume","area","capacity","speed","rate","frequency","distance",
    "temperature","degree","scale","level","point","mark","grade","score","rank",
    "position","place","location","site","spot","area","region","zone","district",
    "neighborhood","community","city","town","village","country","state","nation",
    "world","earth","globe","map","chart","graph","table","diagram","drawing",
    "picture","photo","image","portrait","sketch","outline","plan","design",
    "pattern","model","copy","original","version","edition","form","shape","figure",
    "circle","square","triangle","rectangle","oval","sphere","cube","cone","cylinder",
    "line","curve","angle","arc","point","dot","spot","mark","stripe","band",
    "color","shade","tint","tone","hue","brightness","darkness","light","shadow",
    "cat","cats","dog","dogs","duck","ducks","worm","worms","toy","toys",
})

# Known verbs
known_verbs = set()
verbs_file = vocab_dir / "verbs.txt"
if verbs_file.exists():
    text = verbs_file.read_text().strip()
    for w in re.split(r"[, ]+", text):
        w = w.strip().lower()
        if w:
            known_verbs.add(w)

known_verbs.update({
    "add","subtract","multiply","divide","increase","decrease","give","take",
    "put","get","make","use","find","tell","ask","work","seem","feel","try",
    "leave","call","keep","let","begin","show","hear","play","run","move","live",
    "believe","bring","happen","write","sit","stand","lose","pay","meet","include",
    "continue","set","learn","change","lead","understand","watch","follow","stop",
    "create","speak","read","allow","spend","grow","walk","win","offer","remember",
    "love","consider","appear","buy","wait","serve","die","send","expect","build",
    "stay","fall","cut","reach","kill","remain","suggest","raise","pass","sell",
    "require","report","decide","pull","develop","carry","receive","agree","support",
    "explain","produce","eat","accept","publish","enjoy","describe","afford","refuse",
    "avoid","wish","test","dream","imagine","exist","suffer","care","matter","prove",
    "depend","share","compare","extend","resemble","shape","affect","connect","differ",
    "relate","point","match","express","communicate","interpret","fly","see","look",
    "know","think","eat","sleep","have","hide","hold","mean","roll","pour","fill",
    "open","close","drop","catch","walk","count","try","carry","live","love","use",
    "work","want","seem","call","begin","show","hear","play","run","move","bring",
    "write","stand","lose","pay","meet","include","lead","follow","create","speak",
    "allow","spend","offer","remember","appear","buy","wait","serve","send","expect",
    "stay","fall","reach","remain","suggest","raise","pass","sell","require","report",
    "decide","pull","receive","agree","support","explain","produce","accept","refuse",
    "wish","test","dream","imagine","exist","suffer","prove","depend","share",
    "compare","extend","connect","differ","point","match","express",
    "communicate","interpret","need","help","like","wake","go","come","make",
    "give","take","find","tell","ask",
})

# Known adjectives
known_adj = set()
adj_file = vocab_dir / "adjectives.txt"
if adj_file.exists():
    text = adj_file.read_text().strip()
    for w in re.split(r"[, ]+", text):
        w = w.strip().lower()
        if w:
            known_adj.add(w)

known_adj.update({
    "red","blue","green","yellow","orange","purple","pink","black","white","gray",
    "brown","big","small","large","little","tall","short","long","wide","narrow",
    "hot","cold","warm","cool","empty","full","clean","dirty","wet","dry","new",
    "old","good","bad","happy","sad","angry","scared","brave","sleeping","awake",
    "bright","dark","same","different","free","stuck","smooth","rough","soft","hard",
    "fast","slow","loud","quiet","heavy","light","thick","thin","deep","shallow",
    "correct","wrong","true","false","available","great","matching","vanilla",
    "chocolate","every","single","double","triple","several","special","usual",
    "normal","strange","simple","complex","clear","certain","next","last",
})


def singularize(w):
    w = w.lower()
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("ves") and len(w) > 4:
        return w[:-3] + "f"
    if w.endswith("sses"):
        return w[:-2]
    if w.endswith("ches") or w.endswith("shes") or w.endswith("xes") or w.endswith("zes"):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        return w[:-1]
    return w


def verb_base(w):
    w = w.lower()
    irr = {
        "was":"be","were":"be","been":"be","being":"be",
        "had":"have","has":"have","having":"have",
        "did":"do","done":"do","does":"do","doing":"do",
        "said":"say","says":"say","saying":"say",
        "made":"make","makes":"make","making":"make",
        "went":"go","goes":"go","gone":"go","going":"go",
        "came":"come","comes":"come","coming":"come",
        "took":"take","takes":"take","taken":"take","taking":"take",
        "got":"get","gets":"get","getting":"get",
        "knew":"know","knows":"know","known":"know",
        "saw":"see","sees":"see","seen":"see","seeing":"see",
        "gave":"give","gives":"give","given":"give","giving":"give",
        "felt":"feel","feels":"feel","feeling":"feel",
        "told":"tell","tells":"tell","telling":"tell",
        "thought":"think","thinks":"think","thinking":"think",
        "found":"find","finds":"find","finding":"find",
        "meant":"mean","means":"mean","meaning":"mean",
        "left":"leave","leaves":"leave","leaving":"leave",
        "kept":"keep","keeps":"keep","keeping":"keep",
        "began":"begin","begun":"begin","begins":"begin","beginning":"begin",
        "brought":"bring","brings":"bring","bringing":"bring",
        "built":"build","builds":"build","building":"build",
        "spoke":"speak","spoken":"speak","speaks":"speak","speaking":"speak",
        "wrote":"write","written":"write","writes":"write","writing":"write",
        "ran":"run","runs":"run","running":"run",
        "sat":"sit","sits":"sit","sitting":"sit",
        "stood":"stand","stands":"stand","standing":"stand",
        "led":"lead","leads":"lead","leading":"lead",
        "sent":"send","sends":"send","sending":"send",
        "ate":"eat","eats":"eat","eating":"eat",
        "slept":"sleep","sleeps":"sleep","sleeping":"sleep",
        "hid":"hide","hides":"hide","hiding":"hide",
        "held":"hold","holds":"hold","holding":"hold",
        "woke":"wake","wakes":"wake","waking":"wake",
        "rolled":"roll","rolls":"roll","rolling":"roll",
        "poured":"pour","pours":"pour","pouring":"pour",
        "filled":"fill","fills":"fill","filling":"fill",
        "opened":"open","opens":"open","opening":"open",
        "closed":"close","closes":"close","closing":"close",
        "dropped":"drop","drops":"drop","dropping":"drop",
        "caught":"catch","catches":"catch","catching":"catch",
        "walked":"walk","walks":"walk","walking":"walk",
        "flew":"fly","flies":"fly","flying":"fly",
        "counted":"count","counts":"count","counting":"count",
        "showed":"show","shows":"show","showing":"show",
        "tried":"try","tries":"try","trying":"try",
        "carried":"carry","carries":"carry","carrying":"carry",
        "lived":"live","lives":"live","living":"live",
        "loved":"love","loves":"love","loving":"love",
        "used":"use","uses":"use","using":"use",
        "worked":"work","works":"work","working":"work",
        "wanted":"want","wants":"want","wanting":"want",
        "looked":"look","looks":"look","looking":"look",
        "seemed":"seem","seems":"seem","seeming":"seem",
    }
    if w in irr:
        return irr[w]
    if w.endswith("ing"):
        base = w[:-3]
        if len(base) > 2 and base[-1] == base[-2]:
            base = base[:-1]
        return base if base else w
    if w.endswith("ed"):
        base = w[:-2]
        if base.endswith("i"):
            return base[:-1] + "y"
        if len(base) > 2 and base[-1] == base[-2]:
            base = base[:-1]
        return base if base else w
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("es"):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        return w[:-1]
    return w


def classify_word(w):
    w = w.lower().strip(".,;:!?()\"'-")
    if not w or len(w) < 2 or w in function_words or w in skip_words:
        return None
    if any(c.isdigit() for c in w):
        return None
    if "'" in w:
        return None

    singular = singularize(w)
    vb = verb_base(w)

    # Check known lists
    if singular in known_nouns or w in known_nouns:
        return ("noun", singular if singular != w else w)
    if vb in known_verbs or w in known_verbs:
        return ("verb", vb)
    if w in known_adj:
        return ("adj", w)
    if singular in known_adj:
        return ("adj", singular)

    # Heuristic: noun suffixes
    if w.endswith("tion") or w.endswith("sion") or w.endswith("ment"):
        return ("noun", w)
    if w.endswith("ness") or w.endswith("ity") or w.endswith("ance"):
        return ("noun", w)
    if w.endswith("ence") or w.endswith("ship") or w.endswith("dom"):
        return ("noun", w)

    # Heuristic: adverb -> adjective
    if w.endswith("ly") and len(w) > 3:
        adj_form = w[:-2]
        if adj_form and adj_form not in function_words:
            return ("adj", adj_form)

    # Heuristic: verb forms
    if w.endswith("ing") or w.endswith("ed"):
        if vb != w and vb not in function_words:
            return ("verb", vb)

    # Comparative/superlative -> adjective
    if w.endswith("er") and len(w) > 3:
        return ("adj", w)
    if w.endswith("est") and len(w) > 3:
        return ("adj", w)

    # Default: noun
    return ("noun", singular)


# ===== LOAD STATE =====
done = set()
if progress_path.exists():
    for line in progress_path.read_text().splitlines():
        line = line.strip()
        if line.endswith(".md"):
            done.add(line)

all_md = sorted([p.name for p in reasoning_dir.glob("*.md")])
pending = [f for f in all_md if f not in done]

processed_files = []
new_nouns = set()
new_verbs = set()
new_adjs = set()

# ===== PROCESS EACH FILE =====
for fname in sorted(pending):
    file_path = reasoning_dir / fname
    text = file_path.read_text(encoding="utf-8")

    words = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("---"):
            continue
        if stripped.startswith("Symbolic Mode:") or stripped.startswith("```"):
            continue
        if stripped.startswith("```"):
            continue
        if re.match(r"^[\d\s+\-*/=.]*$", stripped):
            continue
        if stripped.startswith("[user]") or stripped.startswith("[Ninereeds]"):
            # Remove speaker tags
            stripped = re.sub(r"^\[(user|Ninereeds)\]\s*", "", stripped)
        for w in re.findall(r"[a-zA-Z]+(?:'[a-zA-Z]+)?", stripped):
            w = w.lower()
            if w not in function_words and w not in skip_words and len(w) > 1:
                words.add(w)

    for w in words:
        result = classify_word(w)
        if result:
            cat, normalized = result
            if normalized not in function_words and len(normalized) > 1 and normalized not in skip_words:
                if cat == "noun":
                    new_nouns.add(normalized)
                elif cat == "verb":
                    new_verbs.add(normalized)
                elif cat == "adj":
                    new_adjs.add(normalized)

    processed_files.append(fname)

# ===== MERGE AND WRITE =====
all_nouns = known_nouns | new_nouns
all_verbs = known_verbs | new_verbs
all_adjs = known_adj | new_adjs

# Write updated vocab files
nouns_file.write_text("\n".join(sorted(all_nouns)) + "\n", encoding="utf-8")
verbs_file.write_text(", ".join(sorted(all_verbs)) + "\n", encoding="utf-8")
adj_file.write_text(", ".join(sorted(all_adjs)) + "\n", encoding="utf-8")

# Append to progress file
with progress_path.open("a", encoding="utf-8") as f:
    for fname in sorted(processed_files):
        f.write(fname + "\n")

# ===== REPORT =====
print(f"Files processed: {len(processed_files)}")
print(f"New nouns: {len(new_nouns - known_nouns)}")
print(f"New verbs: {len(new_verbs - known_verbs)}")
print(f"New adjectives: {len(new_adjs - known_adj)}")
print(f"Total nouns: {len(all_nouns)}")
print(f"Total verbs: {len(all_verbs)}")
print(f"Total adjectives: {len(all_adjs)}")
print()

if new_nouns - known_nouns:
    print("Sample new nouns:", sorted(new_nouns - known_nouns)[:20])
if new_verbs - known_verbs:
    print("Sample new verbs:", sorted(new_verbs - known_verbs)[:20])
if new_adjs - known_adj:
    print("Sample new adjs:", sorted(new_adjs - known_adj)[:20])
print()
print("RECEIPT")
print("-------")
print(f"Files processed this run: {processed_files}")
print(f"Progress ledger last entry: {processed_files[-1] if processed_files else '(none)'}")
print(f"Output file record count (nouns): {len(all_nouns)}")
print(f"Output file record count (verbs): {len(all_verbs)}")
print(f"Output file record count (adjectives): {len(all_adjs)}")
print(f"Files remaining: {len(all_md) - len(done) - len(processed_files)}")
print(f"Status: DONE")
