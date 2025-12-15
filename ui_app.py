"""
UI de supervision PySide6 pour le pipeline de traitement.
Lance un tableau des images à traiter et permet de lancer le
traitement sur les images sélectionnées via ImageProcessor.
"""

import sys
from functools import partial
from typing import List

from PySide6 import QtCore, QtWidgets

from main import ImageProcessor
from repositories.ai_separation_setting_repository import (
    AiSeparationSettingRepository,
)
from repositories.image_repository import ImageRepositorie


class ProcessWorker(QtCore.QThread):
    """Thread de traitement pour ne pas bloquer l'UI."""

    done = QtCore.Signal(dict)
    errored = QtCore.Signal(str)

    def __init__(self, processor: ImageProcessor, images: List[dict]):
        super().__init__()
        self.processor = processor
        self.images = images

    def run(self):
        for img in self.images:
            try:
                img.setdefault("is_child", False)
                res = self.processor.process(img)
                self.done.emit(
                    {
                        "id": res.image_id,
                        "status_new": res.status_new,
                        "success": res.success,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                self.errored.emit(f"{img.get('name')}: {exc}")


class JobTable(QtWidgets.QTableWidget):
    HEADERS = [
        "ID",
        "Nom",
        "Statut",
        "Catégorie",
        "Lot",
        "Découper",
    ]

    def __init__(self, parent=None):
        super().__init__(0, len(self.HEADERS), parent)
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

    def load_rows(self, rows: List[dict]):
        self.setRowCount(0)
        for row_data in rows:
            row = self.rowCount()
            self.insertRow(row)
            values = [
                row_data.get("id", ""),
                row_data.get("name", ""),
                row_data.get("status_new", ""),
                row_data.get("categorie_id", ""),
                row_data.get("lot_id", ""),
                row_data.get("decouper", 0),
            ]
            for col, val in enumerate(values):
                item = QtWidgets.QTableWidgetItem(str(val))
                self.setItem(row, col, item)

    def selected_rows_data(self, all_rows: List[dict]) -> List[dict]:
        idxs = {idx.row() for idx in self.selectionModel().selectedRows()}
        return [all_rows[i] for i in idxs if i < len(all_rows)]


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Supervision Traitement Images")
        self.resize(1200, 700)

        self.image_repo = ImageRepositorie()
        self.settings_repo = AiSeparationSettingRepository()
        ai_settings = self.settings_repo.get_ai_separation_setting() or {}
        self.processor = ImageProcessor(ai_settings)
        self.power = ai_settings.get("power", 1)

        self.current_rows: List[dict] = []
        self.worker: ProcessWorker | None = None

        self.table = JobTable()
        self.detail = QtWidgets.QTextEdit()
        self.detail.setReadOnly(True)

        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.table)
        splitter.addWidget(self.detail)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        self.setCentralWidget(splitter)
        self._init_toolbar()

        self.table.itemSelectionChanged.connect(self._on_selection)
        self.refresh()

    def _init_toolbar(self):
        toolbar = QtWidgets.QToolBar()
        refresh_action = QtWidgets.QAction("Rafraîchir", self)
        refresh_action.triggered.connect(self.refresh)
        process_action = QtWidgets.QAction("Traiter sélection", self)
        process_action.triggered.connect(self.process_selected)
        self.power_action = QtWidgets.QAction(self._power_label(), self)
        self.power_action.triggered.connect(self.toggle_power)

        toolbar.addAction(refresh_action)
        toolbar.addAction(process_action)
        toolbar.addSeparator()
        toolbar.addAction(self.power_action)
        self.addToolBar(toolbar)

    def refresh(self):
        # rafraîchit l'état power
        settings = self.settings_repo.get_ai_separation_setting() or {}
        self.power = settings.get("power", self.power)
        self.power_action.setText(self._power_label())

        rows = self.image_repo.get_image_to_process()
        self.current_rows = rows
        self.table.load_rows(rows)
        self.detail.setPlainText(f"{len(rows)} images chargées.")

    def _on_selection(self):
        rows = self.table.selected_rows_data(self.current_rows)
        if not rows:
            self.detail.setPlainText("Aucune sélection.")
            return
        parts = []
        for r in rows:
            parts.append(
                f"ID: {r.get('id')} | Nom: {r.get('name')} | Lot: {r.get('lot_id')}\n"
                f"Status: {r.get('status_new')} | Catégorie: {r.get('categorie_id')}\n"
                f"Decouper: {r.get('decouper')} | Exercice: {r.get('exercice')}"
            )
        self.detail.setPlainText("\n\n".join(parts))

    def process_selected(self):
        if self.worker and self.worker.isRunning():
            return
        rows = self.table.selected_rows_data(self.current_rows)
        if not rows:
            QtWidgets.QMessageBox.information(self, "Info", "Sélectionnez au moins une ligne.")
            return
        if not self.power:
            QtWidgets.QMessageBox.warning(self, "Service OFF", "Le service est désactivé.")
            return
        self.worker = ProcessWorker(self.processor, rows)
        self.worker.done.connect(partial(self._on_done, rows=rows))
        self.worker.errored.connect(self._on_error)
        self.worker.finished.connect(self.refresh)
        self.worker.start()
        self.detail.append("Traitement en cours...")

    def _on_done(self, result: dict, rows: List[dict]):
        self.detail.append(f"OK image {result.get('id')} status={result.get('status_new')}")

    def _on_error(self, message: str):
        self.detail.append(f"Erreur: {message}")

    def toggle_power(self):
        new_power = 0 if self.power else 1
        ok = self.settings_repo.set_power(new_power)
        if ok:
            self.power = new_power
            self.power_action.setText(self._power_label())
            self.detail.append(f"Service {'activé' if new_power else 'désactivé'}.")
        else:
            QtWidgets.QMessageBox.critical(self, "Erreur", "Impossible de changer l'état du service.")

    def _power_label(self) -> str:
        return "Service: ON" if self.power else "Service: OFF"


def main():
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

