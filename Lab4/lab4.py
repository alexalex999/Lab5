import sys
import sqlite3
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem,
    QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QMessageBox, QDialog, QLabel, QLineEdit, QFileDialog
)
from PyQt5.QtCore import Qt


class TariffManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tariff Management System")
        self.setGeometry(200, 200, 600, 400)

        try:
            self.conn = sqlite3.connect("tariffs.db")
            self.current_table = "tariffs"
            self.create_table(self.current_table)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to connect to the database: {e}")
            sys.exit(1)

        self.initUI()

    def create_table(self, table_name):
        """Создает таблицу с указанным именем, если она не существует."""
        cursor = self.conn.cursor()
        cursor.execute(f''' 
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                direction TEXT,
                price REAL,
                discount REAL,
                final_price REAL
            )
        ''')
        self.conn.commit()

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Direction", "Price", "Discount", "Final Price"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        button_layout = QHBoxLayout()

        add_button = QPushButton("Add Tariff")
        add_button.clicked.connect(self.add_tariff)
        button_layout.addWidget(add_button)

        remove_button = QPushButton("Remove Tariff")
        remove_button.clicked.connect(self.remove_tariff)
        button_layout.addWidget(remove_button)

        sort_button = QPushButton("Sort Tariffs")
        sort_button.clicked.connect(self.sort_tariffs)
        button_layout.addWidget(sort_button)

        save_button = QPushButton("Save to File")
        save_button.clicked.connect(self.save_to_file)
        button_layout.addWidget(save_button)

        load_button = QPushButton("Load from File")
        load_button.clicked.connect(self.load_from_file)
        button_layout.addWidget(load_button)

        layout.addLayout(button_layout)

    def add_tariff(self):
        dialog = AddTariffDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if data:
                direction, price, discount = data
                final_price = price - (price * discount / 100)

                table_name = f"table_{direction.lower()}"
                if table_name != self.current_table:
                    self.current_table = table_name
                    self.create_table(self.current_table)

                try:
                    cursor = self.conn.cursor()
                    cursor.execute(f'''
                        INSERT INTO {self.current_table} (direction, price, discount, final_price)
                        VALUES (?, ?, ?, ?)
                    ''', (direction, price, discount, final_price))
                    self.conn.commit()
                    self.update_table()
                except sqlite3.Error as e:
                    QMessageBox.critical(self, "Error", f"Failed to add tariff: {e}")

    def remove_tariff(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            for index in sorted(selected_rows, key=lambda x: x.row(), reverse=True):
                direction = self.table.item(index.row(), 0).text()  # Get direction to find ID
                try:
                    cursor = self.conn.cursor()
                    cursor.execute(f'DELETE FROM {self.current_table} WHERE direction = ?', (direction,))
                    self.conn.commit()
                    self.update_table()
                except sqlite3.Error as e:
                    QMessageBox.critical(self, "Error", f"Failed to remove tariff: {e}")
        else:
            QMessageBox.warning(self, "Warning", "Please select a row to remove.")

    def sort_tariffs(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute(f'SELECT * FROM {self.current_table} ORDER BY final_price')
            tariffs = cursor.fetchall()
            self.update_table(tariffs)
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Error", f"Failed to sort tariffs: {e}")

    def save_to_file(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Tariffs", "", "JSON Files (*.json);;All Files (*)")
        if file_name:
            try:
                cursor = self.conn.cursor()
                cursor.execute(f'SELECT direction, price, discount, final_price FROM {self.current_table}')
                tariffs = cursor.fetchall()

                tariffs_data = [
                    {"direction": tariff[0], "price": tariff[1], "discount": tariff[2], "final_price": tariff[3]}
                    for tariff in tariffs
                ]

                with open(file_name, "w") as file:
                    json.dump(tariffs_data, file, indent=4)

                QMessageBox.information(self, "Success", "Tariffs saved to JSON file.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {e}")

    def load_from_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Tariffs", "", "JSON Files (*.json);;All Files (*)")
        if file_name:
            try:
                with open(file_name, "r") as file:
                    tariffs_data = json.load(file)
                    cursor = self.conn.cursor()
                    cursor.execute(f'DELETE FROM {self.current_table}')
                    for tariff in tariffs_data:
                        cursor.execute(f'''
                            INSERT INTO {self.current_table} (direction, price, discount, final_price)
                            VALUES (?, ?, ?, ?)
                        ''', (tariff["direction"], tariff["price"], tariff["discount"], tariff["final_price"]))
                    self.conn.commit()
                    self.update_table()
                    QMessageBox.information(self, "Success", "Tariffs loaded from JSON file.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file: {e}")

    def update_table(self, tariffs=None):
        if tariffs is None:
            try:
                cursor = self.conn.cursor()
                cursor.execute(f'SELECT * FROM {self.current_table}')
                tariffs = cursor.fetchall()
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Error", f"Failed to fetch tariffs: {e}")
                return

        self.table.setRowCount(len(tariffs))
        for row, tariff in enumerate(tariffs):
            self.table.setItem(row, 0, QTableWidgetItem(tariff[1]))  # direction
            self.table.setItem(row, 1, QTableWidgetItem(f"{tariff[2]:.2f}"))  # price
            self.table.setItem(row, 2, QTableWidgetItem(f"{tariff[3]:.2f}"))  # discount
            self.table.setItem(row, 3, QTableWidgetItem(f"{tariff[4]:.2f}"))  # final_price


class AddTariffDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Tariff")
        self.setGeometry(300, 300, 300, 200)

        layout = QVBoxLayout(self)

        self.direction_input = QLineEdit()
        self.direction_input.setPlaceholderText("Enter direction (letters only)")
        layout.addWidget(QLabel("Direction:"))
        layout.addWidget(self.direction_input)

        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("Enter price (0-100000)")
        layout.addWidget(QLabel("Price:"))
        layout.addWidget(self.price_input)

        self.discount_input = QLineEdit()
        self.discount_input.setPlaceholderText("Enter discount (0-100)")
        layout.addWidget(QLabel("Discount (%):"))
        layout.addWidget(self.discount_input)

        button_layout = QHBoxLayout()
        add_button = QPushButton("Add")
        add_button.clicked.connect(self.accept)
        button_layout.addWidget(add_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def accept(self):
        try:
            direction = self.direction_input.text().strip()
            if not direction.isalpha():
                raise ValueError("Direction must contain only letters.")

            price = float(self.price_input.text().strip())
            if price < 0 or price > 100000:
                raise ValueError("Price must be between 0 and 100000.")

            discount = float(self.discount_input.text().strip())
            if discount < 0 or discount > 100:
                raise ValueError("Discount must be between 0 and 100.")

            self._data = (direction, price, discount)
            super().accept()
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", str(e))

    def get_data(self):
        return getattr(self, "_data", None)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TariffManagerApp()
    window.show()
    sys.exit(app.exec_())
