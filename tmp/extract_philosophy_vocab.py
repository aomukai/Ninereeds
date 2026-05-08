"""Extract content words from a philosophy dialogue file."""
import re, sys

FILE = "training_data/philosophy/ninereeds_dialogues_cat9.md"

with open(FILE, encoding="utf-8") as f:
    text = f.read()

# Remove speaker tags
text = re.sub(r'\[STATEMENT\]|\[USER\]|\[NINEREEDS\]', '', text)
# Remove heading markers and numbers
text = re.sub(r'#+', '', text)
text = re.sub(r'\(#[0-9]+\)', '', text)
# Remove standalone numbers
text = re.sub(r'\b[0-9]+\b', '', text)
# Remove punctuation except apostrophes
text = re.sub(r'[^\w\s\'-]', ' ', text)
# Remove extra whitespace
text = re.sub(r'\s+', ' ', text).strip().lower()

# Split into words
raw_words = text.split()

# Stop words and function words to filter
stop_words = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
    'may', 'might', 'can', 'shall', 'must', 'need',
    'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
    'my', 'your', 'his', 'its', 'our', 'their', 'mine', 'yours', 'hers', 'ours', 'theirs',
    'this', 'that', 'these', 'those',
    'and', 'or', 'but', 'if', 'because', 'so', 'than', 'as', 'while', 'though', 'although',
    'not', 'no', 'nor', 'neither',
    'in', 'on', 'at', 'to', 'for', 'with', 'by', 'from', 'of', 'about', 'into', 'through', 'during',
    'before', 'after', 'above', 'below', 'between', 'under', 'over', 'out', 'off', 'up', 'down',
    'isn\'t', 'aren\'t', 'wasn\'t', 'weren\'t', 'don\'t', 'doesn\'t', 'didn\'t', 'won\'t', 'wouldn\'t',
    'can\'t', 'couldn\'t', 'shouldn\'t', 'mightn\'t', 'mustn\'t',
    'itself', 'yourself', 'myself', 'themselves', 'himself', 'herself', 'ourselves',
    'very', 'just', 'also', 'too', 'only', 'even', 'still', 'yet', 'already', 'always', 'never',
    'here', 'there', 'everywhere', 'somewhere', 'anywhere', 'nowhere',
    'now', 'then', 'again', 'often', 'sometimes', 'usually',
    'all', 'each', 'every', 'both', 'few', 'more', 'most', 'some', 'any', 'much', 'many',
    'other', 'another', 'same', 'different',
    'what', 'which', 'who', 'whom', 'whose', 'how', 'why', 'when', 'where',
    'one', 'two', 'three', 'four', 'five', 'first', 'second', 'third',
    'thing', 'things', 'something', 'anything', 'everything', 'nothing',
    'way', 'ways', 'kind', 'kinds', 'sort', 'sorts', 'type', 'types',
    'part', 'parts', 'place', 'places', 'time', 'times',
    'well', 'really', 'actually', 'essentially', 'entirely',
    'since', 'until', 'unless', 'whether', 'except', 'without',
    'ago', 'ever', 'never', 'once', 'twice',
    'though', 'although', 'however', 'therefore', 'thus',
    'say', 'said', 'says', 'go', 'went', 'gone', 'goes',
    'see', 'saw', 'seen', 'sees', 'look', 'looks', 'looked',
    'make', 'makes', 'made', 'making',
    'take', 'takes', 'took', 'taken', 'taking',
    'get', 'gets', 'got', 'gotten', 'getting',
    'come', 'comes', 'came', 'coming',
    'give', 'gives', 'gave', 'given', 'giving',
    'put', 'puts', 'putting',
    'let', 'lets', 'letting',
    'keep', 'keeps', 'kept', 'keeping',
    'set', 'sets', 'setting',
    'seem', 'seems', 'seemed', 'seeming',
    'feel', 'feels', 'felt', 'feeling',
    'mean', 'means', 'meant', 'meaning',
    'know', 'knows', 'knew', 'known', 'knowing',
    'think', 'thinks', 'thought', 'thinking',
    'find', 'finds', 'found', 'finding',
    'show', 'shows', 'showed', 'shown', 'showing',
    'try', 'tries', 'tried', 'trying',
    'ask', 'asks', 'asked', 'asking',
    'need', 'needs', 'needed', 'needing',
    'want', 'wants', 'wanted', 'wanting',
    'tell', 'tells', 'told', 'telling',
    'help', 'helps', 'helped', 'helping',
    'work', 'works', 'worked', 'working',
    'call', 'calls', 'called', 'calling',
    'begin', 'begins', 'began', 'begun', 'beginning',
    'hold', 'holds', 'held', 'holding',
    'turn', 'turns', 'turned', 'turning',
    'follow', 'follows', 'followed', 'following',
    'change', 'changes', 'changed', 'changing',
    'start', 'starts', 'started', 'starting',
    'move', 'moves', 'moved', 'moving',
    'like', 'likely', 'unlikely',
    'long', 'longer', 'longest',
    'well', 'better', 'best',
    'bad', 'worse', 'worst',
    'good', 'better', 'best',
    'little', 'less', 'least',
    'small', 'smaller', 'smallest',
    'large', 'larger', 'largest',
    'big', 'bigger', 'biggest',
    'high', 'higher', 'highest',
    'low', 'lower', 'lowest',
    'old', 'older', 'oldest',
    'new', 'newer', 'newest',
    'close', 'closer', 'closest',
    'far', 'farther', 'farthest',
    'near', 'nearer', 'nearest',
    'late', 'later', 'latest',
    'soon', 'sooner', 'soonest',
    'early', 'earlier', 'earliest',
    'hard', 'harder', 'hardest',
    'easy', 'easier', 'easiest',
    'simple', 'simpler', 'simplest',
    'clear', 'clearer', 'clearest',
    'sure', 'surer', 'surest',
    'exact', 'exacter', 'exactest',
    'right', 'righter', 'rightest',
    'wrong', 'wronger', 'wrongest',
    'true', 'truer', 'truest',
    'real', 'realer', 'realest',
    'possible', 'impossible',
    'necessary', 'unnecessary',
    'common', 'commoner', 'commonest',
    'important', 'unimportant',
    'different', 'indifferent',
    'certain', 'uncertain',
    'particular',
    'general', 'generally',
    'specific', 'specifically',
    'usual', 'usually', 'unusual',
    'normal', 'normally', 'abnormal',
    'special', 'especially',
    'main', 'mainly',
    'basic', 'basically',
    'direct', 'directly', 'indirect',
    'able', 'unable', 'ability',
    'full', 'fully',
    'sure', 'surely',
    'maybe', 'perhaps',
    'quite', 'pretty',
    'almost', 'nearly',
    'enough', 'sufficient',
    'forward', 'backward', 'upward', 'downward',
    'inside', 'outside',
    'together', 'apart',
    'around', 'along', 'across',
    'back', 'forth',
    'away', 'aside',
    'every', 'everything', 'everyone', 'everywhere',
    'some', 'somewhat', 'somewhere', 'someone', 'somebody',
    'any', 'anyone', 'anybody', 'anywhere', 'anything',
    'no', 'none', 'nobody', 'nothing', 'nowhere',
    'else', 'instead',
}

