# Validation de la copie GitHub

Validation réelle du 30 octobre 2026 (UTC), dans des services distincts de la plateforme d'origine.

| Contrôle | Résultat |
| --- | --- |
| Environnement Python neuf et installation des dépendances | Réussi ; pip check sans incohérence |
| Tests Python dans cet environnement | 44 réussis |
| Construction Docker depuis les sources | Réussie |
| Reconstruction avec requirements.lock.txt | Réussie |
| Tests Linux dans l'image reconstruite | 44 réussis |
| Nouvelle instance HDFS, volumes vierges | 28 fichiers écrits et relus intégralement |
| Traitement PySpark local[2] | 28 documents, 382 relations |
| Nouvelle base Neo4j | 289 entités, 382 relations |
| PageRank GDS | 20 résultats retournés |
| API /, /v3, /health, /v3/status, /v3/graph, /v3/pagerank | Réponses HTTP réussies |
| Appel sans jeton | Refus HTTP 401 attendu |
| Question Gemini en direct | Réponse HTTP 200, quatre sujets communs corrects |
| Interface navigateur | Graphe chargé depuis la nouvelle base |

Question : « Quels sujets Big Bird et Longformer ont-ils en commun ? ». Les deux méthodes retrouvent attention mechanisms, long-context modeling, question answering et summarization. Le modèle utilisé est gemini-3.1-flash-lite. La clé du fournisseur est fournie à l'exécution, hors du dépôt.

Les tests ont utilisé le port API 18000, Neo4j 17687/17474 et HDFS 19870, avec le projet Compose `ageo-github-validation` et ses propres volumes. Le projet d'origine n'a pas été modifié.

Corrections pendant la validation : chargement de .env limité au dossier du projet ; attente avec reprises pour le premier démarrage HDFS ; exclusion .runtime du contexte Docker ; nouveau verrou de dépendances construit et testé sous Linux.

Périmètre : données préparées incluses dans le dépôt, import HDFS/Spark/Neo4j et une question en direct. Cette campagne ne refait pas la collecte distante des 25 pages ni tous les appels du benchmark scientifique. Les limites scientifiques et la relecture indépendante restent celles décrites dans le README. Ces résultats ne garantissent pas tous les systèmes ou toutes les versions futures des services externes.
