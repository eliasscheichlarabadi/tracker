import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, simpledialog
from datetime import date, timedelta
import openpyxl
import csv
import json
import os

# === KONFIGURATION ===
EXCEL_DATEI = "Umsatz 25.09 (2).xlsx"
DB_CSV = "db.csv"

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
transaction_listbox = None
open_transaction_windows = []


def format_currency(value):
    """Format a value using German thousands separators and append €."""
    if value is None or value == "":
        return ""
    value = round(float(value), 2)
    if abs(value) >= 1000:
        formatted = (
            f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
    else:
        formatted = f"{abs(value):.2f}".replace(".", ",")
    return f"{formatted} €"


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


def save_all_to_csv():
    """Write the entire DB (Anfangsbestand header if present + all transactions)."""
    try:
        with open(DB_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            if firmenname:
                writer.writerow(["Firma", firmenname])
            writer.writerow(["Anfangsbestand", f"{anfangsbestand:.2f}"])
            for t in transaktionen:
                writer.writerow([t["Datum"], t["Kategorie"], f"{t['Betrag']:.2f}"])
    except Exception:
        pass


def load_db():
    """Load transactions and anfangsbestand from DB_CSV if present."""
    global anfangsbestand, transaktionen, firmenname
    if not os.path.exists(DB_CSV):
        return
    try:
        with open(DB_CSV, newline="", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=";")
            rows = list(reader)
    except Exception:
        return

    transaktionen = []
    anfangsbestand = 0.0
    firmenname_local = ""

    for row in rows:
        if not row:
            continue
        key = row[0].strip().lower()
        if key == "firma" and len(row) > 1:
            firmenname_local = row[1].strip()
        elif key == "anfangsbestand" and len(row) > 1:
            try:
                anfangsbestand = float(row[1].replace(",", "."))
            except ValueError:
                anfangsbestand = 0.0
        elif len(row) >= 3:
            try:
                tdate = row[0]
                kategorie = row[1]
                betrag = float(row[2].replace(",", "."))
                transaktionen.append({
                    "Datum": tdate,
                    "Kategorie": kategorie,
                    "Betrag": betrag,
                })
            except ValueError:
                continue

    if firmenname_local:
        global firmenname
        firmenname = firmenname_local


def ask_firma_if_needed(force: bool = False):
    """Fragt nach dem Firmennamen, sofern nötig oder erzwungen."""
    global firmenname
    if firmenname and not force:
        return

    dialog = ctk.CTkToplevel(app)
    dialog.title("Firmenname")
    dialog.geometry("360x180")

    label = ctk.CTkLabel(dialog, text="Bitte Firmennamen eingeben:")
    label.pack(pady=(25, 10))

    entry = ctk.CTkEntry(dialog, width=240)
    entry.pack(pady=5)

    def submit():
        global firmenname
        name = entry.get().strip()
        if not name:
            info_label.configure(text="❌ Bitte Firmennamen eingeben")
            return
        firmenname = name
        save_all_to_csv()
        dialog.destroy()

    submit_btn = ctk.CTkButton(dialog, text="OK", command=submit)
    submit_btn.pack(pady=15)

    dialog.grab_set()
    app.wait_window(dialog)


def ask_anfangsbestand_if_needed(force: bool = False):
    """Ask user for Anfangsbestand if not already set from CSV."""
    global anfangsbestand
    if anfangsbestand != 0.0 and not force:
        return

    dialog = ctk.CTkToplevel(app)
    dialog.title("Anfangsbestand")
    dialog.geometry("320x140")

    label = ctk.CTkLabel(dialog, text="Anfangsbestand (€):")
    label.pack(pady=(20, 8))

    entry = ctk.CTkEntry(dialog)
    entry.pack(pady=5)

    def submit():
        nonlocal_entry = entry.get()
        try:
            value = float(nonlocal_entry) if nonlocal_entry.strip() else 0.0
        except ValueError:
            info_label.configure(text="❌ Ungültiger Anfangsbestand")
            return

        global anfangsbestand
        anfangsbestand = value
        save_all_to_csv()
        if anfangsbestand >= 1000:
            bestand_str = (
                f"{anfangsbestand:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
        else:
            bestand_str = f"{anfangsbestand:.2f}".replace(".", ",")
        info_label.configure(text=f"Anfangsbestand gesetzt: {bestand_str} €")
        dialog.destroy()

    submit_btn = ctk.CTkButton(dialog, text="OK", command=submit)
    submit_btn.pack(pady=12)

    dialog.grab_set()
    app.wait_window(dialog)


def refresh_transaction_list():
    """Refresh the Listbox content from transaktionen."""
    transaction_listbox.delete(0, tk.END)
    for t in transaktionen:
        betrag = abs(t["Betrag"])
        if betrag >= 1000:
            betrag_str = (
                f"{betrag:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
        else:
            betrag_str = f"{betrag:.2f}".replace(".", ",")

        datum = t["Datum"].ljust(10)
        kategorie = t["Kategorie"].ljust(30)
        betrag_str = f"{betrag_str} €".rjust(15)
        display = f"{datum} | {kategorie} | {betrag_str}"
        transaction_listbox.insert(tk.END, display)

    transaction_listbox.see(tk.END)
    transaction_listbox.selection_clear(0, tk.END)


def transaktion_hinzufügen():
    # accept comma as decimal separator
    betrag_text = betrag_entry.get().strip().replace(",", ".")
    try:
        betrag_raw = float(betrag_text) if betrag_text else 0.0
    except ValueError:
        info_label.configure(text="❌ Ungültiger Betrag")
        return

    kategorie = kategorie_option.get()

    if "Tagesumsatz Kasse" in kategorie:
        betrag = abs(betrag_raw)
    else:
        betrag = -abs(betrag_raw)

    transaktionen.append({
        "Datum": aktuelles_datum.strftime("%Y-%m-%d"),
        "Kategorie": kategorie,
        "Betrag": betrag,
    })

    try:
        save_all_to_csv()
    except Exception as exc:
        info_label.configure(text=f"❌ Fehler beim Speichern in CSV: {exc}")
        return

    betrag_abs = abs(betrag)
    if betrag_abs >= 1000:
        betrag_str = (
            f"{betrag_abs:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
    else:
        betrag_str = f"{betrag_abs:.2f}".replace(".", ",")
    info_label.configure(
        text=f"💾 Transaktion gespeichert ({kategorie}: {betrag_str} €)"
    )
    betrag_entry.delete(0, "end")
    refresh_transaction_list()
    for window in list(open_transaction_windows):
        if window.winfo_exists():
            window.event_generate("<<TransactionsUpdated>>", when="tail")
        else:
            open_transaction_windows.remove(window)


def delete_transaction_at_index(idx):
    try:
        removed = transaktionen.pop(idx)
    except Exception:
        return None

    save_all_to_csv()
    refresh_transaction_list()

    betrag_abs = abs(removed["Betrag"])
    if betrag_abs >= 1000:
        betrag_str = (
            f"{betrag_abs:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
    else:
        betrag_str = f"{betrag_abs:.2f}".replace(".", ",")
    info_label.configure(
        text=f"🗑️ Transaktion gelöscht: {removed['Kategorie']} {betrag_str} €"
    )
    return removed


def delete_selected_transaction():
    sel = transaction_listbox.curselection()
    if not sel:
        info_label.configure(text="❌ Keine Transaktion ausgewählt")
        return

    idx = sel[0]
    if delete_transaction_at_index(idx) is None:
        info_label.configure(text="❌ Fehler beim Löschen")
        return

    for window in list(open_transaction_windows):
        if not window.winfo_exists():
            open_transaction_windows.remove(window)
            continue
        window.event_generate("<<TransactionsUpdated>>", when="tail")


def open_transaction_window():
    """Öffnet ein separates Fenster mit den aktuellen Transaktionen."""

    window = ctk.CTkToplevel(app)
    window.title("Transaktionen")
    window.geometry("520x320")

    list_container = tk.Frame(window)
    list_container.pack(fill="both", expand=True, padx=10, pady=(10, 0))

    listbox = tk.Listbox(list_container, height=10, width=70)
    listbox.pack(side="left", fill="both", expand=True)

    scrollbar = tk.Scrollbar(list_container, orient="vertical", command=listbox.yview)
    scrollbar.pack(side="right", fill="y")
    listbox.config(yscrollcommand=scrollbar.set)

    def populate_listbox():
        listbox.delete(0, tk.END)
        for t in transaktionen:
            betrag = abs(t["Betrag"])
            if betrag >= 1000:
                betrag_str = (
                    f"{betrag:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )
            else:
                betrag_str = f"{betrag:.2f}".replace(".", ",")

            datum = t["Datum"].ljust(10)
            kategorie = t["Kategorie"].ljust(30)
            betrag_str = f"{betrag_str} €".rjust(15)
            listbox.insert(tk.END, f"{datum} | {kategorie} | {betrag_str}")

    populate_listbox()

    def delete_from_window():
        selection = listbox.curselection()
        if not selection:
            messagebox.showinfo(
                "Hinweis",
                "Bitte eine Transaktion auswählen.",
                parent=window,
            )
            return
        idx = selection[0]
        if delete_transaction_at_index(idx) is None:
            messagebox.showerror(
                "Fehler",
                "Transaktion konnte nicht gelöscht werden.",
                parent=window,
            )
            return
        populate_listbox()
        for other in list(open_transaction_windows):
            if other is window:
                continue
            if other.winfo_exists():
                other.event_generate("<<TransactionsUpdated>>", when="tail")
            else:
                open_transaction_windows.remove(other)

    button_bar = ctk.CTkFrame(window)
    button_bar.pack(fill="x", padx=10, pady=10)

    delete_btn = ctk.CTkButton(
        button_bar,
        text="Transaktion löschen",
        fg_color="#e74c3c",
        command=delete_from_window,
    )
    delete_btn.pack(side="left")

    close_button = ctk.CTkButton(button_bar, text="Schließen", command=lambda: on_close())
    close_button.pack(side="right")

    def handle_update(_event):
        if window.winfo_exists():
            populate_listbox()

    window.bind("<<TransactionsUpdated>>", handle_update)
    open_transaction_windows.append(window)

    def on_close():
        if window in open_transaction_windows:
            open_transaction_windows.remove(window)
        window.destroy()

    window.protocol("WM_DELETE_WINDOW", on_close)


def create_new_umsatz():
    """Reset the current revenue data to start a new record."""
    if not messagebox.askyesno(
        "Neuen Umsatz anlegen",
        "Alle aktuellen Transaktionen löschen und neu beginnen?",
        parent=app,
    ):
        return

    global transaktionen, anfangsbestand, aktuelles_datum, firmenname
    transaktionen = []
    anfangsbestand = 0.0
    aktuelles_datum = date.today()
    firmenname = ""

    if os.path.exists(DB_CSV):
        try:
            os.remove(DB_CSV)
        except Exception:
            pass

    refresh_transaction_list()
    datum_anzeigen()
    ask_firma_if_needed(force=True)
    ask_anfangsbestand_if_needed(force=True)
    save_all_to_csv()
    info_label.configure(
        text="🆕 Neuer Umsatz vorbereitet. Bitte Transaktionen erfassen."
    )
    for window in list(open_transaction_windows):
        if window.winfo_exists():
            window.event_generate("<<TransactionsUpdated>>", when="tail")
        else:
            open_transaction_windows.remove(window)



def delete_selected_transaction():
    sel = transaction_listbox.curselection()
    if not sel:
        info_label.configure(text="❌ Keine Transaktion ausgewählt")
        return

    idx = sel[0]
    try:
        removed = transaktionen.pop(idx)
    except Exception:
        info_label.configure(text="❌ Fehler beim Löschen")
        return

    save_all_to_csv()
    refresh_transaction_list()

    betrag_abs = abs(removed["Betrag"])
    if betrag_abs >= 1000:
        betrag_str = (
            f"{betrag_abs:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
    else:
        betrag_str = f"{betrag_abs:.2f}".replace(".", ",")
    info_label.configure(
        text=f"🗑️ Transaktion gelöscht: {removed['Kategorie']} {betrag_str} €"
    )


def open_transaction_window():
    """Öffnet ein separates Fenster mit den aktuellen Transaktionen."""

    window = ctk.CTkToplevel(app)
    window.title("Transaktionen")
    window.geometry("520x260")

    list_container = tk.Frame(window)
    list_container.pack(fill="both", expand=True, padx=10, pady=10)

    listbox = tk.Listbox(list_container, height=10, width=70)
    listbox.pack(side="left", fill="both", expand=True)

    scrollbar = tk.Scrollbar(list_container, orient="vertical", command=listbox.yview)
    scrollbar.pack(side="right", fill="y")
    listbox.config(yscrollcommand=scrollbar.set)

    for t in transaktionen:
        betrag = abs(t["Betrag"])
        if betrag >= 1000:
            betrag_str = (
                f"{betrag:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
        else:
            betrag_str = f"{betrag:.2f}".replace(".", ",")

        datum = t["Datum"].ljust(10)
        kategorie = t["Kategorie"].ljust(30)
        betrag_str = f"{betrag_str} €".rjust(15)
        listbox.insert(tk.END, f"{datum} | {kategorie} | {betrag_str}")

    close_button = ctk.CTkButton(window, text="Schließen", command=window.destroy)
    close_button.pack(pady=(0, 10))


def create_new_umsatz():
    """Reset the current revenue data to start a new record."""
    if not messagebox.askyesno(
        "Neuen Umsatz anlegen",
        "Alle aktuellen Transaktionen löschen und neu beginnen?",
        parent=app,
    ):
        return

    global transaktionen, anfangsbestand, aktuelles_datum, firmenname
    transaktionen = []
    anfangsbestand = 0.0
    aktuelles_datum = date.today()
    firmenname = ""

    if os.path.exists(DB_CSV):
        try:
            os.remove(DB_CSV)
        except Exception:
            pass

    refresh_transaction_list()
    datum_anzeigen()
    ask_firma_if_needed(force=True)
    ask_anfangsbestand_if_needed(force=True)
    save_all_to_csv()
    info_label.configure(
        text="🆕 Neuer Umsatz vorbereitet. Bitte Transaktionen erfassen."
    )


def exportieren():
    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "EÜR"

        header_font = openpyxl.styles.Font(name="Arial", bold=True, size=10)
        normal_font = openpyxl.styles.Font(name="Arial", size=10)
        money_format = "@"
        thin_border = openpyxl.styles.Border(
            left=openpyxl.styles.Side(style="thin"),
            right=openpyxl.styles.Side(style="thin"),
            top=openpyxl.styles.Side(style="thin"),
            bottom=openpyxl.styles.Side(style="thin"),
        )
        header_fill = openpyxl.styles.PatternFill(
            start_color="E6E6E6", end_color="E6E6E6", fill_type="solid"
        )
        grey_fill = openpyxl.styles.PatternFill(
            start_color="F2F2F2", end_color="F2F2F2", fill_type="solid"
        )

        ws.append([firmenname])
        ws.append([])

        ws.append([
            "",
            "",
            "",
            "Anfangsbestand:",
            format_currency(anfangsbestand),
        ])
        anfang_row = ws.max_row
        for col in range(4, 6):
            cell = ws.cell(row=anfang_row, column=col)
            cell.font = header_font
            cell.border = thin_border
            if col == 4:
                cell.fill = grey_fill
                cell.alignment = openpyxl.styles.Alignment(horizontal="right")
            else:
                cell.number_format = money_format
                cell.alignment = openpyxl.styles.Alignment(horizontal="right")

        header_row = ws.max_row + 1
        ws.append(["Beleg-Nr.", "Datum", "Transaktion", "Einnahmen", "Ausgaben"])
        for col in range(1, 6):
            cell = ws.cell(row=header_row, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border
            if col in [4, 5]:
                cell.alignment = openpyxl.styles.Alignment(horizontal="right")
            else:
                cell.alignment = openpyxl.styles.Alignment(horizontal="center")

        for idx, t in enumerate(transaktionen, 1):
            betrag = t["Betrag"]
            einnahme = format_currency(abs(betrag)) if betrag > 0 else ""
            ausgabe = format_currency(abs(betrag)) if betrag < 0 else ""
            ws.append(
                [
                    idx,
                    t["Datum"].replace("-", "/"),
                    t["Kategorie"].split(" ", 1)[1] if " " in t["Kategorie"] else t["Kategorie"],
                    einnahme,
                    ausgabe,
                ]
            )

            current_row = ws.max_row
            for col in range(1, 6):
                cell = ws.cell(row=current_row, column=col)
                cell.font = normal_font
                cell.border = thin_border
                if col in [4, 5]:
                    cell.number_format = money_format
                    cell.alignment = openpyxl.styles.Alignment(horizontal="right")
                elif col == 1 or col == 2:
                    cell.alignment = openpyxl.styles.Alignment(horizontal="center")
                else:
                    cell.alignment = openpyxl.styles.Alignment(horizontal="left")

        einnahmen = sum(t["Betrag"] for t in transaktionen if t["Betrag"] > 0)
        ausgaben = sum(-t["Betrag"] for t in transaktionen if t["Betrag"] < 0)
        gewinn = einnahmen - ausgaben
        endbestand = anfangsbestand + gewinn

        ws.append([])
        last_data_row = ws.max_row
        for col in range(1, 6):
            cell = ws.cell(row=last_data_row, column=col)
            current_border = cell.border
            cell.border = openpyxl.styles.Border(
                left=current_border.left,
                right=current_border.right,
                top=current_border.top,
                bottom=openpyxl.styles.Side(style="thin"),
            )

        ws.append([])

        ws.append([
            "",
            "",
            "Gesamt:",
            format_currency(einnahmen),
            format_currency(ausgaben),
        ])
        current_row = ws.max_row

        gesamt_cell = ws.cell(row=current_row, column=3)
        gesamt_cell.font = header_font
        gesamt_cell.border = thin_border
        gesamt_cell.fill = grey_fill
        gesamt_cell.alignment = openpyxl.styles.Alignment(horizontal="right")

        for col in [4, 5]:
            cell = ws.cell(row=current_row, column=col)
            cell.font = header_font
            cell.border = thin_border
            cell.number_format = money_format
            cell.alignment = openpyxl.styles.Alignment(horizontal="right")

        ws.append([
            "",
            "",
            "",
            "Endbestand:",
            format_currency(endbestand),
        ])
        current_row = ws.max_row
        for col in range(4, 6):
            cell = ws.cell(row=current_row, column=col)
            cell.font = header_font
            cell.border = thin_border
            if col == 4:
                cell.fill = grey_fill
                cell.alignment = openpyxl.styles.Alignment(horizontal="right")
            else:
                cell.number_format = money_format
                cell.alignment = openpyxl.styles.Alignment(horizontal="right")

        column_widths = {1: 12, 2: 12, 3: 40, 4: 18, 5: 18}
        for col, width in column_widths.items():
            ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = width

        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, max_col=5):
            for cell in row:
                cell.font = cell.font.copy(name="Arial", size=10)

        filename = f"Umsatz {aktuelles_datum.strftime('%y.%m')}.xlsx"
        wb.save(filename)

        record_umsatz_export(filename, einnahmen, ausgaben, gewinn, endbestand)
        info_label.configure(text=f"📤 Export erfolgreich: {filename}")
    except Exception as exc:
        info_label.configure(text=f"❌ Fehler beim Export: {exc}")

    name = simpledialog.askstring(
        "Umsatz speichern",
        "Name für den Umsatz (Dateiname)",
        parent=app,
    )

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

kategorien = [
    "💰  Tagesumsatz Kasse",
    "⛽  Tankbeleg",
    "🧹  Rechnung Teppichreinigung",
    "💶  Bargeldeinzahlung",
    "👤  Bargeldeinzahlung - Privat",
    "📊  Buchhaltungsservice",
    "🛍️  Wareneinkauf",
]
kategorie_option = ctk.CTkOptionMenu(app, values=kategorien, width=250)
kategorie_option.pack(pady=10)

betrag_row = ctk.CTkFrame(app)
betrag_row.pack(pady=10)

betrag_entry = ctk.CTkEntry(betrag_row, placeholder_text="Betrag (€)")
betrag_entry.pack(side="left", padx=(0, 8))


def on_enter_pressed(event):
    transaktion_hinzufügen()


betrag_entry.bind("<Return>", on_enter_pressed)

add_arrow_button = ctk.CTkButton(
    betrag_row,
    text="➤",
    width=40,
    command=transaktion_hinzufügen,
)
add_arrow_button.pack(side="left")

export_button = ctk.CTkButton(
    app,
    text="📤 In Excel exportieren",
    fg_color="green",
    command=exportieren,
)
export_button.pack(pady=10)

new_umsatz_button = ctk.CTkButton(
    app,
    text="🆕 Neuen Umsatz anlegen",
    fg_color="#2980b9",
    command=create_new_umsatz,
)
new_umsatz_button.pack(pady=5)

show_transactions_button = ctk.CTkButton(
    app,
    text="📋 Transaktionen anzeigen",
    command=open_transaction_window,
)
show_transactions_button.pack(pady=5)

info_label = ctk.CTkLabel(app, text="")
info_label.pack(pady=10)

transactions_frame = ctk.CTkFrame(app)
transactions_frame.pack(pady=(5, 10), fill="both", expand=False)

listbox_container = tk.Frame(transactions_frame)
listbox_container.pack(side="left", fill="both", expand=True, padx=(10, 0))

transaction_listbox = tk.Listbox(listbox_container, height=8, width=60)
transaction_listbox.pack(side="left", fill="both", expand=True)

scrollbar = tk.Scrollbar(listbox_container, orient="vertical", command=transaction_listbox.yview)
scrollbar.pack(side="right", fill="y")
transaction_listbox.config(yscrollcommand=scrollbar.set)

delete_button = ctk.CTkButton(
    transactions_frame,
    text="Transaktion löschen",
    fg_color="#e74c3c",
    command=delete_selected_transaction,
)
delete_button.pack(side="left", padx=10)

# Load existing DB and ask for firma and Anfangsbestand if needed before starting
load_settings()
load_umsatz_history()
load_db()
refresh_transaction_list()
ask_firma_if_needed()
ask_anfangsbestand_if_needed()

if anfangsbestand >= 1000:
    bestand_str = (
        f"{anfangsbestand:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
else:
    bestand_str = f"{anfangsbestand:.2f}".replace(".", ",")
firmeninfo = f" | Firma: {firmenname}" if firmenname else ""
info_label.configure(
    text=f"Anfangsbestand: {bestand_str} € | geladene Transaktionen: {len(transaktionen)}{firmeninfo}"
)

app.mainloop()
