// Hero das páginas de curso: a mesma técnica do hero da Home (docs/technical/komuniki-particles.md),
// aplicada aos modelos de origami tsuru. Uma nuvem de triângulos que se remonta em loop entre um
// tsuru sozinho, uma guirlanda de quatro tsurus num barbante, e uma nuvem dispersa. Toda a animação
// mora no vertex shader: a CPU copia quatro buffers quando a forma troca e, fora isso, só escreve
// uniforms. Ao contrário da Home, esta caixa não fica atrás do texto do hero (tem sua própria coluna),
// então usa uma só camada de canvas, sem o corte frente/trás por normal de câmera que a Home precisa.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export const CONFIG = {
    count:       window.innerWidth < 720 ? 14000 : 28000,
    spread:      1.35,   // explosão no meio da transição
    drift:       0.028,  // respiração; 0 congela a forma
    speed:       0.42,   // progresso por segundo
    alphaTarget: 7,      // brilho global
    triMin:      0.019,
    triVar:      0.135,
    dwellSolid:  3.2,    // segundos parado nas formas sólidas
    dwellLoose:  1.8,    // segundos parado no disperso
    looseRadius: 3.7,    // raio da nuvem dispersa
};

const SHAPE_NAMES = ['tsuru', 'guirlanda', 'disperso'];
// A guirlanda tem 0,68% da área no barbante: ponderando só por área ele receberia ~190 de 28.000
// partículas espalhadas pela altura da cena e viraria uma linha pontilhada invisível.
const SHARES = { barbante: 0.06 };
// Inclinação da cena, usada como rotação inicial da nuvem e como base para medir o alfa "na vista"
// (etapa 5 do pipeline): as asas do tsuru são chapas planas que, vistas de frente, colapsam em
// linhas finas e cobririam quase nenhum pixel da grade de alfa.
const VIEW = { x: 0.45, y: -0.72 };
// ~0,0014 rad por quadro a 60 Hz, medido em segundos para não acelerar em telas de 120/144 Hz.
const ROTATION_PER_SECOND = 0.0014 * 60;
const REDUCED_MOTION_TIME_SCALE = 0.25;
const MAX_FRAME_DELTA = 0.05;
// Acima deste total de pixels de buffer, o pixel ratio cede para poupar memória de GPU.
const MAX_CANVAS_PIXELS = 1400000;

// Mesma paleta do hero da Home, para as duas nuvens de partículas do site lerem como o mesmo sistema.
// `ink` é a mesma partícula no tema claro: tons médios que aparecem tanto sobre o fundo claro quanto
// sobre o card do hero; o branco tem peso baixo de propósito, porque com blending aditivo ele satura
// a cena inteira rápido.
const PALETTE = [
    { rgb: [1.00, 0.70, 0.18], ink: '#d97706', weight: 34 }, // âmbar
    { rgb: [0.50, 0.31, 0.99], ink: '#7c3aed', weight: 24 }, // violeta
    { rgb: [0.15, 0.88, 0.74], ink: '#0d9488', weight: 17 }, // turquesa
    { rgb: [0.94, 0.38, 0.99], ink: '#c026d3', weight: 13 }, // magenta
    { rgb: [0.84, 0.88, 1.00], ink: '#0b3a75', weight: 12 }, // branco azulado
];

