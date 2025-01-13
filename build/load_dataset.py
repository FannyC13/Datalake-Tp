from datasets import load_dataset

# Télécharger les données
dataset = load_dataset("wikitext", "wikitext-2-raw-v1", cache_dir="./data/raw")

# Organiser les fichiers
dataset['train'].to_csv("./data/raw/train/train.csv", index=False)
dataset['test'].to_csv("./data/raw/test/test.csv", index=False)
dataset['validation'].to_csv("./data/raw/dev/dev.csv", index=False)

print("Les données WikiText V2 ont été téléchargées et organisées.")
