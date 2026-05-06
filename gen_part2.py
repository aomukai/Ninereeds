import json, os, re

phase6_dir = "training_data/phases/phase_6"
dg_file = "training_data/dependency_graph.json"
nodes = json.load(open(dg_file, "r"))["nodes"]
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

# route
wf(1158, "route", "[Ninereeds]This is a route.", "route", [
    {"q": "what does route look like?", "b": ["Route is a path.", "Route has turns.", "Route has stops.", "Route is a line.", "Route is a road."], "s": "Route is a path with turns and stops."},
    {"q": "where is route?", "b": ["Route is on a map.", "Route is through land.", "Route is between towns.", "Route is near hills.", "Route is over ground."], "s": "Route is on a map between towns."},
    {"q": "what does route do?", "b": ["Route goes from place.", "Route goes to place.", "Route bends at hills.", "Route crosses a river.", "Route ends at a town."], "s": "Route goes from place to town."},
    {"q": "what does route give?", "b": ["Route shows the way.", "Route guides travel.", "Route links two towns.", "Route helps trade.", "Route carries people."], "s": "Route shows the way and links towns."},
])

# rule
wf(1159, "rule", "[Ninereeds]This is a rule.", "rule", [
    {"q": "what does rule look like?", "b": ["Rule is a law.", "Rule has words.", "Rule has points.", "Rule is a guide.", "Rule is a line."], "s": "Rule is a law with words and points."},
    {"q": "where is rule?", "b": ["Rule is in a book.", "Rule is at school.", "Rule is at work.", "Rule is with a game.", "Rule is at home."], "s": "Rule is in a book at school."},
    {"q": "what does rule do?", "b": ["Rule tells what is right.", "Rule tells what is wrong.", "Rule keeps order.", "Rule stays the same.", "Rule holds form."], "s": "Rule tells what is right and keeps order."},
    {"q": "what does rule give?", "b": ["Rule gives order.", "Rule keeps peace.", "Rule guides play.", "Rule holds fair.", "Rule helps people."], "s": "Rule gives order and helps people."},
])

# sale
wf(1160, "sale", "[Ninereeds]This is a sale.", "sale", [
    {"q": "what does sale look like?", "b": ["Sale is a deal.", "Sale has goods.", "Sale has a price.", "Sale is an event.", "Sale is a swap."], "s": "Sale is a deal with goods and a price."},
    {"q": "where is sale?", "b": ["Sale is at a store.", "Sale is in a shop.", "Sale is by a door.", "Sale is at market.", "Sale is on a street."], "s": "Sale is at a store at market."},
    {"q": "what does sale do?", "b": ["Sale starts at a time.", "Sale draws a crowd.", "Sale moves goods.", "Sale drops price.", "Sale ends at close."], "s": "Sale drops price and draws a crowd."},
    {"q": "what does sale give?", "b": ["Sale gives new goods.", "Sale gives low price.", "Sale gives deals.", "Sale moves stock.", "Sale helps a shop."], "s": "Sale gives low price and moves stock."},
])

# snapshot
wf(1161, "snapshot", "[Ninereeds]This is a snapshot.", "snapshot", [
    {"q": "what does snapshot look like?", "b": ["Snapshot is a photo.", "Snapshot is quick.", "Snapshot is a shot.", "Snapshot has light.", "Snapshot has a frame."], "s": "Snapshot is a quick photo with a frame."},
    {"q": "where is snapshot?", "b": ["Snapshot is in a camera.", "Snapshot is on a phone.", "Snapshot is at home.", "Snapshot is on a wall.", "Snapshot is in a book."], "s": "Snapshot is in a camera on a phone."},
    {"q": "what does snapshot do?", "b": ["Snapshot captures a moment.", "Snapshot holds a view.", "Snapshot stops time.", "Snapshot saves light.", "Snapshot keeps a scene."], "s": "Snapshot captures a moment and saves a scene."},
    {"q": "what does snapshot give?", "b": ["Snapshot shows a memory.", "Snapshot shares a view.", "Snapshot gives a record.", "Snapshot keeps a face.", "Snapshot holds a place."], "s": "Snapshot shows a memory and holds a place."},
])

print("Words 2-5 done")