# Temporal/spatial words to exclude per prompt instructions
ts_words = {'now', 'then', 'here', 'there', 'before', 'after', 'above', 'below', 'inside', 'outside'}

all_words = [w for w in raw_words if w not in stop_words and w not in ts_words and len(w) > 1 and w.isalpha()]

# Manual categorization
nouns = set()
verbs = set()
adjs = set()

# Nouns (things, concepts, entities)
nouns_raw = [
    'number', 'reality', 'apple', 'chair', 'day', 'world', 'mind',
    'count', 'counting', 'relationship', 'result', 'sun',
    'triangle', 'line', 'angle', 'degree', 'side',
    'structure', 'fiction', 'proof', 'bridge', 'building', 'navigation',
    'system', 'graphic', 'grip',
    'category', 'edge', 'case', 'unit', 'choice', 'boundary',
    'skin', 'piece', 'person', 'door', 'friend', 'problem',
    'infinity', 'quantity', 'property', 'absence', 'end',
    'process', 'distance', 'duration', 'concept', 'image',
    'temperature', 'direction', 'force', 'invention', 'situation',
    'reference', 'point', 'measurement', 'scale', 'position',
    'coordinate', 'map', 'statement', 'rule', 'contradiction',
    'century', 'truth', 'confidence', 'history',
    'division', 'algebra', 'computing', 'tool', 'symbol',
    'discovery', 'probability', 'chance', 'coin', 'knowledge',
    'level', 'particle', 'information', 'nature', 'decision',
    'gap', 'matter', 'sum', 'amount', 'space', 'movement',
    'mathematics', 'geometry', 'arithmetic', 'physics', 'quantum',
    'mathematician', 'physicist', 'human', 'language', 'word',
    'question', 'answer', 'location',
    'paradox', 'framework', 'application',
    'pattern', 'material', 'arrangement', 'test',
    'puzzle', 'insight', 'grain', 'sand', 'beach',
    'drawer', 'computer',
    'signal', 'alignment', 'starting', 'version',
    'foot', 'step', 'half', 'quarter',
    'mathematician', 'physicist', 'user', 'ninereeds',
    'thought', 'century', 'decade', 'year',
    'heads', 'tails',
    'rock', 'stone', 'pile',
    'debt', 'freezing', 'water',
    'greek', 'roman', 'numeral',
    'symbol', 'hand', 'page',
    'gathering', 'combination',
    'incompleteness', 'confidence',
    'uncertainty', 'randomness',
    'quantum', 'particle', 'electron',
    'decision', 'framework',
    'definiteness', 'indefiniteness',
    'confusion', 'clarity',
    'existence', 'nonexistence',
    'inside', 'outside',
    'room', 'drawer',
    'ship', 'bridge',
    'group', 'membership',
    'relation', 'relatedness',
    'discovery', 'invention',
    'knower', 'known',
    'dream', 'reality',
    'appearance', 'essence',
    'subject', 'object',
    'observer', 'observed',
    'measurement', 'measurer',
    'absolute', 'relative',
    'basis', 'foundation',
    'assumption', 'presupposition',
    'implication', 'consequence',
    'context', 'background',
    'horizon', 'limit', 'horizon',
    'series', 'sequence',
    'multiplicity', 'unity',
    'identity', 'difference',
    'sameness', 'otherness',
    'similarity', 'dissimilarity',
    'analogy', 'metaphor',
    'example', 'instance',
    'whole', 'part',
    'member', 'set', 'class',
    'collection', 'aggregate',
    'quality', 'attribute', 'property',
    'feature', 'characteristic',
    'dimension', 'aspect',
    'element', 'component',
    'connection', 'link',
    'dependence', 'independence',
    'determination', 'indetermination',
    'precision', 'accuracy',
    'correctness', 'incorrectness',
    'validity', 'invalidity',
    'soundness', 'unsoundness',
]

