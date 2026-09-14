// Hero da Home da Komuniki: uma nuvem de triângulos que se remonta em microfone,
// Terra e nuvem dispersa, em loop automático. Toda a animação mora no vertex shader:
// a CPU copia quatro buffers quando a forma troca e, fora isso, só escreve uniforms.
// A nuvem é desenhada em duas camadas transparentes que cobrem o hero inteiro, uma atrás
// e outra na frente do texto. Parâmetros e validação: docs/technical/komuniki-particles.md.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export const CONFIG = {
    count:       window.innerWidth < 720 ? 9000 : 16000,
    spread:      1.35,   // explosão no meio da transição
    burstSpread: 3.2,    // explosão do microfone para a Terra; espalha pela tela como a nuvem
    drift:       0.030,  // respiração; 0 congela a forma
    speed:       0.42,   // progresso por segundo
    alphaTarget: 7,      // brilho global
    triMin:      0.020,
    triVar:      0.150,
    oceanKeep:   0.15,   // densidade do oceano vs continente
    dwellSolid:  3.4,    // segundos parado nas formas sólidas
    dwellLoose:  1.6,    // segundos parado no disperso
    looseRadius: 6.2,    // raio da nuvem dispersa; maior avança por baixo e por cima do título
};

const SHAPE_NAMES = ['microfone', 'terra', 'disperso'];
const MIC_RADIUS = 2.9;
const EARTH_RADIUS = 2.62;
// ~0,0016 rad por quadro a 60 Hz, medido em segundos para não acelerar em telas de 120/144 Hz.
const ROTATION_PER_SECOND = 0.0016 * 60;
// prefers-reduced-motion: sem ciclo nem rotação, e a deriva anda a um quarto da velocidade.
const REDUCED_MOTION_TIME_SCALE = 0.25;
// Um quadro lento, ou a volta de uma aba em segundo plano, não faz a animação saltar.
const MAX_FRAME_DELTA = 0.05;
// Arrastar com mouse ou toque gira a forma. Ao soltar, a inércia se dissolve na rotação
// automática e a inclinação volta aos poucos para a vista de frente.
const DRAG_RADIANS_PER_PIXEL = 0.006;
const MAX_TILT = 0.6;
const MAX_SPIN = 6;
const SPIN_DAMPING = 2.2;
const TILT_RETURN = 1.2;
// As camadas cobrem o hero inteiro e cada uma tem antialias: acima deste total de pixels
// de buffer por camada, o pixel ratio cede para poupar memória de GPU.
const MAX_LAYER_PIXELS = 2600000;

// O branco tem peso baixo de propósito: com blending aditivo ele satura a cena inteira rápido.
// `ink` é a mesma partícula no tema claro, como tinta: tons médios que aparecem tanto sobre o
// fundo claro quanto sobre as letras pretas do título; o branco azulado vira o azul da Komuniki.
const PALETTE = [
    { rgb: [1.00, 0.70, 0.18], ink: '#d97706', weight: 34 }, // âmbar
    { rgb: [0.50, 0.31, 0.99], ink: '#7c3aed', weight: 24 }, // violeta
    { rgb: [0.15, 0.88, 0.74], ink: '#0d9488', weight: 17 }, // turquesa
    { rgb: [0.94, 0.38, 0.99], ink: '#c026d3', weight: 13 }, // magenta
    { rgb: [0.84, 0.88, 1.00], ink: '#0b3a75', weight: 12 }, // branco azulado
];

