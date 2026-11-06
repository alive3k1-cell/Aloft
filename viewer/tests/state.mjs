import assert from 'node:assert/strict';import {defaults,sanitize,applyVariant,daylight,clockLabel,programWeights,kelvinRGB,GROUPS,environmentLighting} from '../src/state.js';
const original=defaults();const s=sanitize({...original,master:9,speed:-5,exposure:Infinity,time:50,quality:'unknown',groups:{POOL:{rgb:[-1,2,.5],white:3,level:-2,enabled:false}}});
assert.equal(s.master,1);assert.equal(s.speed,.1);assert.equal(s.exposure,.4);assert.equal(s.time,23.99);assert.equal(s.quality,'balanced');assert.deepEqual(s.groups.POOL.rgb,[0,1,.5]);assert.equal(s.groups.POOL.white,1);assert.equal(s.groups.POOL.level,0);assert.equal(s.groups.POOL.enabled,false);
assert.throws(()=>sanitize(null));assert.throws(()=>sanitize([]));
const saved={name:'test',position:[1,2,3],target:[4,5,6],type:'ORTHO',orthoHeight:45,fov:40,framing:{principalPoint:[640,362.5],resolution:[1280,725]}};const rt=sanitize({...original,savedView:saved,view:'saved'});assert.equal(rt.savedView.type,'ORTHO');assert.deepEqual(rt.savedView.framing,saved.framing);assert.equal(rt.view,'saved');assert.equal(sanitize({view:'saved',savedView:{position:[1,2,3],target:[1,2,3]}}).view,'general');
for(const id of ['reference','cool','warm','lime']){const p=defaults();applyVariant(p,id);assert.equal(p.variant,id);assert.deepEqual(sanitize(JSON.parse(JSON.stringify(p))),p);}
const warm=defaults();applyVariant(warm,'warm');assert.equal(warm.kelvin,3000);for(const g of GROUPS){assert.deepEqual(warm.groups[g].rgb,[0,0,0]);assert.equal(warm.groups[g].white,1);}
assert.ok(daylight(13)>.99);assert.ok(daylight(23.5)<.001);assert.ok(daylight(6)>0&&daylight(6)<1);assert.equal(clockLabel(23.5),'23:30');assert.equal(clockLabel(23.99),'23:59');
for(let t=-60;t<60;t+=.125){const w=programWeights(t);assert.ok(Math.abs(w.reduce((a,b)=>a+b)-1)<1e-9);assert.ok(w.every(x=>x>=0&&x<=1));assert.deepEqual(w,programWeights(t+30));}
assert.deepEqual(programWeights(0),[1,0,0,0]);assert.deepEqual(programWeights(8),[0,0,1,0]);assert.deepEqual(programWeights(18),[0,0,0,1]);assert.deepEqual(programWeights(26),[0,1,0,0]);const a=kelvinRGB(3000),b=kelvinRGB(6500);assert.ok(a[0]>a[2]);assert.ok(b[2]>a[2]);
console.log('State tests passed: input validation, presets, CCT, day/night and30s program.');

const night=environmentLighting(23.5),evening=environmentLighting(18+35/60),day=environmentLighting(13);
assert.ok(night.hemisphere>=.07&&night.hemisphere<.1);assert.ok(evening.day>.2);assert.ok(evening.hemisphere>night.hemisphere*3);
assert.equal(day.sun,2.6);assert.equal(day.hemisphere,.85);assert.equal(day.fill,.55);assert.equal(day.environment,.54);
for(let t=16;t<22;t+=1/60){const a=environmentLighting(t),b=environmentLighting(t+1/60);assert.ok(b.day<=a.day+1e-9);assert.ok(Math.abs(b.hemisphere-a.hemisphere)<.01);}
console.log('V12 environment passed: smooth twilight after18:35, readable night, unchanged daytime.');