for w in nouns_raw:
    # Normalize to singular
    if w.endswith('ies') and len(w) > 4:
        w = w[:-3] + 'y'
    elif w.endswith('ses') or w.endswith('xes') or w.endswith('ches') or w.endswith('shes'):
        w = w[:-2]
    elif w.endswith('s') and not w.endswith('ss') and len(w) > 2:
        w = w[:-1]
    nouns.add(w)

# Verbs (base form)
verbs_raw = [
    'point', 'write', 'live', 'add', 'get', 'count', 'exist',
    'find', 'describe', 'discover', 'prove', 'apply', 'measure',
    'name', 'mean', 'think', 'know', 'work', 'predict', 'fit',
    'grow', 'behave', 'depend', 'decide', 'require', 'impose',
    'recognize', 'treat', 'give', 'hold', 'picture', 'visualize',
    'imagine', 'understand', 'use', 'change', 'remove', 'notice',
    'participate', 'observe', 'test', 'dismiss', 'call',
    'build', 'develop', 'explore', 'invent', 'create',
    'derive', 'capture', 'reach', 'frame', 'demonstrate',
    'suggest', 'leave', 'connect', 'step', 'cross',
    'zoom', 'move', 'pass', 'settle', 'argue', 'resolve',
    'gather', 'combine', 'form', 'behave',
    'subtract', 'multiply', 'divide', 'equal',
    'define', 'express', 'represent', 'signify',
    'contain', 'include', 'comprise', 'consist',
    'produce', 'generate', 'yield', 'result',
    'continue', 'proceed', 'advance',
    'appear', 'disappear', 'vanish',
    'remain', 'stay', 'abide',
    'follow', 'precede', 'succeed',
    'correspond', 'match', 'align',
    'differ', 'vary', 'distinguish',
    'identify', 'classify', 'characterize',
    'infer', 'deduce', 'conclude',
    'assume', 'presuppose', 'postulate',
    'verify', 'confirm', 'validate',
    'refute', 'falsify', 'disprove',
    'perceive', 'sense', 'discern',
    'conceive', 'conceptualize', 'formulate',
    'abstract', 'generalize', 'particularize',
    'compare', 'contrast', 'relate',
    'separate', 'divide', 'distinguish',
    'unite', 'merge', 'combine',
    'order', 'arrange', 'organize',
    'found', 'establish', 'ground',
    'transcend', 'exceed', 'surpass',
    'limit', 'restrict', 'constrain',
    'determine', 'condition', 'shape',
    'reflect', 'mirror', 'express',
    'mediate', 'negotiate', 'bridge',
    'oscillate', 'vibrate', 'fluctuate',
    'synthesize', 'integrate', 'unify',
    'differentiate', 'specify', 'concretize',
    'verbalize', 'articulate', 'utter',
    'engage', 'interact', 'communicate',
    'negate', 'deny', 'reject',
    'affirm', 'assert', 'declare',
    'question', 'doubt', 'wonder',
    'respond', 'reply', 'answer',
    'challenge', 'contest', 'oppose',
    'support', 'defend', 'justify',
    'clarify', 'elucidate', 'explain',
    'interpret', 'read', 'understand',
    'translate', 'convert', 'transform',
    'emerge', 'arise', 'occur',
    'collapse', 'break', 'shatter',
    'converge', 'diverge', 'branch',
    'rotate', 'revolve', 'spin',
    'attract', 'repel', 'pull',
    'push', 'press', 'force',
    'carry', 'bring', 'transport',
    'receive', 'accept', 'take',
    'offer', 'present', 'provide',
    'share', 'distribute', 'spread',
    'focus', 'concentrate', 'center',
    'expand', 'extend', 'stretch',
    'contract', 'shrink', 'compress',
    'fold', 'unfold', 'bend',
    'break', 'split', 'fracture',
]

