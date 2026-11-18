"""Moteur « lèvres sur ce poste » de PhilCut (0.9.92) : LatentSync 1.5 (ByteDance, Apache 2.0), carte NVIDIA de 8 Go.

Ce script est livré DANS le moteur (Python portable + PyTorch CUDA + code de LatentSync, commit 7b380d6, le dernier avant
1.6 : 256 px, 8 Go). PhilCut le lance avec les chemins des modèles téléchargés :

  python philcut_levres.py --verifier
  python philcut_levres.py --video plan.mp4 --audio voix.wav --sortie sortie.mp4 --unet latentsync_unet.pt
         --whisper tiny.pt --vae <dossier vae> --visages buffalo_l.zip [--etapes 20] [--guidance 1.5] [--deepcache]

Il écrit des lignes « PHILCUT <fraction> <texte> » que PhilCut lit pour la barre du bas, et « PHILCUT_ERREUR <texte> »
quand il échoue (mémoire de la carte, visage introuvable…)."""
import argparse, os, sys, tempfile, zipfile

ICI = os.path.dirname(os.path.abspath(__file__))


def dire(fraction, texte):
    print(f"PHILCUT {max(0.0, min(1.0, fraction)):.3f} {texte}", flush=True)


def erreur(texte):
    print(f"PHILCUT_ERREUR {texte}", flush=True)


def verifier():
    import torch, diffusers, transformers, insightface, decord, kornia, cv2, librosa   # noqa: F401
    import DeepCache  # noqa: F401
    sys.path.insert(0, ICI)
    from latentsync.pipelines.lipsync_pipeline import LipsyncPipeline   # noqa: F401
    from latentsync.models.unet import UNet3DConditionModel             # noqa: F401
    cuda = torch.cuda.is_available()
    print(f"torch {torch.__version__} ; diffusers {diffusers.__version__} ; insightface {insightface.__version__} ; "
          f"cuda {'oui' if cuda else 'non'}" + (f" ({torch.cuda.get_device_name(0)}, "
                                                 f"{torch.cuda.get_device_properties(0).total_memory / 2**30:.1f} Go)" if cuda else ""))
    print("PHILCUT_OK", flush=True)
    return 0


class _Suivi:
    """Remplace tqdm dans le pipeline : chaque boucle devient une étape de la barre de PhilCut."""
    PHASES = [("visages", 0.05, 0.25, "Repérage du visage, image par image"),
              ("levres", 0.25, 0.85, "Calcul des lèvres sur la carte graphique"),
              ("recoller", 0.85, 0.98, "Recollage de la bouche dans les images")]
    n = 0

    def __init__(self, iterable=None, desc="", total=None, **_k):
        self.it = iterable
        self.total = total if total is not None else (len(iterable) if hasattr(iterable, "__len__") else 0)
        cle, a, b, texte = self.PHASES[min(_Suivi.n, len(self.PHASES) - 1)]
        _Suivi.n += 1
        self.a, self.b, self.texte = a, b, texte

    def __iter__(self):
        for k, x in enumerate(self.it):
            if self.total:
                dire(self.a + (self.b - self.a) * k / self.total, self.texte)
            yield x

    def update(self, *_a):
        pass

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


