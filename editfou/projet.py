"""Un projet = un dossier `projets/<slug>/` qui contient tout, en fichiers lisibles par un humain ou une IA :

  info.json            source (lien ou fichier), titre, durée, chemin de la vidéo
  etat.json            étape en cours / terminée, message, pour l'interface
  source.mp4           vidéo téléchargée (absent pour un fichier local : on lit l'original)
  voix16k.wav          voix mono 16 kHz
  mots_approx.json     mots des sous-titres YouTube, minutage approximatif (pour choisir les clips)
  mots.json            transcription Whisper mot à mot [{mot, debut, fin, proba}] (temps de la source, s),
                       complète (fichier local) ou seulement sur les passages des clips (mots_plages.json)
  phrases.txt          la même en phrases horodatées : ce que l'IA lit pour choisir les clips
  clips.json           {"clips": [{id, debut, fin, titre, accroche, raison, score, statut}]}
  clips/<id>/          storyboard.json, plans.json, montage.fcproj, <slug>-<id>.mp4, apercu.jpg
  journal.txt          sortie des tâches lancées par l'interface
"""
import datetime, json, os, re, time, unicodedata

from .config import C

ETAPES = ['cree', 'telechargement', 'transcription', 'clips', 'storyboards', 'montage']


def slugifier(texte):
    t = unicodedata.normalize('NFKD', texte).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')[:48] or 'projet'


class Projet:
    def __init__(self, slug):
        self.slug = slug
        self.dossier = os.path.join(C['projets'], slug)
        if not os.path.isdir(self.dossier):
            raise FileNotFoundError('projet inconnu : %s' % slug)

    # ------------------------------------------------------------------ création / liste
    @classmethod
    def creer(cls, source, nom=None):
        local = os.path.isfile(source)
        yt = re.search(r'(?:youtu\.be/|v=|shorts/)([\w-]{11})', source)
        base = slugifier(nom or (os.path.splitext(os.path.basename(source))[0] if local else
                                 'youtube-' + yt.group(1) if yt else re.sub(r'^https?://(www\.)?', '', source)))
        slug, n = base, 2
        while os.path.exists(os.path.join(C['projets'], slug)):
            slug, n = '%s-%d' % (base, n), n + 1
        os.makedirs(os.path.join(C['projets'], slug, 'clips'))
        p = cls(slug)
        p.ecrire('info.json', {'source': os.path.abspath(source) if local else source, 'local': local,
                               'titre': nom or '', 'video': os.path.abspath(source) if local else '',
                               'cree': maintenant()})
        p.etat('cree', 'fait', 'Projet créé')
        return p

    @staticmethod
    def liste():
        if not os.path.isdir(C['projets']):
            return []
        out = []
        for s in sorted(os.listdir(C['projets'])):
            if os.path.isfile(os.path.join(C['projets'], s, 'info.json')):
                out.append(Projet(s))
        return sorted(out, key=lambda p: p.info().get('cree', ''), reverse=True)

    # ------------------------------------------------------------------ fichiers
    def chemin(self, *n):
        return os.path.join(self.dossier, *n)

    def lire(self, nom, defaut=None):
        f = self.chemin(nom)
        for essai in range(20):
            if not os.path.isfile(f):
                return defaut
            try:
                with open(f, encoding='utf-8') as fh:
                    return json.load(fh)
            except (PermissionError, ValueError):     # fichier en cours de remplacement par une autre tâche
                time.sleep(0.05)
        return defaut

    def ecrire(self, nom, data):
        f = self.chemin(nom)
        os.makedirs(os.path.dirname(f), exist_ok=True)
        tmp = '%s.%d.tmp' % (f, os.getpid())
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
        # Windows refuse de remplacer un fichier qu'un autre processus lit (l'interface) : on réessaie
        for essai in range(40):
            try:
                os.replace(tmp, f)
                return
            except PermissionError:
                time.sleep(0.05)
        os.replace(tmp, f)

    def info(self):
        return self.lire('info.json', {})

    def maj_info(self, **kw):
        i = self.info(); i.update(kw); self.ecrire('info.json', i)

    def video(self):
        v = self.info().get('video')
        if not v or not os.path.isfile(v):
            raise FileNotFoundError('vidéo pas encore téléchargée (python -m editfou analyser %s)' % self.slug)
        return v

    def mots(self, debut=None, fin=None):
        """Mots Whisper là où ils existent, sous-titres YouTube approximatifs ailleurs."""
        m = self.lire('mots.json', [])
        approx = self.lire('mots_approx.json')
        if approx:
            plages = self.lire('mots_plages.json', [])
            m = sorted(m + [w for w in approx if not any(a <= w['debut'] < b for a, b in plages)],
                       key=lambda w: w['debut'])
        if debut is not None:
            m = [w for w in m if w['debut'] >= debut - 0.01 and w['fin'] <= fin + 0.3]
        return m

    # ------------------------------------------------------------------ état (pour l'interface)
    def etat(self, etape=None, statut=None, message='', progression=None):
        """Sans argument : lit l'état. Sinon l'écrit (statut : en_cours, fait, erreur, attente_ia)."""
        if etape is None:
            return self.lire('etat.json', {})
        e = {'etape': etape, 'statut': statut, 'message': message, 'maj': maintenant()}
        if progression is not None:
            e['progression'] = progression
        self.ecrire('etat.json', e)
        return e

    # ------------------------------------------------------------------ clips
    def clips(self):
        return self.lire('clips.json', {'clips': []})['clips']

    def clip(self, cid):
        for c in self.clips():
            if c['id'] == cid:
                return c
        raise KeyError('clip inconnu : %s' % cid)

    def maj_clip(self, cid, **kw):
        d = self.lire('clips.json', {'clips': []})
        for c in d['clips']:
            if c['id'] == cid:
                c.update(kw)
                self.ecrire('clips.json', d)
                return c
        raise KeyError('clip inconnu : %s' % cid)

    def storyboard(self, cid):
        return self.lire(os.path.join('clips', cid, 'storyboard.json'))

    def ecrire_storyboard(self, cid, sb):
        self.ecrire(os.path.join('clips', cid, 'storyboard.json'), sb)

    def rendu(self, cid):
        return self.chemin('clips', cid, '%s-%s.mp4' % (self.slug, cid))


def maintenant():
    return datetime.datetime.now().isoformat(timespec='seconds')
