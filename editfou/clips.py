"""Étape « clips » : choisir les moments à transformer en clips verticaux, puis les faire valider.

L'IA (agent ou fournisseur intégré) lit phrases.txt et écrit clips.json :
  {"clips": [{"id": "c01", "debut": 312.4, "fin": 381.9, "titre": "...", "accroche": "...", "raison": "...",
              "score": 8, "statut": "propose"}]}
`normaliser` cale ensuite chaque début / fin sur les mots, vérifie les durées et numérote.
Statuts : propose → valide ou rejete (par l'utilisateur, jamais par l'IA).
"""
from . import ia
from .analyse import hms, phrases

CONSIGNES = """Tu es monteur·se de clips viraux (TikTok, Reels, Shorts) en français.
Voici la transcription horodatée d'une vidéo : « {titre} » ({duree}).
Trouve les {n} meilleurs moments à transformer en clips verticaux autonomes.

Un bon clip :
- commence par une phrase forte qui accroche dans les 2 premières secondes (pas de « euh », pas de contexte manquant) ;
- raconte une idée complète : tension, exemple ou preuve, chute nette ; il se comprend sans le reste de la vidéo ;
- dure entre {dmin} et {dmax} secondes ; se termine à la fin d'une phrase ;
- contient des émotions, des chiffres, des images concrètes, une opinion tranchée ou une leçon claire ;
- ne chevauche pas un autre clip.

Réponds UNIQUEMENT par du JSON, sans commentaire :
{{"clips": [{{"debut": <secondes>, "fin": <secondes>, "titre": "<titre court, 6 mots max>",
  "accroche": "<la première phrase du clip>", "raison": "<pourquoi ça marche, 1 phrase>", "score": <1 à 10>}}]}}
Utilise exactement les temps de la transcription (début d'une phrase, fin d'une phrase).

Transcription (« [début–fin] (mm:ss) texte ») :
{transcription}
"""


def prompt(p, n='5 à 8', dmin=30, dmax=90):
    i = p.info()
    lignes = '\n'.join('[%.2f–%.2f] (%s) %s' % (a, b, hms(a), t) for a, b, t in phrases(p.mots()))
    return CONSIGNES.format(titre=i.get('titre') or p.slug, duree=hms(i.get('duree') or 0), n=n, dmin=dmin,
                            dmax=dmax, transcription=lignes)


def normaliser(p, proposes, dmin=10, dmax=180):
    """Cale les clips sur les mots, retire les doublons et chevauchements, numérote c01, c02…
    Les clips déjà validés ou rejetés gardent leur statut et leur identifiant."""
    mots = p.mots()
    if not mots:
        raise ValueError('pas de transcription')
    anciens = {(round(c['debut'], 1), round(c['fin'], 1)): c for c in p.clips()}
    out = []
    for c in sorted(proposes, key=lambda c: float(c['debut'])):
        a, b = sorted((float(c['debut']), float(c['fin'])))
        dans = [w for w in mots if w['debut'] >= a - 0.4 and w['fin'] <= b + 0.6]
        if not dans:
            continue
        a, b = round(dans[0]['debut'], 2), round(dans[-1]['fin'], 2)
        if not dmin <= b - a <= dmax:
            continue
        if out and a < out[-1]['fin'] - 0.5:
            continue
        ancien = anciens.get((round(a, 1), round(b, 1)), {})
        out.append({'debut': a, 'fin': b, 'titre': c.get('titre', '').strip(), 'accroche': c.get('accroche', '').strip(),
                    'raison': c.get('raison', '').strip(), 'score': c.get('score'),
                    'statut': ancien.get('statut', 'propose'), 'id': ancien.get('id')})
    pris = {c['id'] for c in out if c['id']}
    n = 1
    for c in out:
        if not c['id']:
            while 'c%02d' % n in pris:
                n += 1
            c['id'] = 'c%02d' % n
            pris.add(c['id'])
        c['texte'] = ' '.join(w['mot'] for w in mots if c['debut'] <= w['debut'] < c['fin'])
    return out


def enregistrer(p, proposes):
    clips = normaliser(p, proposes)
    p.ecrire('clips.json', {'clips': clips})
    p.etat('clips', 'fait' if clips else 'erreur',
           '%d clips proposés : à valider' % len(clips) if clips else 'aucun clip retenu')
    return clips


def proposer_ia(p, fournisseur=None):
    p.etat('clips', 'en_cours', "L'IA cherche les meilleurs moments…")
    r = ia.json_de(ia.demander(prompt(p), fournisseur))
    return enregistrer(p, r['clips'] if isinstance(r, dict) else r)
