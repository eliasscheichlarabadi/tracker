import customtkinter as ctk
import tkinter as tk
from datetime import date, timedelta
import openpyxl
import csv
import os

# === KONFIGURATION ===
EXCEL_DATEI = "Umsatz 25.09 (2).xlsx"

# === GRUNDSETUP ===
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("EÜR Rechner")
app.geometry("600x400")

# Funktion zum korrekten Beenden des Programms
def on_closing():
    app.quit()  # Beendet die Hauptschleife
    app.destroy()  # Zerstört das Fenster
    import sys
    sys.exit(0)  # Beendet das Programm vollständig

# Registriere die Funktion für das Schließen-Event
app.protocol("WM_DELETE_WINDOW", on_closing)

# === DATEN ===
heutiges_datum = date.today()
transaktionen = []
anfangsbestand = 0.0
firmenname = ""
DB_CSV = "db.csv"
transaction_listbox = None

# === FUNKTIONEN ===
def datum_anzeigen():
    datum_label.configure(text=aktuelles_datum.strftime("%d.%m.%Y"))

def datum_plus():
    global aktuelles_datum
    aktuelles_datum += timedelta(days=1)
    datum_anzeigen()

def datum_minus():
    global aktuelles_datum
    aktuelles_datum -= timedelta(days=1)
    datum_anzeigen()

def transaktion_hinzufügen():
    # accept comma as decimal separator
    betrag_text = betrag_entry.get().strip().replace(',', '.')
    try:
        betrag_raw = float(betrag_text) if betrag_text != "" else 0.0
    except ValueError:
        info_label.configure(text="❌ Ungültiger Betrag")
        return

    kategorie = kategorie_option.get()

    # Betrag als positiv/negativ speichern basierend auf Kategorie
    # Tagesumsatz Kasse ist Einnahme, alles andere Ausgabe
    if "Tagesumsatz Kasse" in kategorie:
        betrag = abs(betrag_raw)
    else:
        betrag = -abs(betrag_raw)

    trans = {
        "Datum": aktuelles_datum.strftime("%Y-%m-%d"),
        "Kategorie": kategorie,
        "Betrag": betrag
    }
    transaktionen.append(trans)

    # Komplette DB neu schreiben mit Anfangsbestand
    try:
        save_all_to_csv()  # Speichert Anfangsbestand + alle Transaktionen
    except Exception as e:
        info_label.configure(text=f"❌ Fehler beim Speichern in CSV: {e}")
        return

    # Formatiere Betrag mit Tausenderpunkten und Komma für die Anzeige
    betrag_abs = abs(betrag)
    if betrag_abs >= 1000:
        betrag_str = f"{betrag_abs:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        betrag_str = f"{betrag_abs:.2f}".replace(".", ",")
    info_label.configure(text=f"💾 Transaktion gespeichert ({kategorie}: {betrag_str} €)")
    betrag_entry.delete(0, "end")
    refresh_transaction_list()

