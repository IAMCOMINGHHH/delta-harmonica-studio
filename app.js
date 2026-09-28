import { parseScore, noteName, gameGesture, encodeLibrary, decodeLibrary } from "./src/music.js";
import { BUILTIN_SONGS } from "./src/songs.js";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const storageKey = "delta-harmonica-songs-v1";
let customSongs = loadCustomSongs();
let currentSong = BUILTIN_SONGS[0];
let timers = [];
let audioContext;

function loadCustomSongs() {
  try { return JSON.parse(localStorage.getItem(storageKey)) ?? []; } catch { return []; }
}
function persist() { localStorage.setItem(storageKey, JSON.stringify(customSongs)); }
function allSongs() { return [...BUILTIN_SONGS, ...customSongs]; }

function tone(semitone, duration = .25) {
  audioContext ??= new AudioContext();
  const now = audioContext.currentTime;
  const osc = audioContext.createOscillator();
  const gain = audioContext.createGain();
  osc.type = "triangle";
  osc.frequency.value = 261.6256 * 2 ** (semitone / 12);
  gain.gain.setValueAtTime(.0001, now);
  gain.gain.exponentialRampToValueAtTime(.23, now + .02);
  gain.gain.exponentialRampToValueAtTime(.0001, now + duration);
  osc.connect(gain).connect(audioContext.destination);
  osc.start(now); osc.stop(now + duration + .03);
}

function renderKeyboard() {
  const keys = ["Z", "X", "C", "V", "B", "N", "M", ","];
  const labels = ["1 · C", "2 · D", "3 · E", "4 · F", "5 · G", "6 · A", "7 · B", "1' · C5"];
  $("#keyboard").innerHTML = keys.map((key, i) => `<button class="key" data-index="${i}"><small>${key}</small>${i === 7 ? "1′" : i + 1}<span>${labels[i]}</span></button>`).join("");
  $$(".key").forEach((button) => button.addEventListener("pointerdown", () => pressKey(Number(button.dataset.index))));
}

function pressKey(index) {
  const semitones = [0, 2, 4, 5, 7, 9, 11, 12];
  tone(semitones[index]);
  const button = $(`.key[data-index="${index}"]`);
  button.classList.add("active"); setTimeout(() => button.classList.remove("active"), 140);
}

function stopPlayback() { timers.forEach(clearTimeout); timers = []; $$(".score-token").forEach((el) => el.classList.remove("current")); }

function play(song) {
  stopPlayback(); currentSong = song; renderCurrent(); showView("play");
  const bpm = Number($("#tempo").value) || song.bpm;
  const beatMs = 60000 / bpm;
  const parsed = parseScore(song.score);
  parsed.events.forEach((note, index) => {
    timers.push(setTimeout(() => {
      tone(note.semitone, Math.max(.09, note.duration * beatMs / 1000 * (note.legato ? .995 : .97)));
      $$(".score-token").forEach((el) => el.classList.remove("current"));
      const active = $(`.score-token[data-index="${index}"]`);
      active?.classList.add("current"); active?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
      $("#progressText").textContent = `${index + 1} / ${parsed.events.length}`;
      $("#gestureHint").textContent = `${note.token}（${noteName(note.semitone)}）：${gameGesture(note)}`;
    }, note.beat * beatMs));
  });
  timers.push(setTimeout(stopPlayback, parsed.totalBeats * beatMs + 200));
}

function renderCurrent() {
  const parsed = parseScore(currentSong.score);
  $("#nowTitle").textContent = currentSong.title;
  $("#nowMeta").textContent = `${currentSong.bpm} BPM · ${currentSong.artist}`;
  $("#tempo").value = currentSong.bpm; $("#tempoValue").textContent = currentSong.bpm;
  $("#progressText").textContent = `0 / ${parsed.events.length}`;
  $("#scoreStrip").innerHTML = parsed.events.map((note, index) => `<span class="score-token" data-index="${index}">${note.token}</span>`).join("");
}

