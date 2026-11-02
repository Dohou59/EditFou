# EditFou — consignes pour l'agent IA

Tu travailles dans **EditFou** : un lien YouTube (ou une vidéo locale) devient des clips verticaux 9:16 montés
« niveau pro » dans FilmCraft. Les étapes qui demandent du jugement (choisir les moments, écrire les storyboards) sont
**les tiennes** ; tout le reste est fait par `python -m editfou …`. Tu ne valides jamais à la place de l'utilisateur :
il valide les clips, puis chaque storyboard, dans l'interface (`python -m editfou serveur`, http://localhost:5100) ou
en te le disant explicitement.

Réponds dans la langue de l'utilisateur (le projet est en français).

## Le parcours

| # | Étape | Qui | Commande / fichier |
|---|---|---|---|
| 1 | Créer et analyser | toi ou l'interface | `python -m editfou nouveau "<lien ou fichier>" --analyser` (≈ 1 min de calcul par minute de vidéo) |
| 2 | Proposer les clips | **toi** | lire `projets/<p>/phrases.txt`, écrire un JSON, `python -m editfou proposer <p> --fichier clips.json` |
| 3 | Valider les clips | **l'utilisateur** | interface, ou `python -m editfou valider <p> c01 c03` s'il te le demande |
| 4 | Écrire les storyboards | **toi** | `python -m editfou mots <p> <clip>` + `gabarits`, écrire le JSON, `storyboard <p> <clip> --fichier sb.json` |
| 5 | Valider les storyboards | **l'utilisateur** | interface, ou `python -m editfou valider-storyboard <p> <clip>` s'il te le demande |
| 6 | Monter | toi ou l'interface | `python -m editfou monter <p> <clip>` (FilmCraft s'ouvre tout seul ; 3 à 10 min) |

`python -m editfou etat` liste les projets et leur étape ; `python -m editfou etat <p>` détaille un projet.
L'interface se rafraîchit seule : quand tu écris un fichier, l'utilisateur le voit.

## Étape 2 — proposer les clips

`python -m editfou consignes-clips <p>` imprime les consignes complètes avec la transcription : suis-les.
L'essentiel : 5 à 8 moments autonomes de 30 à 90 s, une première phrase qui accroche, une idée complète avec une
chute nette, pas de chevauchement. Les temps sont ceux de `phrases.txt` (secondes de la vidéo source).

```json
{"clips": [{"debut": 312.40, "fin": 381.90, "titre": "Tu perds deux fois",
  "accroche": "Si un truc difficile fait que tu n'avances plus, tu perds deux fois.",
  "raison": "Idée contre-intuitive, chute émotionnelle forte.", "score": 9}]}
```

EditFou cale chaque clip sur les mots et le numérote (`c01`, `c02`…). Ensuite dis à l'utilisateur de valider.

## Étape 4 — écrire un storyboard

1. `python -m editfou mots <p> <clip>` : chaque mot avec son début et sa fin (« (?) » = mot douteux).
2. `python -m editfou gabarits` : les motions disponibles, leurs paramètres et déclencheurs.
3. Lis la recette de style : `.claude/skills/editfou/references/recette.md` et le format complet avec un exemple
   validé : `.claude/skills/editfou/references/storyboard.md`.
4. Écris le JSON (temps = secondes de la **source**, deux décimales, pris dans la liste des mots), puis
   `python -m editfou storyboard <p> <clip> --fichier sb.json`. La commande liste les problèmes : corrige jusqu'à
   « aucun problème détecté ». Laisse `"statut": "brouillon"`.

Règles qui font la différence :
- **Teaser** : la phrase la plus choc (≈ 2 s, 1 à 3 plages) rejouée en noir et blanc avant le récit. Pas de titre.
- **Inserts** : un toutes les 6 à 12 s, qui illustre littéralement ce qui est dit, de 0,8 à 2,5 s (4 s max),
  déclencheurs sur la syllabe du mot (son temps de début). Jamais deux inserts qui se chevauchent.
- **Mots-clés** : un par idée (chiffres, émotions, verbes forts), en minuscules tels que prononcés.
- **Exclure** les relances d'un intervieweur, redites, faux départs ; **corriger** les fautes de transcription.
- **Grave** : le moment le plus lourd passe en N&B, musique coupée (facultatif).

## Ce que tu ne fais pas

- Tu ne passes pas un clip ou un storyboard en `valide` sans que l'utilisateur l'ait demandé.
- Tu n'écris jamais de clé d'API dans un fichier ; les clés (facultatives) vivent dans l'environnement.
- Tu ne modifies pas `editfou.local.json` sans le dire ; tu ne commites jamais `projets/`, des vidéos ou des sons.
- Pas d'export par le canal de contrôle FilmCraft (`export.quick` bloque) : `monter` / `exporter` passent par
  `filmcraft-cli`.

## Code

Paquet Python `editfou/` (Python 3.11+, commentaires en français) : `analyse.py` (yt-dlp, faster-whisper, plans
OpenCV), `clips.py`, `storyboard.py`, `decoupe.py`, `cadrage.py`, `texte.py`, `motion.py` (scène FilmCraft),
`gabarits.py` (motions), `montage.py`, `serveur.py` + `web/index.html`, `filmcraft.py` (canal de contrôle + export).
Un nouveau motion = une fonction dans `gabarits.py` + son entrée dans `INSERTS` ou `SURIMPRESSIONS`.
