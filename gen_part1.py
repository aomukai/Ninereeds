import json, os, re

phase6_dir = "training_data/phases/phase_6"
dg_file = "training_data/dependency_graph.json"
progress_file = "training_data/dependency_graph_progress.txt"
words_file = "training_data/phases/phase_6_words.txt"

next_num = 1157
with open(dg_file, "r") as f: dg = json.load(f)
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
    content = "\n\n".join(parts)
    open(fp, "w").write(content)
    nodes[fp] = {"path": fp, "kind": "phase"}
    processed.append((word, fname))
    print(fname)

wf(1157, "role", "[Ninereeds]This is a role.", "role", [
    {"q": "what does role look like?", "b": ["Role is a job.", "Role has a name.", "Role has tasks.", "Role has duties.", "Role is a part."], "s": "Role is a job with tasks and a name."},
    {"q": "where is role?", "b": ["Role is in a group.", "Role is at work.", "Role is in a scene.", "Role is with people.", "Role is at a place."], "s": "Role is in a group at a place."},
    {"q": "what does role do?", "b": ["Role does work.", "Role has tasks.", "Role plays a part.", "Role stays in place.", "Role works with people."], "s": "Role does work and plays a part."},
    {"q": "what does role give?", "b": ["Role gives order.", "Role gives form.", "Role gives shape.", "Role helps people.", "Role guides a scene."], "s": "Role gives order and helps people."},
])
print("OK")
