"""Windows desktop player for Delta Force's in-game harmonica.

This module deliberately uses only documented Win32 SendInput/RegisterHotKey APIs.
It does not inspect, inject into, or modify the game process.
"""

from __future__ import annotations

import ctypes
import json
import os
import queue
import re
import threading
import time
import tkinter as tk
from ctypes import wintypes
from dataclasses import dataclass, replace
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


DEGREE_SEMITONES = (0, 2, 4, 5, 7, 9, 11)
KEY_VKS = (0x5A, 0x58, 0x43, 0x56, 0x42, 0x4E, 0x4D, 0xBC)  # Z X C V B N M ,
TOKEN_RE = re.compile(r"\|:|:\||\||0(?:/\d+|\*\d+(?:\.\d+)?)?|[-_]|#?[1-7](?:[,']*)?(?:/\d+|\*\d+(?:\.\d+)?)?~?")
NOTE_RE = re.compile(r"^(#?)([1-7])([,']*)(?:/(\d+)|\*(\d+(?:\.\d+)?))?(~?)$")
REST_RE = re.compile(r"^0(?:/(\d+)|\*(\d+(?:\.\d+)?))?$")

BUILTIN_SONGS = [
    {"id": "scale", "title": "音阶练习", "artist": "练习", "bpm": 88,
     "score": "1 2 3 4 | 5 6 7 1' | 1' 7 6 5 | 4 3 2 1"},
    {"id": "twinkle", "title": "小星星", "artist": "传统童谣", "bpm": 96,
     "score": "1 1 5 5 | 6 6 5 - | 4 4 3 3 | 2 2 1 - | 5 5 4 4 | 3 3 2 - | 5 5 4 4 | 3 3 2 - | 1 1 5 5 | 6 6 5 - | 4 4 3 3 | 2 2 1 -"},
    {"id": "ode-to-joy", "title": "欢乐颂（主题）", "artist": "贝多芬", "bpm": 108,
     "score": "3 3 4 5 | 5 4 3 2 | 1 1 2 3 | 3*1.5 2/2 2 - | 3 3 4 5 | 5 4 3 2 | 1 1 2 3 | 2*1.5 1/2 1 -"},
]


@dataclass
class Note:
    token: str
    degree: int
    accidental: bool
    octave: int
    beat: float
    duration: float
    legato: bool = False


def parse_score(source: str) -> tuple[list[Note], float]:
    clean = " ".join(re.sub(r"//.*$", "", line) for line in source.splitlines())
    events: list[Note] = []
    beat = 0.0
    last_note: Note | None = None
    for token in TOKEN_RE.findall(clean):
        if token in {"|", "|:", ":|"}:
            continue
        if token in {"-", "_"}:
            if last_note:
                last_note.duration += 1
            beat += 1
            continue
        rest_match = REST_RE.match(token)
        if rest_match:
            last_note = None
            divisor, multiplier = rest_match.groups()
            beat += 1 / int(divisor) if divisor else float(multiplier or 1)
            continue
        match = NOTE_RE.match(token)
        if not match:
            continue
        accidental, degree_text, marks, divisor, multiplier, legato = match.groups()
        duration = 1 / int(divisor) if divisor else float(multiplier or 1)
        octave = marks.count("'") - marks.count(",")
        last_note = Note(token.rstrip("~"), int(degree_text), bool(accidental), octave, beat, duration, bool(legato))
        events.append(last_note)
        beat += duration
    return events, beat


def note_actions(note: Note) -> tuple[list[str], int]:
    modifiers = []
    if note.octave < 0:
        modifiers.append("left")
    elif note.octave > 0 and not (note.octave == 1 and note.degree == 1):
        modifiers.append("right")
    if note.accidental:
        modifiers.append("middle")
    key_index = 7 if note.degree == 1 and note.octave > 0 else note.degree - 1
    return modifiers, KEY_VKS[key_index]


