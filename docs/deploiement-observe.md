# Archive historique de déploiement

Ce document décrit les incidents de la version antérieure. Pour le test réussi de la copie GitHub et de son nouveau verrou, consulter [validation-installation.md](validation-installation.md).

# État du déploiement

La chaîne a été exécutée avec Docker, HDFS, Spark, Neo4j et GDS.
Les mesures Gemini portent sur trois en-têtes réels de publications.
Les résultats et limites détaillés se trouvent dans README.md et dans le rapport version 2.

Pour redémarrer : ./start.ps1.
Pour réimporter sans nouvel appel Gemini : integration_run.py upload, le service Spark, puis integration_run.py load depuis l'API Docker.

Le benchmark a atteint le quota gratuit quotidien. Après renouvellement, la commande real_benchmark.py --limit 8 reprend le checkpoint.
Les annotations attendent une relecture indépendante. Ne pas utiliser ces quelques essais pour une conclusion générale.

Ne pas publier le fichier .env.
docker compose down arrête les services sans supprimer les volumes.



## Version 3 : déploiement observé le 28 octobre 2026

Les 25 HTML bruts et les 28 extractions V3 ont été stockés et relus dans HDFS. Spark a produit 28 documents et 382 relations. L'import utilise les labels ResearchV3/SourceV3 distincts des données historiques.

L'API en fonctionnement réutilise l'image locale `knowledge-graph-api` et monte `app` et `static` en lecture seule depuis le dossier du projet. `docker compose up -d --no-deps --no-build api` applique cette configuration sans réinstaller les dépendances. Ces montages conservent les corrections lors d'une recréation du conteneur.

Une reconstruction complète a échoué lors de la résolution de `pydantic_core==2.50.1`. Cette même version est présente et fonctionne dans l'image locale existante. La reproductibilité d'une installation entièrement neuve reste à revalider ; le journal est dans `reports/api-v3-deploy.log`. Le bon fonctionnement de l'API locale a été vérifié par HTTP et dans le navigateur.

Le fichier `.env` reste local et n'est pas inclus dans les archives. Le modèle interactif est `gemini-3.1-flash-lite`, présent sur le palier gratuit vérifié. Aucun outil n'active la facturation.
