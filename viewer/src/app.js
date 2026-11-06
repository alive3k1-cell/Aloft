import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {PointerLockControls} from 'three/addons/controls/PointerLockControls.js';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {GTAOPass} from 'three/addons/postprocessing/GTAOPass.js';
import {UnrealBloomPass} from 'three/addons/postprocessing/UnrealBloomPass.js';
import {OutputPass} from 'three/addons/postprocessing/OutputPass.js';
import {ShaderPass} from 'three/addons/postprocessing/ShaderPass.js';
import {FXAAShader} from 'three/addons/shaders/FXAAShader.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {RectAreaLightUniformsLib} from 'three/addons/lights/RectAreaLightUniformsLib.js';
import {GROUPS,GROUP_NAMES,PRESETS,DESCRIPTIONS,defaults,sanitize,applyVariant,daylight,clockLabel,programWeights,kelvinRGB,environmentLighting} from './state.js';
import {installLightShader} from './light-shader.js';
import {installSpillOcclusion,prepareSpillAttributes} from './spill-occlusion.js';

const $=id=>document.getElementById(id);const assets=JSON.parse($('asset-data').textContent);const meta=assets.metadata;const STORAGE='aloft-workbench-v10';
let state;try{state=sanitize(JSON.parse(localStorage.getItem(STORAGE)||'{}'));}catch{state=defaults();}
const stage=$('stage');let renderer,scene,camera,orbit,pointer,composer,bloomPass,fxaaPass,renderPass,aoPass;
let elapsed=0,ready=false,activeReference=null,activeView=state.view,lastTick=performance.now(),fpsTick=lastTick,fpsFrames=0;let cameraType='perspective',needsRender=true,actualFrames=0;
const architecture=[],context=[],neon=[],spill=[],collision=[],keys=new Set();const architectureSources=new Map();const lightUniforms={};const fitPoints=[];let root,sky,sun,fill,hemisphere,fallbackGround,environmentTarget;
let toastTimer;function toast(message){$('toast').textContent=message;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,3000);}
function persist(){needsRender=true;try{localStorage.setItem(STORAGE,JSON.stringify(state));}catch{}}
function download(blob,name){const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),3000);}
function roleOf(o){for(let p=o;p;p=p.parent)if(p.userData.viewer_role)return p.userData;return {};}
function uniformSet(g){return {uTime:{value:0},uMode:{value:2},uMaster:{value:state.master},uLevel:{value:state.groups[g].level},uWhite:{value:state.groups[g].white},uRGB:{value:new THREE.Color(...state.groups[g].rgb)},uWhiteColor:{value:new THREE.Color(1,1,1)},uWaveDepth:{value:.65},uColorAmount:{value:.5},uChaseWidth:{value:.22},uPool:{value:g==='POOL'?1:0},uPoolEffects:{value:0},uPixelHeight:{value:stage.clientHeight},uShow:{value:new THREE.Vector4(1,0,0,0)}};}

function prepareNeonCenters(ob,points){
 ob.updateWorldMatrix(true,false);const inverse=ob.matrixWorld.clone().invert();const path=points.map(p=>new THREE.Vector3().fromArray(p).applyMatrix4(inverse));const pos=ob.geometry.attributes.position;const centers=new Float32Array(pos.count*3);const p=new THREE.Vector3(),best=new THREE.Vector3(),q=new THREE.Vector3(),v=new THREE.Vector3();
 for(let i=0;i<pos.count;i++){p.fromBufferAttribute(pos,i);let dist=Infinity;for(let j=0;j<path.length-1;j++){v.subVectors(path[j+1],path[j]);const t=THREE.MathUtils.clamp(q.subVectors(p,path[j]).dot(v)/v.lengthSq(),0,1);q.copy(path[j]).addScaledVector(v,t);const d=q.distanceToSquared(p);if(d<dist){dist=d;best.copy(q);}}best.toArray(centers,i*3);}
 ob.geometry.setAttribute('aNeonCenter',new THREE.BufferAttribute(centers,3));ob.frustumCulled=false;
}

