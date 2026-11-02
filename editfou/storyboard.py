"""Étape « storyboard » : pour chaque clip validé, l'IA décide le montage dans clips/<id>/storyboard.json.
Tous les temps sont en secondes de la VIDÉO SOURCE (ceux de mots.json) ; le montage les convertit après la coupe
des blancs. Format complet et exemple : .claude/skills/editfou/references/storyboard.md.

{
  "clip": "c01", "titre": "Tu perds deux fois",
  "debut": 312.40, "fin": 381.90,             passage gardé (calé sur les mots)
  "exclure": [[330.1, 332.4]],                relances de l'intervieweur, redites, faux départs
  "teaser": [[361.2, 362.9]],                 1 à 3 plages (≈ 2 s en tout) rejouées en ouverture, N&B
  "grave": [[372.0, 376.5]],                  moment grave : N&B, poussée lente, musique coupée
  "corrections": [{"temps": 340.12, "mot": "ce", "par": "subi"}],     "par": "" supprime le mot
  "mots_cles": ["deux", "heure"],             mots mis en rouge et en grand dans le texte mot par mot
  "inserts": [{"type": "chiffre", "debut": 350.1, "fin": 351.9, "valeur": 20, "texte": "DATES",
               "declencheurs": {"fin_compte": 351.2}}],
  "surimpressions": [{"type": "pastille", "debut": 341.0, "fin": 344.0, "texte": "1"}],
  "musique": true,
  "statut": "brouillon"                       brouillon → valide (par l'utilisateur)
}
"""
import re

from . import ia
from .analyse import hms
from .gabarits import INSERTS, SURIMPRESSIONS, doc

NOMBRES = {'deux': 2, 'trois': 3, 'quatre': 4, 'cinq': 5, 'six': 6, 'sept': 7, 'huit': 8, 'neuf': 9, 'dix': 10,
           'onze': 11, 'douze': 12, 'quinze': 15, 'vingt': 20, 'trente': 30, 'quarante': 40, 'cinquante': 50,
           'cent': 100, 'mille': 1000}
propre = lambda m: re.sub(r'[.,?!;:«»"]', '', m).lower().strip()


def _requis(desc):
    return not desc.startswith('(option)')


def verifier(sb, p):
    """Liste des problèmes (vide = storyboard utilisable)."""
    err = []
    a, b = float(sb.get('debut', 0)), float(sb.get('fin', 0))
    duree_src = p.info().get('duree') or 1e9
    if not 0 <= a < b <= duree_src + 0.5:
        err.append('debut/fin invalides (%.2f–%.2f)' % (a, b))
    if not 8 <= b - a <= 240:
        err.append('durée du passage %.1f s hors de 8–240 s' % (b - a))

    def plages(cle):
        out = []
        for x in sb.get(cle) or []:
            if not (isinstance(x, (list, tuple)) and len(x) == 2 and float(x[0]) < float(x[1])):
                err.append('%s : plage invalide %r' % (cle, x))
            else:
                out.append((float(x[0]), float(x[1])))
        return out
    plages('exclure')
    tz = plages('teaser')
    if sum(y - x for x, y in tz) > 4.5:
        err.append('teaser trop long (%.1f s, viser ≈ 2 s)' % sum(y - x for x, y in tz))
    for x, y in plages('grave'):
        if x < a or y > b:
            err.append('grave hors du passage : %.2f–%.2f' % (x, y))
    for z in sb.get('cadrages') or []:
        if not {'debut', 'fin', 'x'} <= set(z) or not 0 <= float(z['x']) <= 1:
            err.append('cadrage invalide (debut, fin, x entre 0 et 1) : %r' % z)
    for c in sb.get('corrections') or []:
        if not {'temps', 'mot', 'par'} <= set(c):
            err.append('correction incomplète : %r' % c)

    def elements(cle, cat, dmin, dmax):
        prec = []
        for i, e in enumerate(sb.get(cle) or []):
            nom = '%s[%d] %s' % (cle, i, e.get('type'))
            if e.get('type') not in cat:
                err.append('%s : type inconnu (choix : %s)' % (nom, ', '.join(cat)))
                continue
            _, _, params, decl = cat[e['type']]
            x, y = float(e.get('debut', -1)), float(e.get('fin', -1))
            if not (a - 0.01 <= x < y <= b + 0.01):
                err.append('%s : %.2f–%.2f hors du passage ou vide' % (nom, x, y))
            elif not dmin <= y - x <= dmax:
                err.append('%s : durée %.2f s hors de %g–%g s' % (nom, y - x, dmin, dmax))
            for k, desc in params.items():
                if _requis(desc) and e['type'] != 'souligne' and e.get(k) in (None, ''):
                    err.append('%s : paramètre « %s » manquant' % (nom, k))
            d = e.get('declencheurs') or {}
            for k, desc in decl.items():
                if _requis(desc) and k not in d:
                    err.append('%s : déclencheur « %s » manquant' % (nom, k))
            for k, t in d.items():
                if not x - 0.01 <= float(t) <= y + 0.01:
                    err.append('%s : déclencheur %s=%.2f hors de %.2f–%.2f' % (nom, k, float(t), x, y))
            if cle == 'inserts':
                for x0, y0 in prec:
                    if x < y0 and y > x0:
                        err.append('%s : chevauche un autre insert' % nom)
                prec.append((x, y))
    elements('inserts', INSERTS, 0.5, 4.0)
    elements('surimpressions', SURIMPRESSIONS, 0.1, 30.0)
    return err


