"""Analyse d'une source, dans l'ordre le plus rapide pour arriver au choix des clips :

1. lien YouTube : sous-titres (manuels, sinon automatiques) en quelques secondes → mots_approx.json, phrases.txt :
   l'IA peut déjà choisir les clips ;
2. audio seul → voix16k.wav ; sans sous-titres (ou fichier local), transcription Whisper complète ;
3. vidéo H.264 ≤ 1080p téléchargée ensuite (pendant qu'on valide les clips), réunie avec l'audio dans source.mp4 ;
4. transcription Whisper mot à mot précise seulement sur les passages des clips (`assurer_mots`) ;
5. plans + visages d'un passage (OpenCV), au moment du montage.
"""
import glob, json, os, shutil, subprocess, sys, time, wave

import numpy as np

from .config import C

FORMAT_VIDEO = ('bv*[height<=1080][vcodec^=avc1][protocol^=http]/bv*[height<=1080][vcodec^=avc1]/'
                'bv*[height<=1080][ext=mp4]/bv*[height<=1080]')


# ------------------------------------------------------------------ récupération
def _ytdlp(p, extra, progres=None):
    import yt_dlp
    opts = {'quiet': True, 'noprogress': True, 'noplaylist': True,
            # connexion instable : on réessaie et on reprend là où on s'était arrêté
            'socket_timeout': 30, 'retries': 15, 'fragment_retries': 15, 'continuedl': True}
    if shutil.which('node'):                       # YouTube demande un moteur JavaScript (deno par défaut)
        opts['js_runtimes'] = {'node': {'path': None}}
        opts['remote_components'] = ['ejs:github']  # script officiel de yt-dlp qui résout les défis « n »
    if progres:
        opts['progress_hooks'] = [progres]
    opts.update(extra)
    with yt_dlp.YoutubeDL(opts) as y:
        return y.extract_info(p.info()['source'], download=True)


def _suivi(p, quoi):
    """Progression du téléchargement dans info.json (une fois par seconde), sans toucher à l'étape en cours."""
    dernier = [0.0]

    def progres(d):
        if d.get('status') == 'downloading' and time.time() - dernier[0] > 1.0:
            dernier[0] = time.time()
            tot = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
            p.maj_info(telechargement={'quoi': quoi, 'pourcent': round(100 * d.get('downloaded_bytes', 0) / tot)})
    return progres


def sous_titres(p, langue):
    """Sous-titres YouTube en json3 → mots au minutage approximatif. Les automatiques donnent un temps par mot ;
    les manuels un temps par ligne, réparti sur ses mots."""
    langues = [langue, langue + '-orig', langue + '-' + langue.upper(), langue + '.*']
    r = _ytdlp(p, {'skip_download': True, 'writesubtitles': True, 'writeautomaticsub': True,
                   'subtitlesformat': 'json3', 'subtitleslangs': langues, 'outtmpl': p.chemin('st', '%(id)s')})
    p.maj_info(titre=p.info().get('titre') or r.get('title', ''), duree=r.get('duration') or 0,
               chaine=r.get('channel') or r.get('uploader', ''))
    fichiers = sorted(glob.glob(p.chemin('st', '*.json3')), key=lambda f: ('orig' in f, len(f)))
    if not fichiers:
        return []
    with open(fichiers[0], encoding='utf-8') as fh:
        events = json.load(fh).get('events', [])
    mots = []
    for e in events:
        t0, d = e.get('tStartMs', 0) / 1000, e.get('dDurationMs', 0) / 1000
        segs = [s for s in e.get('segs') or [] if str(s.get('utf8', '')).strip()]
        for i, s in enumerate(segs):
            debut = t0 + s.get('tOffsetMs', 0) / 1000
            fin = t0 + segs[i + 1].get('tOffsetMs', 0) / 1000 if i + 1 < len(segs) else t0 + max(d, 0.3)
            ms = s['utf8'].split()
            pas = max(fin - debut, 0.05 * len(ms)) / len(ms)
            for k, m in enumerate(ms):
                mots.append({'mot': m, 'debut': round(debut + k * pas, 3), 'fin': round(debut + (k + 1) * pas, 3)})
    mots.sort(key=lambda w: w['debut'])
    for a, b in zip(mots, mots[1:]):                 # chaque mot s'arrête au début du suivant (au plus 1,2 s)
        a['fin'] = round(max(a['debut'] + 0.05, min(a['fin'], b['debut'], a['debut'] + 1.2)), 3)
    return mots


