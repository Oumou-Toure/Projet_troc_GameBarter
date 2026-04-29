# GameBarter

## Description

GameBarter est une plateforme d'échange de jeux vidéo entre particuliers.
Aucun flux monétaire n'est autorisé : tout repose sur le troc, la négociation et la confiance entre utilisateurs.

---

## Stack technique

- Backend : Python / Django 6.0
- Base de données : SQLite
- Frontend : HTML / CSS / Bootstrap 5.3 / Bootstrap Icons
- Authentification : Système natif Django
- Tests fonctionnels : Playwright
- Tests de charge : Locust
- CI/CD : GitHub Actions

---

## Accès à l'application

| Page | URL |
|---|---|
| Accueil | http://127.0.0.1:8000/ |
| Administration | http://127.0.0.1:8000/admin |
| Interface Locust | http://localhost:8089 |

---

## Accès administrateur

| Champ | Valeur |
|---|---|
| Nom d'utilisateur | oumou2023 |
| Mot de passe | 1234 |

---

## Installation et lancement

### 1. Cloner le dépôt

```bash
git clone <url-du-repo>
cd Projet/troc
```

### 2. Créer et activer l'environnement virtuel

```bash
# Windows
python -m venv venvtroc
venvtroc\Scripts\activate

# Mac/Linux
python -m venv venvtroc
source venvtroc/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Installer les navigateurs Playwright

```bash
playwright install chromium
```

### 5. Appliquer les migrations

```bash
python manage.py migrate
```

### 6. Créer un superutilisateur

```bash
python manage.py createsuperuser
```

### 7. Lancer le serveur

```bash
python manage.py runserver
```

---

## Structure du projet

Projet/
├── .github/
│   └── workflows/
│       └── ci.yml
├── venvtroc/
└── troc/
├── manage.py
├── db.sqlite3
├── media/
├── requirements.txt
├── pytest.ini
├── troc/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── exchange_mvp/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── services/
│   │   ├── command_service.py
│   │   └── query_service.py
│   └── templates/
│       ├── base.html
│       ├── home.html
│       ├── login.html
│       ├── item_detail.html
│       ├── create_trade.html
│       ├── my_items.html
│       ├── my_trades.html
│       ├── user_profile.html
│       ├── rate_trade.html
│       └── notifications.html
└── tests/
├── conftest.py
├── test_auth.py
├── test_trade_flows.py
├── test_trade_edge_flows.py
├── test_cqrs.py
├── test_cqrs_mocked.py
└── locustfile.py

---

## Fonctionnalités principales

### Authentification
- Connexion et déconnexion sécurisée
- Conservation du nom d'utilisateur en cas d'erreur de connexion

### Catalogue d'articles
- Affichage de tous les articles disponibles
- Recherche par titre ou description
- Filtrage par catégorie et par plateforme
- Page détail par article (image, description, plateforme, état, valeur estimée, propriétaire, note moyenne du propriétaire)

### Critères de valeur
Chaque article possède des critères permettant d'estimer sa valeur :
- Plateforme : PS5, PS4, Xbox Series, Xbox One, Nintendo Switch, PC, etc.
- Etat : Neuf, Tres bon etat, Bon etat, Etat correct, Abime
- Valeur estimee en euros (renseignee par l'administrateur)
- Annee de sortie
- Un avertissement s'affiche lors de la proposition d'echange si le ratio de valeur entre les articles depasse 2

### Gestion des articles
- Vue "Mes articles" avec distinction entre articles de base et articles recus par echange
- Possibilite de mettre en echange ou retirer du catalogue un article recu

### Systeme d'echange
- Proposition d'echange avec selection visuelle des articles a offrir
- Messagerie integree avec historique des messages
- Actions disponibles : accepter, refuser, envoyer un message, annuler (pendant la negociation), annuler apres acceptation dans les 24h
- Annulation automatique des echanges conflictuels lors d'une acceptation

### Mode de livraison
Apres acceptation, le proposeur choisit parmi :
- Remise en main propre (lieu et date)
- Via la poste (adresse)
- Autre (champ libre)

Le destinataire confirme le mode de livraison et l'echange est finalise.

### Transfert de propriete
A la confirmation de la livraison, les articles changent automatiquement de proprietaire et apparaissent dans "Mes articles" du nouveau proprietaire avec un badge distinctif.

### Notation
- Note de 1 a 5 etoiles avec commentaire optionnel apres un echange termine
- Visible sur le profil utilisateur avec la moyenne

### Profil utilisateur
- Nombre d'echanges completes, note moyenne, articles disponibles, historique des avis recus

### Notifications
- Notifications in-app pour chaque evenement (echange recu, accepte, refuse, annule, message recu, note recue)
- Badge dans la navbar indiquant les notifications non lues

---

## Modeles de donnees

| Modele | Description |
|---|---|
| Category | Categorie d'article |
| Item | Article avec titre, description, image, plateforme, etat, valeur estimee, proprietaire |
| Trade | Echange entre deux utilisateurs avec statut et mode de livraison |
| Message | Message lie a un echange |
| Rating | Notation post-echange |
| Notification | Notification in-app |

### Statuts d'un echange

| Statut | Description |
|---|---|
| pending | En attente de reponse |
| accepted | Accepte, en attente du mode de livraison |
| completed | Termine, articles transferes |
| refused | Refuse par le destinataire |
| cancelled | Annule |

---

## Pattern CQRS

Le projet implemente le patron CQRS (Command Query Responsibility Segregation) qui separe les actions des consultations.

### CommandService (services/command_service.py)
Gere toutes les actions qui modifient les donnees :
- propose_trade() : proposer un echange
- accept_trade() : accepter un echange
- refuse_trade() : refuser un echange
- cancel_trade() : annuler un echange pending
- cancel_accepted_trade() : annuler apres acceptation dans les 24h
- send_message() : envoyer un message
- set_delivery() : choisir le mode de livraison
- confirm_delivery() : confirmer la livraison et transferer les articles
- rate_trade() : noter un echange termine
- toggle_item_availability() : basculer la disponibilite d'un article recu

### QueryService (services/query_service.py)
Gere toutes les consultations sans modifier les donnees :
- get_trades_for_user() : echanges d'un utilisateur
- get_sent_trades() : echanges envoyes
- get_received_trades() : echanges recus
- get_pending_trades() : echanges en attente
- get_completed_trades() : echanges termines
- get_trade_history() : historique complet
- get_trades_for_item() : echanges impliquant un article
- get_messages_for_trade() : messages d'un echange
- get_average_rating() : note moyenne d'un utilisateur
- get_unread_notifications() : notifications non lues
- get_available_items() : articles disponibles
- get_items_by_platform() : articles par plateforme
- get_items_by_condition() : articles par etat
- check_value_imbalance() : detection de desequilibre de valeur

---

## Tests

### Lancer tous les tests

```bash
cd troc
pytest tests/ -v
```

### Resultats

| Fichier | Tests | Description |
|---|---|---|
| test_auth.py | 9 | Authentification |
| test_trade_flows.py | 12 | Flux principaux du catalogue et de la negociation |
| test_trade_edge_flows.py | 15 | Cas extremes et erreurs |
| test_cqrs.py | 44 | Tests unitaires CQRS avec base de donnees |
| test_cqrs_mocked.py | 33 | Tests unitaires CQRS avec mocks |
| Total | 113 | 113/113 passes |

### Tests de charge (Locust)

```bash
# Terminal 1
python manage.py runserver

