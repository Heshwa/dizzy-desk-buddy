const byId = id => document.getElementById(id);
const radians = degrees => degrees * Math.PI / 180;
const groupOrder = [
  'Helmet and face', 'Torso and base', 'Shoulders and hands',
  'Mounts and retainers', 'Hardware allowances', 'Fit samples'
];
const shellPart = part => /^(Helmet_|Hip_|Torso_|Chest_|Waist_|Foot_|Face_|Crown_|Forearm_|Palm_|Cuff_|Shoulder_housing|Sole_|Volume_|Record_|Bottom_cover)/.test(part.id);
const displayOrder = ['Helmet_front','Helmet_rear','Face_bezel','Crown_inlay_L','Crown_inlay_R',
  'Torso_front','Torso_rear','Hip_front','Hip_rear','Shoulder_housing_L','Shoulder_housing_R'];
const order = part => displayOrder.includes(part.id) ? displayOrder.indexOf(part.id) : displayOrder.length;
const title = part => part.title || part.id.replace(/^CAL_/,'Fit sample ').replaceAll('_',' ');
const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
const identity = () => [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
const add = (a,b) => a.map((value, index) => value + b[index]);
const scaleVector = (a,scale) => a.map(value => value * scale);
const dot = (a,b) => a.reduce((sum,value,index) => sum + value * b[index], 0);
const cross = (a,b) => [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]];
const unit = a => scaleVector(a, 1 / (Math.hypot(...a) || 1));

function multiply(a,b) {
  const result = Array(16).fill(0);
  for (let column = 0; column < 4; column++) {
    for (let row = 0; row < 4; row++) {
      for (let k = 0; k < 4; k++) {
        result[column*4+row] += a[k*4+row] * b[column*4+k];
      }
    }
  }
  return result;
}

function translation(vector) {
  const matrix = identity();
  matrix.splice(12,3,...vector);
  return matrix;
}

function rotation(axis, angle) {
  const c = Math.cos(angle), s = Math.sin(angle);
  return axis === 'z'
    ? [c,s,0,0, -s,c,0,0, 0,0,1,0, 0,0,0,1]
    : [1,0,0,0, 0,c,s,0, 0,-s,c,0, 0,0,0,1];
}

function around(pivot, axis, angle) {
  return multiply(multiply(translation(pivot), rotation(axis,angle)), translation(scaleVector(pivot,-1)));
}

function lookAt(eye, target) {
  const z = unit(add(eye, scaleVector(target, -1)));
  const x = unit(cross([0,0,1], z)), y = cross(z,x);
  return [
    x[0],y[0],z[0],0, x[1],y[1],z[1],0, x[2],y[2],z[2],0,
    -dot(x,eye),-dot(y,eye),-dot(z,eye),1
  ];
}

const vertexSource = `#version 300 es
in vec3 position;
in vec3 vertexNormal;
uniform mat4 model;
uniform mat4 viewProjection;
out vec3 normal;
void main() {
  gl_Position=viewProjection*model*vec4(position,1);
  normal=mat3(model)*vertexNormal;
}`;
const fragmentSource = `#version 300 es
precision highp float;
in vec3 normal;
uniform vec3 color;
uniform vec3 viewAxis;
uniform float opacity;
out vec4 pixel;
void main() {
  vec3 n=normalize(normal);
  float direct=max(0.0,dot(n,normalize(vec3(-.4,-.7,1.0))));
  float fill=max(0.0,dot(n,viewAxis));
  float shade=.49+.42*direct+.14*fill;
  pixel=vec4(color*shade,opacity);
}`;

