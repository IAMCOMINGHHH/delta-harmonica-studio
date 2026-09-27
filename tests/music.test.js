import test from "node:test";
import assert from "node:assert/strict";
import { parseScore, noteName, gameGesture, encodeLibrary, decodeLibrary } from "../src/music.js";

test("parses octave, accidental, rest and duration syntax", () => {
  const result = parseScore("1 #2 3/2 0 4' - 5,");
  assert.deepEqual(result.events.map((n) => n.semitone), [0, 3, 4, 17, -5]);
  assert.equal(result.events[2].duration, .5);
  assert.equal(result.events[3].duration, 2);
  assert.equal(result.totalBeats, 6.5);
});

test("builds readable game gestures", () => {
  assert.equal(gameGesture(parseScore("#6,").events[0]), "按住鼠标左键 + 按住鼠标中键 + 按 N");
  assert.equal(noteName(0), "C4");
});

test("round-trips a versioned library", () => {
  const songs = [{ title: "测试", bpm: 80, score: "1 2" }];
  assert.deepEqual(decodeLibrary(encodeLibrary(songs)), songs);
  assert.throws(() => decodeLibrary("{}"), /受支持/);
});