const VERTEX_SHADER = /* glsl */ `
// ---------- vertex ----------
attribute vec3 aFrom, aTo, aNormFrom, aNormTo, aColor, aBary;
attribute vec3 aColorInk;
attribute float aSeed, aScale;
uniform float uProgress, uTime, uSpread, uDrift, uAlphaFrom, uAlphaTo, uOcclusion;
uniform float uLayer, uInk;
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

  // CAMADAS. A nuvem é desenhada em dois canvases, um atrás e outro na frente
  // do texto do hero. Cada partícula pertence ao lado do plano que passa pelo
  // centro da forma; perto dele as duas camadas se cruzam suavemente, então
  // nada pisca quando a rotação leva a partícula de um lado para o outro.
  float centerZ = (modelViewMatrix * vec4(0.0, 0.0, 0.0, 1.0)).z;
  float front   = smoothstep(-0.35, 0.35, mv.z - centerZ);
  float layer   = mix(1.0 - front, front, uLayer);

  // OCLUSÃO POR NORMAL. Blending aditivo não tem teste de profundidade,
  // então o verso e o interior do modelo somam por cima da frente e a
  // silhueta vira um borrão branco. Neste microfone são 38% da área.
  // A faixa -0.35..0.02 mira só no que está de costas: uma faixa mais
  // larga apaga junto as partículas de raspão, que são a silhueta.
  vec3 nm    = mix(aNormFrom, aNormTo, t);
  float hasN = min(1.0, length(nm) * 2.0);           // 0 = forma sem normal
  vec3 nv    = normalize(normalMatrix * (nm + vec3(0.0, 0.0, 1e-5)));
  float face = smoothstep(-0.35, 0.02, dot(nv, normalize(-mv.xyz)));
  float vis  = mix(1.0, mix(0.05, 1.0, face),
                   hasN * uOcclusion * (1.0 - arc * 0.85));

  // Billboard em espaço de visão, com giro próprio. Triângulos pequenos
  // em repouso, grandes só no meio do voo.
  float ang = uTime * (0.25 + aSeed * 0.9) + aSeed * 60.0;
  float s = sin(ang), c = cos(ang);
  mv.xy += vec2(position.x * c - position.y * s,
                position.x * s + position.y * c) * aScale * (0.70 + arc * 1.30);

  // TEMA. No escuro a luz soma e brilha mais no meio do voo; no claro a
  // partícula é tinta sobre o papel, na cor de tinta da paleta e sem brilho extra.
  vColor = mix(aColor, aColorInk, uInk);
  vBary  = aBary;
  vGlow  = mix(0.62 + arc * 0.85, 1.0, uInk);
  vAlpha = mix(uAlphaFrom, uAlphaTo, t) * (1.0 - arc * 0.35) * vis * layer;
  // Fora desta camada o triângulo vai para fora do recorte e nem é rasterizado.
  gl_Position = layer < 0.002 ? vec4(2.0, 2.0, 2.0, 1.0) : projectionMatrix * mv;
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

// Máscara de terra firme do Natural Earth 110m: equiretangular, 1 bit por pixel,
// MSB-first, row-major. Linha 0 = latitude +90; coluna 0 = longitude -180.
// atan2(x, z), e não atan2(z, x): Greenwich, com a África, começa virado para a câmera.
const LW = 640, LH = 320;
function isLand(mask, x, y, z) {
    const lon = Math.atan2(x, z);                              // -PI..PI
    const lat = Math.asin(Math.max(-1, Math.min(1, y)));       // -PI/2..PI/2
    const px = Math.min(LW - 1, ((lon / (Math.PI * 2) + 0.5) * LW) | 0);
    const py = Math.min(LH - 1, ((0.5 - lat / Math.PI) * LH) | 0);
    const bit = py * LW + px;
    return (mask[bit >> 3] >> (7 - (bit & 7))) & 1;
}

// Inverso radical em base 2 (van der Corput): metade de uma sequência de Hammersley.
function vanDerCorput2(index) {
    let bits = (index << 16) | (index >>> 16);
    bits = ((bits & 0x55555555) << 1) | ((bits & 0xAAAAAAAA) >>> 1);
    bits = ((bits & 0x33333333) << 2) | ((bits & 0xCCCCCCCC) >>> 2);
    bits = ((bits & 0x0F0F0F0F) << 4) | ((bits & 0xF0F0F0F0) >>> 4);
    bits = ((bits & 0x00FF00FF) << 8) | ((bits & 0xFF00FF00) >>> 8);
    return (bits >>> 0) * 2.3283064365386963e-10;
}

// Hash inteiro de k em [0, 1). Qualquer sequência correlacionada com k, como
// (k * 0.7548) % 1, recria as listras diagonais da espiral de Fibonacci.
function hashUnit(k) {
    let hash = Math.imul(k ^ 0x9e3779b9, 0x85ebca6b);
    hash ^= hash >>> 13;
    hash = Math.imul(hash, 0xc2b2ae35);
    hash ^= hash >>> 16;
    return (hash >>> 0) / 4294967296;
}

// Fisher-Yates em posições e normais juntas. A estratificação decide onde os pontos
// ficam; embaralhar decide qual partícula vai para onde. Sem isso, blocos inteiros
// viajam juntos na transição e some a sensação de enxame.
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

// Junta todas as malhas do glTF, já em espaço de mundo, numa sopa de triângulos
// não indexada que só carrega position.
async function loadModelGeometry(url) {
    const gltf = await new GLTFLoader().loadAsync(url);
    gltf.scene.updateMatrixWorld(true);
    const chunks = [];
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
        chunks.push(chunk);
        child.geometry.dispose();
        for (const material of [child.material].flat()) {
            material.dispose();
        }
    });
    if (chunks.length === 0) {
        throw new Error(`Nenhuma malha em ${url}.`);
    }
    const merged = new Float32Array(chunks.reduce((total, chunk) => total + chunk.length, 0));
    let offset = 0;
    for (const chunk of chunks) {
        merged.set(chunk, offset);
        offset += chunk.length;
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(merged, 3));
    return geometry;
}

async function loadLandMask(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Máscara de terra indisponível (${response.status}): ${url}`);
    }
    const mask = new Uint8Array(await response.arrayBuffer());
    if (mask.length !== (LW * LH) / 8) {
        throw new Error(`Máscara de terra com ${mask.length} bytes; esperado ${(LW * LH) / 8}.`);
    }
    return mask;
}