function createSky(){
 const material=new THREE.ShaderMaterial({side:THREE.BackSide,depthWrite:false,uniforms:{uDay:{value:0},uSun:{value:new THREE.Vector3(0,1,0)}},vertexShader:'varying vec3 vDirection;void main(){vDirection=normalize(position);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',fragmentShader:`varying vec3 vDirection;uniform float uDay;uniform vec3 uSun;void main(){vec3 d=normalize(vDirection);float h=smoothstep(-.07,.3,d.y);vec3 night=mix(vec3(.005,.006,.009),vec3(.0018,.003,.007),h);vec3 day=mix(vec3(.6,.72,.82),vec3(.12,.34,.65),h);vec3 c=mix(night,day,uDay);float disk=smoothstep(.9998,.99995,dot(d,normalize(uSun)))*uDay;c+=vec3(3.,2.7,2.)*disk;gl_FragColor=vec4(c,1.);}`,toneMapped:false});
 sky=new THREE.Mesh(new THREE.SphereGeometry(800,32,20),material);sky.frustumCulled=false;sky.renderOrder=-100;scene.add(sky);
}
function setNavigation(mode,lock=false){
 needsRender=true;
 state.navigation=mode;
 if(pointer?.isLocked&&mode==='orbit')pointer.unlock();
 if(orbit)orbit.enabled=mode==='orbit';
 $('orbit').classList.toggle('active',mode==='orbit');$('walk').classList.toggle('active',mode==='walk');$('orbit').setAttribute('aria-pressed',String(mode==='orbit'));$('walk').setAttribute('aria-pressed',String(mode==='walk'));
 $('walk-help').hidden=mode!=='walk';$('navigation-hint').textContent=mode==='walk'?'WASD — движение · мышь — осмотр · Esc — отпустить мышь':'Мышь — вращение · колесо — масштаб · ПКМ — сдвиг';
 if(lock&&mode==='walk')pointer.lock();
}
function createControls(target){
 if(document.pointerLockElement===renderer.domElement)document.exitPointerLock();orbit?.dispose();pointer?.dispose();orbit=new OrbitControls(camera,renderer.domElement);orbit.target.copy(target);orbit.enableDamping=true;orbit.dampingFactor=.075;orbit.minDistance=1;orbit.maxDistance=320;orbit.minPolarAngle=.001;orbit.maxPolarAngle=Math.PI*.64;orbit.maxZoom=20;orbit.minZoom=.1;
 pointer=new PointerLockControls(camera,renderer.domElement);pointer.addEventListener('change',()=>needsRender=true);pointer.addEventListener('lock',()=>$('walk-help').hidden=true);pointer.addEventListener('unlock',()=>{$('walk-help').hidden=state.navigation!=='walk';keys.clear();});orbit.update();setNavigation('orbit');
}
function applyFraming(){
 const aspect=stage.clientWidth/stage.clientHeight;
 if(activeReference){const [rw,rh]=activeReference.resolution,[cx,cy]=activeReference.principalPoint;const dx=2*(cx-rw/2)/rh/aspect,dy=-2*(cy-rh/2)/rh;
  if(camera.isPerspectiveCamera){camera.projectionMatrix.elements[8]=-dx;camera.projectionMatrix.elements[9]=-dy;}else{camera.projectionMatrix.elements[12]=dx;camera.projectionMatrix.elements[13]=dy;}camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
 }
}
function resize(){
 needsRender=true;
 if(!renderer||!camera)return;const w=stage.clientWidth,h=stage.clientHeight;const aspect=w/h;
 if(camera.isPerspectiveCamera)camera.aspect=aspect;else{const hh=camera.userData.orthoHeight/2;camera.left=-hh*aspect;camera.right=hh*aspect;camera.top=hh;camera.bottom=-hh;}
 camera.updateProjectionMatrix();applyFraming();
 renderer.setSize(w,h,false);composer?.setSize(w,h);for(const u of Object.values(lightUniforms))u.uPixelHeight.value=h*renderer.getPixelRatio();if(fxaaPass){const dpr=renderer.getPixelRatio();fxaaPass.material.uniforms.resolution.value.set(1/(w*dpr),1/(h*dpr));}
}
function disposePost(){
 if(composer){for(const p of composer.passes)p.dispose?.();composer.dispose();composer=null;}bloomPass=null;fxaaPass=null;aoPass=null;
}
function configureQuality(){
 if(!renderer)return;disposePost();const q=state.quality;const dpr=q==='fast'?Math.min(window.devicePixelRatio,1):q==='cinematic'?Math.min(window.devicePixelRatio*1.4,2):Math.min(window.devicePixelRatio,1.5);
 renderer.setPixelRatio(dpr);renderer.transmissionResolutionScale=q==='cinematic'?1:.5;renderer.shadowMap.enabled=q!=='fast';renderer.shadowMap.type=q==='cinematic'?THREE.PCFSoftShadowMap:THREE.PCFShadowMap;
 const chosen=new Set();for(const g of GROUPS){const members=spill.filter(a=>a.userData.group===g);if(members.length)chosen.add(members.reduce((a,b)=>a.width>b.width?a:b));}for(const a of spill){a.visible=q!=='fast';a.userData.qualityEnabled=q==='cinematic'||chosen.has(a);}
 const materials=new Set();for(const ob of architecture)for(const m of (Array.isArray(ob.userData.originalMaterial)?ob.userData.originalMaterial:[ob.userData.originalMaterial]))materials.add(m);
 for(const m of materials){const data=m.userData;if(data.viewerTransmission===undefined){data.viewerTransmission=m.transmission||0;data.viewerOpacity=m.opacity;data.viewerTransparent=m.transparent;data.viewerDepthWrite=m.depthWrite;}if(!data.viewerTransmission)continue;const trans=q==='cinematic'?data.viewerTransmission:0;const alpha=q!=='cinematic'&&data.viewerTransmission>.4;if(m.transmission!==trans||m.transparent!==(alpha||data.viewerTransparent)){m.transmission=trans;m.transparent=alpha||data.viewerTransparent;m.opacity=alpha?.28:data.viewerOpacity;m.depthWrite=alpha?false:data.viewerDepthWrite;m.needsUpdate=true;}}
 if(sun){const size=q==='cinematic'?2048:1024;if(sun.shadow.mapSize.x!==size){sun.shadow.map?.dispose();sun.shadow.map=null;sun.shadow.mapSize.set(size,size);}renderer.shadowMap.needsUpdate=true;}
 if(q!=='fast'){
  const target=new THREE.WebGLRenderTarget(1,1,{type:THREE.HalfFloatType,samples:Math.min(q==='cinematic'?4:2,renderer.capabilities.maxSamples)});composer=new EffectComposer(renderer,target);renderPass=new RenderPass(scene,camera);composer.addPass(renderPass);
  if(q==='cinematic'){aoPass=new GTAOPass(scene,camera,1,1);aoPass.blendIntensity=.35;composer.addPass(aoPass);}
  bloomPass=new UnrealBloomPass(new THREE.Vector2(1,1),state.bloom,.35,1.2);composer.addPass(bloomPass);composer.addPass(new OutputPass());fxaaPass=new ShaderPass(FXAAShader);composer.addPass(fxaaPass);
 }
 const aa=Math.min(q==='cinematic'?4:2,renderer.capabilities.maxSamples);$('quality-details').textContent=q==='fast'?'PBR · AgX · облегчённый просмотр':q==='cinematic'?`AgX · GTAO · Bloom · MSAA ×${aa} · FXAA`:'AgX · мягкие тени · Bloom · FXAA';resize();
}
function goView(id,ref=null){
 if(!ready)return;const p=ref|| (id==='saved'?state.savedView:PRESETS[id]);if(!p)return;
 const ortho=p.type==='ORTHO';const type=ortho?'ortho':'perspective';const changed=type!==cameraType;
 if(changed){camera=ortho?new THREE.OrthographicCamera(-1,1,1,-1,.05,2000):new THREE.PerspectiveCamera(44,1,.05,2000);cameraType=type;}
 camera.zoom=1;if(ortho)camera.userData.orthoHeight=p.orthoHeight;else camera.fov=p.fov||44;
 camera.position.fromArray(p.position);if(!ref&&['general','front','side','courtyard'].includes(id)&&stage.clientWidth/stage.clientHeight<.8){const target=new THREE.Vector3().fromArray(p.target);camera.position.sub(target).multiplyScalar(.8/(stage.clientWidth/stage.clientHeight)).add(target);}activeReference=ref||p.framing||null;createControls(new THREE.Vector3().fromArray(p.target));
 activeView=ref?'reference':id;state.view=ref?'general':id;state.reference=ref?ref.id:'';
 $('view-label').textContent=p.name;document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',!ref&&b.dataset.view===id));$('reference').value=state.reference;
 if(ref){$('reference-image').src=assets.photos[ref.id];$('reference-title').textContent=ref.name;$('reference-box').hidden=false;}else $('reference-box').hidden=true;
 if(changed)configureQuality();resize();
 if(!ref&&!p.framing&&['general','front','side','courtyard'].includes(id)){
  for(let i=0;i<30;i++){camera.updateMatrixWorld();const clip=fitPoints.map(v=>v.clone().project(camera));if(clip.every(v=>Math.abs(v.x)<.88&&Math.abs(v.y)<.88))break;camera.position.sub(orbit.target).multiplyScalar(1.07).add(orbit.target);orbit.update();}
 }
 persist();
}
function applyMaterials(){
 for(const ob of architecture){const old=ob.userData.originalMaterial;if(state.materials==='original')ob.material=old;else{if(!ob.userData.clayMaterial)ob.userData.clayMaterial=installSpillOcclusion(new THREE.MeshStandardMaterial({color:0xb8beb7,roughness:.72}));if(!ob.userData.wireMaterial)ob.userData.wireMaterial=new THREE.MeshBasicMaterial({color:0xc7d6bd,wireframe:true});ob.material=state.materials==='clay'?ob.userData.clayMaterial:ob.userData.wireMaterial;}}
 for(const ob of context)ob.visible=state.context;fallbackGround.visible=!state.context;
 for(const ob of neon)ob.visible=state.showNeon;
 renderer.shadowMap.needsUpdate=true;
}
function applyEnvironment(){
 if(!scene)return;const lighting=environmentLighting(state.time);const day=lighting.day;const angle=(state.time-6)*Math.PI/12;
 sun.position.set(26+Math.cos(angle)*70,Math.max(-15,Math.sin(angle)*90),-15-55);sun.intensity=lighting.sun;sun.color.setRGB(1, .85+.12*day,.7+.28*day);
 hemisphere.intensity=lighting.hemisphere;hemisphere.color.set(0x8194bc).lerp(new THREE.Color(0xddeeff),day);hemisphere.groundColor.set(0x343541).lerp(new THREE.Color(0x9a9481),day);fill.intensity=lighting.fill;scene.environmentIntensity=lighting.environment;
 sky.material.uniforms.uDay.value=day;sky.material.uniforms.uSun.value.copy(sun.position).sub(new THREE.Vector3(26,0,-15)).normalize();renderer.toneMappingExposure=2**state.exposure;renderer.shadowMap.needsUpdate=true;
 $('day').classList.toggle('active',day>.5);$('night').classList.toggle('active',day<=.5);$('environment-label').textContent=day>.5?'ДЕНЬ':'НОЧЬ';
}
function updateLights(){
 const modes={reference:0,fade:1,wave:2,chase:3,dots:4,show:5};const white=new THREE.Color().setRGB(...kelvinRGB(state.kelvin),THREE.SRGBColorSpace);const weights=programWeights(elapsed);
 for(const g of GROUPS){const u=lightUniforms[g],v=state.groups[g];if(!u)continue;u.uTime.value=elapsed;u.uMode.value=modes[state.scenario];u.uMaster.value=state.master*(state.showNeon?1:0);u.uLevel.value=v.enabled?v.level:0;u.uWhite.value=v.white;u.uRGB.value.setRGB(...v.rgb);u.uWhiteColor.value.copy(white);u.uPoolEffects.value=state.poolEffects?1:0;u.uShow.value.fromArray(weights);}
 for(const a of spill){const g=state.groups[a.userData.group];a.color.setRGB(g.rgb[0]+white.r*g.white,g.rgb[1]+white.g*g.white,g.rgb[2]+white.b*g.white);a.intensity=(g.enabled&&state.showNeon&&a.userData.qualityEnabled?1:0)*state.master*g.level*(a.userData.group==='POOL'?90:60)*(state.scenario==='reference'?1:.65);}
 if(bloomPass)bloomPass.strength=state.bloom;
}
function walkStep(dt){
 if(state.navigation!=='walk'||!pointer.isLocked)return;let x=0,z=0;if(keys.has('KeyW')||keys.has('ArrowUp'))z+=1;if(keys.has('KeyS')||keys.has('ArrowDown'))z-=1;if(keys.has('KeyD')||keys.has('ArrowRight'))x+=1;if(keys.has('KeyA')||keys.has('ArrowLeft'))x-=1;if(!x&&!z)return;
 const forward=new THREE.Vector3();camera.getWorldDirection(forward);forward.y=0;forward.normalize();const right=new THREE.Vector3().crossVectors(forward,new THREE.Vector3(0,1,0));const v=forward.multiplyScalar(z).addScaledVector(right,x).normalize();const step=dt*(keys.has('ShiftLeft')?8:3.5);const ray=new THREE.Raycaster(camera.position,v,0,step+.45);if(ray.intersectObjects(collision,false).length)return;
 camera.position.addScaledVector(v,step);camera.position.x=THREE.MathUtils.clamp(camera.position.x,-85,135);camera.position.z=THREE.MathUtils.clamp(camera.position.z,-105,90);camera.position.y=.15;needsRender=true;
}
function tick(now){
 const rawDt=Math.max(0,(now-lastTick)/1000);const dt=Math.min(.05,rawDt);lastTick=now;if(state.playing&&!document.hidden)elapsed+=rawDt*state.speed;
 walkStep(dt);if(state.navigation==='orbit'&&orbit.update())needsRender=true;if(state.playing&&state.scenario!=='reference')needsRender=true;
 if(needsRender){applyFraming();if(camera.position.y< -1.35)camera.position.y=-1.35;sky.position.copy(camera.position);updateLights();if(composer)composer.render(dt);else renderer.render(scene,camera);actualFrames++;fpsFrames++;needsRender=false;}
 if(now-fpsTick>=1000){$('fps').textContent=fpsFrames?Math.round(fpsFrames*1000/(now-fpsTick))+' FPS':'Пауза';fpsFrames=0;fpsTick=now;}
}