def telecharger_audio(p):
    f = p.chemin('voix16k.wav')
    if os.path.isfile(f):
        return f
    _ytdlp(p, {'format': 'ba[ext=m4a]/ba', 'outtmpl': p.chemin('audio.%(ext)s')}, _suivi(p, 'audio'))
    src = [x for x in glob.glob(p.chemin('audio.*')) if not x.endswith('.part')]
    if not src:
        raise RuntimeError('téléchargement de l’audio sans fichier')
    extraire_voix(src[0], f + '.tmp.wav')
    os.replace(f + '.tmp.wav', f)
    return f


def telecharger_video(p):
    """Vidéo H.264 ≤ 1080p (FilmCraft et OpenCV lisent mal l'AV1), réunie avec l'audio déjà téléchargé."""
    info = p.info()
    if info.get('local'):
        p.maj_info(video=info['source'], titre=info.get('titre') or os.path.splitext(os.path.basename(info['source']))[0],
                   duree=duree_video(info['source']))
        return info['source']
    sortie = p.chemin('source.mp4')
    if os.path.isfile(sortie):
        return sortie
    telecharger_audio(p)
    _ytdlp(p, {'format': FORMAT_VIDEO, 'outtmpl': p.chemin('image.%(ext)s')}, _suivi(p, 'vidéo'))
    image = [f for f in glob.glob(p.chemin('image.*')) if not f.endswith('.part')]
    audio = [f for f in glob.glob(p.chemin('audio.*')) if not f.endswith('.part')]
    if not image or not audio:
        raise RuntimeError('téléchargement de la vidéo incomplet')
    tmp = p.chemin('source.tmp.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', image[0], '-i', audio[0], '-map', '0:v:0', '-map', '1:a:0',
                    '-c', 'copy', '-movflags', '+faststart', tmp], check=True)
    os.replace(tmp, sortie)
    for f in image + audio:
        os.remove(f)
    p.maj_info(video=sortie, duree=duree_video(sortie), telechargement=None)
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
                    '-f', 'wav', wav], check=True)


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


_modeles = {}


def whisper(modele=None):
    from faster_whisper import WhisperModel
    m = modele or C['modele_whisper']
    if m not in _modeles:
        _modeles[m] = WhisperModel(m, device='cpu', compute_type='int8')
    return _modeles[m]


def _transcrire(son, decalage=0.0, modele=None, langue=None, suivi=None):
    segs, _ = whisper(modele).transcribe(son, language=langue or C['langue'], word_timestamps=True,
                                         vad_filter=False, beam_size=5)
    mots = []
    for s in segs:
        mots += [{'mot': w.word.strip(), 'debut': round(decalage + w.start, 3), 'fin': round(decalage + w.end, 3),
                  'proba': round(w.probability, 2)} for w in s.words]
        if suivi:
            suivi(s.end, len(mots))
    return nettoyer(mots)


def transcrire(p, modele=None, langue=None):
    """Transcription Whisper complète (fichier local, ou vidéo YouTube sans sous-titres)."""
    t0 = time.time()
    son, _ = lire_wav(p.chemin('voix16k.wav'))
    duree = len(son) / 16000
    mots = _transcrire(son, 0.0, modele, langue, lambda t, n: p.etat(
        'transcription', 'en_cours', 'Transcription… %d mots' % n, round(100 * t / max(duree, 1))))
    p.ecrire('mots.json', mots)
    p.ecrire('mots_plages.json', [[0.0, round(duree, 3)]])
    ecrire_phrases(p, mots)
    print('transcription : %d mots en %d s' % (len(mots), time.time() - t0))
    return mots