class Viewer {
  constructor(canvas) {
    this.canvas = canvas;
    const gl = this.gl = canvas.getContext('webgl2',{antialias:true});
    if (!gl) throw new Error('WebGL 2 is unavailable');
    this.program = gl.createProgram();
    for (const [type, source] of [[gl.VERTEX_SHADER, vertexSource], [gl.FRAGMENT_SHADER, fragmentSource]]) {
      const shader = gl.createShader(type);
      gl.shaderSource(shader,source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader,gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
      gl.attachShader(this.program,shader);
    }
    gl.linkProgram(this.program);
    if (!gl.getProgramParameter(this.program,gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(this.program));
    this.uniform = Object.fromEntries(['model','viewProjection','color','viewAxis','opacity']
      .map(name => [name,gl.getUniformLocation(this.program,name)]));
    this.position = gl.getAttribLocation(this.program,'position');
    this.normal = gl.getAttribLocation(this.program,'vertexNormal');
    this.buffers = new Map();
    this.parts = [];
    this.center = [0,0,110];
    this.extent = 250;
    this.pose = () => identity();
    this.resetCamera();
    new ResizeObserver(() => this.draw()).observe(canvas);
    let previous;
    canvas.addEventListener('pointerdown', event => {
      previous = [event.clientX,event.clientY];
      canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener('pointermove', event => {
      if (!previous) return;
      this.yaw -= (event.clientX-previous[0])*.009;
      this.pitch = clamp(this.pitch+(event.clientY-previous[1])*.009, -1.43, 1.43);
      previous = [event.clientX,event.clientY];
      this.draw();
    });
    for (const name of ['pointerup','pointercancel','lostpointercapture']) {
      canvas.addEventListener(name, () => { previous = null; });
    }
    canvas.addEventListener('wheel', event => {
      event.preventDefault();
      this.zoom = clamp(this.zoom*Math.exp(event.deltaY*.001),.25,3.6);
      this.draw();
    },{passive:false});
  }

  resetCamera(yaw = -1.2, pitch = .17) {
    this.yaw = yaw;
    this.pitch = pitch;
    this.zoom = 1;
  }

  async load(part) {
    if (this.buffers.has(part.id)) return;
    let response;
    for (let attempt=0; attempt<3; attempt++) {
      try {
        response = await fetch(part.path);
        break;
      } catch (error) {
        if (attempt===2) throw new Error(`Could not fetch ${title(part)}`,{cause:error});
      }
    }
    if (!response.ok) throw new Error(`Could not load ${title(part)}`);
    this.upload(part,await response.arrayBuffer());
  }

  upload(part, data) {
    if (data.byteLength !== part.count*24) throw new Error(`Mesh is incomplete for ${title(part)}. Expected ${part.count*24} bytes; received ${data.byteLength}`);
    const gl = this.gl;
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    gl.bufferData(gl.ARRAY_BUFFER,data,gl.STATIC_DRAW);
    this.buffers.set(part.id,buffer);
  }

  draw() {
    const {canvas, gl} = this;
    const width = canvas.clientWidth, height = canvas.clientHeight;
    if (!width || !height) return;
    const density = Math.min(devicePixelRatio,2);
    canvas.width = Math.round(width*density);
    canvas.height = Math.round(height*density);
    gl.viewport(0,0,canvas.width,canvas.height);
    gl.clearColor(.925,.939,.92,1);
    gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
    gl.useProgram(this.program);
    gl.enable(gl.DEPTH_TEST);
    const axis = [Math.cos(this.pitch)*Math.cos(this.yaw),Math.cos(this.pitch)*Math.sin(this.yaw),Math.sin(this.pitch)];
    const camera = lookAt(add(this.center,scaleVector(axis,800)),this.center);
    const aspect = width/height;
    const half = this.extent*this.zoom/2;
    const y = half/Math.min(1,aspect), x = y*aspect;
    const projection = [1/x,0,0,0, 0,1/y,0,0, 0,0,-.0008,0, 0,0,-1,1];
    gl.uniformMatrix4fv(this.uniform.viewProjection,false,multiply(projection,camera));
    gl.uniform3fv(this.uniform.viewAxis,axis);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
    const objects = this.parts.toSorted((a,b) => (b.opacity ?? 1) - (a.opacity ?? 1));
    for (const part of objects) {
      const buffer = this.buffers.get(part.id);
      if (!buffer) continue;
      gl.uniformMatrix4fv(this.uniform.model,false,this.pose(part));
      gl.uniform3fv(this.uniform.color,part.color);
      const opacity = part.opacity ?? 1;
      gl.uniform1f(this.uniform.opacity,opacity);
      gl.depthMask(opacity === 1);
      gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
      gl.enableVertexAttribArray(this.position);
      gl.enableVertexAttribArray(this.normal);
      gl.vertexAttribPointer(this.position,3,gl.FLOAT,false,24,0);
      gl.vertexAttribPointer(this.normal,3,gl.FLOAT,false,24,12);
      gl.drawArrays(gl.TRIANGLES,0,part.count);
    }
    gl.depthMask(true);
  }
}

const dialog = byId('part-dialog');
const partList = byId('parts');
const filter = byId('part-group');
const search = byId('part-search');
let partViewer, assembly, parts = [];
let modelScale = 1;
let assemblyRequested = false;
let selectedPartId;

function activePage() {
  const target = location.hash.slice(1);
  return ['assembly','parts','assembly-gif','connected-fit'].includes(target) ? target : 'assembly';
}

function activate() {
  if (dialog.open) dialog.close();
  const page = activePage();
  for (const link of document.querySelectorAll('[data-page]')) {
    const selected = page === link.dataset.page;
    byId(link.dataset.page+'-page').hidden = !selected;
    if (selected) link.setAttribute('aria-current','page');
    else link.removeAttribute('aria-current');
  }
  if (page === 'assembly') startAssembly();
  if (page === 'connected-fit') startConnectedFit();
  if (page === 'assembly-gif') {
    const gif = byId('assembly-animation');
    if (!gif.getAttribute('src')) gif.src = gif.dataset.src;
  }
  window.scrollTo(0,0);
}

function drawAssembly() {
  if (!assembly) return;
  const inside = byId('inside').checked;
  const explode = byId('explode').checked;
  assembly.extent = (explode ? 348 : 247) * modelScale;
  assembly.parts = parts.filter(part => part.region !== 'coupon'
    && (!part.hardware || part.visible_exterior || inside || explode)
    && !(inside && !explode && shellPart(part)));
  assembly.draw();
}

function assemblyPose(part) {
  let motion = identity();
  if (part.region === 'head') {
    motion = around([0,0,109.5*modelScale],'z',radians(+byId('head').value));
  } else if (['L','R'].includes(part.region)) {
    const side = part.region === 'L' ? -1 : 1;
    const control = part.region === 'L' ? 'left' : 'right';
    motion = around([side*56*modelScale,0,94*modelScale],'x',radians(-byId(control).value));
  }
  if (!byId('explode').checked) return motion;
  const direction = unit(add(part.center,[0,0,-100*modelScale]));
  return multiply(translation(scaleVector(direction,43)),motion);
}

async function startAssembly() {
  if (!parts.length) return;
  if (assemblyRequested) {
    drawAssembly();
    return;
  }
  assemblyRequested = true;
  try {
    assembly = new Viewer(byId('assembly-canvas'));
    assembly.center = [0,0,104*modelScale];
    assembly.pose = assemblyPose;
    const meshParts = parts.filter(part => part.region !== 'coupon');
    for (let i = 0; i < meshParts.length; i += 10) {
      await Promise.all(meshParts.slice(i,i+10).map(part => assembly.load(part)));
    }
    const printable = meshParts.filter(part => !part.hardware).length;
    byId('assembly-info').textContent = `${printable} printed parts · about ${Math.round(203*modelScale)} mm tall`;
    drawAssembly();
  } catch (error) {
    byId('assembly-info').textContent = error.message + '. Static views are available in the parts catalogue.';
  }
}

function downloadLink(label, url) {
  const link = document.createElement('a');
  link.textContent = label;
  link.href = url;
  link.className = 'button';
  link.download = '';
  return link;
}

async function inspect(part) {
  selectedPartId = part.id;
  byId('part-title').textContent = title(part);
  byId('detail-group').textContent = part.group;
  byId('part-dimensions').textContent = part.size_mm
    .map(value => Number(value.toFixed(1))).join(' × ') + ' mm · ' + part.material;
  byId('part-downloads').replaceChildren();
  if (part.stl) byId('part-downloads').append(downloadLink('STL',part.stl),downloadLink('STEP',part.step));
  const fallback = byId('part-fallback');
  const canvas = byId('part-canvas');
  fallback.src = 'reports/parts/' + part.id + '.png';
  fallback.alt = title(part);
  fallback.hidden = true;
  canvas.hidden = false;
  byId('part-help').textContent = 'Drag to rotate · scroll to zoom';
  if (!dialog.open) dialog.showModal();
  try {
    partViewer ??= new Viewer(canvas);
    partViewer.parts = [];
    partViewer.draw();
    await partViewer.load(part);
    if (selectedPartId !== part.id || !dialog.open) return;
    partViewer.parts = [part];
    partViewer.center = part.center;
    partViewer.extent = Math.hypot(...part.size_mm)*1.18;
    partViewer.resetCamera(part.id === 'Helmet_front' ? .95 : -1.15, .43);
    partViewer.draw();
  } catch (error) {
    console.warn('Part viewer:', error.message);
    if (selectedPartId !== part.id) return;
    canvas.hidden = true;
    fallback.hidden = false;
    byId('part-help').textContent = 'Static part view';
  }
}

function createCard(part) {
  const card = document.createElement('button');
  card.className = 'part-card';
  card.type = 'button';
  card.dataset.part = part.id;
  const image = document.createElement('img');
  image.src = 'reports/parts/' + part.id + '.png';
  image.loading = 'lazy';
  image.alt = '';
  const label = document.createElement('span');
  label.className = 'part-label';
  label.textContent = title(part);
  const subtitle = document.createElement('span');
  subtitle.className = 'part-meta';
  subtitle.textContent = part.hardware ? part.material : `${part.material} · STL + STEP`;
  card.append(image,label,subtitle);
  card.addEventListener('click',() => inspect(part));
  return card;
}

function drawCatalogue() {
  const terms = search.value.toLowerCase().trim().split(/\s+/);
  const selection = parts.filter(part => (!filter.value || part.group === filter.value)
    && terms.every(term => (title(part)+' '+part.group).toLowerCase().includes(term)));
  byId('part-count').textContent = `${selection.length} of ${parts.length} parts and allowances`;
  const fragment = document.createDocumentFragment();
  for (const group of groupOrder) {
    const members = selection.filter(part => part.group === group).sort((a,b) => order(a)-order(b));
    if (!members.length) continue;
    const region = document.createElement('section');
    region.className = 'part-group';
    const heading = document.createElement('h3');
    heading.textContent = `${group} · ${members.length}`;
    const grid = document.createElement('div');
    grid.className = 'part-grid';
    grid.append(...members.map(createCard));
    region.append(heading,grid);
    fragment.append(region);
  }
  if (!selection.length) {
    const message = document.createElement('p');
    message.textContent = 'No parts match this search.';
    fragment.append(message);
  }
  partList.replaceChildren(fragment);
}

function changePose() {
  for (const name of ['head','left','right']) {
    byId(name+'-value').value = byId(name).value+'°';
  }
  drawAssembly();
}

for (const control of ['inside','explode','head','left','right']) byId(control).addEventListener('input',changePose);
byId('front').onclick = () => { assembly?.resetCamera(-Math.PI/2,0); drawAssembly(); };
byId('rear').onclick = () => { assembly?.resetCamera(Math.PI/2,.17); drawAssembly(); };
byId('reset').onclick = () => {
  for (const name of ['head','left','right']) byId(name).value = 0;
  byId('inside').checked = byId('explode').checked = false;
  assembly?.resetCamera();
  changePose();
};
byId('close-part').onclick = () => dialog.close();
search.addEventListener('input',drawCatalogue);
filter.addEventListener('change',drawCatalogue);
window.addEventListener('hashchange',activate);
let fitViewer, fitStudy;
let fitRequested = false;
const readable = id => id.replaceAll('_',' ');
const fitCoverNames = ['Helmet_front','Helmet_rear','Hip_front','Hip_rear',
  'Torso_front','Torso_rear','Bottom_cover','Face_insert','Face_bezel',
  'Foot_L','Foot_R','Shoulder_housing_L','Shoulder_housing_R','Forearm_L','Forearm_R',
  'Palm_L','Palm_R'];

function drawConnectedFit() {
  if (!fitViewer || !fitStudy) return;
  const focus = byId('fit-focus').value;
  const yaw = +byId('fit-yaw').value;
  const context = parts.filter(p => fitCoverNames.includes(p.id) && byId('fit-shell').checked)
    .map(p => ({...p,opacity:.13}));
  const supports = parts.filter(p => !p.hardware && p.region!=='coupon' &&
    !shellPart(p) && byId('fit-mounts').checked).map(p=>({...p,opacity:.67}));
  const installed = fitStudy.meshes.filter(p => p.kind!=='wire' || byId('fit-wires').checked)
    .map(p => {
      const selected = !focus || focus === p.owner;
      const flag = p.flagged && byId('fit-flagged').checked;
      return {...p, color:flag ? [.95,.25,.18] : p.color, opacity:selected ? 1 : .1};
    });
  const target = installed.find(p => p.owner === focus);
  fitViewer.center = target ? target.center : [0,0,110];
  fitViewer.extent = target ? (target.kind === 'wire' ? 145 : 108) : 264;
  fitViewer.parts = [...installed,...supports,...context];
  fitViewer.pose = p => p.region === 'head' ? around([0,0,109.5*modelScale],'z',radians(yaw)) : identity();
  byId('fit-yaw-value').value = yaw + '°';
  const pose = fitStudy.head_sweep.find(p => p.yaw_deg === yaw);
  byId('fit-pose').textContent = pose?.contacts.length
    ? 'Fixed parts touch the moving head layout at this pose.'
    : 'No contact with fixed parts at this sampled pose.';
  const route = fitStudy.routes.find(r => r.id === focus);
  const component = fitStudy.components.find(p => p.id === focus);
  const contacts = fitStudy.rigid_contacts.filter(c => c.component === focus);
  const blockers = [...new Set(contacts.flatMap(c=>c.touches))].map(readable);
  let detail = 'Select a component or cable bundle to inspect its fit.';
  if (route) {
    const hits = [...new Set([...route.covers_hit,...route.supports_hit,...route.other_parts_hit])];
    detail = route.pins + '. ' + route.centerline_mm + ' mm route. ' +
      (hits.length ? 'Contacts: '+hits.map(readable).join(', ')+'.' : 'No contact with checked solids.');
  } else if (focus === 'usb_c_pd_board') {
    detail = usbFitDescription(fitStudy.usb_c);
  } else if (focus) {
    detail = (component?.basis ?? 'Provisional geometry for this component.') +
      (blockers.length ? ' Contacts: '+blockers.join(', ')+'.' : ' No contact with checked solids.');
  }
  byId('fit-detail').textContent = detail;
  fitViewer.draw();
}

function usbFitDescription(usb) {
  const hits = [...new Set([...usb.seated_case_hits, ...usb.unplugged_insertion_hits,
    ...usb.insertion_hardware_hits, ...usb.insertion_wire_hits])];
  return hits.length ? 'Plug gauge contacts '+hits.map(readable).join(', ')+'.' :
    'Seated and insertion gauges clear. The socket is recessed '+usb.setback_mm+' mm.';
}

function fitSummary(data) {
  const routeClear = data.routes.filter(r => !(r.covers_hit.length ||
    r.supports_hit.length || r.other_parts_hit.length)).length;
  const cards = [
    ['USB-C port', usbFitDescription(data.usb_c)],
    ['Mounts and plugs', data.rigid_contacts.length+' modelled component contacts with shell or mounts.'],
    ['Harness fit', routeClear+' of '+data.routes.length+' routes clear the checked solids. '+
      data.wire_pair_contacts.length+' overlaps outside shared connector fan-outs.'],
    ['Mechanical motion', 'Head and both arm ranges were sampled. Wire twist and strain need a physical test.'],
  ];
  byId('fit-findings').replaceChildren(...cards.map(([heading,description])=>{
    const card=document.createElement('article');
    card.className='fit-card';
    const h=document.createElement('h3');
    h.textContent=heading;
    const p=document.createElement('p');
    p.textContent=description;
    card.append(h,p);
    return card;
  }));
}

async function startConnectedFit() {
  if (!parts.length) return;
  if (fitRequested) {
    drawConnectedFit();
    return;
  }
  fitRequested = true;
  try {
    const response = await fetch('fit-study/connected-fit.json');
    if (!response.ok) throw new Error('Fit study unavailable');
    fitStudy = await response.json();
    fitViewer = new Viewer(byId('fit-canvas'));
    const display = [...fitStudy.meshes,...parts.filter(p=>!p.hardware && p.region!=='coupon')];
    const assets = await fetch('fit-study/fit-view-meshes.json');
    if (!assets.ok) throw new Error('Could not load fit meshes');
    const buffers = await assets.json();
    for (const part of display) {
      const data = Uint8Array.from(atob(buffers[part.id]), character=>character.charCodeAt(0));
      fitViewer.upload(part,data);
    }
    const select = byId('fit-focus');
    const names = new Map(fitStudy.components.map(p=>[p.id,p.label]));
    const wires = new Set(fitStudy.routes.map(p=>p.id));
    for (const owner of new Set(fitStudy.meshes.map(p=>p.owner))) {
      if (!wires.has(owner)) select.add(new Option(names.get(owner) ?? readable(owner),owner));
    }
    const cableGroup = document.createElement('optgroup');
    cableGroup.label = 'Wire bundles';
    for (const route of fitStudy.routes) cableGroup.append(new Option(route.label,route.id));
    select.append(cableGroup);
    byId('fit-verdict').textContent=fitStudy.service_checks_passed ?
      'CAD service checks passed' : 'Some CAD service checks need review';
    fitSummary(fitStudy);
    drawConnectedFit();
  } catch (error) {
    byId('fit-verdict').textContent=error.message;
  }
}

for (const id of ['fit-shell','fit-mounts','fit-wires','fit-flagged','fit-focus','fit-yaw']) {
  byId(id).addEventListener('input',drawConnectedFit);
}
byId('fit-front').onclick=()=>{ fitViewer?.resetCamera(-Math.PI/2,0);drawConnectedFit(); };
byId('fit-rear').onclick=()=>{ fitViewer?.resetCamera(Math.PI/2,.22);drawConnectedFit(); };
byId('fit-reset').onclick=()=>{
  byId('fit-focus').value='';
  byId('fit-yaw').value=0;
  fitViewer?.resetCamera();
  drawConnectedFit();
};
activate();

try {
  const response = await fetch('preview-data.json');
  if (!response.ok) throw new Error('CAD catalogue unavailable');
  const data = await response.json();
  parts = data.parts;
  modelScale = data.scale;
  for (const group of groupOrder) filter.add(new Option(group,group));
  drawCatalogue();
  activate();
} catch (error) {
  byId('assembly-info').textContent = error.message;
  byId('part-count').textContent = error.message;
}