async function init(){
 renderer=new THREE.WebGLRenderer({antialias:false,alpha:false,preserveDrawingBuffer:true,powerPreference:'high-performance'});renderer.setClearColor(0x172029);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.AgXToneMapping;renderer.shadowMap.autoUpdate=false;renderer.domElement.setAttribute('aria-label','3D-сцена: вращайте мышью для осмотра');renderer.domElement.tabIndex=0;stage.prepend(renderer.domElement);
 scene=new THREE.Scene();camera=new THREE.PerspectiveCamera(44,1,.05,2000);createSky();RectAreaLightUniformsLib.init();
 const pmrem=new THREE.PMREMGenerator(renderer);const room=new RoomEnvironment();environmentTarget=pmrem.fromScene(room,.04);scene.environment=environmentTarget.texture;room.dispose();pmrem.dispose();
 sun=new THREE.DirectionalLight(0xffefd8,2.6);sun.castShadow=true;sun.shadow.camera.left=-65;sun.shadow.camera.right=65;sun.shadow.camera.top=70;sun.shadow.camera.bottom=-65;sun.shadow.camera.near=1;sun.shadow.camera.far=240;sun.shadow.bias=-.0003;sun.shadow.normalBias=.025;sun.target.position.set(26,20,-15);scene.add(sun,sun.target);
 hemisphere=new THREE.HemisphereLight(0xddeeff,0x343541,1);fill=new THREE.DirectionalLight(0xc4d6ef,.3);fill.position.set(-25,50,-65);scene.add(hemisphere,fill);
 fallbackGround=new THREE.Mesh(new THREE.PlaneGeometry(450,450),new THREE.MeshStandardMaterial({color:0x515852,roughness:1}));fallbackGround.rotation.x=-Math.PI/2;fallbackGround.position.set(26,-1.53,-15);fallbackGround.receiveShadow=true;scene.add(fallbackGround);
 const raw=atob(assets.model);const buffer=new Uint8Array(raw.length);for(let i=0;i<raw.length;i++)buffer[i]=raw.charCodeAt(i);
 const gltf=await new GLTFLoader().parseAsync(buffer.buffer,'');root=gltf.scene;scene.add(root);
 for(const g of GROUPS)lightUniforms[g]=uniformSet(g);
 root.traverse(ob=>{if(!ob.isMesh)return;const data=roleOf(ob);
  if(data.viewer_role!=='neon'){prepareSpillAttributes(ob,data.viewer_role==='architecture');for(const m of (Array.isArray(ob.material)?ob.material:[ob.material]))installSpillOcclusion(m);}
  ob.frustumCulled=true;const mats=Array.isArray(ob.material)?ob.material:[ob.material];const glass=mats.some(m=>m.transmission>.2||m.transparent);ob.castShadow=!glass;ob.receiveShadow=true;
  if(data.viewer_role==='architecture'){architecture.push(ob);architectureSources.set(data.viewer_source,Math.max(architectureSources.get(data.viewer_source)||0,ob.isInstancedMesh?ob.count:1));ob.userData.originalMaterial=ob.material;if(data.viewer_source.startsWith('BUILDING_WING_ENVELOPE'))collision.push(ob);}
  if(data.viewer_role==='context')context.push(ob);
  if(data.viewer_role==='neon'){const g=data.group;if(!GROUPS.includes(g)||!ob.geometry.attributes.uv)throw new Error('Отсутствуют данные светового контура');const route=meta.segments.find(s=>s.id===data.segment_id);if(!route)throw new Error('Не найдена исходная линия');prepareNeonCenters(ob,route.points);const m=new THREE.MeshStandardMaterial({color:0x333333,emissive:0xffffff,roughness:.35});installLightShader(m,lightUniforms[g]);ob.material=m;ob.castShadow=false;ob.receiveShadow=false;neon.push(ob);}
 });
 for(const p of meta.spill){const a=new THREE.RectAreaLight(0xffffff,1,p.width,p.height);a.position.fromArray(p.position);const x=new THREE.Vector3().fromArray(p.xAxis).normalize(),z=new THREE.Vector3().fromArray(p.direction).negate().normalize(),y=new THREE.Vector3().crossVectors(z,x).normalize();a.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(x,y,z));a.userData.group=p.group;scene.add(a);spill.push(a);}
 const architectureCount=[...architectureSources.values()].reduce((a,b)=>a+b,0);if(neon.length!==meta.visible_segments||architectureCount!==meta.architecture_meshes)throw new Error('Не все части модели загрузились: '+architectureCount+'/'+neon.length);
 const box=new THREE.Box3();for(const ob of architecture)box.expandByObject(ob);box.min.y=Math.max(box.min.y,-1.5);for(const x of [box.min.x,box.max.x])for(const y of [box.min.y,box.max.y])for(const z of [box.min.z,box.max.z])fitPoints.push(new THREE.Vector3(x,y,z));
 ready=true;configureQuality();applyMaterials();applyEnvironment();syncUI();const initial=state.reference?meta.referenceCameras.find(c=>c.id===state.reference):null;goView(state.view,initial);$('loading').hidden=true;lastTick=fpsTick=performance.now();renderer.setAnimationLoop(tick);new ResizeObserver(resize).observe(stage);bindControls();
 window.__aloft={getState:()=>structuredClone(state),getStats:()=>({architecture:architectureCount,neon:neon.length,sourceSegments:meta.source_segments,spillOcclusion:meta.spill_occlusion?.method,supplementalSegments:meta.supplemental_segments,logicalPixels:meta.logical_pixels,cameraType,cameraPosition:camera.position.toArray(),navigation:state.navigation,pointerLocked:!!pointer?.isLocked,pressedKeys:[...keys],elapsed,quality:state.quality,ao:!!aoPass,composer:!!composer,sceneChildren:root.children.length,frame:actualFrames}),getLightStats:()=>Object.fromEntries(GROUPS.map(g=>[g,{master:lightUniforms[g].uMaster.value,level:lightUniforms[g].uLevel.value,rgb:lightUniforms[g].uRGB.value.toArray(),white:lightUniforms[g].uWhite.value,poolEffects:lightUniforms[g].uPoolEffects.value}])),setTime:t=>{elapsed=t;updateLights();needsRender=true;},getEnvironmentStats:()=>({day:daylight(state.time),sun:sun.intensity,hemisphere:hemisphere.intensity,fill:fill.intensity,environment:scene.environmentIntensity}),getRenderer:()=>renderer};
}

