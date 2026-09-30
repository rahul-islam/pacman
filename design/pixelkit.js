/*
 * Pac-Man Neon Asset Kit — pixel-art generator.
 *
 * Single source of truth for every sprite sheet the game loads. It runs in the
 * browser (Claude Design preview page, exposed as window.PixelKit) and in Node
 * (tools/build_assets.mjs writes the PNGs into assets/images).
 *
 * Sheet layouts match what the game slices:
 *   walk sheets     rows = right, down, left, up; columns = animation frames
 *   pacman walk     13x13 frames, 4 per row           -> 52x52
 *   pacman dead     15x15 frames, 12 in one row       -> 180x15
 *   ghost walk      14x14 frames, 2 per row           -> 28x56
 *   ghost eaten     12x12 frames, 1 per row           -> 12x48
 *   frightened_1/2  14x14 frames, 2 / 4 in one row
 *   fruits          12x12 frames, 7 in one row
 *   medals          16x16 frames, 5 in one row
 *   aura            100x100 soft glow drawn under each character
 */
(function (root) {
  "use strict";

  // ---------------------------------------------------------------------------
  // Palette
  // ---------------------------------------------------------------------------
  const PALETTE = {
    ink: "#0B0B12",
    ink2: "#161625",
    white: "#F4F4FF",
    pupil: "#2B2BFF",
    neonCyan: "#3DE8FF",
    neonPink: "#FF4FD8",
    neonViolet: "#7A5CFF",
    neonAmber: "#FFA53D",
    neonRed: "#FF3B5C",
    neonLime: "#7CFF6B",
    gold: "#FFC93D",
  };

  function rgba(hex, alpha) {
    const v = parseInt(hex.slice(1), 16);
    return [(v >> 16) & 255, (v >> 8) & 255, v & 255, alpha === undefined ? 255 : alpha];
  }

  // ---------------------------------------------------------------------------
  // Minimal RGBA raster
  // ---------------------------------------------------------------------------
  function Sheet(w, h) {
    this.w = w;
    this.h = h;
    this.data = new Uint8ClampedArray(w * h * 4);
  }
  Sheet.prototype.set = function (x, y, color) {
    if (!color || x < 0 || y < 0 || x >= this.w || y >= this.h) return;
    const c = typeof color === "string" ? rgba(color) : color;
    const i = (y * this.w + x) * 4;
    this.data[i] = c[0];
    this.data[i + 1] = c[1];
    this.data[i + 2] = c[2];
    this.data[i + 3] = c[3];
  };
  Sheet.prototype.frame = function (fx, fy, fw, fh, paint) {
    for (let y = 0; y < fh; y++) for (let x = 0; x < fw; x++) this.set(fx + x, fy + y, paint(x, y));
  };

  const DIRS = ["right", "down", "left", "up"];
  const DIR_ANGLE = { right: 0, down: 90, left: 180, up: 270 };
  const DIR_VEC = { right: [1, 0], down: [0, 1], left: [-1, 0], up: [0, -1] };

  function angleDiff(a, b) {
    const d = Math.abs(((a - b) % 360) + 360) % 360;
    return d > 180 ? 360 - d : d;
  }

  // ---------------------------------------------------------------------------
  // Pac-Man skins
  // ---------------------------------------------------------------------------
  // body / shade / highlight colours plus an optional decorator that paints
  // over the body. Decorators receive pixel info relative to the centre.
  const SKINS = {
    classic: { label: "Classic", body: "#FFE14D", shade: "#D9A91A", hi: "#FFF6B8" },
    neon: {
      label: "Neon",
      body: "#FF4FD8",
      shade: "#C21FA0",
      hi: "#FFC2F2",
      deco: (p) => (p.r > 5.4 ? "#FFE3F9" : null),
    },
    robot: {
      label: "Robot",
      body: "#AEB9CC",
      shade: "#6F7C93",
      hi: "#E6ECF5",
      eye: false,
      deco: (p) => {
        if (p.dy === -2 && Math.abs(p.dx) <= 4) return "#B8F7FF";
        if (p.dy === -1 && Math.abs(p.dx) <= 5) return "#3DE8FF";
        if (p.dy === 3 && (p.dx === -3 || p.dx === 3)) return "#6F7C93";
        return null;
      },
    },
    ninja: {
      label: "Ninja",
      body: "#7A5CFF",
      shade: "#4B34C9",
      hi: "#B3A3FF",
      deco: (p) => (p.dy === -3 || (p.dy === -4 && Math.abs(p.dx) <= 2) ? "#FF3B5C" : null),
    },
    astro: {
      label: "Astro",
      body: "#FF9F43",
      shade: "#C66A12",
      hi: "#FFD199",
      deco: (p) => {
        if (p.r > 5.4) return p.dx + p.dy < -5 ? "#FFFFFF" : "#BFE6FF";
        return null;
      },
    },
    slime: {
      label: "Slime",
      body: "#7CFF6B",
      shade: "#3FBF4A",
      hi: "#D4FFCC",
      deco: (p) => ((p.x * 7 + p.y * 3) % 11 === 0 && p.r < 5 ? "#4FE05A" : null),
    },
    gold: {
      label: "Gold",
      body: "#FFC93D",
      shade: "#C98A14",
      hi: "#FFF1B8",
      deco: (p) => ((p.dx === -3 && p.dy === -2) || (p.dx === 2 && p.dy === 3) ? "#FFFFFF" : null),
    },
  };

  // Mouth half-angle (degrees) per walk frame: closed, half, wide, half.
  const MOUTH = [0, 24, 48, 24];
  const PAC_EYE = { right: [1, -3], left: [-1, -3], down: [3, 1], up: [-3, -1] };

  // Colour of one Pac-Man pixel, or null when transparent.
  function pacPixel(skin, x, y, size, facing, half, withEye) {
    const c = (size - 1) / 2;
    const dx = x - c;
    const dy = y - c;
    const r = Math.hypot(dx, dy);
    if (r > size / 2 - 0.1) return null;
    if (half > 0 && r > 0.8 && angleDiff((Math.atan2(dy, dx) * 180) / Math.PI, DIR_ANGLE[facing]) <= half) {
      return null;
    }
    const p = { x, y, dx: Math.round(dx), dy: Math.round(dy), r, facing };
    if (withEye && skin.eye !== false) {
      const [ex, ey] = PAC_EYE[facing];
      if (p.dx === ex && p.dy === ey) return "#1A1030";
    }
    const deco = skin.deco && skin.deco(p);
    if (deco) return deco;
    if (dx + dy < -5.5 && r > 4.2) return skin.hi;
    if (dx + dy > 5.5 && r > 4.5) return skin.shade;
    return skin.body;
  }

  function pacmanWalk(skin) {
    const s = 13;
    const sheet = new Sheet(s * 4, s * 4);
    DIRS.forEach((dir, row) => {
      MOUTH.forEach((half, col) => {
        sheet.frame(col * s, row * s, s, s, (x, y) => pacPixel(skin, x, y, s, dir, half, true));
      });
    });
    return sheet;
  }

  // Death: the mouth opens upward until Pac-Man vanishes, then a neon burst.
  function pacmanDead(skin) {
    const s = 15;
    const sheet = new Sheet(s * 12, s);
    const halves = [0, 25, 50, 75, 100, 125, 150, 170, 180];
    halves.forEach((half, i) => {
      sheet.frame(i * s, 0, s, s, (x, y) => {
        if (x < 1 || y < 1 || x > 13 || y > 13) return null;
        return half >= 180 ? null : pacPixel(skin, x - 1, y - 1, 13, "up", half, i < 4);
      });
    });
    [[3, 255], [5, 190], [6, 90]].forEach(([radius, alpha], k) => {
      const col = rgba(skin.hi, alpha);
      const fx = (9 + k) * s;
      for (let a = 0; a < 360; a += 45) {
        const px = Math.round(7 + radius * Math.cos((a * Math.PI) / 180));
        const py = Math.round(7 + radius * Math.sin((a * Math.PI) / 180));
        sheet.set(fx + px, py, col);
      }
    });
    return sheet;
  }

  // ---------------------------------------------------------------------------
  // Ghosts
  // ---------------------------------------------------------------------------
  const GHOSTS = {
    blinky: { body: "#FF3B5C", shade: "#C21E3E", hi: "#FF9AAE" },
    pinky: { body: "#FF6AD5", shade: "#C93CA6", hi: "#FFC2EE" },
    inky: { body: "#3DE8FF", shade: "#19A9C4", hi: "#B8F7FF" },
    clyde: { body: "#FFA53D", shade: "#C9731A", hi: "#FFD9A8" },
  };
  const FRIGHT = { body: "#3B3BFF", shade: "#2323B8", hi: "#8C8CFF", face: "#FFD1F0" };
  const FLASH = { body: "#F4F4FF", shade: "#C8C8E0", hi: "#FFFFFF", face: "#FF3B5C" };

  // Body silhouette (14x14): dome, straight sides, animated feet.
  function ghostShape(x, y, frame) {
    if (y < 7) return (x - 6.5) ** 2 + (y + 0.5 - 6.5) ** 2 <= 42.25;
    if (y < 13) return true;
    return ((x + frame * 2) % 4) < 2;
  }

  function ghostBody(colors, x, y, frame) {
    if (!ghostShape(x, y, frame)) return null;
    if (y < 5 && x < 6.5 && (x - 6.5) ** 2 + (y + 0.5 - 6.5) ** 2 > 20) return colors.hi;
    if (y >= 12) return colors.shade;
    return colors.body;
  }

  // Eye whites 4x4 with a 2x2 pupil looking in `dir`.
  function eyePixel(x, y, dir, left, top) {
    const [vx, vy] = DIR_VEC[dir];
    for (const ox of [left, left + 6]) {
      const wx = ox + vx;
      const wy = top + vy;
      if (x >= wx && x < wx + 4 && y >= wy && y < wy + 4) {
        const px = wx + 1 + vx;
        const py = wy + 1 + vy;
        return x >= px && x < px + 2 && y >= py && y < py + 2 ? PALETTE.pupil : PALETTE.white;
      }
    }
    return null;
  }

  function ghostWalk(colors) {
    const s = 14;
    const sheet = new Sheet(s * 2, s * 4);
    DIRS.forEach((dir, row) => {
      for (let f = 0; f < 2; f++) {
        sheet.frame(f * s, row * s, s, s, (x, y) => eyePixel(x, y, dir, 2, 4) || ghostBody(colors, x, y, f));
      }
    });
    return sheet;
  }

  function scaredPixel(colors, x, y, frame) {
    const body = ghostBody(colors, x, y, frame);
    if (!body) return null;
    const eye = (x === 4 || x === 5 || x === 8 || x === 9) && (y === 5 || y === 6);
    const mouth = x >= 2 && x <= 11 && y === (x % 2 === 0 ? 9 : 10);
    return eye || mouth ? colors.face : body;
  }

  function frightened(frames) {
    const s = 14;
    const sheet = new Sheet(s * frames.length, s);
    frames.forEach(([colors, f], i) => sheet.frame(i * s, 0, s, s, (x, y) => scaredPixel(colors, x, y, f)));
    return sheet;
  }

  function ghostEaten() {
    const s = 12;
    const sheet = new Sheet(s, s * 4);
    DIRS.forEach((dir, row) => sheet.frame(0, row * s, s, s, (x, y) => eyePixel(x, y, dir, 1, 4)));
    return sheet;
  }

  // ---------------------------------------------------------------------------
  // Fruits (12x12) — order matters: index = fruit id used by skin prices
  // ---------------------------------------------------------------------------
  function disc(cx, cy, r) {
    return (x, y) => (x - cx) ** 2 + (y - cy) ** 2 <= r * r;
  }
  function shaded(inside, cx, cy, body, shade, hi) {
    return (x, y) => {
      if (!inside(x, y)) return null;
      const d = x - cx + (y - cy);
      if (d < -3.2) return hi;
      if (d > 2.6) return shade;
      return body;
    };
  }
  function layers(...painters) {
    return (x, y) => {
      for (const p of painters) {
        const c = p(x, y);
        if (c) return c;
      }
      return null;
    };
  }
  function pixels(list, color) {
    const set = new Set(list.map(([x, y]) => x + "," + y));
    return (x, y) => (set.has(x + "," + y) ? color : null);
  }

  const FRUITS = [
    {
      name: "cherry",
      paint: layers(
        pixels([[2, 7], [7, 8]], "#FFC2CC"),
        pixels([[4, 5], [5, 4], [6, 3], [7, 2], [8, 1], [8, 2], [8, 3], [8, 4], [8, 5], [9, 0], [10, 0], [10, 1]], "#57E36B"),
        shaded(disc(3.5, 8.5, 2.8), 3.5, 8.5, "#FF3B5C", "#B81E3A", "#FF8FA3"),
        shaded(disc(8, 8.5, 2.8), 8, 8.5, "#FF3B5C", "#B81E3A", "#FF8FA3"),
      ),
    },
    {
      name: "strawberry",
      paint: layers(
        pixels([[5, 0], [6, 0]], "#2E9E45"),
        pixels([[3, 2], [4, 1], [5, 2], [6, 2], [7, 1], [8, 2]], "#57E36B"),
        (x, y) => {
          if (y < 2 || y > 10) return null;
          const half = [0, 0, 4.5, 5, 5, 4.8, 4.3, 3.6, 2.8, 1.9, 1][y];
          if (Math.abs(x - 5.5) > half) return null;
          if (y > 2 && (x + y) % 3 === 0 && y % 2 === 0) return "#FFE14D";
          return x > 7 && y > 5 ? "#B81E3A" : "#FF3B5C";
        },
      ),
    },
    {
      name: "orange",
      paint: layers(
        pixels([[5, 1]], "#8A5A2B"),
        pixels([[6, 0], [7, 0], [7, 1], [8, 1]], "#57E36B"),
        shaded(disc(5.5, 6.5, 4.8), 5.5, 6.5, "#FFA53D", "#C9731A", "#FFD9A8"),
      ),
    },
    {
      name: "apple",
      paint: layers(
        pixels([[6, 0], [6, 1]], "#8A5A2B"),
        pixels([[7, 1], [8, 0], [8, 1], [9, 0]], "#57E36B"),
        (x, y) => ((x === 5 || x === 6) && y === 2 ? null : shaded(disc(5.5, 7, 4.6), 5.5, 7, "#FF3B5C", "#B81E3A", "#FF9AAE")(x, y)),
      ),
    },
    {
      name: "melon",
      paint: (x, y) => {
        if (((x - 5.5) / 5.2) ** 2 + ((y - 6.5) / 4.6) ** 2 > 1) return null;
        if (x === 3 && y === 4) return "#E0FFE0";
        return (x + (y >> 1)) % 3 === 0 ? "#2E9E45" : "#57E36B";
      },
    },
    {
      name: "bell",
      paint: layers(
        pixels([[5, 1], [6, 1]], "#C9A514"),
        pixels([[5, 10], [6, 10]], "#3DE8FF"),
        (x, y) => {
          if (y < 2 || y > 9) return null;
          const half = [0, 0, 1.5, 2.5, 3, 3.5, 3.5, 4, 4.8, 5.5][y];
          const dx = x - 5.5;
          if (Math.abs(dx) > half) return null;
          if (y === 9) return "#C9A514";
          if (dx < -half + 1.2 && y > 3) return "#FFF6B8";
          return dx > half - 1.2 ? "#C9A514" : "#FFE14D";
        },
      ),
    },
    {
      name: "key",
      paint: (x, y) => {
        const ring = (x - 5.5) ** 2 + (y - 3) ** 2;
        const head = ring <= 3.2 * 3.2 && ring > 1.3 * 1.3;
        const shaft = (x === 5 || x === 6) && y >= 5 && y <= 11;
        const teeth = (x === 7 || x === 8) && (y === 8 || y === 10);
        if (!(head || shaft || teeth)) return null;
        return x >= 6 && !head ? "#19A9C4" : "#3DE8FF";
      },
    },
  ];

  function fruitsSheet() {
    const s = 12;
    const sheet = new Sheet(s * FRUITS.length, s);
    FRUITS.forEach((fruit, i) => sheet.frame(i * s, 0, s, s, fruit.paint));
    return sheet;
  }

  // ---------------------------------------------------------------------------
  // Medals (16x16): gold, silver, bronze, 4th, 5th
  // ---------------------------------------------------------------------------
  const MEDALS = [
    ["#FFC93D", "#C98A14", "#FFF1B8"],
    ["#CFD6E6", "#8792A8", "#FFFFFF"],
    ["#E08A4F", "#A0552A", "#FFC9A3"],
    ["#3DE8FF", "#19A9C4", "#B8F7FF"],
    ["#FF6AD5", "#C93CA6", "#FFC2EE"],
  ];

  function medalsSheet() {
    const s = 16;
    const sheet = new Sheet(s * MEDALS.length, s);
    MEDALS.forEach(([body, shade, hi], i) => {
      sheet.frame(i * s, 0, s, s, (x, y) => {
        const d = Math.hypot(x - 7.5, y - 10);
        if (d <= 5) {
          if (d > 3.3 && d <= 4.1) return shade;
          if ((x === 5 && y === 7) || (x === 6 && y === 7) || (x === 5 && y === 8)) return hi;
          return body;
        }
        const leftBand = y <= 6 && Math.abs(x - (3 + y * 0.6)) < 1.1;
        const rightBand = y <= 6 && Math.abs(x - (12 - y * 0.6)) < 1.1;
        return leftBand || rightBand ? (y < 3 ? "#7A5CFF" : "#5A3FE0") : null;
      });
    });
    return sheet;
  }

  // ---------------------------------------------------------------------------
  // Aura: soft neon glow under a character
  // ---------------------------------------------------------------------------
  function aura(hex, strength) {
    const s = 100;
    const [r, g, b] = rgba(hex);
    const sheet = new Sheet(s, s);
    sheet.frame(0, 0, s, s, (x, y) => {
      const t = Math.max(0, 1 - Math.hypot(x - 49.5, y - 49.5) / 50);
      const a = Math.round(t * t * t * (strength || 70));
      return a ? [r, g, b, a] : null;
    });
    return sheet;
  }

  // ---------------------------------------------------------------------------
  // App icon (256x256)
  // ---------------------------------------------------------------------------
  function icon() {
    const s = 256;
    const sheet = new Sheet(s, s);
    const radius = 56;
    const inRounded = (x, y, inset) => {
      const lo = inset;
      const hi = s - 1 - inset;
      const r = radius - inset;
      const cx = Math.min(Math.max(x, lo + r), hi - r);
      const cy = Math.min(Math.max(y, lo + r), hi - r);
      return (x - cx) ** 2 + (y - cy) ** 2 <= r * r;
    };
    const scale = 12;
    const pacLeft = 36;
    const pacTop = (s - 13 * scale) / 2;
    sheet.frame(0, 0, s, s, (x, y) => {
      if (!inRounded(x, y, 0)) return null;
      if (!inRounded(x, y, 10)) return PALETTE.neonCyan;
      if (!inRounded(x, y, 14)) return PALETTE.ink2;
      const px = Math.floor((x - pacLeft) / scale);
      const py = Math.floor((y - pacTop) / scale);
      if (px >= 0 && px < 13 && py >= 0 && py < 13) {
        const c = pacPixel(SKINS.classic, px, py, 13, "right", 48, true);
        if (c) return c;
      }
      const dot = (cx) => Math.abs(x - cx) <= 9 && Math.abs(y - 128) <= 9;
      if (dot(206)) return "#FFC2EE";
      return PALETTE.ink;
    });
    return sheet;
  }

  // ---------------------------------------------------------------------------
  // Maze: neon outline layer (white; the game tints it per level)
  // ---------------------------------------------------------------------------
  // `rows` is a level file as an array of strings (see tools/generate_levels.py):
  // "#" is wall, every other character is open space (corridors, ghost house,
  // door). Corridors are dilated by a disc so walls get rounded, inset outlines.
  const TILE = 8;

  function mazeLayer(rows) {
    const h = rows.length * TILE;
    const w = rows[0].length * TILE;
    const cols = rows[0].length;
    // Out-of-range pixels copy the nearest edge cell so tunnels stay open.
    const isOpenPx = (px, py) => {
      const cx = Math.min(cols - 1, Math.max(0, Math.floor(px / TILE)));
      const cy = Math.min(rows.length - 1, Math.max(0, Math.floor(py / TILE)));
      return rows[cy][cx] !== "#";
    };
    const R = 2.6;
    const reach = Math.ceil(R);
    const space = new Uint8Array(w * h); // 1 = corridor after dilation
    for (let y = 0; y < h; y++)
      for (let x = 0; x < w; x++) {
        let hit = false;
        for (let oy = -reach; oy <= reach && !hit; oy++)
          for (let ox = -reach; ox <= reach && !hit; ox++)
            if (ox * ox + oy * oy <= R * R && isOpenPx(x + ox, y + oy)) hit = true;
        space[y * w + x] = hit ? 1 : 0;
      }
    const wall = (x, y) => (x < 0 || y < 0 || x >= w || y >= h ? !isOpenPx(x, y) : !space[y * w + x]);
    const edge = new Uint8Array(w * h);
    for (let y = 0; y < h; y++)
      for (let x = 0; x < w; x++)
        if (wall(x, y) && (!wall(x + 1, y) || !wall(x - 1, y) || !wall(x, y + 1) || !wall(x, y - 1))) edge[y * w + x] = 1;

    const sheet = new Sheet(w, h);
    const G = 3; // glow radius in px
    for (let y = 0; y < h; y++)
      for (let x = 0; x < w; x++) {
        if (edge[y * w + x]) {
          sheet.set(x, y, [255, 255, 255, 255]);
          continue;
        }
        let best = 99;
        for (let oy = -G; oy <= G; oy++)
          for (let ox = -G; ox <= G; ox++) {
            const nx = x + ox;
            const ny = y + oy;
            if (nx >= 0 && ny >= 0 && nx < w && ny < h && edge[ny * w + nx]) best = Math.min(best, Math.hypot(ox, oy));
          }
        let a = best <= G ? Math.round(110 * (1 - best / (G + 0.5)) ** 2) : 0;
        if (wall(x, y)) a = Math.max(a, 16); // faint panel fill inside walls
        if (a) sheet.set(x, y, [255, 255, 255, a]);
      }
    return sheet;
  }

  // ---------------------------------------------------------------------------
  // Everything the game loads, keyed by path under assets/images
  // ---------------------------------------------------------------------------
  function buildAll() {
    const out = {};
    for (const [name, skin] of Object.entries(SKINS)) {
      out[`pacman/${name}/walk.png`] = pacmanWalk(skin);
      out[`pacman/${name}/dead.png`] = pacmanDead(skin);
      out[`pacman/${name}/aura.png`] = aura(skin.body, 60);
    }
    for (const [name, colors] of Object.entries(GHOSTS)) {
      out[`ghost/${name}/walk.png`] = ghostWalk(colors);
      out[`ghost/${name}/aura.png`] = aura(colors.body, 70);
    }
    out["ghost/eaten.png"] = ghostEaten();
    out["ghost/frightened_1.png"] = frightened([[FRIGHT, 0], [FRIGHT, 1]]);
    out["ghost/frightened_2.png"] = frightened([[FRIGHT, 0], [FLASH, 1], [FRIGHT, 1], [FLASH, 0]]);
    out["other/fruits.png"] = fruitsSheet();
    out["other/medals.png"] = medalsSheet();
    out["ico.png"] = icon();
    return out;
  }

  const api = { PALETTE, SKINS, GHOSTS, FRUITS, MEDALS, Sheet, rgba, buildAll, mazeLayer };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.PixelKit = api;
})(typeof self !== "undefined" ? self : this);
