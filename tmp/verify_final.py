from pathlib import Path
R = Path(r"D:\Ninereeds")
files = [
    "training_data/phases/phase_4/phase_4_12.md","training_data/phases/phase_4/phase_4_19.md",
    "training_data/phases/phase_4/phase_4_23.md","training_data/phases/phase_4/phase_4_31.md",
    "training_data/phases/phase_4/phase_4_33.md","training_data/phases/phase_4/phase_4_35.md",
    "training_data/phases/phase_4/phase_4_36.md","training_data/phases/phase_4/phase_4_43.md",
    "training_data/phases/phase_4/phase_4_45.md","training_data/phases/phase_4/phase_4_51.md",
    "training_data/phases/phase_4/phase_4_55.md","training_data/phases/phase_4/phase_4_57.md",
    "training_data/phases/phase_4/phase_4_59.md","training_data/phases/phase_4/phase_4_60.md",
    "training_data/phases/phase_4/phase_4_61.md","training_data/phases/phase_4/phase_4_62.md",
    "training_data/phases/phase_4/phase_4_67.md","training_data/phases/phase_4/phase_4_69.md",
    "training_data/phases/phase_4/phase_4_71.md","training_data/phases/phase_4/phase_4_72.md",
    "training_data/phases/phase_4/phase_4_73.md","training_data/phases/phase_4/phase_4_74.md",
    "training_data/phases/phase_4/phase_4_085.md","training_data/phases/phase_4/phase_4_087.md",
    "training_data/phases/phase_4/phase_4_091.md","training_data/phases/phase_5/phase_5_15.md",
    "training_data/phases/phase_5/phase_5_45.md","training_data/phases/phase_5/phase_5_2000.md",
    "training_data/phases/phase_6/phase_6_298.md","training_data/phases/phase_6/phase_6_494.md",
    "training_data/phases/phase_6/phase_6_497.md","training_data/phases/phase_6/phase_6_579.md",
    "training_data/phases/phase_6/phase_6_588.md","training_data/phases/phase_6/phase_6_704.md",
    "training_data/phases/phase_6/phase_6_711.md",
]
g = b = 0
for f in files:
    c = (R / f).read_text("utf-8")
    e = []
    if "[user]" not in c: e.append("no [user]")
    if "[Ninereeds]" not in c: e.append("no [Ninereeds]")
    if "```" in c: e.append("stray fence")
    if e:
        print(f"FAIL {f}: {e}")
        b += 1
    else:
        g += 1
print(f"PASS: {g}, FAIL: {b}")
