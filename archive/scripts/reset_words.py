import json, re, os

words_file = 'training_data/phases/phase_6_words.txt'
dg_file = 'training_data/dependency_graph.json'
progress_file = 'training_data/dependency_graph_progress.txt'
phase6_dir = 'training_data/phases/phase_6'

words = ['role', 'route', 'rule', 'sale', 'snapshot', 'soccer', 'sport', 'storybook', 'tale', 'ten', 'token', 'TRUE']

# Remove last 12 lines from progress
with open(progress_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()
if len(lines) >= 12:
    lines = lines[:-12]
else:
    lines = []
with open(progress_file, 'w', encoding='utf-8') as f:
    f.writelines(lines)

# Put words back
with open(words_file, 'w', encoding='utf-8') as f:
    for w in words:
        f.write(w + '\n')

# Remove graph nodes
with open(dg_file, 'r', encoding='utf-8') as f:
    dg = json.load(f)
nodes = dg['nodes']
for n in range(1145, 1157):
    key = f'phase_6_{n}.md'
    full = f'{phase6_dir}/{key}'
    if full in nodes:
        del nodes[full]
with open(dg_file, 'w', encoding='utf-8') as f:
    json.dump(dg, f, indent=2, ensure_ascii=False)

print(f'Reset. {len(words)} words restored, graph entries removed.')
