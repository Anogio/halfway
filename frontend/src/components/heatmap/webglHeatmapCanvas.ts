import {
  HEATMAP_BASE_ALPHA,
  HEATMAP_MIN_VISIBLE_COVERAGE,
  ISOCHRONE_COLOR_STOPS,
  type ScalarFieldTexture
} from "@/components/heatmap/scalarGrid";

const BLUR_RADIUS = 4;
const BLUR_SIGMA = 2.2;

type QuadLocations = {
  position: number;
  uv: number;
};

type InterpolateLocations = QuadLocations & {
  field: WebGLUniformLocation;
};

type BlurLocations = QuadLocations & {
  field: WebGLUniformLocation;
  texelStep: WebGLUniformLocation;
};

type ColorLocations = QuadLocations & {
  field: WebGLUniformLocation;
  maxTime: WebGLUniformLocation;
  baseAlpha: WebGLUniformLocation;
  minCoverage: WebGLUniformLocation;
};

type RenderTarget = {
  framebuffer: WebGLFramebuffer;
  texture: WebGLTexture;
};

export type WebglHeatmapCanvasRenderer = {
  getCanvas: () => HTMLCanvasElement;
  getBounds: () => ScalarFieldTexture["bounds"] | null;
  setField: (field: ScalarFieldTexture | null) => void;
  destroy: () => void;
};

export function createWebglHeatmapCanvasRenderer(
  initialField: ScalarFieldTexture | null
): WebglHeatmapCanvasRenderer {
  return new HeatmapCanvasRenderer(initialField);
}

class HeatmapCanvasRenderer implements WebglHeatmapCanvasRenderer {
  private readonly canvas: HTMLCanvasElement;
  private readonly gl: WebGLRenderingContext | null;
  private readonly quadBuffer: WebGLBuffer | null;
  private readonly coarseTexture: WebGLTexture | null;
  private readonly interpolateProgram: WebGLProgram | null;
  private readonly blurProgram: WebGLProgram | null;
  private readonly colorProgram: WebGLProgram | null;
  private readonly interpolateLocations: InterpolateLocations | null;
  private readonly blurLocations: BlurLocations | null;
  private readonly colorLocations: ColorLocations | null;
  private readonly targets: RenderTarget[] = [];
  private bounds: ScalarFieldTexture["bounds"] | null = null;

  constructor(initialField: ScalarFieldTexture | null) {
    this.canvas = document.createElement("canvas");
    this.canvas.width = 1;
    this.canvas.height = 1;

    const gl = this.canvas.getContext("webgl", {
      alpha: true,
      antialias: false,
      depth: false,
      premultipliedAlpha: true,
      preserveDrawingBuffer: false,
      stencil: false
    });
    this.gl = gl;

    this.quadBuffer = gl ? createQuadBuffer(gl) : null;
    this.coarseTexture = gl ? createTexture(gl) : null;
    this.interpolateProgram = gl
      ? createProgram(gl, COMMON_VERTEX_SHADER_SOURCE, INTERPOLATE_FRAGMENT_SHADER_SOURCE)
      : null;
    this.blurProgram = gl ? createProgram(gl, COMMON_VERTEX_SHADER_SOURCE, BLUR_FRAGMENT_SHADER_SOURCE) : null;
    this.colorProgram = gl ? createProgram(gl, COMMON_VERTEX_SHADER_SOURCE, COLOR_FRAGMENT_SHADER_SOURCE) : null;

    this.interpolateLocations =
      gl && this.interpolateProgram ? getInterpolateLocations(gl, this.interpolateProgram) : null;
    this.blurLocations = gl && this.blurProgram ? getBlurLocations(gl, this.blurProgram) : null;
    this.colorLocations = gl && this.colorProgram ? getColorLocations(gl, this.colorProgram) : null;

    this.setField(initialField);
  }

  getCanvas() {
    return this.canvas;
  }

  getBounds() {
    return this.bounds;
  }