for w in verbs_raw:
    # Normalize to base form (already base for most)
    verbs.add(w)

# Adjectives/adverbs
adjs_raw = [
    'real', 'true', 'strange', 'perfect', 'abstract', 'physical',
    'mathematical', 'continuous', 'infinite', 'negative', 'positive',
    'uncertain', 'random', 'complete', 'consistent', 'certain',
    'solid', 'deep', 'obvious', 'powerful', 'useful', 'fictional',
    'practical', 'pure', 'genuine', 'precise', 'meaningful',
    'confident', 'honest', 'intelligent', 'ancient', 'conceptual',
    'undetermined', 'finite', 'continuous',
    'absolute', 'relative', 'subjective', 'objective',
    'necessary', 'contingent', 'possible', 'impossible',
    'universal', 'particular', 'general', 'specific',
    'abstract', 'concrete', 'material', 'immaterial',
    'spiritual', 'mental', 'physical', 'corporeal',
    'temporal', 'eternal', 'permanent', 'temporary',
    'static', 'dynamic', 'stable', 'unstable',
    'simple', 'complex', 'complicated', 'sophisticated',
    'clear', 'confused', 'distinct', 'vague',
    'direct', 'indirect', 'immediate', 'mediated',
    'primary', 'secondary', 'fundamental', 'derivative',
    'essential', 'accidental', 'intrinsic', 'extrinsic',
    'logical', 'illogical', 'rational', 'irrational',
    'ordinary', 'extraordinary', 'common', 'rare',
    'similar', 'identical', 'distinct', 'different',
    'equal', 'unequal', 'equivalent', 'comparable',
    'empty', 'full', 'complete', 'incomplete',
    'open', 'closed', 'bounded', 'unbounded',
    'transparent', 'opaque', 'visible', 'invisible',
    'aware', 'unaware', 'conscious', 'unconscious',
    'deliberate', 'accidental', 'intentional', 'unintentional',
    'natural', 'artificial', 'organic', 'mechanical',
    'original', 'derivative', 'novel', 'familiar',
    'significant', 'trivial', 'important', 'negligible',
    'central', 'peripheral', 'marginal', 'core',
    'formal', 'informal', 'structural', 'superficial',
    'empirical', 'theoretical', 'practical', 'speculative',
    'analytic', 'synthetic', 'deductive', 'inductive',
    'probable', 'improbable', 'likely', 'unlikely',
    'definite', 'indefinite', 'determinate', 'indeterminate',
    'knowable', 'unknowable', 'intelligible', 'unintelligible',
    'sensible', 'intellectual', 'rational', 'emotional',
    'intuitive', 'discursive', 'immediate', 'mediated',
    'naive', 'sophisticated', 'primitive', 'developed',
    'raw', 'refined', 'crude', 'polished',
    'sharp', 'blunt', 'keen', 'dull',
    'narrow', 'broad', 'deep', 'shallow',
    'heavy', 'light', 'dense', 'sparse',
    'fast', 'slow', 'rapid', 'gradual',
    'rough', 'smooth', 'coarse', 'fine',
    'tight', 'loose', 'firm', 'weak',
    'rich', 'poor', 'plentiful', 'scarce',
    'simple', 'elaborate', 'plain', 'ornate',
    'inner', 'outer', 'interior', 'exterior',
    'internal', 'external', 'intrinsic', 'extrinsic',
    'prior', 'posterior', 'previous', 'subsequent',
    'simultaneous', 'sequential', 'synchronous', 'asynchronous',
    'actual', 'potential', 'virtual', 'ideal',
    'apparent', 'real', 'seeming', 'genuine',
    'illusory', 'genuine', 'false', 'genuine',
    'true', 'false', 'valid', 'invalid',
    'correct', 'incorrect', 'right', 'wrong',
    'accurate', 'inaccurate', 'precise', 'imprecise',
    'typical', 'atypical', 'normal', 'abnormal',
    'symmetric', 'asymmetric', 'balanced', 'unbalanced',
    'linear', 'nonlinear', 'circular', 'spiral',
]