# Terminal 2
locust -f tests/locustfile.py --host=http://127.0.0.1:8000
```

Ouvrir http://localhost:8089 et configurer 50 utilisateurs avec un spawn rate de 5.

#### Resultats avec 50 utilisateurs simultanees

| Page | Mediane | 95e percentile | Echecs |
|---|---|---|---|
| / catalogue | 21ms | 63ms | 0% |
| /?platform=ps5 | 16ms | 41ms | 0% |
| /?q=mario | 20ms | 71ms | 0% |
| /my-trades/ | 59ms | 130ms | 0% |
| /notifications/ | 24ms | 66ms | 0% |
| POST /login/ | 2300ms | 2700ms | 0% |

#### Analyse des goulots d'etranglement

Le principal goulot identifie est la route POST /login/ avec une mediane de 2300ms sous 50 utilisateurs simultanees. Cette lenteur s'explique par le cout du hashage bcrypt des mots de passe, qui est intentionnellement lent pour des raisons de securite mais devient problematique sous forte charge simultanee.

Les pages de consultation (catalogue, recherche, filtres) sont tres performantes avec des medianes inferieures a 25ms, ce qui montre que la separation CQRS et l'optimisation des requetes (select_related, prefetch_related) sont efficaces.

#### Remédiations proposées

- Passer a Gunicorn multi-processus en production pour paralleliser le traitement des requetes
- Mettre en cache les sessions avec Redis pour reduire la charge sur le login
- Utiliser PostgreSQL en production pour de meilleures performances sous charge
- Implementer un systeme de rate limiting sur le login pour limiter les tentatives simultanees

---

## CI/CD

Le projet utilise GitHub Actions (.github/workflows/ci.yml) :
- Declenchement automatique a chaque push sur main, master et develop
- Declenchement sur chaque Pull Request
- Installation des dependances Python et des navigateurs Playwright
- Execution de l'ensemble de la suite de tests
- Interruption du pipeline en cas d'echec d'un test

---

## Administration

L'administrateur accede a /admin pour :
- Creer et gerer les utilisateurs
- Ajouter des categories
- Ajouter des articles et renseigner plateforme, etat, valeur estimee et annee de sortie
- Consulter tous les echanges, messages et notations

Les articles sont ajoutes par l'administrateur suite a une demande utilisateur. Il n'y a pas d'inscription en libre-service, conformement au perimetre MVP defini.

---

## Phases du projet

### Phase 1 — MVP
Implémentation du produit minimum viable : authentification, catalogue, echanges, messagerie, historique.

### Phase 1 etendue — Ameliorations
Notifications, notation, profil utilisateur, recherche, filtres, mode de livraison, transfert de propriete, criteres de valeur des articles.

### Phase 2 — Tests
Tests fonctionnels Playwright (113 tests au total), pattern CQRS avec deux services dedies, tests unitaires avec et sans mocks.

### Phase 3 — CI/CD et charge
Pipeline GitHub Actions avec execution automatique des tests, tests de charge Locust avec analyse des goulots d'etranglement et remédiations proposees.

---

## Dettes techniques et pistes d'amelioration

- Base de donnees : passer a PostgreSQL en production
- Cache : implementer Redis pour les sessions et les requetes frequentes
- Serveur : utiliser Gunicorn avec Nginx en production
- Stockage des images : utiliser un CDN ou AWS S3
- Inscription utilisateur : ajouter un systeme d'inscription autonome
- Notifications temps reel : implementer WebSockets avec Django Channels
- Tests de charge : augmenter a 200 utilisateurs simultanees pour identifier d'autres goulots
- Couverture de code : integrer un rapport de couverture dans le CI