def exportieren():
    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "EÜR"

        # Funktion für deutsches Zahlenformat
        def format_currency(value):
            if not value:  # Wenn leer
                return ""
            # Runde auf 2 Nachkommastellen
            value = round(float(value), 2)
            # Formatiere mit Tausenderpunkt und Komma
            if abs(value) >= 1000:
                formatted = f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                formatted = f"{abs(value):.2f}".replace(".", ",")
            return f"{formatted} €"

        # Styles definieren
        header_font = openpyxl.styles.Font(name='Arial', bold=True, size=10)
        normal_font = openpyxl.styles.Font(name='Arial', size=10)
        money_format = '@'  # Text-Format für vorformatierte Zahlen
        thin_border = openpyxl.styles.Border(
            left=openpyxl.styles.Side(style='thin'),
            right=openpyxl.styles.Side(style='thin'),
            top=openpyxl.styles.Side(style='thin'),
            bottom=openpyxl.styles.Side(style='thin')
        )
        header_fill = openpyxl.styles.PatternFill(start_color='E6E6E6', end_color='E6E6E6', fill_type='solid')
        grey_fill = openpyxl.styles.PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')

        # Firmenname in der ersten Zeile
        ws.append([firmenname])
        ws.append([])  # Leerzeile
        
        # Anfangsbestand in der dritten Zeile
        ws.append(["", "", "", "Anfangsbestand:", format_currency(anfangsbestand)])
        anfang_row = ws.max_row
        for col in range(4, 6):
            cell = ws.cell(row=anfang_row, column=col)
            cell.font = header_font
            cell.border = thin_border
            if col == 4:  # "Anfangsbestand:" Text
                cell.fill = grey_fill
                cell.alignment = openpyxl.styles.Alignment(horizontal='right')
            elif col == 5:  # Betrag
                cell.number_format = money_format
                cell.alignment = openpyxl.styles.Alignment(horizontal='right')

        # Kopfzeile
        header_row = ws.max_row + 1
        ws.append(["Beleg-Nr.", "Datum", "Transaktion", "Einnahmen", "Ausgaben"])
        for col in range(1, 6):
            cell = ws.cell(row=header_row, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border
            if col in [4, 5]:  # Geldbeträge rechtsbündig
                cell.alignment = openpyxl.styles.Alignment(horizontal='right')
            else:  # Rest zentriert
                cell.alignment = openpyxl.styles.Alignment(horizontal='center')

        # Transaktionen einfügen
        for idx, t in enumerate(transaktionen, 1):
            betrag = t["Betrag"]
            # Formatiere die Beträge
            einnahme = format_currency(abs(betrag)) if betrag > 0 else ""
            ausgabe = format_currency(abs(betrag)) if betrag < 0 else ""
            row = ws.append([
                idx,  # Beleg-Nr.
                t["Datum"].replace("-", "/"),  # Datum im Format DD/MM/YYYY
                t["Kategorie"].split(" ", 1)[1],  # Kategorie ohne Emoji
                einnahme,
                ausgabe
            ])
            
            # Formatierung der Zeile
            current_row = ws.max_row
            for col in range(1, 6):
                cell = ws.cell(row=current_row, column=col)
                cell.font = normal_font
                cell.border = thin_border  # Vollständiger Rand für alle Zellen
                if col in [4, 5]:  # Geldbeträge
                    cell.number_format = money_format
                    cell.alignment = openpyxl.styles.Alignment(horizontal='right')
                elif col == 1:  # Beleg-Nr.
                    cell.alignment = openpyxl.styles.Alignment(horizontal='center')
                elif col == 2:  # Datum
                    cell.alignment = openpyxl.styles.Alignment(horizontal='center')
                else:  # Transaktion
                    cell.alignment = openpyxl.styles.Alignment(horizontal='left')
            
            # Beleg-Nr. zentrieren
            ws.cell(row=current_row, column=1).alignment = openpyxl.styles.Alignment(horizontal='center')

        # Summen
        einnahmen = sum(t["Betrag"] for t in transaktionen if t["Betrag"] > 0)
        ausgaben = sum(-t["Betrag"] for t in transaktionen if t["Betrag"] < 0)
        gewinn = einnahmen - ausgaben
        endbestand = anfangsbestand + gewinn

        ws.append([])
        # Untere Kante für letzte Transaktionszeile
        last_data_row = ws.max_row
        for col in range(1, 6):
            cell = ws.cell(row=last_data_row, column=col)
            current_border = cell.border
            cell.border = openpyxl.styles.Border(
                left=current_border.left,
                right=current_border.right,
                top=current_border.top,
                bottom=openpyxl.styles.Side(style='thin')
            )

        ws.append([])  # Leerzeile vor Summen
        
        # Summen einfügen mit angepasster Formatierung
        # Gesamtzeile mit Einnahmen und Ausgaben nebeneinander
        ws.append(["", "", "Gesamt:", format_currency(einnahmen), format_currency(ausgaben)])
        current_row = ws.max_row
        
        # Gesamttext mit grauem Hintergrund
        gesamt_cell = ws.cell(row=current_row, column=3)
        gesamt_cell.font = header_font
        gesamt_cell.border = thin_border
        gesamt_cell.fill = grey_fill
        gesamt_cell.alignment = openpyxl.styles.Alignment(horizontal='right')
        
        # Einnahmen- und Ausgabenbetrag ohne Fülleffekt
        for col in [4, 5]:  # Spalten für Einnahmen und Ausgaben
            cell = ws.cell(row=current_row, column=col)
            cell.font = header_font
            cell.border = thin_border
            cell.number_format = money_format
            cell.alignment = openpyxl.styles.Alignment(horizontal='right')

        # Endbestand (Text mit grauem Fülleffekt, Betrag ohne)
        ws.append(["", "", "", "Endbestand:", format_currency(endbestand)])
        current_row = ws.max_row
        for col in range(4, 6):
            cell = ws.cell(row=current_row, column=col)
            cell.font = header_font
            cell.border = thin_border
            if col == 4:  # "Endbestand:" Text
                cell.fill = grey_fill
                cell.alignment = openpyxl.styles.Alignment(horizontal='right')
            elif col == 5:  # Geldbetrag
                cell.number_format = money_format
                cell.alignment = openpyxl.styles.Alignment(horizontal='right')

        # Optimierte Spaltenbreiten
        column_widths = {
            1: 12,  # Beleg-Nr.
            2: 12,  # Datum
            3: 40,  # Transaktion (breiter für lange Kategorienamen)
            4: 18,  # Einnahmen
            5: 18   # Ausgaben
        }
        for col, width in column_widths.items():
            ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = width

        # Build filename (e.g. 'Umsatz 25.11.xlsx')
        filename = f"Umsatz {aktuelles_datum.strftime('%y.%m')}.xlsx"
        wb.save(filename)
        # On Windows, open the file automatically after saving
        try:
            abs_path = os.path.abspath(filename)
            if os.name == 'nt':
                os.startfile(abs_path)
        except Exception:
            # best-effort open, ignore errors
            pass

        info_label.configure(text=f"📤 Export erfolgreich: {filename}")
    except Exception as e:
        info_label.configure(text=f"❌ Fehler beim Export: {e}")


def load_db():
    """Load transactions and anfangsbestand from DB_CSV if present."""
    global anfangsbestand, transaktionen
    if not os.path.exists(DB_CSV):
        return
    try:
        with open(DB_CSV, newline="", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=";")
            rows = list(reader)
        if not rows:
            return
        start = 0
        # optional header row for Anfangsbestand
        if rows[0] and rows[0][0].strip().lower() == "anfangsbestand":
            try:
                anfangsbestand = float(rows[0][1].replace(',', '.'))
            except Exception:
                anfangsbestand = 0.0
            start = 1

        for r in rows[start:]:
            if len(r) >= 3:
                try:
                    tdate = r[0]
                    k = r[1]
                    b = float(r[2].replace(',', '.'))
                    transaktionen.append({"Datum": tdate, "Kategorie": k, "Betrag": b})
                except Exception:
                    continue
    except Exception:
        return


def save_all_to_csv():
    """Write the entire DB (Anfangsbestand header if present + all transactions)."""
    try:
        with open(DB_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=';')
            # write anfangsbestand as first line
            writer.writerow(["Anfangsbestand", f"{anfangsbestand:.2f}"])
            for t in transaktionen:
                writer.writerow([t["Datum"], t["Kategorie"], f"{t['Betrag']:.2f}"])
    except Exception:
        return


def refresh_transaction_list():
    """Refresh the Listbox content from transaktionen."""
    transaction_listbox.delete(0, tk.END)
    for idx, t in enumerate(transaktionen):
        # Formatiere Betrag mit Tausenderpunkten und Komma
        betrag = abs(t['Betrag'])
        if betrag >= 1000:
            betrag_str = f"{betrag:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            betrag_str = f"{betrag:.2f}".replace(".", ",")
        
        # Feste Breiten für die Spalten
        datum = t['Datum'].ljust(10)  # Datum hat immer 10 Zeichen
        kategorie = t['Kategorie'].ljust(30)  # Kategorie auf 30 Zeichen auffüllen
        betrag_str = f"{betrag_str} €".rjust(15)  # Betrag rechtsbündig, 15 Zeichen
        
        display = f"{datum} | {kategorie} | {betrag_str}"
        transaction_listbox.insert(tk.END, display)
    
    # Scrolle zur letzten Transaktion
    transaction_listbox.see(tk.END)
    transaction_listbox.selection_clear(0, tk.END)  # Entferne eventuell vorhandene Auswahl


def delete_selected_transaction():
    sel = transaction_listbox.curselection()
    if not sel:
        info_label.configure(text="❌ Keine Transaktion ausgewählt")
        return
    idx = sel[0]
    # remove from memory
    try:
        removed = transaktionen.pop(idx)
    except Exception:
        info_label.configure(text="❌ Fehler beim Löschen")
        return
    # rewrite CSV preserving anfangsbestand
    save_all_to_csv()
    refresh_transaction_list()
    # Formatiere Betrag für die Anzeige
    betrag_abs = abs(removed['Betrag'])
    if betrag_abs >= 1000:
        betrag_str = f"{betrag_abs:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        betrag_str = f"{betrag_abs:.2f}".replace(".", ",")
    info_label.configure(text=f"🗑️ Transaktion gelöscht: {removed['Kategorie']} {betrag_str} €")


def ask_firma_if_needed():
    """Fragt nach dem Firmennamen wenn noch nicht gesetzt."""
    global firmenname
    if firmenname:
        return
    
    # Simple modal dialog
    dialog = ctk.CTkToplevel(app)
    dialog.title("Firma")
    dialog.geometry("400x200")  # Größeres Fenster
    label = ctk.CTkLabel(dialog, text="Firmenname:", font=("Segoe UI", 14))
    label.pack(pady=(30, 10))
    entry = ctk.CTkEntry(dialog, width=250)  # Breiteres Eingabefeld
    entry.pack(pady=10)

    def submit():
        global firmenname
        firma = entry.get().strip()
        if firma:
            firmenname = firma
            dialog.destroy()
        else:
            info_label.configure(text="❌ Bitte Firmennamen eingeben")

    submit_btn = ctk.CTkButton(dialog, text="OK", command=submit, width=120, height=40, font=("Segoe UI", 14))
    submit_btn.pack(pady=20)
    
    # Zentriere das Fenster auf dem Bildschirm
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    dialog.grab_set()
    app.wait_window(dialog)

def ask_anfangsbestand_if_needed():
    """Ask user for Anfangsbestand if not already set from CSV."""
    global anfangsbestand
    if anfangsbestand != 0.0:
        return

    # Simple modal dialog
    dialog = ctk.CTkToplevel(app)
    dialog.title("Anfangsbestand")
    dialog.geometry("300x120")
    label = ctk.CTkLabel(dialog, text="Anfangsbestand (€):")
    label.pack(pady=(20, 5))
    entry = ctk.CTkEntry(dialog)
    entry.pack(pady=5)

    def submit():
        nonlocal_entry = entry.get()
        try:
            val = float(nonlocal_entry) if nonlocal_entry.strip() != "" else 0.0
        except ValueError:
            info_label.configure(text="❌ Ungültiger Anfangsbestand")
            return

        # write/update CSV header
        rows = []
        if os.path.exists(DB_CSV):
            try:
                with open(DB_CSV, newline="", encoding="utf-8") as f:
                    reader = csv.reader(f, delimiter=";")
                    rows = list(reader)
            except Exception:
                rows = []

        try:
            with open(DB_CSV, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["Anfangsbestand", f"{val:.2f}"])
                for r in rows:
                    writer.writerow(r)
        except Exception as e:
            info_label.configure(text=f"❌ Fehler beim Schreiben der DB: {e}")
            dialog.destroy()
            return

        anfangsbestand = val
        # Formatiere Anfangsbestand für die Anzeige
        if anfangsbestand >= 1000:
            bestand_str = f"{anfangsbestand:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            bestand_str = f"{anfangsbestand:.2f}".replace(".", ",")
        info_label.configure(text=f"Anfangsbestand gesetzt: {bestand_str} €")
        dialog.destroy()

    submit_btn = ctk.CTkButton(dialog, text="OK", command=submit)
    submit_btn.pack(pady=10)
    dialog.grab_set()
    app.wait_window(dialog)

# === GUI ELEMENTE ===
aktuelles_datum = heutiges_datum

datum_frame = ctk.CTkFrame(app)
datum_frame.pack(pady=10)

minus_button = ctk.CTkButton(datum_frame, text="◀", width=40, command=datum_minus)
minus_button.pack(side="left", padx=5)

datum_label = ctk.CTkLabel(datum_frame, text="")
datum_label.pack(side="left", padx=10)
datum_anzeigen()

plus_button = ctk.CTkButton(datum_frame, text="▶", width=40, command=datum_plus)
plus_button.pack(side="left", padx=5)

# Kategorie Auswahl mit einheitlicher Einrückung
kategorien = [
    "💰  Tagesumsatz Kasse",
    "⛽  Tankbeleg",
    "🧹  Rechnung Teppichreinigung",
    "💶  Bargeldeinzahlung",
    "👤  Bargeldeinzahlung - Privat",
    "📊  Buchhaltungsservice",
    "🛍️  Wareneinkauf"
]
kategorie_option = ctk.CTkOptionMenu(app, values=kategorien, width=250)
kategorie_option.pack(pady=10)

# Betrag Eingabe
betrag_entry = ctk.CTkEntry(app, placeholder_text="Betrag (€)")
betrag_entry.pack(pady=10)

# Enter-Taste im Betrags-Feld führt Hinzufügen aus
def on_enter_pressed(event):
    transaktion_hinzufügen()
betrag_entry.bind("<Return>", on_enter_pressed)

# Buttons
add_button = ctk.CTkButton(app, text="Transaktion hinzufügen", command=transaktion_hinzufügen)
add_button.pack(pady=5)

export_button = ctk.CTkButton(app, text="📤 In Excel exportieren", fg_color="green", command=exportieren)
export_button.pack(pady=10)

# Info Label
info_label = ctk.CTkLabel(app, text="")
info_label.pack(pady=10)

# Transaction list and delete button
transactions_frame = ctk.CTkFrame(app)
transactions_frame.pack(pady=(5, 10), fill="both", expand=False)

# Use classic Tk Listbox inside the CTk frame for simplicity
listbox_container = tk.Frame(transactions_frame)
listbox_container.pack(side="left", fill="both", expand=True, padx=(10, 0))

transaction_listbox = tk.Listbox(listbox_container, height=8, width=60)
transaction_listbox.pack(side="left", fill="both", expand=True)

scrollbar = tk.Scrollbar(listbox_container, orient="vertical", command=transaction_listbox.yview)
scrollbar.pack(side="right", fill="y")
transaction_listbox.config(yscrollcommand=scrollbar.set)

delete_button = ctk.CTkButton(transactions_frame, text="Transaktion löschen", fg_color="#e74c3c", command=delete_selected_transaction)
delete_button.pack(side="left", padx=10)

# Load existing DB and ask for firma and Anfangsbestand if needed before starting
load_db()
refresh_transaction_list()
ask_firma_if_needed()
ask_anfangsbestand_if_needed()
# Formatiere Anfangsbestand für die Anzeige
if anfangsbestand >= 1000:
    bestand_str = f"{anfangsbestand:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
else:
    bestand_str = f"{anfangsbestand:.2f}".replace(".", ",")
info_label.configure(text=f"Anfangsbestand: {bestand_str} € | geladene Transaktionen: {len(transaktionen)}")

app.mainloop()