const VERTEX_SHADER = /* glsl */ `
// ---------- vertex ----------
attribute vec3 aFrom, aTo, aNormFrom, aNormTo, aColor, aColorInk, aBary;
attribute float aSeed, aScale;
uniform float uProgress, uTime, uSpread, uDrift, uAlphaFrom, uAlphaTo, uOcclusion, uInk;
varying vec3 vColor, vBary;
varying float vGlow, vAlpha;

void main() {
  // Atraso por partícula. Sem isto todas chegam juntas e fica robótico.
  float delay = aSeed * 0.42;
  float t = clamp((uProgress - delay) / 0.58, 0.0, 1.0);
  t = t * t * (3.0 - 2.0 * t);                       // smoothstep

  vec3 p = mix(aFrom, aTo, t);                       // O MORPH É ESTA LINHA

  // Arco: empurra para fora no meio do caminho. Sem isto as partículas
  // viajam em linha reta e some o momento de explosão.
  float arc = sin(t * 3.141592);
  vec3 dir  = normalize(mix(aFrom, aTo, 0.5) + vec3(1e-4));
  p += dir * arc * uSpread * (0.3 + aSeed * 1.3);

  // Respiração quase só durante a transição. Em repouso a forma fica
  // parada, e isso é metade da nitidez.
  p += vec3(sin(uTime * 0.35 + aSeed * 37.0),
            cos(uTime * 0.29 + aSeed * 23.0),
            sin(uTime * 0.24 + aSeed * 51.0)) * uDrift * (0.22 + arc * 0.78);

  vec4 mv = modelViewMatrix * vec4(p, 1.0);

  // OCLUSÃO POR NORMAL. Blending aditivo não tem teste de profundidade, então o verso e o
  // interior do papel somam por cima da frente e a silhueta vira um borrão. A faixa -0.35..0.02
  // mira só no que está de costas: uma faixa mais larga apaga junto as partículas de raspão,
  // que são justamente a silhueta.
  vec3 nm    = mix(aNormFrom, aNormTo, t);
  float hasN = min(1.0, length(nm) * 2.0);           // 0 = forma sem normal (nuvem dispersa)
  vec3 nv    = normalize(normalMatrix * (nm + vec3(0.0, 0.0, 1e-5)));
  float face = smoothstep(-0.35, 0.02, dot(nv, normalize(-mv.xyz)));
  float vis  = mix(1.0, mix(0.05, 1.0, face),
                   hasN * uOcclusion * (1.0 - arc * 0.85));

  // Billboard em espaço de visão com giro próprio. Triângulos pequenos
  // em repouso, grandes só no meio do voo.
  float ang = uTime * (0.25 + aSeed * 0.9) + aSeed * 60.0;
  float cs = cos(ang), sn = sin(ang);
  mv.xy += vec2(position.x * cs - position.y * sn,
                position.x * sn + position.y * cs) * aScale * (0.70 + arc * 1.30);

  // TEMA. No escuro vale a luz aditiva; no claro a partícula é tinta sobre o papel, na cor de
  // tinta da paleta e sem brilho extra (luz somada estouraria para branco sobre o fundo claro).
  vColor = mix(aColor, aColorInk, uInk);
  vBary  = aBary;
  vGlow  = mix(0.74 + arc * 0.80, 1.0, uInk);
  vAlpha = mix(uAlphaFrom, uAlphaTo, t) * (1.0 - arc * 0.35) * vis;
  gl_Position = projectionMatrix * mv;
}
`;

const FRAGMENT_SHADER = /* glsl */ `
// ---------- fragment ----------
varying vec3 vColor, vBary;
varying float vGlow, vAlpha;

void main() {
  // Distância até a aresta mais próxima: desenha só o contorno do triângulo
  float d = min(min(vBary.x, vBary.y), vBary.z);
  float edge = 1.0 - smoothstep(0.0, fwidth(d) * 1.05, d);
  if (edge * vAlpha < 0.004) discard;
  gl_FragColor = vec4(vColor * vGlow, edge * vAlpha);
  #include <colorspace_fragment>
}
`;

// Inverso radical em base 2 (van der Corput): metade de uma sequência de Hammersley, usada para
// amostrar cada triângulo com baixa discrepância (etapa 1 do pipeline).
function vanDerCorput2(index) {
    let bits = (index << 16) | (index >>> 16);
    bits = ((bits & 0x55555555) << 1) | ((bits & 0xAAAAAAAA) >>> 1);
    bits = ((bits & 0x33333333) << 2) | ((bits & 0xCCCCCCCC) >>> 2);
    bits = ((bits & 0x0F0F0F0F) << 4) | ((bits & 0xF0F0F0F0) >>> 4);
    bits = ((bits & 0x00FF00FF) << 8) | ((bits & 0xFF00FF00) >>> 8);
    return (bits >>> 0) * 2.3283064365386963e-10;
}

