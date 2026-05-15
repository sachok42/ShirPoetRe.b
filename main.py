import sys
import os

# Настройка путей для импорта модулей из подпапок
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QToolBar
from PySide6.QtGui import QShortcut, QKeySequence, QAction

from src.window import TextIDE
import model


class ShirPoetApp(TextIDE):
    """Связующий класс: объединяет интерфейс и лингвистическую модель."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ShirPoetRe.b")
        self._init_ai_features()

    def _init_ai_features(self):
        """Инициализация инструментов ИИ."""
        # Создание действия для генерации
        self.ai_action = QAction("Дописать (AI)", self)
        self.ai_action.setToolTip("Предложить продолжение (Ctrl+G)")
        self.ai_action.triggered.connect(self._suggest_word)

        # Интеграция в существующий тулбар
        toolbar = self.findChild(QToolBar)
        if toolbar:
            toolbar.addSeparator()
            toolbar.addAction(self.ai_action)

        # Горячая клавиша Ctrl+G
        self.shortcut = QShortcut(QKeySequence("Ctrl+G"), self)
        self.shortcut.activated.connect(self._suggest_word)

        if self.statusBar():
            self.statusBar().showMessage("Система ShirPoetRe.b готова", 3000)

    def _suggest_word(self):
        """Логика получения и вставки подсказки."""
        context = self.editor.toPlainText()
        try:
            # Вызов модели из model/__init__.py
            suggestion = model.predict(context)
            if suggestion:
                # Вставка слова в текущую позицию курсора
                self.editor.insertPlainText(f" {suggestion}")
        except Exception as e:
            print(f"Ошибка модели: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = ShirPoetApp()
    window.show()

    sys.exit(app.exec())