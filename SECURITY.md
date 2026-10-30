# Configuration et secrets

Ne publier ni `.env`, ni clé Gemini, ni mot de passe Neo4j, ni jeton API. `.env.example` contient seulement des valeurs d’exemple. Les services sont liés à 127.0.0.1 pour une démonstration locale.

Avant toute publication, renouveler toute clé déjà divulguée. La clé précédemment partagée dans la conversation doit être révoquée chez le fournisseur puis remplacée localement ; cette action n’est pas effectuée automatiquement par les scripts.

Le scanner `check_publication.py` détecte des formats usuels de secrets et des chemins privés. Ce contrôle réduit les erreurs, sans garantir l’absence de toutes les données sensibles possibles. Examiner aussi `git diff --cached` avant le premier commit.