// Fisher-Yates em posições e normais juntas. A estratificação decide onde os pontos ficam;
// embaralhar decide qual partícula vai para onde. Sem isso, blocos inteiros viajam juntos na
// transição e some a sensação de enxame.
function shuffleTogether(positions, normals) {
    for (let i = positions.length / 3 - 1; i > 0; i--) {
        const j = (Math.random() * (i + 1)) | 0;
        for (let axis = 0; axis < 3; axis++) {
            const a = i * 3 + axis;
            const b = j * 3 + axis;
            let swap = positions[a];
            positions[a] = positions[b];
            positions[b] = swap;
            swap = normals[a];
            normals[a] = normals[b];
            normals[b] = swap;
        }
    }
}

// Carrega um .glb preservando uma geometria POR MALHA nomeada (não uma sopa mesclada): a guirlanda
// precisa saber qual sopa de triângulos é "barbante" para lhe dar o piso da etapa 3. Cada posição já
// sai em espaço de mundo (child.matrixWorld aplicado), então os dois arquivos entram na mesma escala
// sem normalização extra — vêm "já centrados e escalados" um em relação ao outro.
async function loadNamedParts(url) {
    const gltf = await new GLTFLoader().loadAsync(url);
    gltf.scene.updateMatrixWorld(true);
    const parts = [];
    const vertex = new THREE.Vector3();
    gltf.scene.traverse((child) => {
        if (!child.isMesh) {
            return;
        }
        const position = child.geometry.getAttribute('position');
        const index = child.geometry.getIndex();
        const vertexCount = index ? index.count : position.count;
        const chunk = new Float32Array(vertexCount * 3);
        for (let i = 0; i < vertexCount; i++) {
            vertex.fromBufferAttribute(position, index ? index.getX(i) : i);
            vertex.applyMatrix4(child.matrixWorld).toArray(chunk, i * 3);
        }
        parts.push({ name: child.name, positions: chunk });
        child.geometry.dispose();
        for (const material of [child.material].flat()) {
            material?.dispose();
        }
    });
    if (parts.length === 0) {
        throw new Error(`Nenhuma malha em ${url}.`);
    }
    return parts;
}

function surfaceArea(positions) {
    const a = new THREE.Vector3();
    const b = new THREE.Vector3();
    const c = new THREE.Vector3();
    const ab = new THREE.Vector3();
    const ac = new THREE.Vector3();
    const normal = new THREE.Vector3();
    const triangles = positions.length / 9;
    let total = 0;
    for (let i = 0; i < triangles; i++) {
        a.fromArray(positions, i * 9);
        b.fromArray(positions, i * 9 + 3);
        c.fromArray(positions, i * 9 + 6);
        normal.crossVectors(ab.subVectors(b, a), ac.subVectors(c, a));
        total += normal.length() * 0.5;
    }
    return total;
}

