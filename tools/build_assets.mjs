// Render every sprite sheet from design/pixelkit.js into PNG files.
//
//   node tools/build_assets.mjs [out_dir]      (default: assets/images)
//
// pixelkit.js is the design source (mirrored from the Claude Design project
// "Pac-Man Neon Asset Kit"); this script only encodes its RGBA output as PNG.

import { mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { deflateSync } from "node:zlib";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PixelKit = createRequire(import.meta.url)(join(root, "design", "pixelkit.js"));
const outDir = resolve(process.argv[2] ?? join(root, "assets", "images"));

const CRC_TABLE = Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});

function crc32(buf) {
  let c = 0xffffffff;
  for (const byte of buf) c = CRC_TABLE[(c ^ byte) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function chunk(type, data) {
  const body = Buffer.concat([Buffer.from(type, "ascii"), data]);
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(body));
  return Buffer.concat([len, body, crc]);
}

function encodePng({ w, h, data }) {
  const header = Buffer.alloc(13);
  header.writeUInt32BE(w, 0);
  header.writeUInt32BE(h, 4);
  header[8] = 8; // bit depth
  header[9] = 6; // RGBA
  const rows = Buffer.alloc((w * 4 + 1) * h);
  for (let y = 0; y < h; y++) {
    rows[y * (w * 4 + 1)] = 0; // filter: none
    Buffer.from(data.buffer, y * w * 4, w * 4).copy(rows, y * (w * 4 + 1) + 1);
  }
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", header),
    chunk("IDAT", deflateSync(rows)),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

const sheets = PixelKit.buildAll();
const levelsDir = join(root, "assets", "levels");
for (const file of readdirSync(levelsDir).filter((f) => f.endsWith(".txt"))) {
  const rows = readFileSync(join(levelsDir, file), "utf8").split("\n").filter(Boolean);
  sheets[`maze/${file.replace(".txt", ".png")}`] = PixelKit.mazeLayer(rows);
}
for (const [path, sheet] of Object.entries(sheets)) {
  const file = join(outDir, path);
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, encodePng(sheet));
}
console.log(`wrote ${Object.keys(sheets).length} sheets to ${outDir}`);
