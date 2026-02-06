# Projet BIG DATA 
Ce projet...... 

---
## Prérequis
- Docker
- JavaMS17 
- Fichiers de données NYC Taxi placés dans `data/raw`
---

# METTRE TITRE 

## Lancer le projet
Démarrer tous les services en arrière-plan :
>> docker-compose up -d

## Arreter le projet 
>> docker-compose down 

## Permet de supprimer en cas de doublons et d'echec 
>> docker rm airflow-webserver airflow-scheduler airflow-init airflow-postgres postgres minio spark-master spark-worker-1 spark-worker-2

## Verifier les conteneurs en cours 
>> docker ps

⚠️ Airflow met quelques secondes à être accessible après le démarrage.

## Creer un user 
docker compose exec airflow-webserver airflow users create \
  --username airflow \
  --firstname Airflow \
  --lastname Admin \
  --role Admin \
  --email airflow@example.com \
  --password airflow

Se connecter sur le seul projet de airflow 
activer le dag et lancer la fleche start 

on peut suivre les logs en appuyant sur les étapes 

# Étape 4 — Dashboard
dès que l'état est en "success", ouvrir un navigateur est marqué : "http://localhost:8501" une page comparatif va s'ouvrir 

# Etape 5 — Base de données
Se connecter à : http://localhost....."

## Annexes
### Architecture
Dans ce projet, les couches de données sont définies par les outils utilisés :

- **Raw** : données brutes stockées dans MinIO (`bucket raw-data`)
- **Processed / Gold** : données nettoyées et transformées stockées dans PostgreSQL  
  (`fact_trips`, `dim_zone`)

Les transformations sont réalisées directement avec Spark, sans fichiers intermédiaires.

### Exercice 1 — Collecte des données et intégration 
Cet exercice consiste à lire les fichiers de données brutes (juin et décembre)
et à les transférer dans MinIO.
Il permet de mettre en place la couche Raw du pipeline Big Data.
<img src="image/1.jpeg" alt="Exercice 1 - Ingestion des données" width="900" />



### Exo 3 : 
Table vide qui sont crée 