// Nuvem de exatamente `count` pontos na superfície de UM part, com a normal do triângulo de
// origem: ponderada por área, estratificada (cada partícula pega uma fatia igual da área total) e
// com baixa discrepância dentro do triângulo (etapa 1 do pipeline).
function samplePart(positions, count) {
    if (count <= 0) {
        return { positions: new Float32Array(0), normals: new Float32Array(0) };
    }
    const triangles = positions.length / 9;
    const cumulativeArea = new Float64Array(triangles);
    const faceNormals = new Float32Array(triangles * 3);
    const a = new THREE.Vector3();
    const b = new THREE.Vector3();
    const c = new THREE.Vector3();
    const ab = new THREE.Vector3();
    const ac = new THREE.Vector3();
    const normal = new THREE.Vector3();
    let totalArea = 0;
    for (let i = 0; i < triangles; i++) {
        a.fromArray(positions, i * 9);
        b.fromArray(positions, i * 9 + 3);
        c.fromArray(positions, i * 9 + 6);
        normal.crossVectors(ab.subVectors(b, a), ac.subVectors(c, a));
        const length = normal.length();
        totalArea += length * 0.5;
        cumulativeArea[i] = totalArea;
        if (length > 1e-12) {
            normal.divideScalar(length).toArray(faceNormals, i * 3);
        }
    }

    const outPositions = new Float32Array(count * 3);
    const outNormals = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
        const target = ((i + 0.5) / count) * totalArea;
        let low = 0;
        let high = triangles - 1;
        while (low < high) {
            const middle = (low + high) >> 1;
            if (cumulativeArea[middle] < target) {
                low = middle + 1;
            } else {
                high = middle;
            }
        }
        let u = vanDerCorput2(i);
        let v = (i * 0.6180339887498949) % 1;
        if (u + v > 1) { u = 1 - u; v = 1 - v; }
        a.fromArray(positions, low * 9);
        b.fromArray(positions, low * 9 + 3);
        c.fromArray(positions, low * 9 + 6);
        for (let axis = 0; axis < 3; axis++) {
            const origin = a.getComponent(axis);
            outPositions[i * 3 + axis] = origin + u * (b.getComponent(axis) - origin) + v * (c.getComponent(axis) - origin);
            outNormals[i * 3 + axis] = faceNormals[low * 3 + axis];
        }
    }
    return { positions: outPositions, normals: outNormals };
}

// Etapa 3 do pipeline: piso explícito de partículas por nome de malha (`shares`), o resto
// distribuído por área entre as demais. A última parte fecha em `count` exato (arredondamento).
function sampleParts(parts, count, shares) {
    const areas = parts.map((p) => surfaceArea(p.positions));
    let fixedShare = 0;
    let freeArea = 0;
    parts.forEach((p, i) => {
        if (shares[p.name] != null) {
            fixedShare += shares[p.name];
        } else {
            freeArea += areas[i];
        }
    });
    const share = parts.map((p, i) => (shares[p.name] != null ? shares[p.name] : ((1 - fixedShare) * areas[i]) / freeArea));

    const outPositions = new Float32Array(count * 3);
    const outNormals = new Float32Array(count * 3);
    let written = 0;
    parts.forEach((p, i) => {
        const isLast = i === parts.length - 1;
        const partCount = isLast ? count - written : Math.round(count * share[i]);
        const { positions, normals } = samplePart(p.positions, partCount);
        outPositions.set(positions, written * 3);
        outNormals.set(normals, written * 3);
        written += partCount;
    });
    shuffleTogether(outPositions, outNormals);
    return { positions: outPositions, normals: outNormals };
}

// Volume uniforme numa esfera. Normais zeradas: o shader trata comprimento zero como "sem
// normal" e não aplica oclusão.
function buildScattered(count, radius) {
    const positions = new Float32Array(count * 3);
    const normals = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
        const theta = Math.acos(2 * Math.random() - 1);
        const phi = Math.random() * Math.PI * 2;
        const r = radius * Math.cbrt(Math.random());
        positions[i * 3] = r * Math.sin(theta) * Math.cos(phi);
        positions[i * 3 + 1] = r * Math.sin(theta) * Math.sin(phi);
        positions[i * 3 + 2] = r * Math.cos(theta);
    }
    return { positions, normals };
}