def compact_long_rests(notes: list[Note], max_silence: float = 2.0) -> list[Note]:
    """Keep musical breaths but remove long accompaniment-only gaps."""
    if not notes:
        return []
    result = [replace(notes[0])]
    removed = 0.0
    previous_end = notes[0].beat + notes[0].duration
    for note in notes[1:]:
        gap = note.beat - previous_end
        if gap > max_silence:
            removed += gap - max_silence
        result.append(replace(note, beat=note.beat - removed))
        previous_end = note.beat + note.duration
    return result


if os.name == "nt":
    ULONG_PTR = wintypes.WPARAM

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", ULONG_PTR)]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                    ("wParamH", wintypes.WORD)]

    class INPUT_UNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("data",)
        _fields_ = [("type", wintypes.DWORD), ("data", INPUT_UNION)]


class WindowsInput:
    MOUSE_FLAGS = {
        "left": (0x0002, 0x0004),
        "right": (0x0008, 0x0010),
        "middle": (0x0020, 0x0040),
    }

    def __init__(self) -> None:
        if os.name != "nt":
            raise OSError("自动输入仅支持 Windows")
        self.user32 = ctypes.windll.user32
        self.held: set[str] = set()

    def _send(self, item: INPUT) -> None:
        if self.user32.SendInput(1, ctypes.byref(item), ctypes.sizeof(INPUT)) != 1:
            raise ctypes.WinError()

    def mouse(self, button: str, down: bool) -> None:
        flag = self.MOUSE_FLAGS[button][0 if down else 1]
        self._send(INPUT(type=0, mi=MOUSEINPUT(dwFlags=flag)))
        if down:
            self.held.add(button)
        else:
            self.held.discard(button)

    def key(self, vk: int, down: bool) -> None:
        self._send(INPUT(type=1, ki=KEYBDINPUT(wVk=vk, dwFlags=0 if down else 0x0002)))

    def release_all(self) -> None:
        for button in tuple(self.held):
            self.mouse(button, False)
        for vk in KEY_VKS:
            self.key(vk, False)


