const tools = {
  losa: {
    title: "Losa maciza",
    resultTitle: "Espesor recomendado",
    primaryUnit: "cm",
    fields: [
      { id: "lx", label: "Luz corta", unit: "m", value: 4.2, min: 1, step: 0.1 },
      { id: "ly", label: "Luz larga", unit: "m", value: 5.4, min: 1, step: 0.1 },
      {
        id: "support",
        label: "Condicion de apoyo",
        type: "select",
        value: "continua",
        options: [
          ["simple", "Simplemente apoyada"],
          ["continua", "Continua"],
          ["voladizo", "Voladizo"]
        ]
      },
      { id: "load", label: "Carga de servicio", unit: "kN/m2", value: 7.5, min: 0, step: 0.1 },
      { id: "cover", label: "Recubrimiento", unit: "cm", value: 2.5, min: 1, step: 0.5 }
    ],
    calculate(values) {
      const shortSpan = Number(values.lx);
      const longSpan = Number(values.ly);
      const ratio = longSpan / shortSpan;
      const twoWay = ratio <= 2;
      const divisorMap = { simple: twoWay ? 30 : 24, continua: twoWay ? 36 : 28, voladizo: 10 };
      const divisor = divisorMap[values.support];
      const thickness = roundUp(Math.max((shortSpan * 100) / divisor, 10), 1);
      const selfWeight = round(thickness / 100 * 24, 2);
      const totalService = round(selfWeight + Number(values.load), 2);

      return {
        primary: thickness,
        unit: "cm",
        metrics: [
          ["Sistema", twoWay ? "Bidireccional" : "Unidireccional"],
          ["Relacion Ly/Lx", ratio.toFixed(2)],
          ["Peso propio estimado", `${selfWeight} kN/m2`],
          ["Carga total preliminar", `${totalService} kN/m2`],
          ["Peralte util aproximado", `${round(thickness - Number(values.cover), 1)} cm`]
        ],
        criteria:
          "Estimacion por control de esbeltez en etapa preliminar. Ajusta el espesor final verificando flechas, punzonamiento, cuantias minimas y combinaciones de carga segun la norma que uses."
      };
    }
  },
  viga: {
    title: "Viga rectangular",
    resultTitle: "Altura recomendada",
    primaryUnit: "cm",
    fields: [
      { id: "span", label: "Luz libre", unit: "m", value: 5.8, min: 1, step: 0.1 },
      {
        id: "support",
        label: "Condicion de apoyo",
        type: "select",
        value: "continua",
        options: [
          ["simple", "Simplemente apoyada"],
          ["continua", "Continua"],
          ["voladizo", "Voladizo"]
        ]
      },
      { id: "width", label: "Ancho inicial", unit: "cm", value: 25, min: 15, step: 1 },
      { id: "tributary", label: "Ancho tributario", unit: "m", value: 3.2, min: 0.5, step: 0.1 },
      { id: "slabLoad", label: "Carga de losa", unit: "kN/m2", value: 8, min: 0, step: 0.1 }
    ],
    calculate(values) {
      const span = Number(values.span);
      const divisor = { simple: 12, continua: 15, voladizo: 7 }[values.support];
      const height = roundUp(Math.max((span * 100) / divisor, Number(values.width) * 1.8), 5);
      const width = roundUp(Math.max(Number(values.width), height / 3), 5);
      const lineLoad = round(Number(values.tributary) * Number(values.slabLoad) + width / 100 * height / 100 * 24, 2);

      return {
        primary: height,
        unit: "cm",
        metrics: [
          ["Ancho sugerido", `${width} cm`],
          ["Relacion h/L", `1/${round((span * 100) / height, 1)}`],
          ["Carga lineal preliminar", `${lineLoad} kN/m`],
          ["Peralte util inicial", `${round(height - 5, 1)} cm`]
        ],
        criteria:
          "Predimensionamiento por relaciones luz/peralte habituales para vigas de hormigon armado. El diseno definitivo debe verificar flexion, corte, deformaciones, anclajes y confinamiento."
      };
    }
  },
  columna: {
    title: "Columna",
    resultTitle: "Lado minimo sugerido",
    primaryUnit: "cm",
    fields: [
      { id: "axial", label: "Carga axial mayorada", unit: "kN", value: 950, min: 1, step: 10 },
      { id: "floors", label: "Niveles que soporta", unit: "", value: 3, min: 1, step: 1 },
      { id: "fc", label: "Resistencia f'c", unit: "MPa", value: 21, min: 15, step: 1 },
      { id: "steelRatio", label: "Cuantia estimada", unit: "%", value: 1.5, min: 1, step: 0.1 },
      {
        id: "shape",
        label: "Seccion",
        type: "select",
        value: "cuadrada",
        options: [
          ["cuadrada", "Cuadrada"],
          ["rectangular", "Rectangular"]
        ]
      }
    ],
    calculate(values) {
      const axial = Number(values.axial);
      const fc = Number(values.fc) * 1000;
      const steelRatio = Number(values.steelRatio) / 100;
      const nominalStress = 0.35 * fc * (1 + steelRatio * 6);
      const areaM2 = axial / nominalStress;
      const areaCm2 = areaM2 * 10000;
      const side = roundUp(Math.max(Math.sqrt(areaCm2), 25), 5);
      const rectangularB = values.shape === "rectangular" ? roundUp(Math.max(side * 0.8, 25), 5) : side;
      const rectangularH = values.shape === "rectangular" ? roundUp(areaCm2 / rectangularB, 5) : side;

      return {
        primary: values.shape === "rectangular" ? rectangularH : side,
        unit: "cm",
        metrics: [
          ["Area requerida", `${round(areaCm2, 0)} cm2`],
          ["Seccion sugerida", values.shape === "rectangular" ? `${rectangularB} x ${rectangularH} cm` : `${side} x ${side} cm`],
          ["Cuantia inicial", `${Number(values.steelRatio).toFixed(1)} %`],
          ["Niveles considerados", `${Number(values.floors)}`]
        ],
        criteria:
          "Estimacion de area bruta por capacidad axial preliminar. El dimensionamiento final requiere revisar esbeltez, momentos, interaccion P-M, confinamiento, separacion de barras y efectos sismicos."
      };
    }
  },
  zapata: {
    title: "Zapata aislada",
    resultTitle: "Lado de zapata",
    primaryUnit: "m",
    fields: [
      { id: "serviceLoad", label: "Carga de servicio", unit: "kN", value: 820, min: 1, step: 10 },
      { id: "soil", label: "Capacidad admisible suelo", unit: "kPa", value: 180, min: 20, step: 5 },
      { id: "colB", label: "Columna b", unit: "cm", value: 30, min: 20, step: 1 },
      { id: "colH", label: "Columna h", unit: "cm", value: 30, min: 20, step: 1 },
      { id: "thickness", label: "Peralte inicial", unit: "cm", value: 45, min: 20, step: 5 }
    ],
    calculate(values) {
      const load = Number(values.serviceLoad);
      const soil = Number(values.soil);
      const area = load / soil * 1.1;
      const side = roundUp(Math.sqrt(area), 0.05);
      const pressure = round(load / (side * side), 2);
      const projectionB = round((side - Number(values.colB) / 100) / 2, 2);
      const projectionH = round((side - Number(values.colH) / 100) / 2, 2);

      return {
        primary: side.toFixed(2),
        unit: "m",
        metrics: [
          ["Area requerida", `${round(area, 2)} m2`],
          ["Presion de trabajo", `${pressure} kPa`],
          ["Vuelo en b", `${projectionB} m`],
          ["Vuelo en h", `${projectionH} m`],
          ["Peralte inicial", `${Number(values.thickness)} cm`]
        ],
        criteria:
          "Area preliminar por presion admisible del suelo con 10% adicional por peso propio. Verifica corte unidireccional, punzonamiento, asentamientos, flexion y recubrimientos antes de construir."
      };
    }
  }
};

