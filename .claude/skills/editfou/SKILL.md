---
name: editfou
description: Pilote EditFou, l'outil qui transforme un lien YouTube ou une vidéo locale en clips verticaux 9:16 montés « niveau pro » dans FilmCraft (coupe des blancs, recadrage visage, teaser noir et blanc, texte mot par mot animé, motions natifs, bruitages, musique). Utilise ce skill dès qu'on te demande, dans ce dépôt, de créer un projet à partir d'un lien, de proposer ou choisir les clips / moments viraux d'une vidéo, d'écrire ou corriger un storyboard de clip, de monter ou exporter un clip, ou dès qu'on parle d'EditFou, de clipping, de shorts, de reels ou de TikTok à partir d'une vidéo longue — même sans citer EditFou.
---

# EditFou

EditFou fait le travail mécanique (téléchargement, transcription, découpe, recadrage, montage FilmCraft, export).
**Toi, tu fais le jugement** : choisir les moments, écrire les storyboards. L'utilisateur valide chaque étape.
Le parcours complet et les interdits sont dans `AGENTS.md` à la racine : relis-le si besoin.

## Repérer où en est le projet

```bash
python -m editfou etat              # tous les projets : étape, statut, message
python -m editfou etat <projet>     # détail (clips, statuts)
```

Statut `attente_ia` = c'est à toi. `en_cours` = une tâche tourne (ne relance pas). `erreur` = lis le message et
`projets/<p>/journal.txt`.

## Proposer les clips

1. `python -m editfou consignes-clips <p>` : consignes + transcription en phrases horodatées.
2. Choisis 5 à 8 moments (30–90 s) autonomes : accroche dans les 2 premières secondes, idée complète, chute nette.
   Sur une vidéo courte, moins de clips.
3. Écris le JSON (dans le dossier temporaire), puis `python -m editfou proposer <p> --fichier <clips.json>`.
4. Dis à l'utilisateur de valider (interface http://localhost:5100, `python -m editfou serveur` si elle n'est pas
   lancée).

## Écrire le storyboard d'un clip validé

1. `python -m editfou mots <p> <clip>` et `python -m editfou gabarits`.
2. Lis `references/recette.md` (le style) et `references/storyboard.md` (format + exemple validé « Edgar »).
3. Écris le storyboard puis `python -m editfou storyboard <p> <clip> --fichier <sb.json>` ; corrige jusqu'à
   « aucun problème détecté ». Statut `brouillon` : c'est l'utilisateur qui valide.
4. Résume en quelques lignes ce que tu as prévu (teaser, inserts, moment grave) et invite à valider.

## Monter

Une fois le storyboard validé : `python -m editfou monter <p> <clip>` (en tâche de fond : 3 à 10 min). FilmCraft
s'ouvre s'il ne l'est pas. Résultat : `projets/<p>/clips/<clip>/<p>-<clip>.mp4` et le projet `montage.fcproj`,
modifiable dans FilmCraft. Regarde une image du rendu (`apercu.jpg` ou `ffmpeg -ss … -frames:v 1`) avant
d'annoncer que c'est prêt, et signale les sons absents (`montage.json` → `sons_manquants`).

## Si ça coince

- `python -m editfou diagnostic` vérifie ffmpeg, les paquets, FilmCraft, les polices et les sons.
- FilmCraft ne répond pas : il est peut-être fermé ou bloqué sur une fenêtre ; `monter` le relance si le port est libre.
- Un insert « ignoré : le passage a été coupé » : ses temps tombaient dans un blanc ou une exclusion ; recale-le sur les mots.
- Le texte passe sur le visage : le visage n'a pas été détecté sur ce plan (plan large, profil) ; vérifier
  `clips/<clip>/plans.json`.
