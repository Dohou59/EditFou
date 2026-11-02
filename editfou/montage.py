"""Montage automatique d'un clip validé dans FilmCraft, d'après son storyboard (recette « Edgar ») :

1. coupe de tous les blancs (mots + silences mesurés), passages exclus retirés ;
2. recadrage 9:16 par plan sur le visage, deux cadrages en alternance à chaque coupe ;
3. teaser noir et blanc en ouverture (×1,12, lente poussée), moment grave en N&B ;
4. inserts plein écran et surimpressions natifs (gabarits.py), un bruitage par événement ;
5. texte mot par mot à hauteur de poitrine (Inter Black, mot-clé rouge en majuscules, fondu 0,15 s) ;
6. musique ≈ 13 dB sous la voix, coupée sur le moment grave ; export H.264, -14 LUFS.
Le projet .fcproj reste entièrement modifiable dans FilmCraft.
"""
import json, os, re, subprocess

from . import filmcraft as fc
from .analyse import assurer_mots, plans
from .cadrage import Cadreur, temps_montage, W, H
from .decoupe import plages_parlees
from .filmcraft import cmd, T, F
from .gabarits import INSERTS, SURIMPRESSIONS
from .motion import Scene, im, BLANC, ROUGE
from .storyboard import verifier, propre
from .texte import composer, placer, largeur, CAPITALE

BLANC_TEXTE, PETITE, GRANDE = '#FFFFFF', 50.0, 100.0
VIDES = set("le la les un une des de du d' l' à au aux en et ou que qui qu'il je tu il elle on ça c'est j'y y a "
            "mais ce se sa son ses mon ma mes ton ta tes t'as t'es dans pas plus est où après moi toi comme si fait "
            "pour par sur avec sans nous vous ils elles leur leurs cette ces cet très bien tout tous".split())
NIVEAU_MUSIQUE = -15.0


def _dans(t, plages, marge=0.0):
    return any(a - marge <= t < b for a, b in plages)


def preparer(p, cid, sb):
    """Découpe et chronologie, sans FilmCraft (rapide : sert aussi à l'aperçu de la durée)."""
    video = p.video()
    a, b = float(sb['debut']), float(sb['fin'])
    exclure = [tuple(x) for x in sb.get('exclure') or []]
    teaser = [tuple(x) for x in sb.get('teaser') or []]
    assurer_mots(p, a, b)
    for x, y in teaser:
        assurer_mots(p, x, y)
    tous = p.mots()
    mots = [w for w in tous if a - 0.01 <= w['debut'] < b and not _dans(w['debut'], exclure)]
    if not mots:
        raise ValueError('aucun mot dans le passage %.2f–%.2f' % (a, b))
    duree_src = p.info().get('duree') or 1e9
    fin_rush = round(min(mots[-1]['fin'] + 0.4, b + 0.4, duree_src), 3)
    lo = min([a] + [x for x, _ in teaser]) - 0.5
    hi = max([fin_rush] + [y for _, y in teaser]) + 0.5
    analyse = plans(video, max(0.0, lo), min(hi, duree_src), p.chemin('clips', cid, 'plans.json'))
    garde = plages_parlees(mots, fin_rush, exclure, p.chemin('voix16k.wav'))
    cad = Cadreur(analyse).auto()
    for z in sb.get('cadrages') or []:                  # plans larges à deux : cadrer celui qui parle
        cad.zone(float(z['debut']), float(z['fin']), float(z['x']), float(z.get('y', 0.38)), large=bool(z.get('large')))
    TL0, D0 = cad.chronologie(cad.decouper(garde))
    OUV, OFF = cad.chronologie(cad.decouper(teaser, zoom=1.12)) if teaser else ([], 0.0)
    TL = OUV + [(round(o + OFF, 3), x, y, s, tx, ty) for o, x, y, s, tx, ty in TL0]
    return {'video': video, 'mots': mots, 'tous': tous, 'cad': cad, 'TL0': TL0, 'OUV': OUV, 'OFF': OFF, 'TL': TL,
            'DUREE': round(OFF + D0, 3), 'T': temps_montage(TL0, OFF), 'exclure': exclure, 'fin_rush': fin_rush}


def _aroll(s, d, sb):
    cad, grave = d['cad'], [tuple(x) for x in sb.get('grave') or []]
    for i, (o, x, y, sc, tx, ty) in enumerate(d['TL']):
        i0, i1 = im(o), im(o + y - x)
        if i1 <= i0:
            continue
        r = cmd('timeline.place', {'item': s.item(d['video']), 'track': 'V1', 'time': i0 * F,
                                   'sourceIn': round(x * T), 'duration': (i1 - i0) * F, 'audio': True})
        clips = r.get('clips') or []
        if not clips:
            raise fc.Erreur('placement refusé : %s à %.2f' % (d['video'], x))
        c = clips[0]
        pct, pos = cad.motion_filmcraft(sc, tx, ty)
        cmd('effects.setParam', {'clip': c, 'effect': 'motion', 'param': 'position', 'value': pos})
        if i < len(d['OUV']) or _dans(x, grave):          # noir et blanc + lente poussée
            cmd('effects.apply', {'clips': [c], 'effect': 'black_white'})
            for t, v in ((i0, pct), (i1 - 1, round(pct * 1.07, 3))):
                cmd('effects.setParam', {'clip': c, 'effect': 'motion', 'param': 'scale', 'value': v,
                                         'keyframe': True, 'time': t * F})
        else:
            cmd('effects.setParam', {'clip': c, 'effect': 'motion', 'param': 'scale', 'value': pct})
        s.occupe[0].append((i0, i1))