// Etapa 5: alfa automático medido NA VISTA, não no plano XY do modelo. As asas do tsuru são
// chapas planas que, vistas de frente, viram linhas finas e cobrem quase nenhum pixel; medir no
// plano do modelo subestima o alfa pela metade. Projeta cada ponto na orientação de VIEW antes de
// rasterizar numa grade 64×64 e conta células ocupadas.
function autoAlpha(positions, hasNormals, alphaTarget, view) {
    const cx = Math.cos(view.x);
    const sx = Math.sin(view.x);
    const cy = Math.cos(view.y);
    const sy = Math.sin(view.y);
    const grid = 64;
    const occupied = new Uint8Array(grid * grid);
    const viewX = new Float32Array(positions.length / 3);
    const viewY = new Float32Array(positions.length / 3);
    let extent = 1e-6;
    for (let i = 0, p = 0; i < positions.length; i += 3, p++) {
        const px = positions[i];
        const py = positions[i + 1];
        const pz = positions[i + 2];
        // Y primeiro, depois X: é a ordem do Euler 'XYZ' do three.js, a mesma de VIEW.
        const x1 = px * cy + pz * sy;
        const z1 = -px * sy + pz * cy;
        const y1 = py * cx - z1 * sx;
        viewX[p] = x1;
        viewY[p] = y1;
        extent = Math.max(extent, Math.abs(x1), Math.abs(y1));
    }
    let cells = 0;
    for (let p = 0; p < viewX.length; p++) {
        const gx = (((viewX[p] / extent) * 0.5 + 0.5) * (grid - 1)) | 0;
        const gy = (((viewY[p] / extent) * 0.5 + 0.5) * (grid - 1)) | 0;
        const cell = gy * grid + gx;
        if (occupied[cell] === 0) {
            occupied[cell] = 1;
            cells++;
        }
    }
    const perCell = ((hasNormals ? 0.45 : 1) * (positions.length / 3)) / cells;
    return THREE.MathUtils.clamp(alphaTarget / perCell, 0.15, 1.0);
}

function createShape({ positions, normals }, hasNormals, dwell, alphaTarget) {
    return { positions, normals, dwell, alpha: autoAlpha(positions, hasNormals, alphaTarget, VIEW) };
}

function pickPaletteEntry(totalWeight) {
    let pick = Math.random() * totalWeight;
    for (const entry of PALETTE) {
        pick -= entry.weight;
        if (pick <= 0) {
            return entry;
        }
    }
    return PALETTE[0];
}

// Um triângulo desenhado N vezes: uma única chamada de draw para a nuvem inteira.
function buildCloudGeometry(shape, count, config) {
    const geometry = new THREE.InstancedBufferGeometry();
    geometry.instanceCount = count;
    geometry.setAttribute('position', new THREE.Float32BufferAttribute([0, 0.58, 0, -0.50, -0.29, 0, 0.50, -0.29, 0], 3));
    geometry.setAttribute('aBary', new THREE.Float32BufferAttribute([1, 0, 0, 0, 1, 0, 0, 0, 1], 3));

    const morph = {
        aFrom: new THREE.InstancedBufferAttribute(shape.positions.slice(), 3),
        aTo: new THREE.InstancedBufferAttribute(shape.positions.slice(), 3),
        aNormFrom: new THREE.InstancedBufferAttribute(shape.normals.slice(), 3),
        aNormTo: new THREE.InstancedBufferAttribute(shape.normals.slice(), 3),
    };
    for (const [name, attribute] of Object.entries(morph)) {
        geometry.setAttribute(name, attribute.setUsage(THREE.DynamicDrawUsage));
    }

    const colors = new Float32Array(count * 3);
    const inkColors = new Float32Array(count * 3);
    const seeds = new Float32Array(count);
    const scales = new Float32Array(count);
    const totalWeight = PALETTE.reduce((total, entry) => total + entry.weight, 0);
    const inks = new Map(PALETTE.map((entry) => [entry, new THREE.Color(entry.ink).toArray()]));
    for (let i = 0; i < count; i++) {
        const entry = pickPaletteEntry(totalWeight);
        colors.set(entry.rgb, i * 3);
        inkColors.set(inks.get(entry), i * 3);
        seeds[i] = Math.random();
        // O expoente 4.5 concentra quase tudo nos triângulos pequenos e deixa poucos grandes,
        // que é o que dá profundidade.
        scales[i] = config.triMin + Math.pow(Math.random(), 4.5) * config.triVar;
    }
    geometry.setAttribute('aColor', new THREE.InstancedBufferAttribute(colors, 3));
    geometry.setAttribute('aColorInk', new THREE.InstancedBufferAttribute(inkColors, 3));
    geometry.setAttribute('aSeed', new THREE.InstancedBufferAttribute(seeds, 1));
    geometry.setAttribute('aScale', new THREE.InstancedBufferAttribute(scales, 1));
    return { geometry, morph };
}

