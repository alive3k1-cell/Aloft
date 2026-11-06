import * as THREE from 'three';
// Visibility of the eleven fixed, diffuse-only fill strips is baked against the
// opaque architecture. Geometry, camera movement and RGBW animation stay unchanged.
export function prepareSpillAttributes(object,required=false){
 for(let i=0;i<3;i++){
  const name='_spill_vis'+i;
  if(!object.geometry.getAttribute(name)){
   if(required)throw new Error('Отсутствует проверка перекрытия света: '+object.name);
   // Site/context and mounting channels do not receive the facade fill proxies.
   object.geometry.setAttribute(name,new THREE.Uint8BufferAttribute(new Uint8Array(object.geometry.attributes.position.count*4),4,true));
  }
 }
}
export function installSpillOcclusion(material){
 if(material.userData.spillOcclusionInstalled)return material;
 material.userData.spillOcclusionInstalled=true;
 material.onBeforeCompile=shader=>{
  const varyings='varying vec4 vSpillVis0,vSpillVis1,vSpillVis2;';
  shader.vertexShader=shader.vertexShader.replace('#include <common>','#include <common>\nattribute vec4 _spill_vis0,_spill_vis1,_spill_vis2;\n'+varyings).replace('#include <begin_vertex>','#include <begin_vertex>\nvSpillVis0=_spill_vis0;vSpillVis1=_spill_vis1;vSpillVis2=_spill_vis2;');
  shader.fragmentShader=shader.fragmentShader.replace('#include <common>','#include <common>\n'+varyings+'\nfloat spillVisibility(int i){if(i<4)return vSpillVis0[i];if(i<8)return vSpillVis1[i-4];return vSpillVis2[i-8];}\n');
  const call='RE_Direct_RectArea( rectAreaLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );';
  if(!THREE.ShaderChunk.lights_fragment_begin.includes(call))throw new Error('Изменилась версия шейдера освещения');
  const chunk=THREE.ShaderChunk.lights_fragment_begin.replace(call,`{
   if(max(max(rectAreaLight.color.r,rectAreaLight.color.g),rectAreaLight.color.b)>0. && spillVisibility(UNROLLED_LOOP_INDEX)>0.){
   vec3 beforeDiffuse=reflectedLight.directDiffuse;
   vec3 beforeSpecular=reflectedLight.directSpecular;
   ${call}
   reflectedLight.directDiffuse=mix(beforeDiffuse,reflectedLight.directDiffuse,spillVisibility(UNROLLED_LOOP_INDEX));
   reflectedLight.directSpecular=beforeSpecular;
   }
  }`);
  shader.fragmentShader=shader.fragmentShader.replace('#include <lights_fragment_begin>',chunk);
 };
 material.customProgramCacheKey=()=> 'aloft-occluded-diffuse-spill-v12';return material;
}