  setField(field: ScalarFieldTexture | null) {
    this.bounds = field?.bounds ?? this.bounds;
    if (
      !this.gl ||
      !this.quadBuffer ||
      !this.coarseTexture ||
      !this.interpolateProgram ||
      !this.blurProgram ||
      !this.colorProgram ||
      !this.interpolateLocations ||
      !this.blurLocations ||
      !this.colorLocations
    ) {
      this.clearCanvas();
      return;
    }

    if (!field) {
      this.clearCanvas();
      return;
    }

    this.ensureRenderSize(field.renderWidth, field.renderHeight);
    const gl = this.gl;

    gl.bindTexture(gl.TEXTURE_2D, this.coarseTexture);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, 0);
    gl.texImage2D(
      gl.TEXTURE_2D,
      0,
      gl.RGBA,
      field.width,
      field.height,
      0,
      gl.RGBA,
      gl.UNSIGNED_BYTE,
      field.pixels
    );

    gl.disable(gl.CULL_FACE);
    gl.disable(gl.DEPTH_TEST);
    gl.disable(gl.BLEND);

    this.renderInterpolatePass(field);
    this.renderBlurPass(this.targets[0], this.targets[1], [1 / field.renderWidth, 0]);
    this.renderBlurPass(this.targets[1], this.targets[0], [0, 1 / field.renderHeight]);
    this.renderColorPass(this.targets[0], field.maxTimeS);
    gl.flush();
  }

  destroy() {
    if (!this.gl) {
      return;
    }
    if (this.quadBuffer) {
      this.gl.deleteBuffer(this.quadBuffer);
    }
    if (this.coarseTexture) {
      this.gl.deleteTexture(this.coarseTexture);
    }
    if (this.interpolateProgram) {
      this.gl.deleteProgram(this.interpolateProgram);
    }
    if (this.blurProgram) {
      this.gl.deleteProgram(this.blurProgram);
    }
    if (this.colorProgram) {
      this.gl.deleteProgram(this.colorProgram);
    }
    for (const target of this.targets) {
      this.gl.deleteFramebuffer(target.framebuffer);
      this.gl.deleteTexture(target.texture);
    }
  }

  private ensureRenderSize(width: number, height: number) {
    if (!this.gl) {
      return;
    }
    if (this.canvas.width === width && this.canvas.height === height && this.targets.length === 2) {
      return;
    }

    this.canvas.width = width;
    this.canvas.height = height;

    for (const target of this.targets) {
      this.gl.deleteFramebuffer(target.framebuffer);
      this.gl.deleteTexture(target.texture);
    }
    this.targets.length = 0;
    this.targets.push(createRenderTarget(this.gl, width, height));
    this.targets.push(createRenderTarget(this.gl, width, height));
  }

  private renderInterpolatePass(field: ScalarFieldTexture) {
    if (
      !this.gl ||
      !this.interpolateProgram ||
      !this.interpolateLocations ||
      !this.coarseTexture ||
      !this.targets[0]
    ) {
      return;
    }
    const gl = this.gl;
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.targets[0].framebuffer);
    gl.viewport(0, 0, field.renderWidth, field.renderHeight);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.useProgram(this.interpolateProgram);
    bindQuad(gl, this.quadBuffer, this.interpolateLocations);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, this.coarseTexture);
    gl.uniform1i(this.interpolateLocations.field, 0);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
  }

  private renderBlurPass(source: RenderTarget, target: RenderTarget, texelStep: [number, number]) {
    if (!this.gl || !this.blurProgram || !this.blurLocations) {
      return;
    }
    const gl = this.gl;
    gl.bindFramebuffer(gl.FRAMEBUFFER, target.framebuffer);
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.useProgram(this.blurProgram);
    bindQuad(gl, this.quadBuffer, this.blurLocations);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, source.texture);
    gl.uniform1i(this.blurLocations.field, 0);
    gl.uniform2f(this.blurLocations.texelStep, texelStep[0], texelStep[1]);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
  }

  private renderColorPass(source: RenderTarget, maxTimeS: number) {
    if (!this.gl || !this.colorProgram || !this.colorLocations) {
      return;
    }
    const gl = this.gl;
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.useProgram(this.colorProgram);
    bindQuad(gl, this.quadBuffer, this.colorLocations);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, source.texture);
    gl.uniform1i(this.colorLocations.field, 0);
    gl.uniform1f(this.colorLocations.maxTime, maxTimeS);
    gl.uniform1f(this.colorLocations.baseAlpha, HEATMAP_BASE_ALPHA);
    gl.uniform1f(this.colorLocations.minCoverage, HEATMAP_MIN_VISIBLE_COVERAGE);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
  }

  private clearCanvas() {
    this.canvas.width = 1;
    this.canvas.height = 1;
    if (!this.gl) {
      return;
    }
    this.gl.bindFramebuffer(this.gl.FRAMEBUFFER, null);
    this.gl.viewport(0, 0, 1, 1);
    this.gl.clearColor(0, 0, 0, 0);
    this.gl.clear(this.gl.COLOR_BUFFER_BIT);
  }
}