def lancer(a):
    os.chdir(ICI)                                  # configs/ et latentsync/utils/mask.png sont relatifs au moteur
    sys.path.insert(0, ICI)
    dire(0.01, "Chargement de LatentSync")
    import torch
    if not torch.cuda.is_available():
        erreur("Pas de carte NVIDIA utilisable (CUDA) : ce calcul demande une carte NVIDIA de 8 Go.")
        return 3
    from omegaconf import OmegaConf
    from diffusers import AutoencoderKL, DDIMScheduler
    from accelerate.utils import set_seed
    import latentsync.utils.face_detector as FD
    import latentsync.pipelines.lipsync_pipeline as LP
    from latentsync.models.unet import UNet3DConditionModel
    from latentsync.whisper.audio2feature import Audio2Feature

    # visages : modèles buffalo_l (InsightFace) déposés par PhilCut, jamais téléchargés pendant le calcul
    aux = os.path.join(os.path.dirname(os.path.abspath(a.visages)), "auxiliaire")
    dest = os.path.join(aux, "models", "buffalo_l")
    if not os.path.exists(os.path.join(dest, "det_10g.onnx")):
        os.makedirs(dest, exist_ok=True)
        with zipfile.ZipFile(a.visages) as z:
            for n in z.namelist():
                if n.endswith(".onnx"):
                    with z.open(n) as s, open(os.path.join(dest, os.path.basename(n)), "wb") as d:
                        d.write(s.read())
    origine = FD.FaceAnalysis

    def analyse(**kw):
        kw["root"] = aux
        kw["providers"] = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        return origine(**kw)
    FD.FaceAnalysis = analyse
    LP.tqdm.tqdm = _Suivi

    config = OmegaConf.load(os.path.join(ICI, "configs", "unet", "stage2.yaml"))
    fp16 = torch.cuda.get_device_capability()[0] > 7
    dtype = torch.float16 if fp16 else torch.float32
    scheduler = DDIMScheduler.from_pretrained(os.path.join(ICI, "configs"))
    audio = Audio2Feature(model_path=a.whisper, device="cuda", num_frames=config.data.num_frames,
                          audio_feat_length=config.data.audio_feat_length)
    vae = AutoencoderKL.from_pretrained(a.vae, torch_dtype=dtype)
    vae.config.scaling_factor = 0.18215
    vae.config.shift_factor = 0
    unet, _ = UNet3DConditionModel.from_pretrained(OmegaConf.to_container(config.model), a.unet, device="cpu")
    unet = unet.to(dtype=dtype)
    pipe = LP.LipsyncPipeline(vae=vae, audio_encoder=audio, unet=unet, scheduler=scheduler).to("cuda")
    pipe.set_progress_bar_config(disable=True)
    if a.deepcache:
        from DeepCache import DeepCacheSDHelper
        h = DeepCacheSDHelper(pipe=pipe)
        h.set_params(cache_interval=3, cache_branch_id=0)
        h.enable()
    set_seed(1247)
    torch.cuda.empty_cache()
    tmp = tempfile.mkdtemp(prefix="philcut-latentsync-")
    try:
        pipe(video_path=a.video, audio_path=a.audio, video_out_path=a.sortie, num_frames=config.data.num_frames,
             num_inference_steps=a.etapes, guidance_scale=a.guidance, weight_dtype=dtype, width=config.data.resolution,
             height=config.data.resolution, mask_image_path=config.data.mask_image_path, temp_dir=tmp)
    except torch.cuda.OutOfMemoryError:
        erreur("Mémoire de la carte graphique insuffisante : fermez les autres logiciels qui l'utilisent, ou raccourcissez "
               "le passage.")
        return 4
    except RuntimeError as e:
        if "Face not detected" in str(e) or "face" in str(e).lower():
            erreur("Visage introuvable sur certaines images : il faut un visage net, de face ou de trois quarts, assez grand.")
            return 5
        raise
    dire(1.0, "Terminé")
    return 0 if os.path.exists(a.sortie) else 6


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--verifier", action="store_true")
    p.add_argument("--video")
    p.add_argument("--audio")
    p.add_argument("--sortie")
    p.add_argument("--unet")
    p.add_argument("--whisper")
    p.add_argument("--vae")
    p.add_argument("--visages")
    p.add_argument("--etapes", type=int, default=20)
    p.add_argument("--guidance", type=float, default=1.5)
    p.add_argument("--deepcache", action="store_true")
    a = p.parse_args()
    if a.verifier:
        return verifier()
    return lancer(a)


if __name__ == "__main__":
    sys.exit(main())