def assurer_mots(p, debut, fin, modele=None, langue=None):
    """Transcription Whisper mot à mot précise de [debut, fin] (temps source), faite une seule fois par passage :
    les sous-titres YouTube suffisent pour choisir les clips, pas pour caler le texte et les coupes."""
    from .decoupe import soustraire
    plages = [tuple(x) for x in p.lire('mots_plages.json', [])]
    manque = [(a, b) for a, b in soustraire([(max(0.0, debut - 2), fin + 2)], plages) if b - a > 0.5]
    if not manque:
        return
    wav = telecharger_audio(p)
    mots = p.lire('mots.json', [])
    for a, b in manque:
        print('transcription mot à mot de %s à %s…' % (hms(a), hms(b)))
        son, _ = lire_wav(wav, a, b)
        nv = _transcrire(son, a, modele, langue)
        # mots coupés au bord du morceau : on garde ceux déjà transcrits à côté
        nv = [w for w in nv if (w['debut'] >= a + 0.3 or a < 0.5) and w['fin'] <= b - 0.3]
        if nv:
            lo, hi = nv[0]['debut'], nv[-1]['fin']
            mots = [w for w in mots if w['fin'] <= lo or w['debut'] >= hi] + nv
        plages.append((a, b))
    mots.sort(key=lambda w: w['debut'])
    p.ecrire('mots.json', mots)
    p.ecrire('mots_plages.json', sorted([list(x) for x in plages]))


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


def ecrire_phrases(p, mots, source='Whisper'):
    with open(p.chemin('phrases.txt'), 'w', encoding='utf-8') as o:
        o.write('# %s — %d mots (%s). [début–fin en secondes] (h:mm:ss) texte\n' % (
            p.info().get('titre') or p.slug, len(mots), source))
        for a, b, t in phrases(mots):
            o.write('[%.2f–%.2f] (%s) %s\n' % (a, b, hms(a), t))


def analyser(p, modele=None, langue=None):
    """Chaque étape déjà faite est sautée : on peut relancer après une coupure réseau."""
    info, langue = p.info(), langue or C['langue']
    pret = os.path.isfile(p.chemin('phrases.txt'))
    if not info.get('local') and not pret:
        p.etat('telechargement', 'en_cours', 'Récupération des sous-titres YouTube…')
        try:
            st = sous_titres(p, langue)
        except Exception as e:                       # pas de sous-titres : Whisper prendra le relais
            print('sous-titres indisponibles : %s' % e)
            st = []
        if st:
            p.ecrire('mots_approx.json', st)
            ecrire_phrases(p, st, 'sous-titres YouTube, minutage approximatif')
            pret = True
            p.etat('clips', 'attente_ia', "Sous-titres prêts : l'IA peut proposer les clips (la vidéo se télécharge)")
    if info.get('local'):
        telecharger_video(p)
        if not os.path.isfile(p.chemin('voix16k.wav')):
            p.etat('transcription', 'en_cours', 'Extraction de la voix…')
            extraire_voix(info['source'], p.chemin('voix16k.wav'))
    elif not pret:
        p.etat('telechargement', 'en_cours', 'Téléchargement de l’audio…')
        telecharger_audio(p)
    if not pret:
        transcrire(p, modele, langue)
        p.etat('clips', 'attente_ia', "Transcription prête : l'IA peut proposer les clips")
    if not info.get('local'):
        print('téléchargement de la vidéo (H.264 ≤ 1080p)…')
        telecharger_audio(p)
        telecharger_video(p)
    print('Analyse terminée : %s' % p.chemin('phrases.txt'))


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