const COMMON_VERTEX_SHADER_SOURCE = `
attribute vec2 a_position;
attribute vec2 a_uv;

varying vec2 v_uv;

void main() {
  v_uv = a_uv;
  gl_Position = vec4(a_position, 0.0, 1.0);
}
`;

const INTERPOLATE_FRAGMENT_SHADER_SOURCE = `
precision mediump float;

varying vec2 v_uv;
uniform sampler2D u_field;

void main() {
  vec4 sample = texture2D(u_field, vec2(v_uv.x, 1.0 - v_uv.y));
  gl_FragColor = vec4(sample.rg, 0.0, 1.0);
}
`;

const BLUR_FRAGMENT_SHADER_SOURCE = `
precision mediump float;

varying vec2 v_uv;
uniform sampler2D u_field;
uniform vec2 u_texel_step;

void main() {
  vec2 offsets[9];
  offsets[0] = -4.0 * u_texel_step;
  offsets[1] = -3.0 * u_texel_step;
  offsets[2] = -2.0 * u_texel_step;
  offsets[3] = -1.0 * u_texel_step;
  offsets[4] = vec2(0.0, 0.0);
  offsets[5] = 1.0 * u_texel_step;
  offsets[6] = 2.0 * u_texel_step;
  offsets[7] = 3.0 * u_texel_step;
  offsets[8] = 4.0 * u_texel_step;

  float weights[9];
  weights[0] = ${gaussianWeight(4).toFixed(8)};
  weights[1] = ${gaussianWeight(3).toFixed(8)};
  weights[2] = ${gaussianWeight(2).toFixed(8)};
  weights[3] = ${gaussianWeight(1).toFixed(8)};
  weights[4] = ${gaussianWeight(0).toFixed(8)};
  weights[5] = ${gaussianWeight(1).toFixed(8)};
  weights[6] = ${gaussianWeight(2).toFixed(8)};
  weights[7] = ${gaussianWeight(3).toFixed(8)};
  weights[8] = ${gaussianWeight(4).toFixed(8)};

  vec2 sum = vec2(0.0, 0.0);
  for (int i = 0; i < 9; i += 1) {
    vec2 sample = texture2D(u_field, v_uv + offsets[i]).rg;
    sum += sample * weights[i];
  }
  gl_FragColor = vec4(sum, 0.0, 1.0);
}
`;

