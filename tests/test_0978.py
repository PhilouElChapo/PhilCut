"""0.9.78 : bruitages par ordre alphabétique ; tampons maison prêts posés depuis leur onglet ; yt-dlp : découpage repris
par PhilCut quand FFmpeg échoue."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun
app = commun.application()


class Test0978(unittest.TestCase):
    def test_bruitages_alpha(self):
        from app.dialogues_effets_plus import DialogueBruitages
        from app.fenetre import alpha, Fenetre
        f = Fenetre()
        ed = f.nouveau_projet("16:9")
        d = DialogueBruitages(ed)
        noms = [d.liste.item(i).text() for i in range(d.liste.count())]
        self.assertEqual(noms, sorted(noms, key=alpha))

    def test_maison_pret(self):
        from app import tampons as T
        from app.fenetre import Fenetre
        f = Fenetre()
        ed = f.nouveau_projet("16:9")
        d = ed.tampons(1)
        k = next(iter(T.MAISON))
        L, H = d.format
        T.fabriquer_maison(ed.params, k, L, H)
        self.assertIsNotNone(T.entree_maison(ed.params, k, L, H))
        for i in range(d.liste_maison.count()):
            if d.liste_maison.item(i).data(0x0100) == k:
                d.liste_maison.setCurrentRow(i)
        d._info_maison()
        self.assertTrue(d.liste_maison.currentItem().text().startswith("✓ "))
        poses = []
        d.poser_entree = lambda e: poses.append(e)
        d._maison_double_clic()
        self.assertEqual(poses[0]["maison"], k)

    def test_ytdlp_repli(self):
        from app import videos_en_ligne as VL
        appels = []

        def faux(args, *a, **k):
            appels.append(args)
            if len(appels) == 1:
                raise RuntimeError("yt-dlp n'a pas pu : ERROR: ffmpeg exited with code 3436169992")
            return []
        anc = VL._lancer_ytdlp
        VL._lancer_ytdlp = faux
        try:
            with self.assertRaises(RuntimeError):                 # pas de fichier dans ce faux : mais le repli a bien été tenté
                VL.telecharger("https://x", "/tmp/philcut_essai_yt", audio_seul=True, debut=1, fin=3)
        finally:
            VL._lancer_ytdlp = anc
        self.assertEqual(len(appels), 2)
        self.assertNotIn("-x", appels[1])
        self.assertNotIn("--download-sections", appels[1])


if __name__ == "__main__":
    unittest.main()