def _musique(s, d, sb):
    m = s.sons.get('musique')
    if not m or not sb.get('musique', True):
        return
    Tm, OFF, D = d['T'], d['OFF'], d['DUREE']
    trous = sorted((Tm(x), Tm(y)) for x, y in sb.get('grave') or [])
    t, src = OFF, 0.0
    for x, y in trous + [(D, D)]:
        fin = x - 0.1
        while fin - t > 1.0:
            dispo = m['duree'] - 0.05 - src
            if dispo < 1.0:
                src, dispo = 0.0, m['duree'] - 0.05          # musique trop courte : on la reprend du début
            n = min(fin - t, dispo)
            s.place_audio(m['fichier'], t, src, n, piste='A2',
                          fondus=[(t, -60.0), (t + 0.6, NIVEAU_MUSIQUE), (t + n - 0.5, NIVEAU_MUSIQUE),
                                  (t + n - 1 / 30, -60.0)])
            t, src = t + n, src + n
        t, src = y + 0.3, src + (y + 0.3 - x)


def _motions(s, d, sb, cat, plein=None):
    Tm = d['T']
    for e in sb.get(cat) or []:
        fn = (INSERTS if cat == 'inserts' else SURIMPRESSIONS)[e['type']][0]
        if fn is None:
            continue
        a, b = Tm(float(e['debut'])), Tm(float(e['fin']))
        if b - a < 0.4:
            print('  %s %s ignoré : le passage a été coupé au montage' % (cat, e['type']))
            continue
        decl = {k: Tm(float(v)) for k, v in (e.get('declencheurs') or {}).items()}
        params = {k: v for k, v in e.items() if k not in ('type', 'debut', 'fin', 'declencheurs')}
        fn(s, a, b, params, decl)
        if plein is not None:
            plein.append((a, b))


def _sous_titres(s, d, sb, plein):
    """Texte mot par mot. Renvoie {(mot-clé, temps source): (début, fin, boîte px)} pour les soulignés."""
    Tm, OFF, cad, TL = d['T'], d['OFF'], d['cad'], d['TL']
    corr = sb.get('corrections') or []

    def corrige(w):
        for c in corr:
            if abs(float(c['temps']) - w['debut']) < 0.08 and propre(c['mot']) == propre(w['mot']):
                return c['par']
        return w['mot']

    vus = []
    for o, x, y, *_ in d['OUV']:
        vus += [(corrige(w), o + w['debut'] - x, o + w['fin'] - x, w['debut']) for w in d['tous']
                if x <= w['debut'] < y - 0.05]
    for w in d['mots']:
        txt = corrige(w)
        if txt and txt.strip('?!.,…'):
            vus.append((txt, Tm(w['debut']), Tm(w['fin']), w['debut']))
    vus = [v for v in vus if not _dans(v[1], plein, 0.05)]

    blocs, cur = [], []
    for w in vus:
        if cur and (w[1] - cur[-1][2] > 0.35 or len(cur) >= 5 or w[1] - cur[0][1] > 1.9 or cur[-1][0][-1] in '.?!,…'
                    or ((cur[0][1] < OFF) != (w[1] < OFF)) or _dans((cur[-1][2] + w[1]) / 2, plein)):
            blocs.append(cur); cur = []
        cur.append(w)
    if cur:
        blocs.append(cur)

    def cadrage_a(t):
        for o, a, b, sc, tx, ty in TL:
            if o <= t < o + b - a:
                return a + t - o, sc, tx, ty
        o, a, b, sc, tx, ty = TL[-1]
        return b, sc, tx, ty

    cles = [propre(m) for m in sb.get('mots_cles') or []]
    blanc_seul = [(0.0, OFF)] + [(Tm(x), Tm(y)) for x, y in sb.get('grave') or []]
    boites = {}
    for i, g in enumerate(blocs):
        textes = [re.sub(r'[.,?!…]+$', '', x[0]) or x[0] for x in g]
        cle = next((k for c in cles for k, x in enumerate(g) if propre(x[0]) == c), None)
        if cle is None:                                   # sinon le mot plein le plus long
            pleins = [k for k, x in enumerate(g) if propre(x[0]) not in VIDES and len(propre(x[0])) >= 4]
            cle = max(pleins, key=lambda k: len(textes[k]), default=None)
        fin = min(blocs[i + 1][0][1] - 0.02 if i + 1 < len(blocs) else d['DUREE'], g[-1][2] + 0.45)
        fin = min([fin] + [a for a, b in plein if g[0][1] < a < fin])
        ts, sc, tx, ty = cadrage_a(g[0][1])
        haut = min(max(cad.menton(ts, sc, tx, ty) + 45, 1080), 1420)   # sous le menton, à la poitrine
        centre = W / 2 + 0.25 * (cad.x_visage(ts, sc, tx) - W / 2)     # légèrement vers le visage
        accent = BLANC_TEXTE if _dans(g[0][1], blanc_seul) else ROUGE
        pos, _ = placer(composer(textes, cle, PETITE, GRANDE), haut, centre)
        for k, txt, corps, x, base, est_cle in pos:
            d0 = max(0.0, g[k][1] - 0.02)
            if fin - d0 < 0.06:
                continue
            c = s.mot(d0, fin, txt, x, base, corps, accent if est_cle else BLANC_TEXTE)
            s.opacite(c, [(d0, 0), (d0 + 0.15, 100)])
            if est_cle:
                w = largeur('inter', txt, corps)
                boites[(propre(g[k][0]), round(g[k][3], 2))] = (g[k][1], fin, (x - w / 2, base - CAPITALE * corps,
                                                                               x + w / 2, base))
    return len(blocs), boites


