from ase.io import read, write

src = "/workspace/ni_al/data/processed/pilot01_all.extxyz"
train_out = "/workspace/ni_al/data/datasets/pilot01_ft_train.extxyz"
valid_out = "/workspace/ni_al/data/datasets/pilot01_ft_valid.extxyz"

data = read(src, index=":")

valid_sources = {
    "Al3Ni/iso_p02/Al3Ni_iso_p02.out",
    "Al3Ni2/rattle_003/Al3Ni2_rattle_003.out",
    "Al3Ni5/iso_p02/Al3Ni5_iso_p02.out",
    "AlNi/rattle_003/AlNi_rattle_003.out",
    "AlNi3/shear015_rattle002/AlNi3_shear015_rattle002.out",
}

train = []
valid = []

for atoms in data:
    srcfile = atoms.info["source_file"]

    if srcfile in valid_sources:
        valid.append(atoms)
    else:
        train.append(atoms)

print("Train:", len(train))
print("Valid:", len(valid))

print("\nVALIDATION:")
for a in valid:
    print(
        a.info["phase"],
        a.info["configuration"],
        a.info["source_file"]
    )

assert len(train) == 13
assert len(valid) == 5

write(train_out, train, format="extxyz")
write(valid_out, valid, format="extxyz")

print("\nBalanced fine-tuning split: PASS")