const COLOR_FRAGMENT_SHADER_SOURCE = `
precision mediump float;

varying vec2 v_uv;

uniform sampler2D u_field;
uniform float u_max_time;
uniform float u_base_alpha;
uniform float u_min_coverage;

${buildColorRampShader()}

void main() {
  vec2 sample = texture2D(u_field, v_uv).rg;
  float weightedTime = sample.r;
  float coverage = sample.g;
  if (coverage <= u_min_coverage) {
    discard;
  }

  float normalizedTime = clamp(weightedTime / max(coverage, 0.0001), 0.0, 1.0);
  float timeS = normalizedTime * max(u_max_time, 1.0);
  float outerFade = 1.0 - 0.46 * smoothstep(0.0, 1.0, pow(normalizedTime, 0.84));
  float alpha = clamp(u_base_alpha * pow(coverage, 0.92) * outerFade, 0.0, 0.76);
  vec3 color = heatmapColor(timeS) * alpha;
  gl_FragColor = vec4(color, alpha);
}
`;

function createQuadBuffer(gl: WebGLRenderingContext): WebGLBuffer {
  const buffer = gl.createBuffer();
  if (!buffer) {
    throw new Error("Failed to create WebGL heatmap quad buffer.");
  }
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(
    gl.ARRAY_BUFFER,
    new Float32Array([
      -1, -1, 0, 0,
      1, -1, 1, 0,
      -1, 1, 0, 1,
      -1, 1, 0, 1,
      1, -1, 1, 0,
      1, 1, 1, 1
    ]),
    gl.STATIC_DRAW
  );
  return buffer;
}

function createTexture(gl: WebGLRenderingContext): WebGLTexture {
  const texture = gl.createTexture();
  if (!texture) {
    throw new Error("Failed to create WebGL heatmap texture.");
  }
  gl.bindTexture(gl.TEXTURE_2D, texture);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  return texture;
}

function createRenderTarget(gl: WebGLRenderingContext, width: number, height: number): RenderTarget {
  const texture = createTexture(gl);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, width, height, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);

  const framebuffer = gl.createFramebuffer();
  if (!framebuffer) {
    gl.deleteTexture(texture);
    throw new Error("Failed to create WebGL heatmap framebuffer.");
  }
  gl.bindFramebuffer(gl.FRAMEBUFFER, framebuffer);
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);

  const status = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
  if (status !== gl.FRAMEBUFFER_COMPLETE) {
    gl.deleteFramebuffer(framebuffer);
    gl.deleteTexture(texture);
    throw new Error(`Incomplete WebGL heatmap framebuffer: ${status}`);
  }

  return { framebuffer, texture };
}

function bindQuad(
  gl: WebGLRenderingContext,
  buffer: WebGLBuffer | null,
  locations: QuadLocations
) {
  if (!buffer) {
    return;
  }
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.enableVertexAttribArray(locations.position);
  gl.vertexAttribPointer(locations.position, 2, gl.FLOAT, false, 16, 0);
  gl.enableVertexAttribArray(locations.uv);
  gl.vertexAttribPointer(locations.uv, 2, gl.FLOAT, false, 16, 8);
}

function getInterpolateLocations(
  gl: WebGLRenderingContext,
  program: WebGLProgram
): InterpolateLocations {
  const position = gl.getAttribLocation(program, "a_position");
  const uv = gl.getAttribLocation(program, "a_uv");
  const field = gl.getUniformLocation(program, "u_field");
  if (position < 0 || uv < 0 || !field) {
    throw new Error("Failed to resolve interpolate shader locations.");
  }
  return { position, uv, field };
}

function getBlurLocations(gl: WebGLRenderingContext, program: WebGLProgram): BlurLocations {
  const position = gl.getAttribLocation(program, "a_position");
  const uv = gl.getAttribLocation(program, "a_uv");
  const field = gl.getUniformLocation(program, "u_field");
  const texelStep = gl.getUniformLocation(program, "u_texel_step");
  if (position < 0 || uv < 0 || !field || !texelStep) {
    throw new Error("Failed to resolve blur shader locations.");
  }
  return { position, uv, field, texelStep };
}

