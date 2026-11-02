"""Analyse d'une source : téléchargement (yt-dlp) ou fichier local, voix 16 kHz, transcription mot à mot
(faster-whisper, CPU), phrases horodatées pour l'IA, et plans + visages d'un passage (OpenCV) au moment du montage.
"""
import json, os, subprocess, sys, time, wave

import numpy as np

from .config import C


# ------------------------------------------------------------------ récupération
def telecharger(p):
    """Télécharge la vidéo du lien (≤ 1080p, MP4) dans le projet. Repris de l'idée d'OpenClip (yt-dlp)."""
    info = p.info()
    if info.get('local'):
        p.maj_info(video=info['source'], titre=info.get('titre') or os.path.splitext(os.path.basename(info['source']))[0],
                   duree=duree_video(info['source']))
        return info['source']
    sortie = p.chemin('source.mp4')
    if os.path.isfile(sortie):
        return sortie
    import yt_dlp

    def progres(d):
        if d.get('status') == 'downloading':
            tot = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
            p.etat('telechargement', 'en_cours', 'Téléchargement…', round(100 * d.get('downloaded_bytes', 0) / tot))

    opts = {'format': 'bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/bv*[height<=1080]+ba/b',
            'merge_output_format': 'mp4', 'outtmpl': p.chemin('source.%(ext)s'), 'quiet': True,
            'noprogress': True, 'progress_hooks': [progres], 'noplaylist': True}
    with yt_dlp.YoutubeDL(opts) as y:
        r = y.extract_info(info['source'], download=True)
    if not os.path.isfile(sortie):
        autres = [f for f in os.listdir(p.dossier) if f.startswith('source.')]
        if not autres:
            raise RuntimeError('téléchargement sans fichier MP4')
        os.replace(p.chemin(autres[0]), sortie)
    p.maj_info(video=sortie, titre=info.get('titre') or r.get('title', ''), duree=r.get('duration') or duree_video(sortie),
               chaine=r.get('channel') or r.get('uploader', ''))
    return sortie


def duree_video(f):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f],
                       capture_output=True, text=True)
    try:
        return round(float(r.stdout.strip()), 3)
    except ValueError:
        return 0.0


# ------------------------------------------------------------------ voix et transcription
def extraire_voix(video, wav):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', video, '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le',
                    wav], check=True)


def lire_wav(wav, debut=0.0, fin=None):
    """Échantillons float32 de [debut, fin] (s). On lit le PCM soi-même : certains paquets `av` ne sont pas
    compatibles avec faster-whisper."""
    with wave.open(wav) as w:
        sr = w.getframerate()
        i0 = int(debut * sr)
        n = w.getnframes() - i0 if fin is None else int((fin - debut) * sr)
        w.setpos(max(0, min(i0, w.getnframes())))
        x = np.frombuffer(w.readframes(max(0, n)), dtype=np.int16).astype(np.float32) / 32768
    return x, sr


def transcrire(p, modele=None, langue=None):
    from faster_whisper import WhisperModel
    t0 = time.time()
    son, _ = lire_wav(p.chemin('voix16k.wav'))
    duree = len(son) / 16000
    m = WhisperModel(modele or C['modele_whisper'], device='cpu', compute_type='int8')
    segs, _ = m.transcribe(son, language=langue or C['langue'], word_timestamps=True, vad_filter=False, beam_size=5)
    mots = []
    for s in segs:
        mots += [{'mot': w.word.strip(), 'debut': round(w.start, 3), 'fin': round(w.end, 3),
                  'proba': round(w.probability, 2)} for w in s.words]
        p.etat('transcription', 'en_cours', 'Transcription… %d mots' % len(mots), round(100 * s.end / max(duree, 1)))
    mots = nettoyer(mots)
    p.ecrire('mots.json', mots)
    ecrire_phrases(p, mots)
    print('transcription : %d mots en %d s' % (len(mots), time.time() - t0))
    return mots


def nettoyer(brut):
    """Recolle les jetons coupés par Whisper (« J » + « 'ai », « -à »)."""
    mots = []
    for w in brut:
        t = w['mot']
        if not t:
            continue
        if mots and t[:1] in ("'", '-', '’'):
            mots[-1]['mot'] += t
            mots[-1]['fin'] = w['fin']
        else:
            mots.append(dict(w))
    return mots


def phrases(mots, ecart=0.6, max_duree=12.0):
    """Regroupe les mots en phrases [(debut, fin, texte)] : ponctuation forte, blanc > ecart, ou trop long."""
    out, cur = [], []
    for w in mots:
        if cur and (w['debut'] - cur[-1]['fin'] > ecart or w['fin'] - cur[0]['debut'] > max_duree):
            out.append(cur); cur = []
        cur.append(w)
        if w['mot'][-1:] in '.?!':
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return [(g[0]['debut'], g[-1]['fin'], ' '.join(x['mot'] for x in g)) for g in out]


