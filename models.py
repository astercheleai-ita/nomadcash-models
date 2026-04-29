import mysql.connector
from datetime import date
import os
import string
import random
from werkzeug.security import generate_password_hash, check_password_hash

# Database connection configuration
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'nomadcash')
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

class Utente:
    def __init__(self, email, nome=None, avatar=None):
        self.email = email
        self.nome = nome
        self.avatar = avatar

    @classmethod
    def create(cls, email, nome, password, avatar=None):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Check if user exists
            cursor.execute("SELECT email FROM utenti WHERE email = %s", (email,))
            if cursor.fetchone():
                return False, "Email già esistente. Utente non creato."

            hashed_password = generate_password_hash(password)
            cursor.execute("INSERT INTO utenti (email, nome, password, avatar) VALUES (%s, %s, %s, %s)",
                           (email, nome, hashed_password, avatar))
            conn.commit()
            return True, "Utente creato con successo."
        except Exception as e:
            conn.rollback()
            return False, f"Errore durante la creazione: {e}"
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def read(cls, email):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM utenti WHERE email = %s", (email,))
            row = cursor.fetchone()
            if row:
                return cls(row['email'], row['nome'], row['avatar'])
            return None
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def authenticate(cls, email, password):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM utenti WHERE email = %s", (email,))
            row = cursor.fetchone()
            if row and row.get('password') and check_password_hash(row['password'], password):
                return cls(row['email'], row['nome'], row['avatar'])
            return None
        finally:
            cursor.close()
            conn.close()

    def update(self, nome=None, avatar=None):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            if nome is not None:
                self.nome = nome
            if avatar is not None:
                self.avatar = avatar

            cursor.execute("UPDATE utenti SET nome = %s, avatar = %s WHERE email = %s",
                           (self.nome, self.avatar, self.email))
            conn.commit()
            return True
        finally:
            cursor.close()
            conn.close()

    def delete(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Check if user has associated expenses
            cursor.execute("SELECT COUNT(*) FROM spese WHERE email_utente = %s", (self.email,))
            count = cursor.fetchone()[0]
            if count > 0:
                return False, "L'utente ha spese associate e non può essere eliminato."

            cursor.execute("DELETE FROM utenti WHERE email = %s", (self.email,))
            conn.commit()
            return True, "Utente eliminato con successo."
        finally:
            cursor.close()
            conn.close()


class Viaggio:
    def __init__(self, id_viaggio=None, codice_viaggio=None, nome_viaggio=None, data_partenza=None, data_fine=None, descrizione_itinerario=None, chiuso=False):
        self.id_viaggio = id_viaggio
        self.codice_viaggio = codice_viaggio
        self.nome_viaggio = nome_viaggio
        self.data_partenza = data_partenza
        self.data_fine = data_fine
        self.descrizione_itinerario = descrizione_itinerario
        self.chiuso = chiuso

    @staticmethod
    def generate_trip_code():
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    @classmethod
    def create(cls, nome_viaggio, data_partenza, data_fine, descrizione_itinerario, email_creatore):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            codice_viaggio = cls.generate_trip_code()
            # Ensure uniqueness
            cursor.execute("SELECT id_viaggio FROM viaggi WHERE codice_viaggio = %s", (codice_viaggio,))
            while cursor.fetchone():
                codice_viaggio = cls.generate_trip_code()
                cursor.execute("SELECT id_viaggio FROM viaggi WHERE codice_viaggio = %s", (codice_viaggio,))

            cursor.execute("INSERT INTO viaggi (codice_viaggio, nome_viaggio, data_partenza, data_fine, descrizione_itinerario) VALUES (%s, %s, %s, %s, %s)",
                           (codice_viaggio, nome_viaggio, data_partenza, data_fine, descrizione_itinerario))
            id_viaggio = cursor.lastrowid

            # Automatically add the creator to the participants table as admin
            cursor.execute("INSERT INTO partecipanti_viaggio (id_viaggio, email_utente, admin) VALUES (%s, %s, TRUE)", (id_viaggio, email_creatore))

            conn.commit()
            return id_viaggio
        except Exception as e:
            conn.rollback()
            return None
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def read(cls, id_viaggio):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM viaggi WHERE id_viaggio = %s", (id_viaggio,))
            row = cursor.fetchone()
            if row:
                return cls(row['id_viaggio'], row['codice_viaggio'], row['nome_viaggio'], row['data_partenza'], row['data_fine'], row['descrizione_itinerario'], row.get('chiuso', False))
            return None
        finally:
            cursor.close()
            conn.close()

    def update(self, nome_viaggio=None, descrizione_itinerario=None):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            if nome_viaggio is not None:
                self.nome_viaggio = nome_viaggio
            if descrizione_itinerario is not None:
                self.descrizione_itinerario = descrizione_itinerario

            cursor.execute("UPDATE viaggi SET nome_viaggio = %s, descrizione_itinerario = %s WHERE id_viaggio = %s",
                           (self.nome_viaggio, self.descrizione_itinerario, self.id_viaggio))
            conn.commit()
            return True
        finally:
            cursor.close()
            conn.close()

    def delete(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM spese WHERE id_viaggio = %s", (self.id_viaggio,))
            count = cursor.fetchone()[0]
            if count > 0:
                return False, "Il viaggio ha spese associate e non può essere eliminato."

            cursor.execute("DELETE FROM viaggi WHERE id_viaggio = %s", (self.id_viaggio,))
            conn.commit()
            return True, "Viaggio eliminato con successo."
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def close_trip(cls, id_viaggio):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE viaggi SET chiuso = TRUE WHERE id_viaggio = %s", (id_viaggio,))
            conn.commit()
            return True
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def find_viaggio_attivo_per_utente(cls, email_utente):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            oggi = date.today()
            cursor.execute("""
                SELECT v.* 
                FROM viaggi v
                JOIN partecipanti_viaggio pv ON v.id_viaggio = pv.id_viaggio
                WHERE pv.email_utente = %s AND v.data_fine >= %s AND v.chiuso = FALSE
                ORDER BY v.data_partenza ASC LIMIT 1
            """, (email_utente, oggi))
            row = cursor.fetchone()
            if row:
                return cls(row['id_viaggio'], row['codice_viaggio'], row['nome_viaggio'], row['data_partenza'], row['data_fine'], row['descrizione_itinerario'], row.get('chiuso', False))
            return None
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def join_by_code(cls, codice_viaggio, email_utente):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # Find trip by code
            cursor.execute("SELECT * FROM viaggi WHERE codice_viaggio = %s", (codice_viaggio,))
            trip_row = cursor.fetchone()
            
            if not trip_row:
                return False, "Codice viaggio non valido."
            
            # Check if trip is still active
            if date.today() > trip_row['data_fine']:
                return False, "Questo viaggio è già terminato."

            # Add user to partecipanti_viaggio
            cursor.execute("INSERT IGNORE INTO partecipanti_viaggio (id_viaggio, email_utente, admin) VALUES (%s, %s, FALSE)", (trip_row['id_viaggio'], email_utente))
            conn.commit()
            return True, "Ti sei unito al viaggio con successo."
        except Exception as e:
            conn.rollback()
            return False, f"Errore durante l'operazione: {e}"
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def is_user_admin(cls, id_viaggio, email_utente):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT admin FROM partecipanti_viaggio WHERE id_viaggio = %s AND email_utente = %s", (id_viaggio, email_utente))
            row = cursor.fetchone()
            if row and row['admin']:
                return True
            return False
        finally:
            cursor.close()
            conn.close()
            
    @classmethod
    def remove_admin_if_ended(cls, id_viaggio, email_utente):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # Check if trip is ended
            cursor.execute("SELECT data_fine FROM viaggi WHERE id_viaggio = %s", (id_viaggio,))
            trip = cursor.fetchone()
            if trip and date.today() >= trip['data_fine']:
                # Check if there are unpaid expenses
                cursor.execute("SELECT COUNT(*) as count FROM spese WHERE id_viaggio = %s AND pagata = FALSE", (id_viaggio,))
                unpaid = cursor.fetchone()['count']
                if unpaid == 0:
                    cursor.execute("UPDATE partecipanti_viaggio SET admin = FALSE WHERE id_viaggio = %s AND email_utente = %s", (id_viaggio, email_utente))
                    conn.commit()
                    return True
            return False
        finally:
            cursor.close()
            conn.close()


class Spesa:
    def __init__(self, id_spesa=None, id_viaggio=None, email_utente=None, testo_messaggio=None, importo=None, categoria=None, data_spesa=None, pagata=False, data_pagamento=None):
        self.id_spesa = id_spesa
        self.id_viaggio = id_viaggio
        self.email_utente = email_utente
        self.testo_messaggio = testo_messaggio
        self.importo = importo
        self.categoria = categoria
        self.data_spesa = data_spesa
        self.pagata = pagata
        self.data_pagamento = data_pagamento

    @classmethod
    def create(cls, id_viaggio, email_utente, testo_messaggio, importo, categoria):
        if float(importo) <= 0:
            return False, "L'importo deve essere positivo."

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            data_odierna = date.today()
            cursor.execute("""
                INSERT INTO spese (id_viaggio, email_utente, testo_messaggio, importo, categoria, data_spesa)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (id_viaggio, email_utente, testo_messaggio, importo, categoria, data_odierna))

            conn.commit()
            return True, "Spesa inserita con successo."
        except Exception as e:
            conn.rollback()
            return False, f"Errore durante l'inserimento: {e}"
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def read_all_by_viaggio(cls, id_viaggio):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT s.*, u.nome
                FROM spese s
                JOIN utenti u ON s.email_utente = u.email
                WHERE s.id_viaggio = %s
                ORDER BY s.data_spesa DESC, s.id_spesa DESC
            """, (id_viaggio,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def delete(cls, id_spesa):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT pagata FROM spese WHERE id_spesa = %s", (id_spesa,))
            spesa = cursor.fetchone()
            
            if spesa and spesa['pagata']:
                return False, "La spesa è già stata pagata e non può essere eliminata."

            cursor.execute("DELETE FROM spese WHERE id_spesa = %s", (id_spesa,))
            conn.commit()
            return True, "Spesa eliminata."
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def mark_all_paid(cls, id_viaggio):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            oggi = date.today()
            cursor.execute("UPDATE spese SET pagata = TRUE, data_pagamento = %s WHERE id_viaggio = %s AND pagata = FALSE", (oggi, id_viaggio))
            conn.commit()
            return True
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def divisione_equa(cls, id_viaggio):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Trova i partecipanti basandosi sulla tabella partecipanti_viaggio
            cursor.execute("SELECT email_utente FROM partecipanti_viaggio WHERE id_viaggio = %s", (id_viaggio,))
            partecipanti = [row['email_utente'] for row in cursor.fetchall()]

            num_viaggiatori = len(partecipanti)
            if num_viaggiatori == 0:
                return []

            # 2. Calcola totale spese NON pagate
            cursor.execute("SELECT SUM(importo) as totale FROM spese WHERE id_viaggio = %s AND pagata = FALSE", (id_viaggio,))
            totale_row = cursor.fetchone()
            totale_spese = float(totale_row['totale']) if totale_row['totale'] else 0.0

            quota_individuale = totale_spese / num_viaggiatori if num_viaggiatori > 0 else 0

            # 3. Calcola quanto ha anticipato ciascuno
            cursor.execute("""
                SELECT email_utente, SUM(importo) as anticipato
                FROM spese
                WHERE id_viaggio = %s AND pagata = FALSE
                GROUP BY email_utente
            """, (id_viaggio,))
            anticipi_db = cursor.fetchall()

            anticipi = {p: 0.0 for p in partecipanti}
            for r in anticipi_db:
                email = r['email_utente']
                if email in anticipi:
                    anticipi[email] = float(r['anticipato'])
                else:
                    anticipi[email] = float(r['anticipato'])
                    partecipanti.append(email) 

            # 4. Calcola i bilanci
            bilanci = []
            for email in partecipanti:
                anticipato = anticipi[email]
                bilancio = anticipato - quota_individuale

                cursor.execute("SELECT nome FROM utenti WHERE email = %s", (email,))
                nome_row = cursor.fetchone()
                nome = nome_row['nome'] if nome_row else email

                bilanci.append({
                    "email": email,
                    "nome": nome,
                    "anticipato": anticipato,
                    "quota": quota_individuale,
                    "bilancio": bilancio
                })

            return bilanci
        finally:
            cursor.close()
            conn.close()