def _soulignes(s, d, sb, boites):
    for e in sb.get('surimpressions') or []:
        if e.get('type') != 'souligne':
            continue
        t = float((e.get('declencheurs') or {}).get('mot', e.get('debut', 0)))
        cand = [(abs(ts - t), k) for k in boites for (m, ts) in [k] if m == propre(e.get('mot', '')) and abs(ts - t) < 0.5]
        if not cand:
            print('  souligné « %s » ignoré : ce mot n’est pas mot-clé de son bloc' % e.get('mot'))
            continue
        a, b, (x0, y0, x1, y1) = boites[min(cand)[1]]
        ta = a + 0.12
        if b - ta > 0.2:
            s.barre(ta, b, x0, y1 + 22, x1 - x0, 12, ROUGE, t=ta, duree=6)
            s.son('clic', ta, -10)


def monter(p, cid, exporter=True, force=False, journal=None):
    sb = p.storyboard(cid)
    if not sb:
        raise ValueError('pas de storyboard pour %s' % cid)
    if sb.get('statut') != 'valide' and not force:
        raise ValueError('storyboard %s pas encore validé (statut : %s)' % (cid, sb.get('statut')))
    err = verifier(sb, p)
    if err:
        raise ValueError('storyboard invalide :\n- ' + '\n- '.join(err))
    p.etat('montage', 'en_cours', 'Découpe et recadrage de %s…' % cid)
    d = preparer(p, cid, sb)
    print('%s : %.2f s (dont teaser %.2f s), %d morceaux' % (cid, d['DUREE'], d['OFF'], len(d['TL'])))

    p.etat('montage', 'en_cours', 'Construction dans FilmCraft de %s…' % cid)
    fc.assurer()
    s = Scene('%s %s' % (p.slug, cid), d['DUREE'])
    _aroll(s, d, sb)
    if d['OFF']:
        s.son('braam', 0.0, -8)            # le teaser s'ouvre sur un braam…
        s.son('whoosh', d['OFF'], -8)      # …et bascule sur le récit en couleur
    _musique(s, d, sb)
    plein = []
    _motions(s, d, sb, 'inserts', plein)
    n_blocs, boites = _sous_titres(s, d, sb, plein)
    _motions(s, d, sb, 'surimpressions')
    _soulignes(s, d, sb, boites)
    projet = p.chemin('clips', cid, 'montage.fcproj')
    s.enregistrer(projet)
    bilan = {'duree': d['DUREE'], 'ouverture': d['OFF'], 'morceaux': len(d['TL']), 'inserts': plein,
             'blocs_texte': n_blocs, 'sons_manquants': sorted(s.manquants), 'projet': projet}
    p.ecrire(os.path.join('clips', cid, 'montage.json'), dict(bilan, TL=d['TL']))
    print('projet FilmCraft : %s — %d inserts, %d blocs de texte%s' % (
        projet, len(plein), n_blocs, (', sons absents : ' + ', '.join(sorted(s.manquants))) if s.manquants else ''))
    p.maj_clip(cid, monte=False)
    if exporter:
        exporter_clip(p, cid, journal)
    p.etat('montage', 'fait', 'Clip %s monté' % cid)
    return bilan


def exporter_clip(p, cid, journal=None):
    p.etat('montage', 'en_cours', 'Export de %s…' % cid)
    sortie = p.rendu(cid)
    fc.exporter(p.chemin('clips', cid, 'montage.fcproj'), sortie, journal)
    duree = json.loads(open(p.chemin('clips', cid, 'montage.json'), encoding='utf-8').read())['duree']
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(min(duree / 2, d_apercu(duree))), '-i', sortie,
                    '-frames:v', '1', '-vf', 'scale=360:-1', p.chemin('clips', cid, 'apercu.jpg')])
    p.maj_clip(cid, monte=True)
    print('vidéo : %s' % sortie)
    return sortie


def d_apercu(duree):
    return max(0.5, min(3.0, duree / 3))
