# Crédits

EditFou reprend des idées et du code d'autres projets libres :

- **OpenClip** par AIONIX (<https://github.com/aionixos/openclip>, licence MIT, © 2026 AIONIX) : le principe
  « lien YouTube → transcription → l'IA choisit les moments → clips verticaux », le téléchargement par yt-dlp
  et les consignes de sélection des moments viraux (`editfou/clips.py`).
- **ClaudeCut** (outil interne de l'autrice) : coupe des blancs, recadrage par plan, texte mot par mot et
  recette de style validée (`editfou/decoupe.py`, `editfou/cadrage.py`, `editfou/texte.py`).
- **FilmCraft** (<https://filmcraft.app>) : le montage est construit dans FilmCraft par son canal de contrôle
  et exporté par `filmcraft-cli`. FilmCraft n'est pas inclus dans ce dépôt : il s'installe à part.

Polices incluses (licence SIL Open Font License 1.1, textes dans `editfou/polices/`) :
Inter (Rasmus Andersson), Bebas Neue (Dharma Type), Playfair Display (Claus Eggers Sørensen).

Les bruitages et musiques ne sont pas inclus : chacun pointe vers sa propre bibliothèque
(`editfou.local.json`, clé `sons`).
