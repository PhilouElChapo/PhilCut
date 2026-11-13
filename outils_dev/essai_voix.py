"""Essai réel de « Continuer avec ma voix » (0.9.57, modèle « voix_clone » : Chatterbox Multilingual ONNX, licence MIT),
lancé par GitHub Actions (essai_voix.yml) : télécharge les fichiers du modèle, prend un extrait de voix (espeak-ng, voix
française de synthèse : il ne s'agit que de vérifier la chaîne), fait dire une phrase et vérifie :
- le découpage du texte (aucun jeton inconnu, minuscules ou non) ;
- la durée du son (cohérente avec le nombre de jetons de parole : le décodeur ne rend pas l'extrait) ;
- le niveau (pas de silence, pas de saturation), la mention « fabriquée par IA » dans le fichier ;
- le temps de calcul sur le processeur.
Usage : python outils_dev/essai_voix.py <dossier de travail>"""
import os, subprocess, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from app import voix_clone as V

DEPOT = "https://huggingface.co/onnx-community/chatterbox-multilingual-ONNX/resolve/main/"
FICHIERS = {"encodeur": "onnx/speech_encoder.onnx", "encodeur_donnees": "onnx/speech_encoder.onnx_data",
            "jetons": "onnx/embed_tokens.onnx", "jetons_donnees": "onnx/embed_tokens.onnx_data",
            "langage": "onnx/language_model_q4.onnx", "langage_donnees": "onnx/language_model_q4.onnx_data",
            "decodeur": "onnx/conditional_decoder.onnx", "decodeur_donnees": "onnx/conditional_decoder.onnx_data",
            "tokenizer": "tokenizer.json"}


def main(d):
    os.makedirs(d, exist_ok=True)
    chemins = {}
    t = time.time()
    for role, f in FICHIERS.items():
        p = os.path.join(d, os.path.basename(f))
        if not os.path.exists(p):
            urllib.request.urlretrieve(DEPOT + f, p)
        chemins[role] = p
    print(f"modèle : {sum(os.path.getsize(p) for p in chemins.values()) / 1e9:.2f} Go en {time.time() - t:.0f} s")
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(chemins["tokenizer"])
    for essai in ("[fr]Bonjour, ça va ? Et maintenant, passons à autre chose.", "[fr]bonjour, ça va ? et maintenant, passons à autre chose.",
                  "[fr]Élève, être, çà, où."):
        e = tok.encode(essai)
        print("jetons", repr(essai), e.ids, "inconnus :", e.ids.count(1), "morceaux :", e.tokens)
    import unicodedata
    e = tok.encode("[fr]" + unicodedata.normalize("NFKD", "élève être"))
    print("NFKD", e.ids, e.tokens)
    texte = ("Bonjour à tous. Aujourd'hui nous partons en promenade au bord de la mer, il fait beau et le vent souffle un peu.")
    subprocess.run(["espeak-ng", "-v", "fr", "-s", "150", "-w", os.path.join(d, "ref0.wav"), texte], check=True)
    ref = V.lire_reference(os.path.join(d, "ref0.wav"))
    print(f"extrait : {ref.size / V.TAUX:.1f} s")
    t = time.time()
    s = V.sessions(None, chemins)
    print(f"chargement : {time.time() - t:.0f} s ; entrées du langage : {s['langage'].get_inputs()[2].type}")
    emp = V.empreinte(s, ref)
    print("empreinte :", [x.shape for x in emp])
    phrase = "Et maintenant, passons à autre chose."
    ids = V.jetons_texte(s["tokenizer"], phrase, "fr")
    t = time.time()
    j = V.parole(s, ids, emp, 0.5, V.jetons_attendus(phrase))
    tp = time.time() - t
    print(f"jetons de parole : {j.shape[1]} en {tp:.1f} s ({tp / max(1, j.shape[1]) * 1000:.0f} ms par jeton)")
    t = time.time()
    son = V.decoder(s, j, emp)
    print(f"décodeur : {son.size / V.TAUX:.2f} s de son en {time.time() - t:.1f} s ; attendu pour les seuls jetons produits : "
          f"{j.shape[1] / 25:.2f} s ; avec l'extrait : {(j.shape[1] + emp[1].shape[1]) / 25:.2f} s")
    sortie = os.path.join(d, "suite.wav")
    t = time.time()
    chem, duree = V.dire(phrase + " Nous allons voir comment fabriquer un plan de liaison entre deux rushes.", ref, sortie, "fr",
                         params=None, s=s, progression=lambda f, txt="": None)
    print(f"dire : {duree:.2f} s en {time.time() - t:.1f} s ; mention IA : {V.lire_mention(chem)}")
    import wave
    with wave.open(chem) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32767
    print(f"niveau : extrait {V.niveau(ref):.3f}, suite {V.niveau(a):.3f}, pic {np.abs(a).max():.3f}")
    assert 2.0 < duree < 20.0, duree
    assert V.lire_mention(chem)
    assert np.abs(a).max() < 0.99 and V.niveau(a) > 0.01
    # l'anglais aussi (autre langue, même voix)
    chem2, d2 = V.dire("And now, let's move on to something else.", ref, os.path.join(d, "suite_en.wav"), "en", s=s)
    print(f"anglais : {d2:.2f} s")
    print("ESSAI REUSSI")


if __name__ == "__main__":
    main(sys.argv[1])
