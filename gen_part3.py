import json, os, re

phase6_dir = "training_data/phases/phase_6"
dg_file = "training_data/dependency_graph.json"
dg = json.load(open(dg_file, "r"))
nodes = dg["nodes"]
processed = []

def wf(n, word, open_line, qword, blocks):
    fname = "phase_6_%d.md" % n
    fp = os.path.join(phase6_dir, fname).replace("\\", "/")
    parts = []
    for b in blocks:
        part = [
            "[user]%s" % b["q"],
            open_line,
            b["b"][0],
            b["b"][1],
            b["b"][2],
            b["b"][3],
            b["b"][4],
            b["s"]
        ]
        parts.append("\n".join(part))
    open(fp, "w").write("\n\n".join(parts))
    nodes[fp] = {"path": fp, "kind": "phase"}
    processed.append((word, fname))
    print(fname)

# soccer
wf(1162, "soccer", "[Ninereeds]This is soccer.", "soccer", [
    {"q": "what does soccer look like?", "b": ["Soccer is a game.", "Soccer is a sport.", "Soccer has a ball.", "Soccer has a field.", "Soccer has a goal."], "s": "Soccer is a game with a ball and a goal."},
    {"q": "where is soccer?", "b": ["Soccer is on a field.", "Soccer is in a park.", "Soccer is at a court.", "Soccer is near homes.", "Soccer is in a league."], "s": "Soccer is on a field in a park."},
    {"q": "what does soccer do?", "b": ["Soccer has a kick.", "Soccer has a pass.", "Soccer has a goal.", "Soccer has a team.", "Soccer has a match."], "s": "Soccer has a kick and a pass and a goal."},
    {"q": "what does soccer give?", "b": ["Soccer gives fun.", "Soccer gives sport.", "Soccer gives play.", "Soccer builds teams.", "Soccer builds skill."], "s": "Soccer gives fun and builds teams."},
])

# sport
wf(1163, "sport", "[Ninereeds]This is a sport.", "sport", [
    {"q": "what does sport look like?", "b": ["Sport is a game.", "Sport is active.", "Sport has a ball.", "Sport has a net.", "Sport has a field."], "s": "Sport is an active game with a field."},
    {"q": "where is sport?", "b": ["Sport is in a gym.", "Sport is on a field.", "Sport is in a pool.", "Sport is at a park.", "Sport is at a rink."], "s": "Sport is in a gym or on a field."},
    {"q": "what does sport do?", "b": ["Sport has a run.", "Sport has a throw.", "Sport has a catch.", "Sport has a jump.", "Sport has a swing."], "s": "Sport has a run and a throw and a jump."},
    {"q": "what does sport give?", "b": ["Sport gives health.", "Sport gives fitness.", "Sport gives fun.", "Sport builds strength.", "Sport builds teamwork."], "s": "Sport gives health and builds strength."},
])

# storybook
wf(1164, "storybook", "[Ninereeds]This is a storybook.", "storybook", [
    {"q": "what does storybook look like?", "b": ["Storybook is a book.", "Storybook has words.", "Storybook has art.", "Storybook has a cover.", "Storybook is a tale."], "s": "Storybook is a book with words and art."},
    {"q": "where is storybook?", "b": ["Storybook is on a shelf.", "Storybook is in a room.", "Storybook is at school.", "Storybook is at home.", "Storybook is in a bag."], "s": "Storybook is on a shelf at home."},
    {"q": "what does storybook do?", "b": ["Storybook tells a tale.", "Storybook has pictures.", "Storybook holds a plot.", "Storybook shows a scene.", "Storybook ends a chapter."], "s": "Storybook tells a tale and shows a scene."},
    {"q": "what does storybook give?", "b": ["Storybook gives wonder.", "Storybook gives dreams.", "Storybook gives fun.", "Storybook teaches lessons.", "Storybook builds knowledge."], "s": "Storybook gives wonder and teaches lessons."},
])