const state = {
  tool: "losa",
  values: {}
};

const toolTitle = document.querySelector("#toolTitle");
const resultTitle = document.querySelector("#resultTitle");
const primaryValue = document.querySelector("#primaryValue");
const primaryUnit = document.querySelector("#primaryUnit");
const resultList = document.querySelector("#resultList");
const criteriaText = document.querySelector("#criteriaText");
const inputsGrid = document.querySelector("#inputsGrid");
const resetButton = document.querySelector("#resetButton");
const tabs = document.querySelectorAll(".tab-button");

function renderInputs() {
  const tool = tools[state.tool];
  toolTitle.textContent = tool.title;
  resultTitle.textContent = tool.resultTitle;
  inputsGrid.innerHTML = "";

  tool.fields.forEach((field) => {
    if (!(field.id in state.values)) {
      state.values[field.id] = field.value;
    }

    const wrapper = document.createElement("label");
    wrapper.className = "field";
    wrapper.htmlFor = field.id;

    const label = document.createElement("span");
    label.textContent = field.unit ? `${field.label} (${field.unit})` : field.label;
    wrapper.appendChild(label);

    const control = field.type === "select" ? document.createElement("select") : document.createElement("input");
    control.id = field.id;
    control.name = field.id;

    if (field.type === "select") {
      field.options.forEach(([value, text]) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = text;
        control.appendChild(option);
      });
    } else {
      control.type = "number";
      control.min = field.min;
      control.step = field.step;
    }

    control.value = state.values[field.id];
    control.addEventListener("input", () => {
      state.values[field.id] = control.value;
      calculateAndRender();
    });

    wrapper.appendChild(control);

    if (field.unit) {
      const hint = document.createElement("p");
      hint.className = "hint";
      hint.textContent = `Ingresa el valor en ${field.unit}.`;
      wrapper.appendChild(hint);
    }

    inputsGrid.appendChild(wrapper);
  });
}

function calculateAndRender() {
  const tool = tools[state.tool];
  const result = tool.calculate(state.values);
  primaryValue.textContent = result.primary;
  primaryUnit.textContent = result.unit;
  criteriaText.textContent = result.criteria;
  resultList.innerHTML = "";

  result.metrics.forEach(([label, value]) => {
    const row = document.createElement("div");
    row.className = "metric";
    row.innerHTML = `<span>${label}</span><strong>${value}</strong>`;
    resultList.appendChild(row);
  });
}

function switchTool(toolId) {
  state.tool = toolId;
  state.values = {};
  tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.tool === toolId));
  renderInputs();
  calculateAndRender();
}

function round(value, digits) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function roundUp(value, step) {
  return Math.ceil(value / step) * step;
}

tabs.forEach((tab) => {
  tab.addEventListener("click", () => switchTool(tab.dataset.tool));
});

resetButton.addEventListener("click", () => switchTool(state.tool));

renderInputs();
calculateAndRender();