function getColorLocations(gl: WebGLRenderingContext, program: WebGLProgram): ColorLocations {
  const position = gl.getAttribLocation(program, "a_position");
  const uv = gl.getAttribLocation(program, "a_uv");
  const field = gl.getUniformLocation(program, "u_field");
  const maxTime = gl.getUniformLocation(program, "u_max_time");
  const baseAlpha = gl.getUniformLocation(program, "u_base_alpha");
  const minCoverage = gl.getUniformLocation(program, "u_min_coverage");
  if (position < 0 || uv < 0 || !field || !maxTime || !baseAlpha || !minCoverage) {
    throw new Error("Failed to resolve color shader locations.");
  }
  return {
    position,
    uv,
    field,
    maxTime,
    baseAlpha,
    minCoverage
  };
}

function createProgram(
  gl: WebGLRenderingContext,
  vertexSource: string,
  fragmentSource: string
): WebGLProgram {
  const vertexShader = compileShader(gl, gl.VERTEX_SHADER, vertexSource);
  const fragmentShader = compileShader(gl, gl.FRAGMENT_SHADER, fragmentSource);
  const program = gl.createProgram();
  if (!program) {
    gl.deleteShader(vertexShader);
    gl.deleteShader(fragmentShader);
    throw new Error("Failed to create WebGL heatmap program.");
  }

  gl.attachShader(program, vertexShader);
  gl.attachShader(program, fragmentShader);
  gl.linkProgram(program);
  gl.deleteShader(vertexShader);
  gl.deleteShader(fragmentShader);

  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    const info = gl.getProgramInfoLog(program) ?? "Unknown WebGL program link error";
    gl.deleteProgram(program);
    throw new Error(info);
  }

  return program;
}

function compileShader(
  gl: WebGLRenderingContext,
  type: number,
  source: string
): WebGLShader {
  const shader = gl.createShader(type);
  if (!shader) {
    throw new Error("Failed to create WebGL heatmap shader.");
  }
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const info = gl.getShaderInfoLog(shader) ?? "Unknown WebGL shader compile error";
    gl.deleteShader(shader);
    throw new Error(info);
  }
  return shader;
}

function buildColorRampShader(): string {
  const segments = ISOCHRONE_COLOR_STOPS.slice(0, -1)
    .map(([startTime, startColor], index) => {
      const [endTime, endColor] = ISOCHRONE_COLOR_STOPS[index + 1];
      const start = colorToVec3(startColor);
      const end = colorToVec3(endColor);
      return index === 0
        ? `if (timeS <= ${endTime.toFixed(1)}) {
  float t = clamp((timeS - ${startTime.toFixed(1)}) / ${Math.max(endTime - startTime, 1).toFixed(1)}, 0.0, 1.0);
  return mix(${start}, ${end}, t);
}`
        : `if (timeS <= ${endTime.toFixed(1)}) {
  float t = clamp((timeS - ${startTime.toFixed(1)}) / ${Math.max(endTime - startTime, 1).toFixed(1)}, 0.0, 1.0);
  return mix(${start}, ${end}, t);
}`;
    })
    .join("\n");

  const lastStop = ISOCHRONE_COLOR_STOPS[ISOCHRONE_COLOR_STOPS.length - 1][1];
  return `
vec3 heatmapColor(float timeS) {
${segments}
  return ${colorToVec3(lastStop)};
}
`;
}

function colorToVec3([r, g, b]: [number, number, number]): string {
  return `vec3(${(r / 255).toFixed(6)}, ${(g / 255).toFixed(6)}, ${(b / 255).toFixed(6)})`;
}

function gaussianWeight(offset: number): number {
  const numerator = Math.exp(-(offset * offset) / (2 * BLUR_SIGMA * BLUR_SIGMA));
  const denominator = Array.from({ length: BLUR_RADIUS * 2 + 1 }, (_, idx) => idx - BLUR_RADIUS)
    .map((value) => Math.exp(-(value * value) / (2 * BLUR_SIGMA * BLUR_SIGMA)))
    .reduce((sum, value) => sum + value, 0);
  return numerator / denominator;
}
