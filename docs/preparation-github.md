# Préparation du premier commit

La copie GitHub est séparée de la plateforme d'origine. Aucun fichier .env local n'y est copié. Caches, environnements Python, journaux et fichiers d'exécution sont exclus de Git et de l'archive.

Le dépôt est initialisé sur main et les fichiers sont préparés pour le premier commit. Aucun commit ni envoi GitHub n'a été effectué.

La copie a été installée et testée réellement dans un environnement Python neuf et des services Docker isolés : voir validation-installation.md. Les 44 tests passent sur Windows et dans l'image Linux ; la chaîne HDFS/Spark/Neo4j et une réponse Gemini en direct ont été vérifiées.

Les secrets locaux ont été recherchés dans les fichiers destinés à la publication sans être affichés. Avant publication, le propriétaire doit encore révoquer toute clé divulguée, choisir le dépôt distant et décider d'une éventuelle licence. Aucune licence n'a été choisie automatiquement.
