import sys, os, json, uuid, shutil, datetime, random
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from PySide6.QtWidgets import (
    QApplication, QWidget, QListWidget, QTextEdit, QLineEdit, QPushButton,
    QListWidgetItem, QFileDialog, QMessageBox, QLabel, QHBoxLayout, QVBoxLayout,
    QSplitter, QToolBar, QInputDialog
)
from PySide6.QtGui import QPainter, QColor, QFont, QTextCharFormat, QAction, QKeySequence
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon

APP_DIR = Path.home() / ".knowledge_garage"
NOTES_DIR = APP_DIR / "notes"
IMAGES_DIR = APP_DIR / "images"
INDEX_FILE = APP_DIR / "index.json"

for d in (APP_DIR, NOTES_DIR, IMAGES_DIR):
    d.mkdir(parents=True, exist_ok=True)

def now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"

def load_index():
    if INDEX_FILE.exists():
        return json.loads(INDEX_FILE.read_text())
    return []

def save_index(index):
    INDEX_FILE.write_text(json.dumps(index, indent=2))

def note_path(note_id):
    return NOTES_DIR / f"{note_id}.json"

class Note:
    def __init__(self, id=None, title="", body_html="", tags=None, images=None, created_at=None, updated_at=None):
        self.id = id or str(uuid.uuid4())
        self.title = title
        self.body_html = body_html
        self.tags = tags or []
        self.images = images or []
        self.created_at = created_at or now_iso()
        self.updated_at = updated_at or now_iso()

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "body_html": self.body_html,
            "tags": self.tags,
            "images": self.images,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    def save(self):
        self.updated_at = now_iso()
        note_path(self.id).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, note_id):
        p = note_path(note_id)
        if not p.exists(): return None
        data = json.loads(p.read_text())
        return cls(**data)

class CodeRainWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.raindrops = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_rain)
        self.timer.start(30)
        self.katakana = [chr(i) for i in range(0x30A0, 0x30FF + 1)] # Katakana characters

    def resizeEvent(self, event):
        super().resizeEvent(event)
        font_size = 16
        num_drops = self.width() // font_size
        self.raindrops = []
        for i in range(num_drops):
            self.raindrops.append({
                'x': i * font_size,
                'y': random.randint(0, self.height() * 2),
                'speed': random.randint(3, 7),
                'length': random.randint(10, 25),
                'chars': [random.choice(self.katakana) for _ in range(random.randint(10, 25))]
            })

    def update_rain(self):
        for drop in self.raindrops:
            drop['y'] += drop['speed']
            if drop['y'] - (drop['length'] * 16) > self.height():
                drop['y'] = random.randint(-200, 0)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 255))
        font = QFont('monospace', 16)
        painter.setFont(font)

        for drop in self.raindrops:
            for i, char in enumerate(drop['chars']):
                y_pos = drop['y'] - (i * 16)
                if 0 < y_pos < self.height():
                    alpha = 255 - (i * (255 // drop['length']))
                    if i == 0:
                        painter.setPen(QColor(129, 199, 132, alpha))
                    else:
                        painter.setPen(QColor(76, 175, 80, alpha))
                    painter.drawText(drop['x'], y_pos, char)

class MainWindow(QWidget):
    def _create_toolbar(self):
        toolbar = QToolBar()
        actions = [
            ("New", self.new_note, Qt.Key_F1),
            ("Save", self.save_note, Qt.Key_F2),
            ("Delete", self.delete_note, Qt.Key_F3),
            ("Bold", self.toggle_bold, Qt.Key_F4),
            ("Italic", self.toggle_italic, Qt.Key_F5),
            ("Insert Image", self.insert_image, Qt.Key_F6),
            ("Code Block", self.insert_code_block, Qt.Key_F7),
            ("Manage Tags", self.edit_tags_of_note, Qt.Key_F8)
        ]
        for name, slot, shortcut in actions:
            act = QAction(name, self)
            act.triggered.connect(slot)
            act.setShortcut(QKeySequence(shortcut))
            toolbar.addAction(act)

        toolbar.addSeparator()

        self.fullscreen_action = QAction("Fullscreen", self)
        self.fullscreen_action.setShortcut(QKeySequence(Qt.Key_F11))
        self.fullscreen_action.triggered.connect(self.toggle_fullscreen)
        toolbar.addAction(self.fullscreen_action)

        return toolbar

    def __init__(self):
        super().__init__()
        self.setWindowTitle("The Knowledge Garage")
        self.setWindowIcon(QIcon('icon.ico'))
        self.resize(1000, 650)
        
        self.rain_widget = CodeRainWidget(self)
        
        self.ui_container = QWidget(self)
        self.ui_container.setObjectName("ui_container")

        self.index = load_index()
        self.note_cache = {}
        self.current_note_id = None
        
        self.is_dirty = False

        self.load_all_notes()

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search notes...")
        self.search_bar.textChanged.connect(self.filter_notes)

        self.notes_list = QListWidget()
        self.notes_list.itemClicked.connect(self.on_note_selected)

        left_v = QVBoxLayout()
        left_v.addWidget(QLabel("Search"))
        left_v.addWidget(self.search_bar)
        left_v.addWidget(QLabel("Notes"))
        left_v.addWidget(self.notes_list)

        self.tags_list = QListWidget()
        self.tags_list.setSelectionMode(QListWidget.MultiSelection)
        self.tags_list.itemClicked.connect(self.on_tag_clicked)
        left_v.addWidget(QLabel("Tags"))
        left_v.addWidget(self.tags_list)

        self.selected_tags_filter = set()
        left_container = QWidget()
        left_container.setLayout(left_v)

        self.toolbar = self._create_toolbar()

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Note title")
        self.title_edit.textChanged.connect(self.mark_as_dirty)

        self.body = QTextEdit()
        self.body.setAcceptRichText(True)
        self.body.textChanged.connect(self.mark_as_dirty)


        right_v = QVBoxLayout()
        right_v.insertWidget(0, self.toolbar)
        right_v.addWidget(self.title_edit)
        right_v.addWidget(self.body)
        right_container = QWidget()
        right_container.setLayout(right_v)

        splitter = QSplitter()
        splitter.addWidget(left_container)
        splitter.addWidget(right_container)
        splitter.setStretchFactor(1, 4)

        ui_layout = QHBoxLayout(self.ui_container)
        ui_layout.addWidget(splitter)
        self.ui_container.setLayout(ui_layout)
        
        self.load_notes_index()

        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.setInterval(2000) # Auto-save every 2 seconds
        self.auto_save_timer.timeout.connect(self.auto_save_note)
        self.auto_save_timer.start()

    def _create_toolbar(self):
        toolbar = QToolBar()
        actions = [
            ("New", self.new_note, Qt.Key_F1),
            ("Save", self.save_note, Qt.Key_F2),
            ("Delete", self.delete_note, Qt.Key_F3),
            ("Bold", self.toggle_bold, Qt.Key_F4),
            ("Italic", self.toggle_italic, Qt.Key_F5),
            ("Insert Image", self.insert_image, Qt.Key_F6),
            ("Code Block", self.insert_code_block, Qt.Key_F7),
            ("Manage Tags", self.edit_tags_of_note, Qt.Key_F8)
        ]
        for name, slot, shortcut in actions:
            act = QAction(name, self)
            act.triggered.connect(slot)
            act.setShortcut(QKeySequence(shortcut))
            toolbar.addAction(act)

        toolbar.addSeparator()

        self.fullscreen_action = QAction("Fullscreen", self)
        self.fullscreen_action.setShortcut(QKeySequence(Qt.Key_F11))
        self.fullscreen_action.triggered.connect(self.toggle_fullscreen)
        toolbar.addAction(self.fullscreen_action)

        return toolbar
    def load_all_notes(self):
        self.note_cache = {m['id']: Note.load(m['id']) for m in self.index if (NOTES_DIR / f"{m['id']}.json").exists()}

    def resizeEvent(self, event):
        self.rain_widget.resize(event.size())
        self.ui_container.resize(event.size())
        super().resizeEvent(event)

    def load_notes_index(self):
        self.index.sort(key=lambda m: m.get("updated_at", ""), reverse=True)
        self.refresh_notes_list()
        self.refresh_tags()

    def refresh_tags(self):
        self.tags_list.clear()
        all_tags = sorted(list(set(t for m in self.index for t in m.get("tags", []))))
        for tag in all_tags:
            item = QListWidgetItem(tag)
            item.setData(Qt.UserRole, tag)
            self.tags_list.addItem(item)

    def refresh_notes_list(self, filtered=None):
        self.notes_list.clear()
        notes_to_show = filtered if filtered is not None else self.index
        for meta in notes_to_show:
            item = QListWidgetItem(meta.get("title", "Untitled"))
            item.setData(Qt.UserRole, meta['id'])
            self.notes_list.addItem(item)

    def new_note(self):
        note = Note(title="New Note")
        note.save()
        self.note_cache[note.id] = note
        self.index.append({"id": note.id, "title": note.title, "tags": note.tags, "updated_at": note.updated_at})
        save_index(self.index)
        self.current_note_id = note.id
        self.refresh_notes_list()
        self.refresh_tags()
        self.select_note_by_id(note.id)
        self.title_edit.setText(note.title)
        self.body.setHtml(note.body_html)
        self.is_dirty = False

    def auto_save_note(self):
        if self.is_dirty:
            self.save_note()

    def mark_as_dirty(self):
        self.is_dirty = True

    def open_note(self, note_id):
        # This function is now a simple placeholder
        # All logic has been moved to on_note_selected
        pass

    def select_note_by_id(self, note_id):
        for i in range(self.notes_list.count()):
            item = self.notes_list.item(i)
            if item.data(Qt.UserRole) == note_id:
                item.setSelected(True)
                self.notes_list.setCurrentItem(item)
                return

    def on_note_selected(self, item):
        if not item: return
        note_id = item.data(Qt.UserRole)
        note = self.note_cache.get(note_id)
        if not note: return

        self.current_note_id = note_id
        self.title_edit.setText(note.title)

        html = note.body_html
        soup = BeautifulSoup(html, 'html.parser')
        for img in soup.find_all('img'):
            if img.has_attr('src') and not img['src'].startswith('file://'):
                try:
                    img['src'] = (APP_DIR / img['src']).as_uri()
                except ValueError:
                    pass # ignore malformed paths
        self.body.setHtml(str(soup))
        self.is_dirty = False
        self.select_note_by_id(note_id)

    def save_note(self):
        if not self.current_note_id: return
        note = self.note_cache.get(self.current_note_id)
        if not note: return
        note.title = self.title_edit.text()
        html = self.body.toHtml()
        soup = BeautifulSoup(html, 'html.parser')
        for img in soup.find_all('img'):
            if img.has_attr('src') and img['src'].startswith('file://'):
                try:
                    p = Path(urlparse(img['src']).path[1:]) # strip leading '/'
                    img['src'] = p.relative_to(APP_DIR).as_posix()
                except (ValueError, AttributeError):
                    pass # ignore malformed urls
        note.body_html = str(soup.body)
        note.save()
        self.is_dirty = False

        for m in self.index:
            if m['id'] == note.id:
                m['title'] = note.title
                m['tags'] = note.tags
                m['updated_at'] = note.updated_at
                break
        save_index(self.index)
        self.refresh_notes_list()
        self.select_note_by_id(note.id)

    def delete_note(self):
        if not self.current_note_id: return
        del self.note_cache[self.current_note_id]
        note_path(self.current_note_id).unlink()
        self.index = [m for m in self.index if m['id'] != self.current_note_id]
        save_index(self.index)
        self.current_note_id = None
        self.title_edit.clear()
        self.body.clear()
        self.refresh_notes_list()
        self.refresh_tags()

    def toggle_bold(self):
        fmt = QTextCharFormat()
        cur = self.body.textCursor()
        fmt.setFontWeight(QFont.Bold if cur.charFormat().fontWeight() != QFont.Bold else QFont.Normal)
        cur.mergeCharFormat(fmt)

    def toggle_italic(self):
        fmt = QTextCharFormat()
        cur = self.body.textCursor()
        fmt.setFontItalic(not cur.charFormat().fontItalic())
        cur.mergeCharFormat(fmt)

    def toggle_fullscreen(self):
        # Use XOR to toggle the fullscreen flag. This is the most reliable method.
        self.setWindowState(self.windowState() ^ Qt.WindowFullScreen)
        # Update the button text based on the new state.
        if self.isFullScreen():
            self.fullscreen_action.setText("Exit Fullscreen")
        else:
            self.fullscreen_action.setText("Fullscreen")

    def insert_code_block(self):
        cur = self.body.textCursor()
        html = "<pre style='background-color:#222; color:#4CAF50; padding:10px; border-radius:5px;'># type code here\n</pre><p></p>"
        cur.insertHtml(html)

    def insert_image(self):
        if not self.current_note_id: return
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.gif)")
        if not file_path: return
        new_name = f"{uuid.uuid4()}{Path(file_path).suffix}"
        dest = IMAGES_DIR / new_name
        shutil.copy(file_path, dest)
        rel = dest.relative_to(APP_DIR).as_posix()
        image_url = dest.as_uri()
        cur = self.body.textCursor()
        cur.insertHtml(f"<img src='{image_url}' width='400'/><p></p>")
        note = self.note_cache.get(self.current_note_id)
        if note:
            note.images.append(rel)
            self.mark_as_dirty()
            self.auto_save_note()

    def edit_tags_of_note(self):
        print("DEBUG: edit_tags_of_note called")
        if not self.current_note_id: return
        note = self.note_cache.get(self.current_note_id)
        if not note: return
        text, ok = QInputDialog.getText(self, "Edit tags", "Enter tags separated by commas:", text=",".join(note.tags))
        if not ok: return
        tags = [t.strip() for t in text.split(",") if t.strip()]
        note.tags = tags
        note.save()
        for m in self.index:
            if m['id'] == note.id:
                m['tags'] = tags
        save_index(self.index)
        self.refresh_tags()

    def filter_notes(self):
        q = self.search_bar.text().lower().strip()
        filtered_index = []
        for meta in self.index:
            note = self.note_cache.get(meta['id'])
            if not note:
                continue

            include = False
            # Search logic
            if q == "" or \
               q in meta.get("title", "").lower() or \
               any(q in t.lower() for t in meta.get("tags", [])) or \
               q in note.body_html.lower():
                include = True

            # Tag filter logic
            if self.selected_tags_filter and not self.selected_tags_filter.issubset(set(meta.get("tags", []))):
                include = False

            if include:
                filtered_index.append(meta)
        self.refresh_notes_list(filtered_index)

    def on_tag_clicked(self, item):
        tag = item.data(Qt.UserRole)
        if tag in self.selected_tags_filter:
            self.selected_tags_filter.remove(tag)
            item.setSelected(False)
        else:
            self.selected_tags_filter.add(tag)
            item.setSelected(True)
        self.filter_notes()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F11:
            self.toggle_fullscreen()
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    style_file = Path(__file__).parent / "stylesheet.qss"
    if style_file.exists():
        with open(style_file, "r") as f:
            app.setStyleSheet(f.read())
    w = MainWindow()
    w.show()
    sys.exit(app.exec())