function syncUI(){
 for(const [id,key] of [['time','time'],['exposure','exposure'],['quality','quality'],['variant','variant'],['scenario','scenario'],['speed','speed'],['master','master'],['bloom','bloom'],['kelvin','kelvin'],['materials','materials']])$(id).value=state[key];
 for(const [id,key] of [['pool-effects','poolEffects'],['context','context'],['show-neon','showNeon']])$(id).checked=state[key];
 $('time-value').textContent=clockLabel(state.time);$('exposure-value').textContent=state.exposure.toFixed(2);$('speed-value').textContent=state.speed.toFixed(2)+'×';$('master-value').textContent=Math.round(state.master*100)+'%';$('bloom-value').textContent=Math.round(state.bloom*100)+'%';$('kelvin-value').textContent=state.kelvin+' K';$('scenario-description').textContent=DESCRIPTIONS[state.scenario];$('play').textContent=state.playing?'Ⅱ Пауза':'▶ Воспроизвести';
 $('quality-index').textContent=state.tab==='lighting'?'03':'04';$('saved-view').hidden=!state.savedView;$('lighting-panel').hidden=state.tab!=='lighting';$('architecture-panel').hidden=state.tab!=='architecture';document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('active',b.dataset.tab===state.tab));
 for(const g of GROUPS){const v=state.groups[g];$('g-'+g+'-enabled').checked=v.enabled;$('g-'+g+'-color').value='#'+new THREE.Color(...v.rgb).getHexString();$('g-'+g+'-level').value=v.level;$('g-'+g+'-white').value=v.white;$('g-'+g+'-level-value').textContent=Math.round(v.level*100)+'%';$('g-'+g+'-white-value').textContent=Math.round(v.white*100)+'%';}
}