for w in adjs_raw:
    # Normalize adverbs to adjective form (already mostly adjectives)
    adjs.add(w)

# Read current vocab files
def read_vocab(path):
    try:
        with open(path, encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()

existing_verbs = read_vocab('training_data/philosophy/verbs.txt')
existing_adjs = read_vocab('training_data/philosophy/adjectives.txt')
existing_nouns = read_vocab('training_data/philosophy/nouns.txt')

new_verbs = verbs - existing_verbs
new_adjs = adjs - existing_adjs
new_nouns = nouns - existing_nouns

# Append to files
with open('training_data/philosophy/verbs.txt', 'a', encoding='utf-8') as f:
    for w in sorted(new_verbs):
        f.write(w + '\n')

with open('training_data/philosophy/adjectives.txt', 'a', encoding='utf-8') as f:
    for w in sorted(new_adjs):
        f.write(w + '\n')

with open('training_data/philosophy/nouns.txt', 'a', encoding='utf-8') as f:
    for w in sorted(new_nouns):
        f.write(w + '\n')

# Dedupe and sort each file globally
def dedupe_sort(path):
    with open(path, encoding='utf-8') as f:
        lines = sorted(set(line.strip() for line in f if line.strip()))
    with open(path, 'w', encoding='utf-8') as f:
        for line in lines:
            f.write(line + '\n')

dedupe_sort('training_data/philosophy/verbs.txt')
dedupe_sort('training_data/philosophy/adjectives.txt')
dedupe_sort('training_data/philosophy/nouns.txt')

# Remove processed line from files.txt
with open('training_data/philosophy/files.txt', encoding='utf-8') as f:
    lines = [l.strip() for l in f if l.strip()]

# Remove the cat9 line
lines = [l for l in lines if 'cat9' not in l]

with open('training_data/philosophy/files.txt', 'w', encoding='utf-8') as f:
    for l in lines:
        f.write(l + '\n')

print(f'processed: {FILE}')
print(f'verbs: {len(verbs)} ({len(new_verbs)} new)')
print(f'adjectives: {len(adjs)} ({len(new_adjs)} new)')
print(f'nouns: {len(nouns)} ({len(new_nouns)} new)')
