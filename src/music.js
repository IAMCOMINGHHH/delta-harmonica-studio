export const DEGREE_SEMITONES = [0, 2, 4, 5, 7, 9, 11];

export function parseScore(source, beatsPerBar = 4) {
  const clean = source
    .split(/\r?\n/)
    .map((line) => line.replace(/\/\/.*$/, ""))
    .join(" ");
  const raw = clean.match(/\|:|:\||\||0(?:\/\d+|\*\d+(?:\.\d+)?)?|[-_]|#?[1-7](?:[,']*)?(?:\/\d+|\*\d+(?:\.\d+)?)?~?/g) ?? [];
  const events = [];
  let beat = 0;
  let lastNote = null;

  for (const token of raw) {
    if (token === "|" || token === "|:" || token === ":|") continue;
    if (token === "-" || token === "_") {
      if (lastNote) lastNote.duration += 1;
      beat += 1;
      continue;
    }
    const restMatch = token.match(/^0(?:\/(\d+)|\*(\d+(?:\.\d+)?))?$/);
    if (restMatch) {
      lastNote = null;
      beat += restMatch[1] ? 1 / Number(restMatch[1]) : restMatch[2] ? Number(restMatch[2]) : 1;
      continue;
    }

    const match = token.match(/^(#?)([1-7])([,']*)(?:\/(\d+)|\*(\d+(?:\.\d+)?))?(~?)$/);
    if (!match) continue;
    const [, accidental, degreeText, octaveMarks, divisor, multiplier, legato] = match;
    const duration = divisor ? 1 / Number(divisor) : multiplier ? Number(multiplier) : 1;
    const octave = [...octaveMarks].reduce((sum, mark) => sum + (mark === "'" ? 1 : -1), 0);
    const degree = Number(degreeText);
    const semitone = DEGREE_SEMITONES[degree - 1] + octave * 12 + (accidental ? 1 : 0);
    lastNote = { token: token.replace(/~$/, ""), degree, accidental: Boolean(accidental), octave, semitone, beat, duration, legato: Boolean(legato) };
    events.push(lastNote);
    beat += duration;
  }

  return { events, totalBeats: beat, beatsPerBar };
}

export function noteName(semitone, tonicMidi = 60) {
  const names = ["C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B"];
  const midi = tonicMidi + semitone;
  return `${names[((midi % 12) + 12) % 12]}${Math.floor(midi / 12) - 1}`;
}

export function gameGesture(note) {
  const keys = ["Z", "X", "C", "V", "B", "N", "M"];
  const parts = [];
  if (note.octave < 0) parts.push("按住鼠标左键");
  if (note.octave > 0) parts.push("按住鼠标右键");
  if (note.accidental) parts.push("按住鼠标中键");
  parts.push(`按 ${keys[note.degree - 1]}`);
  return parts.join(" + ");
}

export function encodeLibrary(songs) {
  return JSON.stringify({ format: "delta-harmonica-library", version: 1, songs }, null, 2);
}

export function decodeLibrary(text) {
  const data = JSON.parse(text);
  if (data?.format !== "delta-harmonica-library" || data.version !== 1 || !Array.isArray(data.songs)) {
    throw new Error("不是受支持的曲库文件");
  }
  return data.songs;
}
