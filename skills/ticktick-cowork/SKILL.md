---
name: ticktick-cowork
description: Workflow de coworking avec TickTick. Récupère les tâches tagguées 'claude' depuis TickTick via le CLI ticktick, les présente, puis guide l'utilisateur pour rechercher, planifier et exécuter chaque tâche. Utiliser ce skill quand l'utilisateur invoque /ticktick-cowork.
---

# TickTick Cowork

Workflow interactif pour travailler sur des tâches TickTick tagguées `claude` avec l'aide de Claude.

## Prérequis

Le CLI `ticktick` doit être installé et authentifié (`ticktick auth` déjà fait). Les credentials OAuth sont dans `.env` au sein du repo `ticktick_claude`.

## Workflow

### Étape 1 : Récupérer les tâches

Exécute `ticktick claude-tasks --json` pour lister les tâches ouvertes tagguées `claude`. Parse le JSON pour extraire les IDs, titres, descriptions et checklist items.

### Étape 2 : Présenter les tâches

Affiche la liste dans un format lisible :
- Titre de la tâche
- Tags
- Projet
- Priorité (si définie)

S'il n'y a qu'une seule tâche, confirme avec l'utilisateur avant de continuer. S'il y en a plusieurs, demande laquelle travailler.

### Étape 3 : Analyser la tâche sélectionnée

Lis attentivement :
- Le titre
- La description (`desc` pour les tâches CHECKLIST, `content` pour les tâches TEXT)
- Les checklist items existants

Si la tâche fait référence à des fichiers ou du code dans le repo courant, explore le codebase pour construire le contexte. Pose des questions si la tâche est ambiguë.

### Étape 4 : Proposer un plan — deux chemins

Présente deux options à l'utilisateur :

**Chemin A : Recherche & découpage** — Si la tâche nécessite plus d'investigation ou est trop large pour une session :
- Recherche le problème
- Écris les résultats via `ticktick append-description <project_id> <task_id> "<résumé>"`
- Découpe en sous-étapes via `ticktick append-description <project_id> <task_id> "" --checklist "étape 1" "étape 2" ...`
- La tâche reste ouverte avec un roadmap clair

**Chemin B : Compléter la tâche** — Si la tâche est actionnable et faisable maintenant :
- Décris les étapes prévues
- Demande l'approbation de l'utilisateur
- Exécute (écriture de code, édition de fichiers, commandes, etc.)

### Étape 5 : Exécuter

- **Chemin A** : Investigue, puis écris le résumé et la checklist dans TickTick. La tâche reste ouverte.
- **Chemin B** : Réalise le travail. Présente les résultats. Si l'utilisateur est satisfait, marque la tâche comme faite via `ticktick complete-task <project_id> <task_id>`.

## Commandes CLI disponibles

| Commande | Usage |
|---|---|
| `ticktick claude-tasks --json` | Lister les tâches tagguées claude (JSON) |
| `ticktick tasks --project <id> --json` | Lister les tâches d'un projet |
| `ticktick projects` | Lister les projets |
| `ticktick append-description <project> <task> "<text>" --checklist "item1" "item2"` | Ajouter description + checklist atomiquement |
| `ticktick add-checklist <project> <task> "item1" "item2"` | Ajouter des checklist items |
| `ticktick complete-task <project> <task>` | Marquer une tâche comme complétée |

## Pièges à éviter

- Ne jamais appeler `append-description` puis `add-checklist` séparément dans la même session — utilise `--checklist` sur `append-description` pour éviter la race condition de stale-read.
- Toujours envoyer l'objet tâche complet lors des mises à jour API pour ne pas perdre de champs.
- Le champ description dépend du type de tâche : `desc` pour CHECKLIST, `content` pour TEXT.
