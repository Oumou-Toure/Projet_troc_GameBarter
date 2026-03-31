# 🎮 GameBarter

## Description

GameBarter est une plateforme d'échange de jeux vidéo entre particuliers.
Aucun flux monétaire n'est autorisé : tout repose sur le troc, la négociation et la confiance entre utilisateurs.


## Stack technique

- **Backend** : Python / Django 6.0
- **Base de données** : SQLite
- **Frontend** : HTML / CSS / Bootstrap 5.3 / Bootstrap Icons
- **Authentification** : Système natif Django


## Accès à l'application

| Page | URL |
|---|---|
| Accueil | http://127.0.0.1:8000/ |
| Administration | http://127.0.0.1:8000/admin |


## Accès administrateur

| Champ | Valeur |
|---|---|
| Nom d'utilisateur | `oumou2023` |
| Mot de passe | `1234` |


## Installation et lancement

### 1. Cloner le dépôt
```bash
git clone <url-du-repo>
cd Projet/troc
```

### 2. Créer et activer l'environnement virtuel
```bash
# Créer
python -m venv venvtroc

# Activer (Windows)
venvtroc\Scripts\activate

# Activer (Mac/Linux)
source venvtroc/bin/activate
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Appliquer les migrations
```bash
python manage.py migrate
```

### 5. Créer un superutilisateur (admin)
```bash
python manage.py createsuperuser
```

### 6. Lancer le serveur
```bash
python manage.py runserver
```

## Fonctionnalités

### Authentification
- Connexion / Déconnexion sécurisée
- Gestion des erreurs de connexion avec conservation du nom d'utilisateur

### Catalogue d'articles
- Affichage de tous les articles disponibles
- Recherche par titre ou description
- Filtrage par catégorie
- Page détail par article (image, description, propriétaire, note moyenne)

### Gestion des articles
- Vue "Mes articles" avec distinction entre :
  - Articles de base (ajoutés par l'administrateur)
  - Articles reçus par échange (badge distinctif)
- Possibilité de mettre en échange ou retirer du catalogue un article reçu

### Système d'échange
- Proposition d'échange avec sélection visuelle des articles à offrir
- Message initial optionnel
- Négociation par messagerie intégrée (bulles de chat)
- Actions disponibles :
  - Accepter
  - Refuser
  - Envoyer un message
  - Annuler (proposeur, pendant `pending`)
  - Annuler après acceptation (proposeur, dans les **24h**)
- Annulation automatique des échanges conflictuels lors d'une acceptation

### Mode de livraison
Après acceptation d'un échange, le proposeur choisit parmi :
- Remise en main propre (lieu + date)
- Via la poste (adresse)
- Autre (champ libre)

Le destinataire confirme ensuite le mode → échange **terminé**.

### Transfert de propriété
À la confirmation de la livraison :
- Les articles changent de propriétaire automatiquement
- Ils apparaissent dans "Mes articles" du nouveau propriétaire
- Ils disparaissent du catalogue

### Notation
- Après un échange terminé (`completed`), chaque partie peut noter l'autre
- Note de 1 à 5 étoiles avec commentaire optionnel
- Note visible sur le profil utilisateur

### Profil utilisateur
- Avatar généré automatiquement
- Nombre d'échanges complétés
- Note moyenne reçue
- Articles disponibles
- Historique des avis reçus

### Notifications
- Notifications in-app pour chaque événement :
  - Nouvel échange reçu
  - Échange accepté / refusé / annulé
  - Mode de livraison défini / confirmé
  - Nouveau message
  - Nouvelle notation
- Badge dans la navbar indiquant les notifications non lues
- Page dédiée avec historique


## Modèles de données

| Modèle | Description |
|---|---|
| `Category` | Catégorie d'article |
| `Item` | Article avec titre, description, image, propriétaire, disponibilité |
| `Trade` | Échange entre deux utilisateurs avec statut et mode de livraison |
| `Message` | Message lié à un échange |
| `Rating` | Notation post-échange |
| `Notification` | Notification in-app |

### Statuts d'un échange

| Statut | Description |
|---|---|
| `pending` | En attente de réponse |
| `accepted` | Accepté, en attente du mode de livraison |
| `completed` | Terminé, articles transférés |
| `refused` | Refusé par le destinataire |
| `cancelled` | Annulé |



## Administration

L'administrateur accède à `/admin` pour :
- Créer et gérer les utilisateurs
- Ajouter des catégories
- Ajouter des articles et les affecter aux utilisateurs
- Consulter tous les échanges, messages et notations

> Les articles sont ajoutés par l'administrateur suite à une demande utilisateur
> (email, forum, etc.). Il n'y a pas d'inscription en libre-service, conformément
> au périmètre MVP défini.


