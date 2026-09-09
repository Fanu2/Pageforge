import sys
import json
from fractions import Fraction
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QFileDialog, QDialog,
    QDialogButtonBox, QFormLayout, QComboBox, QGroupBox, QSplitter,
    QAbstractItemView, QStatusBar, QTabWidget
)

# Conventions represented in the supplied Khatrawan spreadsheet:
# 1 Kanal = 20 Marla
# 1 Killa = 8 Kanal = 160 Marla
# 1 Marla = 9 Sarshai
MARLA_PER_KANAL = 20.0
MARLA_PER_KILLA = 160.0
SARSHARI_PER_MARLA = 9.0


def fmt(x, digits=6):
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:.{digits}f}".rstrip("0").rstrip(".")


def parse_share(text):
    text = text.strip()
    if not text:
        raise ValueError("Ownership share cannot be empty.")
    try:
        return float(Fraction(text)) if "/" in text else float(text)
    except Exception as exc:
        raise ValueError(f"Invalid ownership share: {text}") from exc


def area_marla(kanal, marla):
    return float(kanal) * MARLA_PER_KANAL + float(marla)


def area_parts(total_marla):
    killa = int(total_marla // MARLA_PER_KILLA)
    rem = total_marla - killa * MARLA_PER_KILLA
    kanal = int(rem // MARLA_PER_KANAL)
    rem -= kanal * MARLA_PER_KANAL
    marla = int(rem)
    sarshai = int(round((rem - marla) * SARSHARI_PER_MARLA))
    if sarshai >= 9:
        marla += 1
        sarshai = 0
    if marla >= 20:
        kanal += 1
        marla -= 20
    if kanal >= 8:
        killa += 1
        kanal -= 8
    return killa, kanal, marla, sarshai


def area_text(total_marla):
    k, ka, m, s = area_parts(total_marla)
    return f"{k} Killa • {ka} Kanal • {m} Marla • {s} Sarshai"


class KhewatDialog(QDialog):
    def __init__(self, parent=None, existing=None):
        super().__init__(parent)
        self.setWindowTitle("Add Khewat" if existing is None else "Edit Khewat")
        form = QFormLayout(self)
        self.number = QLineEdit(str(existing["number"]) if existing else "")
        self.note = QLineEdit(str(existing.get("note", "")) if existing else "")
        form.addRow("Khewat number:", self.number)
        form.addRow("Description / note:", self.note)
        hint = QLabel("The Khewat's total area is calculated automatically from its parcels.")
        hint.setWordWrap(True)
        form.addRow(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        return self.number.text().strip(), self.note.text().strip()


class ParcelDialog(QDialog):
    def __init__(self, khewat, parent=None, existing=None):
        super().__init__(parent)
        self.setWindowTitle("Add Parcel" if existing is None else "Edit Parcel")
        form = QFormLayout(self)
        self.khewat = QLabel(str(khewat))
        self.murabba = QLineEdit(str(existing.get("murabba", "")) if existing else "")
        self.square = QLineEdit(str(existing.get("square", "")) if existing else "")
        self.kanal = QSpinBox()
        self.kanal.setRange(0, 1000000)
        self.kanal.setValue(int(existing.get("kanal", 0)) if existing else 0)
        self.marla = QDoubleSpinBox()
        self.marla.setRange(0, 19.999999)
        self.marla.setDecimals(6)
        self.marla.setValue(float(existing.get("marla", 0)) if existing else 0)
        self.kh_no = QLineEdit(str(existing.get("kh_no", "")) if existing else "")
        form.addRow("Khewat:", self.khewat)
        form.addRow("Murabba:", self.murabba)
        form.addRow("Square:", self.square)
        form.addRow("Area — Kanal:", self.kanal)
        form.addRow("Area — Marla:", self.marla)
        form.addRow("Khasra / Kh. No.:", self.kh_no)
        hint = QLabel("A parcel belongs to exactly one Khewat. Enter its area as Kanal + remaining Marla.")
        hint.setWordWrap(True)
        form.addRow(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        return {
            "murabba": self.murabba.text().strip(),
            "square": self.square.text().strip(),
            "kanal": self.kanal.value(),
            "marla": self.marla.value(),
            "kh_no": self.kh_no.text().strip(),
        }


class OwnerDialog(QDialog):
    def __init__(self, khewats, parent=None, existing=None):
        super().__init__(parent)
        self.setWindowTitle("Add Ownership Share" if existing is None else "Edit Ownership Share")
        form = QFormLayout(self)
        self.owner = QLineEdit(str(existing.get("owner", "")) if existing else "")
        self.khewat = QComboBox()
        self.khewat.addItems([str(k) for k in khewats])
        if existing:
            i = self.khewat.findText(str(existing["khewat"]))
            if i >= 0:
                self.khewat.setCurrentIndex(i)
        self.share = QLineEdit(str(existing.get("share", "1/1")) if existing else "1/1")
        form.addRow("Owner:", self.owner)
        form.addRow("Khewat:", self.khewat)
        form.addRow("Share:", self.share)
        hint = QLabel("Examples: 1/12, 37/312, 106/1347, or 0.25")
        hint.setWordWrap(True)
        form.addRow(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        return {
            "owner": self.owner.text().strip(),
            "khewat": self.khewat.currentText(),
            "share": self.share.text().strip(),
        }


class KhatrawanCalculator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Khatrawan — Khewat Parcel & Ownership Calculator")
        self.resize(1500, 920)
        self.khewats = []
        self.parcels = []
        self.owners = []
        self._loading = False
        self.build_ui()
        self.load_sample()
        self.recalculate()

    def build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setSpacing(9)

        title = QLabel("Khatrawan — Khewat Parcel & Ownership Calculator")
        title.setObjectName("Title")
        subtitle = QLabel(
            "Khewat-wise parcels • Murabba / Square • Kanal + Marla • fractional ownership • "
            "spreadsheet-style owner totals"
        )
        subtitle.setObjectName("Subtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        bar = QHBoxLayout()
        buttons = [
            ("+ Khewat", self.add_khewat),
            ("+ Parcel", self.add_parcel),
            ("Edit Parcel", self.edit_parcel),
            ("Delete Parcel", self.delete_parcel),
            ("+ Owner Share", self.add_owner),
            ("Edit Owner", self.edit_owner),
            ("Delete Owner", self.delete_owner),
            ("Load Sample", self.load_sample),
            ("New", self.new_project),
            ("Open", self.open_project),
            ("Save", self.save_project),
            ("Export XLSX", self.export_xlsx),
        ]
        for text, slot in buttons:
            b = QPushButton(text)
            b.clicked.connect(slot)
            bar.addWidget(b)
        bar.addStretch()
        root.addLayout(bar)

        self.tabs = QTabWidget()
        self.build_khewat_tab()
        self.build_parcel_tab()
        self.build_owner_tab()
        self.build_result_tab()
        root.addWidget(self.tabs, 1)

        cards = QHBoxLayout()
        self.card_total = QLabel()
        self.card_parcels = QLabel()
        self.card_allocated = QLabel()
        self.card_difference = QLabel()
        for label in (self.card_total, self.card_parcels, self.card_allocated, self.card_difference):
            label.setObjectName("Card")
            cards.addWidget(label)
        root.addLayout(cards)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self.setup_menu()
        self.setStyleSheet("""
            QMainWindow { background: #f5f7fb; }
            #Title { font-size: 27px; font-weight: 700; padding-top: 4px; }
            #Subtitle { color: #64748b; font-size: 13px; padding-bottom: 3px; }
            QGroupBox { font-weight: 700; border: 1px solid #d7dce5; border-radius: 10px;
                        margin-top: 8px; padding: 10px; background: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
            QPushButton { padding: 8px 11px; border-radius: 7px; }
            QPushButton:hover { background: #e8eefc; }
            QTableWidget { border: 1px solid #d7dce5; gridline-color: #e7eaf0; background: white; }
            QHeaderView::section { padding: 7px; font-weight: 700; }
            #Card { background: white; border: 1px solid #d7dce5; border-radius: 9px;
                    padding: 11px; font-weight: 600; }
        """)

    def setup_menu(self):
        fm = self.menuBar().addMenu("&File")
        for text, slot in [
            ("New Project", self.new_project),
            ("Open Project", self.open_project),
            ("Save Project", self.save_project),
            ("Export XLSX", self.export_xlsx),
            ("Exit", self.close),
        ]:
            a = QAction(text, self)
            a.triggered.connect(slot)
            fm.addAction(a)
        hm = self.menuBar().addMenu("&Help")
        a = QAction("Unit Rules", self)
        a.triggered.connect(self.show_about)
        hm.addAction(a)

    def table(self, headers):
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setSelectionMode(QAbstractItemView.SingleSelection)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        return t

    def build_khewat_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        box = QGroupBox("Khewats")
        bl = QVBoxLayout(box)
        self.khewat_table = self.table(["Khewat", "Description", "Parcel Count", "Total Kanal", "Total Marla", "Total Area"])
        bl.addWidget(self.khewat_table)
        lay.addWidget(box)
        self.tabs.addTab(page, "Khewats")

    def build_parcel_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        box = QGroupBox("Khewat-wise Area Parcels")
        bl = QVBoxLayout(box)
        self.parcel_table = self.table([
            "Khewat", "Murabba", "Square", "Kanal (K)", "Marla (M)", "Total Marla", "Khasra / Kh. No."
        ])
        bl.addWidget(self.parcel_table)
        hint = QLabel(
            "Each row is one parcel inside a Khewat. Murabba and Square are descriptive land-record "
            "identifiers; the parcel area is entered in K and M."
        )
        hint.setWordWrap(True)
        bl.addWidget(hint)
        lay.addWidget(box)
        self.tabs.addTab(page, "Parcels")

    def build_owner_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        box = QGroupBox("Ownership")
        bl = QVBoxLayout(box)
        self.owner_table = self.table(["Owner", "Khewat", "Share", "Share Decimal", "Khewat Area", "Owner Area"])
        bl.addWidget(self.owner_table)
        lay.addWidget(box)
        self.tabs.addTab(page, "Owners")

    def build_result_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        box = QGroupBox("Final Result — Spreadsheet Style")
        bl = QVBoxLayout(box)
        self.result_table = self.table([])
        self.result_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        bl.addWidget(self.result_table)
        lay.addWidget(box)
        self.tabs.addTab(page, "Final Result")

    def load_sample(self):
        self.khewats = [
            {"number": "100", "note": ""},
            {"number": "101", "note": ""},
            {"number": "102", "note": ""},
            {"number": "215", "note": ""},
            {"number": "216", "note": ""},
        ]
        # Representative structure transcribed from the supplied Khatrawan spreadsheet:
        # Khewat 100 = 1638 Marla; Khewat 101 = 346 Marla; Khewat 102 = 1347 Marla.
        self.parcels = [
            {"khewat": "100", "murabba": "9", "square": "", "kanal": 8, "marla": 0, "kh_no": ""},
            {"khewat": "100", "murabba": "20", "square": "", "kanal": 8, "marla": 0, "kh_no": ""},
            {"khewat": "100", "murabba": "21", "square": "", "kanal": 8, "marla": 0, "kh_no": ""},
            {"khewat": "100", "murabba": "22", "square": "", "kanal": 8, "marla": 0, "kh_no": ""},
            {"khewat": "100", "murabba": "24", "square": "", "kanal": 7, "marla": 11, "kh_no": ""},
            {"khewat": "100", "murabba": "25", "square": "", "kanal": 7, "marla": 4, "kh_no": ""},
            {"khewat": "100", "murabba": "16", "square": "", "kanal": 7, "marla": 12, "kh_no": ""},
            {"khewat": "101", "murabba": "1", "square": "", "kanal": 8, "marla": 0, "kh_no": ""},
            {"khewat": "101", "murabba": "2", "square": "", "kanal": 8, "marla": 0, "kh_no": ""},
            {"khewat": "102", "murabba": "10", "square": "", "kanal": 0, "marla": 0, "kh_no": ""},
            {"khewat": "102", "murabba": "5/1", "square": "", "kanal": 5, "marla": 6, "kh_no": ""},
            {"khewat": "102", "murabba": "5/2", "square": "", "kanal": 2, "marla": 6, "kh_no": ""},
            {"khewat": "102", "murabba": "6/1", "square": "", "kanal": 3, "marla": 12, "kh_no": ""},
            {"khewat": "102", "murabba": "6/2", "square": "", "kanal": 4, "marla": 0, "kh_no": ""},
            {"khewat": "102", "murabba": "7", "square": "", "kanal": 5, "marla": 0, "kh_no": ""},
            {"khewat": "102", "murabba": "14/1", "square": "", "kanal": 4, "marla": 5, "kh_no": ""},
            {"khewat": "102", "murabba": "14/2", "square": "", "kanal": 3, "marla": 15, "kh_no": ""},
            {"khewat": "102", "murabba": "15", "square": "", "kanal": 7, "marla": 12, "kh_no": ""},
            {"khewat": "102", "murabba": "17", "square": "", "kanal": 8, "marla": 0, "kh_no": ""},
            {"khewat": "102", "murabba": "18", "square": "", "kanal": 8, "marla": 0, "kh_no": ""},
            # Khewat 215 — total 594 Marla in the supplied spreadsheet.
            {"khewat": "215", "murabba": "3", "square": "", "kanal": 8, "marla": 0, "kh_no": "371"},
            {"khewat": "215", "murabba": "4/1", "square": "", "kanal": 4, "marla": 4, "kh_no": ""},
            {"khewat": "215", "murabba": "5", "square": "", "kanal": 1, "marla": 12, "kh_no": ""},
            {"khewat": "215", "murabba": "1", "square": "", "kanal": 7, "marla": 18, "kh_no": ""},
            {"khewat": "215", "murabba": "2", "square": "", "kanal": 8, "marla": 0, "kh_no": ""},
            # Khewat 216 — total 514 Marla in the supplied spreadsheet.
            {"khewat": "216", "murabba": "142", "square": "", "kanal": 0, "marla": 9, "kh_no": "373"},
            {"khewat": "216", "murabba": "247", "square": "", "kanal": 1, "marla": 16, "kh_no": ""},
            {"khewat": "216", "murabba": "343", "square": "", "kanal": 0, "marla": 5, "kh_no": ""},
            {"khewat": "216", "murabba": "23", "square": "", "kanal": 7, "marla": 11, "kh_no": ""},
            {"khewat": "216", "murabba": "19/1", "square": "", "kanal": 3, "marla": 18, "kh_no": "375"},
            {"khewat": "216", "murabba": "19/2", "square": "", "kanal": 4, "marla": 4, "kh_no": ""},
            {"khewat": "216", "murabba": "22", "square": "", "kanal": 7, "marla": 11, "kh_no": ""},
        ]
        # Preserve the key ownership relationships visible in the source.
        self.owners = [
            {"owner": "Ram Singh", "khewat": "100", "share": "97/819"},
            {"owner": "Baldev Kaur", "khewat": "100", "share": "38/819"},
            {"owner": "Simerjit Kaur", "khewat": "100", "share": "43/546"},
            {"owner": "Ajaib Singh", "khewat": "100", "share": "32/819"},
            {"owner": "Sukh Jass Baljeet", "khewat": "100", "share": "1175/2184"},
            {"owner": "Satpal", "khewat": "100", "share": "695/6552"},
            {"owner": "Paramjit Kaur", "khewat": "100", "share": "10/273"},
            {"owner": "Shinder Kaur", "khewat": "100", "share": "10/273"},
            {"owner": "Ram Singh", "khewat": "101", "share": "27/346"},
            {"owner": "Jagsir", "khewat": "101", "share": "25/346"},
            {"owner": "Sukh Sat", "khewat": "101", "share": "149/346"},
            {"owner": "Jass Baljeet", "khewat": "101", "share": "46/173"},
            {"owner": "Jaskaran", "khewat": "101", "share": "25/346"},
            {"owner": "Simerjit Kaur", "khewat": "101", "share": "9/173"},
            {"owner": "Ajaib Singh", "khewat": "101", "share": "5/173"},
            {"owner": "Ram Singh", "khewat": "102", "share": "106/1347"},
            {"owner": "Simerjit Kaur", "khewat": "102", "share": "11/449"},
            {"owner": "Ajaib Singh", "khewat": "102", "share": "73/1347"},
            {"owner": "Jass Baljeet", "khewat": "102", "share": "358/1347"},
            {"owner": "Satpal", "khewat": "102", "share": "290/1347"},
            {"owner": "Jaskaran", "khewat": "102", "share": "106/1347"},
            {"owner": "Shinder Kaur", "khewat": "102", "share": "98/1347"},
            {"owner": "Sukhpal Singh", "khewat": "102", "share": "283/1347"},
            {"owner": "Veerpal Kaur", "khewat": "102", "share": "119/6682"},
            # Khewat 215 ownership — shares total 1.00 in the supplied spreadsheet.
            {"owner": "Ram Singh", "khewat": "215", "share": "35/297"},
            {"owner": "Baldev kaur", "khewat": "215", "share": "122/297"},
            {"owner": "Simerjit Kaur", "khewat": "215", "share": "23/297"},
            {"owner": "Ajaib Singh", "khewat": "215", "share": "4/99"},
            {"owner": "Sat sukh jass baljeet", "khewat": "215", "share": "35/99"},
            # Khewat 216 ownership — shares total 1.00 in the supplied spreadsheet.
            {"owner": "ram Singh", "khewat": "216", "share": "8/735"},
            {"owner": "Mithu", "khewat": "216", "share": "8/2205"},
            {"owner": "Shinder Kaur", "khewat": "216", "share": "1/6"},
            {"owner": "Malkit Singh", "khewat": "216", "share": "1/6"},
            {"owner": "Jagseer singh", "khewat": "216", "share": "32/441"},
            {"owner": "jass baljeet", "khewat": "216", "share": "1/6"},
            {"owner": "sat sukh", "khewat": "216", "share": "1469/4410"},
            {"owner": "jaskaran", "khewat": "216", "share": "32/441"},
            {"owner": "Ajaib Singh", "khewat": "216", "share": "16/2205"},
        ]
        self.refresh_tables()
        self.statusBar().showMessage("Sample structure loaded from Khatrawan_Area_claculator.ods.")

    def khewat_total(self, number):
        return sum(
            area_marla(p["kanal"], p["marla"])
            for p in self.parcels if str(p["khewat"]) == str(number)
        )

    def refresh_tables(self):
        self._loading = True
        # Khewats
        self.khewat_table.setRowCount(len(self.khewats))
        for r, k in enumerate(self.khewats):
            n = k["number"]
            total = self.khewat_total(n)
            vals = [
                n, k.get("note", ""),
                str(sum(1 for p in self.parcels if p["khewat"] == n)),
                fmt(total / 20), fmt(total), area_text(total)
            ]
            for c, v in enumerate(vals):
                self.khewat_table.setItem(r, c, QTableWidgetItem(v))

        # Parcels
        self.parcel_table.setRowCount(len(self.parcels))
        for r, p in enumerate(self.parcels):
            total = area_marla(p["kanal"], p["marla"])
            vals = [p["khewat"], p["murabba"], p["square"], str(p["kanal"]),
                    fmt(p["marla"]), fmt(total), p.get("kh_no", "")]
            for c, v in enumerate(vals):
                self.parcel_table.setItem(r, c, QTableWidgetItem(v))

        # Owners
        self.owner_table.setRowCount(len(self.owners))
        for r, o in enumerate(self.owners):
            try:
                dec = parse_share(o["share"])
            except Exception:
                dec = 0
            ka = self.khewat_total(o["khewat"])
            vals = [o["owner"], o["khewat"], o["share"], fmt(dec, 9),
                    fmt(ka), fmt(ka * dec)]
            for c, v in enumerate(vals):
                self.owner_table.setItem(r, c, QTableWidgetItem(v))

        self._loading = False
        self.recalculate()

    def recalculate(self):
        nums = [k["number"] for k in self.khewats]
        owner_names = []
        for o in self.owners:
            if o["owner"] not in owner_names:
                owner_names.append(o["owner"])

        alloc = {owner: {n: 0.0 for n in nums} for owner in owner_names}
        share_totals = {n: 0.0 for n in nums}

        for o in self.owners:
            try:
                s = parse_share(o["share"])
            except Exception:
                continue
            if o["khewat"] in nums:
                a = self.khewat_total(o["khewat"])
                alloc[o["owner"]][o["khewat"]] += a * s
                share_totals[o["khewat"]] += s

        headers = ["Owner"]
        for n in nums:
            headers.append(f"Khewat {n}\n(K/M)")
        headers += ["Total Marla", "Total K/M", "Status"]
        self.result_table.setColumnCount(len(headers))
        self.result_table.setHorizontalHeaderLabels(headers)
        self.result_table.setRowCount(len(owner_names) + 1)

        grand = 0.0
        for r, owner in enumerate(owner_names):
            self.result_table.setItem(r, 0, QTableWidgetItem(owner))
            total = 0.0
            for c, n in enumerate(nums, 1):
                v = alloc[owner][n]
                total += v
                self.result_table.setItem(r, c, QTableWidgetItem(fmt(v)))
            self.result_table.setItem(r, len(nums) + 1, QTableWidgetItem(fmt(total)))
            self.result_table.setItem(r, len(nums) + 2, QTableWidgetItem(area_text(total)))
            self.result_table.setItem(r, len(nums) + 3, QTableWidgetItem("Calculated"))

        total_row = len(owner_names)
        self.result_table.setItem(total_row, 0, QTableWidgetItem("TOTAL"))
        allocated = 0.0
        for c, n in enumerate(nums, 1):
            v = sum(alloc[o][n] for o in owner_names)
            allocated += v
            self.result_table.setItem(total_row, c, QTableWidgetItem(fmt(v)))
        self.result_table.setItem(total_row, len(nums) + 1, QTableWidgetItem(fmt(allocated)))
        self.result_table.setItem(total_row, len(nums) + 2, QTableWidgetItem(area_text(allocated)))

        total_area = sum(self.khewat_total(n) for n in nums)
        difference = total_area - allocated

        for n in nums:
            status = "Complete" if abs(share_totals[n] - 1.0) < 1e-8 else (
                "OVER 100%" if share_totals[n] > 1 else f"INCOMPLETE ({fmt(share_totals[n] * 100, 3)}%)"
            )
            # Put status in the status column on total row as a compact overall message.
            if status != "Complete":
                self.statusBar().showMessage(f"Khewat {n}: {status}")

        self.result_table.setItem(total_row, len(nums) + 3,
                                  QTableWidgetItem("Check ownership shares"))

        self.card_total.setText(f"Total Khewat Area\n{fmt(total_area)} Marla\n{area_text(total_area)}")
        self.card_parcels.setText(f"Area Parcels\n{len(self.parcels)} parcels\n{len(nums)} Khewats")
        self.card_allocated.setText(f"Owner Allocated\n{fmt(allocated)} Marla\n{area_text(allocated)}")
        self.card_difference.setText(f"Difference / Unallocated\n{fmt(difference)} Marla")

        if all(abs(share_totals[n] - 1.0) < 1e-8 for n in nums) if nums else True:
            self.statusBar().showMessage(
                f"{len(nums)} Khewats • {len(self.parcels)} parcels • {len(owner_names)} owners • ownership totals balanced"
            )
        self.khewat_table.resizeRowsToContents()
        self.parcel_table.resizeRowsToContents()
        self.owner_table.resizeRowsToContents()
        self.result_table.resizeRowsToContents()

    def add_khewat(self):
        d = KhewatDialog(self)
        if d.exec() != QDialog.Accepted:
            return
        number, note = d.values()
        if not number:
            QMessageBox.warning(self, "Required", "Enter a Khewat number.")
            return
        if any(k["number"] == number for k in self.khewats):
            QMessageBox.warning(self, "Duplicate", "That Khewat already exists.")
            return
        self.khewats.append({"number": number, "note": note})
        self.refresh_tables()
        self.tabs.setCurrentIndex(0)

    def add_parcel(self):
        if not self.khewats:
            QMessageBox.information(self, "Add Khewat First", "Create a Khewat before adding parcels.")
            return
        selected = self.khewat_table.currentRow()
        default = self.khewats[selected]["number"] if selected >= 0 else self.khewats[0]["number"]
        # Small custom choice dialog using the parcel dialog's fixed Khewat label.
        d = ParcelDialog(default, self)
        if d.exec() == QDialog.Accepted:
            p = d.values()
            p["khewat"] = default
            self.parcels.append(p)
            self.refresh_tables()
            self.tabs.setCurrentIndex(1)

    def edit_parcel(self):
        r = self.parcel_table.currentRow()
        if r < 0:
            QMessageBox.information(self, "Select Parcel", "Select a parcel first.")
            return
        old = self.parcels[r]
        d = ParcelDialog(old["khewat"], self, old)
        if d.exec() == QDialog.Accepted:
            p = d.values()
            p["khewat"] = old["khewat"]
            self.parcels[r] = p
            self.refresh_tables()

    def delete_parcel(self):
        r = self.parcel_table.currentRow()
        if r < 0:
            return
        if QMessageBox.question(self, "Delete Parcel", "Delete the selected parcel?") == QMessageBox.Yes:
            del self.parcels[r]
            self.refresh_tables()

    def add_owner(self):
        if not self.khewats:
            QMessageBox.information(self, "Add Khewat First", "Create a Khewat first.")
            return
        d = OwnerDialog([k["number"] for k in self.khewats], self)
        if d.exec() != QDialog.Accepted:
            return
        o = d.values()
        if not o["owner"]:
            QMessageBox.warning(self, "Required", "Enter an owner name.")
            return
        try:
            s = parse_share(o["share"])
            if s < 0:
                raise ValueError("Share cannot be negative.")
        except Exception as e:
            QMessageBox.warning(self, "Invalid Share", str(e))
            return
        self.owners.append(o)
        self.refresh_tables()
        self.tabs.setCurrentIndex(2)

    def edit_owner(self):
        r = self.owner_table.currentRow()
        if r < 0:
            return
        d = OwnerDialog([k["number"] for k in self.khewats], self, self.owners[r])
        if d.exec() == QDialog.Accepted:
            o = d.values()
            try:
                parse_share(o["share"])
            except Exception as e:
                QMessageBox.warning(self, "Invalid Share", str(e))
                return
            self.owners[r] = o
            self.refresh_tables()

    def delete_owner(self):
        r = self.owner_table.currentRow()
        if r < 0:
            return
        if QMessageBox.question(self, "Delete Owner", "Delete the selected ownership entry?") == QMessageBox.Yes:
            del self.owners[r]
            self.refresh_tables()

    def new_project(self):
        if QMessageBox.question(self, "New Project", "Clear the current project?") == QMessageBox.Yes:
            self.khewats, self.parcels, self.owners = [], [], []
            self.refresh_tables()

    def save_project(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Project", "", "Khatrawan Project (*.json)")
        if not path:
            return
        data = {"khewats": self.khewats, "parcels": self.parcels, "owners": self.owners}
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self.statusBar().showMessage(f"Saved: {path}")

    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "Khatrawan Project (*.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self.khewats = data.get("khewats", [])
            self.parcels = data.get("parcels", [])
            self.owners = data.get("owners", [])
            self.refresh_tables()
            self.statusBar().showMessage(f"Opened: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Open Failed", str(e))

    def export_xlsx(self):
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        except ImportError:
            QMessageBox.warning(self, "Missing Package", "Install Excel support with:\npip install openpyxl")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export XLSX", "Khatrawan_Area_Result.xlsx", "Excel Workbook (*.xlsx)"
        )
        if not path:
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "Final Result"

        nums = [k["number"] for k in self.khewats]
        owners = []
        for o in self.owners:
            if o["owner"] not in owners:
                owners.append(o["owner"])

        ws.append(["Khewat"] + nums)
        ws.append(["Area (Marla)"] + [self.khewat_total(n) for n in nums])
        ws.append(["Owner"] + nums + ["Total Marla", "Total K/M", "Status"])

        alloc = {o: {n: 0.0 for n in nums} for o in owners}
        for o in self.owners:
            try:
                alloc[o["owner"]][o["khewat"]] += self.khewat_total(o["khewat"]) * parse_share(o["share"])
            except Exception:
                pass

        for owner in owners:
            vals = [owner]
            total = 0.0
            for n in nums:
                v = alloc[owner][n]
                vals.append(v)
                total += v
            vals.extend([total, area_text(total), "Calculated"])
            ws.append(vals)

        total_row = ["TOTAL"]
        grand = 0
        for n in nums:
            v = sum(alloc[o][n] for o in owners)
            total_row.append(v)
            grand += v
        total_row.extend([grand, area_text(grand), "Check ownership shares"])
        ws.append(total_row)

        pi = wb.create_sheet("Khewat Parcels")
        pi.append(["Khewat", "Murabba", "Square", "Kanal (K)", "Marla (M)", "Total Marla", "Khasra / Kh. No."])
        for p in self.parcels:
            pi.append([
                p["khewat"], p["murabba"], p["square"], p["kanal"], p["marla"],
                area_marla(p["kanal"], p["marla"]), p.get("kh_no", "")
            ])

        oi = wb.create_sheet("Ownership Input")
        oi.append(["Owner", "Khewat", "Share", "Share Decimal"])
        for o in self.owners:
            oi.append([o["owner"], o["khewat"], o["share"], parse_share(o["share"])])

        ki = wb.create_sheet("Khewats")
        ki.append(["Khewat", "Description", "Parcel Count", "Total Marla", "Total K/M"])
        for k in self.khewats:
            n = k["number"]
            ki.append([n, k.get("note", ""), sum(1 for p in self.parcels if p["khewat"] == n),
                       self.khewat_total(n), area_text(self.khewat_total(n))])

        for sheet in wb.worksheets:
            for cell in sheet[1]:
                cell.font = Font(bold=True)
                cell.fill = PatternFill("solid", fgColor="DCE6F1")
                cell.alignment = Alignment(horizontal="center")
            for col in sheet.columns:
                letter = col[0].column_letter
                width = max(14, min(30, max(len(str(c.value or "")) for c in col) + 2))
                sheet.column_dimensions[letter].width = width
            for row in sheet.iter_rows():
                for cell in row:
                    cell.border = Border(bottom=Side(style="hair", color="D9DDE5"))

        wb.save(path)
        self.statusBar().showMessage(f"Exported: {path}")

    def show_about(self):
        QMessageBox.information(
            self, "Unit Rules",
            "Khatrawan — Khewat Parcel & Ownership Calculator\n\n"
            "Area conventions:\n"
            "• 1 Kanal = 20 Marla\n"
            "• 1 Killa = 8 Kanal = 160 Marla\n"
            "• 1 Marla = 9 Sarshai\n\n"
            "Every parcel belongs to one Khewat and contributes its Kanal + Marla area "
            "to that Khewat's total. Ownership shares are then applied to the Khewat total."
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Khatrawan — Khewat Parcel & Ownership Calculator")
    app.setFont(QFont("Segoe UI", 10))
    window = KhatrawanCalculator()
    window.show()
    sys.exit(app.exec())
