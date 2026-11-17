"""Escena interactiva para visualizar rutas metabólicas."""

from __future__ import annotations

import streamlit as st

_HTML = """
<section
  class="molecular-scene"
  aria-label="Visualización molecular de la ruta"
>
  <div class="scene-heading">
    <div>
      <span class="scene-eyebrow">SIMULACIÓN DE RUTA</span>
      <strong class="scene-title">Flujo metabólico</strong>
    </div>
    <span class="scene-cost" data-cost>EN ESPERA</span>
  </div>
  <canvas class="molecule-canvas" aria-hidden="true"></canvas>
  <div class="scene-endpoints">
    <div class="endpoint endpoint-source">
      <span class="endpoint-label">SUSTRATO INICIAL</span>
      <strong data-source></strong>
    </div>
    <span class="endpoint-arrow" aria-hidden="true">→</span>
    <div class="endpoint endpoint-destination">
      <span class="endpoint-label">DESTINO</span>
      <strong data-destination></strong>
    </div>
  </div>
  <div class="scene-footer">
    <span class="scene-status" data-status>
      Elige dos metabolitos para explorar la red.
    </span>
    <span class="scene-note">
      Átomos simbólicos · visualización conceptual
    </span>
  </div>
</section>
"""

_CSS = """
:host {
  display: block;
  color: var(--st-text-color, #eaf8f6);
  font-family: var(--st-font, sans-serif);
}
.molecular-scene {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 340px;
  overflow: hidden;
  padding: 22px 26px 18px;
  border: 1px solid rgba(111, 221, 202, .2);
  border-radius: 22px;
  background:
    radial-gradient(
      ellipse at 50% 48%, rgba(32, 132, 124, .23), transparent 49%
    ),
    radial-gradient(
      ellipse at 88% 8%, rgba(80, 107, 213, .19), transparent 34%
    ),
    linear-gradient(135deg, #0d222a 0%, #09171f 55%, #101a2b 100%);
  box-shadow: inset 0 1px rgba(255,255,255,.035), 0 20px 60px rgba(0,0,0,.18);
}
.molecular-scene::before {
  position: absolute;
  inset: 0;
  pointer-events: none;
  content: "";
  opacity: .16;
  background-image: radial-gradient(
    rgba(179, 246, 232, .45) .7px, transparent .7px
  );
  background-size: 24px 24px;
  mask-image: linear-gradient(
    90deg, transparent, #000 20%, #000 80%, transparent
  );
}
.scene-heading, .scene-endpoints, .scene-footer {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.scene-heading > div { display: grid; gap: 3px; }
.scene-eyebrow, .endpoint-label {
  color: #86b8b4;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: .16em;
}
.scene-title {
  color: #f0fbf8;
  font-family: var(--st-heading-font, var(--st-font, sans-serif));
  font-size: 17px;
  font-weight: 650;
  letter-spacing: -.025em;
}
.scene-cost {
  padding: 7px 10px;
  border: 1px solid rgba(77, 220, 190, .26);
  border-radius: 999px;
  background: rgba(36, 184, 155, .1);
  color: #74efd0;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: .09em;
  white-space: nowrap;
}
.molecule-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.scene-heading {
  position: absolute;
  top: 22px;
  right: 26px;
  left: 26px;
}
.scene-endpoints {
  position: absolute;
  right: 26px;
  bottom: 62px;
  left: 26px;
  align-items: flex-end;
}
.endpoint { display: grid; min-width: 0; gap: 5px; }
.endpoint-destination { text-align: right; }
.endpoint strong {
  overflow: hidden;
  color: #f2fbf8;
  font-family: var(--st-heading-font, var(--st-font, sans-serif));
  font-size: clamp(13px, 2vw, 17px);
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.endpoint-arrow {
  padding-bottom: 1px;
  color: #56dfc0;
  font-size: 19px;
}
.scene-footer {
  position: absolute;
  right: 26px;
  bottom: 16px;
  left: 26px;
  padding-top: 10px;
  border-top: 1px solid rgba(151, 215, 205, .12);
  color: #9ab7b5;
  font-size: 10px;
}
.scene-status { color: #b8d4d0; }
.scene-note { text-align: right; }
@media (max-width: 520px) {
  .molecular-scene { height: 320px; padding: 18px 16px 14px; }
  .scene-heading { top: 18px; right: 16px; left: 16px; }
  .scene-endpoints { right: 16px; bottom: 58px; left: 16px; }
  .scene-footer { right: 16px; left: 16px; }
  .scene-footer { align-items: flex-start; font-size: 9px; }
  .scene-note { max-width: 42%; }
}
@media (prefers-reduced-motion: reduce) {
  .molecular-scene::before { opacity: .08; }
}
"""

