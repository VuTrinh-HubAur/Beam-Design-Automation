const pointLoadsEl = document.getElementById("point-loads");
const distLoadsEl = document.getElementById("distributed-loads");

function makeRow(fields) {
  const row = document.createElement("div");
  row.className = "row";
  row.innerHTML =
    fields.map((f) => `<input type="number" step="0.1" placeholder="${f}" data-key="${f}" />`).join("") +
    `<button type="button" class="remove">✕</button>`;
  row.querySelector(".remove").addEventListener("click", () => row.remove());
  return row;
}

function addPointLoad(mag = "", pos = "") {
  const row = makeRow(["magnitude", "position"]);
  row.querySelectorAll("input")[0].value = mag;
  row.querySelectorAll("input")[1].value = pos;
  pointLoadsEl.appendChild(row);
}

function addUdl(mag = "", start = "", end = "") {
  const row = makeRow(["magnitude", "start", "end"]);
  const inputs = row.querySelectorAll("input");
  inputs[0].value = mag;
  inputs[1].value = start;
  inputs[2].value = end;
  distLoadsEl.appendChild(row);
}

document.querySelectorAll("[data-add]").forEach((btn) => {
  btn.addEventListener("click", () => {
    if (btn.dataset.add === "point") addPointLoad();
    else addUdl();
  });
});

function collectRows(container, keys) {
  return Array.from(container.querySelectorAll(".row")).map((row) => {
    const obj = {};
    row.querySelectorAll("input").forEach((inp) => {
      obj[inp.dataset.key] = inp.value;
    });
    return obj;
  }).filter((o) => keys.every((k) => o[k] !== "" && o[k] !== undefined));
}

function stat(k, v) {
  return `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`;
}

document.getElementById("beam-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const statusEl = document.getElementById("status");
  statusEl.className = "status";
  statusEl.textContent = "Analysing…";

  const payload = {
    span: document.getElementById("span").value,
    allowable_stress_mpa: document.getElementById("allowable_stress_mpa").value,
    deflection_limit_ratio: document.getElementById("deflection_limit_ratio").value,
    youngs_modulus_gpa: document.getElementById("youngs_modulus_gpa").value,
    moment_of_inertia_cm4: document.getElementById("moment_of_inertia_cm4").value,
    point_loads: collectRows(pointLoadsEl, ["magnitude", "position"]),
    distributed_loads: collectRows(distLoadsEl, ["magnitude", "start", "end"]),
  };

  try {
    const res = await fetch("/api/design", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Request failed");
    render(data);
    statusEl.textContent = "Done.";
  } catch (err) {
    statusEl.className = "status error";
    statusEl.textContent = "Error: " + err.message;
  }
});

function render(data) {
  const a = data.analysis;
  const summary = document.getElementById("summary");
  summary.classList.remove("hidden");
  summary.innerHTML =
    stat("Reaction L", a.reaction_left + " kN") +
    stat("Reaction R", a.reaction_right + " kN") +
    stat("Max shear", a.max_shear + " kN") +
    stat("Max moment", a.max_moment + " kN·m") +
    stat("Max deflection", a.max_deflection_mm + " mm");

  const sel = document.getElementById("selected");
  sel.classList.remove("hidden");
  const s = data.selected_section;
  if (s) {
    sel.className = "selected pass";
    sel.innerHTML =
      `<h3>Selected section: ${s.section} <span class="badge ok">PASS</span></h3>` +
      `<div>Mass ${s.mass_per_m} kg/m · I ${s.inertia_cm4} cm⁴ · Z ${s.modulus_cm3} cm³</div>` +
      `<div class="util">` +
      `<span>Bending: ${s.bending_stress_mpa} MPa (util ${(s.bending_utilization * 100).toFixed(0)}%)</span>` +
      `<span>Deflection: ${s.max_deflection_mm} / ${s.deflection_limit_mm} mm (util ${(s.deflection_utilization * 100).toFixed(0)}%)</span>` +
      `</div>`;
  } else {
    sel.className = "selected fail";
    sel.innerHTML = `<h3>No library section is adequate <span class="badge bad">FAIL</span></h3>
      <div>Increase allowable stress, relax the deflection limit, or extend the section library.</div>`;
  }

  const diagrams = document.getElementById("diagrams");
  diagrams.classList.remove("hidden");
  document.getElementById("img-shear").src = data.diagrams.shear;
  document.getElementById("img-moment").src = data.diagrams.moment;
  document.getElementById("img-deflection").src = data.diagrams.deflection;

  const checksWrap = document.getElementById("checks-wrap");
  checksWrap.classList.remove("hidden");
  const rows = data.section_checks
    .map(
      (c) => `<tr class="${s && c.section === s.section ? "selected-row" : ""}">
        <td>${c.section}</td><td>${c.mass_per_m}</td>
        <td>${c.bending_stress_mpa}</td><td>${(c.bending_utilization * 100).toFixed(0)}%</td>
        <td>${c.max_deflection_mm}</td><td>${(c.deflection_utilization * 100).toFixed(0)}%</td>
        <td>${c.passes ? "✓" : "✗"}</td></tr>`
    )
    .join("");
  document.getElementById("checks").innerHTML =
    `<table><thead><tr>
      <th>Section</th><th>kg/m</th><th>σ MPa</th><th>σ util</th><th>δ mm</th><th>δ util</th><th>OK</th>
    </tr></thead><tbody>${rows}</tbody></table>`;
}

// Sensible starting example.
addUdl("15", "0", "6");
addPointLoad("40", "3");