class Player:
    def __init__(self, backend: WindowsInput, update) -> None:
        self.backend = backend
        self.update = update
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return bool(self.thread and self.thread.is_alive())

    def start(self, notes: list[Note], bpm: int, countdown: int = 3) -> None:
        self.stop()
        self.stop_event.clear()
        self.pause_event.clear()
        self.thread = threading.Thread(target=self._run, args=(notes, bpm, countdown), daemon=True)
        self.thread.start()

    def toggle_pause(self) -> None:
        if not self.running:
            return
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.update("继续演奏")
        else:
            self.pause_event.set()
            self.backend.release_all()
            self.update("已暂停；按 F7 继续")

    def stop(self) -> None:
        self.stop_event.set()
        self.pause_event.clear()
        self.backend.release_all()

    def _wait(self, seconds: float) -> bool:
        deadline = time.perf_counter() + seconds
        while time.perf_counter() < deadline:
            if self.stop_event.is_set():
                return False
            while self.pause_event.is_set() and not self.stop_event.is_set():
                time.sleep(0.03)
                deadline += 0.03
            time.sleep(min(0.01, max(0, deadline - time.perf_counter())))
        return not self.stop_event.is_set()

    def _run(self, notes: list[Note], bpm: int, countdown: int) -> None:
        try:
            for remaining in range(countdown, 0, -1):
                self.update(f"{remaining} 秒后开始，请切回游戏并拿出口琴")
                if not self._wait(1):
                    return
            beat_seconds = 60 / bpm
            cursor = 0.0
            for index, note in enumerate(notes, 1):
                if not self._wait(max(0, note.beat - cursor) * beat_seconds):
                    return
                modifiers, vk = note_actions(note)
                for button in modifiers:
                    self.backend.mouse(button, True)
                modifier_lead = 0.018 if modifiers else 0.0
                if modifier_lead and not self._wait(modifier_lead):
                    return
                self.backend.key(vk, True)
                gate = 0.995 if note.legato else 0.97
                hold = min(max(note.duration * beat_seconds * gate, 0.055), note.duration * beat_seconds - 0.006)
                if not self._wait(hold):
                    return
                self.backend.key(vk, False)
                for button in reversed(modifiers):
                    self.backend.mouse(button, False)
                cursor = note.beat + (modifier_lead + hold) / beat_seconds
                self.update(f"演奏中 {index}/{len(notes)} · {note.token}")
            self.update("演奏完成")
        except Exception as exc:
            self.update(f"演奏失败：{exc}")
        finally:
            self.backend.release_all()


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("三角洲口琴工坊 · Windows 自动演奏器")
        self.root.geometry("820x650")
        self.root.minsize(700, 560)
        self.songs = list(BUILTIN_SONGS)
        self._load_saved_songs()
        self.backend = WindowsInput()
        self.player = Player(self.backend, self.set_status)
        self.status = tk.StringVar(value="就绪 · F6 开始 / F7 暂停继续 / F8 停止")
        self.song_var = tk.StringVar()
        self.bpm_var = tk.IntVar(value=88)
        self.skip_long_var = tk.BooleanVar(value=True)
        self.hotkey_queue: queue.SimpleQueue[int] = queue.SimpleQueue()
        self._build()
        self._refresh_songs()
        self._start_hotkeys()
        self._poll_hotkeys()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="三角洲口琴自动演奏器", font=("Microsoft YaHei UI", 20, "bold")).pack(anchor="w")
        ttk.Label(frame, text="使用 Windows SendInput；不读取游戏、不注入进程、不提供反检测。", foreground="#b45309").pack(anchor="w", pady=(4, 18))

        row = ttk.Frame(frame)
        row.pack(fill="x")
        ttk.Label(row, text="曲目").pack(side="left")
        self.song_box = ttk.Combobox(row, textvariable=self.song_var, state="readonly", width=38)
        self.song_box.pack(side="left", padx=8, fill="x", expand=True)
        self.song_box.bind("<<ComboboxSelected>>", self.load_selected)
        ttk.Button(row, text="导入网页曲库 JSON", command=self.import_library).pack(side="left")

        meta = ttk.Frame(frame)
        meta.pack(fill="x", pady=12)
        ttk.Label(meta, text="曲名").pack(side="left")
        self.title_entry = ttk.Entry(meta, width=30)
        self.title_entry.pack(side="left", padx=(8, 18))
        ttk.Label(meta, text="BPM").pack(side="left")
        ttk.Spinbox(meta, from_=30, to=240, textvariable=self.bpm_var, width=7).pack(side="left", padx=8)
        ttk.Checkbutton(meta, text="跳过长休止", variable=self.skip_long_var).pack(side="left", padx=10)
        ttk.Button(meta, text="保存为自定义曲目", command=self.save_song).pack(side="right")

        ttk.Label(frame, text="数字简谱").pack(anchor="w")
        self.score = tk.Text(frame, height=16, font=("Cascadia Mono", 12), undo=True, wrap="word")
        self.score.pack(fill="both", expand=True, pady=(6, 10))
        ttk.Label(frame, text="格式：1–7；1, 低音；1' 高音；#4 半音；0 休止；- 延音；3/2 半拍；3*2 两拍").pack(anchor="w")

        controls = ttk.Frame(frame)
        controls.pack(fill="x", pady=16)
        ttk.Button(controls, text="开始（F6）", command=self.start).pack(side="left")
        ttk.Button(controls, text="暂停/继续（F7）", command=self.player.toggle_pause).pack(side="left", padx=8)
        ttk.Button(controls, text="停止（F8）", command=self.stop).pack(side="left")
        ttk.Label(controls, textvariable=self.status).pack(side="right")

    def _refresh_songs(self) -> None:
        self.song_box["values"] = [song["title"] for song in self.songs]
        self.song_box.current(0)
        self.load_selected()

    def _load_saved_songs(self) -> None:
        path = Path(__file__).with_name("desktop_songs.json")
        if not path.exists():
            return
        try:
            songs = json.loads(path.read_text(encoding="utf-8"))
            self.songs.extend(song for song in songs if isinstance(song, dict) and {"title", "bpm", "score"} <= song.keys())
        except (OSError, ValueError):
            pass

    def load_selected(self, _event=None) -> None:
        index = self.song_box.current()
        if index < 0:
            return
        song = self.songs[index]
        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, song["title"])
        self.bpm_var.set(song["bpm"])
        self.score.delete("1.0", "end")
        self.score.insert("1.0", song["score"])

    def start(self) -> None:
        notes, _ = parse_score(self.score.get("1.0", "end"))
        if not notes:
            messagebox.showerror("无法演奏", "没有识别到有效音符。")
            return
        if self.skip_long_var.get():
            notes = compact_long_rests(notes)
        self.player.start(notes, max(30, min(240, self.bpm_var.get())))

    def stop(self) -> None:
        self.player.stop()
        self.set_status("已停止")

    def set_status(self, text: str) -> None:
        self.root.after(0, self.status.set, text)

    def save_song(self) -> None:
        title = self.title_entry.get().strip() or "未命名"
        score = self.score.get("1.0", "end").strip()
        if not parse_score(score)[0]:
            messagebox.showerror("无法保存", "没有识别到有效音符。")
            return
        song = {"id": f"desktop-{int(time.time())}", "title": title, "artist": "自定义", "bpm": self.bpm_var.get(), "score": score, "custom": True}
        self.songs.append(song)
        self._refresh_songs()
        self.song_box.current(len(self.songs) - 1)
        path = Path(__file__).with_name("desktop_songs.json")
        path.write_text(json.dumps([s for s in self.songs if s.get("custom")], ensure_ascii=False, indent=2), encoding="utf-8")
        self.set_status(f"已保存《{title}》")

    def import_library(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("曲库 JSON", "*.json"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            songs = data["songs"] if isinstance(data, dict) else data
            valid = [s for s in songs if isinstance(s, dict) and {"title", "bpm", "score"} <= s.keys()]
            self.songs.extend(valid)
            self._refresh_songs()
            self.set_status(f"已导入 {len(valid)} 首曲目")
        except Exception as exc:
            messagebox.showerror("导入失败", str(exc))

    def _start_hotkeys(self) -> None:
        def loop() -> None:
            user32 = ctypes.windll.user32
            for hotkey_id, vk in ((1, 0x75), (2, 0x76), (3, 0x77)):  # F6 F7 F8
                user32.RegisterHotKey(None, hotkey_id, 0, vk)
            message = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                if message.message == 0x0312:
                    self.hotkey_queue.put(int(message.wParam))
            for hotkey_id in (1, 2, 3):
                user32.UnregisterHotKey(None, hotkey_id)
        threading.Thread(target=loop, daemon=True).start()

    def _poll_hotkeys(self) -> None:
        try:
            while True:
                hotkey_id = self.hotkey_queue.get_nowait()
                {1: self.start, 2: self.player.toggle_pause, 3: self.stop}[hotkey_id]()
        except queue.Empty:
            pass
        self.root.after(50, self._poll_hotkeys)

    def close(self) -> None:
        self.player.stop()
        self.root.destroy()


def main() -> None:
    if os.name != "nt":
        raise SystemExit("此演奏器仅支持 Windows。")
    root = tk.Tk()
    root.withdraw()
    accepted = messagebox.askyesno(
        "封号风险确认",
        "本程序会模拟键盘和鼠标输入。三角洲行动官方将自动脚本和鼠标宏列为禁用工具，可能导致账号或设备封禁。\n\n"
        "程序不提供防检测能力。建议不要在正式对局中使用。\n\n是否理解风险并继续？",
    )
    if not accepted:
        root.destroy()
        return
    root.deiconify()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
