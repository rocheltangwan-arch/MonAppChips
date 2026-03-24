import sqlite3
import os
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.utils import platform
from kivy.clock import Clock
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty


class MainLayout(BoxLayout):
    session_active = BooleanProperty(False)
    liste_partenaires = ListProperty(["Simple"])
    tot_v_diagramme = NumericProperty(0)
    tot_d_diagramme = NumericProperty(0)
    montant_max_diagramme = NumericProperty(1000)
    gains_texte = StringProperty("0 FCFA")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Chemin de la DB selon la plateforme
        db_path = "chips_gestion.db"
        if platform == 'android':
            from android.storage import app_storage_path
            db_path = os.path.join(app_storage_path(), "chips_gestion.db")

        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

        # Table ACTIVE (se vide à la clôture)
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS transactions
                               (
                                   id
                                   INTEGER
                                   PRIMARY
                                   KEY
                                   AUTOINCREMENT,
                                   type
                                   TEXT,
                                   categorie
                                   TEXT,
                                   montant
                                   REAL,
                                   quantite
                                   INTEGER,
                                   prix_unitaire
                                   REAL,
                                   date
                                   TEXT
                               )''')

        # Table ARCHIVES (stocke tout l'historique passé)
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS archives
                               (
                                   id
                                   INTEGER
                                   PRIMARY
                                   KEY
                                   AUTOINCREMENT,
                                   type
                                   TEXT,
                                   categorie
                                   TEXT,
                                   montant
                                   REAL,
                                   date
                                   TEXT
                               )''')

        self.cursor.execute('CREATE TABLE IF NOT EXISTS config (cle TEXT PRIMARY KEY, valeur TEXT)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS partenaires (nom TEXT PRIMARY KEY)')
        self.conn.commit()

        self.charger_partenaires()
        Clock.schedule_once(self.verifier_etat_session)

    def charger_partenaires(self):
        self.cursor.execute("SELECT nom FROM partenaires")
        self.liste_partenaires = ["Simple"] + [row[0] for row in self.cursor.fetchall()]

    def ajouter_nouveau_partenaire(self, nom):
        if nom.strip():
            try:
                self.cursor.execute("INSERT INTO partenaires (nom) VALUES (?)", (nom.strip(),))
                self.conn.commit()
                self.charger_partenaires()
                self.ids.part_in.text = ""
            except:
                pass

    def verifier_etat_session(self, dt=None):
        self.cursor.execute("SELECT valeur FROM config WHERE cle='session_active'")
        res = self.cursor.fetchone()
        self.session_active = (res and res[0] == "1")
        self.actualiser_tout()

    def toggle_session(self):
        if self.session_active:  # Fermeture de la session
            # 1. Calcul du bilan de la session actuelle
            self.cursor.execute("SELECT type, montant FROM transactions")
            res = self.cursor.fetchall()
            v = sum(r[1] for r in res if r[0] == "VENTE")
            d = sum(r[1] for r in res if r[0] == "DEPENSE")
            gain = v - d
            date_cloture = datetime.now().strftime("%d/%m/%Y à %H:%M")

            # 2. Archiver les détails
            self.cursor.execute(
                "INSERT INTO archives (type, categorie, montant, date) SELECT type, categorie, montant, date FROM transactions")

            # 3. Insérer la ligne de BILAN qui servira de séparateur
            self.cursor.execute("INSERT INTO archives (type, categorie, montant, date) VALUES (?,?,?,?)",
                                ("FIN_SESSION", f"SESSION DU {date_cloture}", gain, date_cloture))

            # 4. Vider la session active
            self.cursor.execute("DELETE FROM transactions")
            self.conn.commit()
            self.session_active = False
        else:
            self.session_active = True

        self.cursor.execute("INSERT OR REPLACE INTO config (cle, valeur) VALUES ('session_active', ?)",
                            ("1" if self.session_active else "0",))
        self.conn.commit()
        self.actualiser_tout()

    def sauvegarder_entree(self, t, cat, mt):
        if mt and self.session_active:
            d = datetime.now().strftime("%d/%m/%Y")
            self.cursor.execute("INSERT INTO transactions (type, categorie, montant, date) VALUES (?,?,?,?)",
                                (t, cat, float(mt), d))
            self.conn.commit()
            self.actualiser_tout()

    def sauvegarder_vente(self, part, qty, prix):
        if qty and prix and self.session_active:
            mt = float(qty) * float(prix)
            d = datetime.now().strftime("%d/%m/%Y")
            self.cursor.execute(
                "INSERT INTO transactions (type, categorie, montant, quantite, prix_unitaire, date) VALUES (?,?,?,?,?,?)",
                ("VENTE", part, mt, int(qty), float(prix), d))
            self.conn.commit()
            self.actualiser_tout()

    def supprimer_derniere(self, type_t):
        self.cursor.execute("DELETE FROM transactions WHERE id = (SELECT MAX(id) FROM transactions WHERE type=?)",
                            (type_t,))
        self.conn.commit()
        self.actualiser_tout()

    def actualiser_tout(self):
        # Update Historiques
        self.cursor.execute("SELECT categorie, montant FROM transactions WHERE type='DEPENSE' ORDER BY id DESC")
        self.ids.hist_depenses_label.text = "\n".join(
            [f"{r[0]} : {r[1]:,.0f}" for r in self.cursor.fetchall()]) if self.session_active else "Session fermée."

        self.cursor.execute("SELECT categorie, montant FROM transactions WHERE type='VENTE' ORDER BY id DESC")
        self.ids.hist_ventes_label.text = "\n".join(
            [f"{r[0]} : {r[1]:,.0f}" for r in self.cursor.fetchall()]) if self.session_active else "Session fermée."

        self.calculer_bilan()

    def calculer_bilan(self):
        self.cursor.execute("SELECT type, montant FROM transactions")
        res = self.cursor.fetchall()
        v = sum(r[1] for r in res if r[0] == "VENTE")
        d = sum(r[1] for r in res if r[0] == "DEPENSE")
        self.tot_v_diagramme, self.tot_d_diagramme = v, d
        self.montant_max_diagramme = max(v, d, 1000) * 1.2
        gain = v - d
        self.gains_texte = f"[color={'55ff55' if gain >= 0 else 'ff5555'}][b]Bilan: {gain:,.0f} FCFA[/b][/color]"

        self.cursor.execute("SELECT type, categorie, montant FROM transactions ORDER BY id DESC")
        self.ids.hist_bilan_detail.text = "\n".join([f"{r[0]} | {r[1]} : {r[2]:,.0f}" for r in self.cursor.fetchall()])

    def charger_archives(self):
        # On récupère tout l'historique
        self.cursor.execute("SELECT date, type, categorie, montant FROM archives ORDER BY id DESC")
        res = self.cursor.fetchall()

        lignes = []
        for r in res:
            date, t_type, cat, mt = r
            if t_type == "FIN_SESSION":
                # Bloc de résumé coloré pour séparer les sessions
                color = "55ff55" if mt >= 0 else "ff5555"
                lignes.append(f"\n[b]━━━━━━━━━━━━━━━━━━━━━━━━━━[/b]")
                lignes.append(f"[color={color}][b]{cat}[/b][/color]")
                lignes.append(f"[color={color}][b]GAIN NET : {mt:,.0f} FCFA[/b][/color]")
                lignes.append(f"[b]━━━━━━━━━━━━━━━━━━━━━━━━━━[/b]\n")
            else:
                # Ligne de détail simple
                lignes.append(f" • {t_type} ({cat}) : {mt:,.0f} FCFA")

        self.ids.archives_label.text = "\n".join(lignes) if lignes else "Aucune archive pour le moment."
class GestionApp(App):
    def build(self):
        return MainLayout()


if __name__ == "__main__":
    GestionApp().run()