export async function mountParticles(container, { tsuruUrl, garlandUrl, config: overrides = {} } = {}) {
    const config = { ...CONFIG, ...overrides };
    const count = config.count;
    const [tsuruParts, garlandParts] = await Promise.all([loadNamedParts(tsuruUrl), loadNamedParts(garlandUrl)]);
    // Toda forma tem o mesmo N: a partícula nº 7.412 do tsuru é a nº 7.412 da guirlanda.
    const shapes = [
        createShape(sampleParts(tsuruParts, count, {}), true, config.dwellSolid, config.alphaTarget),
        createShape(sampleParts(garlandParts, count, SHARES), true, config.dwellSolid, config.alphaTarget),
        createShape(buildScattered(count, config.looseRadius), false, config.dwellLoose, config.alphaTarget),
    ];

    const { geometry, morph } = buildCloudGeometry(shapes[0], count, config);
    const material = new THREE.ShaderMaterial({
        uniforms: {
            uProgress: { value: 1 },
            uTime: { value: 0 },
            uSpread: { value: config.spread },
            uDrift: { value: config.drift },
            uAlphaFrom: { value: shapes[0].alpha },
            uAlphaTo: { value: shapes[0].alpha },
            uOcclusion: { value: 1 },
            uInk: { value: 0 },
        },
        vertexShader: VERTEX_SHADER,
        fragmentShader: FRAGMENT_SHADER,
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
    });
    const uniforms = material.uniforms;
    const cloud = new THREE.Mesh(geometry, material);
    // A bounding sphere é a do triângulo base, minúscula: sem isto a nuvem some da tela.
    cloud.frustumCulled = false;
    cloud.rotation.set(VIEW.x, VIEW.y, 0);
    const scene = new THREE.Scene();
    scene.add(cloud);
    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
    camera.position.z = 11;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setClearColor(0x000000, 0);
    renderer.domElement.className = 'ed-course-particles-canvas';
    renderer.domElement.setAttribute('aria-hidden', 'true');
    container.appendChild(renderer.domElement);

    let layoutKey = '';
    const syncLayout = () => {
        const rect = container.getBoundingClientRect();
        const width = Math.max(1, Math.round(rect.width));
        const height = Math.max(1, Math.round(rect.height));
        const ratio = Math.min(window.devicePixelRatio, 2, Math.sqrt(MAX_CANVAS_PIXELS / (width * height)));
        const key = `${width}|${height}|${ratio}`;
        if (key === layoutKey) {
            return;
        }
        layoutKey = key;
        renderer.setPixelRatio(ratio);
        renderer.setSize(width, height, false);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
    };

    // A luz soma sobre o preto do tema escuro. Sobre o fundo claro ela estouraria para branco,
    // então ali a partícula vira tinta que cobre o que está embaixo.
    const syncTheme = () => {
        const ink = !document.documentElement.classList.contains('dark');
        uniforms.uInk.value = ink ? 1 : 0;
        material.blending = ink ? THREE.NormalBlending : THREE.AdditiveBlending;
    };

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const timer = new THREE.Timer();
    timer.connect(document);
    let current = 0;
    let target = 0;
    let morphing = false;
    let dwellLeft = shapes[0].dwell;
    let time = 0;
    let frames = 0;
    let frameId = 0;

    // Trocar de forma = quatro cópias de buffer e needsUpdate. Depois disso a CPU não toca em
    // nenhum buffer: o loop só escreve uniforms e a rotação.
    const setMorph = (from, to) => {
        morph.aFrom.array.set(shapes[from].positions);
        morph.aTo.array.set(shapes[to].positions);
        morph.aNormFrom.array.set(shapes[from].normals);
        morph.aNormTo.array.set(shapes[to].normals);
        for (const attribute of Object.values(morph)) {
            attribute.needsUpdate = true;
        }
        uniforms.uAlphaFrom.value = shapes[from].alpha;
        uniforms.uAlphaTo.value = shapes[to].alpha;
    };

    const applyMotionPreference = () => {
        if (reducedMotion.matches) {
            // Sem ciclo: o tsuru parado, na inclinação de VIEW.
            setMorph(0, 0);
            current = 0;
            target = 0;
            morphing = false;
            uniforms.uProgress.value = 1;
            cloud.rotation.set(VIEW.x, VIEW.y, 0);
        }
        dwellLeft = shapes[current].dwell;
    };

    const renderFrame = () => {
        frameId = requestAnimationFrame(renderFrame);
        timer.update();
        const delta = Math.min(timer.getDelta(), MAX_FRAME_DELTA);
        if (reducedMotion.matches) {
            time += delta * REDUCED_MOTION_TIME_SCALE;
        } else {
            time += delta;
            if (morphing) {
                uniforms.uProgress.value = Math.min(1, uniforms.uProgress.value + delta * config.speed);
                if (uniforms.uProgress.value === 1) {
                    morphing = false;
                    current = target;
                    dwellLeft = shapes[current].dwell;
                }
            } else {
                dwellLeft -= delta;
                if (dwellLeft <= 0) {
                    // Ciclo: tsuru → guirlanda → disperso → tsuru → …
                    target = (current + 1) % shapes.length;
                    setMorph(current, target);
                    uniforms.uProgress.value = 0;
                    morphing = true;
                }
            }
            cloud.rotation.y += ROTATION_PER_SECOND * delta;
        }
        syncLayout();
        uniforms.uTime.value = time;
        renderer.render(scene, camera);
        frames++;
        if (frames === 1) {
            announceReady(container);
        }
    };

    const start = () => {
        if (frameId === 0) {
            timer.reset();
            frameId = requestAnimationFrame(renderFrame);
        }
    };
    const stop = () => {
        cancelAnimationFrame(frameId);
        frameId = 0;
    };

    // É fundo de página: nada renderiza enquanto a caixa está fora da viewport.
    const intersectionObserver = new IntersectionObserver((entries) => {
        if (entries[entries.length - 1].isIntersecting) {
            start();
        } else {
            stop();
            announceReady(container);
        }
    });
    const themeObserver = new MutationObserver(syncTheme);
    syncTheme();
    applyMotionPreference();
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    reducedMotion.addEventListener('change', applyMotionPreference);
    intersectionObserver.observe(container);

    const dispose = () => {
        stop();
        intersectionObserver.disconnect();
        themeObserver.disconnect();
        reducedMotion.removeEventListener('change', applyMotionPreference);
        timer.dispose();
        geometry.dispose();
        material.dispose();
        renderer.dispose();
        renderer.domElement.remove();
    };

    return {
        renderer,
        dispose,
        get state() {
            return {
                shape: SHAPE_NAMES[current],
                target: SHAPE_NAMES[target],
                morphing,
                progress: uniforms.uProgress.value,
                frames,
                running: frameId !== 0,
                reducedMotion: reducedMotion.matches,
                theme: uniforms.uInk.value === 1 ? 'claro' : 'escuro',
                drawCalls: renderer.info.render.calls,
                count,
            };
        },
    };
}

// O módulo da página (js/school-editorial.js) só mostra a página depois deste aviso: o primeiro
// quadro desenhado, a caixa fora da tela ou a falha da montagem.
function announceReady(element) {
    if (!('particlesReady' in element.dataset)) {
        element.dataset.particlesReady = '';
        element.dispatchEvent(new CustomEvent('komuniki:particles-ready'));
    }
}

async function mountFromDataset(element) {
    const { tsuruUrl, garlandUrl, config } = element.dataset;
    const handle = await mountParticles(element, { tsuruUrl, garlandUrl, config: config ? JSON.parse(config) : {} });
    element.addEventListener('htmx:beforeCleanupElement', handle.dispose, { once: true });
    if ('particlesDebug' in element.dataset) {
        window.komunikiTsuruParticles = handle;
    }
}

for (const element of document.querySelectorAll('[data-particles-tsuru]')) {
    mountFromDataset(element).catch((error) => {
        announceReady(element);
        console.error('Partículas de curso indisponíveis:', error);
    });
}