# tale
wf(1165, "tale", "[Ninereeds]This is a tale.", "tale", [
    {"q": "what does tale look like?", "b": ["Tale is a story.", "Tale has a plot.", "Tale has a hero.", "Tale has a villain.", "Tale has an ending."], "s": "Tale is a story with a plot and a hero."},
    {"q": "where is tale?", "b": ["Tale is in a book.", "Tale is at a campfire.", "Tale is on a page.", "Tale is at bedtime.", "Tale is in a scroll."], "s": "Tale is in a book at bedtime."},
    {"q": "what does tale do?", "b": ["Tale has a beginning.", "Tale has a middle.", "Tale has drama.", "Tale has actions.", "Tale has a moral."], "s": "Tale has a beginning and a middle and a moral."},
    {"q": "what does tale give?", "b": ["Tale gives wonder.", "Tale gives insight.", "Tale teaches values.", "Tale holds memory.", "Tale shares wisdom."], "s": "Tale gives wonder and teaches values."},
])

# ten
wf(1166, "ten", "[Ninereeds]This is ten.", "ten", [
    {"q": "what does ten look like?", "b": ["Ten is a number.", "Ten has two digits.", "Ten has a one.", "Ten has a zero.", "Ten is round."], "s": "Ten is a number with two digits."},
    {"q": "where is ten?", "b": ["Ten is on a clock.", "Ten is on a page.", "Ten is in a row.", "Ten is on a hand.", "Ten is in math."], "s": "Ten is on a clock and in math."},
    {"q": "what does ten do?", "b": ["Ten counts things.", "Ten holds place.", "Ten follows nine.", "Ten comes before eleven.", "Ten is in a decade."], "s": "Ten counts things and follows nine."},
    {"q": "what does ten give?", "b": ["Ten gives a count.", "Ten makes a group.", "Ten forms a set.", "Ten fills a box.", "Ten gives a pack."], "s": "Ten gives a count and makes a group."},
])

# token
wf(1167, "token", "[Ninereeds]This is a token.", "token", [
    {"q": "what does token look like?", "b": ["Token is a piece.", "Token is small.", "Token is round.", "Token is flat.", "Token is a chip."], "s": "Token is a small round piece."},
    {"q": "where is token?", "b": ["Token is in a pocket.", "Token is in a purse.", "Token is on a desk.", "Token is at a game.", "Token is by a door."], "s": "Token is in a pocket or on a desk."},
    {"q": "what does token do?", "b": ["Token stands for value.", "Token holds a turn.", "Token marks a place.", "Token serves as coin.", "Token works for access."], "s": "Token stands for value and marks a place."},
    {"q": "what does token give?", "b": ["Token gives access.", "Token gives a turn.", "Token shows value.", "Token plays a part.", "Token holds a spot."], "s": "Token gives access and holds a spot."},
])

# TRUE
wf(1168, "TRUE", "[Ninereeds]This is a true.", "true", [
    {"q": "what does true look like?", "b": ["True is a word.", "True is a state.", "True is a fact.", "True is a sign.", "True is a yes."], "s": "True is a word that is a yes."},
    {"q": "where is true?", "b": ["True is in a book.", "True is on a page.", "True is on a sign.", "True is in speech.", "True is in a code."], "s": "True is in a book on a page."},
    {"q": "what does true do?", "b": ["True says what is real.", "True says what is right.", "True matches facts.", "True holds to truth.", "True stays the same."], "s": "True says what is real and matches facts."},
    {"q": "what does true give?", "b": ["True gives truth.", "True gives fact.", "True gives proof.", "True shows real.", "True builds trust."], "s": "True gives truth and shows what is real."},
])

# Save dep graph
json.dump(dg, open(dg_file, "w"), indent=2, ensure_ascii=False)

# Clear words file
open('training_data/phases/phase_6_words.txt', "w").close()

# Append to progress
for word, fname in processed:
    open('training_data/dependency_graph_progress.txt', "a").write("%s -> %s\n" % (word, fname))

print("ALL_DONE:%d" % len(processed))
