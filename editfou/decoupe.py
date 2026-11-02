"""Ce qu'on garde du passage : les mots prononcés, moins les passages exclus et les silences mesurés à l'énergie.
Recette ClaudeCut validée sur « Edgar » : chaque mot de 0,05 s avant à 0,08 s après, recollés si l'écart est court.
"""
import numpy as np

from .analyse import lire_wav


def silences_energie(wav, debut, fin, seuil_min=0.35):
    """Plages muettes de [debut, fin] (temps de la source) d'après l'énergie : rattrape les mots que Whisper étire."""
    x, sr = lire_wav(wav, debut, fin)
    n = int(sr * 0.02)
    if len(x) < n * 10:
        return []
    rms = np.sqrt(np.mean(x[:len(x) // n * n].reshape(-1, n) ** 2, axis=1)) + 1e-9
    db = 20 * np.log10(rms)
    seuil = max(np.percentile(db, 10) + 10, db.max() - 38)
    muet = db < seuil
    out, i = [], 0
    while i < len(muet):
        if muet[i]:
            j = i
            while j < len(muet) and muet[j]:
                j += 1
            if (j - i) * 0.02 >= seuil_min:
                out.append((debut + i * 0.02, debut + j * 0.02))
            i = j
        else:
            i += 1
    return out


def soustraire(plages, trous):
    for t0, t1 in trous:
        nv = []
        for a, b in plages:
            if t1 <= a or t0 >= b:
                nv.append((a, b))
            else:
                if t0 > a:
                    nv.append((a, t0))
                if t1 < b:
                    nv.append((t1, b))
        plages = nv
    return plages


def plages_parlees(mots, fin_rush, exclure=(), wav=None, souffle=0.12, min_morceau=0.18):
    """Plages de la source à garder ; `mots` ne contient que ceux du passage."""
    garde = []
    for w in mots:
        a, b = max(0.0, w['debut'] - 0.05), min(fin_rush, w['fin'] + 0.08)
        if a >= fin_rush:
            break
        if garde and a - garde[-1][1] <= souffle:
            garde[-1] = (garde[-1][0], max(garde[-1][1], b))
        else:
            garde.append((a, b))
    if not garde:
        return []
    garde[-1] = (garde[-1][0], fin_rush)
    garde = soustraire(garde, exclure)
    if wav:
        garde = soustraire(garde, [(a + 0.08, b - 0.08) for a, b in silences_energie(wav, garde[0][0], fin_rush)])
    return [(round(a, 3), round(b, 3)) for a, b in garde if b - a >= min_morceau]
