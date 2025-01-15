import argparse
import os
from datasets import load_dataset
import boto3
from pathlib import Path

def download_wikitext(output_dir):
    """Télécharge les données WikiText-2 et les organise dans les sous-dossiers."""
    
    # Créer les répertoires nécessaires
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    for split in ['train', 'test', 'validation']:
        Path(os.path.join(output_dir, split)).mkdir(exist_ok=True)
    
    # Télécharger le dataset
    dataset = load_dataset("wikitext", "wikitext-2-raw-v1")
    
    # Sauvegarder chaque split dans son dossier respectif
    for split in dataset.keys():
        output_file = os.path.join(output_dir, split, f'wikitext-2-{split}.txt')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in dataset[split]['text']:
                if item.strip():  # Éviter les lignes vides
                    f.write(item + '\n')

def create_bucket_if_not_exists(s3_client, bucket_name):
    """Crée le bucket si nécessaire."""
    try:
        buckets = s3_client.list_buckets()
        if bucket_name not in [bucket['Name'] for bucket in buckets.get('Buckets', [])]:
            s3_client.create_bucket(Bucket=bucket_name)
            print(f"Bucket '{bucket_name}' créé avec succès.")
        else:
            print(f"Bucket '{bucket_name}' existe déjà.")
    except Exception as e:
        print(f"Erreur lors de la vérification ou de la création du bucket : {e}")
        raise


def combine_and_upload(input_dir, endpoint_url):
    """Combine les fichiers et les téléverse dans le bucket raw."""
    # Initialiser le client S3
    s3_client = boto3.client('s3',aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),region_name=os.getenv('AWS_DEFAULT_REGION'),endpoint_url=endpoint_url)
    create_bucket_if_not_exists(s3_client, 'raw')
    # Combiner tous les fichiers
    combined_content = []
    for split in ['train', 'test', 'validation']:
        split_dir = os.path.join(input_dir, split)
        for filename in os.listdir(split_dir):
            file_path = os.path.join(split_dir, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                combined_content.extend(f.readlines())
    
    # Sauvegarder le fichier combiné temporairement
    combined_file = os.path.join(input_dir, 'wikitext-2-combined.txt')
    with open(combined_file, 'w', encoding='utf-8') as f:
        f.writelines(combined_content)
    
    # Téléverser vers S3
    try:
        s3_client.upload_file(
            combined_file,
            'raw',
            'wikitext-2-combined.txt'
        )
        print(f"Fichier téléversé avec succès dans s3://raw/wikitext-2-combined.txt")
    except Exception as e:
        print(f"Erreur lors du téléversement : {e}")
    
    # Nettoyer le fichier temporaire
    os.remove(combined_file)

def main():
    parser = argparse.ArgumentParser(description='Télécharge et traite les données WikiText-2')
    parser.add_argument('--output-dir', type=str, default='data/raw',
                        help='Répertoire de sortie pour les données')
    parser.add_argument('--endpoint-url', type=str, default='http://localhost:4566',
                        help='URL du endpoint S3 (LocalStack)')
    
    args = parser.parse_args()
    
    print("Téléchargement des données...")
    download_wikitext(args.output_dir)
    print("Données téléchargées et organisées.")
    
    print("Combinaison et téléversement des fichiers...")
    combine_and_upload(args.output_dir, args.endpoint_url)
    print("Traitement terminé.")

if __name__ == "__main__":
    main()