def hms(t):
    return '%d:%02d:%04.1f' % (t // 3600, t % 3600 // 60, t % 60) if t >= 3600 else '%d:%04.1f' % (t // 60, t % 60)


def ecrire_phrases(p, mots):
    with open(p.chemin('phrases.txt'), 'w', encoding='utf-8') as o:
        o.write('# %s — %d mots. [début–fin en secondes] (mm:ss) texte\n' % (p.info().get('titre', p.slug), len(mots)))
        for a, b, t in phrases(mots):
            o.write('[%.2f–%.2f] (%s) %s\n' % (a, b, hms(a), t))


def analyser(p, modele=None, langue=None):
    """Téléchargement + voix + transcription. Chaque étape déjà faite est sautée."""
    p.etat('telechargement', 'en_cours', 'Récupération de la vidéo…')
    video = telecharger(p)
    p.etat('transcription', 'en_cours', 'Extraction de la voix…')
    if not os.path.isfile(p.chemin('voix16k.wav')):
        extraire_voix(video, p.chemin('voix16k.wav'))
    if not os.path.isfile(p.chemin('mots.json')):
        transcrire(p, modele, langue)
    elif not os.path.isfile(p.chemin('phrases.txt')):
        ecrire_phrases(p, p.mots())
    p.etat('clips', 'attente_ia', "Transcription prête : l'IA peut proposer les clips")


# ------------------------------------------------------------------ plans et visages d'un passage
def plans(video, debut, fin, sortie=None):
    """Coupes d'image (histogramme HSV) + visage principal par plan (cascades de Haar, face puis profils)
    sur [debut, fin] de la source. x/y_visage en fraction de l'image ; taille_visage = largeur du visage / largeur
    de l'image (≥ 0,1 : plan serré). Temps de la source."""
    import cv2
    if sortie and os.path.isfile(sortie):
        with open(sortie) as f:
            d = json.load(f)
        if abs(d.get('debut', -1) - debut) < 0.01 and abs(d.get('fin', -1) - fin) < 0.01:
            return d
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    faces = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    profils = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
    i = int(debut * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, i)
    coupes, prec, det, k = [round(debut, 3)], None, {}, 0
    while i / fps < fin:
        ok, img = cap.read()
        if not ok:
            break
        t = i / fps
        hsv = cv2.cvtColor(cv2.resize(img, (160, 90)), cv2.COLOR_BGR2HSV)
        h = cv2.calcHist([hsv], [0, 1], None, [16, 8], [0, 180, 0, 256]); cv2.normalize(h, h)
        if prec is not None and cv2.compareHist(prec, h, cv2.HISTCMP_BHATTACHARYYA) > 0.35 and t - coupes[-1] > 0.4:
            coupes.append(round(t, 3))
        prec = h
        if k % 5 == 0:
            g = cv2.cvtColor(cv2.resize(img, (W // 2, H // 2)), cv2.COLOR_BGR2GRAY)
            f = list(faces.detectMultiScale(g, 1.1, 5, minSize=(30, 30)))
            if not f:
                f = list(profils.detectMultiScale(g, 1.1, 5, minSize=(30, 30)))
                f += [(g.shape[1] - x - w, y, w, hh) for (x, y, w, hh) in
                      profils.detectMultiScale(cv2.flip(g, 1), 1.1, 5, minSize=(30, 30))]
            det[t] = [((x + w / 2) * 2 / W, (y + hh / 2) * 2 / H, w * 2 / W) for (x, y, w, hh) in f]
        i += 1; k += 1
    coupes.append(round(min(fin, i / fps), 3))
    out = []
    for a, b in zip(coupes, coupes[1:]):
        ds = [d for t, v in det.items() if a <= t < b for d in v]
        if ds:
            grand = max(d[2] for d in ds)
            prin = [d for d in ds if d[2] > 0.6 * grand]
            x = float(np.median([d[0] for d in prin])); y = float(np.median([d[1] for d in prin]))
            nb = len({round(d[0], 1) for d in ds if d[2] > 0.5 * grand})
        else:
            x, y, grand, nb = 0.5, 0.4, 0, 0
        out.append({'debut': a, 'fin': b, 'x_visage': round(x, 3), 'y_visage': round(y, 3),
                    'taille_visage': round(grand, 3), 'nb_visages': nb})
    d = {'largeur': W, 'hauteur': H, 'fps': fps, 'debut': debut, 'fin': fin, 'plans': out}
    if sortie:
        with open(sortie, 'w') as f:
            json.dump(d, f, indent=1)
    return d


if __name__ == '__main__':
    sys.exit('utiliser : python -m editfou analyser <projet>')
