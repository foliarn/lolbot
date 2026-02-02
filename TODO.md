# TODO - Améliorations Futures

Liste des fonctionnalités et améliorations possibles.

## Priorité Haute

- [ ] **Tests unitaires** : Ajouter des tests pour les modules critiques
- [ ] **Gestion d'erreurs améliorée** : Meilleurs messages d'erreur utilisateur
- [ ] **Logs structurés** : Utiliser un logger centralisé avec niveaux
- [ ] **Rate limit intelligent** : Adapter dynamiquement selon les headers API

## Priorité Moyenne

- [ ] **Support multi-régions** : NA, KR, BR, etc.
- [ ] **Graphiques de stats** : Génération d'images avec matplotlib
- [ ] **Historique de progression** : Tracker le rang au fil du temps
- [ ] **Commande /compare** : Comparer deux joueurs
- [ ] **Notifications Discord webhooks** : Alternative aux DMs

## Priorité Basse

- [ ] **Interface web** : Dashboard pour voir les stats
- [ ] **Support des builds** : Recommandations de stuff
- [ ] **Analyse de méta** : Tendances des picks/bans
- [ ] **Commandes vocales** : Intégration voice channels
- [ ] **Multi-langue** : Support FR/EN/ES

## Optimisations

- [ ] **Connection pooling** : Réutiliser les connexions HTTP
- [ ] **Cache Redis** : Alternative plus performante que SQLite
- [ ] **Async batch processing** : Grouper les requêtes similaires
- [ ] **Compression des données** : Réduire la taille du cache

## Fonctionnalités Clash Scout

- [ ] **Analyse de draft** : Prédire les picks/bans adverses
- [ ] **Recommandations de team comp** : Synergies de champions
- [ ] **Historique Clash** : Tracker les performances en Clash
- [ ] **Détection de duos** : Identifier les joueurs qui duoQ ensemble
- [ ] **Champion pools par rôle** : Analyse plus fine

## Patch Watcher

- [ ] **Analyse IA des changements** : Résumer l'impact des buffs/nerfs
- [ ] **Notifications push** : Via mobile app
- [ ] **Comparaison de patches** : Voir l'évolution sur plusieurs versions
- [ ] **Alertes personnalisées** : Seuils de changements

## UX/UI

- [ ] **Embeds interactifs** : Boutons et menus déroulants
- [ ] **Pagination** : Pour les listes longues
- [ ] **Autocomplete** : Suggestions de champions
- [ ] **Reactions** : Emojis pour les actions rapides

## Sécurité

- [ ] **Validation des inputs** : Prévenir les injections
- [ ] **Rate limiting bot** : Limiter les commandes par utilisateur
- [ ] **Encryption** : Chiffrer les données sensibles en DB
- [ ] **Audit logs** : Tracker toutes les actions

## DevOps

- [ ] **Docker** : Containerisation du bot
- [ ] **CI/CD** : Déploiement automatique
- [ ] **Health checks** : Monitoring automatique
- [ ] **Backup automatique** : Base de données

## Documentation

- [ ] **Tutoriels vidéo** : Guide d'utilisation
- [ ] **Wiki complet** : Toutes les commandes détaillées
- [ ] **API documentation** : Pour développeurs tiers
- [ ] **Changelog** : Historique des versions

## Community

- [ ] **Serveur Discord dédié** : Support et feedback
- [ ] **Vote system** : Upvote/downvote des features
- [ ] **Leaderboard** : Classement des utilisateurs
- [ ] **Achievements** : Badges et récompenses

---

## Notes de développement

### Idées en vrac

- Intégration avec u.gg / op.gg pour les builds
- Système de notifications pour les live games des streamers
- Mode "coach" avec conseils personnalisés
- Analyse de replay (si API disponible)
- Prédictions de matchs avec ML
- Support des événements (MSI, Worlds)

### Problèmes connus

- Data Dragon peut avoir un délai avant mise à jour après patch
- SPECTATOR-V4 ne donne pas toujours les rangs précis
- Clash API peut être vide si pas de tournoi actif
- Rate limit peut être problématique avec beaucoup d'utilisateurs

### Contributions recherchées

- Traductions
- Designs d'embeds
- Algorithmes de scoring
- Tests sur différentes régions
