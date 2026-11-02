# Recette de style — clip vertical « niveau pro »

Validée sur le montage « Edgar » (novembre 2026), d'après l'analyse image par image d'un monteur de référence
(texte mot par mot, inserts courts). C'est un système, pas un gabarit : chaque clip a ses propres inserts.

## 1. Structure
- **Pas de titre d'accroche.** On ouvre sur un **teaser noir et blanc** : la phrase la plus choc du clip (≈ 2 s,
  1 à 3 plages), plus serrée (×1,12) avec une lente poussée, texte blanc seul. Braam à 0, whoosh à la bascule,
  puis le récit commence en couleur.
- Le moment le plus grave du récit repasse en N&B avec poussée lente, la musique se tait, le mot-clé reste blanc.
- Arc : teaser → thèse → preuve / exemple → mécanisme → chute. On coupe sur la tension, sans conclusion ni appel
  à l'action.
- On retire les relances de l'intervieweur (« Sérieusement ? », « C'est vrai. »), les redites et tous les blancs.

## 2. Rythme et cadrage (automatique)
- Tous les silences coupés (mots de la transcription + silences mesurés à l'énergie).
- Deux cadrages en alternance à chaque coupe dans un même plan (×1,22 serré, ×1,12 large) : la coupe devient
  invisible et l'image change toutes les ~2 s.
- Visage centré plan par plan ; pas de zoom animé ni de secousse sur l'A-roll.

## 3. Texte mot par mot (automatique, réglé par `mots_cles` et `corrections`)
- Un bloc de 2 à 5 mots **à hauteur de poitrine, sous le menton** (jamais sur le visage, jamais en bas).
- Petits mots de liaison blancs / **MOT-CLÉ en majuscules, rouge #E0202A**, en grand / suite en petit. Inter Black.
- Chaque mot apparaît au moment exact où il est prononcé (fondu 0,15 s) ; le bloc est remplacé d'un coup.
- Un bloc s'arrête sur : écart > 0,35 s, 5 mots, 1,9 s, ponctuation, début d'un insert, fin du teaser.
- Mot-clé : le premier de `mots_cles` présent dans le bloc, sinon le mot plein le plus long. Choisir des mots qui
  portent le sens : chiffres, émotions, verbes forts, le mot qu'on retient.

## 4. Inserts plein écran (le storyboard)
- Un insert illustre **littéralement** ce qui est dit (une heure → horloge, deux fois → ×1 → ×2, 20 dates →
  compteur, chute → courbe qui plonge, « d'abord » → chapitre 01).
- Il commence sur le premier mot de la phrase et dure la phrase : idéal 0,8–2,5 s, 4 s au maximum.
- Chaque animation part **sur la syllabe** du mot déclencheur (temps de début du mot dans `mots`).
- Un insert toutes les 6 à 12 s : assez pour relancer l'attention, pas au point de cacher la personne.
  Laisser l'A-roll respirer sur les phrases d'émotion (le visage dit plus qu'un motion).
- Charte : fond noir à grille, rouge #E0202A, Playfair italique (la petite phrase), Inter Black / Bebas
  (mots-clés). `phrase` = 2 à 5 mots en italique au-dessus ; `texte` = le mot-clé en majuscules.
- Varier les gabarits ; `mot_choc` est le joker, à ne pas enchaîner plus de deux fois de suite.

## 5. Surimpressions (sur l'A-roll, jamais sur le visage)
- `pastille` 1, 2, 3 en haut à gauche quand la personne énumère ; `compteur` ×1 → ×2 sous le texte ;
  `souligne` : barre rouge sous le mot-clé d'un bloc (le mot doit être dans `mots_cles`).

## 6. Son (automatique)
- Chaque événement graphique a son bruitage, pic calé sur l'image (punch sur un tampon, ding à la fin d'un
  compteur, tic-tac qui s'arrête net sur « heure »…). Pas de bruitage sur un simple mot de texte.
- Musique ≈ 13 dB sous la voix, coupée sur le moment grave (fondus). Export normalisé à -14 LUFS.
