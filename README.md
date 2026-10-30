# AGEO RECHERCHE

Prototype académique de graphe de connaissances scientifiques : collecte ciblée arXiv, extraction de sujets avec Gemini, stockage HDFS, traitement PySpark, Neo4j/GDS et questions en langage naturel avec comparaison Cypher/GraphRAG.

## Ce que contient le dépôt

- `app/` : API FastAPI, extraction, graphe et GraphRAG.
- `static/` : interface AGEO RECHERCHE.
- `jobs/` et `hadoop/` : traitement Spark et configuration HDFS.
- `data/corpus-v3/` : corpus de 25 résumés, métadonnées et ontologie.
- `data/experiments/v3/records/` : 28 enregistrements préparés, avec preuves.
- `data/references-v3/` et `data/gold/` : références **proposées**, non validées indépendamment.
- `docs/` : rapport PDF, fiche de relecture et résultats enregistrés.
- `tests/` : vérifications locales sans appel réel Gemini.

Les HTML/PDF bruts, caches, journaux, sorties Spark et `.env` ne sont pas versionnés. Les scripts conservent leurs chemins à la racine pour rester exécutables.

## Installation validée

Une installation neuve a été construite et exécutée dans des services Docker isolés. Les 44 tests passent également dans l’image Linux ; HDFS, Spark, Neo4j, PageRank, l’API et une question Gemini réelle ont été vérifiés. Voir [le compte rendu](docs/validation-installation.md).

## Installation et configuration

Prérequis : Python 3.11 pour les scripts locaux ; Docker Desktop avec conteneurs Linux et Docker Compose pour HDFS, Spark et Neo4j.

```sh
python -m venv .venv
```

Activer l’environnement (`.venv\Scripts\Activate.ps1` sous PowerShell, `source .venv/bin/activate` sous Linux/macOS), puis :

```sh
pip install -r requirements-dev.txt
```

Copier `.env.example` vers `.env`. Choisir des valeurs personnelles pour `NEO4J_PASSWORD` et `API_TOKEN`, puis renseigner une clé Gemini dans `GEMINI_API_KEY`. Ne jamais publier `.env`.

```sh
docker compose up -d --build neo4j namenode datanode api
```

Attendre le démarrage des services. Ouvrir http://127.0.0.1:8000/v3 et saisir le jeton `API_TOKEN`. **Une installation neuve n’a pas encore importé les données dans Neo4j** : utiliser « Aperçu des fichiers préparés » pour inspecter le corpus fourni.

Pour importer directement le corpus fourni, depuis l’environnement Python local :

PowerShell :

```powershell
$env:NEO4J_URI='bolt://127.0.0.1:7687'
python -m app.corpus_v3 --input records
```

Linux/macOS :

```sh
NEO4J_URI=bolt://127.0.0.1:7687 python -m app.corpus_v3 --input records
```

Cliquer ensuite sur « Charger le corpus Neo4j ». Les labels V3 sont distincts des données historiques. Les copies de mesures de `docs/results/` décrivent l’expérience d’origine, pas une nouvelle exécution sur votre machine.

## Reproduire la chaîne HDFS/Spark

```sh
python expand_corpus.py
python upload_raw_v3.py
python resume_infrastructure_v3.py
```

La première commande collecte les 25 pages à partir d’une liste prédéfinie, avec cache et délai. La deuxième stocke et relit les HTML dans HDFS. La troisième stocke les extractions fournies, vérifie leur intégrité, exécute Spark et importe la sortie dans Neo4j. Elle réutilise l’image API construite précédemment (`--no-build`). Cette chaîne ne relance pas automatiquement l’extraction Gemini des sujets.

Pour une nouvelle extraction : `python extract_topics_v3.py --max-calls 5`. Les appels et quotas dépendent du projet Gemini. Le modèle configuré est `gemini-3.1-flash-lite`, utilisé dans l’expérience sur un palier gratuit. Vérifier les conditions du fournisseur dans son compte ; le code n’active pas la facturation.

## Tests et benchmark

```sh
python -m unittest discover -s tests -q
```

Le workflow `.github/workflows/tests.yml` lance ces tests sous Linux. Les tests unitaires ne nécessitent ni clé ni services Docker actifs.

Après import Neo4j, le benchmark exploratoire peut être repris :

```sh
python benchmark_v3.py --allow-provisional --max-calls 10
python finalize_benchmark_v3.py
```

Pour des scripts exécutés sur l’hôte, définir `NEO4J_URI=bolt://127.0.0.1:7687` ; la valeur `bolt://neo4j:7687` de `.env.example` est destinée au conteneur API.

Sans `--allow-provisional`, le benchmark refuse les références non relues. Les checkpoints isolent modèle, corpus, références et modèles Cypher.

## Résultats et limites

L’expérience enregistrée comprend 25 articles, 289 entités et 382 relations ; Spark fonctionne en `local[2]`. Les 60 paires du benchmark correspondent à 10 questions, deux protocoles et trois répétitions. Le F1 moyen provisoire est de 0,956 pour les deux méthodes. Aucun gain général de GraphRAG n’est démontré.

Les auteurs viennent des métadonnées HTML ; les sujets des résumés ; les affiliations ne couvrent que trois en-têtes PDF. Les références restent en attente de relecture humaine indépendante. Les homonymes, les articles complets, CITES et COLLABORATES_WITH ne sont pas évalués dans cette campagne. La collecte ne découvre pas librement de nouveaux articles.

Le rapport d’origine et ses captures sont dans `docs/rapport-projet-v3.pdf`. Voir `docs/deploiement-observe.md` pour l’historique des incidents. Le Dockerfile et les tests utilisent `requirements.lock.txt`, généré à partir de la nouvelle image Linux réellement construite et testée. `requirements.txt` décrit les contraintes de versions ; le verrou conserve les versions résolues.

## Données et droits

Les publications et métadonnées proviennent d’arXiv, avec leurs liens sources dans le corpus. Elles restent soumises aux droits et conditions de leurs auteurs et d’arXiv. Aucune licence de code n’a été choisie au nom du propriétaire : la publication GitHub n’accorde pas automatiquement une licence de réutilisation.
