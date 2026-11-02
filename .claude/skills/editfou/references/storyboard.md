# Format du storyboard (`projets/<p>/clips/<clip>/storyboard.json`)

Tous les temps sont en **secondes de la vidéo source** (ceux de `python -m editfou mots`), deux décimales.
EditFou les convertit en temps du montage après la coupe des blancs.

| Clé | Type | Rôle |
|---|---|---|
| `clip`, `titre` | texte | identifiant (`c01`) et titre |
| `debut`, `fin` | s | passage gardé ; reprendre ceux du clip validé (on peut resserrer) |
| `exclure` | `[[a, b], …]` | passages retirés : relances d'un intervieweur, redites, faux départs |
| `teaser` | `[[a, b], …]` | 1 à 3 plages (≈ 2 s en tout) rejouées en ouverture, N&B, ×1,12 |
| `grave` | `[[a, b], …]` | moment grave : N&B, poussée lente, musique coupée, mot-clé blanc |
| `corrections` | `[{temps, mot, par}]` | `temps` = début du mot, `mot` = mot transcrit exact, `par` = remplacement (`""` supprime) |
| `cadrages` | `[{debut, fin, x, y, large}]` | (facultatif) recadrer un plan : `x`, `y` = position du visage à suivre en fraction de l'image source (0 = gauche / haut), `large: true` pour un plan large ; voir `clips/<clip>/plans.json` |
| `mots_cles` | `[texte]` | en minuscules, tels que prononcés ; mis en rouge et en grand |
| `inserts` | `[{type, debut, fin, …params, declencheurs}]` | motions plein écran (voir `python -m editfou gabarits`) |
| `surimpressions` | idem | éléments sur l'A-roll : `pastille`, `compteur`, `souligne` |
| `musique` | booléen | nappe musicale sous la voix (défaut `true`) |
| `statut` | `brouillon` / `valide` | **l'IA écrit `brouillon` ; seul l'utilisateur valide** |

Contrôle : `python -m editfou verifier <p> <clip>` (durées, chevauchements, paramètres, déclencheurs).

## Exemple validé — « Tu perds deux fois » (Edgar, 64 s de source → 54 s montées)

Transcription (extraits) : « J'ai probablement autant de situations difficiles que la plupart des gens. Je te dis la
vérité. La seule différence, c'est que les moments de torpeur ou les états difficiles, moi, j'y reste vraiment pas
plus d'une heure en général. […] Mon père, il meurt […] en pleine saison. […] il reste 20 dates. »

```json
{"clip": "c01", "titre": "Tu perds deux fois", "debut": 0.0, "fin": 64.26,
 "exclure": [[13.20, 13.90], [30.50, 31.10]],
 "teaser": [[52.74, 53.58], [56.00, 57.04]],
 "grave": [[52.70, 57.10]],
 "corrections": [{"temps": 25.78, "mot": "ce", "par": "subi"}, {"temps": 25.98, "mot": "vieux", "par": ""},
                 {"temps": 49.40, "mot": "qui", "par": "qu'il"}, {"temps": 61.62, "mot": "tournes.", "par": "tournes,"}],
 "mots_cles": ["vérité", "différence", "torpeur", "difficiles", "heure", "apprentissage", "balèze", "champions", "deux",
               "premier", "refuse", "meurt", "saison", "spectacles", "n'avances", "situation", "cool", "enchaîné",
               "subi", "vraiment", "vie", "deuxième", "captes", "dates", "20"],
 "inserts": [
  {"type": "courbe", "debut": 6.32, "fin": 9.30, "sens": "chute", "texte": "TORPEUR", "phrase": "les moments de",
   "declencheurs": {"impact": 7.36}},
  {"type": "horloge", "debut": 9.46, "fin": 12.38, "texte": "1 HEURE", "phrase": "j'y reste pas plus d'",
   "declencheurs": {"depart": 9.76, "arret": 11.86}},
  {"type": "mot_choc", "debut": 17.98, "fin": 20.12, "texte": "CHAMPIONS", "phrase": "les grands",
   "declencheurs": {"impact": 19.04}},
  {"type": "progression", "debut": 23.00, "fin": 24.44, "valeur": 100, "texte": "APPRENTISSAGE",
   "phrase": "mais c'est un", "declencheurs": {"depart": 23.32, "fin": 24.20}},
  {"type": "mot_choc", "debut": 29.24, "fin": 30.22, "texte": "DEUX FOIS", "phrase": "Tu perds",
   "declencheurs": {"impact": 29.86}},
  {"type": "comparaison", "debut": 31.34, "fin": 33.98, "avant": "×1", "apres": "×2", "phrase": "pas une,",
   "texte": "mais bien deux.", "declencheurs": {"avant": 31.40, "rature": 32.40, "apres": 33.58}},
  {"type": "chapitre", "debut": 34.70, "fin": 36.78, "numero": "01", "texte": "LE TRUC PAS COOL",
   "phrase": "d'abord", "declencheurs": {"impact": 35.08}},
  {"type": "chapitre", "debut": 39.44, "fin": 43.14, "numero": "02", "texte": "LA DITE SITUATION",
   "phrase": "et le deuxième", "declencheurs": {"impact": 39.66}},
  {"type": "mot_choc", "debut": 49.98, "fin": 50.94, "texte": "JE REFUSE", "sous_texte": "deux fois.",
   "declencheurs": {"impact": 50.10}},
  {"type": "chiffre", "debut": 61.78, "fin": 64.26, "valeur": 20, "texte": "DATES", "phrase": "il reste",
   "declencheurs": {"fin_compte": 63.58}}
 ],
 "surimpressions": [
  {"type": "souligne", "debut": 3.84, "fin": 4.20, "mot": "vérité", "declencheurs": {"mot": 3.84}},
  {"type": "pastille", "debut": 37.38, "fin": 38.42, "texte": "1", "declencheurs": {"impact": 37.60}},
  {"type": "pastille", "debut": 43.34, "fin": 47.08, "texte": "2", "declencheurs": {"impact": 43.40}},
  {"type": "compteur", "debut": 47.22, "fin": 49.02, "avant": "×1", "apres": "×2",
   "declencheurs": {"avant": 47.28, "rature": 47.62, "apres": 48.46}}
 ],
 "musique": true, "statut": "brouillon"}
```

Pourquoi ces choix :
- teaser = « Mon père, il meurt » + « en pleine saison » : la phrase la plus lourde, rejouée en ouverture ;
- `exclure` retire les relances de l'animatrice (« Sérieusement ? », « C'est vrai. ») ;
- chaque insert illustre la phrase en cours : torpeur → courbe qui plonge, « une heure » → horloge,
  « deux fois, pas une, mais bien deux » → ×1 barré / ×2, « d'abord / le deuxième » → chapitres 01 / 02,
  « il reste 20 dates » → compteur jusqu'à 20 ;
- les phrases d'émotion (« Mon père, il meurt… ») restent sur le visage, en N&B (`grave`) ;
- les corrections réparent « ce vieux » (entendu pour « subi ») et la ponctuation.