def brouillon_auto(p, c):
    """Storyboard minimal sans IA : coupe des blancs, texte mot par mot, un compteur par chiffre prononcé.
    Pas de teaser ni de moment grave : c'est le travail de l'IA (ou de l'utilisateur)."""
    mots = p.mots(c['debut'], c['fin'])
    inserts, cles = [], []
    for w in mots:
        m = propre(w['mot'])
        v = float(m.replace(',', '.')) if re.fullmatch(r'\d+([.,]\d+)?', m) else NOMBRES.get(m)
        if v is None or v < 2:
            continue
        x, y = round(max(c['debut'], w['debut'] - 0.6), 2), round(min(c['fin'], w['fin'] + 0.9), 2)
        if inserts and x < inserts[-1]['fin'] + 4:
            continue
        inserts.append({'type': 'chiffre', 'debut': x, 'fin': y, 'valeur': v,
                        'declencheurs': {'fin_compte': round(w['debut'] + 0.05, 2)}})
        cles.append(m)
    return {'clip': c['id'], 'titre': c.get('titre', ''), 'debut': c['debut'], 'fin': c['fin'], 'exclure': [],
            'teaser': [], 'grave': [], 'corrections': [], 'mots_cles': cles, 'inserts': inserts, 'surimpressions': [],
            'musique': True, 'statut': 'brouillon', 'auteur': 'auto'}


def mots_horodates(p, c):
    """Les mots du clip, un par ligne, pour l'IA : « début fin mot »."""
    lignes = []
    mots = p.mots(c['debut'], c['fin'])
    for w, s in zip(mots, mots[1:] + [None]):
        lignes.append('%.2f %.2f %s%s' % (w['debut'], w['fin'], w['mot'], '  (?)' if w.get('proba', 1) < 0.6 else ''))
        if s and s['debut'] - w['fin'] > 0.4:
            lignes.append('      … blanc %.1f s' % (s['debut'] - w['fin']))
    return '\n'.join(lignes)


CONSIGNES = """Tu es monteur·se de clips verticaux « niveau pro » (style Hossain / Edgar).
Écris le storyboard JSON du clip « {titre} » ({debut:.2f}–{fin:.2f} s de la source, {duree}).

Règles de la recette (validée) :
- Ouverture : un TEASER noir et blanc de ≈ 2 s = la phrase la plus choc du clip (1 à 3 plages de mots, prises
  n'importe où dans le passage), rejouée avant le récit. Pas de titre.
- Le moment le plus grave (s'il y en a un) passe en noir et blanc, la musique se tait (« grave »).
- Retirer (« exclure ») les relances d'un intervieweur, redites, faux départs.
- « mots_cles » : 1 mot par idée qui porte le sens (chiffres, émotions, verbes forts), en minuscules, tel qu'il est
  prononcé ; ils passent en rouge et en grand dans le texte mot par mot.
- Inserts plein écran : 1 toutes les 6 à 12 s environ, chacun illustre LITTÉRALEMENT ce qui est dit,
  commence sur le premier mot de la phrase et dure la phrase (0,8 à 2,5 s idéal, 4 s maximum), sans chevauchement.
  Les déclencheurs tombent sur la syllabe du mot (temps « début » du mot).
- Surimpressions légères sur l'A-roll quand ça aide (pastille de chapitre, compteur ×1 → ×2).
- Corriger les fautes évidentes de transcription (« corrections »).

{gabarits}

Format de sortie : UNIQUEMENT ce JSON (temps en secondes de la source, deux décimales) :
{{"clip": "{id}", "titre": "...", "debut": {debut:.2f}, "fin": {fin:.2f}, "exclure": [], "teaser": [[a, b]],
  "grave": [], "corrections": [], "mots_cles": [], "inserts": [{{"type": "...", "debut": a, "fin": b, "<param>": "...",
  "declencheurs": {{"<nom>": t}}}}], "surimpressions": [], "musique": true, "statut": "brouillon"}}

Mots du clip (« début fin mot ») :
{mots}
"""


def prompt(p, c):
    return CONSIGNES.format(titre=c.get('titre') or c['id'], debut=c['debut'], fin=c['fin'], id=c['id'],
                            duree=hms(c['fin'] - c['debut']), gabarits=doc(), mots=mots_horodates(p, c))


def ecrire(p, cid, sb):
    sb.setdefault('statut', 'brouillon')
    sb['clip'] = cid
    p.ecrire_storyboard(cid, sb)
    return verifier(sb, p)


def proposer_ia(p, cid, fournisseur=None):
    c = p.clip(cid)
    sb = ia.json_de(ia.demander(prompt(p, c), fournisseur))
    sb['auteur'] = 'ia:' + ia.disponible(fournisseur)
    return ecrire(p, cid, sb)