function generatePreview() {
  const parsed = parseScore($("#scoreInput").value);
  $("#generatedScore").innerHTML = parsed.events.length ? parsed.events.map((note, i) => `<div class="generated-note"><span>${i + 1}</span><b>${note.token}</b><span>${noteName(note.semitone)} · ${gameGesture(note)}</span></div>`).join("") : "<p>尚未识别到音符。</p>";
  $("#editorMessage").textContent = `已生成 ${parsed.events.length} 个音符，共 ${parsed.totalBeats} 拍。`;
  return parsed;
}

function editorSong() { return { id: `custom-${Date.now()}`, title: $("#songTitle").value.trim() || "未命名", artist: $("#songArtist").value.trim() || "佚名", bpm: Math.min(240, Math.max(30, Number($("#songBpm").value) || 90)), score: $("#scoreInput").value.trim(), custom: true }; }

function renderLibrary() {
  $("#songList").innerHTML = allSongs().map((song) => `<article class="song-card"><span class="label">${song.custom ? "我的曲目" : "内置曲目"}</span><h3>${escapeHtml(song.title)}</h3><p>${escapeHtml(song.artist)} · ${song.bpm} BPM</p><div class="actions"><button data-play="${song.id}" class="primary">试听</button><button data-edit="${song.id}">编辑</button>${song.custom ? `<button data-delete="${song.id}">删除</button>` : ""}</div></article>`).join("");
}
function escapeHtml(text) { const div = document.createElement("div"); div.textContent = text; return div.innerHTML; }
function findSong(id) { return allSongs().find((song) => song.id === id); }
function showView(id) { $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === id)); $$(".view").forEach((v) => v.classList.toggle("active", v.id === id)); }

renderKeyboard(); renderCurrent(); renderLibrary(); generatePreview();
$$('.tab').forEach((tab) => tab.addEventListener("click", () => showView(tab.dataset.view)));
$("#playSong").addEventListener("click", () => play(currentSong));
$("#stopSong").addEventListener("click", stopPlayback);
$("#tempo").addEventListener("input", (e) => $("#tempoValue").textContent = e.target.value);
$("#previewScore").addEventListener("click", () => { const song = editorSong(); if (generatePreview().events.length) play(song); });
$("#scoreInput").addEventListener("input", generatePreview);
$("#saveSong").addEventListener("click", () => { const song = editorSong(); if (!parseScore(song.score).events.length) return $("#editorMessage").textContent = "请至少输入一个有效音符。"; customSongs.push(song); persist(); renderLibrary(); $("#editorMessage").textContent = `《${song.title}》已保存到本地曲库。`; });
$("#clearEditor").addEventListener("click", () => { $("#songTitle").value = ""; $("#songArtist").value = ""; $("#scoreInput").value = ""; generatePreview(); });
$("#songList").addEventListener("click", (e) => {
  const playId = e.target.dataset.play, editId = e.target.dataset.edit, deleteId = e.target.dataset.delete;
  if (playId) play(findSong(playId));
  if (editId) { const s = findSong(editId); $("#songTitle").value = s.title; $("#songArtist").value = s.artist; $("#songBpm").value = s.bpm; $("#scoreInput").value = s.score; generatePreview(); showView("editor"); }
  if (deleteId && confirm("确定删除这首本地曲目吗？")) { customSongs = customSongs.filter((s) => s.id !== deleteId); persist(); renderLibrary(); }
});
$("#exportLibrary").addEventListener("click", () => { const blob = new Blob([encodeLibrary(customSongs)], { type: "application/json" }); const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: "delta-harmonica-library.json" }); a.click(); URL.revokeObjectURL(a.href); });
$("#importLibrary").addEventListener("change", async (e) => { try { customSongs = decodeLibrary(await e.target.files[0].text()); persist(); renderLibrary(); alert(`已导入 ${customSongs.length} 首曲目。`); } catch (error) { alert(error.message); } e.target.value = ""; });
document.addEventListener("keydown", (e) => { if (/INPUT|TEXTAREA/.test(document.activeElement.tagName) || e.repeat) return; const index = ["z","x","c","v","b","n","m",","].indexOf(e.key.toLowerCase()); if (index >= 0) pressKey(index); });