function bindControls(){
 document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>goView(b.dataset.view)));
 document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>{state.tab=b.dataset.tab;syncUI();persist();}));
 $('reference').addEventListener('change',e=>{const p=meta.referenceCameras.find(c=>c.id===e.target.value);if(p)goView('reference',p);else goView('general');});$('close-reference').onclick=()=>$('reference-box').hidden=true;
 if(typeof renderer.domElement.requestPointerLock!=='function'){$('walk').disabled=true;$('walk').title='Прогулка требует браузер с мышью и клавиатурой';}$('orbit').onclick=()=>setNavigation('orbit');$('walk').onclick=()=>{if(camera.isOrthographicCamera)goView('street');camera.position.set(58,.15,-50);camera.lookAt(27,18,-30);setNavigation('walk',true);};renderer.domElement.addEventListener('click',()=>{if(state.navigation==='walk'&&!pointer.isLocked)pointer.lock();});
 $('save-view').onclick=()=>{const target=state.navigation==='orbit'?orbit.target.clone():camera.position.clone().addScaledVector(camera.getWorldDirection(new THREE.Vector3()),20);state.savedView={name:'Мой ракурс',position:camera.position.toArray(),target:target.toArray(),type:camera.isOrthographicCamera?'ORTHO':'PERSP',orthoHeight:camera.isOrthographicCamera?camera.userData.orthoHeight/camera.zoom:50,fov:camera.fov||44,framing:activeReference?{principalPoint:activeReference.principalPoint,resolution:activeReference.resolution}:null};syncUI();persist();toast('Ракурс сохранён');};
 $('day').onclick=()=>{state.time=13;syncUI();applyEnvironment();persist();};$('night').onclick=()=>{state.time=23.5;syncUI();applyEnvironment();persist();};
 for(const [id,key] of [['time','time'],['exposure','exposure'],['speed','speed'],['master','master'],['bloom','bloom'],['kelvin','kelvin']])$(id).addEventListener('input',e=>{state[key]=Number(e.target.value);syncUI();if(key==='time'||key==='exposure')applyEnvironment();updateLights();persist();});
 $('quality').onchange=e=>{state.quality=e.target.value;configureQuality();persist();};$('variant').onchange=e=>{if(e.target.value!=='custom')applyVariant(state,e.target.value);else state.variant='custom';syncUI();updateLights();persist();};
 $('scenario').onchange=e=>{state.scenario=e.target.value;if(state.scenario==='dots'&&state.variant!=='custom')applyVariant(state,'lime');elapsed=0;syncUI();updateLights();persist();};$('play').onclick=()=>{state.playing=!state.playing;syncUI();persist();};$('restart').onclick=()=>{elapsed=0;updateLights();toast('Сценарий запущен сначала');};
 for(const [id,key] of [['pool-effects','poolEffects'],['context','context'],['show-neon','showNeon']])$(id).onchange=e=>{state[key]=e.target.checked;applyMaterials();updateLights();persist();};$('materials').onchange=e=>{state.materials=e.target.value;applyMaterials();persist();};
 for(const g of GROUPS){$('g-'+g+'-enabled').onchange=e=>{state.groups[g].enabled=e.target.checked;state.variant='custom';syncUI();persist();};$('g-'+g+'-color').addEventListener('input',e=>{state.groups[g].rgb=new THREE.Color(e.target.value).toArray();state.variant='custom';syncUI();persist();});for(const key of ['level','white'])$('g-'+g+'-'+key).addEventListener('input',e=>{state.groups[g][key]=Number(e.target.value);state.variant='custom';syncUI();updateLights();persist();});}
 $('fullscreen').onclick=async()=>{try{if(!document.fullscreenElement)await $('app').requestFullscreen();else await document.exitFullscreen();}catch{toast('Браузер не разрешил полноэкранный режим');}};
 $('snapshot').onclick=()=>{if(composer)composer.render(0);else renderer.render(scene,camera);renderer.domElement.toBlob(blob=>{if(blob)download(blob,'Aloft_'+state.scenario+'.png');});};
 $('panel-toggle').onclick=()=>{document.body.classList.toggle('panel-closed');$('panel-toggle').setAttribute('aria-expanded',String(!document.body.classList.contains('panel-closed')));resize();};
 $('export-settings').onclick=()=>download(new Blob([JSON.stringify(state,null,2)],{type:'application/json'}),'Aloft_lighting_settings.json');$('import-settings').onclick=()=>$('settings-file').click();$('settings-file').onchange=async e=>{try{const f=e.target.files[0];if(!f)return;if(f.size>100000)throw new Error();const loaded=JSON.parse(await f.text());if(loaded.schema!=='aloft-workbench/1')throw new Error();state=sanitize(loaded);elapsed=0;configureQuality();applyEnvironment();applyMaterials();syncUI();goView(state.view,state.reference?meta.referenceCameras.find(c=>c.id===state.reference):null);persist();toast('Настройки загружены');}catch{toast('Не удалось прочитать настройки. Выберите JSON, сохранённый из Aloft.');}e.target.value='';};
 $('reset').onclick=()=>{state=defaults();elapsed=0;configureQuality();applyEnvironment();applyMaterials();syncUI();goView('general');persist();toast('Настройки сброшены');};
 window.addEventListener('keydown',e=>{if(e.code==='Escape'&&pointer.isLocked){pointer.unlock();keys.clear();return;}if(/INPUT|SELECT|TEXTAREA/.test(document.activeElement?.tagName))return;keys.add(e.code);if(e.code==='Space'){e.preventDefault();state.playing=!state.playing;syncUI();persist();}if(e.code==='KeyN'){$(daylight(state.time)>.5?'night':'day').click();}if(e.code.startsWith('Digit')){const n=Number(e.code.slice(5));const v=Object.keys(PRESETS)[n-1];if(v)goView(v);}});window.addEventListener('keyup',e=>keys.delete(e.code));window.addEventListener('blur',()=>keys.clear());document.addEventListener('visibilitychange',()=>{lastTick=fpsTick=performance.now();fpsFrames=0;});
}

for(const g of GROUPS){const item=document.createElement('div');item.className='group';item.innerHTML=`<div class="group-top"><label><input id="g-${g}-enabled" type="checkbox" checked>${GROUP_NAMES[g]}</label><input id="g-${g}-color" type="color" aria-label="${GROUP_NAMES[g]}: цвет RGB"></div><div class="group-bottom"><div><label class="range-label" for="g-${g}-level">Яркость<output id="g-${g}-level-value"></output></label><input id="g-${g}-level" type="range" min="0" max="1" step=".01"></div><div><label class="range-label" for="g-${g}-white">Белый W<output id="g-${g}-white-value"></output></label><input id="g-${g}-white" type="range" min="0" max="1" step=".01"></div></div>`;$('group-controls').append(item);}
for(const r of meta.referenceCameras){const option=document.createElement('option');option.value=r.id;option.textContent=r.name;$('reference').append(option);}
if(matchMedia('(max-width:800px)').matches)document.body.classList.add('panel-closed');
init().catch(error=>{console.error(error);$('loading').hidden=true;$('error').hidden=false;$('error').textContent='Не удалось открыть 3D-модель. Попробуйте актуальный Chrome или Edge с аппаратным ускорением. '+error.message;});