function normalizeGeometry(geometry, radius) {
    geometry.center();
    geometry.computeBoundingSphere();
    const scale = radius / geometry.boundingSphere.radius;
    geometry.scale(scale, scale, scale);
    return geometry;
}

// Nuvem de exatamente `count` pontos na superfície, com a normal do triângulo de origem.
function sampleSurface(geometry, count) {
    const source = geometry.getAttribute('position').array;
    const triangles = source.length / 9;
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
        a.fromArray(source, i * 9);
        b.fromArray(source, i * 9 + 3);
        c.fromArray(source, i * 9 + 6);
        normal.crossVectors(ab.subVectors(b, a), ac.subVectors(c, a));
        const length = normal.length();
        totalArea += length * 0.5;
        cumulativeArea[i] = totalArea;
        if (length > 1e-12) {
            normal.divideScalar(length).toArray(faceNormals, i * 3);
        }
    }

    const positions = new Float32Array(count * 3);
    const normals = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
        // Ponderada por área e estratificada: cada partícula pega uma fatia igual da área total.
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
        // Baixa discrepância dentro do triângulo.
        let u = vanDerCorput2(i);
        let v = (i * 0.6180339887498949) % 1;
        if (u + v > 1) { u = 1 - u; v = 1 - v; }
        a.fromArray(source, low * 9);
        b.fromArray(source, low * 9 + 3);
        c.fromArray(source, low * 9 + 6);
        for (let axis = 0; axis < 3; axis++) {
            const origin = a.getComponent(axis);
            positions[i * 3 + axis] = origin + u * (b.getComponent(axis) - origin) + v * (c.getComponent(axis) - origin);
            normals[i * 3 + axis] = faceNormals[low * 3 + axis];
        }
    }
    shuffleTogether(positions, normals);
    return { positions, normals };
}

// Terra construída direto: espiral de Fibonacci com jitter, oceano desbastado.
function buildEarth(mask, count, oceanKeep) {
    const GA = Math.PI * (3 - Math.sqrt(5));
    const candidates = Math.ceil((count / (0.30 + 0.70 * oceanKeep)) * 1.12);
    // Sem jitter a espiral vira listras diagonais de moiré bem visíveis.
    const jitter = 0.6 * Math.sqrt((4 * Math.PI) / candidates);
    const kept = [];
    for (let k = 0; k < candidates; k++) {
        let y = 1 - ((k + 0.5) / candidates) * 2;
        const ring = Math.sqrt(Math.max(0, 1 - y * y));
        let x = Math.cos(GA * k) * ring;
        let z = Math.sin(GA * k) * ring;
        x += (hashUnit(k * 3) - 0.5) * jitter;
        y += (hashUnit(k * 3 + 1) - 0.5) * jitter;
        z += (hashUnit(k * 3 + 2) - 0.5) * jitter;
        const inverseLength = 1 / Math.hypot(x, y, z);
        x *= inverseLength;
        y *= inverseLength;
        z *= inverseLength;
        // Os continentes aparecem por densidade, não por cor.
        if (!isLand(mask, x, y, z) && hashUnit(k + 991) > oceanKeep) {
            continue;
        }
        kept.push(x, y, z);
    }

    const available = kept.length / 3;
    const positions = new Float32Array(count * 3);
    const normals = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
        // Reamostra por índice para chegar em exatamente `count`.
        const j = Math.min(available - 1, Math.floor((i * available) / count)) * 3;
        for (let axis = 0; axis < 3; axis++) {
            normals[i * 3 + axis] = kept[j + axis];              // a normal é a direção radial
            positions[i * 3 + axis] = kept[j + axis] * EARTH_RADIUS;
        }
    }
    shuffleTogether(positions, normals);
    return { positions, normals };
}

