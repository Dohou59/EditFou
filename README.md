# EditFou

**Du lien YouTube au clip vertical monté « niveau pro », validé étape par étape.**

Tu colles un lien (ou une vidéo de ton PC). EditFou la télécharge et la transcrit mot à mot, l'IA propose les
meilleurs moments, tu gardes ceux que tu veux. Pour chaque clip, l'IA écrit un storyboard, tu le valides, et le
montage se construit tout seul dans [FilmCraft](https://filmcraft.app) :

- coupe de tous les blancs, recadrage 9:16 sur le visage, deux cadrages en alternance à chaque coupe ;
- teaser noir et blanc en ouverture avec la phrase la plus forte, moment grave en noir et blanc ;
- texte **mot par mot** à hauteur de poitrine (Inter Black, mot-clé rouge en majuscules), chaque mot qui apparaît
  quand il est prononcé ;
- motions plein écran natifs (compteur, horloge, courbe, ×1 → ×2, chapitres, mot choc…) calés sur la syllabe ;
- un bruitage par animation, pic sur l'image ; musique sous la voix ; son normalisé à -14 LUFS.

Le projet FilmCraft reste **entièrement modifiable** : chaque mot, chaque forme, chaque son est un élément à part.

## Pensé pour être piloté par une IA

Les étapes de jugement (choisir les clips, écrire les storyboards) sont faites par **ton agent** : ouvre Claude
Code (ou un autre agent) dans ce dossier, il lit `AGENTS.md` / `CLAUDE.md` et le skill `.claude/skills/editfou`,
et sait quoi faire :

> « Propose les clips du projet EditFou *mon-podcast* »
> « Écris le storyboard du clip c02 »

Pas d'agent sous la main ? Renseigne un fournisseur dans `editfou.local.json` (`anthropic`, `openai`, `gemini` ou
`ollama`) et sa clé dans l'environnement : les boutons « Proposer avec… » apparaissent dans l'interface.

## Installation

Prérequis : Python 3.11+, [ffmpeg](https://ffmpeg.org) dans le PATH, FilmCraft (version portable) et les polices
de `editfou/polices/` installées (double-clic → Installer).

```bash
git clone https://github.com/Dohou59/EditFou.git
cd EditFou
pip install -r requirements.txt
cp editfou.example.json editfou.local.json   # puis renseigner le dossier de FilmCraft et tes sons
python -m editfou diagnostic
```

### Bruitages et musique

EditFou n'inclut aucun son. Dans `editfou.local.json`, la clé `sons` associe chaque rôle à un fichier de ta
bibliothèque (`python -m editfou sons` liste les rôles et mesure le pic de chaque son) : `musique`, `braam`,
`whoosh`, `whoosh_bas`, `woosh`, `swoosh`, `punch`, `hit`, `boom`, `pop`, `clic`, `declencheur`, `ding`, `tictac`,
`riser`, `verre`. Un rôle absent est simplement muet.

## Utilisation

```bash
python -m editfou serveur          # interface : http://localhost:5100
```

1. Colle un lien YouTube → **Analyser** : les sous-titres YouTube arrivent en quelques secondes, l'IA peut déjà
   choisir les clips pendant que la vidéo se télécharge. Whisper ne transcrit ensuite que les clips gardés.
   (Fichier de ton PC : transcription Whisper complète, ≈ 1 min par minute de vidéo.)
2. Demande à ton agent de proposer les clips → **Garder** / **Écarter** (début et fin ajustables).
3. Demande-lui le storyboard de chaque clip gardé → relis la ligne de temps → **Valider le storyboard**.
4. **Lancer le montage** → le MP4 apparaît dans la page, le projet FilmCraft est à côté.

Tout existe aussi en ligne de commande (`python -m editfou --help`), et tout est lisible dans
`projets/<projet>/` (transcription, `clips.json`, `clips/<id>/storyboard.json`, `montage.fcproj`, MP4).

## Ajouter un motion

Un motion est une fonction de `editfou/gabarits.py` qui pose des formes, des textes, des images clés et des sons
dans la scène FilmCraft (`editfou/motion.py`), plus une ligne dans `INSERTS` ou `SURIMPRESSIONS` avec sa
description, ses paramètres et ses déclencheurs. L'IA le découvre aussitôt par `python -m editfou gabarits`.

## Crédits

Idée et sélection des moments inspirées d'[OpenClip](https://github.com/aionixos/openclip) (MIT, AIONIX) ;
recette de montage issue de ClaudeCut ; montage par FilmCraft. Détails dans [NOTICE.md](NOTICE.md).
Licence : [MIT](LICENSE).