_JS = """
export default function (component) {
  const { data, parentElement } = component;
  const canvas = parentElement.querySelector(".molecule-canvas");
  const context = canvas.getContext("2d");
  const sourceLabel = parentElement.querySelector("[data-source]");
  const destinationLabel = parentElement.querySelector("[data-destination]");
  const statusLabel = parentElement.querySelector("[data-status]");
  const costLabel = parentElement.querySelector("[data-cost]");
  const scene = parentElement.querySelector(".molecular-scene");
  const reducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;
  let width = 0;
  let height = 0;
  let frame = 0;
  let elapsed = 0;
  let pointer = { x: -1000, y: -1000 };
  let previousTime = 0;
  let particles = [];

  sourceLabel.textContent = data.source;
  destinationLabel.textContent = data.destination;
  if (!data.calculated) {
    statusLabel.textContent =
      "Selecciona los metabolitos y calcula su recorrido.";
    costLabel.textContent = "LISTO PARA EXPLORAR";
  } else if (data.path.length > 1) {
    statusLabel.textContent =
      (data.path.length - 1) +
      ((data.path.length - 1) === 1
        ? " transformación · "
        : " transformaciones · ") +
      data.cost +
      (data.cost === 1 ? " reacción mínima" : " reacciones mínimas");
    costLabel.textContent =
      data.cost + (data.cost === 1 ? " REACCIÓN" : " REACCIONES");
  } else if (data.path.length === 1) {
    statusLabel.textContent = "Mismo metabolito de inicio y destino.";
    costLabel.textContent = "0 REACCIONES";
  } else {
    statusLabel.textContent =
      "No se encontró una vía entre estos metabolitos.";
    costLabel.textContent = "SIN CONEXIÓN";
  }

  function resize() {
    const bounds = canvas.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    width = bounds.width;
    height = bounds.height;
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    const count = Math.max(22, Math.floor(width / 13));
    particles = Array.from({ length: count }, (_, index) => ({
      x: (index * 97.31) % Math.max(width, 1),
      y: (index * 53.77) % Math.max(height, 1),
      speed: .4 + ((index * 17) % 13) / 18,
      size: .6 + ((index * 11) % 9) / 12,
      phase: index * 1.71
    }));
    draw(0);
  }

  function drawAtom(x, y, radius, color, glow) {
    context.save();
    context.shadowBlur = glow ? 17 : 7;
    context.shadowColor = color;
    const gradient = context.createRadialGradient(
      x - radius * .3, y - radius * .35, 1, x, y, radius
    );
    gradient.addColorStop(0, "#f5fffb");
    gradient.addColorStop(.24, color);
    gradient.addColorStop(1, color + "65");
    context.fillStyle = gradient;
    context.beginPath();
    context.arc(x, y, radius, 0, Math.PI * 2);
    context.fill();
    context.restore();
  }

  function drawMolecule(x, y, scale, label, active) {
    const palette = [
      "#57e4c4", "#8ca9ff", "#f2bc70", "#a18cff", "#61d5e8", "#f391a8"
    ];
    const seed = Array.from(label || "metabolito").reduce(
      (total, letter) => total + letter.charCodeAt(0), 0
    );
    const satellites = 4 + seed % 4;
    const atoms = [[0, 0, 13, palette[seed % palette.length]]];
    for (let index = 0; index < satellites; index += 1) {
      const angle = seed * .017 + index * Math.PI * 2 / satellites;
      const distance = 20 + (seed + index * 7) % 13;
      const radius = 4 + (seed + index) % 4;
      const color = palette[(seed + index + 1) % palette.length];
      atoms.push([
        Math.cos(angle) * distance,
        Math.sin(angle) * distance,
        radius,
        color
      ]);
    }
    context.save();
    context.translate(x, y);
    context.scale(scale, scale);
    context.lineWidth = 1.3;
    context.strokeStyle = "rgba(132, 221, 207, .46)";
    for (let index = 1; index < atoms.length; index += 1) {
      context.beginPath();
      context.moveTo(atoms[0][0], atoms[0][1]);
      context.lineTo(atoms[index][0], atoms[index][1]);
      context.stroke();
    }
    context.beginPath();
    context.arc(0, 0, 37, 0, Math.PI * 2);
    context.strokeStyle = active
      ? "rgba(88, 232, 198, .32)"
      : "rgba(111, 161, 181, .2)";
    context.lineWidth = 1;
    context.stroke();
    atoms.forEach((atom, index) => {
      const pulse = active && index === 0
        ? 1 + Math.sin(elapsed * 2.4) * .1
        : 1;
      drawAtom(atom[0], atom[1], atom[2] * pulse, atom[3], active);
    });
    if (label) {
      context.fillStyle = "rgba(223, 245, 239, .93)";
      context.font = "600 10px system-ui, sans-serif";
      context.textAlign = "center";
      context.fillText(label, 0, 53, 105);
    }
    context.restore();
  }

  function draw(time) {
    if (!width || !height) return;
    if (previousTime) elapsed += Math.min(time - previousTime, 50) / 1000;
    previousTime = time || previousTime;
    context.clearRect(0, 0, width, height);

    const ambient = context.createRadialGradient(
      pointer.x, pointer.y, 0, pointer.x, pointer.y, 190
    );
    ambient.addColorStop(0, "rgba(54, 211, 183, .12)");
    ambient.addColorStop(1, "rgba(54, 211, 183, 0)");
    context.fillStyle = ambient;
    context.fillRect(0, 0, width, height);

    particles.forEach((particle) => {
      const x = (particle.x + elapsed * particle.speed * 5) % width;
      const y = particle.y + Math.sin(elapsed * .55 + particle.phase) * 5;
      context.beginPath();
      context.arc(x, y, particle.size, 0, Math.PI * 2);
      context.fillStyle = "rgba(169, 229, 218, .38)";
      context.fill();
    });

    const route = Array.isArray(data.path) ? data.path : [];
    if (data.calculated && route.length) {
      const marks = route.length > 8
        ? Array.from(
            { length: 8 },
            (_, index) => route[Math.round(index * (route.length - 1) / 7)]
          )
        : route;
      const left = Math.max(78, width * .12);
      const right = Math.min(width - 78, width * .88);
      const span = Math.max(right - left, 1);
      const points = marks.map((label, index) => ({
        x: marks.length === 1
          ? width / 2
          : left + span * index / (marks.length - 1),
        y: height * .42 + Math.sin(index * 1.45 + elapsed * .45) * 10,
        label
      }));

      context.lineWidth = 2;
      context.strokeStyle = "rgba(75, 220, 190, .38)";
      context.beginPath();
      points.forEach((point, index) => {
        if (index === 0) context.moveTo(point.x, point.y);
        else context.lineTo(point.x, point.y);
      });
      context.stroke();

      points.forEach((point, index) => {
        drawMolecule(
          point.x,
          point.y,
          index === 0 || index === points.length - 1 ? .84 : .58,
          point.label, index === 0 || index === points.length - 1);
      });

      if (points.length > 1) {
        const cycle = Number.isFinite(elapsed) ? elapsed * .16 : 0;
        const progress = ((cycle % 1) + 1) % 1;
        const position = progress * (points.length - 1);
        const segment = Math.min(
          Math.floor(position), points.length - 2
        );
        const fraction = position - segment;
        const from = points[segment];
        const to = points[segment + 1];
        if (from && to) {
          drawAtom(
            from.x + (to.x - from.x) * fraction,
            from.y + (to.y - from.y) * fraction,
            4.2, "#f2d57c", true
          );
        }
      }
    } else {
      drawMolecule(width * .29, height * .42, 1.04, data.source, true);
      drawMolecule(width * .71, height * .42, 1.04, data.destination, true);
      context.setLineDash([3, 8]);
      context.strokeStyle = "rgba(111, 196, 184, .28)";
      context.lineWidth = 1;
      context.beginPath();
      context.moveTo(width * .39, height * .42);
      context.lineTo(width * .61, height * .42);
      context.stroke();
      context.setLineDash([]);
    }

    if (!reducedMotion) frame = requestAnimationFrame(draw);
  }

  function onPointerMove(event) {
    const bounds = scene.getBoundingClientRect();
    pointer = {
      x: event.clientX - bounds.left,
      y: event.clientY - bounds.top
    };
  }

  function onPointerLeave() {
    pointer = { x: -1000, y: -1000 };
  }

  const observer = new ResizeObserver(resize);
  observer.observe(canvas);
  scene.addEventListener("pointermove", onPointerMove);
  scene.addEventListener("pointerleave", onPointerLeave);
  resize();
  if (!reducedMotion) frame = requestAnimationFrame(draw);

  return () => {
    cancelAnimationFrame(frame);
    observer.disconnect();
    scene.removeEventListener("pointermove", onPointerMove);
    scene.removeEventListener("pointerleave", onPointerLeave);
  };
}
"""

_MOLECULAR_SCENE = st.components.v2.component(
    "molecular_route_scene",
    html=_HTML,
    css=_CSS,
    js=_JS,
)


def mostrar_escena_molecular(
    origen: str,
    destino: str,
    *,
    ruta: tuple[str, ...] = (),
    costo: float | None = None,
    calculada: bool = False,
) -> None:
    """Renderiza una escena animada sin atribuir fórmulas a los nodos."""
    _MOLECULAR_SCENE(
        data={
            "source": origen,
            "destination": destino,
            "path": list(ruta),
            "cost": costo,
            "calculated": calculada,
        },
        height=340,
    )