// Volume uniforme numa esfera. Normais zeradas: o shader não aplica oclusão.
function buildScattered(count, looseRadius) {
    const positions = new Float32Array(count * 3);
    const normals = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
        const theta = Math.acos(2 * Math.random() - 1);
        const phi = Math.random() * Math.PI * 2;
        const radius = looseRadius * Math.cbrt(Math.random());
        positions[i * 3] = radius * Math.sin(theta) * Math.cos(phi);
        positions[i * 3 + 1] = radius * Math.sin(theta) * Math.sin(phi);
        positions[i * 3 + 2] = radius * Math.cos(theta);
    }
    return { positions, normals };
}

// Uma forma estreita e sólida empilha partículas no mesmo pixel e estoura em branco;
// um volume aberto some. O alfa sai das partículas por célula ocupada numa grade
// 64×64 vista de frente. O 0.45 desconta o que a oclusão apaga de qualquer jeito.
function autoAlpha(positions, hasNormals, alphaTarget) {
    const grid = 64;
    const occupied = new Uint8Array(grid * grid);
    let extent = 1e-6;
    for (let i = 0; i < positions.length; i += 3) {
        extent = Math.max(extent, Math.abs(positions[i]), Math.abs(positions[i + 1]));
    }
    let cells = 0;
    for (let i = 0; i < positions.length; i += 3) {
        const gx = (((positions[i] / extent) * 0.5 + 0.5) * (grid - 1)) | 0;
        const gy = (((positions[i + 1] / extent) * 0.5 + 0.5) * (grid - 1)) | 0;
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
    return { positions, normals, dwell, alpha: autoAlpha(positions, hasNormals, alphaTarget) };
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

// Um triângulo desenhado N vezes: uma única chamada de draw por camada para a nuvem inteira.
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
    // A tinta vem em sRGB; o shader trabalha em linear e converte na saída.
    const inks = new Map(PALETTE.map((entry) => [entry, new THREE.Color(entry.ink).toArray()]));
    for (let i = 0; i < count; i++) {
        const entry = pickPaletteEntry(totalWeight);
        colors.set(entry.rgb, i * 3);
        inkColors.set(inks.get(entry), i * 3);
        seeds[i] = Math.random();
        // O expoente 4.5 concentra quase tudo nos triângulos pequenos e deixa poucos grandes.
        scales[i] = config.triMin + Math.pow(Math.random(), 4.5) * config.triVar;
    }
    geometry.setAttribute('aColor', new THREE.InstancedBufferAttribute(colors, 3));
    geometry.setAttribute('aColorInk', new THREE.InstancedBufferAttribute(inkColors, 3));
    geometry.setAttribute('aSeed', new THREE.InstancedBufferAttribute(seeds, 1));
    geometry.setAttribute('aScale', new THREE.InstancedBufferAttribute(scales, 1));
    return { geometry, morph };
}

const roundCssPixels = (value) => Math.round(value * 100) / 100;

export async function mountParticles(container, { modelUrl, maskUrl, config: overrides = {}, layerHost } = {}) {
    const config = { ...CONFIG, ...overrides };
    const count = config.count;
    const [model, mask] = await Promise.all([loadModelGeometry(modelUrl), loadLandMask(maskUrl)]);
    // Toda forma tem o mesmo N: a partícula nº 4.217 do microfone é a nº 4.217 da Terra.
    const shapes = [
        createShape(sampleSurface(normalizeGeometry(model, MIC_RADIUS), count), true, config.dwellSolid, config.alphaTarget),
        createShape(buildEarth(mask, count, config.oceanKeep), true, config.dwellSolid, config.alphaTarget),
        createShape(buildScattered(count, config.looseRadius), false, config.dwellLoose, config.alphaTarget),
    ];
    model.dispose();

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
            uLayer: { value: 0 },
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
    const scene = new THREE.Scene();
    scene.add(cloud);
    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
    camera.position.z = 10.5;

    // Duas camadas transparentes com a mesma cena: a de trás passa sob o texto do hero e a
    // da frente sobre ele. Cada camada é um canvas, então há uma chamada de draw por camada.
    const host = layerHost ?? container.closest('[data-particles-scene]') ?? container;
    const layers = ['back', 'front'].map((name) => {
        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, depth: false, stencil: false });
        renderer.setClearColor(0x000000, 0);
        renderer.domElement.className = `ed-particles-canvas ed-particles-${name}`;
        renderer.domElement.setAttribute('aria-hidden', 'true');
        return renderer;
    });
    const [back, front] = layers;
    host.prepend(back.domElement);
    host.append(front.domElement);

    // A câmera enquadra o slot do figure, como o palco original; os canvases só mostram mais
    // do mesmo plano ao redor. A forma fica no mesmo lugar e tamanho, e nada bate numa borda.
    let layoutKey = '';
    const syncLayout = () => {
        const frame = back.domElement.getBoundingClientRect();
        const slot = container.getBoundingClientRect();
        const width = roundCssPixels(Math.max(1, frame.width));
        const height = roundCssPixels(Math.max(1, frame.height));
        const slotWidth = roundCssPixels(Math.max(1, slot.width));
        const slotHeight = roundCssPixels(Math.max(1, slot.height));
        const offsetX = roundCssPixels(frame.left - slot.left);
        const offsetY = roundCssPixels(frame.top - slot.top);
        const ratio = Math.min(window.devicePixelRatio, 2, Math.sqrt(MAX_LAYER_PIXELS / (width * height)));
        const key = `${width}|${height}|${slotWidth}|${slotHeight}|${offsetX}|${offsetY}|${ratio}`;
        if (key === layoutKey) {
            return;
        }
        layoutKey = key;
        for (const renderer of layers) {
            renderer.setPixelRatio(ratio);
            renderer.setSize(width, height, false);
        }
        camera.aspect = slotWidth / slotHeight;
        camera.setViewOffset(slotWidth, slotHeight, offsetX, offsetY, width, height);
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
    let drag = null;
    let spin = 0;

    // Trocar de forma = quatro cópias de buffer e needsUpdate. Depois disso a CPU não
    // toca em nenhum buffer: o loop só escreve uniforms e a rotação.
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
        // Só a saída do microfone espalha mais; Terra → nuvem e nuvem → microfone usam o spread normal.
        uniforms.uSpread.value = from === 0 && to === 1 ? config.burstSpread : config.spread;
    };

    const applyMotionPreference = () => {
        if (reducedMotion.matches) {
            // Sem ciclo: o microfone parado, de frente.
            setMorph(0, 0);
            current = 0;
            target = 0;
            morphing = false;
            uniforms.uProgress.value = 1;
            cloud.rotation.set(0, 0, 0);
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
                    // Ciclo: microfone → Terra → disperso → microfone → …
                    target = (current + 1) % shapes.length;
                    setMorph(current, target);
                    uniforms.uProgress.value = 0;
                    morphing = true;
                }
            }
        }
        if (!drag) {
            // A rotação automática continua; a inércia do arraste se dissolve nela.
            cloud.rotation.y += ((reducedMotion.matches ? 0 : ROTATION_PER_SECOND) + spin) * delta;
            spin *= Math.exp(-delta * SPIN_DAMPING);
            if (!reducedMotion.matches) {
                cloud.rotation.x *= Math.exp(-delta * TILT_RETURN);
            }
        }
        syncLayout();
        uniforms.uTime.value = time;
        uniforms.uLayer.value = 0;
        back.render(scene, camera);
        uniforms.uLayer.value = 1;
        front.render(scene, camera);
        frames++;
        if (frames === 1) {
            announceReady(container);
        }
    };

    // Arraste sobre o espaço da forma. No toque só o gesto horizontal gira: o vertical continua rolando a página.
    const onPointerDown = (event) => {
        if (event.button !== 0) {
            return;
        }
        drag = { id: event.pointerId, x: event.clientX, y: event.clientY, time: event.timeStamp };
        spin = 0;
        container.setPointerCapture(event.pointerId);
        container.classList.add('is-dragging');
    };
    const onPointerMove = (event) => {
        if (!drag || event.pointerId !== drag.id) {
            return;
        }
        const dx = event.clientX - drag.x;
        const dy = event.clientY - drag.y;
        const seconds = Math.max((event.timeStamp - drag.time) / 1000, 1 / 240);
        cloud.rotation.y += dx * DRAG_RADIANS_PER_PIXEL;
        cloud.rotation.x = THREE.MathUtils.clamp(cloud.rotation.x + dy * DRAG_RADIANS_PER_PIXEL, -MAX_TILT, MAX_TILT);
        spin = THREE.MathUtils.clamp((dx * DRAG_RADIANS_PER_PIXEL) / seconds, -MAX_SPIN, MAX_SPIN);
        drag = { id: drag.id, x: event.clientX, y: event.clientY, time: event.timeStamp };
    };
    const onPointerUp = (event) => {
        if (!drag || event.pointerId !== drag.id) {
            return;
        }
        // Parar antes de soltar, ou movimento reduzido, zera a inércia.
        if (event.timeStamp - drag.time > 80 || reducedMotion.matches) {
            spin = 0;
        }
        drag = null;
        container.classList.remove('is-dragging');
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

    // É fundo de página: nada renderiza enquanto o hero está fora da viewport.
    const intersectionObserver = new IntersectionObserver((entries) => {
        if (entries[entries.length - 1].isIntersecting) {
            start();
        } else {
            stop();
            // Página aberta já rolada: não há palco na tela para esperar.
            announceReady(container);
        }
    });
    const themeObserver = new MutationObserver(syncTheme);
    syncTheme();
    applyMotionPreference();
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    reducedMotion.addEventListener('change', applyMotionPreference);
    intersectionObserver.observe(host);
    container.addEventListener('pointerdown', onPointerDown);
    container.addEventListener('pointermove', onPointerMove);
    container.addEventListener('pointerup', onPointerUp);
    container.addEventListener('pointercancel', onPointerUp);

    const dispose = () => {
        stop();
        intersectionObserver.disconnect();
        themeObserver.disconnect();
        container.removeEventListener('pointerdown', onPointerDown);
        container.removeEventListener('pointermove', onPointerMove);
        container.removeEventListener('pointerup', onPointerUp);
        container.removeEventListener('pointercancel', onPointerUp);
        container.classList.remove('is-dragging');
        reducedMotion.removeEventListener('change', applyMotionPreference);
        timer.dispose();
        geometry.dispose();
        material.dispose();
        for (const renderer of layers) {
            renderer.dispose();
            renderer.domElement.remove();
        }
    };

    return {
        renderers: layers,
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
                rotation: [cloud.rotation.x, cloud.rotation.y],
                drawCalls: layers.reduce((total, renderer) => total + renderer.info.render.calls, 0),
                count,
            };
        },
    };
}

// O módulo da página (js/school-editorial.js) só mostra a Home depois deste aviso: o primeiro quadro desenhado, o palco
// fora da tela ou a falha da montagem. Até lá o conteúdo fica sob o fade, então o palco não surge atrasado.
function announceReady(element) {
    if (!('particlesReady' in element.dataset)) {
        element.dataset.particlesReady = '';
        element.dispatchEvent(new CustomEvent('komuniki:particles-ready'));
    }
}

async function mountFromDataset(element) {
    const { modelUrl, maskUrl, config } = element.dataset;
    const handle = await mountParticles(element, { modelUrl, maskUrl, config: config ? JSON.parse(config) : {} });
    // Numa navegação comum o navegador libera tudo; isto cobre o palco removido por uma troca do htmx.
    element.addEventListener('htmx:beforeCleanupElement', handle.dispose, { once: true });
    if ('particlesDebug' in element.dataset) {
        window.komunikiParticles = handle;
    }
}

for (const element of document.querySelectorAll('[data-particles]')) {
    mountFromDataset(element).catch((error) => {
        announceReady(element);
        console.error('Partículas da Home indisponíveis:', error);
    });
}
